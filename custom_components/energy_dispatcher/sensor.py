from __future__ import annotations

from typing import Any, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
# from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo

# ====== NYA PLANERINGSSENSORER (v0.5.4) ======
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import (
    DOMAIN,
    STORE_MANUAL,
    M_EV_BATT_KWH,
    M_EV_CURRENT_SOC,
    M_EV_TARGET_SOC,
    M_HOME_BATT_CAP_KWH,
    M_HOME_BATT_SOC_FLOOR,
    M_EVSE_MAX_A,
    M_EVSE_PHASES,
    M_EVSE_VOLTAGE,
)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    st = hass.data[DOMAIN][entry.entry_id]
    coordinator = st["coordinator"]

    entities = [
        EnrichedPriceSensor(coordinator, entry.entry_id),
        HouseBaselineSensor(coordinator, entry.entry_id),
        BatteryRuntimeSensor(coordinator, entry.entry_id),
        BatteryCostSensor(coordinator, entry.entry_id),
        BatteryVsGridDeltaSensor(coordinator, entry.entry_id),
        SolarPowerNowSensor(coordinator, entry.entry_id),
        SolarEnergyTodaySensor(coordinator, entry.entry_id),
        SolarEnergyTomorrowSensor(coordinator, entry.entry_id),
        PVPowerNowSensor(coordinator, entry.entry_id),
        PVEnergyTodaySensor(coordinator, entry.entry_id),
        SolarDelta15mSensor(coordinator, entry.entry_id),
        EVTimeUntilChargeSensor(coordinator, entry.entry_id),
        EVChargeReasonSensor(coordinator, entry.entry_id),
        BattTimeUntilChargeSensor(coordinator, entry.entry_id),
        BattChargeReasonSensor(coordinator, entry.entry_id),
    ]
    async_add_entities(entities)


class BaseEDSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry_id: str):
        super().__init__(coordinator)
        self._entry_id = entry_id

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, "energy_dispatcher")},
            name="Energy Dispatcher",
            manufacturer="Bokbacken",
        )


class EnrichedPriceSensor(BaseEDSensor):
    _attr_name = "Enriched Power Price"
    _attr_native_unit_of_measurement = "SEK/kWh"
    _attr_icon = "mdi:currency-usd"

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_enriched_price_{self._entry_id}"

    @property
    def native_value(self) -> Optional[float]:
        return self.coordinator.data.get("current_enriched")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        hourly = self.coordinator.data.get("hourly_prices") or []
        out = [
            {
                "time": p.time.isoformat(),
                "spot": p.spot_sek_per_kwh,
                "enriched": p.enriched_sek_per_kwh,
            }
            for p in hourly
        ]
        return {
            "hourly": out,
            "cheap_threshold": self.coordinator.data.get("cheap_threshold"),
        }


class HouseBaselineSensor(BaseEDSensor):
    _attr_name = "House Load Baseline Now"
    _attr_native_unit_of_measurement = "W"
    _attr_icon = "mdi:home-lightning-bolt"
    _attr_device_class = "power"
    _attr_state_class = "measurement"

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_house_baseline_w_{self._entry_id}"

    @property
    def native_value(self):
        return self.coordinator.data.get("house_baseline_w")

    @property
    def extra_state_attributes(self):
        return {
            "method": self.coordinator.data.get("baseline_method"),
            "source_value": self.coordinator.data.get("baseline_source_value"),
            "baseline_kwh_per_h": self.coordinator.data.get("baseline_kwh_per_h"),
            "exclusion_reason": self.coordinator.data.get("baseline_exclusion_reason"),
        }


class BatteryRuntimeSensor(BaseEDSensor):
    _attr_name = "Battery Runtime Estimate"
    _attr_native_unit_of_measurement = "h"
    _attr_icon = "mdi:clock-outline"

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_battery_runtime_{self._entry_id}"

    @property
    def native_value(self) -> Optional[float]:
        return self.coordinator.data.get("battery_runtime_h")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "baseline_kwh_per_h": self.coordinator.data.get("baseline_kwh_per_h"),
            "house_baseline_w": self.coordinator.data.get("house_baseline_w"),
        }


