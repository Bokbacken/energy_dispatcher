"""
ForecastSolarProvider

Hämtar prognos från Forecast.Solar och konverterar till list[ForecastPoint].
Stödjer 1–2 plan i MVP. Horizon kan anges som CSV. API-key valfri.
Implementerar caching för att undvika för många API-anrop.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Dict
from urllib.parse import quote

import async_timeout
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .models import ForecastPoint
from .manual_forecast_engine import ManualForecastEngine, detect_weather_capabilities

_LOGGER = logging.getLogger(__name__)

FS_BASE = "https://api.forecast.solar"

# Cache duration in minutes - how long to keep cached data before refetching
CACHE_DURATION_MINUTES = 30

# Class-level cache shared across all instances
# Key: URL, Value: (timestamp, raw_points, compensated_points)
_FORECAST_CACHE: Dict[str, Tuple[datetime, List[ForecastPoint], List[ForecastPoint]]] = {}


def _az_to_api(az: str | int) -> int:
    """
    Forecast.Solar använder -180…180 där 0=söder, -90=öst, 90=väst.
    Du kan ange "S","E","W","N" eller gradtal direkt.
    """
    if isinstance(az, int):
        return az
    if isinstance(az, str):
        a = az.strip().upper()
        if a == "S":
            return 0
        if a == "E":
            return -90
        if a == "W":
            return 90
        if a == "N":
            return 180
    return 0


class ForecastSolarProvider:
    def __init__(
        self,
        hass,
        lat: float,
        lon: float,
        planes_json: str,
        apikey: Optional[str] = None,
        horizon_csv: Optional[str] = None,
        weather_entity: Optional[str] = None,
        cloud_0_factor: int = 250,
        cloud_100_factor: int = 20,
        forecast_source: str = "forecast_solar",
        manual_step_minutes: int = 15,
        manual_diffuse_svf: Optional[float] = None,
        manual_temp_coeff: float = -0.38,
        manual_inverter_ac_cap: Optional[float] = None,
        manual_calibration_enabled: bool = False,
    ):
        self.hass = hass
        self.lat = lat
        self.lon = lon
        self.apikey = apikey or ""
        self.horizon_csv = horizon_csv
        self.weather_entity = weather_entity or ""
        self.cloud_0_factor = cloud_0_factor
        self.cloud_100_factor = cloud_100_factor
        self.forecast_source = forecast_source
        
        try:
            self.planes = json.loads(planes_json)
            if not isinstance(self.planes, list):
                raise ValueError("planes_json måste vara en JSON-lista")
        except Exception as e:  # noqa: BLE001
            _LOGGER.exception("Kunde inte parsa fs_planes: %s", e)
            self.planes = [{"dec": 37, "az": 0, "kwp": 5.67}]
        
        # Initialize manual forecast engine if selected
        self.manual_engine = None
        if forecast_source == "manual_physics":
            _LOGGER.info("Initializing manual physics forecast engine (weather_entity=%s)", weather_entity)
            self.manual_engine = ManualForecastEngine(
                hass=hass,
                lat=lat,
                lon=lon,
                planes_json=planes_json,
                horizon_csv=horizon_csv,
                weather_entity=weather_entity,
                step_minutes=manual_step_minutes,
                diffuse_svf=manual_diffuse_svf,
                temp_coeff_pct_per_c=manual_temp_coeff,
                inverter_ac_kw_cap=manual_inverter_ac_cap,
                calibration_enabled=manual_calibration_enabled,
            )
        else:
            _LOGGER.info("Using Forecast.Solar forecast engine (apikey=%s)", "***" if apikey else "none")

    def _build_url(self) -> str:
        parts = []
        for p in self.planes[:2]:  # stöd 1–2 plan
            dec = int(p.get("dec", 37))
            az = _az_to_api(p.get("az", 0))
            kwp = float(p.get("kwp", 5.0))
            parts += [str(dec), str(az), str(kwp)]
        if self.apikey:
            url = f"{FS_BASE}/{quote(self.apikey)}/estimate/{self.lat}/{self.lon}/" + "/".join(parts)
        else:
            url = f"{FS_BASE}/estimate/{self.lat}/{self.lon}/" + "/".join(parts)
        if self.horizon_csv:
            url += f"?horizon={quote(self.horizon_csv)}"
        return url

    async def async_fetch_watts(self) -> Tuple[List[ForecastPoint], List[ForecastPoint]]:
        """
        Hämtar result.watts och returnerar tuple av (raw, compensated) list[ForecastPoint].
        Tidsstämplar sätts till lokal timezone (HA:s DEFAULT_TIME_ZONE).
        
        Implementerar caching med 30 minuters livstid för att undvika för många API-anrop.
        
        If forecast_source is "manual_physics", uses manual forecast engine instead.
        """
        # Use manual forecast engine if selected
        if self.forecast_source == "manual_physics":
            if self.manual_engine:
                _LOGGER.debug("Using manual physics forecast engine")
                raw = await self.manual_engine.async_compute_forecast()
                # For manual engine, raw and compensated are the same
                # (physics already accounts for conditions)
                return raw, raw
            else:
                _LOGGER.warning(
                    "Forecast source is 'manual_physics' but manual engine is not initialized. "
                    "Falling back to Forecast.Solar. Check weather_entity configuration."
                )
        
        # Otherwise use Forecast.Solar
        _LOGGER.debug("Using Forecast.Solar forecast engine")
        url = self._build_url()
        now = dt_util.now()
        
        # Check if we have a valid cached result
        if url in _FORECAST_CACHE:
            cache_time, cached_raw, cached_compensated = _FORECAST_CACHE[url]
            age_minutes = (now - cache_time).total_seconds() / 60.0
            
            if age_minutes < CACHE_DURATION_MINUTES:
                _LOGGER.debug(
                    "Forecast.Solar: Using cached data (age: %.1f minutes, %d points)",
                    age_minutes,
                    len(cached_raw)
                )
                # Re-apply cloud compensation in case weather has changed
                # but use the same raw forecast data
                compensated = await self._apply_cloud_compensation(cached_raw)
                return cached_raw, compensated
            else:
                _LOGGER.debug(
                    "Forecast.Solar: Cache expired (age: %.1f minutes), fetching new data",
                    age_minutes
                )
        else:
            _LOGGER.debug("Forecast.Solar: No cached data, fetching from API")

        # Fetch from API
        _LOGGER.debug("Forecast.Solar URL: %s", url)
        session = async_get_clientsession(self.hass)
        try:
            with async_timeout.timeout(20):
                resp = await session.get(url)
                if resp.status != 200:
                    text = await resp.text()
                    _LOGGER.warning("Forecast.Solar status=%s text=%s", resp.status, text)
                    # Return cached data if available, even if expired
                    if url in _FORECAST_CACHE:
                        _LOGGER.info("Forecast.Solar: API error, using stale cache")
                        _, cached_raw, cached_compensated = _FORECAST_CACHE[url]
                        return cached_raw, cached_compensated
                    return [], []
                data = await resp.json()
        except Exception as e:  # noqa: BLE001
            _LOGGER.exception("Kunde inte hämta Forecast.Solar: %s", e)
            # Return cached data if available, even if expired
            if url in _FORECAST_CACHE:
                _LOGGER.info("Forecast.Solar: Exception, using stale cache")
                _, cached_raw, cached_compensated = _FORECAST_CACHE[url]
                return cached_raw, cached_compensated
            return [], []

        result = data.get("result") or {}
        watts_map = result.get("watts") or {}
        raw: List[ForecastPoint] = []
        for ts, w in watts_map.items():
            # ex: "2022-10-12 08:00:00" i lokal tid
            try:
                dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                # gör tz-aware i HA:s lokala timezone
                dt = dt.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
                raw.append(ForecastPoint(time=dt, watts=float(w)))
            except Exception:
                continue

        _LOGGER.info("Forecast.Solar: Fetched fresh data from API, parsed %s raw points", len(raw))
        
        # Apply cloud compensation if weather entity is configured
        compensated = await self._apply_cloud_compensation(raw)
        
        _LOGGER.debug("Forecast.Solar: parsed %s compensated points", len(compensated))
        
        # Store in cache
        _FORECAST_CACHE[url] = (now, raw, compensated)
        
        return raw, compensated

    async def _get_hourly_weather_forecast(self) -> Dict[datetime, Dict[str, float]]:
        """
        Get hourly weather forecast data from weather entity.
        
        Returns:
            Dict mapping datetime to weather data dict with keys like 'cloud_coverage', 'temperature', etc.
        """
        if not self.weather_entity:
            return {}
        
        try:
            # Call weather.get_forecasts service to get hourly forecast
            response = await self.hass.services.async_call(
                "weather",
                "get_forecasts",
                {
                    "entity_id": self.weather_entity,
                    "type": "hourly",
                },
                blocking=True,
                return_response=True,
            )
            
            if not response or self.weather_entity not in response:
                _LOGGER.debug("No forecast data returned from weather service for %s", self.weather_entity)
                return {}
            
            forecast_data = response[self.weather_entity].get("forecast", [])
            if not forecast_data:
                _LOGGER.debug("Empty forecast data from weather service")
                return {}
            
            # Build a dict mapping datetime to weather data
            forecast_dict = {}
            for entry in forecast_data:
                if "datetime" in entry:
                    try:
                        # Parse datetime string (ISO 8601 format)
                        dt_str = entry["datetime"]
                        if isinstance(dt_str, str):
                            # Parse ISO format datetime
                            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                            # Convert to local timezone
                            dt = dt.astimezone(dt_util.DEFAULT_TIME_ZONE)
                        else:
                            dt = dt_str
                        
                        # Store the weather data
                        forecast_dict[dt] = entry
                    except (ValueError, TypeError) as e:
                        _LOGGER.debug("Failed to parse datetime from forecast entry: %s", e)
                        continue
            
            _LOGGER.debug("Retrieved %d hourly forecast points from weather service", len(forecast_dict))
            return forecast_dict
            
        except Exception as e:
            _LOGGER.debug("Failed to get hourly forecast from weather service: %s", e)
            return {}
    
    async def _apply_cloud_compensation(self, raw: List[ForecastPoint]) -> List[ForecastPoint]:
        """
        Apply cloud compensation to raw forecast based on weather entity hourly forecast.
        If no weather entity is configured or hourly forecast is unavailable, falls back to current state.
        """
        if not self.weather_entity or not raw:
            return list(raw)
        
        # Try to get hourly forecast data first
        hourly_forecast = await self._get_hourly_weather_forecast()
        
        if not hourly_forecast:
            # Fallback to current state if hourly forecast is not available
            _LOGGER.debug("Hourly forecast not available, falling back to current state")
            state = self.hass.states.get(self.weather_entity)
            if not state:
                _LOGGER.debug("Weather entity %s not found, returning raw forecast", self.weather_entity)
                return list(raw)
            
            attrs = state.attributes
            cloudiness = None
            
            # Try to get cloudiness from various possible attribute names
            for key in ["cloudiness", "cloud_coverage", "cloud_cover", "cloud"]:
                if key in attrs:
                    try:
                        cloudiness = float(attrs[key])
                        break
                    except (ValueError, TypeError):
                        continue
            
            if cloudiness is None:
                _LOGGER.debug("No cloudiness data in weather entity %s, returning raw forecast", self.weather_entity)
                return list(raw)
            
            # Ensure cloudiness is in range 0-100
            cloudiness = max(0.0, min(100.0, cloudiness))
            
            # Calculate compensation factor
            factor_percent = self.cloud_0_factor - (cloudiness / 100.0) * (self.cloud_0_factor - self.cloud_100_factor)
            factor = factor_percent / 100.0
            
            _LOGGER.debug("Cloud compensation (current state): cloudiness=%.1f%%, factor=%.2f", cloudiness, factor)
            
            # Apply same factor to all forecast points
            compensated = [
                ForecastPoint(time=point.time, watts=point.watts * factor)
                for point in raw
            ]
            
            return compensated
        
        # Use hourly forecast data to apply time-varying compensation
        _LOGGER.debug("Using hourly forecast data for cloud compensation")
        compensated = []
        
        for point in raw:
            # Find the closest forecast time (within 1 hour)
            closest_forecast = None
            min_diff = timedelta(hours=2)  # Search within 2 hours
            
            for forecast_time in hourly_forecast.keys():
                diff = abs(point.time - forecast_time)
                if diff < min_diff:
                    min_diff = diff
                    closest_forecast = forecast_time
            
            if closest_forecast is None:
                # No close forecast found, use raw value
                compensated.append(point)
                continue
            
            # Get cloudiness from forecast
            forecast_entry = hourly_forecast[closest_forecast]
            cloudiness = None
            
            # Try to get cloudiness from various possible attribute names
            for key in ["cloudiness", "cloud_coverage", "cloud_cover", "cloud"]:
                if key in forecast_entry:
                    try:
                        cloudiness = float(forecast_entry[key])
                        break
                    except (ValueError, TypeError):
                        continue
            
            if cloudiness is None:
                # No cloudiness in this forecast entry, use raw value
                compensated.append(point)
                continue
            
            # Ensure cloudiness is in range 0-100
            cloudiness = max(0.0, min(100.0, cloudiness))
            
            # Calculate compensation factor
            factor_percent = self.cloud_0_factor - (cloudiness / 100.0) * (self.cloud_0_factor - self.cloud_100_factor)
            factor = factor_percent / 100.0
            
            # Apply factor to this point
            compensated.append(ForecastPoint(time=point.time, watts=point.watts * factor))
        
        _LOGGER.debug("Cloud compensation complete using hourly forecast data")
        return compensated
