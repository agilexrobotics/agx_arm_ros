#!/usr/bin/env python3
# -*-coding:utf8-*-
from .revo2_pro import Revo2ProWrapper


class Revo2TouchWrapper(Revo2ProWrapper):
    """Revo2 Touch wrapper extending the Revo2 Pro bridge integration."""

    EFFECTOR_OPTION_NAME = "REVO2_TOUCH"
    WRAPPER_NAME = "Revo2TouchWrapper"
    IO_THREAD_NAME = "revo2-touch-io"
