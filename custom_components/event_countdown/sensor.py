"""Sensors showing each configured Event Countdown event."""
from __future__ import annotations

import logging
import re
from datetime import date, timedelta

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    CONF_DELETE_AFTER_OCCURRENCE,
    CONF_LANGUAGE,
    DEFAULT_LANGUAGE,
    DOMAIN,
    ENTRY_TYPE,
    ENTRY_TYPE_EVENT,
    EVENT_TYPE_ANNIVERSARY,
    EVENT_TYPE_BIRTHDAY,
    EVENT_TYPE_EVENT,
    SIGNAL_EVENTS_CHANGED,
)
from .lang import get_language

_LOGGER = logging.getLogger(__name__)
_UPDATE_INTERVAL = timedelta(hours=1)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up one stable sensor for each configured event entry."""
    language_code = entry.options.get(
        CONF_LANGUAGE, entry.data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)
    )
    if language_code == "auto":
        language_code = hass.config.language
    lang = get_language(language_code)
    sensors: dict[str, EventCountdownSensor] = {}

    @callback
    def _sync_entities() -> None:
        current_entries = {
            event_entry.entry_id: event_entry
            for event_entry in hass.config_entries.async_entries(DOMAIN)
            if event_entry.data.get(ENTRY_TYPE) == ENTRY_TYPE_EVENT
        }

        stale_entry_ids = set(sensors) - set(current_entries)
        for entry_id in stale_entry_ids:
            sensor = sensors.pop(entry_id)
            hass.async_create_task(sensor.async_remove(force_remove=True))
            _remove_entity_from_registry(hass, sensor.unique_id)

        new_sensors: list[EventCountdownSensor] = []
        for event_entry in current_entries.values():
            if event_entry.entry_id in sensors:
                sensors[event_entry.entry_id].set_event_entry(event_entry)
                continue
            sensor = EventCountdownSensor(entry, event_entry, lang)
            sensors[event_entry.entry_id] = sensor
            new_sensors.append(sensor)

        if new_sensors:
            async_add_entities(new_sensors, update_before_add=True)

        new_entry_ids = {new_sensor.event_entry_id for new_sensor in new_sensors}
        for entry_id, sensor in sensors.items():
            if entry_id not in new_entry_ids:
                sensor.async_schedule_update_ha_state(force_refresh=True)

    @callback
    def _refresh(now=None) -> None:
        hass.async_create_task(_remove_expired_events(hass))
        _sync_entities()

    _remove_legacy_slot_entities(hass, entry)
    _sync_entities()
    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_EVENTS_CHANGED, _refresh)
    )
    entry.async_on_unload(async_track_time_interval(hass, _refresh, _UPDATE_INTERVAL))


def _remove_legacy_slot_entities(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove old fixed slot entities created by previous versions."""
    ent_reg = er.async_get(hass)
    legacy_pattern = re.compile(rf"^{re.escape(entry.entry_id)}_event\d+$")
    for entity_entry in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
        if entity_entry.unique_id and legacy_pattern.match(entity_entry.unique_id):
            ent_reg.async_remove(entity_entry.entity_id)


def _remove_entity_from_registry(hass: HomeAssistant, unique_id: str | None) -> None:
    """Remove an event entity registry entry after its event config entry disappears."""
    if unique_id is None:
        return
    ent_reg = er.async_get(hass)
    entity_id = ent_reg.async_get_entity_id("sensor", DOMAIN, unique_id)
    if entity_id is not None:
        ent_reg.async_remove(entity_id)


def _event_from_entry(entry: ConfigEntry) -> dict:
    """Return the latest event data for a config entry."""
    return {**entry.data.get("event", {}), **entry.options}


async def _remove_expired_events(hass: HomeAssistant) -> None:
    """Remove event entries that occurred and are flagged for deletion afterwards."""
    today = date.today()

    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.data.get(ENTRY_TYPE) != ENTRY_TYPE_EVENT:
            continue

        event = _event_from_entry(entry)
        if not event.get(CONF_DELETE_AFTER_OCCURRENCE):
            continue

        day = event.get("day")
        month = event.get("month")
        if not day or not month:
            continue

        try:
            target = date(today.year, month, day)
        except ValueError:
            continue

        if target < today:
            _LOGGER.info(
                "Event Countdown: removing '%s' (occurred on %s)",
                event.get("name"),
                target,
            )
            await hass.config_entries.async_remove(entry.entry_id)


