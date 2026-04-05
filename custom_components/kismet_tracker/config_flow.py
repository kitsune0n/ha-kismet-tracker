"""Config flow for Kismet Tracker."""

from __future__ import annotations

from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .const import (
    CONF_AWAY_TIMEOUT,
    CONF_ENABLE_AIR_SENSORS,
    CONF_HOST,
    CONF_IGNORE_RANDOMIZED,
    CONF_MIN_RSSI_HOME,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_RECENT_WINDOW,
    CONF_SCAN_INTERVAL,
    CONF_TRACK_ALL_VISIBLE,
    CONF_USE_SSL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    CONF_WHITELIST,
    DEFAULT_AWAY_TIMEOUT,
    DEFAULT_MIN_RSSI,
    DEFAULT_PORT,
    DEFAULT_RECENT_DEVICES_WINDOW,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    DEFAULT_IGNORE_RANDOMIZED_LOCAL_MAC,
)
from .coordinator import build_base_url
from .kismet_client import KismetClient
from .util import parse_mac_list


class CannotConnect(Exception):
    """Hub is not reachable."""


def _merge_for_probe(entry: config_entries.ConfigEntry, patch: dict[str, Any]) -> dict[str, Any]:
    merged = dict(entry.data)
    merged.update(entry.options)
    merged.update(patch)
    return merged


def _whitelist_to_multiline(mac_list: list[str]) -> str:
    return "\n".join(mac_list)


async def _validate_connection(hass: HomeAssistant, info: dict[str, Any]) -> None:
    verify = bool(info.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL))
    session = async_create_clientsession(hass, verify_ssl=verify)
    base = build_base_url(
        str(info[CONF_HOST]),
        int(info[CONF_PORT]),
        bool(info.get(CONF_USE_SSL, False)),
    )
    user = info.get(CONF_USERNAME)
    pwd = info.get(CONF_PASSWORD)
    auth = aiohttp.BasicAuth(user, pwd) if user and pwd else None
    client = KismetClient(session, base, auth=auth)
    if not await client.ping():
        raise CannotConnect


def _user_data_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): str,
            vol.Required(
                CONF_PORT,
                default=defaults.get(CONF_PORT, DEFAULT_PORT),
            ): vol.Coerce(int),
            vol.Required(
                CONF_USE_SSL,
                default=defaults.get(CONF_USE_SSL, False),
            ): bool,
            vol.Required(
                CONF_VERIFY_SSL,
                default=defaults.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
            ): bool,
            vol.Optional(
                CONF_USERNAME,
                default=defaults.get(CONF_USERNAME, ""),
            ): str,
            vol.Optional(
                CONF_PASSWORD,
                default=defaults.get(CONF_PASSWORD, ""),
            ): str,
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=defaults.get(CONF_SCAN_INTERVAL, 30),
            ): vol.All(vol.Coerce(int), vol.Range(min=5, max=3600)),
            vol.Required(
                CONF_TRACK_ALL_VISIBLE,
                default=defaults.get(CONF_TRACK_ALL_VISIBLE, False),
            ): bool,
            vol.Required(
                CONF_WHITELIST,
                default=defaults.get(CONF_WHITELIST, ""),
            ): str,
            vol.Required(
                CONF_IGNORE_RANDOMIZED,
                default=defaults.get(
                    CONF_IGNORE_RANDOMIZED,
                    DEFAULT_IGNORE_RANDOMIZED_LOCAL_MAC,
                ),
            ): bool,
            vol.Optional(
                CONF_AWAY_TIMEOUT,
                default=defaults.get(
                    CONF_AWAY_TIMEOUT,
                    int(DEFAULT_AWAY_TIMEOUT.total_seconds()),
                ),
            ): vol.All(vol.Coerce(int), vol.Range(min=30, max=86400)),
            vol.Optional(
                CONF_MIN_RSSI_HOME,
                default=defaults.get(CONF_MIN_RSSI_HOME, DEFAULT_MIN_RSSI),
            ): vol.All(vol.Coerce(int), vol.Range(min=-200, max=0)),
            vol.Optional(
                CONF_ENABLE_AIR_SENSORS,
                default=defaults.get(CONF_ENABLE_AIR_SENSORS, False),
            ): bool,
            vol.Optional(
                CONF_RECENT_WINDOW,
                default=defaults.get(CONF_RECENT_WINDOW, DEFAULT_RECENT_DEVICES_WINDOW),
            ): vol.All(vol.Coerce(int), vol.Range(min=30, max=900)),
        }
    )


