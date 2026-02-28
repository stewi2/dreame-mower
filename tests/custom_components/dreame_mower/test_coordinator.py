"""Test the Dreame Mower coordinator."""

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_NAME, CONF_PASSWORD, CONF_USERNAME
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dreame_mower.coordinator import DreameMowerCoordinator
from custom_components.dreame_mower.const import DOMAIN
from custom_components.dreame_mower.config_flow import CONF_ACCOUNT_TYPE, CONF_COUNTRY, CONF_DID, CONF_MAC, CONF_MODEL, CONF_SERIAL


@pytest.fixture
def minimal_config_entry():
    """Create a minimal config entry for testing."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Test Minimal Mower",
        data={
            CONF_NAME: "Test Mower",
            CONF_MAC: "11:22:33:44:55:66",
            CONF_MODEL: "dreame.mower.test789",
            CONF_SERIAL: "MIN123456",
            CONF_DID: "test_device_456",
            CONF_USERNAME: "test_user",
            CONF_PASSWORD: "test_password",
            CONF_ACCOUNT_TYPE: "dreame",
            CONF_COUNTRY: "DE",
        },
        entry_id="test_minimal_entry",
    )


async def test_coordinator_initialization(hass: HomeAssistant, minimal_config_entry):
    """Test that DreameMowerCoordinator initializes correctly with minimal config."""
    coordinator = DreameMowerCoordinator(hass, entry=minimal_config_entry)
    
    # Check that coordinator is properly initialized
    assert coordinator is not None
    assert coordinator.entry == minimal_config_entry
    assert coordinator.name == DOMAIN
    assert coordinator.update_interval is None  # No polling by default


async def test_coordinator_async_update_data(hass: HomeAssistant, minimal_config_entry):
    """Test coordinator's _async_update_data method returns expected structure."""
    coordinator = DreameMowerCoordinator(hass, entry=minimal_config_entry)
    
    # Call the update data method directly
    data = await coordinator._async_update_data()
    
    # Verify returned data structure
    assert data is not None
    assert isinstance(data, dict)
    
    # Check all required fields are present
    required_fields = ["name", "connected", "last_update", "mac", "model", "serial", "firmware", "manufacturer"]
    for field in required_fields:
        assert field in data, f"Field {field} missing from coordinator data"
    
    # Verify data values from config entry
    assert data["name"] == "Test Mower"
    assert data["mac"] == "11:22:33:44:55:66"
    assert data["model"] == "dreame.mower.test789"
    assert data["serial"] == "MIN123456"
    assert data["manufacturer"] == "Dreametech™"
    
    # Verify default/placeholder values
    assert data["connected"] is False
    assert data["last_update"] is not None  # Should have a timestamp from device initialization
    assert data["firmware"] == "Unknown"


async def test_coordinator_initial_data_fetch(hass: HomeAssistant, minimal_config_entry):
    """Test coordinator can fetch initial data without errors."""
    coordinator = DreameMowerCoordinator(hass, entry=minimal_config_entry)

    # Call _async_update_data directly to avoid the ConfigEntryState.SETUP_IN_PROGRESS
    coordinator.data = await coordinator._async_update_data()

    # Data should be available after first refresh
    assert coordinator.data is not None
    assert coordinator.data["name"] == "Test Mower"


async def test_coordinator_with_required_config_data(hass: HomeAssistant):
    """Test coordinator requires all essential config data."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Mower Required Data",
        data={
            "name": "Test Required Mower",
            CONF_MAC: "AA:BB:CC:DD:EE:FF",
            CONF_MODEL: "dreame.mower.required123",
            CONF_SERIAL: "REQ123456",
            CONF_DID: "required_device_789",
            CONF_USERNAME: "test_required_user",
            CONF_PASSWORD: "test_required_password",
            CONF_ACCOUNT_TYPE: "dreame",
            CONF_COUNTRY: "US",
        },
        entry_id="test_required_entry",
    )
    
    coordinator = DreameMowerCoordinator(hass, entry=config_entry)
    data = await coordinator._async_update_data()
    
    # Should use provided name from config
    assert data["name"] == "Test Required Mower"