"""Select entities for Dreame Mower."""

from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import DreameMowerCoordinator
from .dreame.device import MowingMode
from .entity import DreameMowerEntity

_MOWING_MODE_LABELS: dict[MowingMode, str] = {
    MowingMode.ALL_AREA: "All area",
    MowingMode.EDGE: "Edge",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Dreame Mower selects from a config entry."""
    coordinator: DreameMowerCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities(
        [
            DreameMowerMapSelect(coordinator),
            DreameMowerMowingActionSelect(coordinator),
        ]
    )


class DreameMowerMapSelect(DreameMowerEntity, SelectEntity):
    """Select entity for the active map."""

    def __init__(self, coordinator: DreameMowerCoordinator) -> None:
        """Initialize the map select entity."""
        super().__init__(coordinator, "map_select")
        self._attr_name = "Map"
        self._attr_icon = "mdi:map-marker-path"

    @property
    def options(self) -> list[str]:
        """Return the available map options."""
        return [self._option_label(map_entry) for map_entry in self.coordinator.available_maps]

    @property
    def current_option(self) -> str | None:
        """Return the currently selected map option."""
        current_map_id = self.coordinator.current_map_id
        if current_map_id is None:
            return None

        for map_entry in self.coordinator.available_maps:
            if map_entry["id"] == current_map_id:
                return self._option_label(map_entry)

        return None

    async def async_select_option(self, option: str) -> None:
        """Select the active map on the mower."""
        map_id = self._map_id_from_option(option)
        if map_id is None:
            raise ValueError(f"Unknown map option: {option}")

        if not await self.coordinator.device.set_current_map(map_id):
            raise ValueError(f"Failed to select map option: {option}")

    def _option_label(self, map_entry: dict[str, Any]) -> str:
        """Return the label shown for a map option."""
        name = map_entry.get("name") or f"Map {map_entry['id']}"
        return f"{name} (#{map_entry['id']})"

    def _map_id_from_option(self, option: str) -> int | None:
        """Resolve a select option back to its map ID."""
        for map_entry in self.coordinator.available_maps:
            if self._option_label(map_entry) == option:
                return int(map_entry["id"])
        return None


class DreameMowerMowingActionSelect(DreameMowerEntity, SelectEntity):
    """Select entity for the default start-mowing action."""

    def __init__(self, coordinator: DreameMowerCoordinator) -> None:
        """Initialize the mowing action select entity."""
        super().__init__(coordinator, "mowing_action")
        self._attr_name = "Mowing Action"
        self._attr_icon = "mdi:play-box-multiple"

    @property
    def options(self) -> list[str]:
        """Return selectable default mowing actions."""
        return [_MOWING_MODE_LABELS[mode] for mode in self.coordinator.selectable_mowing_modes]

    @property
    def current_option(self) -> str:
        """Return the selected default mowing action."""
        return _MOWING_MODE_LABELS[self.coordinator.selected_mowing_mode]

    async def async_select_option(self, option: str) -> None:
        """Update the default mowing action used by the start button."""
        for mode, label in _MOWING_MODE_LABELS.items():
            if label == option:
                await self.coordinator.async_set_selected_mowing_mode(mode)
                return

        raise ValueError(f"Unknown mowing action option: {option}")