def _options_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=defaults.get(CONF_SCAN_INTERVAL, 30),
            ): vol.All(vol.Coerce(int), vol.Range(min=5, max=3600)),
            vol.Required(
                CONF_TRACK_ALL_VISIBLE,
                default=defaults.get(CONF_TRACK_ALL_VISIBLE, False),
            ): bool,
            vol.Required(
                CONF_WHITELIST,
                default=defaults.get(CONF_WHITELIST, ""),
            ): str,
            vol.Required(
                CONF_IGNORE_RANDOMIZED,
                default=defaults.get(
                    CONF_IGNORE_RANDOMIZED,
                    DEFAULT_IGNORE_RANDOMIZED_LOCAL_MAC,
                ),
            ): bool,
            vol.Optional(
                CONF_AWAY_TIMEOUT,
                default=defaults.get(
                    CONF_AWAY_TIMEOUT,
                    int(DEFAULT_AWAY_TIMEOUT.total_seconds()),
                ),
            ): vol.All(vol.Coerce(int), vol.Range(min=30, max=86400)),
            vol.Optional(
                CONF_MIN_RSSI_HOME,
                default=defaults.get(CONF_MIN_RSSI_HOME, DEFAULT_MIN_RSSI),
            ): vol.All(vol.Coerce(int), vol.Range(min=-200, max=0)),
            vol.Optional(
                CONF_ENABLE_AIR_SENSORS,
                default=defaults.get(CONF_ENABLE_AIR_SENSORS, False),
            ): bool,
            vol.Optional(
                CONF_RECENT_WINDOW,
                default=defaults.get(CONF_RECENT_WINDOW, DEFAULT_RECENT_DEVICES_WINDOW),
            ): vol.All(vol.Coerce(int), vol.Range(min=30, max=900)),
        }
    )


class KismetConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            track_all = bool(user_input.get(CONF_TRACK_ALL_VISIBLE, False))
            try:
                macs = parse_mac_list(user_input[CONF_WHITELIST])
            except ValueError:
                errors["base"] = "invalid_mac"
            else:
                if not track_all and not macs:
                    errors["base"] = "whitelist_required"
                else:
                    payload = {**user_input, CONF_WHITELIST: macs}
                    unique_id = f"{payload[CONF_HOST]}:{payload[CONF_PORT]}"
                    await self.async_set_unique_id(unique_id)
                    self._abort_if_unique_id_configured()
                    try:
                        await _validate_connection(self.hass, payload)
                    except CannotConnect:
                        errors["base"] = "cannot_connect"
                    except aiohttp.ClientResponseError:
                        errors["base"] = "cannot_connect"
                    except aiohttp.ClientError:
                        errors["base"] = "cannot_connect"
                    else:
                        title = f"Kismet {payload[CONF_HOST]}:{payload[CONF_PORT]}"
                        return self.async_create_entry(title=title, data=payload)

        defaults: dict[str, Any] = {}
        if user_input:
            wl_raw = user_input.get(CONF_WHITELIST, "")
            defaults = {**user_input, CONF_WHITELIST: wl_raw}
        return self.async_show_form(
            step_id="user",
            data_schema=_user_data_schema(defaults),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> KismetOptionsFlow:
        return KismetOptionsFlow(config_entry)


class KismetOptionsFlow(config_entries.OptionsFlow):
    """Options for Kismet Tracker."""

    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self._entry = entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        merged = _merge_for_probe(self._entry, {})
        if CONF_WHITELIST in merged and isinstance(merged[CONF_WHITELIST], list):
            merged_for_defaults = {
                **merged,
                CONF_WHITELIST: _whitelist_to_multiline(merged[CONF_WHITELIST]),
            }
        else:
            merged_for_defaults = dict(merged)

        if user_input is not None:
            track_all = bool(user_input.get(CONF_TRACK_ALL_VISIBLE, False))
            try:
                macs = parse_mac_list(user_input[CONF_WHITELIST])
            except ValueError:
                errors["base"] = "invalid_mac"
            else:
                if not track_all and not macs:
                    errors["base"] = "whitelist_required"
                else:
                    options = {**user_input, CONF_WHITELIST: macs}
                    probe = _merge_for_probe(self._entry, options)
                    try:
                        await _validate_connection(self.hass, probe)
                    except CannotConnect:
                        errors["base"] = "cannot_connect"
                    except aiohttp.ClientResponseError:
                        errors["base"] = "cannot_connect"
                    except aiohttp.ClientError:
                        errors["base"] = "cannot_connect"
                    else:
                        return self.async_create_entry(title="", data=options)

        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(merged_for_defaults),
            errors=errors,
        )
