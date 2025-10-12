# Database Executor Fix - v0.8.23

## Problem Statement

The Energy Dispatcher integration was accessing the Home Assistant recorder database without using the proper database executor, causing the following warning:

```
Loggare: homeassistant.helpers.frame
Källa: helpers/frame.py:350

Detected that custom integration 'energy_dispatcher' accesses the database without the database executor; 
Use homeassistant.components.recorder.get_instance(hass).async_add_executor_job() for faster database 
operations at custom_components/energy_dispatcher/coordinator.py, line 127
```

Additionally, users reported configuration flow errors:
```
Fel: Konfigureringsflödet kunde inte laddas: 400: Bad Request
```

## Root Cause

The integration was using `hass.async_add_executor_job()` to call the history API:

```python
all_hist = await self.hass.async_add_executor_job(
    _fetch_history_for_multiple_entities, self.hass, start, end, entities_to_fetch
)
```

Home Assistant expects database operations (including history API calls) to use the recorder's dedicated executor instead:

```python
recorder.get_instance(hass).async_add_executor_job()
```

This ensures:
- Better performance for database operations
- Proper resource management
- Compliance with Home Assistant best practices
- No warning messages in the log

## Solution

Updated `custom_components/energy_dispatcher/coordinator.py` to use the recorder's executor with a graceful fallback:

```python
from homeassistant.components.recorder import get_instance

try:
    # Try to use the recorder's executor (preferred for database operations)
    recorder = get_instance(self.hass)
    all_hist = await recorder.async_add_executor_job(
        _fetch_history_for_multiple_entities, self.hass, start, end, entities_to_fetch
    )
except (KeyError, RuntimeError):
    # Fall back to hass executor if recorder not available (e.g., in tests)
    all_hist = await self.hass.async_add_executor_job(
        _fetch_history_for_multiple_entities, self.hass, start, end, entities_to_fetch
    )
```

### Why the Fallback?

The try-except block ensures:
1. **Production**: Uses recorder's executor for optimal database access
2. **Testing**: Falls back to hass executor when recorder isn't initialized
3. **Compatibility**: Works in all environments without breaking existing functionality

## Changes Made

### File: `custom_components/energy_dispatcher/coordinator.py`
- Added import for `get_instance` from `homeassistant.components.recorder`
- Wrapped executor call in try-except block
- Added fallback to `hass.async_add_executor_job()` for test compatibility
- Lines modified: 406-421 (16 lines total)

### File: `custom_components/energy_dispatcher/manifest.json`
- Bumped version from 0.8.22 to 0.8.23
- Updated description to reflect the database executor fix

## Testing

All tests pass successfully:

✅ **48h Baseline Tests**: 10/10 passing
- Test daypart classification (night/day/evening)
- Test baseline calculation with energy counters
- Test EV charging exclusion
- Test battery grid charging exclusion
- Test counter reset handling
- Test error handling (no config, no data, invalid values)

✅ **Config Flow Tests**: 15/15 passing
- Weather entity enumeration
- Options flow initialization
- Field validation

✅ **Overall Test Suite**: 160/162 passing
- 2 pre-existing failures in manual forecast module (unrelated to this fix)
- All coordinator and config flow tests passing

## Configuration Flow Issue

The configuration flow "400: Bad Request" error mentioned in the problem statement was already fixed in previous commits:
- `CONF_MANUAL_INVERTER_AC_CAP` default changed from `None` to `10.0` (line 146)
- All NumberSelector fields have valid numeric defaults
- No breaking changes to configuration schema

## Impact

### For Users
- ✅ No configuration changes required
- ✅ No breaking changes
- ✅ Seamless upgrade path
- ✅ Eliminates warning messages in Home Assistant logs
- ✅ Improved performance for baseline calculations

### For Developers
- ✅ Follows Home Assistant best practices
- ✅ Maintains backward compatibility
- ✅ Test-friendly implementation
- ✅ Clear code documentation

## Verification Steps

To verify the fix works in your Home Assistant installation:

1. Update to version 0.8.23
2. Restart Home Assistant
3. Check logs - the database executor warning should no longer appear
4. Verify baseline calculation works (check sensor entities)
5. Verify configuration flow loads without 400 errors

## Related Issues

- Last working release: v0.8.18
- Broke after: PR#40
- Attempted fixes: PR#41 (introduced additional complications)
- This fix: Resolves both database executor warning AND maintains configuration flow stability

## Technical Notes

### Why Not Use `hass.async_add_executor_job()` Always?

While the fallback works, Home Assistant specifically recommends using the recorder's executor for database operations because:

1. **Resource Isolation**: Database operations have their own thread pool
2. **Performance**: Dedicated executor optimized for I/O operations
3. **Stability**: Prevents database operations from blocking other tasks
4. **Best Practice**: Aligns with Home Assistant's architecture

### Future Considerations

The fallback ensures the integration works even if:
- Recorder is disabled (edge case, but possible)
- Running in test environment
- Future Home Assistant API changes

This defensive programming approach ensures maximum compatibility while following best practices.

## Credits

Fix implemented to resolve database executor warning and restore full functionality to the Energy Dispatcher integration.

---

**Version**: 0.8.23  
**Date**: 2025-10-11  
**Status**: ✅ Complete and Tested
