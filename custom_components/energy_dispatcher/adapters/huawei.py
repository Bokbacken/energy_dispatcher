from .base import BatteryAdapter
from homeassistant.core import HomeAssistant

class HuaweiBatteryAdapter(BatteryAdapter):
    def __init__(self, hass: HomeAssistant, device_id: str):
        super().__init__(hass)
        self._device_id = device_id

    def supports_forced_charge(self) -> bool:
        return True

    async def async_force_charge(self, power_w: int, duration_min: int) -> None:
        # Mirrors your existing automation but from our integration
        await self.hass.services.async_call(
            "huawei_solar",
            "forcible_charge",
            {
                "device_id": self._device_id,
                "power": str(power_w),
                "duration": duration_min,
            },
            blocking=False,
        )

    async def async_cancel_force_charge(self) -> None:
        # Some systems don't expose cancel; for Huawei, can no-op or switch mode back if needed
        return
