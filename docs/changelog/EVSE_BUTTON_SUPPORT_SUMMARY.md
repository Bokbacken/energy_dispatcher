# EVSE Button Support - Release v0.8.26

## Problem Statement

The Energy Dispatcher integration's config flow only accepted `switch` entities for EVSE start and stop controls. However, many EV chargers use `button` entities instead of switches:
- Some chargers have separate start and stop buttons
- Others have a single combined switch
- Some might have two separate switches

This caused validation errors when users tried to select button entities during configuration:
```
Entity button.43201610a_1_starta_laddning belongs to domain button, expected ['switch']
Entity button.43201610a_1_stoppa_laddning belongs to domain button, expected ['switch']
```

## Solution

Updated the entity selector configuration to accept both `switch` and `button` domains, allowing users to select the appropriate entity type for their charger.

## Changes Made

### 1. config_flow.py
Changed the domain restriction from a single domain to a list of domains:
```python
# Before
vol.Optional(CONF_EVSE_START_SWITCH, ...): selector.EntitySelector(
    selector.EntitySelectorConfig(domain="switch")
)

# After
vol.Optional(CONF_EVSE_START_SWITCH, ...): selector.EntitySelector(
    selector.EntitySelectorConfig(domain=["switch", "button"])
)
```

### 2. translations/en.json
Updated all user-facing strings to reflect the support for both entity types:
- Labels: "EVSE Start Switch Entity" → "EVSE Start Switch/Button Entity"
- Descriptions: "Switch entity to start EV charging" → "Switch or button entity to start EV charging"

### 3. translations/sv.json
Updated Swedish translations similarly:
- Labels: "EVSE startknapp-entitet" → "EVSE startbrytare/knapp-entitet"
- Descriptions: "Brytar-entitet för att starta EV-laddning" → "Brytare- eller knapp-entitet för att starta EV-laddning"

### 4. manifest.json
- Bumped version from 0.8.25 to 0.8.26
- Updated description to reflect the enhancement

## Technical Details

The underlying code in `ev_dispatcher.py` already supported button entities through the `_press_or_turn()` method:
```python
async def _press_or_turn(self, entity_id: str, on: bool):
    domain = entity_id.split(".")[0]
    if domain == "button":
        await self.hass.services.async_call("button", "press", ...)
    elif domain in ("switch", "input_boolean"):
        service = "turn_on" if on else "turn_off"
        await self.hass.services.async_call(domain, service, ...)
```

This means the functionality was already present - we just needed to update the config flow validation to allow button entities to be selected.

## Supported Charger Configurations

After this change, the integration supports all these configurations:

1. **Two buttons** (start + stop)
   - EVSE Start: `button.charger_start`
   - EVSE Stop: `button.charger_stop`

2. **Single switch** (on/off)
   - EVSE Start: `switch.charger_charging`
   - EVSE Stop: `switch.charger_charging` (same entity)

3. **Two switches** (separate enable/disable)
   - EVSE Start: `switch.charger_enable`
   - EVSE Stop: `switch.charger_disable`

4. **Mixed button and switch**
   - EVSE Start: `button.charger_start`
   - EVSE Stop: `switch.charger_pause`

## Testing

### Validation Performed
- ✅ Python syntax validation of config_flow.py
- ✅ JSON validation of all translation files
- ✅ JSON validation of manifest.json
- ✅ CodeQL security scan (0 vulnerabilities)
- ✅ Verified entity selector configuration accepts both domains
- ✅ Verified ev_dispatcher.py already handles buttons correctly

### User Impact
Users can now:
- Select button entities during initial setup
- Select button entities when updating configuration via options flow
- Use any combination of switches and buttons that matches their charger setup

No breaking changes - existing configurations with switch entities continue to work exactly as before.

## Related Files
- `custom_components/energy_dispatcher/config_flow.py`
- `custom_components/energy_dispatcher/ev_dispatcher.py`
- `custom_components/energy_dispatcher/translations/en.json`
- `custom_components/energy_dispatcher/translations/sv.json`
- `custom_components/energy_dispatcher/manifest.json`

## Version History
- v0.8.18: Last known working release
- v0.8.19-0.8.24: Various fixes (PR#40, PR#41)
- v0.8.25: Fixed NumberSelector step values and missing DEFAULTS
- v0.8.26: Added button support for EVSE start/stop entities (this release)
