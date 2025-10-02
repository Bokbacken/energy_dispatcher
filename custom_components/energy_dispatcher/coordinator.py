"""Coordinator som samlar in data och bygger underlag."""
from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any, Optional

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .adapters.base import BatteryAdapterBase, EVAdapterBase
from .adapters.ev_manual import ManualEVAdapter
from .adapters.evse_generic import GenericEVSEAdapter
from .adapters.huawei import HuaweiLunaBatteryAdapter
from .bec import PriceAndCostHelper
from .const import (
    ATTR_BATTERY_STATE,
    ATTR_EV_STATE,
    ATTR_HOUSE_STATE,
    ATTR_PLAN,
    ATTR_PRICE_SCHEDULE,
    ATTR_SOLAR_FORECAST,
    CONF_BATTERY_SETTINGS,
    CONF_ENABLE_AUTO_DISPATCH,
    CONF_EV_SETTINGS,
    CONF_FORECAST_API_KEY,
    CONF_FORECAST_HORIZON,
    CONF_FORECAST_LAT,
    CONF_FORECAST_LON,
    CONF_PV_ARRAYS,
    CONF_PRICE_API_TOKEN,
    CONF_PRICE_AREA,
    CONF_PRICE_CURRENCY,
    CONF_PRICE_SENSOR,
    CONF_SCAN_INTERVAL,
    DOMAIN,
)
from .models import (
    BatterySettings,
    BatteryState,
    EnergyDispatcherConfig,
    EnergyDispatcherData,
    EnergyPlan,
    EVSettings,
    EVState,
    ForecastSettings,
    HouseSettings,
    NordpoolSettings,
    PVArrayConfig,
    PricePoint,
    SolarForecastPoint,
)
from .planner import EnergyPlanner
from . import helpers

_LOGGER = logging.getLogger(__name__)


