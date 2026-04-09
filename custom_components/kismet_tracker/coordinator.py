"""DataUpdateCoordinator for Kismet API polling."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import time
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

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
    CONF_TRACK_ALL_LOOKBACK_SEC,
    CONF_TRACK_ALL_VISIBLE,
    CONF_USE_SSL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    CONF_WHITELIST,
    DEFAULT_AWAY_TIMEOUT,
    DEFAULT_MIN_RSSI,
    DEFAULT_RECENT_DEVICES_WINDOW,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TRACK_ALL_LOOKBACK_SEC,
    DEFAULT_VERIFY_SSL,
    TRACK_ALL_LOOKBACK_MAX_SEC,
    TRACK_ALL_LOOKBACK_MIN_SEC,
    DOMAIN,
    LOGGER,
    RSSI_HOME_DISABLED_THRESHOLD,
)
from .kismet_client import KismetClient
from .util import extract_device_fields, is_locally_administered_mac, normalize_mac


def merge_entry_config(entry: ConfigEntry) -> dict[str, Any]:
    """Merge config entry data and options (options override)."""
    merged = dict(entry.data)
    merged.update(entry.options)
    return merged


def build_base_url(host: str, port: int, use_ssl: bool) -> str:
    scheme = "https" if use_ssl else "http"
    return f"{scheme}://{host}:{port}"


@dataclass
class KismetDeviceSnapshot:
    """Per-MAC snapshot used by device_tracker."""

    mac: str
    last_time: float | None
    signal_dbm: float | None
    phytypes: list[str]


@dataclass
class KismetCoordinatorData:
    """Coordinator update payload."""

    devices: dict[str, KismetDeviceSnapshot]
    recent_rf_device_count: int | None


class KismetDataUpdateCoordinator(DataUpdateCoordinator[KismetCoordinatorData]):
    """Poll Kismet (allow list or last-time window) and optional air-activity metrics."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
    ) -> None:
        self.config_entry = entry
        merged = merge_entry_config(entry)
        scan_sec = int(
            merged.get(CONF_SCAN_INTERVAL, int(DEFAULT_SCAN_INTERVAL.total_seconds()))
        )
        update_interval = timedelta(seconds=max(5, scan_sec))
        super().__init__(
            hass,
            LOGGER,
            name=f"{DOMAIN} {entry.title}",
            update_interval=update_interval,
        )
        verify = bool(merged.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL))
        self._session = async_create_clientsession(hass, verify_ssl=verify)
        base = build_base_url(
            merged[CONF_HOST],
            int(merged[CONF_PORT]),
            bool(merged.get(CONF_USE_SSL, False)),
        )
        user = merged.get(CONF_USERNAME)
        pwd = merged.get(CONF_PASSWORD)
        auth = aiohttp.BasicAuth(user, pwd) if user and pwd else None
        self._client = KismetClient(self._session, base, auth=auth)

    def track_all_visible(self) -> bool:
        """When True, poll Kismet last-time window and expose all matching MACs."""
        merged = merge_entry_config(self.config_entry)
        return bool(merged.get(CONF_TRACK_ALL_VISIBLE, False))

    def track_all_lookback_sec(self) -> int:
        """Seconds for last-time query in track-all mode."""
        merged = merge_entry_config(self.config_entry)
        raw = int(merged.get(CONF_TRACK_ALL_LOOKBACK_SEC, DEFAULT_TRACK_ALL_LOOKBACK_SEC))
        return max(TRACK_ALL_LOOKBACK_MIN_SEC, min(TRACK_ALL_LOOKBACK_MAX_SEC, raw))

    def whitelisted_macs(self) -> list[str]:
        """MAC addresses configured for tracking (whitelist mode only)."""
        merged = merge_entry_config(self.config_entry)
        raw = merged.get(CONF_WHITELIST) or []
        if isinstance(raw, str):
            from .util import parse_mac_list

            return parse_mac_list(raw)
        out: list[str] = []
        for m in raw:
            try:
                out.append(normalize_mac(str(m)))
            except ValueError:
                continue
        return list(dict.fromkeys(out))

    def tracked_macs(self) -> list[str]:
        """MACs that should get entity_platform entities (respect random-MAC filter)."""
        merged = merge_entry_config(self.config_entry)
        ignore_rand = bool(merged.get(CONF_IGNORE_RANDOMIZED, True))
        if self.track_all_visible():
            if not self.data:
                return []
            macs = list(self.data.devices.keys())
        else:
            macs = self.whitelisted_macs()
        if not ignore_rand:
            return macs
        return [m for m in macs if not is_locally_administered_mac(m)]

    def away_seconds(self) -> float:
        merged = merge_entry_config(self.config_entry)
        return float(merged.get(CONF_AWAY_TIMEOUT, DEFAULT_AWAY_TIMEOUT.total_seconds()))

    def min_rssi_home(self) -> float | None:
        merged = merge_entry_config(self.config_entry)
        if CONF_MIN_RSSI_HOME not in merged:
            return float(DEFAULT_MIN_RSSI)
        val = merged.get(CONF_MIN_RSSI_HOME)
        if val is None:
            return None
        return float(val)

    def air_sensors_enabled(self) -> bool:
        merged = merge_entry_config(self.config_entry)
        return bool(merged.get(CONF_ENABLE_AIR_SENSORS, False))

    def recent_window_sec(self) -> int:
        merged = merge_entry_config(self.config_entry)
        return int(merged.get(CONF_RECENT_WINDOW, DEFAULT_RECENT_DEVICES_WINDOW))

    def is_home_for_mac(self, mac: str, snap: KismetDeviceSnapshot | None) -> bool:
        """Whether this MAC should be considered home."""
        if snap is None or snap.last_time is None:
            return False
        now = time.time()
        if now - snap.last_time > self.away_seconds():
            return False
        min_rssi = self.min_rssi_home()
        if (
            min_rssi is not None
            and min_rssi > RSSI_HOME_DISABLED_THRESHOLD
            and snap.signal_dbm is not None
        ):
            if snap.signal_dbm < min_rssi:
                return False
        return True

    async def _async_update_data(self) -> KismetCoordinatorData:
        try:
            if self.track_all_visible():
                lookback = self.track_all_lookback_sec()
                raw_list = await self._client.fetch_devices_in_last_seconds(lookback)
            else:
                macs = self.whitelisted_macs()
                if not macs:
                    LOGGER.warning(
                        "Kismet tracker: allow list is empty; enable 'Track all visible "
                        "devices' or add MAC addresses"
                    )
                raw_list = await self._client.fetch_devices_for_macs(macs)
        except aiohttp.ClientResponseError as err:
            raise UpdateFailed(f"Kismet HTTP error: {err.status}") from err
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Kismet connection failed: {err}") from err

        devices: dict[str, KismetDeviceSnapshot] = {}
        for item in raw_list:
            if not isinstance(item, dict):
                continue
            fields = extract_device_fields(item)
            m = fields.get("mac")
            if not m:
                continue
            try:
                norm = normalize_mac(str(m))
            except ValueError:
                continue
            devices[norm] = KismetDeviceSnapshot(
                mac=norm,
                last_time=fields.get("last_time"),
                signal_dbm=fields.get("signal_dbm"),
                phytypes=list(fields.get("phytypes") or []),
            )

        recent: int | None = None
        if self.air_sensors_enabled():
            try:
                recent = await self._client.fetch_recent_device_count(
                    self.recent_window_sec()
                )
            except (aiohttp.ClientError, TimeoutError) as err:
                LOGGER.debug("Recent device count failed: %s", err)
                recent = None

        return KismetCoordinatorData(devices=devices, recent_rf_device_count=recent)
