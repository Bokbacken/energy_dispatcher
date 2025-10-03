from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.core import HomeAssistant
from .const import DOMAIN, DEFAULT_UPDATE_INTERVAL

class EnergyDispatcherCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant):
        super().__init__(
            hass,
            logger=hass.helpers.logger.logging.getLogger(__name__),
            name=f"{DOMAIN}_coordinator",
            update_interval=timedelta(seconds=DEFAULT_UPDATE_INTERVAL),
        )
        self.data = {}

    async def _async_update_data(self):
        # TODO: fetch forecast, prices, consumption, battery soc etc.
        # Store in self.data
        return self.data
