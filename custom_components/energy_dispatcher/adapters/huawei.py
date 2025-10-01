from __future__ import annotations
from homeassistant.core import HomeAssistant
from homeassistant.const import STATE_UNKNOWN
from ..const import CONF_BATTERY_SOC_ENTITY, CONF_HUAWEI_DEVICE_ID
from .base import BatteryAdapter, BatteryCapabilities
from ..models import Metrics

class HuaweiBatteryAdapter(BatteryAdapter):
    """
    Adapter for Huawei SUN2000/LUNA via huawei_solar integration.
    Uses services:
      - huawei_solar.forcible_charge {duration, power, device_id}
      - huawei_solar.forcible_discharge {duration, power, device_id}
    Power is W as string in many setups; we send string for compatibility.
    """
    def __init__(self, hass: HomeAssistant, config: dict):
        self.hass = hass
        self.soc_entity = config[CONF_BATTERY_SOC_ENTITY]
        self.device_id = config[CONF_HUAWEI_DEVICE_ID]
        self.capabilities = BatteryCapabilities(
            can_force_charge_from_grid=True,
            can_force_discharge_to_load=True,
            can_write_TOU_schedule=False
        )

    async def get_soc(self) -> float:
        state = self.hass.states.get(self.soc_entity)
        if not state or state.state in (None, STATE_UNKNOWN, "unavailable"):
            return 0.0
        try:
            return float(state.state)
        except Exception:
            return 0.0

    async def get_power_limits(self) -> tuple[float, float]:
        # For MVP, read from options later; here return None -> use config limits
        return (None, None)

    async def get_metrics(self) -> Metrics:
        # Extend to read p_batt, p_pv, etc. if you map entities in config_flow
        return Metrics()

    async def force_charge(self, minutes: int, power_kw: float) -> None:
        power_w = str(int(round(power_kw * 1000)))
        await self.hass.services.async_call(
            "huawei_solar",
            "forcible_charge",
            {"duration": int(minutes), "power": power_w},
            blocking=False,
            target={"device_id": self.device_id},
        )

    async def stop_charge(self) -> None:
        await self.hass.services.async_call(
            "huawei_solar",
            "forcible_charge",
            {"duration": 1, "power": "0"},
            blocking=False,
            target={"device_id": self.device_id},
        )

    async def force_discharge(self, minutes: int, power_kw: float) -> None:
        power_w = str(int(round(power_kw * 1000)))
        await self.hass.services.async_call(
            "huawei_solar",
            "forcible_discharge",
            {"duration": int(minutes), "power": power_w},
            blocking=False,
            target={"device_id": self.device_id},
        )

    async def stop_discharge(self) -> None:
        await self.hass.services.async_call(
            "huawei_solar",
            "forcible_discharge",
            {"duration": 1, "power": "0"},
            blocking=False,
            target={"device_id": self.device_id},
        )
