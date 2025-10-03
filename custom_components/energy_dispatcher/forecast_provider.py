"""
ForecastSolarProvider

Hämtar prognos från Forecast.Solar och konverterar till list[ForecastPoint].
Stödjer 1–2 plan i MVP. Horizon kan anges som CSV. API-key valfri.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import List, Optional
from urllib.parse import quote

import async_timeout
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .models import ForecastPoint

_LOGGER = logging.getLogger(__name__)

FS_BASE = "https://api.forecast.solar"


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
    ):
        self.hass = hass
        self.lat = lat
        self.lon = lon
        self.apikey = apikey or ""
        self.horizon_csv = horizon_csv
        try:
            self.planes = json.loads(planes_json)
            if not isinstance(self.planes, list):
                raise ValueError("planes_json måste vara en JSON-lista")
        except Exception as e:  # noqa: BLE001
            _LOGGER.exception("Kunde inte parsa fs_planes: %s", e)
            self.planes = [{"dec": 37, "az": 0, "kwp": 5.67}]

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

    async def async_fetch_watts(self) -> List[ForecastPoint]:
        """
        Hämtar result.watts och returnerar list[ForecastPoint].
        Tidsstämplar sätts till lokal timezone (HA:s DEFAULT_TIME_ZONE).
        """
        url = self._build_url()
        _LOGGER.debug("Forecast.Solar URL: %s", url)

        session = async_get_clientsession(self.hass)
        try:
            with async_timeout.timeout(20):
                resp = await session.get(url)
            if resp.status != 200:
                text = await resp.text()
                _LOGGER.warning("Forecast.Solar status=%s text=%s", resp.status, text)
                return []
            data = await resp.json()
        except Exception as e:  # noqa: BLE001
            _LOGGER.exception("Kunde inte hämta Forecast.Solar: %s", e)
            return []

        result = data.get("result") or {}
        watts_map = result.get("watts") or {}
        out: List[ForecastPoint] = []
        for ts, w in watts_map.items():
            # ex: "2022-10-12 08:00:00" i lokal tid
            try:
                dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                # gör tz-aware i HA:s lokala timezone
                dt = dt.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
                out.append(ForecastPoint(time=dt, watts=float(w)))
            except Exception:
                continue

        _LOGGER.debug("Forecast.Solar: parsed %s points", len(out))
        return out
