"""Kismet-backed device_tracker entities (allow list or all visible in time window)."""

from __future__ import annotations

from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.components.device_tracker.const import SourceType
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_HOME, STATE_NOT_HOME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import KismetDataUpdateCoordinator, KismetDeviceSnapshot

_BLE_SOURCE_TYPE = getattr(SourceType, "BLUETOOTH_LE", SourceType.BLUETOOTH)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up device_tracker platform."""
    coordinator: KismetDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    if coordinator.track_all_visible():
        added: set[str] = set()

        @callback
        def _add_new_entities() -> None:
            macs = coordinator.tracked_macs()
            new = [m for m in macs if m not in added]
            if not new:
                return
            async_add_entities(KismetDeviceTracker(coordinator, m) for m in new)
            added.update(new)

        _add_new_entities()
        entry.async_on_unload(coordinator.async_add_listener(_add_new_entities))
    else:
        macs = coordinator.tracked_macs()
        async_add_entities(KismetDeviceTracker(coordinator, mac) for mac in macs)


class KismetDeviceTracker(
    CoordinatorEntity[KismetDataUpdateCoordinator],
    TrackerEntity,
):
    """Presence from Kismet multimac polling."""

    _attr_should_poll = False

    def __init__(self, coordinator: KismetDataUpdateCoordinator, mac: str) -> None:
        super().__init__(coordinator)
        safe = mac.replace(":", "")
        self._mac = mac
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{safe}"
        self._attr_name = f"Kismet {mac}"

    @property
    def source_type(self) -> SourceType:
        snap = self.coordinator.data.devices.get(self._mac) if self.coordinator.data else None
        if snap and snap.phytypes and any("bluetooth" in p for p in snap.phytypes):
            return _BLE_SOURCE_TYPE
        return SourceType.ROUTER

    @property
    def battery_level(self) -> None:
        return None

    @property
    def state(self) -> str:
        snap = (
            self.coordinator.data.devices.get(self._mac)
            if self.coordinator.data
            else None
        )
        return (
            STATE_HOME
            if self.coordinator.is_home_for_mac(self._mac, snap)
            else STATE_NOT_HOME
        )

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        snap: KismetDeviceSnapshot | None = (
            self.coordinator.data.devices.get(self._mac)
            if self.coordinator.data
            else None
        )
        return {
            "mac": self._mac,
            "last_time": snap.last_time if snap else None,
            "signal_dbm": snap.signal_dbm if snap else None,
            "phytypes": snap.phytypes if snap else [],
        }
