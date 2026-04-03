"""Optional sensors for RF activity (Kismet last-time window count)."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import KismetDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor platform."""
    coordinator: KismetDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    if not coordinator.air_sensors_enabled():
        return
    async_add_entities([KismetRecentRfDevicesSensor(coordinator)])


class KismetRecentRfDevicesSensor(
    CoordinatorEntity[KismetDataUpdateCoordinator],
    SensorEntity,
):
    """Count of devices seen recently (Kismet /devices/last-time/...)."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "devices"
    _attr_icon = "mdi:access-point-network"

    def __init__(self, coordinator: KismetDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_recent_rf_devices"
        self._attr_name = "Kismet recent RF devices"
        self._attr_suggested_display_precision = 0

    @property
    def native_value(self) -> int | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.recent_rf_device_count

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        return {"window_sec": self.coordinator.recent_window_sec()}
