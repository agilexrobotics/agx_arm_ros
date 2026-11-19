"""Motor-status freshness checks without constructing a ROS node or connecting hardware."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from builtin_interfaces.msg import Time
from diagnostic_msgs.msg import DiagnosticStatus


_source = Path(__file__).resolve().parents[1] / "agx_arm_ctrl" / "agx_arm_ctrl_single_node.py"
_spec = importlib.util.spec_from_file_location("agx_arm_motor_status_test_module", _source)
driver = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(driver)


def make_driver_state(timestamp):
    foc_status = SimpleNamespace(
        driver_enable_status=True, voltage_too_low=False, motor_overheating=False,
        driver_overcurrent=False, driver_overheating=False, collision_status=False,
        driver_error_status=False, stall_status=False,
    )
    return SimpleNamespace(
        timestamp=timestamp,
        msg=SimpleNamespace(
            foc_status=foc_status, vol=48.0, foc_temp=35, motor_temp=40,
            bus_current=1.2, foc_status_code=64,
        ),
    )


def test_frame_cached_during_publish_is_fresh(monkeypatch):
    clock = [10.0]
    monkeypatch.setattr(driver.time, "time", lambda: clock[0])

    def receive_then_read(joint_index):
        clock[0] += 1e-6
        return make_driver_state(clock[0])

    node = Mock()
    node.get_clock.return_value.now.return_value.to_msg.return_value = Time()
    node.arm_joint_names = ["joint1", "joint2"]
    node.can_port = "can0"
    node._STATUS_TIMEOUT_S = 2.0
    node.agx_arm.get_driver_states.side_effect = receive_then_read
    node.agx_arm.is_ok.return_value = False
    driver.AgxArmRosNode._publish_status(node)
    statuses = node.motor_status_pub.publish.call_args.args[0].status
    assert [status.level for status in statuses] == [DiagnosticStatus.OK] * 2


def test_disable_clears_enable_wish_even_if_unconfirmed(monkeypatch):
    monkeypatch.setattr(driver.time, "sleep", lambda s: None)
    node = Mock()
    node.enable_flag = True
    node.agx_arm.disable.return_value = True
    node.agx_arm.get_joint_enable_status.return_value = True
    assert driver.AgxArmRosNode._enable_arm(node, False, timeout=0.1)
    assert node.enable_flag is False