class BatteryCostSensor(BaseEDSensor):
    _attr_name = "Battery Energy Cost"
    _attr_native_unit_of_measurement = "SEK/kWh"
    _attr_icon = "mdi:battery-heart-variant"

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_battery_cost_{self._entry_id}"

    @property
    def native_value(self) -> float:
        store = self.coordinator.hass.data.get(DOMAIN, {}).get(self._entry_id, {})
        return float(store.get("wace", 0.0))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        store = self.coordinator.hass.data.get(DOMAIN, {}).get(self._entry_id, {})
        return {
            "total_energy_kwh": float(store.get("wace_tot_energy_kwh", 0.0)),
            "total_cost_sek": float(store.get("wace_tot_cost_sek", 0.0)),
        }


class BatteryVsGridDeltaSensor(BaseEDSensor):
    _attr_name = "Battery vs Grid Price Delta"
    _attr_native_unit_of_measurement = "SEK/kWh"
    _attr_icon = "mdi:scale-balance"

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_batt_vs_grid_delta_{self._entry_id}"

    @property
    def native_value(self):
        return self.coordinator.data.get("grid_vs_batt_delta_sek_per_kwh")


class SolarPowerNowSensor(BaseEDSensor):
    _attr_name = "Solar Power Forecast Now"
    _attr_native_unit_of_measurement = "W"
    _attr_icon = "mdi:solar-power"
    _attr_device_class = "power"
    _attr_state_class = "measurement"

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_solar_now_w_{self._entry_id}"

    @property
    def native_value(self):
        return self.coordinator.data.get("solar_now_w")

    @property
    def extra_state_attributes(self):
        pts = self.coordinator.data.get("solar_points") or []
        return {"points": [{"time": p.time.isoformat(), "watts": p.watts} for p in pts[:96]]}


class SolarEnergyTodaySensor(BaseEDSensor):
    _attr_name = "Solar Energy Forecast Today"
    _attr_native_unit_of_measurement = "kWh"
    _attr_icon = "mdi:solar-power"
    _attr_device_class = "energy"
    _attr_state_class = "measurement"

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_solar_today_kwh_{self._entry_id}"

    @property
    def native_value(self):
        return self.coordinator.data.get("solar_today_kwh")


class SolarEnergyTomorrowSensor(BaseEDSensor):
    _attr_name = "Solar Energy Forecast Tomorrow"
    _attr_native_unit_of_measurement = "kWh"
    _attr_icon = "mdi:solar-power"
    _attr_device_class = "energy"
    _attr_state_class = "measurement"

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_solar_tomorrow_kwh_{self._entry_id}"

    @property
    def native_value(self):
        return self.coordinator.data.get("solar_tomorrow_kwh")


class PVPowerNowSensor(BaseEDSensor):
    _attr_name = "Solar Production Now"
    _attr_native_unit_of_measurement = "W"
    _attr_icon = "mdi:solar-power"
    _attr_device_class = "power"
    _attr_state_class = "measurement"

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_pv_now_w_{self._entry_id}"

    @property
    def native_value(self):
        return self.coordinator.data.get("pv_now_w")


class PVEnergyTodaySensor(BaseEDSensor):
    _attr_name = "Solar Production Today"
    _attr_native_unit_of_measurement = "kWh"
    _attr_icon = "mdi:solar-power"
    _attr_device_class = "energy"
    _attr_state_class = "measurement"

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_pv_today_kwh_{self._entry_id}"

    @property
    def native_value(self):
        return self.coordinator.data.get("pv_today_kwh")


class SolarDelta15mSensor(BaseEDSensor):
    _attr_name = "Solar Forecast Delta 15m"
    _attr_native_unit_of_measurement = "W"
    _attr_icon = "mdi:chart-line"
    _attr_state_class = "measurement"

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_solar_delta_15m_{self._entry_id}"

    @property
    def native_value(self):
        return self.coordinator.data.get("solar_delta_15m_w")

    @property
    def extra_state_attributes(self):
        return {"percent_of_forecast": self.coordinator.data.get("solar_delta_15m_pct")}


