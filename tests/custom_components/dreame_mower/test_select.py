"""Tests for Dreame Mower select entities."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.dreame_mower.dreame.device import MowingMode
from custom_components.dreame_mower.select import (
    DreameMowerMapSelect,
    DreameMowerMowingActionSelect,
)


def _make_coordinator():
    coordinator = MagicMock()
    coordinator.device_mac = "AA:BB:CC:DD:EE:FF"
    coordinator.device_name = "Test Mower"
    coordinator.device_model = "dreame.mower.test"
    coordinator.device_serial = "SN123"
    coordinator.device_manufacturer = "Dreametech™"
    coordinator.device_firmware = "1.0.0"
    coordinator.device_connected = True
    coordinator.device = MagicMock()
    coordinator.device.set_current_map = AsyncMock(return_value=True)
    coordinator.available_maps = [
        {"id": 1, "index": 0, "name": "Front", "area": 25.0},
        {"id": 2, "index": 1, "name": "Back", "area": 30.5},
    ]
    coordinator.current_map_id = 2
    coordinator.contours = [[1, 0], [2, 0]]
    coordinator.selected_mowing_mode = MowingMode.ALL_AREA
    coordinator.selectable_mowing_modes = [MowingMode.ALL_AREA, MowingMode.EDGE]
    coordinator.async_set_selected_mowing_mode = AsyncMock()
    return coordinator


def _make_map_select(coordinator=None):
    entity = DreameMowerMapSelect.__new__(DreameMowerMapSelect)
    entity.coordinator = coordinator or _make_coordinator()
    entity._entity_description_key = "map_select"
    entity._attr_has_entity_name = True
    entity.hass = MagicMock()
    return entity


def _make_mowing_action_select(coordinator=None):
    entity = DreameMowerMowingActionSelect.__new__(DreameMowerMowingActionSelect)
    entity.coordinator = coordinator or _make_coordinator()
    entity._entity_description_key = "mowing_action"
    entity._attr_has_entity_name = True
    entity.hass = MagicMock()
    return entity


def test_map_select_options_and_current_option():
    entity = _make_map_select()

    assert entity.options == ["Front (#1)", "Back (#2)"]
    assert entity.current_option == "Back (#2)"


@pytest.mark.asyncio
async def test_map_select_calls_device_set_current_map():
    coordinator = _make_coordinator()
    entity = _make_map_select(coordinator)

    await entity.async_select_option("Front (#1)")

    coordinator.device.set_current_map.assert_awaited_once_with(1)


def test_mowing_action_select_options_and_current_option():
    entity = _make_mowing_action_select()

    assert entity.options == ["All area", "Edge"]
    assert entity.current_option == "All area"


@pytest.mark.asyncio
async def test_mowing_action_select_updates_coordinator_mode():
    coordinator = _make_coordinator()
    entity = _make_mowing_action_select(coordinator)

    await entity.async_select_option("Edge")

    coordinator.async_set_selected_mowing_mode.assert_awaited_once_with(MowingMode.EDGE)
