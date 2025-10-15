from __future__ import annotations

import logging
from typing import Any, Dict

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    PLATFORMS,
    STORE_MANUAL,
    STORE_ENTITIES,
    CONF_EV_CURRENT_SOC,
    CONF_EV_TARGET_SOC,
    CONF_EV_BATT_KWH,
    CONF_EVSE_MAX_A,
    CONF_EVSE_PHASES,
    CONF_EVSE_VOLTAGE,
    CONF_BATT_CAP_KWH,
    CONF_BATT_CAPACITY_ENTITY,
    CONF_AUTO_CREATE_DASHBOARD,
    CONF_EXPORT_MODE,
    CONF_MIN_EXPORT_PRICE_SEK_PER_KWH,
    CONF_BATTERY_DEGRADATION_COST_PER_CYCLE_SEK,
    M_EV_CURRENT_SOC,
    M_EV_TARGET_SOC,
    M_EV_BATT_KWH,
    M_EVSE_MAX_A,
    M_EVSE_PHASES,
    M_EVSE_VOLTAGE,
    M_HOME_BATT_CAP_KWH,
    M_HOME_BATT_SOC_FLOOR,
)
from .coordinator import EnergyDispatcherCoordinator
from .ev_dispatcher import EVDispatcher
from .bec import BatteryEnergyCost

_LOGGER = logging.getLogger(__name__)


async def create_default_dashboard(hass: HomeAssistant, entry: ConfigEntry):
    """Create a default Energy Dispatcher dashboard."""
    try:
        # Import lovelace dashboard components
        from homeassistant.components import lovelace
        
        # Dashboard URL key - unique identifier
        dashboard_url = "energy-dispatcher"
        
        # Check if dashboard already exists
        try:
            lovelace_data = hass.data.get("lovelace")
            if lovelace_data is not None and hasattr(lovelace_data, "dashboards"):
                existing = lovelace_data.dashboards
                if dashboard_url in existing:
                    _LOGGER.info("Energy Dispatcher dashboard already exists, skipping creation")
                    return
        except (AttributeError, KeyError):
            pass
        
        # Dashboard configuration
        dashboard_config = {
            "mode": "storage",
            "icon": "mdi:lightning-bolt",
            "title": "Energy Control",
            "show_in_sidebar": True,
            "require_admin": False,
        }
        
        # Basic dashboard view configuration
        view_config = {
            "title": "Energy Control",
            "path": "energy-control",
            "icon": "mdi:lightning-bolt",
            "cards": [
                {
                    "type": "markdown",
                    "content": "# Energy Dispatcher\n\nYour automated dashboard has been created! This is a basic view to get you started.\n\nFor a complete dashboard with graphs and controls, see the [Dashboard Guide](https://github.com/Bokbacken/energy_dispatcher/blob/main/docs/dashboard_guide.md)."
                },
                {
                    "type": "entities",
                    "title": "⚙️ Essential Settings",
                    "entities": [
                        f"number.{DOMAIN}_ev_aktuell_soc",
                        f"number.{DOMAIN}_ev_mal_soc",
                        f"number.{DOMAIN}_ev_batterikapacitet",
                        f"number.{DOMAIN}_hemmabatteri_kapacitet",
                    ]
                },
                {
                    "type": "entities",
                    "title": "🔋 Battery & EV Status",
                    "entities": [
                        f"sensor.{DOMAIN}_battery_soc",
                        f"sensor.{DOMAIN}_ev_soc",
                        f"sensor.{DOMAIN}_optimal_battery_action",
                        f"sensor.{DOMAIN}_ev_optimal_action",
                    ]
                },
                {
                    "type": "entities",
                    "title": "⚡ Quick Controls",
                    "entities": [
                        f"switch.{DOMAIN}_auto_ev_enabled",
                        f"switch.{DOMAIN}_auto_planner_enabled",
                    ]
                }
            ]
        }
        
        # Try to use the lovelace storage system
        try:
            # Access lovelace config
            lovelace_config = hass.data.get("lovelace")
            if lovelace_config is None:
                _LOGGER.warning("Lovelace not initialized yet, will create dashboard notification instead")
                raise ValueError("Lovelace not ready")
            
            # Create dashboard using lovelace storage
            # Note: This is a simplified approach. In production, we'd use the full Lovelace API
            _LOGGER.info("Dashboard creation via storage is complex - creating notification instead")
            raise ValueError("Using notification approach")
            
        except (AttributeError, KeyError, ValueError, Exception) as ex:
            # If direct creation fails, create a persistent notification with instructions
            _LOGGER.info(f"Creating dashboard notification instead of direct creation: {ex}")
            
            await hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "Energy Dispatcher Dashboard Ready",
                    "message": (
                        "**Welcome to Energy Dispatcher!** 🎉\n\n"
                        "A basic dashboard view is available, but for the full experience:\n\n"
                        "1. Go to **Settings → Dashboards**\n"
                        "2. Create a new dashboard called **Energy Control**\n"
                        "3. Follow our [Dashboard Setup Guide](https://github.com/Bokbacken/energy_dispatcher/blob/main/docs/dashboard_guide.md)\n\n"
                        "Or continue using the auto-generated entities in your existing dashboards!\n\n"
                        f"**Available entities:** `{DOMAIN}.*`"
                    ),
                    "notification_id": f"{DOMAIN}_dashboard_setup",
                },
                blocking=False,
            )
            _LOGGER.info("Created dashboard setup notification for user")
            
    except Exception as e:
        _LOGGER.warning("Failed to create dashboard or notification: %s", str(e))
        # Don't fail setup if dashboard creation fails


