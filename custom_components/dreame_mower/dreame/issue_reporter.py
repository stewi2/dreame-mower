"""Issue reporting and GitHub issue creation for Dreame Mower."""

from __future__ import annotations

import json
import logging
import urllib.parse
from collections import deque
from datetime import datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

_LOGGER = logging.getLogger(__name__)

# Maximum number of recent notifications to track
MAX_RECENT_NOTIFICATIONS = 5


class DreameMowerIssueReporter:
    """Handles issue reporting and GitHub issue creation for unhandled MQTT messages."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the error reporter."""
        self.hass = hass
        # Track recent notifications with timestamps (most recent first)
        self.recent_notifications: deque[dict[str, Any]] = deque(maxlen=MAX_RECENT_NOTIFICATIONS)

    async def _get_integration_version(self) -> str:
        """Get integration version from Home Assistant's integration registry."""
        try:
            integration = await async_get_integration(self.hass, "dreame_mower")
            return integration.version or "unknown"
        except Exception as ex:
            _LOGGER.warning("Failed to get integration version: %s", ex)
            return "unknown"

    def _track_notification(self, notification_type: str, title: str, description: str) -> None:
        """Track a notification for context in future MQTT discovery reports."""
        notification_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": notification_type,
            "title": title,
            "description": description
        }
        # Add to the front (most recent first)
        self.recent_notifications.appendleft(notification_entry)
        _LOGGER.debug("Tracked notification: %s - %s", notification_type, title)

    def _get_recent_notifications_context(self) -> str:
        """Get formatted string of recent notifications for GitHub issue context."""
        if not self.recent_notifications:
            return "No recent notifications"
        
        context_lines = []
        for idx, notif in enumerate(self.recent_notifications, 1):
            timestamp = notif["timestamp"]
            notif_type = notif["type"]
            title = notif["title"]
            description = notif["description"]
            
            context_lines.append(
                f"{idx}. **[{timestamp}]** {notif_type}: {title}\n"
                f"   {description}"
            )
        
        return "\n\n".join(context_lines)

    async def create_unhandled_mqtt_notification(
        self, 
        mqtt_data: dict[str, Any], 
        device_model: str,
        device_firmware: str
    ) -> None:
        """Create Home Assistant notification for unhandled MQTT message with GitHub issue link."""
        try:
            # Load integration version when needed
            integration_version = await self._get_integration_version()
            
            message_type = mqtt_data.get("type", "unknown")
            raw_message = mqtt_data.get("raw_message", {})
            event_time = mqtt_data.get("event_time")
            
            # Track this MQTT discovery event
            if message_type == "property":
                siid = mqtt_data.get("siid", "?")
                piid = mqtt_data.get("piid", "?")
                value = mqtt_data.get("value", "?")
                discovery_title = f"MQTT Discovery: Property siid:{siid} piid:{piid}"
                discovery_description = f"New property discovered with value: {value}"
            else:
                discovery_title = f"MQTT Discovery: {message_type}"
                discovery_description = f"New MQTT message type discovered"
            
            self._track_notification("Discovery", discovery_title, discovery_description)
            
            # Create a shortened version for the notification
            message_str = str(raw_message)
            if len(message_str) > 100:
                message_preview = message_str[:100] + "..."
            else:
                message_preview = message_str
            
            # Create GitHub issue URL with pre-filled content
            github_url = self._create_github_issue_url(
                message_type, raw_message, device_model, device_firmware, integration_version, event_time
            )
            
            # Create unique notification ID
            notification_id = f"dreame_mower_unhandled_mqtt_{hash(message_str) % 1000000}"
            
            # Create notification content based on message type
            if message_type == "property":
                title, message = self._create_property_notification(
                    mqtt_data, message_preview, github_url, device_model
                )
            else:
                title, message = self._create_message_notification(
                    message_preview, github_url, device_model
                )
            
            # Create the persistent notification in Home Assistant
            await self.hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "notification_id": notification_id,
                    "title": title,
                    "message": message,
                },
            )
        except Exception as ex:
            _LOGGER.error("Failed to create unhandled MQTT notification: %s", ex)

    async def create_device_error_notification(
        self,
        code: int,
        name: str,
        description: str,
        device_model: str,
        device_firmware: str
    ) -> None:
        """Create Home Assistant error notification for device error codes."""
        try:
            # Track this notification for context
            self._track_notification("Error", name, description)
            
            # Create unique notification ID
            notification_id = f"dreame_mower_device_error_{code}"
            
            title = f"🚨 {device_model} Error: {name}"
            message = (
                f"**Error Code:** {code}\n\n"
                f"**Description:** {description}\n\n"
                f"**Device:** {device_model} (Firmware: {device_firmware})\n\n"
                f"Please check your mower and address any issues indicated by this error code."
            )
            
            # Create the persistent notification in Home Assistant
            await self.hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "notification_id": notification_id,
                    "title": title,
                    "message": message,
                },
            )
            
            _LOGGER.warning("Created HA error notification for device code %d: %s", code, name)
            
        except Exception as ex:
            _LOGGER.error("Failed to create device error notification: %s", ex)

    async def create_device_info_notification(
        self,
        code: int,
        name: str,
        description: str,
        device_model: str,
        device_firmware: str
    ) -> None:
        """Create Home Assistant info notification for device info codes."""
        try:
            # Track this notification for context
            self._track_notification("Info", name, description)
            
            # Create unique notification ID
            notification_id = f"dreame_mower_device_info_{code}"
            
            title = f"ℹ️ {device_model} Status: {name}"
            message = (
                f"**Status Code:** {code}\n\n"
                f"**Description:** {description}\n\n"
                f"**Device:** {device_model} (Firmware: {device_firmware})"
            )
            
            # Create the persistent notification in Home Assistant
            await self.hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "notification_id": notification_id,
                    "title": title,
                    "message": message,
                },
            )
        except Exception as ex:
            _LOGGER.error("Failed to create device info notification: %s", ex)

    def _anonymize_message(self, message: dict[str, Any]) -> dict[str, Any]:
        """Anonymize sensitive information in MQTT message."""
        import copy
        
        # Create a deep copy to avoid modifying the original
        anonymized = copy.deepcopy(message)
        
        def anonymize_recursive(obj: Any) -> Any:
            """Recursively anonymize sensitive fields."""
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key.lower() in ('did', 'device_id', 'deviceid', 'uid', 'user_id', 'userid'):
                        # Replace with anonymized version - keep format but hide actual value
                        if isinstance(value, str) and len(value) > 4:
                            obj[key] = value[:2] + "*" * (len(value) - 4) + value[-2:]
                        elif isinstance(value, int):
                            # For numeric IDs, show first and last digit
                            str_val = str(value)
                            if len(str_val) > 2:
                                obj[key] = str_val[0] + "*" * (len(str_val) - 2) + str_val[-1]
                            else:
                                obj[key] = "*" * len(str_val)
                    else:
                        obj[key] = anonymize_recursive(value)
            elif isinstance(obj, list):
                return [anonymize_recursive(item) for item in obj]
            return obj
        
        anonymize_recursive(anonymized)
        return anonymized

    def _create_github_issue_url(
        self, 
        message_type: str, 
        raw_message: dict[str, Any],
        device_model: str,
        device_firmware: str,
        integration_version: str,
        event_time: str | None = None
    ) -> str:
        """Create GitHub issue URL with pre-filled content including recent notification context."""
        # Anonymize the raw message before including it
        anonymized_message = self._anonymize_message(raw_message)
        
        # Build event time section if available
        event_time_section = ""
        if event_time:
            event_time_section = f"\n**Event Time:** {event_time}\n"
        
        # Get recent notifications context
        recent_context = self._get_recent_notifications_context()
        
        issue_title = f"New MQTT message discovered: {message_type}"
        issue_body = f"""## New MQTT Message Discovered

**Device Information:**
- Model: {device_model}
- Firmware: {device_firmware}
- Integration Version: {integration_version}{event_time_section}
**Recent Activity Timeline:**
<!-- This shows what was happening on the device, including when this message occurred -->
{recent_context}

**Full Message (anonymized):**
```json
{json.dumps(anonymized_message, indent=2)}
```
"""

        return "https://github.com/antondaubert/dreame-mower/issues/new?" + urllib.parse.urlencode({
            "title": issue_title,
            "body": issue_body,
            "labels": "enhancement,mqtt-discovery"
        })

    def _create_property_notification(
        self, 
        mqtt_data: dict[str, Any], 
        message_preview: str, 
        github_url: str,
        device_model: str = "Dreame Mower"
    ) -> tuple[str, str]:
        """Create notification content for unhandled property messages."""
        siid = mqtt_data.get("siid", "?")
        piid = mqtt_data.get("piid", "?")
        value = mqtt_data.get("value", "?")
        
        title = f"🔍 New {device_model} Property: siid:{siid} piid:{piid}"
        message = (
            f"**Property:** siid:{siid} piid:{piid} = {value}\n\n"
            f"**Preview:** {message_preview}\n\n"
            f"[📝 Report this discovery on GitHub]({github_url})\n\n"
            f"✅ **Device IDs automatically anonymized in GitHub link**"
        )
        
        return title, message

    def _create_message_notification(
        self, 
        message_preview: str, 
        github_url: str,
        device_model: str = "Dreame Mower"
    ) -> tuple[str, str]:
        """Create notification content for unhandled message types."""
        title = f"📨 Unhandled {device_model} Message"
        message = (
            f"**Message Preview:** {message_preview}\n\n"
            f"[📝 Report this discovery on GitHub]({github_url})\n\n"
            f"✅ **Device IDs automatically anonymized in GitHub link**"
        )
        
        return title, message