class ForecastSolarClient:
    """Minimal klient för Forecast.Solar API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        api_key: str,
        latitude: float,
        longitude: float,
        pv_arrays: list[PVArrayConfig],
        horizon: list[int],
    ) -> None:
        self.session = session
        self.api_key = api_key
        self.lat = latitude
        self.lon = longitude
        self.pv_arrays = pv_arrays
        self.horizon = horizon

    async def async_fetch_forecast(self) -> list[SolarForecastPoint]:
        """Hämta prognos genom att summera samtliga strängar."""
        tasks = [
            self._fetch_for_array(array)
            for array in self.pv_arrays
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        combined: dict[datetime, dict[str, float]] = defaultdict(lambda: {
            "watts": 0.0,
            "watt_hours_period": 0.0,
            "watt_hours": 0.0,
        })
        for result in results:
            if isinstance(result, Exception):
                _LOGGER.error("Fel vid hämtning av solprognos: %s", result)
                continue
            for point in result:
                combined[point["timestamp"]]["watts"] += point["watts"]
                combined[point["timestamp"]]["watt_hours_period"] += point["watt_hours_period"]
                combined[point["timestamp"]]["watt_hours"] += point["watt_hours"]

        points: list[SolarForecastPoint] = []
        for timestamp in sorted(combined.keys()):
            row = combined[timestamp]
            points.append(
                SolarForecastPoint(
                    timestamp=timestamp,
                    watts=row["watts"],
                    watt_hours_period=row["watt_hours_period"],
                    cumulative_wh=row["watt_hours"],
                )
            )

        return points

    async def _fetch_for_array(self, array: PVArrayConfig) -> list[dict[str, float]]:
        """Hämta prognos för en PV-sträng."""
        # Forecast.Solar endpoint:
        # /api_key/estimate/{lat}/{lon}/{tilt}/{azimuth}/{kwp}
        # AZIMUTH använder bokstav (N, S, E, W) eller gradtal.
        azimuth = array.azimuth.upper()
        url = (
            "https://api.forecast.solar/"
            f"{self.api_key}/estimate/"
            f"{self.lat}/{self.lon}/"
            f"{array.tilt}/{azimuth}/{array.peak_power_kwp}"
        )
        if self.horizon:
            horizon_str = ",".join(str(h) for h in self.horizon)
            url += f"?horizon={horizon_str}"

        async with self.session.get(url, timeout=30) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise HomeAssistantError(
                    f"Forecast.Solar svarade {resp.status}: {text}"
                )
            data = await resp.json()

        results: list[dict[str, float]] = []
        for iso_ts, watts in data.get("result", {}).get("watts", {}).items():
            timestamp = datetime.fromisoformat(iso_ts).astimezone(UTC)
            period_wh = data["result"]["watt_hours_period"][iso_ts]
            cumulative = data["result"]["watt_hours"][iso_ts]
            results.append(
                {
                    "timestamp": timestamp,
                    "watts": float(watts),
                    "watt_hours_period": float(period_wh),
                    "watt_hours": float(cumulative),
                }
            )
        return results


class NordpoolPriceClient:
    """Klient för Nord Pools dataportal (per API-token) eller fallback till sensor."""

    def __init__(
        self,
        hass: HomeAssistant,
        session: aiohttp.ClientSession,
        settings: NordpoolSettings,
        fallback_sensor_entity_id: str | None,
    ) -> None:
        self.hass = hass
        self.session = session
        self.settings = settings
        self.fallback_sensor = fallback_sensor_entity_id

    async def async_fetch_prices(self) -> list[PricePoint]:
        """Försök hämta via API-token, annars via sensor."""
        if self.settings.api_token:
            try:
                return await self._fetch_via_api()
            except Exception as err:
                _LOGGER.warning("Nord Pool API misslyckades: %s", err)

        if self.fallback_sensor:
            return self._fetch_from_sensor()

        raise UpdateFailed("Inga prisdata tillgängliga (API eller sensor)")

    async def _fetch_via_api(self) -> list[PricePoint]:
        """Hämta prislista via Nord Pools dataportal API."""
        # OBS: API:et kräver giltigt token. Här används DayAheadPrices endpoint.
        area = self.settings.area.upper()
        url = f"https://dataportal-api.nordpoolgroup.com/api/DayAheadPrices/{area}"
        headers = {
            "Authorization": f"Bearer {self.settings.api_token}",
            "Accept": "application/json",
        }
        async with self.session.get(url, headers=headers, timeout=30) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise HomeAssistantError(
                    f"Nord Pool {resp.status}: {body}"
                )
            payload = await resp.json()

        prices = []
        for row in payload.get("data", []):
            start = datetime.fromisoformat(row["start"]).astimezone(UTC)
            end = datetime.fromisoformat(row["end"]).astimezone(UTC)
            price = float(row["price"])
            prices.append(
                PricePoint(
                    start=start,
                    end=end,
                    price=price / 1000,  # Nord Pool levererar i per MWh
                    is_predicted=row.get("isEstimated", False),
                )
            )
        return prices

    def _fetch_from_sensor(self) -> list[PricePoint]:
        """Hämta prisdata från en sensor-entity (förväntad HA Nord Pool integration)."""
        state = self.hass.states.get(self.fallback_sensor)
        if state is None:
            raise UpdateFailed(
                f"Pris-sensorn {self.fallback_sensor} hittades inte"
            )

        attrs = state.attributes
        raw_prices = attrs.get("today", []) + attrs.get("tomorrow", [])
        prices: list[PricePoint] = []
        tz = self.hass.config.time_zone

        for row in raw_prices:
            start = datetime.fromisoformat(row["start"]).astimezone(tz).astimezone(UTC)
            end = datetime.fromisoformat(row["end"]).astimezone(tz).astimezone(UTC)
            price = float(row["value"])
            prices.append(
                PricePoint(
                    start=start,
                    end=end,
                    price=price,
                    is_predicted=row.get("is_tomorrow", False),
                )
            )
        if not prices:
            raise UpdateFailed("Pris-sensorn gav ingen data")
        return prices


class EnergyDispatcherCoordinator(DataUpdateCoordinator[EnergyDispatcherData]):
    """Hanterar insamling av data och generering av plan."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.config = self._build_config(entry)
        self.session = aiohttp_client.async_get_clientsession(hass)

        update_interval = timedelta(
            seconds=entry.options.get(CONF_SCAN_INTERVAL, 300)
        )

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}-{entry.entry_id}",
            update_interval=update_interval,
        )

        self._forecast_client = ForecastSolarClient(
            self.session,
            self.config.forecast.api_key,
            self.config.forecast.latitude,
            self.config.forecast.longitude,
            self.config.forecast.pv_arrays,
            self.config.forecast.horizon,
        )
        self._price_client = NordpoolPriceClient(
            hass,
            self.session,
            self.config.prices,
            entry.options.get(CONF_PRICE_SENSOR),
        )
        self._battery_adapter = self._create_battery_adapter()
        self._ev_adapter = self._create_ev_adapter()
        self._price_helper = PriceAndCostHelper(self.config)

    def _build_config(self, entry: ConfigEntry) -> EnergyDispatcherConfig:
        """Översätt ConfigEntry till vår modell."""
        data = entry.data
        options = entry.options

        horizon_str = data.get(CONF_FORECAST_HORIZON) or helpers.get_default_horizon_string()
        horizon = [int(item.strip()) for item in horizon_str.split(",") if item.strip()]

        pv_json = json.loads(data[CONF_PV_ARRAYS])
        pv_arrays = [
            PVArrayConfig(
                label=item["label"],
                tilt=float(item["tilt"]),
                azimuth=item["azimuth"],
                peak_power_kwp=float(item["peak_power_kwp"]),
            )
            for item in pv_json
        ]

        forecast_settings = ForecastSettings(
            api_key=data[CONF_FORECAST_API_KEY],
            latitude=float(data[CONF_FORECAST_LAT]),
            longitude=float(data[CONF_FORECAST_LON]),
            horizon=horizon,
            pv_arrays=pv_arrays,
        )

        price_settings = NordpoolSettings(
            area=data[CONF_PRICE_AREA],
            currency=data[CONF_PRICE_CURRENCY],
            api_token=data.get(CONF_PRICE_API_TOKEN),
            price_sensor_entity_id=options.get(CONF_PRICE_SENSOR),
        )

        battery_settings = None
        if CONF_BATTERY_SETTINGS in data:
            b = data[CONF_BATTERY_SETTINGS]
            battery_settings = BatterySettings(
                adapter_type=b["adapter_type"],
                capacity_kwh=float(b["capacity_kwh"]),
                min_soc=float(b["min_soc"]),
                max_soc=float(b["max_soc"]),
                soc_sensor_entity_id=b["soc_sensor_entity_id"],
                power_sensor_entity_id=b.get("power_sensor_entity_id"),
                grid_import_sensor_entity_id=b.get("grid_import_sensor_entity_id"),
                force_charge_entity_id=b.get("force_charge_entity_id"),
                force_discharge_entity_id=b.get("force_discharge_entity_id"),
                charge_mode_select_entity_id=b.get("charge_mode_select_entity_id"),
                charge_current_number_entity_id=b.get("charge_current_number_entity_id"),
                supports_force_charge=b.get("supports_force_charge", False),
                supports_force_discharge=b.get("supports_force_discharge", False),
                power_sign_invert=b.get("power_sign_invert", False),
            )

        ev_settings = None
        if CONF_EV_SETTINGS in data:
            e = data[CONF_EV_SETTINGS]
            ev_settings = EVSettings(
                adapter_type=e["adapter_type"],
                capacity_kwh=float(e["capacity_kwh"]),
                default_target_soc=float(e["default_target_soc"]),
                min_ampere=float(e["min_ampere"]),
                max_ampere=float(e["max_ampere"]),
                default_ampere=float(e["default_ampere"]),
                soc_sensor_entity_id=e.get("soc_sensor_entity_id"),
                charger_switch_entity_id=e.get("charger_switch_entity_id"),
                charger_pause_switch_entity_id=e.get("charger_pause_switch_entity_id"),
                current_number_entity_id=e.get("current_number_entity_id"),
                manual_departure_time=e.get("manual_departure_time"),
                manual_ready_by_time=e.get("manual_ready_by_time"),
                efficiency=float(e.get("efficiency", 0.9)),
                allow_manual_soc_entry=bool(e.get("allow_manual_soc_entry", True)),
            )

        house_settings_data = data["house_settings"]
        house_settings = HouseSettings(
            avg_consumption_sensor=house_settings_data.get("avg_consumption_sensor"),
            temperature_sensor=house_settings_data.get("temperature_sensor"),
            base_load_kw=float(house_settings_data.get("base_load_kw", 0.5)),
            hvac_load_sensor=house_settings_data.get("hvac_load_sensor"),
            dishwasher_load_kw=float(house_settings_data.get("dishwasher_load_kw", 1.5)),
            washer_load_kw=float(house_settings_data.get("washer_load_kw", 2.0)),
            dryer_load_kw=float(house_settings_data.get("dryer_load_kw", 2.2)),
            extra_manual_entities=house_settings_data.get("extra_manual_entities", []),
        )

        return EnergyDispatcherConfig(
            name=entry.data.get(CONF_NAME, "Energy Dispatcher"),
            forecast=forecast_settings,
            prices=price_settings,
            battery=battery_settings,
            ev=ev_settings,
            house=house_settings,
            scan_interval=timedelta(seconds=entry.options.get(CONF_SCAN_INTERVAL, 300)),
            auto_dispatch=entry.options.get(CONF_ENABLE_AUTO_DISPATCH, True),
        )

    def _create_battery_adapter(self) -> BatteryAdapterBase | None:
        settings = self.config.battery
        if not settings:
            return None

        if settings.adapter_type == "huawei":
            return HuaweiLunaBatteryAdapter(self.hass, settings)
        return BatteryAdapterBase.from_entity(self.hass, settings)

    def _create_ev_adapter(self) -> EVAdapterBase | None:
        settings = self.config.ev
        if not settings:
            return None

        if settings.adapter_type == "generic_evse":
            return GenericEVSEAdapter(self.hass, settings)
        return ManualEVAdapter(self.hass, settings)

    async def _async_update_data(self) -> EnergyDispatcherData:
        """Huvudmetod som DataUpdateCoordinator kör."""
        try:
            forecast, prices = await asyncio.gather(
                self._forecast_client.async_fetch_forecast(),
                self._price_client.async_fetch_prices(),
            )
        except Exception as err:
            raise UpdateFailed(f"Misslyckades hämta forecast/pris: {err}") from err

        battery_state = await self._async_get_battery_state()
        ev_state = await self._async_get_ev_state()
        house_state = await self._async_get_house_state()

        plan = EnergyPlan(
            generated_at=datetime.now(UTC),
            horizon_hours=48,
        )
        planner = EnergyPlanner()
        plan = planner.build_plan(
            config=self.config,
            forecast=forecast,
            price_points=prices,
            battery_state=battery_state,
            ev_state=ev_state,
            house_state=house_state,
            price_helper=self._price_helper,
        )

        return EnergyDispatcherData(
            forecast_points=forecast,
            price_points=prices,
            battery_state=battery_state,
            ev_state=ev_state,
            house_state=house_state,
            plan=plan,
        )

    async def _async_get_battery_state(self) -> BatteryState | None:
        if not self._battery_adapter:
            return None
        return await self._battery_adapter.async_get_state()

    async def _async_get_ev_state(self) -> EVState | None:
        if not self._ev_adapter:
            return None
        return await self._ev_adapter.async_get_state()

    async def _async_get_house_state(self):
        """Samla huset/lastdata."""
        return await self._price_helper.async_get_house_state(self.hass, self.entry)
