"""Huawei Solar battery and EMMA control adapters for Energy Dispatcher."""

from homeassistant.core import HomeAssistant
from .base import BatteryAdapter


class HuaweiBatteryAdapter(BatteryAdapter):
    """Adapter for Huawei battery systems with EMMA controller.
    
    Provides control over battery charging/discharging operations
    through the huawei_solar integration services.
    """

    def __init__(self, hass: HomeAssistant, device_id: str):
        """Initialize the Huawei battery adapter.
        
        Args:
            hass: Home Assistant instance
            device_id: The battery device ID from huawei_solar integration
        """
        super().__init__(hass)
        self._device_id = device_id

    def supports_forced_charge(self) -> bool:
        """Huawei systems support forced charging."""
        return True

    async def async_force_charge(self, power_w: int, duration_min: int) -> None:
        """Force battery to charge from grid at specified power for duration.
        
        Args:
            power_w: Charge power in watts (must not exceed max charge power)
            duration_min: Duration in minutes (1-1440)
        """
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
        """Stop any active forcible charge or discharge operation."""
        await self.hass.services.async_call(
            "huawei_solar",
            "stop_forcible_charge",
            {"device_id": self._device_id},
            blocking=False,
        )

    async def async_force_discharge(self, power_w: int, duration_min: int) -> None:
        """Force battery to discharge at specified power for duration.
        
        Args:
            power_w: Discharge power in watts (must not exceed max discharge power)
            duration_min: Duration in minutes (1-1440)
        """
        await self.hass.services.async_call(
            "huawei_solar",
            "forcible_discharge",
            {
                "device_id": self._device_id,
                "power": str(power_w),
                "duration": duration_min,
            },
            blocking=False,
        )

    async def async_force_charge_to_soc(self, power_w: int, target_soc: int) -> None:
        """Force battery to charge to a target State of Charge.
        
        Args:
            power_w: Charge power in watts
            target_soc: Target SOC percentage (12-100%)
        """
        await self.hass.services.async_call(
            "huawei_solar",
            "forcible_charge_soc",
            {
                "device_id": self._device_id,
                "power": str(power_w),
                "target_soc": target_soc,
            },
            blocking=False,
        )

    async def async_force_discharge_to_soc(self, power_w: int, target_soc: int) -> None:
        """Force battery to discharge to a target State of Charge.
        
        Args:
            power_w: Discharge power in watts
            target_soc: Target SOC percentage (12-100%)
        """
        await self.hass.services.async_call(
            "huawei_solar",
            "forcible_discharge_soc",
            {
                "device_id": self._device_id,
                "power": str(power_w),
                "target_soc": target_soc,
            },
            blocking=False,
        )


class HuaweiEMMAAdapter:
    """Adapter for EMMA-specific grid connection control.
    
    Provides control over grid export power limits and modes
    through the huawei_solar integration services.
    """

    def __init__(self, hass: HomeAssistant, emma_device_id: str):
        """Initialize the EMMA adapter.
        
        Args:
            hass: Home Assistant instance
            emma_device_id: The EMMA device ID from huawei_solar integration
        """
        self.hass = hass
        self._emma_device_id = emma_device_id

    async def async_set_zero_export(self) -> None:
        """Disable all grid export (zero-power grid connection mode).
        
        Useful during negative price periods or when export is not desired.
        Excess solar will charge battery or be curtailed.
        """
        await self.hass.services.async_call(
            "huawei_solar",
            "set_zero_power_grid_connection",
            {"device_id": self._emma_device_id},
            blocking=False,
        )

    async def async_set_export_limit_w(self, power_w: int) -> None:
        """Set maximum grid export power in watts.
        
        Args:
            power_w: Maximum export power in watts (>= -1000)
                    Positive values limit export
                    Negative values can limit import
        """
        await self.hass.services.async_call(
            "huawei_solar",
            "set_maximum_feed_grid_power",
            {
                "device_id": self._emma_device_id,
                "power": power_w,
            },
            blocking=False,
        )

    async def async_set_export_limit_percent(self, percentage: int) -> None:
        """Set maximum grid export as percentage of inverter capacity.
        
        Args:
            percentage: Maximum export percentage (0-100%)
        """
        await self.hass.services.async_call(
            "huawei_solar",
            "set_maximum_feed_grid_power_percent",
            {
                "device_id": self._emma_device_id,
                "power_percentage": percentage,
            },
            blocking=False,
        )

    async def async_reset_export_limit(self) -> None:
        """Remove all export restrictions (unlimited mode).
        
        Returns grid export to unrestricted operation.
        """
        await self.hass.services.async_call(
            "huawei_solar",
            "reset_maximum_feed_grid_power",
            {"device_id": self._emma_device_id},
            blocking=False,
        )

    async def async_set_tou_periods(self, periods: str) -> None:
        """Configure Time-of-Use periods for battery charge/discharge.
        
        Args:
            periods: Multi-line string with TOU period definitions
                    Format: HH:MM-HH:MM/DAYS/FLAG
                    Where:
                    - HH:MM-HH:MM: Time range (24-hour format)
                    - DAYS: Days of week (1=Mon, 7=Sun), e.g., "1234567" for all days
                    - FLAG: "+" for charge, "-" for discharge
                    
                    Example:
                    00:00-06:00/1234567/+
                    17:00-21:00/1234567/-
                    
                    Maximum 14 periods allowed.
        """
        await self.hass.services.async_call(
            "huawei_solar",
            "set_tou_periods",
            {
                "device_id": self._emma_device_id,
                "periods": periods,
            },
            blocking=False,
        )
