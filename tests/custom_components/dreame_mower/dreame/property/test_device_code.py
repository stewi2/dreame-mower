"""Tests for DeviceCodeHandler and device code registry functionality."""

import pytest

from custom_components.dreame_mower.dreame.property.device_code import (
    DeviceCodeHandler,
    DeviceCodeDefinition,
    DeviceCodeRegistry,
    DeviceCodeType,
    BASE_DEVICE_CODES,
    MOVA_DEVICE_CODES,
    get_device_code_registry,
    NOTIFICATION_CODE_FIELD,
    NOTIFICATION_NAME_FIELD,
    NOTIFICATION_DESCRIPTION_FIELD,
    NOTIFICATION_TIMESTAMP_FIELD,
)


class TestDeviceCodeDefinition:
    """Test cases for DeviceCodeDefinition."""

    def test_init(self):
        """Test device code definition initialization."""
        definition = DeviceCodeDefinition(
            code=28,
            name="BLADES_SEVERELY_WORN",
            description="Blades are severely worn. Replace them soon.",
            code_type=DeviceCodeType.WARNING
        )
        
        assert definition.code == 28
        assert definition.name == "BLADES_SEVERELY_WORN"
        assert definition.description == "Blades are severely worn. Replace them soon."
        assert definition.code_type == DeviceCodeType.WARNING

    @pytest.mark.parametrize("code_type,expected_error,expected_warning,expected_info", [
        (DeviceCodeType.ERROR, True, False, False),
        (DeviceCodeType.WARNING, False, True, False),
        (DeviceCodeType.INFO, False, False, True),
    ])
    def test_type_checking_methods(self, code_type, expected_error, expected_warning, expected_info):
        """Test type checking methods for all code types."""
        definition = DeviceCodeDefinition(1, "TEST", "Test", code_type)
        
        assert definition.is_error() == expected_error
        assert definition.is_warning() == expected_warning
        assert definition.is_info() == expected_info


class TestDeviceCodeRegistry:
    """Test cases for DeviceCodeRegistry."""

    def test_init(self):
        """Test registry initialization."""
        test_codes = {
            0: DeviceCodeDefinition(0, "TEST", "Test", DeviceCodeType.INFO)
        }
        registry = DeviceCodeRegistry(test_codes)
        
        assert registry.get_code(0) is not None
        assert registry.get_name(0) == "TEST"

    def test_get_code(self):
        """Test getting device code definition."""
        registry = DeviceCodeRegistry(BASE_DEVICE_CODES)
        
        # Test existing code
        definition = registry.get_code(28)
        assert definition is not None
        assert definition.name == "BLADES_SEVERELY_WORN"
        assert definition.description == "Blades are severely worn. Replace them soon."
        assert definition.code_type == DeviceCodeType.WARNING
        
        # Test non-existing code
        assert registry.get_code(999) is None

    def test_get_name_and_description(self):
        """Test getting name and description with fallbacks."""
        registry = DeviceCodeRegistry(BASE_DEVICE_CODES)
        
        # Test existing code
        assert registry.get_name(28) == "BLADES_SEVERELY_WORN"
        assert registry.get_description(28) == "Blades are severely worn. Replace them soon."
        
        # Test unknown code fallbacks
        assert registry.get_name(999) == "Unknown Code 999"
        assert registry.get_description(999) == "Unknown device code: 999"

    @pytest.mark.parametrize("code,expected_error,expected_warning,expected_info", [
        (2, True, False, False),    # MOWER_GOT_STUCK (error)
        (28, False, True, False),   # BLADES_SEVERELY_WORN (warning)
        (48, False, False, True),   # MOWING_COMPLETED (info)
        (999, False, False, False), # Unknown code
    ])
    def test_type_checking_methods(self, code, expected_error, expected_warning, expected_info):
        """Test registry type checking methods."""
        registry = DeviceCodeRegistry(BASE_DEVICE_CODES)
        
        assert registry.is_error(code) == expected_error
        assert registry.is_warning(code) == expected_warning
        assert registry.is_info(code) == expected_info

    def test_extend(self):
        """Test registry extension functionality."""
        base_codes = {
            1: DeviceCodeDefinition(1, "BASE", "Base", DeviceCodeType.INFO)
        }
        additional_codes = {
            2: DeviceCodeDefinition(2, "ADDITIONAL", "Additional", DeviceCodeType.ERROR)
        }
        
        base_registry = DeviceCodeRegistry(base_codes)
        extended_registry = base_registry.extend(additional_codes)
        
        # Original registry should be unchanged
        assert base_registry.get_code(2) is None
        
        # Extended registry should have both codes
        assert extended_registry.get_code(1) is not None
        assert extended_registry.get_code(2) is not None
        assert extended_registry.get_name(2) == "ADDITIONAL"

    def test_get_mapping(self):
        """Test getting code-to-name mapping."""
        test_codes = {
            1: DeviceCodeDefinition(1, "CODE_ONE", "First", DeviceCodeType.INFO),
            2: DeviceCodeDefinition(2, "CODE_TWO", "Second", DeviceCodeType.ERROR)
        }
        registry = DeviceCodeRegistry(test_codes)
        
        mapping = registry.get_mapping()
        assert mapping == {1: "CODE_ONE", 2: "CODE_TWO"}