class EVTimeUntilChargeSensor(BaseEDSensor):
    _attr_name = "EV Time Until Charge"
    _attr_native_unit_of_measurement = "min"
    _attr_icon = "mdi:clock-start"

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_ev_time_until_charge_{self._entry_id}"

    @property
    def native_value(self):
        return self.coordinator.data.get("time_until_charge_ev_min")


class EVChargeReasonSensor(BaseEDSensor):
    _attr_name = "EV Charge Reason"
    _attr_icon = "mdi:information-outline"

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_ev_charge_reason_{self._entry_id}"

    @property
    def native_value(self):
        return self.coordinator.data.get("auto_ev_reason")

    @property
    def extra_state_attributes(self):
        return {
            "setpoint_a": self.coordinator.data.get("auto_ev_setpoint_a"),
            "cheap_threshold": self.coordinator.data.get("cheap_threshold"),
        }


class BattTimeUntilChargeSensor(BaseEDSensor):
    _attr_name = "Battery Time Until Charge"
    _attr_native_unit_of_measurement = "min"
    _attr_icon = "mdi:clock-start"

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_batt_time_until_charge_{self._entry_id}"

    @property
    def native_value(self):
        return self.coordinator.data.get("time_until_charge_batt_min")


class BattChargeReasonSensor(BaseEDSensor):
    _attr_name = "Battery Charge Reason"
    _attr_icon = "mdi:information-outline"

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_batt_charge_reason_{self._entry_id}"

    @property
    def native_value(self):
        return self.coordinator.data.get("batt_charge_reason")

# ====== v0.5.4: PLANERING + DIAGNOSTIK ======
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import (
    DOMAIN, STORE_MANUAL,
    M_EV_BATT_KWH, M_EV_CURRENT_SOC, M_EV_TARGET_SOC,
    M_HOME_BATT_CAP_KWH, M_HOME_BATT_SOC_FLOOR,
    M_EVSE_MAX_A, M_EVSE_PHASES, M_EVSE_VOLTAGE,
)

class _BasePlan(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry_id: str, name: str, unit: str | None = None, icon: str | None = None):
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._attr_name = name
        self._attr_native_unit_of_measurement = unit
        if icon:
            self._attr_icon = icon

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(identifiers={(DOMAIN, "energy_dispatcher")}, name="Energy Dispatcher", manufacturer="Bokbacken")

    def _m(self, key: str, default: float) -> float:
        st = self.coordinator.hass.data.get(DOMAIN, {}).get(self._entry_id, {})
        return float(st.get(STORE_MANUAL, {}).get(key, default))

    def _pv_now_w(self) -> float:
        pv = self.coordinator.data.get("pv_now_w")
        if pv is None:
            pv = self.coordinator.data.get("solar_now_w") or 0.0
        return float(pv or 0.0)

    def _house_w(self) -> float:
        return float(self.coordinator.data.get("house_baseline_w") or 0.0)

class EVEnergyNeedSensor(_BasePlan):
    _attr_icon = "mdi:battery-clock"
    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_ev_need_kwh_{self._entry_id}"
    @property
    def native_value(self):
        cap = self._m(M_EV_BATT_KWH, 75.0)
        cur = self._m(M_EV_CURRENT_SOC, 40.0) / 100.0
        tgt = self._m(M_EV_TARGET_SOC, 80.0) / 100.0
        need = max(0.0, (tgt - cur) * cap)
        return round(need, 2)

class PVSurplusNowSensor(_BasePlan):
    _attr_icon = "mdi:solar-power"
    _attr_native_unit_of_measurement = "kW"
    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_pv_surplus_kw_{self._entry_id}"
    @property
    def native_value(self):
        surplus_w = max(0.0, self._pv_now_w() - self._house_w())
        return round(surplus_w / 1000.0, 2)

