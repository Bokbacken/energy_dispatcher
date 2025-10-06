# Energy Dispatcher - Future Improvements & Suggested PRs

This document outlines planned improvements focused on reducing manual configuration and enhancing usability. The goal is to minimize code-based setup and provide more UI-driven configuration.

## Vision

**Goal**: Create an integration where 90% of functionality is accessible through the UI, requiring minimal to no YAML configuration from users.

**Principles**:
- UI-first: Configuration via Home Assistant's device/integration UI
- Auto-discovery: Automatically detect and configure compatible devices
- Sensible defaults: Work well out-of-box without extensive tuning
- Progressive disclosure: Hide complexity from beginners, available for advanced users
- Dashboard generation: Auto-create basic dashboards

## High Priority Improvements

### PR-1: Automated Dashboard Generation ✅ **COMPLETED**

**Problem**: Users need to manually create dashboards by copying YAML code

**Solution**: Generate a basic dashboard automatically when integration is set up

**Status**: ✅ Implemented in v0.8.7+

**What was delivered**:
- Added `auto_create_dashboard` configuration option (default: True) in config flow
- Created `create_default_dashboard()` function that shows a persistent notification
- Notification provides users with:
  - Welcome message and setup instructions
  - Direct link to Dashboard Setup Guide
  - Entity naming pattern for dashboard creation
- Graceful error handling ensures setup never fails due to dashboard creation issues
- Can be disabled by setting `auto_create_dashboard: false` in configuration

**Implementation**:
```python
# In __init__.py after successful setup
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # ... existing setup code ...
    
    # Auto-create dashboard if user opts in
    if config.get(CONF_AUTO_CREATE_DASHBOARD, True):
        await create_default_dashboard(hass, entry)
    
    return True

async def create_default_dashboard(hass: HomeAssistant, entry: ConfigEntry):
    """Create a default Energy Dispatcher dashboard."""
    # Shows a persistent notification with setup instructions
    # and links to comprehensive dashboard guide
```

**Benefits**:
- ✅ Users receive immediate guidance on dashboard setup
- ✅ Reduces barrier to entry for new users
- ✅ Provides consistent onboarding experience
- ✅ Opt-in/opt-out flexibility via configuration

---

### PR-2: Integration Setup Wizard with Device Discovery

**Problem**: Users need to know entity names and manually enter them

**Solution**: Multi-step setup wizard with auto-discovery of compatible devices

**Implementation**:
```python
class EnergyDispatcherFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2
    
    async def async_step_user(self, user_input=None):
        """Initial setup step - choose configuration method."""
        return self.async_show_menu(
            step_id="user",
            menu_options=["auto_discover", "manual_setup", "import_config"]
        )
    
    async def async_step_auto_discover(self, user_input=None):
        """Discover compatible devices automatically."""
        discovered = await self._discover_devices()
        
        return self.async_show_form(
            step_id="auto_discover",
            data_schema=vol.Schema({
                vol.Required("battery_system"): vol.In(discovered["batteries"]),
                vol.Required("ev_charger"): vol.In(discovered["chargers"]),
                vol.Optional("solar_inverter"): vol.In(discovered["solar"]),
            }),
            description_placeholders={
                "discovered_count": len(discovered["batteries"]) + 
                                   len(discovered["chargers"]) + 
                                   len(discovered["solar"])
            }
        )
    
    async def _discover_devices(self):
        """Auto-discover compatible devices."""
        batteries = {}
        chargers = {}
        solar = {}
        
        # Scan for known integrations
        for entry in self.hass.config_entries.async_entries():
            # Detect Huawei Solar
            if entry.domain == "huawei_solar":
                batteries[entry.entry_id] = entry.title
            
            # Detect common EV chargers
            elif entry.domain in ["easee", "zaptec", "wallbox"]:
                chargers[entry.entry_id] = entry.title
            
            # Detect solar systems
            elif entry.domain in ["solaredge", "fronius", "solarman"]:
                solar[entry.entry_id] = entry.title
        
        # Scan entities for battery and charger patterns
        for entity_id in self.hass.states.async_entity_ids():
            # Battery detection
            if "battery" in entity_id and "soc" in entity_id:
                # Extract integration from entity_id
                integration = entity_id.split(".")[0]
                if integration not in batteries:
                    batteries[entity_id] = f"Battery ({entity_id})"
            
            # Charger detection
            if "charger" in entity_id or "wallbox" in entity_id:
                if entity_id not in chargers:
                    chargers[entity_id] = f"Charger ({entity_id})"
        
        return {
            "batteries": batteries,
            "chargers": chargers,
            "solar": solar,
        }
```