class TestDeviceCodeHandler:
    """Test cases for DeviceCodeHandler."""

    def test_init(self):
        """Test handler initialization."""
        handler = DeviceCodeHandler()
        
        # All properties should be None initially
        assert handler.device_code is None
        assert handler.device_code_name is None
        assert handler.device_code_description is None
        assert handler.device_code_is_error is None
        assert handler.device_code_is_warning is None

    @pytest.mark.parametrize("input_value,expected_success,expected_code,expected_name,expected_error,expected_warning", [
        (28, True, 28, "BLADES_SEVERELY_WORN", False, True),  # Valid known code
        ("28", True, 28, "BLADES_SEVERELY_WORN", False, True), # String number
        (999, True, 999, "Unknown Code 999", False, False),    # Unknown code
        ("invalid", False, None, None, None, None),           # Invalid type
    ])
    def test_parse_value(self, input_value, expected_success, expected_code, expected_name, expected_error, expected_warning):
        """Test parsing various device code values."""
        handler = DeviceCodeHandler()
        
        result = handler.parse_value(input_value)
        
        assert result == expected_success
        assert handler.device_code == expected_code
        assert handler.device_code_name == expected_name
        assert handler.device_code_is_error == expected_error
        assert handler.device_code_is_warning == expected_warning

    def test_get_notification_data(self):
        """Test getting notification data."""
        handler = DeviceCodeHandler()
        handler.parse_value(28)
        
        notification_data = handler.get_notification_data()
        
        assert NOTIFICATION_CODE_FIELD in notification_data
        assert NOTIFICATION_NAME_FIELD in notification_data
        assert NOTIFICATION_DESCRIPTION_FIELD in notification_data
        assert NOTIFICATION_TIMESTAMP_FIELD in notification_data
        
        assert notification_data[NOTIFICATION_CODE_FIELD] == 28
        assert notification_data[NOTIFICATION_NAME_FIELD] == "BLADES_SEVERELY_WORN"
        assert notification_data[NOTIFICATION_DESCRIPTION_FIELD] == "Blades are severely worn. Replace them soon."

    def test_set_model(self):
        """Test changing device model."""
        handler = DeviceCodeHandler()
        
        # Start with base model
        handler.parse_value(0)
        assert handler.device_code_name == "NO_DEVICE_CODE"
        
        # Switch to MOVA model (which overrides code 0)
        handler.set_model("mova.mower.g2405b")
        handler.parse_value(0)
        assert handler.device_code_name == "ROBOT_LIFTED"


