from __future__ import annotations

from typing import Any, Optional

from .forecast_provider import ForecastSolarProvider

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    st = hass.data[DOMAIN][entry.entry_id]
    coordinator = st["coordinator"]
    # Merge data and options to get the current configuration
    config = {**entry.data, **(entry.options or {})}

    entities = [
        EnrichedPriceSensor(coordinator, entry.entry_id),
        HouseBaselineSensor(coordinator, entry.entry_id),
        BaselineNightSensor(coordinator, entry.entry_id),
        BaselineDaySensor(coordinator, entry.entry_id),
        BaselineEveningSensor(coordinator, entry.entry_id),
        BatteryRuntimeSensor(coordinator, entry.entry_id),
        BatteryCostSensor(coordinator, entry.entry_id),
        BatteryVsGridDeltaSensor(coordinator, entry.entry_id),
        BatteryChargingStateSensor(coordinator, entry.entry_id),
        BatteryPowerFlowSensor(coordinator, entry.entry_id),
        SolarPowerNowSensor(coordinator, entry.entry_id),
        SolarEnergyTodaySensor(coordinator, entry.entry_id),
        SolarEnergyTomorrowSensor(coordinator, entry.entry_id),
        PVPowerNowSensor(coordinator, entry.entry_id),
        PVEnergyTodaySensor(coordinator, entry.entry_id),
        SolarDelta15mSensor(coordinator, entry.entry_id),
        EVTimeUntilChargeSensor(coordinator, entry.entry_id),
        EVChargeReasonSensor(coordinator, entry.entry_id),
        EVChargingSessionSensor(coordinator, entry.entry_id),
        BattTimeUntilChargeSensor(coordinator, entry.entry_id),
        BattChargeReasonSensor(coordinator, entry.entry_id),
        # Cost strategy sensors
        CostLevelSensor(coordinator, entry.entry_id),
        BatteryReserveSensor(coordinator, entry.entry_id),
        NextHighCostWindowSensor(coordinator, entry.entry_id),
    ]
    
    # Add forecast sensors (raw and cloud compensated)
    forecast_provider = ForecastSolarProvider(
        hass=hass,
        lat=config["fs_lat"],
        lon=config["fs_lon"],
        planes_json=config["fs_planes"],
        apikey=config.get("fs_apikey"),
        horizon_csv=config.get("fs_horizon"),
        weather_entity=config.get("weather_entity"),
        cloud_0_factor=config.get("cloud_0_factor", 250),
        cloud_100_factor=config.get("cloud_100_factor", 20),
    )
    entities.extend([
        SolarForecastRawSensor(hass, forecast_provider),
        SolarForecastCompensatedSensor(hass, forecast_provider),
    ])
    
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


class BaselineNightSensor(BaseEDSensor):
    _attr_name = "House Load Baseline Night"
    _attr_native_unit_of_measurement = "W"
    _attr_icon = "mdi:weather-night"
    _attr_device_class = "power"
    _attr_state_class = "measurement"

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_baseline_night_w_{self._entry_id}"

    @property
    def native_value(self):
        return self.coordinator.data.get("baseline_night_w")

    @property
    def extra_state_attributes(self):
        return {
            "time_period": "00:00-07:59",
        }


class BaselineDaySensor(BaseEDSensor):
    _attr_name = "House Load Baseline Day"
    _attr_native_unit_of_measurement = "W"
    _attr_icon = "mdi:white-balance-sunny"
    _attr_device_class = "power"
    _attr_state_class = "measurement"

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_baseline_day_w_{self._entry_id}"

    @property
    def native_value(self):
        return self.coordinator.data.get("baseline_day_w")

    @property
    def extra_state_attributes(self):
        return {
            "time_period": "08:00-15:59",
        }


