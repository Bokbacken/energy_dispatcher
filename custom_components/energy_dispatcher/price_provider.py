from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .models import PricePoint


@dataclass
class PriceFees:
    tax: float            # SEK/kWh
    transfer: float       # SEK/kWh
    surcharge: float      # SEK/kWh (OBS: kan utökas till % senare)
    vat: float            # ex 0.25
    fixed_monthly: float  # SEK/månad
    include_fixed: bool   # om fast avgift ska inkluderas per timme


def _enriched_spot(spot: float, fees: PriceFees) -> float:
    base = spot + fees.tax + fees.transfer + fees.surcharge
    enriched = base * (1.0 + fees.vat)
    if fees.include_fixed and fees.fixed_monthly > 0:
        enriched += fees.fixed_monthly / 720.0  # ~720 timmar/månad
    return round(enriched, 6)


class PriceProvider:
    """
    Läser custom Nordpool-entity och bygger timlista (idag+imorgon),
    samt beräknar 'enriched' pris/timme.
    Förutsätter attributen raw_today/raw_tomorrow ~ list[{start, value}].
    """

    def __init__(self, hass: HomeAssistant, nordpool_entity: str, fees: PriceFees):
        self.hass = hass
        self.nordpool_entity = nordpool_entity
        self.fees = fees

    def get_hourly_prices(self) -> List[PricePoint]:
        st = self.hass.states.get(self.nordpool_entity)
        if not st:
            return []
        attrs = st.attributes or {}
        rows = []
        rows.extend(attrs.get("raw_today") or [])
        rows.extend(attrs.get("raw_tomorrow") or [])
        prices: List[PricePoint] = []
        for row in rows:
            try:
                ts = row.get("start")
                v = float(row.get("value"))
                # ts kan vara ISO; tolka till tz-aware datetime i lokal tz
                dt = dt_util.parse_datetime(ts)
                if dt is None:
                    # fallback
                    dt = datetime.fromisoformat(ts)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                dt = dt.astimezone(dt_util.DEFAULT_TIME_ZONE)
                enriched = _enriched_spot(v, self.fees)
                prices.append(PricePoint(time=dt.replace(minute=0, second=0, microsecond=0),
                                         spot_sek_per_kwh=v,
                                         enriched_sek_per_kwh=enriched))
            except Exception:
                continue
        return prices

    def get_current_enriched(self, hourly: List[PricePoint]) -> Optional[float]:
        if not hourly:
            return None
        now = dt_util.now().replace(minute=0, second=0, microsecond=0)
        # hitta närmast timblock <= now
        candidates = [p for p in hourly if p.time <= now]
        if not candidates:
            return hourly[0].enriched_sek_per_kwh
        candidates.sort(key=lambda p: p.time, reverse=True)
        return candidates[0].enriched_sek_per_kwh
