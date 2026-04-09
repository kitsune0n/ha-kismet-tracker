"""Thin async client for Kismet REST API used by this integration."""

from __future__ import annotations

from typing import Any

import aiohttp


def _parse_device_list_payload(data: Any) -> list[dict[str, Any]]:
    """Normalize Kismet JSON list or wrapper dict to a list of device records."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("kismet.device.list", "devices"):
            inner = data.get(key)
            if isinstance(inner, list):
                return inner
    return []


class KismetClient:
    """Minimal Kismet HTTP API wrapper."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        auth: aiohttp.BasicAuth | None = None,
    ) -> None:
        self._session = session
        self._base = base_url.rstrip("/")
        self._auth = auth

    async def ping(self) -> bool:
        """Return True if the server responds to a lightweight devices query."""
        url = f"{self._base}/devices/last-time/-1/devices.json"
        try:
            async with self._session.get(url, auth=self._auth, timeout=10) as resp:
                return resp.status == 200
        except aiohttp.ClientError:
            return False

    async def fetch_devices_for_macs(self, macs: list[str]) -> list[dict[str, Any]]:
        """POST /devices/multimac/devices.json — ideal for whitelist polling."""
        if not macs:
            return []
        url = f"{self._base}/devices/multimac/devices.json"
        payload = {"devices": macs}
        async with self._session.post(
            url,
            json=payload,
            auth=self._auth,
            timeout=30,
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
        return _parse_device_list_payload(data)

    async def fetch_devices_in_last_seconds(self, seconds: int) -> list[dict[str, Any]]:
        """GET /devices/last-time/-{seconds}/devices.json — devices active in the window."""
        url = f"{self._base}/devices/last-time/-{seconds}/devices.json"
        async with self._session.get(
            url,
            auth=self._auth,
            timeout=60,
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
        return _parse_device_list_payload(data)

    async def fetch_recent_device_count(self, seconds: int) -> int:
        """Count devices in last-time window (same endpoint as fetch_devices_in_last_seconds)."""
        devices = await self.fetch_devices_in_last_seconds(seconds)
        return len(devices)
