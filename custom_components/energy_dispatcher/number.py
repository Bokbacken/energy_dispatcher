from __future__ import annotations
from typing import Optional
from homeassistant.components.number import NumberEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.typing import StateType
from .const import (
    DOMAIN, STORE_ENTITIES, STORE_MANUAL,
    M_EV_BATT_KWH, M_EV_CURRENT_SOC, M_EV_TARGET_SOC,
    M_HOME_BATT_CAP_KWH, M_HOME_BATT_SOC_FLOOR,
    M_EVSE_MAX_A, M_EVSE_PHASES, M_EVSE_VOLTAGE,
    EVENT_ACTION,
)

DEFAULTS = {
    M_EV_BATT_KWH: 75.0,
    M_EV_CURRENT_SOC: 40.0,
    M_EV_TARGET_SOC: 80.0,
    M_HOME_BATT_CAP_KWH: 30.0,
    M_HOME_BATT_SOC_FLOOR: 10.0,
    M_EVSE_MAX_A: 16.0,
    M_EVSE_PHASES: 3.0,
    M_EVSE_VOLTAGE: 230.0,
}

async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    st = hass.data[DOMAIN][entry.entry_id]
    st.setdefault(STORE_MANUAL, {})
    st.setdefault(STORE_ENTITIES, {})
    manual = st[STORE_MANUAL]
    def nv(key: str) -> float:
        return float(manual.get(key, DEFAULTS[key]))
    entities = [
        EDNumber(entry.entry_id, "ev_battery_capacity", "kWh", 10, 150, 1, M_EV_BATT_KWH, nv(M_EV_BATT_KWH)),
        EDNumber(entry.entry_id, "ev_current_soc", "%", 0, 100, 1, M_EV_CURRENT_SOC, nv(M_EV_CURRENT_SOC)),
        EDNumber(entry.entry_id, "ev_target_soc", "%", 10, 100, 5, M_EV_TARGET_SOC, nv(M_EV_TARGET_SOC)),
        EDNumber(entry.entry_id, "home_battery_capacity", "kWh", 1, 50, 0.5, M_HOME_BATT_CAP_KWH, nv(M_HOME_BATT_CAP_KWH)),
        EDNumber(entry.entry_id, "home_battery_soc_floor", "%", 0, 50, 1, M_HOME_BATT_SOC_FLOOR, nv(M_HOME_BATT_SOC_FLOOR)),
        EDNumber(entry.entry_id, "evse_max_current", "A", 6, 32, 1, M_EVSE_MAX_A, nv(M_EVSE_MAX_A)),
        EDNumber(entry.entry_id, "evse_phases", None, 1, 3, 1, M_EVSE_PHASES, nv(M_EVSE_PHASES)),
        EDNumber(entry.entry_id, "evse_voltage", "V", 180, 250, 1, M_EVSE_VOLTAGE, nv(M_EVSE_VOLTAGE)),
    ]
    async_add_entities(entities)

class EDNumber(NumberEntity):
    should_poll = False
    _attr_has_entity_name = True
    
    def __init__(self, entry_id: str, translation_key: str, unit: Optional[str],
                 min_v: float, max_v: float, step: float, key: str, init_value: float):
        self._entry_id = entry_id
        self._attr_translation_key = translation_key
        self._unit = unit
        self._min = min_v
        self._max = max_v
        self._step = step
        self._key = key
        self._value = init_value

    async def async_added_to_hass(self) -> None:
        st = self.hass.data[DOMAIN][self._entry_id]
        st.setdefault(STORE_MANUAL, {})
        st.setdefault(STORE_ENTITIES, {})
        st[STORE_MANUAL].setdefault(self._key, float(self._value))
        st[STORE_ENTITIES][f"number_{self._key}"] = self.entity_id

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(identifiers={(DOMAIN, "energy_dispatcher")}, name="Energy Dispatcher", manufacturer="Bokbacken")

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_number_{self._key}_{self._entry_id}"

    @property
    def native_unit_of_measurement(self) -> Optional[str]:
        return self._unit

    @property
    def native_min_value(self) -> float:
        return float(self._min)

    @property
    def native_max_value(self) -> float:
        return float(self._max)

    @property
    def native_step(self) -> float:
        return float(self._step)

    @property
    def native_value(self) -> StateType:
        return float(self.hass.data[DOMAIN][self._entry_id][STORE_MANUAL].get(self._key, self._value))

    async def async_set_native_value(self, value: float) -> None:
        self.hass.data[DOMAIN][self._entry_id][STORE_MANUAL][self._key] = float(value)
        self.async_write_ha_state()
        self.hass.bus.async_fire(EVENT_ACTION, {"entry_id": self._entry_id, "entity_id": self.entity_id, "key": self._key, "value": float(value)})
