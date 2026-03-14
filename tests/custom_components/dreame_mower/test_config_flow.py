"""Tests for config_flow utility functions."""

import pytest
from custom_components.dreame_mower.config_flow import (
    _device_type_for_model,
    DEVICE_TYPE_MOWER,
    DEVICE_TYPE_SWBOT,
)


class TestDeviceTypeForModel:
    """Test _device_type_for_model helper."""

    def test_mower_model(self):
        assert _device_type_for_model("dreame.mower.p2255") == DEVICE_TYPE_MOWER

    def test_mova_model(self):
        assert _device_type_for_model("mova.mower.g2405a") == DEVICE_TYPE_MOWER

    def test_swbot_model(self):
        assert _device_type_for_model("dreame.swbot.g2509") == DEVICE_TYPE_SWBOT

    def test_unknown_model_defaults_to_mower(self):
        assert _device_type_for_model("some.unknown.model") == DEVICE_TYPE_MOWER
