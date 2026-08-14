#!/usr/bin/env python3
# -*-coding:utf8-*-
import threading
import time
from contextlib import contextmanager
from typing import Optional, List, Dict, Iterator, TYPE_CHECKING

from .revo2 import FingerPosition

if TYPE_CHECKING:
    from pyAgxArm.protocols.can_protocol.drivers.core.arm_driver_abstract import ArmDriverAbstract
    from pyAgxArm.protocols.can_protocol.drivers.effector.revo2_pro import Revo2ProDriverDefault

DEFAULT_READ_HZ = 100.0
DEFAULT_SEND_HZ = 100.0
DEFAULT_FINGER_DURATIONS_MS: List[int] = [50] * 6


class _TunnelBusArbiter:
    """Serialize wrist-tunnel read/write SDK transactions."""

    def __init__(self) -> None:
        self._cond = threading.Condition()
        self._readers = 0
        self._writer_active = False
        self._writer_waiting = 0

    @contextmanager
    def read_session(
        self,
        *,
        try_only: bool = False,
        timeout: Optional[float] = None,
    ) -> Iterator[bool]:
        acquired = False
        with self._cond:
            deadline = None if timeout is None else time.monotonic() + timeout
            while self._writer_active or self._writer_waiting > 0:
                if try_only:
                    yield False
                    return
                if deadline is not None and time.monotonic() >= deadline:
                    yield False
                    return
                remaining = None if deadline is None else max(0.0, deadline - time.monotonic())
                self._cond.wait(timeout=remaining)
            self._readers += 1
            acquired = True
        try:
            yield True
        finally:
            if acquired:
                with self._cond:
                    self._readers -= 1
                    if self._readers == 0:
                        self._cond.notify_all()

    @contextmanager
    def write_session(self) -> Iterator[None]:
        with self._cond:
            self._writer_waiting += 1
            while self._readers > 0:
                self._cond.wait()
            self._writer_waiting -= 1
            self._writer_active = True
        try:
            yield
        finally:
            with self._cond:
                self._writer_active = False
                self._cond.notify_all()


