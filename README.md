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

[{ "start": "2025-09-28T11:00:00+02:00", "end": "...", "price": 0.31234 }, ...]

See “Create price sensors” below.
- Optional: PV power (W), House load (W)
- Huawei device_id (for services)
- Targets and limits (SoC floor, morning target, max grid charge kW, etc.)

## Create price list sensors (built-in Nord Pool)
Use the built-in service `nordpool.get_prices_for_date` to build two template sensors (today + tomorrow). Example (SE4, SEK):

```yaml
template:
- trigger:
    - trigger: time_pattern
      minutes: /10
    - trigger: homeassistant
      event: start
  action:
    - action: nordpool.get_prices_for_date
      data:
        config_entry: YOUR_CONFIG_ENTRY_ID
        date: "{{ now().date() }}"
        areas: SE4
        currency: SEK
      response_variable: today_price
    - action: nordpool.get_prices_for_date
      data:
        config_entry: YOUR_CONFIG_ENTRY_ID
        date: "{{ (now() + timedelta(days=1)).date() }}"
        areas: SE4
        currency: SEK
      response_variable: tomorrow_price
  sensor:
    - name: Nord Pool SE4 Idag prislista
      state: "{{ now() }}"
      attributes:
        data: >
          {% set out = [] %}
          {% for p in (today_price['SE4'] or []) %}
            {% set _ = out.append({'start': (p.start|as_datetime|as_local).isoformat(),
                                   'end':   (p.end|as_datetime|as_local).isoformat(),
                                   'price': (p.price|float/1000)}) %}
          {% endfor %}
          {{ out }}
    - name: Nord Pool SE4 Imorgon prislista
      state: "{{ now() }}"
      attributes:
        data: >
          {% set out = [] %}
          {% for p in (tomorrow_price['SE4'] or []) %}
            {% set _ = out.append({'start': (p.start|as_datetime|as_local).isoformat(),
                                   'end':   (p.end|as_datetime|as_local).isoformat(),
                                   'price': (p.price|float/1000)}) %}
          {% endfor %}
          {{ out }}
Adjust division if your price unit differs. The integration reads both sensors and merges into a 48h series.

## Dashboard (example)
ApexCharts (line) using your price sensors:

yaml
Copy
type: custom:apexcharts-card
chart_type: line
graph_span: 48h
header:
  show: true
  title: Nord Pool (idag & imorgon)
series:
  - name: Pris
    type: custom
    data_generator: |
      EVAL:(() => {
        const t = hass.states['sensor.nord_pool_se4_idag_prislista']?.attributes?.data || [];
        const tm = hass.states['sensor.nord_pool_se4_imorgon_prislista']?.attributes?.data || [];
        return t.concat(tm).map(p => [new Date(p.start).getTime(), Number(p.price)||0]);
      })()
Show plan vs SOC with additional cards (coming as example dashboard in future versions).

## How it works
A coordinator rebuilds a plan every 15 min (or when prices publish).
Planner (greedy):
Night: choose cheapest slots until the SoC target can be reached given max grid charge kW and battery efficiency.
Day: discharge slots where price is higher than BEC + margin.
Dispatcher: every minute, if a slot starts now, it issues the appropriate service call:
Huawei: huawei_solar.forcible_charge / forcible_discharge
BEC (Battery Effective Cost): weighted average cost of energy stored in the battery. Future versions will estimate PV vs grid share and update BEC in real time.
Entities
Switches
switch.energy_dispatcher_optimize_battery
switch.energy_dispatcher_pause
Buttons
button.energy_dispatcher_force_batt_charge_30m
button.energy_dispatcher_force_batt_charge_60m
button.energy_dispatcher_force_batt_charge_120m
Sensors
sensor.energy_dispatcher_plan_length (debug)
Services
energy_dispatcher.force_batt_charge (minutes, power_kw)
energy_dispatcher.stop_batt_charge
Roadmap
BEC real-time update with PV/grid share
EV planning (EVSE and manual SOC), “ready by” scheduling
More battery adapters (Victron/Fronius/GoodWe)
TOU writer for brands with schedules
Example dashboard pack and blueprints
Contributing
PRs welcome. Add new adapters under custom_components/energy_dispatcher/adapters/ by subclassing BatteryAdapter.