**Benefits**:
- Dramatically reduces setup time
- Eliminates typing errors in entity names
- Better user experience for beginners

**Estimated Effort**: High (5-7 days)

---

### PR-3: Visual Dashboard Builder in Config Flow

**Problem**: Dashboard creation requires YAML knowledge

**Solution**: Build dashboard cards through integration options UI

**Implementation**:
```python
async def async_step_dashboard_builder(self, user_input=None):
    """Configure dashboard preferences."""
    if user_input is not None:
        # Save preferences and generate dashboard
        self.config_data["dashboard_config"] = user_input
        await self._create_dashboard_from_config(user_input)
        return self.async_create_entry(
            title=self.config_data["name"],
            data=self.config_data
        )
    
    return self.async_show_form(
        step_id="dashboard_builder",
        data_schema=vol.Schema({
            vol.Required("include_price_graph", default=True): bool,
            vol.Required("include_solar_graph", default=True): bool,
            vol.Required("include_battery_graph", default=True): bool,
            vol.Required("include_controls", default=True): bool,
            vol.Required("include_settings", default=True): bool,
            vol.Optional("graph_hours", default=48): vol.In([24, 48, 72]),
            vol.Optional("dashboard_theme", default="auto"): vol.In([
                "auto", "light", "dark"
            ]),
        }),
        description_placeholders={
            "info": "Select which components to include in your dashboard"
        }
    )
```

**Benefits**:
- No YAML knowledge required
- Customizable without editing files
- Can regenerate dashboard easily

**Estimated Effort**: Medium-High (4-5 days)

---

### PR-4: Vehicle API Integration (Tesla, VW ID, Kia/Hyundai)

**Problem**: Users must manually update EV SOC

**Solution**: Direct API integration for popular EV brands

**Implementation**:
```python
# In vehicle_manager.py
class VehicleAPIAdapter:
    """Base class for vehicle API adapters."""
    
    async def get_soc(self) -> float:
        """Get current state of charge."""
        raise NotImplementedError
    
    async def get_range(self) -> float:
        """Get estimated range in km."""
        raise NotImplementedError
    
    async def is_charging(self) -> bool:
        """Check if vehicle is currently charging."""
        raise NotImplementedError

class TeslaAPIAdapter(VehicleAPIAdapter):
    """Tesla API integration using tesla_custom integration."""
    
    def __init__(self, hass: HomeAssistant, vehicle_id: str):
        self.hass = hass
        self.vehicle_id = vehicle_id
    
    async def get_soc(self) -> float:
        """Get SOC from Tesla integration."""
        entity = f"sensor.{self.vehicle_id}_battery"
        state = self.hass.states.get(entity)
        return float(state.state) if state else None
    
    async def get_range(self) -> float:
        """Get range from Tesla integration."""
        entity = f"sensor.{self.vehicle_id}_range"
        state = self.hass.states.get(entity)
        return float(state.state) if state else None
    
    async def is_charging(self) -> bool:
        """Check if charging from Tesla integration."""
        entity = f"binary_sensor.{self.vehicle_id}_charging"
        state = self.hass.states.get(entity)
        return state.state == "on" if state else False

class VWIDAPIAdapter(VehicleAPIAdapter):
    """Volkswagen ID API integration."""
    # Implementation for VW Connect integration
    pass

class KiaHyundaiAPIAdapter(VehicleAPIAdapter):
    """Kia/Hyundai API integration."""
    # Implementation for Kia/Hyundai integration
    pass

# In config flow
async def async_step_vehicle_config(self, user_input=None):
    """Configure vehicle with optional API."""
    available_apis = await self._detect_vehicle_apis()
    
    return self.async_show_form(
        step_id="vehicle_config",
        data_schema=vol.Schema({
            vol.Required("vehicle_type"): vol.In({
                "manual": "Manual SOC Entry",
                **available_apis
            }),
            vol.Optional("vehicle_entity"): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="sensor",
                    device_class="battery"
                )
            ),
        })
    )
```

**Benefits**:
- Automatic SOC updates
- More accurate charge timing
- Reduced user interaction needed

**Estimated Effort**: High (7-10 days per brand)

---

### PR-5: Pre-configured Charger Profiles

**Problem**: Users need to manually enter charger specifications

**Solution**: Database of common chargers with auto-configuration

