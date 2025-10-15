from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum

@dataclass
class Plane:
    dec: int
    az: int
    kwp: float

@dataclass
class ForecastPoint:
    time: datetime
    watts: float

@dataclass
class PricePoint:
    time: datetime
    spot_sek_per_kwh: float
    enriched_sek_per_kwh: float
    export_sek_per_kwh: float = 0.0  # Export price for this hour

@dataclass
class PlanAction:
    time: datetime
    charge_batt_w: int = 0
    discharge_batt_w: int = 0
    ev_charge_a: Optional[int] = None
    notes: Optional[str] = None


# Energy Cost Classification
class CostLevel(Enum):
    """Energy cost classification levels."""
    CHEAP = "cheap"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class CostThresholds:
    """Thresholds for energy cost classification."""
    cheap_max: float = 1.5  # SEK/kWh
    high_min: float = 3.0   # SEK/kWh
    
    def classify(self, price_sek_per_kwh: float) -> CostLevel:
        """Classify price into cost level."""
        if price_sek_per_kwh <= self.cheap_max:
            return CostLevel.CHEAP
        elif price_sek_per_kwh >= self.high_min:
            return CostLevel.HIGH
        else:
            return CostLevel.MEDIUM


# Charging Modes
class ChargingMode(Enum):
    """EV charging optimization modes."""
    ASAP = "asap"           # Charge as soon as possible
    ECO = "eco"             # Optimize for solar/cheap energy
    DEADLINE = "deadline"   # Meet specific deadline
    COST_SAVER = "cost_saver"  # Minimize cost even if slower


# Vehicle Configuration
@dataclass
class VehicleConfig:
    """Configuration for an electric vehicle."""
    id: str
    name: str
    brand: str
    model: str
    battery_kwh: float
    max_charge_current: int  # Amperes
    phases: int = 3
    voltage: int = 230
    default_target_soc: float = 80.0
    charging_efficiency: float = 0.9
    has_api: bool = False
    charger_id: Optional[str] = None
    
    @staticmethod
    def tesla_model_y_lr_2022() -> 'VehicleConfig':
        """Preset for Tesla Model Y Long Range 2022."""
        return VehicleConfig(
            id="tesla_model_y_lr",
            name="Tesla Model Y Long Range",
            brand="Tesla",
            model="Model Y Long Range 2022",
            battery_kwh=75.0,
            max_charge_current=16,
            phases=3,
            voltage=230,
            default_target_soc=80.0,
            charging_efficiency=0.92,
            has_api=False
        )
    
    @staticmethod
    def hyundai_ioniq_electric_2019() -> 'VehicleConfig':
        """Preset for Hyundai Ioniq Electric 2019."""
        return VehicleConfig(
            id="hyundai_ioniq_electric",
            name="Hyundai Ioniq Electric",
            brand="Hyundai",
            model="Ioniq Electric 2019",
            battery_kwh=28.0,
            max_charge_current=16,
            phases=1,
            voltage=230,
            default_target_soc=100.0,
            charging_efficiency=0.88,
            has_api=False
        )


# Charger Configuration
@dataclass
class ChargerConfig:
    """Configuration for an EVSE charger."""
    id: str
    name: str
    brand: str
    model: str
    min_current: int = 6
    max_current: int = 16
    phases: int = 3
    voltage: int = 230
    supports_api: bool = False
    
    # Entity IDs for control
    start_switch: Optional[str] = None
    stop_switch: Optional[str] = None
    current_number: Optional[str] = None
    power_sensor: Optional[str] = None
    energy_sensor: Optional[str] = None
    total_energy_sensor: Optional[str] = None
    
    @staticmethod
    def generic_3phase_16a() -> 'ChargerConfig':
        """Preset for generic 3-phase 16A charger."""
        return ChargerConfig(
            id="generic_3phase",
            name="Generic 3-Phase Charger",
            brand="Generic",
            model="3-Phase 16A",
            min_current=6,
            max_current=16,
            phases=3,
            voltage=230,
            supports_api=False
        )
    
    @staticmethod
    def generic_1phase_16a() -> 'ChargerConfig':
        """Preset for generic 1-phase 16A charger."""
        return ChargerConfig(
            id="generic_1phase",
            name="Generic 1-Phase Charger",
            brand="Generic",
            model="1-Phase 16A",
            min_current=6,
            max_current=16,
            phases=1,
            voltage=230,
            supports_api=False
        )


# Vehicle State
@dataclass
class VehicleState:
    """Runtime state of a vehicle."""
    vehicle_id: str
    current_soc: float  # Percent
    target_soc: float   # Percent
    charging_mode: ChargingMode = ChargingMode.ECO
    deadline: Optional[datetime] = None
    is_connected: bool = False
    is_charging: bool = False
    last_update: Optional[datetime] = None


# Charging Session
@dataclass
class ChargingSession:
    """Tracking for a charging session."""
    vehicle_id: str
    charger_id: str
    start_time: datetime
    start_soc: float
    target_soc: float
    deadline: Optional[datetime] = None
    mode: ChargingMode = ChargingMode.ECO
    start_energy: Optional[float] = None  # kWh from total counter
    end_time: Optional[datetime] = None
    end_soc: Optional[float] = None
    energy_delivered: Optional[float] = None  # kWh
    active: bool = True


# EVSettings and EVState (backward compatibility)
@dataclass
class EVSettings:
    """Settings for EV adapter (legacy compatibility)."""
    capacity_kwh: float
    default_target_soc: float
    default_ampere: int
    efficiency: float = 0.9


@dataclass
class EVState:
    """State from EV adapter (legacy compatibility)."""
    soc: float
    target_soc: float
    required_kwh: float
    estimated_charge_time: float
    charger_available: bool
    last_update: datetime