class EVChargeTimePVOnlySensor(_BasePlan):
    _attr_icon = "mdi:timer-outline"
    _attr_native_unit_of_measurement = "h"
    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_ev_time_pv_only_h_{self._entry_id}"
    @property
    def native_value(self):
        need = EVEnergyNeedSensor(self.coordinator, self._entry_id, "tmp").native_value or 0.0
        surplus_kw = PVSurplusNowSensor(self.coordinator, self._entry_id, "tmp").native_value or 0.0
        phases = int(self._m(M_EVSE_PHASES, 3.0))
        volt = float(self._m(M_EVSE_VOLTAGE, 230.0))
        max_a = float(self._m(M_EVSE_MAX_A, 16.0))
        evse_max_kw = (phases * volt * max_a) / 1000.0
        eff_kw = min(float(surplus_kw), float(evse_max_kw))
        if eff_kw > 0:
            return round(need / eff_kw, 2)
        return None

class HomeBattAvailableSensor(_BasePlan):
    _attr_icon = "mdi:battery-home"
    _attr_native_unit_of_measurement = "kWh"
    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_home_batt_avail_kwh_{self._entry_id}"
    @property
    def native_value(self):
        cap = self._m(M_HOME_BATT_CAP_KWH, 30.0)
        floor = self._m(M_HOME_BATT_SOC_FLOOR, 10.0)
        soc_ent = self.coordinator._get_cfg("batt_soc_entity", "")
        try:
            soc = float(str(self.coordinator.hass.states.get(soc_ent).state).replace(",", "."))
        except Exception:
            soc = 0.0
        usable = max(0.0, (soc - floor) / 100.0)
        return round(max(0.0, usable * cap), 2)

class BattNeededTo80Sensor(_BasePlan):
    _attr_icon = "mdi:battery-80"
    _attr_native_unit_of_measurement = "kWh"
    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_batt_needed_80_kwh_{self._entry_id}"
    @property
    def native_value(self):
        cap = self._m(M_EV_BATT_KWH, 75.0)
        cur = self._m(M_EV_CURRENT_SOC, 40.0) / 100.0
        need = max(0.0, 0.80 - cur) * cap
        avail = HomeBattAvailableSensor(self.coordinator, self._entry_id, "tmp").native_value or 0.0
        return round(min(need, float(avail)), 2)

class BattNeededTo100Sensor(_BasePlan):
    _attr_icon = "mdi:battery"
    _attr_native_unit_of_measurement = "kWh"
    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_batt_needed_100_kwh_{self._entry_id}"
    @property
    def native_value(self):
        cap = self._m(M_EV_BATT_KWH, 75.0)
        cur = self._m(M_EV_CURRENT_SOC, 40.0) / 100.0
        need = max(0.0, 1.0 - cur) * cap
        avail = HomeBattAvailableSensor(self.coordinator, self._entry_id, "tmp").native_value or 0.0
        return round(min(need, float(avail)), 2)

class EDDiagnosticsSensor(CoordinatorEntity, SensorEntity):
    _attr_icon = "mdi:information-outline"
    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_diagnostics_{self.coordinator.entry_id}"
    @property
    def name(self) -> str:
        return "ED Diagnostics"
    @property
    def native_value(self):
        return self.coordinator.data.get("diag_status", "ok")
    @property
    def extra_state_attributes(self):
        return self.coordinator.data.get("diag_attrs", {})

async def async_setup_entry(hass, entry, async_add_entities):
    st = hass.data[DOMAIN][entry.entry_id]
    coordinator = st["coordinator"]
    new_entities = [
        EVEnergyNeedSensor(coordinator, entry.entry_id, "EV Energibehov (till mål)", "kWh", "mdi:battery-clock"),
        PVSurplusNowSensor(coordinator, entry.entry_id, "PV-överskott nu", "kW", "mdi:solar-power"),
        EVChargeTimePVOnlySensor(coordinator, entry.entry_id, "EV Laddtid PV-only", "h", "mdi:timer-outline"),
        HomeBattAvailableSensor(coordinator, entry.entry_id, "Hemmabatteri energi tillgänglig", "kWh", "mdi:battery-home"),
        BattNeededTo80Sensor(coordinator, entry.entry_id, "Batterienergi som krävs till 80%", "kWh", "mdi:battery-80"),
        BattNeededTo100Sensor(coordinator, entry.entry_id, "Batterienergi som krävs till 100%", "kWh", "mdi:battery"),
        EDDiagnosticsSensor(coordinator),
    ]
    async_add_entities(new_entities, True)
