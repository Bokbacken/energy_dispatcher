from datetime import datetime
from homeassistant.core import HomeAssistant
from .adapters.base import BatteryAdapter, EVSEAdapter

class Dispatcher:
    def __init__(self, hass: HomeAssistant, battery: BatteryAdapter, evse: EVSEAdapter):
        self.hass = hass
        self.battery = battery
        self.evse = evse
        self._overrides = {
            "ev_force_until": None,
            "ev_pause_until": None,
            "battery_force_until": None,
        }

    def set_override(self, key: str, until_dt):
        self._overrides[key] = until_dt

    async def execute_action(self, action, now: datetime):
        # Handle EV overrides
        if self._overrides["ev_pause_until"] and now < self._overrides["ev_pause_until"]:
            await self.evse.async_stop()
            return

        if self._overrides["ev_force_until"] and now < self._overrides["ev_force_until"]:
            await self.evse.async_set_current(action.ev_charge_a or 16)
            await self.evse.async_start()
        else:
            if action.ev_charge_a is not None:
                await self.evse.async_set_current(action.ev_charge_a)
                await self.evse.async_start()
            else:
                await self.evse.async_stop()

        # Battery forced charge override
        if self._overrides["battery_force_until"] and now < self._overrides["battery_force_until"]:
            if self.battery.supports_forced_charge():
                await self.battery.async_force_charge(power_w=4000, duration_min=60)
            return

        # Normal battery plan
        if action.charge_batt_w > 0 and self.battery.supports_forced_charge():
            await self.battery.async_force_charge(power_w=action.charge_batt_w, duration_min=60)
