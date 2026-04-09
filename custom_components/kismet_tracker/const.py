"""Constants for the Kismet Tracker integration."""

from __future__ import annotations

from datetime import timedelta
import logging

DOMAIN = "kismet_tracker"
LOGGER = logging.getLogger(__package__)

DEFAULT_PORT = 2501
DEFAULT_SCAN_INTERVAL = timedelta(seconds=30)
DEFAULT_AWAY_TIMEOUT = timedelta(seconds=180)
DEFAULT_VERIFY_SSL = False
DEFAULT_IGNORE_RANDOMIZED_LOCAL_MAC = True
DEFAULT_RECENT_DEVICES_WINDOW = 120
DEFAULT_MIN_RSSI = -85
# Kismet last-time window (seconds) when tracking all visible devices.
DEFAULT_TRACK_ALL_LOOKBACK_SEC = 86400
TRACK_ALL_LOOKBACK_MIN_SEC = 60
TRACK_ALL_LOOKBACK_MAX_SEC = 604800
# RSSI values at or below this skip the RSSI gate (Kismet may omit signal on some PHYs).
RSSI_HOME_DISABLED_THRESHOLD = -200

CONF_HOST = "host"
CONF_PORT = "port"
CONF_USE_SSL = "use_ssl"
CONF_VERIFY_SSL = "verify_ssl"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_WHITELIST = "whitelist"
CONF_TRACK_ALL_VISIBLE = "track_all_visible_devices"
CONF_TRACK_ALL_LOOKBACK_SEC = "track_all_lookback_sec"
CONF_IGNORE_RANDOMIZED = "ignore_randomized_local_mac"
CONF_AWAY_TIMEOUT = "away_timeout_sec"
CONF_MIN_RSSI_HOME = "min_rssi_for_home"
CONF_ENABLE_AIR_SENSORS = "enable_air_sensors"
CONF_RECENT_WINDOW = "recent_devices_window_sec"
