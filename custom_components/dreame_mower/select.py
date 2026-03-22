"""Zone select entity for Dreame Mower Integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import DreameMowerCoordinator
from .entity import DreameMowerEntity

_LOGGER = logging.getLogger(__name__)

ALL_ZONES_OPTION = "All zones"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up zone select entity."""
    coordinator: DreameMowerCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities([DreameMowerZoneSelect(coordinator)])


class DreameMowerZoneSelect(DreameMowerEntity, SelectEntity):
    """Select entity for choosing which zone to mow."""

    def __init__(self, coordinator: DreameMowerCoordinator) -> None:
        """Initialize the zone select entity."""
        super().__init__(coordinator, "zone_select")
        self._attr_translation_key = "zone_select"
        self._attr_icon = "mdi:map-marker-radius"
        self._attr_current_option = ALL_ZONES_OPTION
        self._attr_options = [ALL_ZONES_OPTION]

        # Subscribe to vector map updates so options stay current
        coordinator.device.register_property_callback(self._on_property_change)

        # Populate from any already-loaded map
        self._rebuild_options()

    def _rebuild_options(self) -> None:
        """Rebuild option list from current vector map zones."""
        zones = self.coordinator.zones
        self._attr_options = [ALL_ZONES_OPTION] + [z["name"] for z in zones]

        # If the previously selected option no longer exists, reset to default
        if self._attr_current_option not in self._attr_options:
            self._attr_current_option = ALL_ZONES_OPTION
            self.coordinator.selected_zone_id = None

    def _on_property_change(self, property_name: str, value: Any) -> None:
        """Handle device property changes."""
        if property_name == "vector_map_updated":
            self._rebuild_options()
            if self.hass:
                self.hass.create_task(self._async_write_state())

    async def _async_write_state(self) -> None:
        try:
            self.async_write_ha_state()
        except Exception as ex:
            _LOGGER.debug("Error writing zone select state: %s", ex)

    @property
    def current_option(self) -> str:
        return self._attr_current_option or ALL_ZONES_OPTION

    @property
    def options(self) -> list[str]:
        return self._attr_options

    async def async_select_option(self, option: str) -> None:
        """Handle a zone selection by the user."""
        if option not in self._attr_options:
            _LOGGER.warning("Unknown zone option selected: %s", option)
            return

        self._attr_current_option = option

        if option == ALL_ZONES_OPTION:
            self.coordinator.selected_zone_id = None
        else:
            # TODO: Support selecting multiple zones from the UI; this select entity
            # currently persists only a single selected zone ID.
            zone = next(
                (z for z in self.coordinator.zones if z["name"] == option), None
            )
            self.coordinator.selected_zone_id = zone["id"] if zone else None

        self.async_write_ha_state()