**Implementation**:
```python
# In charger_profiles.py
CHARGER_PROFILES = {
    "easee_home": {
        "name": "Easee Home",
        "max_current": 32,
        "phases": 3,
        "voltage": 230,
        "dynamic_current": True,
        "api_control": True,
    },
    "wallbox_pulsar": {
        "name": "Wallbox Pulsar Plus",
        "max_current": 32,
        "phases": 1,
        "voltage": 230,
        "dynamic_current": True,
        "api_control": True,
    },
    "zaptec_go": {
        "name": "Zaptec Go",
        "max_current": 32,
        "phases": 3,
        "voltage": 230,
        "dynamic_current": True,
        "api_control": True,
    },
    "generic_16a_1phase": {
        "name": "Generic 16A Single Phase",
        "max_current": 16,
        "phases": 1,
        "voltage": 230,
        "dynamic_current": False,
        "api_control": False,
    },
    "generic_16a_3phase": {
        "name": "Generic 16A Three Phase",
        "max_current": 16,
        "phases": 3,
        "voltage": 230,
        "dynamic_current": False,
        "api_control": False,
    },
}

async def async_step_charger_select(self, user_input=None):
    """Select charger from profiles or custom."""
    if user_input is not None:
        if user_input["charger"] == "custom":
            return await self.async_step_charger_custom()
        else:
            # Use profile
            profile = CHARGER_PROFILES[user_input["charger"]]
            self.config_data["charger"] = profile
            return await self.async_step_charger_entities()
    
    charger_options = {
        profile_id: profile["name"] 
        for profile_id, profile in CHARGER_PROFILES.items()
    }
    charger_options["custom"] = "Custom Configuration"
    
    return self.async_show_form(
        step_id="charger_select",
        data_schema=vol.Schema({
            vol.Required("charger"): vol.In(charger_options),
        }),
        description_placeholders={
            "info": "Select your charger model or choose custom"
        }
    )
```

**Benefits**:
- One-click charger setup
- Accurate specifications
- Faster configuration

**Estimated Effort**: Low-Medium (2-3 days)

---

### PR-6: Interactive Setup Tutorial

**Problem**: Users don't understand the integration's capabilities

**Solution**: In-app tutorial overlay on first dashboard visit

**Implementation**:
```javascript
// As a custom Lovelace card
class EnergyDispatcherTutorial extends HTMLElement {
    set hass(hass) {
        if (!this.content) {
            this.innerHTML = `
                <ha-card>
                    <div class="tutorial-overlay">
                        <h2>Welcome to Energy Dispatcher!</h2>
                        <p>Let's take a quick tour...</p>
                        <button class="start-tour">Start Tour</button>
                        <button class="skip-tour">Skip</button>
                    </div>
                </ha-card>
            `;
            
            this.querySelector('.start-tour').addEventListener('click', () => {
                this.startTour();
            });
            
            this.querySelector('.skip-tour').addEventListener('click', () => {
                this.dismissTutorial();
            });
        }
    }
    
    startTour() {
        const steps = [
            {
                element: '.quick-controls',
                content: 'Use these buttons to override automatic decisions',
            },
            {
                element: '.price-graph',
                content: 'This graph shows electricity prices and solar forecast',
            },
            {
                element: '.optimization-status',
                content: 'Here you can see what the system is doing and why',
            },
        ];
        
        // Implement tour steps with highlighting
    }
}

customElements.define('energy-dispatcher-tutorial', EnergyDispatcherTutorial);
```

**Benefits**:
- Better user onboarding
- Increased understanding
- Reduced support requests

**Estimated Effort**: Medium (3-4 days)

---

## Medium Priority Improvements

### PR-7: Preset Configuration Bundles

**Problem**: Users need to configure many settings individually

**Solution**: Pre-configured bundles for common scenarios

**Implementation**:
```python
CONFIGURATION_PRESETS = {
    "swedish_villa": {
        "name": "Swedish Villa (15 kWh battery, 1 EV)",
        "price_vat": 0.25,
        "price_tax": 0.395,
        "price_transfer": 0.50,
        "batt_cap_kwh": 15.0,
        "batt_soc_floor": 10.0,
        "ev_batt_kwh": 75.0,
        "evse_max_a": 16,
        "evse_phases": 3,
    },
    "apartment_small": {
        "name": "Apartment (No battery, 1 small EV)",
        "price_vat": 0.25,
        "batt_cap_kwh": 0,
        "ev_batt_kwh": 40.0,
        "evse_max_a": 16,
        "evse_phases": 1,
    },
    "large_home": {
        "name": "Large Home (30 kWh battery, 2 EVs)",
        "price_vat": 0.25,
        "price_tax": 0.395,
        "batt_cap_kwh": 30.0,
        "ev_batt_kwh": 75.0,
        "evse_max_a": 32,
        "evse_phases": 3,
    },
}
```