class BaselineEveningSensor(BaseEDSensor):
    _attr_name = "House Load Baseline Evening"
    _attr_native_unit_of_measurement = "W"
    _attr_icon = "mdi:weather-sunset"
    _attr_device_class = "power"
    _attr_state_class = "measurement"

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_baseline_evening_w_{self._entry_id}"

    @property
    def native_value(self):
        return self.coordinator.data.get("baseline_evening_w")

    @property
    def extra_state_attributes(self):
        return {
            "time_period": "16:00-23:59",
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
        bec = store.get("bec")
        if bec:
            return float(bec.wace)
        # Fallback to legacy storage
        return float(store.get("wace", 0.0))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        store = self.coordinator.hass.data.get(DOMAIN, {}).get(self._entry_id, {})
        bec = store.get("bec")
        if bec:
            history_summary = bec.get_history_summary()
            return {
                "total_energy_kwh": float(bec.energy_kwh),
                "total_cost_sek": float(bec.get_total_cost()),
                "battery_soc_percent": float(bec.get_soc()),
                "battery_capacity_kwh": float(bec.capacity_kwh),
                "history_events": history_summary.get("total_events", 0),
                "history_charge_events": history_summary.get("charge_events", 0),
                "history_discharge_events": history_summary.get("discharge_events", 0),
                "history_total_charged_kwh": history_summary.get("total_charged_kwh", 0.0),
                "history_total_discharged_kwh": history_summary.get("total_discharged_kwh", 0.0),
                "history_oldest_event": history_summary.get("oldest_event"),
                "history_newest_event": history_summary.get("newest_event"),
            }
        # Fallback to legacy storage
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


class EVChargingSessionSensor(BaseEDSensor):
    _attr_name = "EV Charging Session"
    _attr_icon = "mdi:ev-station"

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_ev_charging_session_{self._entry_id}"

    @property
    def native_value(self):
        """Return session status."""
        dispatcher = self.hass.data[DOMAIN][self._entry_id].get("dispatcher")
        if not dispatcher:
            return "unknown"
        
        session_info = dispatcher.get_charging_session_info()
        return "active" if session_info["active"] else "idle"

    @property
    def extra_state_attributes(self):
        """Return session details as attributes."""
        dispatcher = self.hass.data[DOMAIN][self._entry_id].get("dispatcher")
        if not dispatcher:
            return {}
        
        session_info = dispatcher.get_charging_session_info()
        attrs = {
            "active": session_info["active"],
        }
        
        if session_info["active"]:
            attrs["start_soc"] = session_info["start_soc"]
            attrs["target_soc"] = session_info["target_soc"]
            if session_info["start_energy"] is not None:
                attrs["start_energy_kwh"] = round(session_info["start_energy"], 2)
        
        return attrs


class BatteryChargingStateSensor(BaseEDSensor):
    _attr_name = "Battery Charging State"
    _attr_icon = "mdi:battery-charging"

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_batt_charging_state_{self._entry_id}"

    def _get_normalized_battery_power(self):
        """Get battery power normalized to standard convention (positive=charging)."""
        from .const import CONF_BATT_POWER_ENTITY, CONF_BATT_POWER_INVERT_SIGN
        
        batt_power_entity = self.coordinator._get_cfg(CONF_BATT_POWER_ENTITY, "")
        if not batt_power_entity:
            return None
        
        state = self.coordinator.hass.states.get(batt_power_entity)
        if not state or state.state in (None, "", "unknown", "unavailable"):
            return None
        
        try:
            power = float(state.state)
            # Apply sign inversion if configured (for Huawei-style sensors)
            invert_sign = self.coordinator._get_cfg(CONF_BATT_POWER_INVERT_SIGN, False)
            if invert_sign:
                power = -power
            return power
        except (ValueError, TypeError):
            return None
    
    @property
    def native_value(self):
        """Return battery charging state: charging, discharging, or idle."""
        power = self._get_normalized_battery_power()
        if power is None:
            return "unknown"
        
        # Standard convention: positive = charging, negative = discharging
        if power > 50:  # Charging threshold: 50W
            return "charging"
        elif power < -50:  # Discharging threshold: 50W
            return "discharging"
        else:
            return "idle"

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        attrs = {}
        power = self._get_normalized_battery_power()
        if power is not None:
            attrs["battery_power_w"] = power
        return attrs


class BatteryPowerFlowSensor(BaseEDSensor):
    _attr_name = "Battery Power Flow"
    _attr_native_unit_of_measurement = "W"
    _attr_icon = "mdi:transmission-tower"
    _attr_device_class = "power"
    _attr_state_class = "measurement"

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_batt_power_flow_{self._entry_id}"

    def _get_normalized_battery_power(self):
        """Get battery power normalized to standard convention (positive=charging)."""
        from .const import CONF_BATT_POWER_ENTITY, CONF_BATT_POWER_INVERT_SIGN
        
        batt_power_entity = self.coordinator._get_cfg(CONF_BATT_POWER_ENTITY, "")
        if not batt_power_entity:
            return None
        
        state = self.coordinator.hass.states.get(batt_power_entity)
        if not state or state.state in (None, "", "unknown", "unavailable"):
            return None
        
        try:
            power = float(state.state)
            # Apply sign inversion if configured (for Huawei-style sensors)
            invert_sign = self.coordinator._get_cfg(CONF_BATT_POWER_INVERT_SIGN, False)
            if invert_sign:
                power = -power
            return power
        except (ValueError, TypeError):
            return None
    
    @property
    def native_value(self):
        """Return battery power flow (positive=charging, negative=discharging)."""
        return self._get_normalized_battery_power()

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        store = self.coordinator.hass.data.get(DOMAIN, {}).get(self._entry_id, {})
        bec = store.get("bec")
        
        attrs = {}
        if bec:
            attrs["battery_soc_percent"] = float(bec.get_soc())
            attrs["battery_energy_kwh"] = float(bec.energy_kwh)
            attrs["battery_capacity_kwh"] = float(bec.capacity_kwh)
        
        return attrs


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


class SolarForecastRawSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_unique_id = "solar_forecast_raw"

    def __init__(self, hass: HomeAssistant, forecast_provider: ForecastSolarProvider):
        self.hass = hass
        self._forecast_provider = forecast_provider
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "energy_dispatcher")},
            name="Energy Dispatcher",
            manufacturer="Bokbacken",
        )
        self._state = None
        self._attr_extra_state_attributes = {}

    @property
    def name(self):
        return "Solar Forecast (Raw)"

    @property
    def state(self):
        return self._state

    async def async_update(self):
        raw, _ = await self._forecast_provider.async_fetch_watts()
        self._state = sum(point.watts for point in raw)
        self._attr_extra_state_attributes = {
            "forecast": [(point.time.isoformat(), point.watts) for point in raw]
        }


class SolarForecastCompensatedSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_unique_id = "solar_forecast_compensated"

    def __init__(self, hass: HomeAssistant, forecast_provider: ForecastSolarProvider):
        self.hass = hass
        self._forecast_provider = forecast_provider
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "energy_dispatcher")},
            name="Energy Dispatcher",
            manufacturer="Bokbacken",
        )
        self._state = None
        self._attr_extra_state_attributes = {}

    @property
    def name(self):
        return "Solar Forecast (Cloud Compensated)"

    @property
    def state(self):
        return self._state

    async def async_update(self):
        _, compensated = await self._forecast_provider.async_fetch_watts()
        self._state = sum(point.watts for point in compensated)
        self._attr_extra_state_attributes = {
            "forecast": [(point.time.isoformat(), point.watts) for point in compensated]
        }


class CostLevelSensor(BaseEDSensor):
    """Sensor showing current price cost level (cheap/medium/high)."""
    _attr_name = "Cost Level"
    _attr_icon = "mdi:tag-multiple"

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_cost_level_{self._entry_id}"

    @property
    def native_value(self) -> Optional[str]:
        return self.coordinator.data.get("cost_level")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        cost_summary = self.coordinator.data.get("cost_summary", {})
        return {
            "cheap_threshold_sek_per_kwh": cost_summary.get("cheap_threshold"),
            "high_threshold_sek_per_kwh": cost_summary.get("high_threshold"),
            "cheap_hours_next_24h": cost_summary.get("cheap_hours"),
            "medium_hours_next_24h": cost_summary.get("medium_hours"),
            "high_hours_next_24h": cost_summary.get("high_hours"),
            "avg_price_next_24h": cost_summary.get("avg_price"),
            "min_price_next_24h": cost_summary.get("min_price"),
            "max_price_next_24h": cost_summary.get("max_price"),
        }


class BatteryReserveSensor(BaseEDSensor):
    """Sensor showing recommended battery reserve SOC based on upcoming prices."""
    _attr_name = "Battery Reserve Recommendation"
    _attr_native_unit_of_measurement = "%"
    _attr_icon = "mdi:battery-alert"

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_battery_reserve_{self._entry_id}"

    @property
    def native_value(self) -> Optional[float]:
        reserve = self.coordinator.data.get("battery_reserve_recommendation")
        if reserve is not None:
            return round(reserve, 1)
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "description": "Recommended minimum battery SOC to maintain for upcoming high-cost periods"
        }


class NextHighCostWindowSensor(BaseEDSensor):
    """Sensor showing the next high-cost time window."""
    _attr_name = "Next High Cost Window"
    _attr_icon = "mdi:clock-alert"

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_next_high_cost_window_{self._entry_id}"

    @property
    def native_value(self) -> Optional[str]:
        windows = self.coordinator.data.get("high_cost_windows", [])
        if windows and len(windows) > 0:
            start, end = windows[0]
            return start.strftime("%H:%M")
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        windows = self.coordinator.data.get("high_cost_windows", [])
        attr = {"high_cost_windows_count": len(windows)}
        
        if windows:
            # Add all windows as attributes
            windows_list = []
            for i, (start, end) in enumerate(windows):
                windows_list.append({
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "start_time": start.strftime("%H:%M"),
                    "end_time": end.strftime("%H:%M"),
                    "duration_hours": (end - start).total_seconds() / 3600
                })
            attr["windows"] = windows_list
            
            # Add next window details to state attributes
            if len(windows) > 0:
                start, end = windows[0]
                attr["next_window_start"] = start.isoformat()
                attr["next_window_end"] = end.isoformat()
                attr["next_window_duration_hours"] = round((end - start).total_seconds() / 3600, 1)
        
        return attr
