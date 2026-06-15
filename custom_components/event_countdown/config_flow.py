import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_DELETE_AFTER_OCCURRENCE,
    CONF_LANGUAGE,
    DEFAULT_LANGUAGE,
    DOMAIN,
    ENTRY_TYPE,
    ENTRY_TYPE_EVENT,
    ENTRY_TYPE_GLOBAL,
    EVENT_TYPE_ANNIVERSARY,
    EVENT_TYPE_BIRTHDAY,
    EVENT_TYPE_EVENT,
)

_LANGUAGE_SELECT_OPTIONS = [
    {"value": "auto", "label": "Automatic (use Home Assistant's language)"},
    {"value": "en", "label": "English"},
    {"value": "da", "label": "Dansk"},
]

_TYPE_OPTIONS = [
    {"value": EVENT_TYPE_BIRTHDAY, "label": "Birthday 🎂"},
    {"value": EVENT_TYPE_ANNIVERSARY, "label": "Anniversary 💍"},
    {"value": EVENT_TYPE_EVENT, "label": "Event 📅"},
]

_MONTH_OPTIONS = [
    {"value": "1", "label": "January"},
    {"value": "2", "label": "February"},
    {"value": "3", "label": "March"},
    {"value": "4", "label": "April"},
    {"value": "5", "label": "May"},
    {"value": "6", "label": "June"},
    {"value": "7", "label": "July"},
    {"value": "8", "label": "August"},
    {"value": "9", "label": "September"},
    {"value": "10", "label": "October"},
    {"value": "11", "label": "November"},
    {"value": "12", "label": "December"},
]


def _event_schema(event: dict | None = None) -> vol.Schema:
    ev = event or {}
    recurring = ev.get("recurring")
    if recurring is None:
        recurring = ev.get("type", EVENT_TYPE_BIRTHDAY) != EVENT_TYPE_EVENT

    return vol.Schema(
        {
            vol.Required("name", default=ev.get("name", "")): selector.TextSelector(),
            vol.Required("day", default=int(ev.get("day", 1))): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1, max=31, step=1, mode=selector.NumberSelectorMode.BOX
                )
            ),
            vol.Required("month", default=str(ev.get("month", 1))): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=_MONTH_OPTIONS,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(
                "year",
                description={"suggested_value": ev.get("year")},
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1900, max=2100, step=1, mode=selector.NumberSelectorMode.BOX
                )
            ),
            vol.Required("type", default=ev.get("type", EVENT_TYPE_BIRTHDAY)): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=_TYPE_OPTIONS,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required("soon", default=int(ev.get("soon", 30))): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1, max=365, step=1, mode=selector.NumberSelectorMode.BOX
                )
            ),
            vol.Optional(
                "picture",
                description={"suggested_value": ev.get("picture", "")},
            ): selector.TextSelector(),
            vol.Required("recurring", default=bool(recurring)): selector.BooleanSelector(),
            vol.Required(
                "disabled", default=bool(ev.get("disabled", False))
            ): selector.BooleanSelector(),
            vol.Required(
                CONF_DELETE_AFTER_OCCURRENCE,
                default=bool(ev.get(CONF_DELETE_AFTER_OCCURRENCE, False)),
            ): selector.BooleanSelector(),
        }
    )


def _form_to_event(user_input: dict) -> dict:
    event: dict = {
        "name": user_input["name"].strip(),
        "day": int(user_input["day"]),
        "month": int(user_input["month"]),
        "type": user_input["type"],
        "soon": int(user_input["soon"]),
        "recurring": bool(user_input["recurring"]),
        CONF_DELETE_AFTER_OCCURRENCE: bool(user_input.get(CONF_DELETE_AFTER_OCCURRENCE, False)),
        "disabled": bool(user_input.get("disabled", False)),
    }
    event["year"] = int(user_input["year"]) if user_input.get("year") is not None else None
    picture = user_input.get("picture")
    event["picture"] = picture.strip() if picture else None
    return event


class EventCountdownConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 5

    async def async_step_user(self, user_input=None):
        existing = self.hass.config_entries.async_entries(DOMAIN)
        has_global = any(
            e.data.get(ENTRY_TYPE) == ENTRY_TYPE_GLOBAL for e in existing
        )

        if not has_global:
            # First install creates the global configuration entry directly
            return self.async_create_entry(
                title="⚙️ Event Manager Configuration",
                data={ENTRY_TYPE: ENTRY_TYPE_GLOBAL},
            )

        # Integration already installed → adding an event
        return await self.async_step_event(user_input)

    async def async_step_event(self, user_input=None):
        if user_input is not None:
            event = _form_to_event(user_input)
            return self.async_create_entry(
                title=event["name"],
                data={ENTRY_TYPE: ENTRY_TYPE_EVENT, "event": event},
            )
        return self.async_show_form(step_id="event", data_schema=_event_schema())

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        if config_entry.data.get(ENTRY_TYPE) == ENTRY_TYPE_GLOBAL:
            return GlobalOptionsFlow(config_entry)
        return EventOptionsFlow(config_entry)


class GlobalOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        return await self.async_step_global(user_input)

    async def async_step_global(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={
                    CONF_LANGUAGE: user_input[CONF_LANGUAGE],
                },
            )

        current_language = self._config_entry.options.get(
            CONF_LANGUAGE,
            self._config_entry.data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE),
        )
        return self.async_show_form(
            step_id="global",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_LANGUAGE, default=current_language
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=_LANGUAGE_SELECT_OPTIONS,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
        )


class EventOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        return await self.async_step_event(user_input)

    async def async_step_event(self, user_input=None):
        if user_input is not None:
            event = _form_to_event(user_input)
            self.hass.config_entries.async_update_entry(
                self._config_entry, title=event["name"]
            )
            return self.async_create_entry(title="", data=event)

        current = {
            **self._config_entry.data.get("event", {}),
            **self._config_entry.options,
        }
        return self.async_show_form(
            step_id="event", data_schema=_event_schema(current)
        )