class Revo2ProWrapper:

    EFFECTOR_OPTION_NAME = "REVO2_PRO"
    WRAPPER_NAME = "Revo2ProWrapper"
    IO_THREAD_NAME = "revo2-pro-io"

    FINGER_NAMES: List[str] = [
        'thumb_tip', 'thumb_base',
        'index_finger', 'middle_finger',
        'ring_finger', 'pinky_finger',
    ]

    POSITION_MIN: int = 0
    POSITION_MAX: int = 1000

    HAND_LEFT: str = "left"
    HAND_RIGHT: str = "right"

    def __init__(self, agx_arm, hand_side: Optional[str] = None):
        self._agx_arm: Optional[ArmDriverAbstract] = agx_arm
        self._effector: Optional[Revo2ProDriverDefault] = None
        self._hand_side = hand_side
        self._initialized: bool = False

        self._arbiter = _TunnelBusArbiter()
        self._poll_interval_s = 1.0 / DEFAULT_READ_HZ
        self._send_interval_s = 1.0 / DEFAULT_SEND_HZ
        self._position_tolerance = 1

        self._state_lock = threading.Lock()
        self._target_positions: Optional[List[int]] = None
        self._last_sent_positions: Optional[List[int]] = None

        self._cache_lock = threading.Lock()
        self._cached_finger_position: Optional[FingerPosition] = None

        self._poll_stop = threading.Event()
        self._poll_thread: Optional[threading.Thread] = None
        self._joint_control_enabled: bool = False

    @property
    def is_polling(self) -> bool:
        return self._poll_thread is not None and self._poll_thread.is_alive()

    def initialize(self) -> bool:
        if self._initialized:
            return True

        try:
            self._effector = self._agx_arm.init_effector(
                getattr(
                    self._agx_arm.OPTIONS.EFFECTOR,
                    self.EFFECTOR_OPTION_NAME,
                )
            )
            if self._hand_side in (self.HAND_LEFT, self.HAND_RIGHT):
                self._effector.set_hand_side(self._hand_side)
            self._initialized = True

            with self._arbiter.read_session() as acquired:
                if acquired:
                    self._effector.get_device_info()
                    self._read_finger_positions_sync(update_cache=True, bus_held=True)

            cached = self._get_cached_finger_position()
            if cached is not None:
                with self._state_lock:
                    self._target_positions = [
                        getattr(cached, name) for name in self.FINGER_NAMES
                    ]
                    self._last_sent_positions = list(self._target_positions)

            self.start_polling()
            return True
        except Exception as e:
            print(f"[{self.WRAPPER_NAME}] Initialization failed: {e}")
            self._initialized = False
            self._effector = None
            return False

    def start_polling(
        self,
        read_hz: Optional[float] = None,
        send_hz: Optional[float] = None,
        position_tolerance: Optional[int] = None,
    ) -> None:
        """Start background IO thread: serialized read/write, cache-only reads."""
        if read_hz is not None:
            self._poll_interval_s = 1.0 / float(read_hz)
        if send_hz is not None:
            self._send_interval_s = 1.0 / float(send_hz)
        if position_tolerance is not None:
            self._position_tolerance = int(position_tolerance)
        if self.is_polling:
            return
        self._poll_stop.clear()
        self._poll_thread = threading.Thread(
            target=self._io_loop,
            name=self.IO_THREAD_NAME,
            daemon=True,
        )
        self._poll_thread.start()

    def stop_polling(self, join_timeout: float = 1.0) -> None:
        self._poll_stop.set()
        thread = self._poll_thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=join_timeout)
        self._poll_thread = None

    def is_ok(self) -> bool:
        return self._initialized and self._effector is not None

    def _get_cached_finger_position(self) -> Optional[FingerPosition]:
        with self._cache_lock:
            return self._cached_finger_position

    def _update_cache(self, finger_pos: FingerPosition) -> None:
        with self._cache_lock:
            self._cached_finger_position = finger_pos

    def _positions_to_finger_position(self, positions: List[int]) -> FingerPosition:
        return FingerPosition(
            thumb_tip=positions[0],
            thumb_base=positions[1],
            index_finger=positions[2],
            middle_finger=positions[3],
            ring_finger=positions[4],
            pinky_finger=positions[5],
        )

    def _io_loop(self) -> None:
        next_read = time.monotonic()
        next_send = time.monotonic()
        while not self._poll_stop.is_set():
            now = time.monotonic()
            if self._joint_control_enabled:
                wait_s = min(next_read, next_send) - now
            else:
                wait_s = next_read - now
            if wait_s > 0 and self._poll_stop.wait(timeout=wait_s):
                break
            now = time.monotonic()
            if now >= next_read:
                next_read = now + self._poll_interval_s
                self._try_read()
            if self._joint_control_enabled and now >= next_send:
                next_send = now + self._send_interval_s
                self._try_send()

    def _try_read(self) -> None:
        if self._joint_control_enabled:
            with self._arbiter.read_session(try_only=True) as acquired:
                if not acquired:
                    return
                self._read_finger_positions_sync(update_cache=True, bus_held=True)
            return
        with self._arbiter.read_session() as acquired:
            if not acquired:
                return
            self._read_finger_positions_sync(update_cache=True, bus_held=True)

    def _should_skip_send(self, target: List[int]) -> bool:
        with self._state_lock:
            if (
                self._last_sent_positions is not None
                and target == self._last_sent_positions
            ):
                return True
        cached = self._get_cached_finger_position()
        if cached is not None:
            current = [getattr(cached, name) for name in self.FINGER_NAMES]
            if all(abs(c - t) <= self._position_tolerance for c, t in zip(current, target)):
                with self._state_lock:
                    self._last_sent_positions = list(target)
                return True
        return False

    def _try_send(self) -> None:
        with self._state_lock:
            target = self._target_positions
        if target is None:
            return
        if self._should_skip_send(target):
            return
        with self._arbiter.write_session():
            self._send_positions_sync(target, bus_held=True)
        with self._state_lock:
            self._last_sent_positions = list(target)

    def _read_finger_positions_sync(
        self,
        *,
        update_cache: bool = True,
        bus_held: bool = False,
    ) -> Optional[FingerPosition]:
        if not self._initialized or self._effector is None:
            return None
        if not bus_held:
            with self._arbiter.read_session() as acquired:
                if not acquired:
                    return None
                return self._do_read_finger_positions(update_cache=update_cache)
        return self._do_read_finger_positions(update_cache=update_cache)

    def _do_read_finger_positions(self, *, update_cache: bool) -> Optional[FingerPosition]:
        positions = self._effector.get_finger_positions()
        if positions is None or len(positions) < 6:
            return None
        finger_pos = self._positions_to_finger_position(list(positions[:6]))
        if update_cache:
            self._update_cache(finger_pos)
        return finger_pos

    def _send_positions_sync(
        self,
        positions: List[int],
        *,
        bus_held: bool = False,
    ) -> None:
        if not self._initialized or self._effector is None:
            return
        durations = DEFAULT_FINGER_DURATIONS_MS
        if not bus_held:
            with self._arbiter.write_session():
                self._effector.set_finger_positions_and_durations(
                    positions, durations
                )
            return
        self._effector.set_finger_positions_and_durations(positions, durations)

    def get_finger_position(self) -> Optional[FingerPosition]:
        """Return cached finger positions; no SDK read while polling."""
        if self.is_polling:
            return self._get_cached_finger_position()
        return self._read_finger_positions_sync(update_cache=True)

    def _validate_finger_values(self, **fingers) -> Dict[str, Optional[int]]:
        result = {}
        for finger_name, value in fingers.items():
            if value is None:
                result[finger_name] = None
                continue
            if not (self.POSITION_MIN <= value <= self.POSITION_MAX):
                raise ValueError(
                    f"{finger_name} position must be in range "
                    f"[{self.POSITION_MIN}, {self.POSITION_MAX}], current value: {value}"
                )
            result[finger_name] = value
        return result

    def _fill_with_current_position(self, **fingers) -> Dict[str, int]:
        current_pos = self._get_cached_finger_position()
        if current_pos is None and self._target_positions is not None:
            current_pos = self._positions_to_finger_position(self._target_positions)
        result = {}
        for finger_name in self.FINGER_NAMES:
            value = fingers.get(finger_name)
            if value is None:
                if current_pos is not None:
                    result[finger_name] = getattr(current_pos, finger_name, 0)
                else:
                    result[finger_name] = 0
            else:
                result[finger_name] = value
        return result

    def position_ctrl(
        self,
        thumb_tip: Optional[int] = None,
        thumb_base: Optional[int] = None,
        index_finger: Optional[int] = None,
        middle_finger: Optional[int] = None,
        ring_finger: Optional[int] = None,
        pinky_finger: Optional[int] = None,
    ) -> bool:
        if not self._initialized or self._effector is None:
            return False
        self._joint_control_enabled = True

        finger_values = self._validate_finger_values(
            thumb_tip=thumb_tip,
            thumb_base=thumb_base,
            index_finger=index_finger,
            middle_finger=middle_finger,
            ring_finger=ring_finger,
            pinky_finger=pinky_finger,
        )
        filled = self._fill_with_current_position(**finger_values)
        target = [filled[name] for name in self.FINGER_NAMES]

        with self._state_lock:
            self._target_positions = target

        if not self.is_polling:
            self._send_positions_sync(target)
            with self._state_lock:
                self._last_sent_positions = list(target)
        return True

    def is_hand_left(self) -> bool:
        if self._effector is not None:
            return self._effector.hand_side == self.HAND_LEFT
        return self._hand_side == self.HAND_LEFT

    def is_hand_right(self) -> bool:
        if self._effector is not None:
            return self._effector.hand_side == self.HAND_RIGHT
        return self._hand_side == self.HAND_RIGHT
