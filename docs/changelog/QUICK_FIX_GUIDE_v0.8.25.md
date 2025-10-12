# Quick Fix Guide - Energy Dispatcher v0.8.25

## Problem
Configuration flow fails with "400: Bad Request" error since v0.8.19.

## Solution
Upgrade to v0.8.25.

## What Was Wrong?

### Critical Bug
- Latitude/longitude inputs used `step=0.0001` (too small)
- Home Assistant requires `step >= 0.001` for NumberSelector
- This caused the entire config form to fail loading

### Additional Issues
- 9 optional fields were missing from DEFAULTS dictionary
- Could cause issues when rebuilding the form after validation errors

## What Was Fixed?

1. **Changed latitude/longitude step from 0.0001 to 0.001**
   - Still allows 3 decimal places (e.g., 56.697)
   - 0.001° ≈ 111 meters at equator (sufficient for solar forecasting)

2. **Added 9 missing DEFAULTS entries:**
   - Huawei device ID
   - EV charger switches and current control
   - Forecast.Solar API key, coordinates, and configuration

## How to Upgrade

### HACS Users
1. Go to HACS → Integrations
2. Find Energy Dispatcher
3. Click Update
4. Restart Home Assistant

### Manual Installation
1. Download v0.8.25
2. Replace `custom_components/energy_dispatcher/` folder
3. Restart Home Assistant

## After Upgrade

✅ **New Installations**
- Configuration form loads without errors
- All fields work correctly
- Can configure latitude/longitude with 0.001° precision

✅ **Existing Installations**
- Continue to work without any action
- Can now modify configuration without errors

✅ **Previously Failed Installations**
- Delete the failed entry (if any)
- Add Energy Dispatcher again
- Configuration will work correctly

## No Action Required
- No breaking changes
- Existing configurations continue to work
- Upgrade is automatic

## Testing
- All 27 unit tests pass
- All 23 Python files compile successfully
- Schema validation confirmed working

## Version History
- **v0.8.18** - Last working version
- **v0.8.19-v0.8.24** - Broken (400 error)
- **v0.8.25** - Fixed (this release)

## Need Help?
If you still experience issues after upgrading to v0.8.25:
1. Check you're actually running v0.8.25 (Settings → Devices → Energy Dispatcher)
2. Clear browser cache (Ctrl+Shift+R or Cmd+Shift+R)
3. Restart Home Assistant
4. Check Home Assistant logs for any errors
5. Open an issue on GitHub if problem persists

## Technical Details
See `CONFIG_FLOW_FIX_v0.8.25.md` for full technical documentation.
