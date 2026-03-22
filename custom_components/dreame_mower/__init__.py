"""The Dreame Mower Implementation.

This file serves as the main entry point for the integration.
It sets up the coordinator and forwards platform setup to dedicated modules.
To add new features, simply extend the PLATFORMS tuple - each platform
will automatically route to its corresponding module (e.g., switch.py, button.py).
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DATA_COORDINATOR, DATA_PLATFORMS, DOMAIN
from .coordinator import DreameMowerCoordinator
from .config_flow import DEVICE_TYPE_SWBOT

_MOWER_PLATFORMS = (
    Platform.LAWN_MOWER,
    Platform.SENSOR,
    Platform.CAMERA,
    Platform.SELECT,
)
_SWBOT_PLATFORMS = (
    Platform.SENSOR,
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Dreame Mower from a config entry."""
    
    # Create coordinator
    coordinator = DreameMowerCoordinator(hass, entry=entry)
    
    platforms = (
        _SWBOT_PLATFORMS
        if coordinator.device_type == DEVICE_TYPE_SWBOT
        else _MOWER_PLATFORMS
    )
    
    # Connect to the device
    await coordinator.async_connect_device()
    
    # Start coordinator updates (minimal - may not do anything initially)
    await coordinator.async_config_entry_first_refresh()
    
    # Trigger initial data update to reflect current device state
    await coordinator.async_request_refresh()
    
    # Store coordinator in hass data
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        DATA_COORDINATOR: coordinator,
        DATA_PLATFORMS: platforms,
    }

    # Set up all platforms for this device/entry.
    await hass.config_entries.async_forward_entry_setups(entry, platforms)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Disconnect device before unloading
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    entry_platforms = hass.data[DOMAIN][entry.entry_id][DATA_PLATFORMS]
    await coordinator.async_disconnect_device()
    
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, entry_platforms):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)