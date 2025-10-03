# Energy Dispatcher (HACS)

Ett modulärt Home Assistant-tillägg för smart styrning av batteri och EV-laddning baserat på elpris, solprognos och husets förbrukning – med tydliga over-ride-knappar.

## Funktioner (MVP)
- Prisberikning: Spot (Nordpool custom) + energiskatt, överföring, påslag, moms (+ valfri fast avgift/h).
- Battery WACE: Snittkostnad (SEK/kWh) för energin i batteriet (“price battery power”).
- Huawei LUNA2K: Stöd för forcible_charge via adapter (grid force charge).
- EV manual: Ange SoC current/target och få energi- och tidsestimat. Styr generisk EVSE (start/stop + 6–16A).
- Planner: Enkel heuristik för 24–48h med billiga timmar + solprognos.
- Over-rides: Force EV charge X min, Pause EV X min, Force battery charge X min.

## Installation
- Lägg till detta repo i HACS som “Custom repository”.
- Installera “Energy Dispatcher”.
- Starta om Home Assistant.

## Konfiguration
Gå till Inställningar → Enheter & tjänster → Lägg till integration → Energy Dispatcher

Du kommer kunna ange:
- Spot-priskälla (sensor.nordpool_*), avgifter/moms/fast.
- Batteri: kapacitet, SoC-entity, max charge/discharge, Huawei device_id.
- EV/EVSE: manuellt läge (SoC/target, batt kWh), EVSE start/stop-entities + “number” för Ampere, faser/volt.
- Forecast: Forecast.Solar (lat/lon, plane(s), horizon); ev. API-key.

## Dashboard-exempel (Mushroom)
```yaml
type: vertical-stack
cards:
  - type: entities
    title: Energi & Pris
    entities:
      - entity: sensor.energy_dispatcher_enriched_price
        name: Berikat elpris (SEK/kWh)
      - entity: sensor.energy_dispatcher_battery_cost
        name: Batteriets snittkostnad (SEK/kWh)
      - entity: sensor.energy_dispatcher_battery_runtime
        name: Batteriets driftstid (h)

  - type: horizontal-stack
    cards:
      - type: button
        name: EV Force 60m
        tap_action:
          action: call-service
          service: energy_dispatcher.ev_force_charge
          service_data: {duration: 60, current: 16}
      - type: button
        name: EV Pause 30m
        tap_action:
          action: call-service
          service: energy_dispatcher.ev_pause
          service_data: {duration: 30}
      - type: button
        name: Batt Force 60m
        tap_action:
          action: call-service
          service: energy_dispatcher.force_battery_charge
          service_data: {power_w: 10000, duration: 60}
