"""Tests for dreame/const.py utility functions."""

import pytest
from homeassistant.components.lawn_mower import LawnMowerActivity

from custom_components.dreame_mower.dreame.const import (
    DeviceStatus,
    map_status_to_activity,
)


class TestMapStatusToActivity:
    """Test map_status_to_activity helper."""

    def test_mowing(self):
        assert map_status_to_activity(DeviceStatus.MOWING) == LawnMowerActivity.MOWING

    def test_standby_and_paused(self):
        assert map_status_to_activity(DeviceStatus.STANDBY) == LawnMowerActivity.PAUSED
        assert map_status_to_activity(DeviceStatus.PAUSED) == LawnMowerActivity.PAUSED

    def test_error(self):
        assert map_status_to_activity(DeviceStatus.PAUSED_DUE_TO_ERRORS) == LawnMowerActivity.ERROR

    def test_returning(self):
        assert map_status_to_activity(DeviceStatus.RETURNING_TO_CHARGE) == LawnMowerActivity.RETURNING

    def test_docked_states(self):
        for status in (DeviceStatus.CHARGING, DeviceStatus.MAPPING,
                       DeviceStatus.CHARGING_COMPLETE, DeviceStatus.UPDATING):
            assert map_status_to_activity(status) == LawnMowerActivity.DOCKED

    def test_unknown_status_defaults_to_docked(self):
        assert map_status_to_activity(9999) == LawnMowerActivity.DOCKED
