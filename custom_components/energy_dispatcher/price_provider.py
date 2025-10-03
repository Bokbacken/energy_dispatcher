from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .models import PricePoint


@dataclass
class PriceFees:
    tax: float
    transfer: float
    surcharge: float
    vat: float
    fixed_monthly: float
    include_fixed: bool


def _enriched_spot(spot: float, fees: PriceFees) -> float:
    base = spot + fees.tax + fees.transfer + fees.surcharge
    enriched = base * (1.0 + fees.vat)
    if fees.include_fixed and fees.fixed_monthly > 0:
        enriched += fees.fixed_monthly / 720.0
    return round(enriched, 6)


class PriceProvider:
    def __init__(self, hass: HomeAssistant, nordpool_entity: str, fees: PriceFees):
        self.hass = hass
        self.nordpool_entity = nordpool_entity
        self.fees = fees

    def _to_local_dt(self, ts) -> Optional[datetime]:
        # ts kan vara str eller datetime
        if isinstance(ts, datetime):
            dt = ts
        else:
            dt = dt_util.parse_datetime(ts)
            if dt is None:
                try:
                    dt = datetime.fromisoformat(ts)
                except Exception:
                    return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(dt_util.DEFAULT_TIME_ZONE)

    def get_hourly_prices(self) -> List[PricePoint]:
        st = self.hass.states.get(self.nordpool_entity)
        if not st:
            return []
        attrs = st.attributes or {}
        rows = []
        rows.extend(attrs.get("raw_today") or [])
        rows.extend(attrs.get("raw_tomorrow") or [])  # kan vara tomt före ~14:00

        prices: List[PricePoint] = []
        for row in rows:
            try:
                dt = self._to_local_dt(row.get("start"))
                if not dt:
                    continue
                v = float(row.get("value"))
                enriched = _enriched_spot(v, self.fees)
                prices.append(
                    PricePoint(
                        time=dt.replace(minute=0, second=0, microsecond=0),
                        spot_sek_per_kwh=v,
                        enriched_sek_per_kwh=enriched,
                    )
                )
            except Exception:
                continue

        prices.sort(key=lambda p: p.time)
        return prices

    def get_current_enriched(self, hourly: List[PricePoint]) -> Optional[float]:
        if not hourly:
            return None
        now = dt_util.now().replace(minute=0, second=0, microsecond=0)
        # senaste timme <= now, annars första framtida
        past = [p for p in hourly if p.time <= now]
        if past:
            return past[-1].enriched_sek_per_kwh
        return hourly[0].enriched_sek_per_kwh