async def _async_register_services(hass: HomeAssistant):
    """Register services for Energy Dispatcher."""
    
    # Only register once
    if hass.services.has_service(DOMAIN, "battery_cost_reset"):
        return

    async def handle_schedule_appliance(call):
        """Handle appliance scheduling service call."""
        from .appliance_optimizer import ApplianceOptimizer
        from datetime import time as time_type
        
        appliance = call.data["appliance"]
        power_w = call.data["power_w"]
        duration_hours = call.data["duration_hours"]
        earliest_start_time = call.data.get("earliest_start")
        latest_end_time = call.data.get("latest_end")
        
        # Get first coordinator entry for optimization
        entries = [
            data for data in hass.data.get(DOMAIN, {}).values()
            if isinstance(data, dict) and "coordinator" in data
        ]
        if not entries:
            _LOGGER.error("No Energy Dispatcher coordinator found for appliance scheduling")
            return
        
        coordinator = entries[0]["coordinator"]
        
        # Convert time objects to datetime if provided
        earliest_start = None
        latest_end = None
        from homeassistant.util import dt as dt_util
        from datetime import datetime, timedelta
        
        now = dt_util.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        if earliest_start_time:
            if isinstance(earliest_start_time, time_type):
                earliest_start = today.replace(
                    hour=earliest_start_time.hour,
                    minute=earliest_start_time.minute,
                    second=0
                )
                # If time has passed today, use tomorrow
                if earliest_start < now:
                    earliest_start += timedelta(days=1)
        
        if latest_end_time:
            if isinstance(latest_end_time, time_type):
                latest_end = today.replace(
                    hour=latest_end_time.hour,
                    minute=latest_end_time.minute,
                    second=0
                )
                # If time has passed today, use tomorrow
                if latest_end < now:
                    latest_end += timedelta(days=1)
                # Ensure latest_end is after earliest_start
                if earliest_start and latest_end <= earliest_start:
                    latest_end += timedelta(days=1)
        
        # Get price and solar data from coordinator
        optimizer = ApplianceOptimizer()
        prices = coordinator.data.get("prices", [])
        solar_forecast = coordinator.data.get("solar_forecast", [])
        battery_soc = coordinator.data.get("battery_soc")
        battery_capacity_kwh = coordinator.data.get("battery_capacity_kwh")
        
        try:
            recommendation = optimizer.optimize_schedule(
                appliance_name=appliance,
                power_w=power_w,
                duration_hours=duration_hours,
                prices=prices,
                solar_forecast=solar_forecast if solar_forecast else None,
                earliest_start=earliest_start,
                latest_end=latest_end,
                battery_soc=battery_soc,
                battery_capacity_kwh=battery_capacity_kwh,
            )
            
            # Store recommendation in coordinator data
            if "appliance_recommendations" not in coordinator.data:
                coordinator.data["appliance_recommendations"] = {}
            coordinator.data["appliance_recommendations"][appliance] = recommendation
            
            # Trigger coordinator update to refresh sensors
            await coordinator.async_request_refresh()
            
            # Send notification
            optimal_time = recommendation["optimal_start_time"]
            await hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": f"{appliance.replace('_', ' ').title()} Schedule",
                    "message": (
                        f"**Optimal time:** {optimal_time.strftime('%Y-%m-%d %H:%M')}\n"
                        f"**Estimated cost:** {recommendation['estimated_cost_sek']:.2f} SEK\n"
                        f"**Savings vs now:** {recommendation['cost_savings_vs_now_sek']:.2f} SEK\n"
                        f"**Reason:** {recommendation['reason']}\n\n"
                        f"Confidence: {recommendation['confidence']}"
                    ),
                    "notification_id": f"{DOMAIN}_appliance_{appliance}",
                },
                blocking=False,
            )
            
            _LOGGER.info(
                "Appliance scheduling: %s at %s, cost %.2f SEK, savings %.2f SEK",
                appliance,
                optimal_time.strftime("%H:%M"),
                recommendation["estimated_cost_sek"],
                recommendation["cost_savings_vs_now_sek"],
            )
        except Exception as e:
            _LOGGER.error("Error scheduling appliance %s: %s", appliance, str(e))
            await hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": f"{appliance.replace('_', ' ').title()} Schedule Error",
                    "message": f"Failed to optimize schedule: {str(e)}",
                    "notification_id": f"{DOMAIN}_appliance_{appliance}_error",
                },
                blocking=False,
            )

    async def handle_battery_cost_reset(call):
        """Handle battery cost reset service call."""
        for entry_id, data in hass.data.get(DOMAIN, {}).items():
            if isinstance(data, dict) and "bec" in data:
                bec = data["bec"]
                bec.reset_cost()
                await bec.async_save()
                # Update legacy storage for backward compatibility
                data["wace"] = bec.wace
                data["wace_tot_energy_kwh"] = bec.energy_kwh
                data["wace_tot_cost_sek"] = bec.get_total_cost()
                _LOGGER.info("Battery cost reset for entry %s", entry_id)

    async def handle_battery_cost_set_soc(call):
        """Handle battery SOC set service call."""
        soc_percent = call.data.get("soc_percent")
        if soc_percent is None:
            _LOGGER.error("SOC percentage not provided")
            return
            
        for entry_id, data in hass.data.get(DOMAIN, {}).items():
            if isinstance(data, dict) and "bec" in data:
                bec = data["bec"]
                bec.set_soc(soc_percent)
                await bec.async_save()
                # Update legacy storage for backward compatibility
                data["wace"] = bec.wace
                data["wace_tot_energy_kwh"] = bec.energy_kwh
                data["wace_tot_cost_sek"] = bec.get_total_cost()
                _LOGGER.info("Battery SOC set to %.1f%% for entry %s", soc_percent, entry_id)

    async def handle_create_dashboard_notification(call):
        """Handle manual dashboard notification creation."""
        # Get the first config entry for this integration
        entries = hass.config_entries.async_entries(DOMAIN)
        if not entries:
            _LOGGER.error("No Energy Dispatcher integration configured")
            return
        
        # Use the first entry to create the notification
        entry = entries[0]
        _LOGGER.info("Manually creating dashboard notification for entry %s", entry.entry_id)
        await create_default_dashboard(hass, entry)

    async def handle_set_export_mode(call):
        """Handle set export mode service call."""
        mode = call.data.get("mode")
        min_export_price = call.data.get("min_export_price")
        
        if not mode:
            _LOGGER.error("Export mode is required")
            return
        
        # Get the first config entry for this integration
        entries = hass.config_entries.async_entries(DOMAIN)
        if not entries:
            _LOGGER.error("No Energy Dispatcher integration configured")
            return
        
        entry = entries[0]
        
        # Update the config entry options
        new_options = dict(entry.options or {})
        new_options[CONF_EXPORT_MODE] = mode
        
        if min_export_price is not None:
            new_options[CONF_MIN_EXPORT_PRICE_SEK_PER_KWH] = float(min_export_price)
        
        hass.config_entries.async_update_entry(entry, options=new_options)
        
        # Get coordinator and update export analyzer if it exists
        if entry.entry_id in hass.data[DOMAIN]:
            coordinator = hass.data[DOMAIN][entry.entry_id].get("coordinator")
            if coordinator and hasattr(coordinator, "export_analyzer"):
                analyzer = coordinator.export_analyzer
                analyzer.update_settings(
                    export_mode=mode,
                    min_export_price_sek_per_kwh=min_export_price if min_export_price is not None else None,
                )
                # Trigger coordinator refresh to update sensors
                await coordinator.async_request_refresh()
        
        _LOGGER.info("Export mode updated to: %s (min_price: %s)", mode, min_export_price)
        
        # Send notification
        await hass.services.async_call(
            "persistent_notification",
            "create",
            {
                "title": "Export Mode Updated",
                "message": (
                    f"Export mode set to: {mode}\n"
                    + (f"Minimum export price: {min_export_price:.2f} SEK/kWh" if min_export_price is not None else "")
                ),
                "notification_id": f"{DOMAIN}_export_mode_update",
            },
            blocking=False,
        )

    hass.services.async_register(
        DOMAIN,
        "schedule_appliance",
        handle_schedule_appliance
    )
    
    hass.services.async_register(
        DOMAIN,
        "battery_cost_reset",
        handle_battery_cost_reset
    )
    
    hass.services.async_register(
        DOMAIN,
        "battery_cost_set_soc",
        handle_battery_cost_set_soc
    )
    
    hass.services.async_register(
        DOMAIN,
        "create_dashboard_notification",
        handle_create_dashboard_notification
    )
    
    hass.services.async_register(
        DOMAIN,
        "set_export_mode",
        handle_set_export_mode
    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    hass.data.setdefault(DOMAIN, {})

    # Slå ihop data + options till aktuell konfig
    config: Dict[str, Any] = {**entry.data, **(entry.options or {})}

    coordinator = EnergyDispatcherCoordinator(hass)
    coordinator.entry_id = entry.entry_id

    cfg_lookup = lambda key, default=None: hass.data[DOMAIN][entry.entry_id]["config"].get(key, default)
    dispatcher = EVDispatcher(hass=hass, cfg_lookup=cfg_lookup, entry_id=entry.entry_id)

    # Initialize STORE_MANUAL with values from config if they exist
    # This ensures config_flow values are properly saved
    manual_store = {}
    if CONF_EV_CURRENT_SOC in config:
        manual_store[M_EV_CURRENT_SOC] = float(config[CONF_EV_CURRENT_SOC])
    if CONF_EV_TARGET_SOC in config:
        manual_store[M_EV_TARGET_SOC] = float(config[CONF_EV_TARGET_SOC])
    if CONF_EV_BATT_KWH in config:
        manual_store[M_EV_BATT_KWH] = float(config[CONF_EV_BATT_KWH])
    if CONF_EVSE_MAX_A in config:
        manual_store[M_EVSE_MAX_A] = float(config[CONF_EVSE_MAX_A])
    if CONF_EVSE_PHASES in config:
        manual_store[M_EVSE_PHASES] = float(config[CONF_EVSE_PHASES])
    if CONF_EVSE_VOLTAGE in config:
        manual_store[M_EVSE_VOLTAGE] = float(config[CONF_EVSE_VOLTAGE])
    if CONF_BATT_CAP_KWH in config:
        manual_store[M_HOME_BATT_CAP_KWH] = float(config[CONF_BATT_CAP_KWH])

    # Initialize Battery Energy Cost tracker
    # Try to get capacity from sensor first, fall back to manual config
    battery_capacity = config.get(CONF_BATT_CAP_KWH, 15.0)
    capacity_entity = config.get(CONF_BATT_CAPACITY_ENTITY, "")
    if capacity_entity:
        state = hass.states.get(capacity_entity)
        if state and state.state not in (None, "", "unknown", "unavailable"):
            try:
                sensor_capacity = float(state.state)
                if sensor_capacity > 0:
                    battery_capacity = sensor_capacity
                    _LOGGER.info("Using battery capacity from sensor %s: %.2f kWh", capacity_entity, battery_capacity)
            except (ValueError, TypeError):
                _LOGGER.warning("Invalid capacity value from sensor %s, using manual capacity", capacity_entity)
    
    bec = BatteryEnergyCost(hass, capacity_kwh=battery_capacity)
    await bec.async_load()

    hass.data[DOMAIN][entry.entry_id] = {
        "config": config,
        "flags": {"auto_ev_enabled": True, "auto_planner_enabled": True},
        "coordinator": coordinator,
        "dispatcher": dispatcher,
        "bec": bec,
        STORE_MANUAL: manual_store,
        STORE_ENTITIES: {},
        # Legacy WACE storage (kept for backward compatibility)
        "wace": bec.wace,
        "wace_tot_energy_kwh": bec.energy_kwh,
        "wace_tot_cost_sek": bec.get_total_cost(),
    }

    await coordinator.async_config_entry_first_refresh()
    entry.async_on_unload(entry.add_update_listener(async_options_updated))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Register services
    await _async_register_services(hass)
    
    # Auto-create dashboard if user opts in
    if config.get(CONF_AUTO_CREATE_DASHBOARD, True):
        await create_default_dashboard(hass, entry)
    
    _LOGGER.info("Energy Dispatcher %s init complete", entry.entry_id)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_options_updated(hass: HomeAssistant, entry: ConfigEntry):
    # Uppdatera sammanslagen konfig i store
    st = hass.data[DOMAIN][entry.entry_id]
    config = {**entry.data, **(entry.options or {})}
    st["config"] = config
    
    # Update STORE_MANUAL with new config values if they changed
    # But only if the value doesn't already exist (don't overwrite manual changes)
    manual_store = st.get(STORE_MANUAL, {})
    if CONF_EV_CURRENT_SOC in config and M_EV_CURRENT_SOC not in manual_store:
        manual_store[M_EV_CURRENT_SOC] = float(config[CONF_EV_CURRENT_SOC])
    if CONF_EV_TARGET_SOC in config and M_EV_TARGET_SOC not in manual_store:
        manual_store[M_EV_TARGET_SOC] = float(config[CONF_EV_TARGET_SOC])
    if CONF_EV_BATT_KWH in config and M_EV_BATT_KWH not in manual_store:
        manual_store[M_EV_BATT_KWH] = float(config[CONF_EV_BATT_KWH])
    if CONF_EVSE_MAX_A in config and M_EVSE_MAX_A not in manual_store:
        manual_store[M_EVSE_MAX_A] = float(config[CONF_EVSE_MAX_A])
    if CONF_EVSE_PHASES in config and M_EVSE_PHASES not in manual_store:
        manual_store[M_EVSE_PHASES] = float(config[CONF_EVSE_PHASES])
    if CONF_EVSE_VOLTAGE in config and M_EVSE_VOLTAGE not in manual_store:
        manual_store[M_EVSE_VOLTAGE] = float(config[CONF_EVSE_VOLTAGE])
    if CONF_BATT_CAP_KWH in config and M_HOME_BATT_CAP_KWH not in manual_store:
        manual_store[M_HOME_BATT_CAP_KWH] = float(config[CONF_BATT_CAP_KWH])
    
    # Refresh så koordinatorn får nya värden
    await st["coordinator"].async_request_refresh()
