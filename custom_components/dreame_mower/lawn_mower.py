"""Minimal Lawn Mower Entity for Dreame Mower Implementation."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.lawn_mower import (  # type: ignore[attr-defined]
    LawnMowerActivity,
    LawnMowerEntity,
    LawnMowerEntityFeature,
)

from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import DreameMowerCoordinator
from .dreame.device import MowingMode
from .entity import DreameMowerEntity
from .dreame.const import STATUS_PROPERTY, map_status_to_activity

_LOGGER = logging.getLogger(__name__)

# Basic feature support for minimal implementation
MINIMAL_SUPPORT_FEATURES = (
    LawnMowerEntityFeature.START_MOWING
    | LawnMowerEntityFeature.PAUSE
    | LawnMowerEntityFeature.DOCK
)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Dreame Mower lawn mower entity from a config entry."""
    coordinator: DreameMowerCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]

    entity = DreameMowerLawnMower(coordinator)
    async_add_entities([entity])


class DreameMowerLawnMower(DreameMowerEntity, LawnMowerEntity):
    """Minimal Dreame Mower lawn mower entity."""

    def __init__(self, coordinator: DreameMowerCoordinator) -> None:
        """Initialize the minimal lawn mower entity."""
        super().__init__(coordinator, "lawn_mower")
        
        self._attr_device_class = DOMAIN
        self._attr_supported_features = MINIMAL_SUPPORT_FEATURES
        self._attr_activity = LawnMowerActivity.DOCKED
        self._attr_icon = "mdi:robot-mower"
        self._attr_name = None  # Fix "A2 None" issue - set explicit name to None so HA uses just device name

        # Register listener for status changes
        self.coordinator.device.register_property_callback(self._on_property_change)
        
        # Initialize activity based on current device status
        self._initialize_activity()
    
    def _initialize_activity(self) -> None:
        """Initialize activity based on current device status."""
        try:
            current_status_code = self.coordinator.device_status_code
            if current_status_code is not None:
                self._attr_activity = map_status_to_activity(current_status_code)
        except Exception as ex:
            _LOGGER.exception("Error initializing activity: %s", ex)

    @property
    def available(self) -> bool:
        """Return True if the mower is available."""
        # Inherit base availability logic and add mower-specific checks
        return super().available

    @property
    def activity(self) -> LawnMowerActivity | None:
        """Return the current activity of the mower."""
        if not self.available:
            return None
        return self._attr_activity
    
    def _on_property_change(self, property_name: str, value: Any) -> None:
        """Handle property changes from the device."""
        if property_name == STATUS_PROPERTY.name:
            new_activity = map_status_to_activity(value)
            if new_activity != self._attr_activity:
                self._attr_activity = new_activity
                self.schedule_update_ha_state()

    async def async_start_mowing(self) -> None:
        """Start mowing using the device's public mowing entrypoint."""
        try:
            mode = self.coordinator.selected_mowing_mode
            start_kwargs: dict[str, Any] = {"mode": mode}
            if mode == MowingMode.EDGE:
                start_kwargs["contour_ids"] = self.coordinator.contours

            if not await self.coordinator.device.start_mowing(**start_kwargs):
                _LOGGER.error("Failed to start mowing")
        except Exception as ex:
            _LOGGER.error("Exception while starting mowing: %s", ex)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes including available zones and contours."""
        attributes: dict[str, Any] = {}
        zones = self.coordinator.zones
        contours = self.coordinator.contours
        available_maps = self.coordinator.available_maps
        current_map_id = self.coordinator.current_map_id
        task_target_map_id = self.coordinator.task_target_map_id
        if zones:
            attributes["zones"] = zones
        if contours:
            attributes["contours"] = contours
        if available_maps:
            attributes["maps"] = available_maps
        if current_map_id is not None:
            attributes["current_map_id"] = current_map_id
        if task_target_map_id is not None:
            attributes["task_target_map_id"] = task_target_map_id
        attributes["selected_mowing_mode"] = self.coordinator.selected_mowing_mode.value
        return attributes

    async def async_pause(self) -> None:
        """Pause mowing."""
        try:
            if not await self.coordinator.device.pause():
                _LOGGER.error("Failed to pause mowing")
        except Exception as ex:
            _LOGGER.error("Exception while pausing mowing: %s", ex)

    async def async_dock(self) -> None:
        """Return to dock."""
        try:
            if not await self.coordinator.device.return_to_dock():
                _LOGGER.error("Failed to dock")
        except Exception as ex:
            _LOGGER.error("Exception while docking: %s", ex)
