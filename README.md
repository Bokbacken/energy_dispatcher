# Energy Dispatcher (beta)

A modular Home Assistant custom integration for price- and weather-aware battery/EV control with 15‑minute Nord Pool support. MVP focuses on Huawei SUN2000/LUNA (via huawei_solar) and generic EVSE control. Architecture is adapter-based to support more brands.

## Features (MVP)
- Plan 15‑minute slots: 
  - Night greedy charging to reach a morning SoC target within power limits
  - Day discharge only when current price > Battery Effective Cost (BEC) + margin
- Battery Effective Cost (weighted cost of stored energy)
- Buttons: force battery charge 30/60/120 min
- Switches: optimize battery, global pause
- Works with price list sensors providing `attributes.data: [{start, end, price}]` (we provide templates in docs)
- Extensible adapters (Huawei battery included)

## Install (HACS custom repo)
1. Go to HACS → Integrations → 3‑dot menu → Custom repositories
2. Add `https://github.com/YOUR_GITHUB/energy_dispatcher` as type Integration
3. Install “Energy Dispatcher”
4. Restart Home Assistant

## Configure
Settings → Devices & Services → Add Integration → Energy Dispatcher

You will map:
- Battery brand (Huawei)
- Battery SoC sensor
- Price list sensors (today and tomorrow). Each must expose `attributes.data` as a list of objects:
