"""Datamodeller och hjälptyper för Energy Dispatcher."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional

from homeassistant.core import HomeAssistant


@dataclass(slots=True)
class PVArrayConfig:
    """Beskrivning av en PV-sträng."""
    label: str
    tilt: float
    azimuth: str
    peak_power_kwp: float


@dataclass(slots=True)
class ForecastSettings:
    """Inställningar för Forecast.Solar."""
    api_key: str
    latitude: float
    longitude: float
    horizon: list[int]
    pv_arrays: list[PVArrayConfig]


@dataclass(slots=True)
class NordpoolSettings:
    """Inställningar för elpris (Nord Pool eller sensor)."""
    area: str
    currency: str
    api_token: Optional[str]
    price_sensor_entity_id: Optional[str]


@dataclass(slots=True)
class BatterySettings:
    """Inställningar för batteriet."""
    adapter_type: str
    capacity_kwh: float
    min_soc: float
    max_soc: float
    soc_sensor_entity_id: str
    power_sensor_entity_id: Optional[str]
    grid_import_sensor_entity_id: Optional[str]
    force_charge_entity_id: Optional[str]
    force_discharge_entity_id: Optional[str]
    charge_mode_select_entity_id: Optional[str]
    charge_current_number_entity_id: Optional[str]
    supports_force_charge: bool = False
    supports_force_discharge: bool = False
    power_sign_invert: bool = False  # True om positivt = urladdning


@dataclass(slots=True)
class EVSettings:
    """Inställningar för EV-laddning."""
    adapter_type: str
    capacity_kwh: float
    default_target_soc: float
    min_ampere: float
    max_ampere: float
    default_ampere: float
    soc_sensor_entity_id: Optional[str]
    charger_switch_entity_id: Optional[str]
    charger_pause_switch_entity_id: Optional[str]
    current_number_entity_id: Optional[str]
    manual_departure_time: Optional[str]  # HH:MM, lokal tid
    manual_ready_by_time: Optional[str]
    efficiency: float = 0.9
    allow_manual_soc_entry: bool = True


@dataclass(slots=True)
class HouseSettings:
    """Inställningar för huset / laster."""
    avg_consumption_sensor: Optional[str]
    temperature_sensor: Optional[str]
    base_load_kw: Optional[float]
    hvac_load_sensor: Optional[str]
    dishwasher_load_kw: Optional[float]
    washer_load_kw: Optional[float]
    dryer_load_kw: Optional[float]
    extra_manual_entities: list[str] = field(default_factory=list)


@dataclass(slots=True)
class EnergyDispatcherConfig:
    """Sammanhållen konfiguration för hela integrationen."""
    name: str
    forecast: ForecastSettings
    prices: NordpoolSettings
    battery: Optional[BatterySettings]
    ev: Optional[EVSettings]
    house: HouseSettings
    scan_interval: timedelta
    auto_dispatch: bool


@dataclass(slots=True)
class SolarForecastPoint:
    """En punkt i solprognosen."""
    timestamp: datetime
    watts: float
    watt_hours_period: float
    cumulative_wh: float


@dataclass(slots=True)
class PricePoint:
    """Ett prisintervall (kan vara 60 eller 15 minuter)."""
    start: datetime
    end: datetime
    price: float  # i konfigurerad valuta/kWh
    is_predicted: bool = True


@dataclass(slots=True)
class BatteryState:
    """Aktuellt batteritillstånd."""
    soc: float  # 0-1
    power_kw: Optional[float]
    estimated_hours_remaining: Optional[float]
    price_per_kwh: Optional[float]
    last_update: datetime


@dataclass(slots=True)
class EVState:
    """Aktuellt EV-tillstånd."""
    soc: float  # 0-1
    target_soc: float
    required_kwh: float
    estimated_charge_time: Optional[float]
    charger_available: bool
    last_update: datetime


@dataclass(slots=True)
class HouseState:
    """Aktuellt hushållsstatus."""
    avg_consumption_kw: Optional[float]
    temperature_c: Optional[float]
    projected_adjusted_kw: Optional[float]
    last_update: datetime
    overrides_active: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EnergyPlanAction:
    """En planerad åtgärd."""
    action_type: str  # e.g. "charge_battery", "pause_ev", "notify"
    start: datetime
    end: datetime
    target_value: Optional[float] = None
    notes: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EnergyPlan:
    """Samlad plan för kommande period."""
    generated_at: datetime
    horizon_hours: int
    battery_actions: list[EnergyPlanAction] = field(default_factory=list)
    ev_actions: list[EnergyPlanAction] = field(default_factory=list)
    household_actions: list[EnergyPlanAction] = field(default_factory=list)


@dataclass(slots=True)
class EnergyDispatcherData:
    """Den data Coordinator levererar till entiteterna."""
    forecast_points: list[SolarForecastPoint]
    price_points: list[PricePoint]
    battery_state: Optional[BatteryState]
    ev_state: Optional[EVState]
    house_state: HouseState
    plan: EnergyPlan


@dataclass(slots=True)
class EnergyDispatcherRuntimeData:
    """Objekt som sparas i hass.data[DOMAIN][entry]."""
    coordinator: "EnergyDispatcherCoordinator"
    planner: "EnergyPlanner"
    dispatcher: "ActionDispatcher"
    store: "EnergyDispatcherStore"
    hass: HomeAssistant
