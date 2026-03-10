"""Tests for MissionCompletionEventHandler class."""

import pytest
from unittest.mock import Mock
from datetime import datetime

from custom_components.dreame_mower.dreame.property.mission_completion import (
    MissionCompletionEventHandler,
    MISSION_COMPLETION_EVENT_PROPERTY_NAME,
    PROGRESS_FIELD,
    DURATION_FIELD,
    AREA_FIELD,
    UNKNOWN_FIELD_7,
    START_TIMESTAMP_FIELD,
    DATA_FILE_PATH_FIELD,
    UNKNOWN_FIELD_11,
    CHARGING_EVENTS_FIELD,
    UNKNOWN_FIELD_13,  # For backward compatibility
    UNKNOWN_FIELD_14,
    UNKNOWN_FIELD_15,
    UNKNOWN_FIELD_60,
    MAP_NAME_FIELD,
)


class TestMissionCompletionEventHandler:
    """Test cases for MissionCompletionEventHandler."""

    def test_init(self):
        """Test handler initialization."""
        handler = MissionCompletionEventHandler()
        
        # All properties should be None initially
        assert handler.progress_percent is None
        assert handler.duration_minutes is None
        assert handler.area_sqm is None
        assert handler.unknown_field_7 is None
        assert handler.start_timestamp is None
        assert handler.data_file_path is None
        assert handler.unknown_field_11 is None
        assert handler.charging_events is None
        assert handler.unknown_field_13 is None  # Backward compat alias
        assert handler.unknown_field_14 is None
        assert handler.unknown_field_15 is None
        assert handler.unknown_field_60 is None
        assert handler.start_datetime is None

    def test_parse_mission_completion_event_full_data(self):
        """Test parsing a complete mission completion event with all fields."""
        handler = MissionCompletionEventHandler()
        notify_callback = Mock()
        
        # Create test data based on the Service 4:1 mission completion event format
        # Example: Mission completed - 100% progress, 127 min duration, 68.20 m² area
        test_arguments = [
            {"piid": 1, "value": 100},  # Progress percentage
            {"piid": 2, "value": 127},  # Duration in minutes
            {"piid": 3, "value": 6820},  # Area value (68.20 m² when divided by 100)
            {"piid": 7, "value": 42},  # Unknown field 7
            {"piid": 8, "value": 1725643523},  # Start timestamp (2024-09-06 20:32:03 UTC)
            {"piid": 9, "value": "/tmp/mowing_session_analysis_20240906_203203_extended.json"},  # Data file path
            {"piid": 11, "value": 1},  # Unknown field 11 (possibly success indicator)
            {"piid": 13, "value": []},  # Unknown field 13
            {"piid": 14, "value": 280},  # Unknown field 14
            {"piid": 15, "value": 2},  # Unknown field 15
            {"piid": 60, "value": 255},  # Unknown field 60
        ]
        
        # Parse the event
        result = handler._parse_mission_completion_event(test_arguments, notify_callback)
        
        # Verify parsing success
        assert result is True
        
        # Verify parsed values
        assert handler.progress_percent == 100
        assert handler.duration_minutes == 127
        assert handler.area_sqm == 68.20  # 6820 / 100 = 68.20 m²
        assert handler.unknown_field_7 == 42
        assert handler.start_timestamp == 1725643523
        assert handler.data_file_path == "/tmp/mowing_session_analysis_20240906_203203_extended.json"
        assert handler.unknown_field_11 == 1
        assert handler.charging_events == []
        assert handler.unknown_field_13 == []  # Backward compat alias
        assert handler.unknown_field_14 == 280
        assert handler.unknown_field_15 == 2
        assert handler.unknown_field_60 == 255
        
        # Verify datetime conversion
        assert handler.start_datetime is not None
        assert handler.start_datetime.year == 2024
        assert handler.start_datetime.month == 9
        assert handler.start_datetime.day == 6

        # Verify helper properties
        assert handler.has_data_file is True
        assert handler.is_complete is True
        
        # Verify callback was called with main event data
        notify_callback.assert_any_call(MISSION_COMPLETION_EVENT_PROPERTY_NAME, {
            PROGRESS_FIELD: 100,
            DURATION_FIELD: 127,
            AREA_FIELD: 68.20,
            UNKNOWN_FIELD_7: 42,
            START_TIMESTAMP_FIELD: 1725643523,
            DATA_FILE_PATH_FIELD: "/tmp/mowing_session_analysis_20240906_203203_extended.json",
            UNKNOWN_FIELD_11: 1,
            CHARGING_EVENTS_FIELD: [],
            UNKNOWN_FIELD_14: 280,
            UNKNOWN_FIELD_15: 2,
            UNKNOWN_FIELD_60: 255,
            MAP_NAME_FIELD: None,
        })
        
        # Verify individual field notifications for backward compatibility
        notify_callback.assert_any_call("mission_progress_percent", 100)
        notify_callback.assert_any_call("mission_duration_minutes", 127)
        notify_callback.assert_any_call("mission_area_sqm", 68.20)
        notify_callback.assert_any_call("mission_data_file_path", "/tmp/mowing_session_analysis_20240906_203203_extended.json")
        notify_callback.assert_any_call("mission_start_timestamp", 1725643523)

    def test_parse_mission_completion_event_partial_data(self):
        """Test parsing mission completion event with only some fields."""
        handler = MissionCompletionEventHandler()
        notify_callback = Mock()
        
        # Create test data with only progress and duration
        test_arguments = [
            {"piid": 1, "value": 85},  # Progress percentage
            {"piid": 2, "value": 95},  # Duration in minutes
        ]
        
        # Parse the event
        result = handler._parse_mission_completion_event(test_arguments, notify_callback)
        
        # Verify parsing success
        assert result is True
        
        # Verify parsed values
        assert handler.progress_percent == 85
        assert handler.duration_minutes == 95
        assert handler.area_sqm is None  # Not provided
        assert handler.start_timestamp is None  # Not provided
        assert handler.data_file_path is None  # Not provided
        
        # Verify helper properties
        assert handler.has_data_file is False
        assert handler.is_complete is False  # Not 100%
        
        # Verify callback was called
        notify_callback.assert_any_call(MISSION_COMPLETION_EVENT_PROPERTY_NAME, {
            PROGRESS_FIELD: 85,
            DURATION_FIELD: 95,
            AREA_FIELD: None,
            UNKNOWN_FIELD_7: None,
            START_TIMESTAMP_FIELD: None,
            DATA_FILE_PATH_FIELD: None,
            UNKNOWN_FIELD_11: None,
            CHARGING_EVENTS_FIELD: None,
            UNKNOWN_FIELD_14: None,
            UNKNOWN_FIELD_15: None,
            UNKNOWN_FIELD_60: None,
            MAP_NAME_FIELD: None,
        })

    def test_parse_mission_completion_event_with_extreme_timestamp(self):
        """Test parsing with extreme timestamp value (edge case) should fail."""
        handler = MissionCompletionEventHandler()
        notify_callback = Mock()
        
        test_arguments = [
            {"piid": 1, "value": 100},
            {"piid": 8, "value": 253402300800},  # Very large timestamp (year 9999+)
        ]
        
        result = handler._parse_mission_completion_event(test_arguments, notify_callback)
        
        # Should fail when timestamp conversion fails
        assert result is False

    def test_parse_mission_completion_event_unknown_piid(self):
        """Test parsing with unknown piid values should fail."""
        handler = MissionCompletionEventHandler()
        notify_callback = Mock()
        
        test_arguments = [
            {"piid": 1, "value": 100},
            {"piid": 999, "value": "unknown_field"},  # Unknown piid
        ]
        
        result = handler._parse_mission_completion_event(test_arguments, notify_callback)
        
        # Should fail when encountering unknown piid
        assert result is False

    def test_parse_mission_completion_event_invalid_arguments(self):
        """Test parsing with malformed arguments should fail."""
        handler = MissionCompletionEventHandler()
        notify_callback = Mock()
        
        # Missing required fields in arguments
        test_arguments = [
            {"piid": 1},  # Missing value - should cause KeyError
            {"piid": 2, "value": 50},  # Valid entry but won't be reached
        ]
        
        result = handler._parse_mission_completion_event(test_arguments, notify_callback)
        
        # Should fail due to missing 'value' key in first argument
        assert result is False
        assert handler.progress_percent is None
        assert handler.duration_minutes is None

    def test_parse_mission_completion_event_missing_piid(self):
        """Test parsing with missing piid should fail."""
        handler = MissionCompletionEventHandler()
        notify_callback = Mock()
        
        test_arguments = [
            {"value": 100},  # Missing piid - should cause KeyError
        ]
        
        result = handler._parse_mission_completion_event(test_arguments, notify_callback)
        
        # Should fail due to missing 'piid' key
        assert result is False
        assert handler.progress_percent is None

    def test_handle_event_correct_service_event(self):
        """Test handle_event with correct Service 4:1 event."""
        handler = MissionCompletionEventHandler()
        notify_callback = Mock()
        
        test_arguments = [
            {"piid": 1, "value": 100},
            {"piid": 2, "value": 60},
        ]
        
        # Should handle Service 4, Event 1
        result = handler.handle_event(4, 1, test_arguments, notify_callback)
        
        assert result is True
        assert handler.progress_percent == 100
        assert handler.duration_minutes == 60

    def test_handle_event_wrong_service_event(self):
        """Test handle_event with wrong service/event ID."""
        handler = MissionCompletionEventHandler()
        notify_callback = Mock()
        
        test_arguments = [
            {"piid": 1, "value": 100},
        ]
        
        # Should not handle Service 2, Event 1 (wrong service)
        result = handler.handle_event(2, 1, test_arguments, notify_callback)
        
        assert result is False
        assert handler.progress_percent is None  # Should not be set

    def test_area_conversion_precision(self):
        """Test area conversion (divide by 100 to get m²) with various values."""
        handler = MissionCompletionEventHandler()
        notify_callback = Mock()
        
        test_cases = [
            (100, 1.0),      # 100 / 100 = 1.0 m²
            (6820, 68.20),   # 6820 / 100 = 68.20 m² (your example)
            (5000, 50.0),    # 5000 / 100 = 50.0 m²
            (1, 0.01),       # 1 / 100 = 0.01 m²
        ]
        
        for area_value, expected_m_squared in test_cases:
            handler._reset_values()
            
            test_arguments = [{"piid": 3, "value": area_value}]
            handler._parse_mission_completion_event(test_arguments, notify_callback)
            
            assert handler.area_sqm == expected_m_squared

    def test_reset_values(self):
        """Test that _reset_values clears all stored data."""
        handler = MissionCompletionEventHandler()
        
        # Set some values
        handler._progress_percent = 100
        handler._duration_minutes = 60
        handler._area_sqm = 100.0
        handler._start_datetime = datetime.now()
        
        # Reset
        handler._reset_values()
        
        # Verify all values are None
        assert handler.progress_percent is None
        assert handler.duration_minutes is None
        assert handler.area_sqm is None
        assert handler.start_datetime is None

    def test_properties_return_correct_values(self):
        """Test that all property accessors return correct values."""
        handler = MissionCompletionEventHandler()
        
        # Set test values directly
        handler._progress_percent = 95
        handler._duration_minutes = 120
        handler._area_sqm = 500.25
        handler._unknown_field_7 = 42
        handler._start_timestamp = 1725643523
        handler._data_file_path = "/tmp/test.json"
        handler._unknown_field_11 = 1
        handler._charging_events = []
        handler._unknown_field_14 = 280
        handler._unknown_field_15 = 2
        handler._unknown_field_60 = 255
        handler._start_datetime = datetime(2024, 9, 6, 20, 32, 3)
        
        # Test all property accessors
        assert handler.progress_percent == 95
        assert handler.duration_minutes == 120
        assert handler.area_sqm == 500.25
        assert handler.unknown_field_7 == 42
        assert handler.start_timestamp == 1725643523
        assert handler.data_file_path == "/tmp/test.json"
        assert handler.unknown_field_11 == 1
        assert handler.charging_events == []
        assert handler.unknown_field_13 == []  # Backward compat alias
        assert handler.unknown_field_14 == 280
        assert handler.unknown_field_15 == 2
        assert handler.unknown_field_60 == 255
        assert handler.start_datetime == datetime(2024, 9, 6, 20, 32, 3)
        assert handler.has_data_file is True
        assert handler.is_complete is False  # 95% not 100%

    def test_edge_case_empty_arguments(self):
        """Test parsing with empty arguments list."""
        handler = MissionCompletionEventHandler()
        notify_callback = Mock()
        
        result = handler._parse_mission_completion_event([], notify_callback)
        
        # Should succeed but not set any values
        assert result is True
        assert handler.progress_percent is None
        
        # Should still call main notification with all None values
        notify_callback.assert_called_with(MISSION_COMPLETION_EVENT_PROPERTY_NAME, {
            PROGRESS_FIELD: None,
            DURATION_FIELD: None,
            AREA_FIELD: None,
            UNKNOWN_FIELD_7: None,
            START_TIMESTAMP_FIELD: None,
            DATA_FILE_PATH_FIELD: None,
            UNKNOWN_FIELD_11: None,
            CHARGING_EVENTS_FIELD: None,
            UNKNOWN_FIELD_14: None,
            UNKNOWN_FIELD_15: None,
            UNKNOWN_FIELD_60: None,
            MAP_NAME_FIELD: None,
        })

    def test_data_file_path_variations(self):
        """Test various data file path formats."""
        handler = MissionCompletionEventHandler()
        notify_callback = Mock()
        
        test_paths = [
            "/tmp/mowing_session_analysis_20240906_203203.json",
            "/tmp/mowing_session_analysis_20240906_203203_extended.json",
            "session_data.json",
            "",  # Empty string
        ]
        
        for path in test_paths:
            handler._reset_values()
            test_arguments = [{"piid": 9, "value": path}]
            handler._parse_mission_completion_event(test_arguments, notify_callback)
            
            assert handler.data_file_path == path
            assert handler.has_data_file == (path != "")

    def test_parse_mission_completion_event_oct1_2025_data(self):
        """Test parsing mission completion event from October 1, 2025 with specific field values."""
        handler = MissionCompletionEventHandler()
        notify_callback = Mock()
        
        # Test data from real October 1, 2025 event
        test_arguments = [
            {"piid": 1, "value": 100},  # Progress percentage (complete)
            {"piid": 2, "value": 183},  # Duration in minutes (3h 3min)
            {"piid": 3, "value": 25339},  # Area value (253.39 m² when divided by 100)
            {"piid": 7, "value": 1},  # Unknown field 7
            {"piid": 8, "value": 1759314580},  # Start timestamp (2025-10-01)
            {"piid": 9, "value": "ali_dreame/2025/10/01/Nxxxxxx4/-1xxxxxxx8_162243699.0430.json"},  # Data file path
            {"piid": 11, "value": 0},  # Unknown field 11
            {"piid": 60, "value": -1},  # Unknown field 60
            {"piid": 13, "value": [[1759318403, 24], [1759328060, 24]]},  # Unknown field 13 - array data
            {"piid": 14, "value": 270},  # Unknown field 14
            {"piid": 15, "value": -1},  # Unknown field 15
        ]
        
        # Parse the event
        result = handler._parse_mission_completion_event(test_arguments, notify_callback)
        
        # Verify parsing success
        assert result is True
        
        # Verify parsed values
        assert handler.progress_percent == 100
        assert handler.duration_minutes == 183
        assert handler.area_sqm == 253.39  # 25339 / 100 = 253.39 m²
        assert handler.unknown_field_7 == 1
        assert handler.start_timestamp == 1759314580
        assert handler.data_file_path == "ali_dreame/2025/10/01/Nxxxxxx4/-1xxxxxxx8_162243699.0430.json"
        assert handler.unknown_field_11 == 0
        assert handler.charging_events == [[1759318403, 24], [1759328060, 24]]
        assert handler.unknown_field_13 == [[1759318403, 24], [1759328060, 24]]  # Backward compat
        assert handler.unknown_field_14 == 270
        assert handler.unknown_field_15 == -1
        assert handler.unknown_field_60 == -1
        
        # Verify datetime conversion for 2025 timestamp
        assert handler.start_datetime is not None
        assert handler.start_datetime.year == 2025
        assert handler.start_datetime.month == 10
        assert handler.start_datetime.day == 1
        
        # Verify helper properties
        assert handler.has_data_file is True
        assert handler.is_complete is True
        
        # Verify callback was called with main event data
        notify_callback.assert_any_call(MISSION_COMPLETION_EVENT_PROPERTY_NAME, {
            PROGRESS_FIELD: 100,
            DURATION_FIELD: 183,
            AREA_FIELD: 253.39,
            UNKNOWN_FIELD_7: 1,
            START_TIMESTAMP_FIELD: 1759314580,
            DATA_FILE_PATH_FIELD: "ali_dreame/2025/10/01/Nxxxxxx4/-1xxxxxxx8_162243699.0430.json",
            UNKNOWN_FIELD_11: 0,
            CHARGING_EVENTS_FIELD: [[1759318403, 24], [1759328060, 24]],
            UNKNOWN_FIELD_14: 270,
            UNKNOWN_FIELD_15: -1,
            UNKNOWN_FIELD_60: -1,
            MAP_NAME_FIELD: None,
        })
        
        # Verify individual field notifications for backward compatibility
        notify_callback.assert_any_call("mission_progress_percent", 100)
        notify_callback.assert_any_call("mission_duration_minutes", 183)
        notify_callback.assert_any_call("mission_area_sqm", 253.39)
        notify_callback.assert_any_call("mission_data_file_path", "ali_dreame/2025/10/01/Nxxxxxx4/-1xxxxxxx8_162243699.0430.json")
        notify_callback.assert_any_call("mission_start_timestamp", 1759314580)

    def test_charging_events_helper_methods(self):
        """Test helper methods for parsing and analyzing charging events."""
        handler = MissionCompletionEventHandler()
        notify_callback = Mock()
        
        # Test data from October 1, 2025 event with 2 charging sessions
        test_arguments = [
            {"piid": 1, "value": 100},
            {"piid": 2, "value": 183},
            {"piid": 8, "value": 1759314580},  # Mission start: 12:29:40
            {"piid": 13, "value": [[1759318403, 24], [1759328060, 24]]},  # Two 24-min charging events
        ]
        
        handler._parse_mission_completion_event(test_arguments, notify_callback)
        
        # Test charging_event_count
        assert handler.charging_event_count == 2
        
        # Test total_charging_time_minutes
        assert handler.total_charging_time_minutes == 48  # 24 + 24
        
        # Test get_charging_events_with_datetime
        events_with_dt = handler.get_charging_events_with_datetime()
        assert events_with_dt is not None
        assert len(events_with_dt) == 2
        
        # Verify first charging event
        first_event = events_with_dt[0]
        assert first_event["timestamp"] == 1759318403
        assert first_event["duration_minutes"] == 24
        assert first_event["offset_from_start_minutes"] == (1759318403 - 1759314580) // 60  # ~63 minutes
        assert first_event["datetime"].year == 2025
        assert first_event["datetime"].month == 10
        assert first_event["datetime"].day == 1
        
        # Verify second charging event
        second_event = events_with_dt[1]
        assert second_event["timestamp"] == 1759328060
        assert second_event["duration_minutes"] == 24
        assert second_event["offset_from_start_minutes"] == (1759328060 - 1759314580) // 60  # ~224 minutes
        assert second_event["datetime"].year == 2025
        
    def test_charging_events_no_data(self):
        """Test charging event helpers with no charging events."""
        handler = MissionCompletionEventHandler()
        
        # No charging events
        assert handler.charging_event_count == 0
        assert handler.total_charging_time_minutes == 0
        assert handler.get_charging_events_with_datetime() is None
        
        # Empty charging events list
        handler._charging_events = []
        assert handler.charging_event_count == 0
        assert handler.total_charging_time_minutes == 0
        
        # Charging events but no start timestamp
        handler._charging_events = [[1759318403, 24]]
        handler._start_timestamp = None
        assert handler.charging_event_count == 1
        assert handler.total_charging_time_minutes == 24
        assert handler.get_charging_events_with_datetime() is None  # No start timestamp
        
    def test_charging_events_malformed_data(self):
        """Test charging event helpers with malformed data."""
        handler = MissionCompletionEventHandler()
        
        # Malformed events (missing duration)
        handler._charging_events = [[1759318403], [1759328060, 24]]
        assert handler.charging_event_count == 2
        assert handler.total_charging_time_minutes == 24  # Only second event counts
        
        # With start timestamp
        handler._start_timestamp = 1759314580
        events_with_dt = handler.get_charging_events_with_datetime()
        assert events_with_dt is not None
        assert len(events_with_dt) == 1  # Only valid event included

    def test_parse_mission_completion_event_with_map_name(self):
        """Test parsing mission completion event with piid 16 (map_name) — as seen in issue #31."""
        handler = MissionCompletionEventHandler()
        notify_callback = Mock()

        # Real-world data from issue #31 (mova.mower.g2529b firmware 4.3.6_0169)
        test_arguments = [
            {"piid": 1, "value": 102},   # Progress percent
            {"piid": 2, "value": 23},    # Duration minutes
            {"piid": 3, "value": 774},   # Area (7.74 m²)
            {"piid": 7, "value": 2},
            {"piid": 8, "value": 1772956800},  # Start timestamp
            {"piid": 9, "value": "ali_dreame/2026/03/08/HJxxxxxx4/-1xxxxxxx4_082338835.0169.json"},
            {"piid": 11, "value": 1},
            {"piid": 60, "value": 224},
            {"piid": 13, "value": []},
            {"piid": 14, "value": 107},
            {"piid": 15, "value": 0},
            {"piid": 16, "value": "map1"},  # New field: map name/identifier
        ]

        result = handler._parse_mission_completion_event(test_arguments, notify_callback)

        assert result is True
        assert handler.progress_percent == 102
        assert handler.duration_minutes == 23
        assert handler.area_sqm == 7.74
        assert handler.data_file_path == "ali_dreame/2026/03/08/HJxxxxxx4/-1xxxxxxx4_082338835.0169.json"
        assert handler.map_name == "map1"

        notify_callback.assert_any_call(MISSION_COMPLETION_EVENT_PROPERTY_NAME, {
            PROGRESS_FIELD: 102,
            DURATION_FIELD: 23,
            AREA_FIELD: 7.74,
            UNKNOWN_FIELD_7: 2,
            START_TIMESTAMP_FIELD: 1772956800,
            DATA_FILE_PATH_FIELD: "ali_dreame/2026/03/08/HJxxxxxx4/-1xxxxxxx4_082338835.0169.json",
            UNKNOWN_FIELD_11: 1,
            CHARGING_EVENTS_FIELD: [],
            UNKNOWN_FIELD_14: 107,
            UNKNOWN_FIELD_15: 0,
            UNKNOWN_FIELD_60: 224,
            MAP_NAME_FIELD: "map1",
        })