def _compute_event(event: dict, lang: dict[str, str]) -> dict | None:
    """Compute display data for a single event without mixing it with other events."""
    try:
        if event.get("disabled"):
            return None

        today = date.today()
        name = event.get("name")
        day = event.get("day")
        month = event.get("month")
        year = event.get("year")
        if not name or not day or not month:
            return None

        event_type = (event.get("type") or EVENT_TYPE_BIRTHDAY).lower()
        recurring = event.get("recurring")
        if recurring is None:
            recurring = event_type != EVENT_TYPE_EVENT

        try:
            target = date(today.year, month, day)
        except ValueError:
            _LOGGER.warning("Event Countdown: invalid date for '%s'", name)
            return None

        if target < today:
            if not recurring:
                return None
            target = date(today.year + 1, month, day)

        days_remaining = (target - today).days
        age = (target.year - year) if isinstance(year, int) else None
        soon_threshold = (
            event.get("soon") if isinstance(event.get("soon"), int) else 30
        )
        is_soon = days_remaining <= soon_threshold

        if days_remaining == 0:
            day_text = lang["today"]
        elif days_remaining == 1:
            day_text = lang["tomorrow"]
        else:
            day_text = lang["in_days"].format(days=days_remaining)

        if event_type == EVENT_TYPE_BIRTHDAY:
            base = re.sub(lang["strip_word"], "", name, flags=re.IGNORECASE).strip()
            full_name = (
                lang["birthday_with_age"].format(base=base, age=age, day_text=day_text)
                if age is not None
                else lang["birthday_no_age"].format(base=base, day_text=day_text)
            )
        elif event_type == EVENT_TYPE_ANNIVERSARY:
            full_name = (
                lang["anniversary_with_age"].format(
                    age=age, name=name.lower(), day_text=day_text
                )
                if age is not None
                else lang["anniversary_no_age"].format(name=name, day_text=day_text)
            )
        else:
            full_name = lang["event"].format(name=name, day_text=day_text)

        return {
            "name": name,
            "full_name": full_name,
            "type": event_type,
            "age": age,
            "days_remaining": days_remaining,
            "soon": is_soon,
            "soon_threshold": soon_threshold,
            "picture": event.get("picture"),
            "event_date": (
                f"{year}-{month:02d}-{day:02d}"
                if isinstance(year, int)
                else f"{today.year}-{month:02d}-{day:02d}"
            ),
        }
    except Exception:
        _LOGGER.exception("Event Countdown: error processing event %s", event)
        return None


class EventCountdownSensor(SensorEntity):
    """A sensor bound to exactly one event config entry."""

    _attr_icon = "mdi:calendar-clock"
    _attr_should_poll = False

    def __init__(
        self, global_entry: ConfigEntry, event_entry: ConfigEntry, lang: dict[str, str]
    ) -> None:
        self._global_entry = global_entry
        self._event_entry = event_entry
        self._lang = lang
        self._attr_unique_id = f"{global_entry.entry_id}_event_{event_entry.entry_id}"
        self._attr_name = event_entry.title
        self._data: dict | None = None

    @property
    def event_entry_id(self) -> str:
        """Return the config entry id for the event backing this sensor."""
        return self._event_entry.entry_id

    def set_event_entry(self, event_entry: ConfigEntry) -> None:
        """Update the config entry backing this sensor after edits."""
        self._event_entry = event_entry
        self._attr_name = event_entry.title

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._global_entry.entry_id)},
            name="Event Countdown",
            manufacturer="CagosDk",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> str:
        """Whether this event should be displayed as upcoming ("soon")."""
        return "true" if self._data and self._data["soon"] else "false"

    @property
    def entity_picture(self) -> str | None:
        return self._data["picture"] if self._data else None

    @property
    def extra_state_attributes(self):
        if not self._data:
            return {"full_name": self._lang["no_event"], "soon": False}
        return {
            "name": self._data["name"],
            "full_name": self._data["full_name"],
            "type": self._data["type"],
            "age": self._data["age"],
            "days_remaining": self._data["days_remaining"],
            "soon": self._data["soon"],
            "soon_threshold": self._data["soon_threshold"],
            "entity_picture": self._data["picture"],
            "event_date": self._data["event_date"],
        }

    def update(self) -> None:
        self._data = _compute_event(_event_from_entry(self._event_entry), self._lang)