class TestDeviceCodeRegistries:
    """Test cases for model-specific registries."""

    def test_base_device_codes_coverage(self):
        """Test that key base device codes are present."""
        assert 28 in BASE_DEVICE_CODES   # New blade wear code
        
        # Verify the new code 28
        blade_code = BASE_DEVICE_CODES[28]
        assert blade_code.name == "BLADES_SEVERELY_WORN"
        assert blade_code.code_type == DeviceCodeType.WARNING

    @pytest.mark.parametrize("model,expected_code_0_name,expected_code_28_name", [
        (None, "NO_DEVICE_CODE", "BLADES_SEVERELY_WORN"),                    # Base registry
        ("dreame.mower.p2255", "NO_DEVICE_CODE", "BLADES_SEVERELY_WORN"),     # A1 registry
        ("mova.mower.g2405b", "ROBOT_LIFTED", "BLADES_SEVERELY_WORN"),       # MOVA registry
        ("unknown.model", "NO_DEVICE_CODE", "BLADES_SEVERELY_WORN"),         # Unknown model
    ])
    def test_get_device_code_registry(self, model, expected_code_0_name, expected_code_28_name):
        """Test getting registries for different models."""
        registry = get_device_code_registry(model)
        
        # Code 28 should be available in all registries
        assert registry.get_name(28) == expected_code_28_name
        
        # Code 0 varies by model
        assert registry.get_name(0) == expected_code_0_name


class TestNewBladeWearCode:
    """Specific tests for the new blade wear code 28."""

    def test_blade_wear_code_properties(self):
        """Test the new blade wear code 28 properties and availability across all registries."""
        handler = DeviceCodeHandler()
        handler.parse_value(28)
        
        assert handler.device_code == 28
        assert handler.device_code_name == "BLADES_SEVERELY_WORN"
        assert handler.device_code_description == "Blades are severely worn. Replace them soon."
        assert handler.device_code_is_warning is True
        assert handler.device_code_is_error is False
        
        # Verify available in all model registries
        for model in [None, "dreame.mower.p2255", "mova.mower.g2405b"]:
            registry = get_device_code_registry(model)
            assert registry.get_name(28) == "BLADES_SEVERELY_WORN"


class TestMovaDriveWheelCodes:
    """Tests for MOVA drive wheel error codes 4 and 5."""

    @pytest.mark.parametrize("code,expected_name,expected_description", [
        (4, "LEFT_DRIVE_WHEEL_ERROR", "Left drive wheel error"),
        (5, "RIGHT_DRIVE_WHEEL_ERROR", "Right drive wheel error"),
    ])
    def test_codes_in_mova_registry(self, code, expected_name, expected_description):
        """Codes 4 and 5 should be present in MOVA_DEVICE_CODES."""
        assert code in MOVA_DEVICE_CODES
        defn = MOVA_DEVICE_CODES[code]
        assert defn.name == expected_name
        assert defn.description == expected_description
        assert defn.code_type == DeviceCodeType.ERROR
        assert defn.is_error() is True

    @pytest.mark.parametrize("model,code,expected_name", [
        ("mova.mower.g2405b", 4, "LEFT_DRIVE_WHEEL_ERROR"),
        ("mova.mower.g2405c", 4, "LEFT_DRIVE_WHEEL_ERROR"),
        ("mova.mower.g2529b", 4, "LEFT_DRIVE_WHEEL_ERROR"),
        ("mova.mower.g2405b", 5, "RIGHT_DRIVE_WHEEL_ERROR"),
        ("mova.mower.g2529b", 5, "RIGHT_DRIVE_WHEEL_ERROR"),
    ])
    def test_codes_available_for_mova_models(self, model, code, expected_name):
        """Codes 4 and 5 should resolve correctly for all MOVA models."""
        registry = get_device_code_registry(model)
        assert registry.get_name(code) == expected_name
        assert registry.is_error(code) is True

    @pytest.mark.parametrize("code", [4, 5])
    def test_codes_not_in_base_registry(self, code):
        """Codes 4 and 5 should not be in the base or A1 registry."""
        assert get_device_code_registry(None).get_code(code) is None
        assert get_device_code_registry("dreame.mower.p2255").get_code(code) is None

    @pytest.mark.parametrize("code,expected_name", [
        (4, "LEFT_DRIVE_WHEEL_ERROR"),
        (5, "RIGHT_DRIVE_WHEEL_ERROR"),
    ])
    def test_parse_value_with_mova_model(self, code, expected_name):
        """Handler with MOVA model should parse codes 4 and 5 correctly."""
        handler = DeviceCodeHandler(model="mova.mower.g2529b")
        assert handler.parse_value(code) is True
        assert handler.device_code == code
        assert handler.device_code_name == expected_name
        assert handler.device_code_is_error is True
        assert handler.device_code_is_warning is False