"""Shared helpers for MAC normalization and Kismet device field extraction."""

from __future__ import annotations

import re
from typing import Any, Mapping

_MAC_RE = re.compile(r"^([0-9A-Fa-f]{2})[:-]?([0-9A-Fa-f]{2})[:-]?([0-9A-Fa-f]{2})[:-]?([0-9A-Fa-f]{2})[:-]?([0-9A-Fa-f]{2})[:-]?([0-9A-Fa-f]{2})$")


def normalize_mac(raw: str) -> str:
    """Normalize MAC to AA:BB:CC:DD:EE:FF uppercase."""
    s = raw.strip().upper().replace("-", ":")
    parts = s.split(":")
    if len(parts) == 6 and all(len(p) == 2 for p in parts):
        return ":".join(parts)
    m = _MAC_RE.match(raw.strip().upper().replace("-", ""))
    if not m:
        raise ValueError(f"Invalid MAC address: {raw!r}")
    return ":".join(m.groups()).upper()


def parse_mac_list(raw: str) -> list[str]:
    """Parse comma or newline separated MAC list."""
    items: list[str] = []
    for line in raw.replace(",", "\n").splitlines():
        part = line.strip()
        if not part:
            continue
        items.append(normalize_mac(part))
    return list(dict.fromkeys(items))


def is_locally_administered_mac(mac: str) -> bool:
    """IEEE 802: U/L bit set in first octet (randomized / local)."""
    first = int(mac.split(":")[0], 16)
    return (first & 0x02) != 0


def _get_flat(device: Mapping[str, Any], *keys: str) -> Any:
    for k in keys:
        if k in device:
            return device[k]
    return None


def extract_device_fields(device: Mapping[str, Any]) -> dict[str, Any]:
    """Return normalized fields from a Kismet device record."""
    mac = _get_flat(
        device,
        "kismet.device.base.macaddr",
    )
    if mac is None:
        base = device.get("kismet.device.base")
        if isinstance(base, dict):
            mac = base.get("kismet.device.base.macaddr") or base.get("macaddr")

    last_time = _get_flat(
        device,
        "kismet.device.base.last_time",
    )
    if last_time is None:
        base = device.get("kismet.device.base")
        if isinstance(base, dict):
            last_time = base.get("kismet.device.base.last_time") or base.get(
                "last_time"
            )

    signal = _get_flat(
        device,
        "kismet.device.base.signal",
        "kismet.device.base.last_signal_dbm",
    )
    if signal is None:
        signal = _get_flat(
            device,
            "dot11.device.last_signal_dbm",
        )

    phytypes: list[str] = []
    phy = _get_flat(device, "kismet.device.base.phyname")
    if isinstance(phy, str):
        phytypes.append(phy.lower())
    if not phytypes:
        for key in device:
            if isinstance(key, str) and "bluetooth" in key.lower():
                phytypes.append("bluetooth")
            if isinstance(key, str) and "dot11" in key.lower():
                phytypes.append("ieee80211")

    return {
        "mac": str(mac).upper() if mac else None,
        "last_time": float(last_time) if last_time is not None else None,
        "signal_dbm": float(signal) if signal is not None else None,
        "phytypes": phytypes,
    }
