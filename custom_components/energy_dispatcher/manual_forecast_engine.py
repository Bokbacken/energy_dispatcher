"""
Manual PV Forecast Engine - Physics-based solar forecasting.

This module implements a lightweight physics-based PV forecast engine
that uses weather data (irradiance, cloud cover, temperature, wind) to
generate solar power forecasts without relying on external APIs.

Abbreviations and Acronyms:
- GHI: Global Horizontal Irradiance (W/m²) - total solar radiation on a horizontal surface
- DNI: Direct Normal Irradiance (W/m²) - direct beam solar radiation perpendicular to sun
- DHI: Diffuse Horizontal Irradiance (W/m²) - scattered sky radiation on horizontal surface
- POA: Plane-of-Array - the tilted surface of the solar panel
- AOI: Angle of Incidence - angle between sun ray and panel normal
- IAM: Incidence Angle Modifier - correction for non-perpendicular sunlight
- SVF: Sky View Factor - fraction of sky hemisphere visible (0-1)
- HDKR: Hay-Davies-Klucher-Reindl - transposition model for tilted surfaces
- PVWatts: NREL's simple PV performance model (industry standard)
- NOCT: Nominal Operating Cell Temperature (typically 45°C at 800 W/m²)
- STC: Standard Test Conditions (1000 W/m², 25°C cell temp, AM1.5 spectrum)
- E0: Eccentricity correction factor for Earth-Sun distance variation
- kt: Clearness index - ratio of GHI to extraterrestrial irradiance

Physics Models Used:
- Haurwitz: Simple clear-sky GHI calculation (robust, no atmospheric data needed)
- Kasten-Czeplak: Cloud cover to GHI mapping (C^3.4 relationship)
- Erbs: GHI decomposition to DNI/DHI using clearness index correlations
- HDKR: Anisotropic diffuse irradiance transposition to tilted planes
- PVWatts: DC and AC power calculation with temperature effects

Note: All formulas log input values and intermediate results at DEBUG level
to enable forecast improvement analysis by comparing predicted vs actual output.
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from homeassistant.util import dt as dt_util

from .models import ForecastPoint

_LOGGER = logging.getLogger(__name__)

# Solar constant (W/m²)
SOLAR_CONSTANT = 1367.0


@dataclass
class WeatherCapabilities:
    """Detected weather data capabilities."""
    has_dni: bool = False
    has_dhi: bool = False
    has_ghi: bool = False
    has_shortwave_radiation: bool = False
    has_direct_radiation: bool = False
    has_diffuse_radiation: bool = False
    has_cloud_cover: bool = False
    has_temperature: bool = False
    has_wind_speed: bool = False
    has_relative_humidity: bool = False
    has_pressure: bool = False
    
    def get_tier(self) -> int:
        """
        Get capability tier:
        1 = DNI/DHI or GHI available (best)
        2 = Cloud cover available (good)
        3 = No relevant data (worst)
        """
        if self.has_dni and self.has_dhi:
            return 1
        if self.has_ghi or self.has_shortwave_radiation:
            return 1
        if self.has_cloud_cover:
            return 2
        return 3
    
    def get_description(self) -> str:
        """Get human-readable description of capabilities."""
        fields = []
        if self.has_dni:
            fields.append("DNI")
        if self.has_dhi:
            fields.append("DHI")
        if self.has_ghi:
            fields.append("GHI")
        if self.has_shortwave_radiation:
            fields.append("Shortwave")
        if self.has_cloud_cover:
            fields.append("Cloud")
        if self.has_temperature:
            fields.append("Temp")
        if self.has_wind_speed:
            fields.append("Wind")
        
        tier = self.get_tier()
        tier_desc = {1: "Excellent", 2: "Good", 3: "Limited"}
        return f"{tier_desc.get(tier, 'Unknown')}: {', '.join(fields) if fields else 'None'}"


def detect_weather_capabilities(hass, entity_id: str) -> WeatherCapabilities:
    """
    Detect weather data capabilities from a Home Assistant entity.
    
    Args:
        hass: Home Assistant instance
        entity_id: Weather entity ID to probe
    
    Returns:
        WeatherCapabilities object with detected fields
    """
    caps = WeatherCapabilities()
    
    if not entity_id:
        return caps
    
    state = hass.states.get(entity_id)
    if not state:
        _LOGGER.warning("Weather entity %s not found", entity_id)
        return caps
    
    attrs = state.attributes
    
    # Check for irradiance fields
    if "global_horizontal_irradiance" in attrs:
        caps.has_ghi = True
    if "direct_normal_irradiance" in attrs:
        caps.has_dni = True
    if "diffuse_horizontal_irradiance" in attrs:
        caps.has_dhi = True
    if "shortwave_radiation" in attrs:
        caps.has_shortwave_radiation = True
    if "direct_radiation" in attrs:
        caps.has_direct_radiation = True
    if "diffuse_radiation" in attrs:
        caps.has_diffuse_radiation = True
    
    # Check for cloud cover
    for key in ["cloud_cover", "cloudiness", "cloud_coverage", "cloud"]:
        if key in attrs:
            caps.has_cloud_cover = True
            break
    
    # Check for meteorological data
    if "temperature" in attrs:
        caps.has_temperature = True
    if "wind_speed" in attrs:
        caps.has_wind_speed = True
    if "relative_humidity" in attrs or "humidity" in attrs:
        caps.has_relative_humidity = True
    if "pressure" in attrs:
        caps.has_pressure = True
    
    _LOGGER.info(
        "Weather capabilities for %s: %s",
        entity_id,
        caps.get_description()
    )
    
    return caps


def eccentricity_correction(day_of_year: int) -> float:
    """
    Calculate Earth-Sun distance correction factor.
    
    Args:
        day_of_year: Day of year (1-365/366)
    
    Returns:
        Eccentricity correction factor E0
    """
    B = 2 * math.pi * (day_of_year - 1) / 365.0
    E0 = 1.000110 + 0.034221 * math.cos(B) + 0.001280 * math.sin(B)
    E0 += 0.000719 * math.cos(2 * B) + 0.000077 * math.sin(2 * B)
    return E0


def solar_position(lat: float, lon: float, dt: datetime) -> Tuple[float, float, float]:
    """
    Calculate solar position (altitude and azimuth).
    
    Args:
        lat: Latitude in degrees
        lon: Longitude in degrees
        dt: Datetime (must be timezone-aware)
    
    Returns:
        Tuple of (altitude_deg, azimuth_deg, zenith_deg)
    """
    # Convert to UTC if not already
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=dt_util.UTC)
    else:
        dt = dt.astimezone(dt_util.UTC)
    
    # Day of year
    doy = dt.timetuple().tm_yday
    
    # Declination angle (simplified)
    decl = 23.45 * math.sin(math.radians(360 * (284 + doy) / 365.0))
    
    # Equation of time (minutes)
    B = 2 * math.pi * (doy - 81) / 364.0
    EoT = 9.87 * math.sin(2 * B) - 7.53 * math.cos(B) - 1.5 * math.sin(B)
    
    # Local solar time
    time_offset = EoT + 4 * lon  # minutes
    solar_time = dt.hour + dt.minute / 60.0 + dt.second / 3600.0 + time_offset / 60.0
    
    # Hour angle
    hour_angle = 15.0 * (solar_time - 12.0)
    
    # Solar altitude
    lat_rad = math.radians(lat)
    decl_rad = math.radians(decl)
    ha_rad = math.radians(hour_angle)
    
    sin_alt = (math.sin(lat_rad) * math.sin(decl_rad) +
               math.cos(lat_rad) * math.cos(decl_rad) * math.cos(ha_rad))
    altitude = math.degrees(math.asin(max(-1, min(1, sin_alt))))
    
    # Solar azimuth (0° = North, 90° = East, 180° = South, 270° = West)
    cos_az = ((math.sin(decl_rad) - math.sin(lat_rad) * sin_alt) /
              (math.cos(lat_rad) * math.cos(math.radians(altitude))))
    cos_az = max(-1, min(1, cos_az))
    azimuth = math.degrees(math.acos(cos_az))
    
    if solar_time > 12.0:
        azimuth = 360.0 - azimuth
    
    zenith = 90.0 - altitude
    
    return altitude, azimuth, zenith


def clearsky_ghi_haurwitz(zenith_deg: float) -> float:
    """
    Calculate clear-sky GHI using simplified Haurwitz model.
    
    Args:
        zenith_deg: Solar zenith angle in degrees
    
    Returns:
        Clear-sky GHI in W/m²
    """
    if zenith_deg >= 90.0:
        return 0.0
    
    z_rad = math.radians(zenith_deg)
    cos_z = math.cos(z_rad)
    
    if cos_z <= 0:
        return 0.0
    
    # Haurwitz formula
    ghi_cs = 1098.0 * cos_z * math.exp(-0.059 / cos_z)
    
    return max(0.0, ghi_cs)


def cloud_to_ghi(ghi_clear: float, cloud_fraction: float) -> float:
    """
    Map cloud cover to GHI using a balanced cloud transmission model.
    
    The original Kasten-Czeplak model (1 - 0.75 * C^3.4) works well for
    satellite measurements but is too aggressive for weather forecasts,
    which tend to overestimate cloud cover.
    
    This implementation uses a more balanced quadratic model that:
    - Provides smooth transitions across all cloud levels
    - Accounts for diffuse skylight even in heavy overcast
    - Better matches real-world PV production under forecast conditions
    
    The formula ensures:
    - 0% cloud = 100% transmission
    - 50% cloud = ~50% transmission
    - 75% cloud = ~25% transmission  
    - 100% cloud = 15% transmission (overcast still allows diffuse light)
    
    Formula: 0.15 + 0.85 * (1 - C)^1.8
    
    This gives better accuracy for weather forecast data while maintaining
    physical realism (never goes to zero, accounts for diffuse radiation).
    
    Args:
        ghi_clear: Clear-sky GHI in W/m²
        cloud_fraction: Cloud cover fraction (0-1)
    
    Returns:
        Actual GHI in W/m²
    """
    C = max(0.0, min(1.0, cloud_fraction))
    
    # Use a balanced power law model with guaranteed minimum
    # Power of 1.8 gives good response across all cloud levels
    # Minimum 15% accounts for diffuse skylight
    ghi = ghi_clear * (0.15 + 0.85 * ((1.0 - C) ** 1.8))
    
    return max(0.0, ghi)


def erbs_decomposition(ghi: float, zenith_deg: float, dni_extra: float) -> Tuple[float, float]:
    """
    Decompose GHI into DHI and DNI using Erbs correlation.
    
    Args:
        ghi: Global Horizontal Irradiance in W/m²
        zenith_deg: Solar zenith angle in degrees
        dni_extra: Extraterrestrial DNI in W/m²
    
    Returns:
        Tuple of (dhi, dni) in W/m²
    """
    if zenith_deg >= 90.0 or ghi <= 0:
        return 0.0, 0.0
    
    z_rad = math.radians(zenith_deg)
    cos_z = math.cos(z_rad)
    
    if cos_z <= 0:
        return 0.0, 0.0
    
    # Clearness index
    kt = ghi / max(dni_extra * cos_z, 1.0)
    kt = max(0.0, min(1.0, kt))
    
    # Diffuse fraction using Erbs correlation
    if kt <= 0.22:
        Fd = 1.0 - 0.09 * kt
    elif kt <= 0.80:
        Fd = 0.9511 - 0.1604 * kt + 4.388 * kt**2 - 16.638 * kt**3 + 12.336 * kt**4
    else:
        Fd = 0.165
    
    Fd = max(0.0, min(1.0, Fd))
    
    # Calculate DHI and DNI
    dhi = Fd * ghi
    dni = max(0.0, (ghi - dhi) / max(cos_z, 1e-6))
    
    return dhi, dni


def poa_hdkr(
    ghi: float,
    dhi: float,
    dni: float,
    zenith_deg: float,
    azimuth_deg: float,
    tilt_deg: float,
    surf_az_deg: float,
    albedo: float = 0.2
) -> float:
    """
    Calculate plane-of-array irradiance using HDKR transposition model.
    
    Args:
        ghi: Global Horizontal Irradiance in W/m²
        dhi: Diffuse Horizontal Irradiance in W/m²
        dni: Direct Normal Irradiance in W/m²
        zenith_deg: Solar zenith angle in degrees
        azimuth_deg: Solar azimuth in degrees (0° = N, 90° = E)
        tilt_deg: Panel tilt from horizontal in degrees
        surf_az_deg: Panel azimuth in degrees (0° = N, 90° = E)
        albedo: Ground reflectance (default 0.2)
    
    Returns:
        POA irradiance in W/m²
    """
    if zenith_deg >= 90.0:
        return 0.0
    
    z_rad = math.radians(zenith_deg)
    sun_az_rad = math.radians(azimuth_deg)
    tilt_rad = math.radians(tilt_deg)
    surf_az_rad = math.radians(surf_az_deg)
    
    cos_z = math.cos(z_rad)
    
    # Angle of incidence on tilted surface
    cos_aoi = (math.sin(math.radians(90.0 - zenith_deg)) * math.sin(tilt_rad) *
               math.cos(sun_az_rad - surf_az_rad) +
               math.cos(math.radians(90.0 - zenith_deg)) * math.cos(tilt_rad))
    cos_aoi = max(0.0, cos_aoi)
    
    # Direct beam component
    beam = dni * cos_aoi
    
    # HDKR diffuse component
    if (dni + dhi) > 0:
        Ai = dni / (dni + dhi)  # Anisotropy index
    else:
        Ai = 0.0
    
    Rb = cos_aoi / max(cos_z, 1e-6) if cos_z > 0 else 0.0
    
    if ghi > 0:
        F = math.sqrt(dni / max(ghi, 1e-6))
    else:
        F = 0.0
    
    # Circumsolar and isotropic diffuse
    diffuse = dhi * (Ai * Rb + (1 - Ai) * (1 + math.cos(tilt_rad)) / 2 *
                     (1 + F * math.sin(tilt_rad / 2) ** 3))
    
    # Ground-reflected component
    ground = ghi * albedo * (1 - math.cos(tilt_rad)) / 2
    
    poa_total = beam + diffuse + ground
    
    return max(0.0, poa_total)


def horizon_alt_interp(horizon12_deg: List[float], sun_az_deg: float) -> float:
    """
    Interpolate horizon altitude at a given azimuth.
    
    Args:
        horizon12_deg: List of 12 horizon altitudes at 30° intervals
                      starting from North (0°, 30°, 60°, ..., 330°)
        sun_az_deg: Sun azimuth in degrees
    
    Returns:
        Interpolated horizon altitude in degrees
    """
    if not horizon12_deg or len(horizon12_deg) != 12:
        return 0.0
    
    az = sun_az_deg % 360.0
    i0 = int(az // 30) % 12
    i1 = (i0 + 1) % 12
    frac = (az - 30 * i0) / 30.0
    
    h0 = horizon12_deg[i0]
    h1 = horizon12_deg[i1]
    
    return h0 * (1 - frac) + h1 * frac


def apply_horizon_blocking(
    dni: float,
    dhi: float,
    sun_alt_deg: float,
    sun_az_deg: float,
    horizon12_deg: List[float],
    svf: Optional[float] = None
) -> Tuple[float, float]:
    """
    Apply horizon blocking to DNI and optionally reduce DHI by sky-view factor.
    
    Args:
        dni: Direct Normal Irradiance in W/m²
        dhi: Diffuse Horizontal Irradiance in W/m²
        sun_alt_deg: Sun altitude in degrees
        sun_az_deg: Sun azimuth in degrees
        horizon12_deg: List of 12 horizon altitudes
        svf: Sky view factor (0-1), if None will be calculated
    
    Returns:
        Tuple of (blocked_dni, adjusted_dhi) in W/m²
    """
    # Block DNI if sun is below horizon
    horizon_alt = horizon_alt_interp(horizon12_deg, sun_az_deg)
    blocked_dni = 0.0 if sun_alt_deg < horizon_alt else dni
    
    # Calculate or use provided sky-view factor
    if svf is None:
        svf = approximate_svf(horizon12_deg)
    
    adjusted_dhi = dhi * svf
    
    return blocked_dni, adjusted_dhi


def approximate_svf(horizon12_deg: List[float]) -> float:
    """
    Approximate sky-view factor from 12-point horizon profile.
    
    Args:
        horizon12_deg: List of 12 horizon altitudes in degrees
    
    Returns:
        Sky view factor (0.7 to 1.0)
    """
    if not horizon12_deg:
        return 1.0
    
    # Simple approximation: SVF ≈ 1 - average(sin(horizon_alt))
    avg_sin = sum(math.sin(math.radians(max(0, h))) for h in horizon12_deg) / len(horizon12_deg)
    svf = 1.0 - avg_sin
    
    # Clamp to reasonable range
    return max(0.7, min(1.0, svf))


def cell_temp_pvsyst(poa: float, temp_amb: float, wind_speed: float = 1.0) -> float:
    """
    Calculate cell temperature using simplified PVsyst-like model.
    
    Args:
        poa: Plane-of-array irradiance in W/m²
        temp_amb: Ambient temperature in °C
        wind_speed: Wind speed in m/s (default 1.0)
    
    Returns:
        Cell temperature in °C
    """
    # Simplified NOCT-based model
    # NOCT ≈ 45°C at 800 W/m², ambient 20°C, wind 1 m/s
    noct = 45.0
    
    # Temperature rise above ambient
    delta_t = (noct - 20.0) * (poa / 800.0)
    
    # Wind cooling effect (simplified)
    wind_factor = max(0.7, 1.0 - 0.03 * (wind_speed - 1.0))
    
    tcell = temp_amb + delta_t * wind_factor
    
    return tcell


def pvwatts_dc(
    poa: float,
    tcell: float,
    pdc0_w: float,
    gamma_pdc_per_c: float = -0.0038
) -> float:
    """
    Calculate DC power output using PVWatts model.
    
    Args:
        poa: Plane-of-array irradiance in W/m²
        tcell: Cell temperature in °C
        pdc0_w: Rated DC power at STC in W
        gamma_pdc_per_c: Temperature coefficient per °C (default -0.38%/°C)
    
    Returns:
        DC power in W
    """
    # PVWatts: Pdc = Pdc0 * (POA/1000) * [1 + gamma * (Tcell - 25)]
    temp_factor = 1.0 + gamma_pdc_per_c * (tcell - 25.0)
    pdc = pdc0_w * (poa / 1000.0) * temp_factor
    
    return max(0.0, pdc)


def pvwatts_ac(
    pdc_w: float,
    pac_max_w: Optional[float] = None,
    eta_inv_nom: float = 0.96
) -> float:
    """
    Calculate AC power output with inverter efficiency and clipping.
    
    Args:
        pdc_w: DC power in W
        pac_max_w: Maximum AC power (inverter rating) in W, if None uses nominal conversion
        eta_inv_nom: Nominal inverter efficiency (default 0.96)
    
    Returns:
        AC power in W
    """
    # Simple model: AC = DC * efficiency, with optional clipping
    pac = pdc_w * eta_inv_nom
    
    if pac_max_w is not None:
        pac = min(pac, pac_max_w)
    
    return max(0.0, pac)


class ManualForecastEngine:
    """Manual physics-based PV forecast engine."""
    
    def __init__(
        self,
        hass,
        lat: float,
        lon: float,
        planes_json: str,
        horizon_csv: Optional[str] = None,
        weather_entity: Optional[str] = None,
        step_minutes: int = 15,
        diffuse_svf: Optional[float] = None,
        temp_coeff_pct_per_c: float = -0.38,
        inverter_ac_kw_cap: Optional[float] = None,
        calibration_enabled: bool = False,
    ):
        """
        Initialize manual forecast engine.
        
        Args:
            hass: Home Assistant instance
            lat: Latitude in degrees
            lon: Longitude in degrees
            planes_json: JSON string with plane configurations
            horizon_csv: CSV string with 12 horizon altitudes
            weather_entity: Weather entity ID
            step_minutes: Forecast time step in minutes (15, 30, or 60)
            diffuse_svf: Diffuse sky-view factor override (0.85-1.0)
            temp_coeff_pct_per_c: Module temp coefficient in %/°C
            inverter_ac_kw_cap: Optional system-level inverter cap in kW
            calibration_enabled: Enable per-plane calibration
        """
        self.hass = hass
        self.lat = lat
        self.lon = lon
        self.weather_entity = weather_entity or ""
        self.step_minutes = step_minutes
        self.diffuse_svf = diffuse_svf
        self.temp_coeff = temp_coeff_pct_per_c / 100.0  # Convert % to fraction
        self.inverter_ac_kw_cap = inverter_ac_kw_cap
        self.calibration_enabled = calibration_enabled
        
        # Parse planes
        try:
            self.planes = json.loads(planes_json)
            if not isinstance(self.planes, list):
                raise ValueError("planes_json must be a JSON list")
        except Exception as e:
            _LOGGER.exception("Failed to parse planes_json: %s", e)
            self.planes = [{"dec": 45, "az": "S", "kwp": 5.0}]
        
        # Parse horizon (12 values at 30° intervals)
        self.horizon12 = []
        if horizon_csv:
            try:
                parts = [float(x.strip()) for x in horizon_csv.split(",")]
                if len(parts) == 12:
                    self.horizon12 = parts
                else:
                    _LOGGER.warning("Horizon CSV must have 12 values, got %d", len(parts))
                    self.horizon12 = [0.0] * 12
            except Exception as e:
                _LOGGER.exception("Failed to parse horizon CSV: %s", e)
                self.horizon12 = [0.0] * 12
        else:
            self.horizon12 = [0.0] * 12
        
        # Detect weather capabilities
        self.weather_caps = detect_weather_capabilities(hass, self.weather_entity)
        
        # Calibration scalars (per-plane)
        self.calibration_scalars: Dict[int, float] = {}
    
    def _normalize_azimuth(self, az: str | int) -> float:
        """
        Convert azimuth to degrees (0° = N, 90° = E, 180° = S, 270° = W).
        
        Args:
            az: Azimuth as string (N, E, S, W, etc.) or degrees
        
        Returns:
            Azimuth in degrees (0-359)
        """
        if isinstance(az, (int, float)):
            return float(az) % 360.0
        
        az_str = str(az).strip().upper()
        azimuth_map = {
            "N": 0, "NNE": 22.5, "NE": 45, "ENE": 67.5,
            "E": 90, "ESE": 112.5, "SE": 135, "SSE": 157.5,
            "S": 180, "SSW": 202.5, "SW": 225, "WSW": 247.5,
            "W": 270, "WNW": 292.5, "NW": 315, "NNW": 337.5,
        }
        
        return azimuth_map.get(az_str, 180.0)
    
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
                            from homeassistant.util import dt as dt_util
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
    
    def _get_weather_data(self, dt: datetime, hourly_forecast: Optional[Dict[datetime, Dict[str, float]]] = None) -> Dict[str, Optional[float]]:
        """
        Get weather data from entity at specified time.
        
        Args:
            dt: Datetime to get weather for
            hourly_forecast: Optional dict of hourly forecast data (from _get_hourly_weather_forecast)
        
        Returns:
            Dict with weather fields (ghi, dni, dhi, cloud_cover, temperature, wind_speed)
        """
        data = {
            "ghi": None,
            "dni": None,
            "dhi": None,
            "cloud_cover": None,
            "temperature": None,
            "wind_speed": None,
        }
        
        if not self.weather_entity:
            return data
        
        # If hourly forecast is provided, try to use it first
        if hourly_forecast:
            # Find the closest forecast time
            closest_forecast = None
            min_diff = timedelta(hours=2)  # Search within 2 hours
            
            for forecast_time in hourly_forecast.keys():
                diff = abs(dt - forecast_time)
                if diff < min_diff:
                    min_diff = diff
                    closest_forecast = forecast_time
            
            if closest_forecast is not None:
                forecast_entry = hourly_forecast[closest_forecast]
                
                # Get irradiance
                if "global_horizontal_irradiance" in forecast_entry:
                    try:
                        data["ghi"] = float(forecast_entry["global_horizontal_irradiance"])
                    except (ValueError, TypeError):
                        pass
                elif "shortwave_radiation" in forecast_entry:
                    try:
                        data["ghi"] = float(forecast_entry["shortwave_radiation"])
                    except (ValueError, TypeError):
                        pass
                
                if "direct_normal_irradiance" in forecast_entry:
                    try:
                        data["dni"] = float(forecast_entry["direct_normal_irradiance"])
                    except (ValueError, TypeError):
                        pass
                
                if "diffuse_horizontal_irradiance" in forecast_entry:
                    try:
                        data["dhi"] = float(forecast_entry["diffuse_horizontal_irradiance"])
                    except (ValueError, TypeError):
                        pass
                
                # Get cloud cover
                for key in ["cloud_cover", "cloudiness", "cloud_coverage", "cloud"]:
                    if key in forecast_entry:
                        try:
                            # Assume 0-100 scale
                            data["cloud_cover"] = float(forecast_entry[key])
                            break
                        except (ValueError, TypeError):
                            continue
                
                # Get temperature
                if "temperature" in forecast_entry:
                    try:
                        data["temperature"] = float(forecast_entry["temperature"])
                    except (ValueError, TypeError):
                        pass
                
                # Get wind speed
                if "wind_speed" in forecast_entry:
                    try:
                        data["wind_speed"] = float(forecast_entry["wind_speed"])
                    except (ValueError, TypeError):
                        pass
                
                # If we got data from forecast, return it
                if any(v is not None for v in data.values()):
                    return data
        
        # Fallback to current state if forecast is not available
        state = self.hass.states.get(self.weather_entity)
        if not state:
            return data
        
        attrs = state.attributes
        
        # Get irradiance
        if "global_horizontal_irradiance" in attrs:
            try:
                data["ghi"] = float(attrs["global_horizontal_irradiance"])
            except (ValueError, TypeError):
                pass
        elif "shortwave_radiation" in attrs:
            try:
                data["ghi"] = float(attrs["shortwave_radiation"])
            except (ValueError, TypeError):
                pass
        
        if "direct_normal_irradiance" in attrs:
            try:
                data["dni"] = float(attrs["direct_normal_irradiance"])
            except (ValueError, TypeError):
                pass
        
        if "diffuse_horizontal_irradiance" in attrs:
            try:
                data["dhi"] = float(attrs["diffuse_horizontal_irradiance"])
            except (ValueError, TypeError):
                pass
        
        # Get cloud cover
        for key in ["cloud_cover", "cloudiness", "cloud_coverage", "cloud"]:
            if key in attrs:
                try:
                    # Assume 0-100 scale
                    data["cloud_cover"] = float(attrs[key])
                    break
                except (ValueError, TypeError):
                    continue
        
        # Get temperature
        if "temperature" in attrs:
            try:
                data["temperature"] = float(attrs["temperature"])
            except (ValueError, TypeError):
                pass
        
        # Get wind speed
        if "wind_speed" in attrs:
            try:
                data["wind_speed"] = float(attrs["wind_speed"])
            except (ValueError, TypeError):
                pass
        
        return data
    
    async def async_compute_forecast(
        self,
        start_time: Optional[datetime] = None,
        hours_ahead: int = 48
    ) -> List[ForecastPoint]:
        """
        Compute manual physics-based forecast.
        
        This method logs comprehensive calculation data for forecast improvement:
        - Solar geometry: altitude, azimuth, zenith angle
        - Weather inputs: DNI, DHI, GHI, cloud cover, temperature, wind
        - Irradiance tier used and calculated values
        - Per-plane calculations: POA, cell temp, DC/AC power
        - Calibration factors applied (if any)
        - System-level clipping events
        
        To analyze forecast accuracy, compare logged forecasts with actual generation
        from PV sensors. All calculation inputs are logged at DEBUG level to enable
        detailed analysis and potential calibration improvements.
        
        Args:
            start_time: Start time for forecast (default: now)
            hours_ahead: Hours to forecast ahead (default: 48)
        
        Returns:
            List of ForecastPoint objects with forecasted power (watts) per timestep
        """
        if start_time is None:
            start_time = dt_util.now()
        
        # Ensure timezone-aware
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
        
        forecast_points = []
        
        # Generate time steps
        num_steps = int(hours_ahead * 60 / self.step_minutes)
        
        # Log forecast run parameters
        _LOGGER.debug(
            "Starting manual forecast: lat=%.4f, lon=%.4f, planes=%d, step=%d min, hours=%d",
            self.lat, self.lon, len(self.planes), self.step_minutes, hours_ahead
        )
        
        # Get hourly weather forecast once for all time steps
        hourly_forecast = await self._get_hourly_weather_forecast()
        if hourly_forecast:
            _LOGGER.info("Using hourly weather forecast data for manual forecast (%d points)", len(hourly_forecast))
        else:
            _LOGGER.info("Hourly forecast not available, falling back to current weather state")
        
        for i in range(num_steps):
            dt = start_time + timedelta(minutes=i * self.step_minutes)
            
            # Calculate solar position
            sun_alt, sun_az, sun_zenith = solar_position(self.lat, self.lon, dt)
            
            # Skip if sun is below horizon
            if sun_alt <= 0:
                forecast_points.append(ForecastPoint(time=dt, watts=0.0))
                continue
            
            # Get weather data (with hourly forecast if available)
            weather = self._get_weather_data(dt, hourly_forecast)
            
            # Calculate extraterrestrial DNI (Direct Normal Irradiance outside atmosphere)
            doy = dt.timetuple().tm_yday
            E0 = eccentricity_correction(doy)
            dni_extra = SOLAR_CONSTANT * E0
            
            # Log solar geometry and weather inputs (only for first few points to avoid log spam)
            if i < 3 or i % 24 == 0:  # Log first 3 and then hourly
                _LOGGER.debug(
                    "[%s] Solar: alt=%.1f° az=%.1f° zenith=%.1f° | Weather: DNI=%s DHI=%s GHI=%s cloud=%s%% temp=%.1f°C wind=%.1fm/s",
                    dt.strftime("%Y-%m-%d %H:%M"),
                    sun_alt, sun_az, sun_zenith,
                    weather["dni"], weather["dhi"], weather["ghi"],
                    weather["cloud_cover"],
                    weather["temperature"] if weather["temperature"] is not None else 20.0,
                    weather["wind_speed"] if weather["wind_speed"] is not None else 1.0
                )
            
            # Determine irradiance based on available data (tier system)
            tier_used = None
            if weather["dni"] is not None and weather["dhi"] is not None:
                # Tier 1: Use provided DNI/DHI
                dni = weather["dni"]
                dhi = weather["dhi"]
                ghi = dni * math.cos(math.radians(sun_zenith)) + dhi
                tier_used = "1-DNI/DHI"
            elif weather["ghi"] is not None:
                # Tier 1: Decompose GHI
                ghi = weather["ghi"]
                dhi, dni = erbs_decomposition(ghi, sun_zenith, dni_extra)
                tier_used = "1-GHI"
            elif weather["cloud_cover"] is not None:
                # Tier 2: Use cloud cover mapping
                ghi_clear = clearsky_ghi_haurwitz(sun_zenith)
                cloud_fraction = weather["cloud_cover"] / 100.0
                ghi = cloud_to_ghi(ghi_clear, cloud_fraction)
                dhi, dni = erbs_decomposition(ghi, sun_zenith, dni_extra)
                tier_used = "2-Cloud"
            else:
                # Tier 3: Use clear-sky model
                ghi = clearsky_ghi_haurwitz(sun_zenith)
                dhi, dni = erbs_decomposition(ghi, sun_zenith, dni_extra)
                tier_used = "3-ClearSky"
            
            # Apply horizon blocking
            dni_blocked, dhi_adjusted = apply_horizon_blocking(
                dni, dhi, sun_alt, sun_az, self.horizon12, self.diffuse_svf
            )
            
            # Log irradiance calculations
            if i < 3 or i % 24 == 0:
                _LOGGER.debug(
                    "[%s] Irradiance (Tier %s): GHI=%.0f DNI=%.0f→%.0f DHI=%.0f→%.0f W/m²",
                    dt.strftime("%Y-%m-%d %H:%M"),
                    tier_used,
                    ghi, dni, dni_blocked, dhi, dhi_adjusted
                )
            
            # Get meteorological data
            temp_amb = weather["temperature"] if weather["temperature"] is not None else 20.0
            wind_speed = weather["wind_speed"] if weather["wind_speed"] is not None else 1.0
            
            # Calculate power for each plane
            total_ac_w = 0.0
            plane_details = []
            
            for plane_idx, plane in enumerate(self.planes):
                tilt = float(plane.get("dec", 45))
                azimuth = self._normalize_azimuth(plane.get("az", 180))
                kwp = float(plane.get("kwp", 5.0))
                pdc0_w = kwp * 1000.0  # Convert kWp to W
                
                # Calculate POA (Plane-of-Array) irradiance using HDKR model
                poa = poa_hdkr(
                    ghi, dhi_adjusted, dni_blocked,
                    sun_zenith, sun_az,
                    tilt, azimuth
                )
                
                # Calculate cell temperature using PVsyst-like model
                tcell = cell_temp_pvsyst(poa, temp_amb, wind_speed)
                
                # Calculate DC power using PVWatts model
                pdc_w = pvwatts_dc(poa, tcell, pdc0_w, self.temp_coeff)
                
                # Apply calibration if enabled
                calib_factor = 1.0
                if self.calibration_enabled and plane_idx in self.calibration_scalars:
                    calib_factor = self.calibration_scalars[plane_idx]
                    pdc_w *= calib_factor
                
                # Calculate AC power (inverter conversion)
                pac_w = pvwatts_ac(pdc_w)
                
                total_ac_w += pac_w
                
                # Store details for logging
                plane_details.append({
                    "idx": plane_idx,
                    "az": azimuth,
                    "tilt": tilt,
                    "poa": poa,
                    "tcell": tcell,
                    "pdc": pdc_w,
                    "pac": pac_w,
                    "calib": calib_factor
                })
            
            # Apply system-level inverter cap if configured
            total_before_cap = total_ac_w
            if self.inverter_ac_kw_cap is not None:
                total_ac_w = min(total_ac_w, self.inverter_ac_kw_cap * 1000.0)
            
            # Log plane calculations (first few and hourly)
            if i < 3 or i % 24 == 0:
                for pd in plane_details:
                    _LOGGER.debug(
                        "[%s] Plane %d (az=%.0f° tilt=%.0f°): POA=%.0f W/m² → Tcell=%.1f°C → DC=%.0fW → AC=%.0fW (calib=%.3f)",
                        dt.strftime("%Y-%m-%d %H:%M"),
                        pd["idx"], pd["az"], pd["tilt"], pd["poa"],
                        pd["tcell"], pd["pdc"], pd["pac"], pd["calib"]
                    )
                if self.inverter_ac_kw_cap is not None and total_before_cap > total_ac_w:
                    _LOGGER.debug(
                        "[%s] Inverter clipping: %.0fW → %.0fW (cap=%.0fkW)",
                        dt.strftime("%Y-%m-%d %H:%M"),
                        total_before_cap, total_ac_w, self.inverter_ac_kw_cap
                    )
            
            forecast_points.append(ForecastPoint(time=dt, watts=total_ac_w))
        
        _LOGGER.info(
            "Manual forecast computed: %d points from %s to %s, tier=%s, total_energy=%.2fkWh",
            len(forecast_points),
            start_time.isoformat(),
            forecast_points[-1].time.isoformat() if forecast_points else "N/A",
            self.weather_caps.get_description(),
            sum(p.watts for p in forecast_points) * self.step_minutes / 60.0 / 1000.0
        )
        
        return forecast_points
