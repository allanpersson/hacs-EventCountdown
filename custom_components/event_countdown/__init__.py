import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    CONF_DELETE_AFTER_OCCURRENCE,
    DOMAIN,
    ENTRY_TYPE,
    ENTRY_TYPE_EVENT,
    ENTRY_TYPE_GLOBAL,
    LEGACY_TYPE_MAP,
    SIGNAL_EVENTS_CHANGED,
)

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor"]


def _is_global(entry: ConfigEntry) -> bool:
    return entry.data.get(ENTRY_TYPE) == ENTRY_TYPE_GLOBAL


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    if _is_global(entry):
        # The global entry owns the event sensors
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    else:
        # Event entries hold data only — notify event sensors to sync/recompute
        async_dispatcher_send(hass, SIGNAL_EVENTS_CHANGED)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if _is_global(entry):
        return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    # Event entry removed/unloaded — sync/recompute event sensors
    async_dispatcher_send(hass, SIGNAL_EVENTS_CHANGED)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    if _is_global(entry):
        # Global options changed — reload sensors to apply them
        await hass.config_entries.async_reload(entry.entry_id)
    else:
        # Event edited — just recompute
        async_dispatcher_send(hass, SIGNAL_EVENTS_CHANGED)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old config entries to the current version."""
    if entry.version >= 5:
        return True

    if entry.data.get(ENTRY_TYPE) == ENTRY_TYPE_EVENT:
        new_data = {**entry.data}
        event = {**new_data.get("event", {})}
        event["type"] = LEGACY_TYPE_MAP.get(event.get("type"), event.get("type"))
        event.setdefault(CONF_DELETE_AFTER_OCCURRENCE, False)
        new_data["event"] = event

        new_options = {**entry.options}
        if "type" in new_options:
            new_options["type"] = LEGACY_TYPE_MAP.get(
                new_options["type"], new_options["type"]
            )
        if new_options:
            new_options.setdefault(CONF_DELETE_AFTER_OCCURRENCE, False)

        hass.config_entries.async_update_entry(
            entry, data=new_data, options=new_options, version=5
        )
    else:
        title = entry.title
        if title in {"Global Configuration", "⚙️ Global Configuration"}:
            title = "⚙️ Event Manager Configuration"
        hass.config_entries.async_update_entry(entry, title=title, version=5)

    return True
