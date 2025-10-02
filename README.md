### Energy Dispatcher

Energy Dispatcher är en modulär Home Assistant-integration som planerar och styr energiflöden baserat på solprognos, spotpris, batteri och elbilsladdning. Fokus ligger på att optimera för lågkostnadsperioder, nyttja solkraft och göra manuella överstyrningar enkla via dashboard.

#### Funktioner
- Hämtar solprognos direkt via Forecast.Solar med stöd för flera panelsträngar och horisont-profiler.
- Hämtar aktuella och framtida elpriser via Nord Pool API eller befintlig Nord Pool-sensor (fallback).
- Planerar batteriladdning/urladdning, EV-laddning och tunga hushållslaster.
- Tjänster för att forcera laddning/urladdning av batteri, pausa/återuppta EV-laddning, sätta manuellt SOC m.m.
- Auto-dispatch kan slås av/på via switch (till exempel för att låta familjen styra manuellt).
- Sensorer, knappar och switchar som gör det lätt att bygga ett snyggt Lovelace-dashboard.

#### Installation via HACS
1. Lägg koden i en GitHub-repository, t.ex. `https://github.com/dittkonto/energy_dispatcher`.
2. I Home Assistant, gå in i HACS → Integrations → Custom repositories → lägg till URL och välj kategori `Integration`.
3. Installera och starta om Home Assistant.

#### Konfiguration
1. Gå till **Inställningar → Enheter & Tjänster → Lägg till integration**.
2. Sök efter **Energy Dispatcher**.
3. Följ flödet:
   - Ange Forecast.Solar key och koordinater.
   - Ange PV-strängar som JSON-lista (exempel visas).
   - Ange Nord Pool area, valuta och valfritt API-token eller sensor-entity.
   - Konfigurera batteri (Huawei eller generella entiteter).
   - Konfigurera EV (generell EVSE eller manuell).
   - Ange hushållssensorer och standardlaster.
   - Ställ in uppdateringsintervall och om auto-dispatch ska vara aktiv.

> **Tips:** Nord Pool API kräver åtkomst via deras dataportal. Läs mer i [API | Nord Pool](https://www.nordpoolgroup.com/en/trading/api/).

#### Dashboard-exempel
Skapa en ny Lovelace-sida (t.ex. “Energi”) och lägg till kort:

```yaml
type: vertical-stack
title: Energiöversikt
cards:
  - type: entities
    title: Plan
    entities:
      - sensor.energy_dispatcher_plan_summary
      - sensor.energy_dispatcher_price_schedule
      - switch.energy_dispatcher_auto_dispatch
      - button.energy_dispatcher_force_battery_charge
      - button.energy_dispatcher_force_battery_discharge
  - type: history-graph
    entities:
      - sensor.energy_dispatcher_price_schedule
      - sensor.energy_dispatcher_solar_forecast
    hours_to_show: 48
  - type: entities
    title: Batteri & EV
    entities:
      - sensor.energy_dispatcher_battery_status
      - sensor.energy_dispatcher_ev_status