**Benefits**:
- Quick setup for typical scenarios
- Better defaults
- Learning tool for understanding settings

**Estimated Effort**: Low (1-2 days)

---

### PR-8: Smart Entity Detection

**Problem**: Integration doesn't know which entities relate to which devices

**Solution**: Machine learning-based entity classification

**Implementation**:
```python
class EntityClassifier:
    """Classify entities by their purpose using pattern matching."""
    
    BATTERY_PATTERNS = [
        r".*battery.*soc",
        r".*battery.*charge",
        r".*battery.*level",
        r".*battery.*percent",
    ]
    
    CHARGER_PATTERNS = [
        r".*charger.*power",
        r".*wallbox.*current",
        r".*evse.*status",
    ]
    
    SOLAR_PATTERNS = [
        r".*solar.*power",
        r".*pv.*production",
        r".*inverter.*output",
    ]
    
    @classmethod
    def classify_entity(cls, entity_id: str, attributes: dict) -> str:
        """Classify entity based on ID and attributes."""
        import re
        
        # Check battery patterns
        for pattern in cls.BATTERY_PATTERNS:
            if re.match(pattern, entity_id, re.IGNORECASE):
                return "battery"
        
        # Check charger patterns
        for pattern in cls.CHARGER_PATTERNS:
            if re.match(pattern, entity_id, re.IGNORECASE):
                return "charger"
        
        # Check solar patterns
        for pattern in cls.SOLAR_PATTERNS:
            if re.match(pattern, entity_id, re.IGNORECASE):
                return "solar"
        
        return "unknown"
```

**Benefits**:
- Faster setup
- Fewer errors
- Better user experience

**Estimated Effort**: Medium (3-4 days)

---

### PR-9: Configuration Import/Export

**Problem**: Users can't share configurations or migrate easily

**Solution**: Import/export configuration as JSON

**Implementation**:
```python
async def async_step_import_config(self, user_input=None):
    """Import configuration from JSON file."""
    if user_input is not None:
        try:
            config_json = json.loads(user_input["config_json"])
            validated_config = validate_imported_config(config_json)
            return self.async_create_entry(
                title=validated_config["name"],
                data=validated_config
            )
        except (json.JSONDecodeError, ValueError) as err:
            return self.async_show_form(
                step_id="import_config",
                errors={"base": "invalid_json"},
            )
    
    return self.async_show_form(
        step_id="import_config",
        data_schema=vol.Schema({
            vol.Required("config_json"): str,
        }),
        description_placeholders={
            "info": "Paste your Energy Dispatcher configuration JSON"
        }
    )

# Add export service
async def async_export_config(hass: HomeAssistant, call: ServiceCall):
    """Export current configuration as JSON."""
    entry_id = call.data.get("entry_id")
    entry = hass.config_entries.async_get_entry(entry_id)
    
    export_data = {
        "version": 1,
        "name": entry.title,
        "data": entry.data,
        "options": entry.options,
        "exported_at": datetime.now().isoformat(),
    }
    
    # Send to persistent notification
    await hass.services.async_call(
        "persistent_notification",
        "create",
        {
            "title": "Configuration Exported",
            "message": f"```json\n{json.dumps(export_data, indent=2)}\n```",
            "notification_id": "energy_dispatcher_export",
        },
    )
```

**Benefits**:
- Easy backup/restore
- Share configurations
- Migrate between systems

**Estimated Effort**: Low-Medium (2-3 days)

---

### PR-10: Real-time Optimization Visualization

**Problem**: Users don't see what the optimizer is planning

**Solution**: Visual timeline showing planned actions

**Implementation**:
```python
class OptimizationTimelineSensor(SensorEntity):
    """Sensor exposing optimization timeline."""
    
    @property
    def state(self):
        """Return number of planned actions."""
        return len(self._timeline)
    
    @property
    def extra_state_attributes(self):
        """Return timeline as attribute."""
        return {
            "timeline": [
                {
                    "time": action.time.isoformat(),
                    "action": action.action_type,
                    "target": action.target_device,
                    "value": action.target_value,
                    "reason": action.reason,
                }
                for action in self._timeline
            ],
            "next_action": self._timeline[0] if self._timeline else None,
        }
```

With corresponding dashboard card:

```yaml
type: custom:energy-dispatcher-timeline
entity: sensor.energy_dispatcher_optimization_timeline
hours: 24
show_legend: true
color_by_action:
  charge_battery: '#4CAF50'
  discharge_battery: '#FF9800'
  charge_ev: '#2196F3'
  pause_ev: '#9E9E9E'
```

