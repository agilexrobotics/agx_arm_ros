#!/usr/bin/env python3
# -*-coding:utf8-*-
from .agx_gripper import (
    AgxGripperWrapper,
    GripperStatus,
    GripperCtrlStatus,
    GripperTeachingParam,
)

from .revo2 import (
    Revo2Wrapper,
    HandStatus,
    FingerPosition,
    FingerSpeed,
    FingerCurrent,
)

from .revo2_pro import Revo2ProWrapper
from .revo2_touch import Revo2TouchWrapper

__all__ = [
    # AgxGripper
    'AgxGripperWrapper',
    'GripperStatus',
    'GripperCtrlStatus',
    'GripperTeachingParam',
    # Revo2
    'Revo2Wrapper',
    'HandStatus',
    'FingerPosition',
    'FingerSpeed',
    'FingerCurrent',
    # Revo2 Pro
    'Revo2ProWrapper',
    # Revo2 Touch
    'Revo2TouchWrapper',
]