**Benefits**:
- Transparency of decisions
- User confidence
- Easier debugging

**Estimated Effort**: High (5-6 days)

---

## Low Priority / Nice-to-Have

### PR-11: Mobile App Integration

**Problem**: Users need to open Home Assistant to control

**Solution**: Dedicated mobile app views and notifications

**Estimated Effort**: Very High (15-20 days)

---

### PR-12: Voice Control Integration

**Problem**: Manual interaction required

**Solution**: Alexa/Google Assistant integration

**Estimated Effort**: Medium (3-5 days)

---

### PR-13: Machine Learning for Load Prediction

**Problem**: Baseline load uses simple calculations

**Solution**: ML model trained on historical usage

**Estimated Effort**: Very High (20+ days)

---

### PR-14: Community Dashboard Templates

**Problem**: Users want different dashboard styles

**Solution**: Template gallery in integration

**Estimated Effort**: Medium (4-5 days)

---

### PR-15: Cost Report Generation

**Problem**: No easy way to see savings

**Solution**: Automated monthly reports with comparisons

**Estimated Effort**: Medium (3-4 days)

---

## Implementation Roadmap

### Phase 1: Essential Usability (Q1 2024)
- PR-1: Automated Dashboard Generation
- PR-5: Pre-configured Charger Profiles
- PR-7: Preset Configuration Bundles
- PR-9: Configuration Import/Export

**Goal**: Reduce setup time by 60%

### Phase 2: Advanced Discovery (Q2 2024)
- PR-2: Integration Setup Wizard with Device Discovery
- PR-8: Smart Entity Detection
- PR-3: Visual Dashboard Builder

**Goal**: 80% of users can configure without documentation

### Phase 3: Intelligence & Integration (Q3 2024)
- PR-4: Vehicle API Integration (Tesla)
- PR-4: Vehicle API Integration (VW ID)
- PR-10: Real-time Optimization Visualization

**Goal**: Fully automated operation for API-enabled vehicles

### Phase 4: Polish & Enhancement (Q4 2024)
- PR-6: Interactive Setup Tutorial
- PR-14: Community Dashboard Templates
- PR-15: Cost Report Generation

**Goal**: Best-in-class user experience

### Phase 5: Advanced Features (2025)
- PR-13: Machine Learning for Load Prediction
- PR-11: Mobile App Integration
- PR-12: Voice Control Integration

**Goal**: Industry-leading smart home energy management

---

## Contributing

These improvements are prioritized based on:
1. **Impact**: How many users benefit
2. **Effort**: Development time required
3. **Dependencies**: What needs to be in place first

To contribute to any of these PRs:
1. Comment on the related issue
2. Review the implementation plan
3. Submit a draft PR for review
4. Work with maintainers to refine

## Measuring Success

### Key Metrics

1. **Setup Time**: Target < 10 minutes for basic setup
2. **Configuration Errors**: Target < 5% error rate during setup
3. **Support Requests**: Target 50% reduction in "how to configure" questions
4. **User Satisfaction**: Target 4.5/5 rating
5. **Dashboard Adoption**: Target 90% of users using auto-generated dashboard

### User Feedback Collection

Implement anonymous usage statistics:
```python
# In coordinator.py
async def _async_send_analytics(self):
    """Send anonymous usage statistics."""
    if self._config.get("allow_analytics", False):
        stats = {
            "version": VERSION,
            "setup_method": "auto_discover" or "manual",
            "features_used": self._get_features_used(),
            "error_count": self._error_count,
            "uptime_hours": self._uptime.total_seconds() / 3600,
        }
        
        # Send to analytics endpoint (anonymized)
        await self._send_stats(stats)
```

---

## Summary

The future of Energy Dispatcher is **UI-first, code-minimal**. By implementing these improvements, we can:

- ✅ Reduce setup time from 1-2 hours to < 10 minutes
- ✅ Eliminate need for YAML knowledge for 90% of users
- ✅ Auto-configure compatible devices
- ✅ Provide instant, working dashboard
- ✅ Enable easy customization through UI

**Target User Experience**:
> "I installed Energy Dispatcher, it detected my Huawei battery and Easee charger, created a dashboard, and started optimizing immediately. I didn't need to read any documentation or write any code."

This is achievable with the proposed PRs and will make Energy Dispatcher the most user-friendly energy management integration in Home Assistant.

## Feedback

Have ideas for other improvements? Want to help implement these? Open an issue or discussion on [GitHub](https://github.com/Bokbacken/energy_dispatcher/issues).
