# Sample Data Notes

Use this alongside the generated report (docs/generated/sample_data_report.md).

Perfect windows (no large gaps, no resets)
- Window 1: START — END (DURATION). Files: …
- Window 2: START — END (DURATION). Files: …
- Window 3: START — END (DURATION). Files: …

Gappy windows (robustness tests)
- Gap 1: FILE, START — END (GAP DURATION), context …
- Gap 2: FILE, START — END (GAP DURATION), context …
- Gap 3: FILE, START — END (GAP DURATION), context …

File-specific expectations
- historic_total_energy_supply_from_grid.csv: cumulative import kWh (report shows any resets).
- historic_total_feed_in_to_grid.csv: cumulative export kWh (multi-day export validation).
- historic_total_house_energy_consumption.csv: cumulative load; cross-check attribution (import + PV + battery = load + export).
- historic_total_energy_from_pv.csv: cumulative PV; validate “free energy” fraction and sunny-day behavior.
- historic_total_charged_energy_to_batteries.csv / historic_total_discharge_from_batteries.csv: battery flow accounting.
- historic_batteries_power_in_out.csv: power series; cross-check or fallback when meters are absent.
- historic_batteries_SOC.csv: SoC for reserve/limits.
- historic_energy_spot_price.csv / historic_energy_full_price.csv: alignment and precision vs Nordpool YAML and adders.
- historic_feed_in_to_grid_today.csv / historic_today_energy_supply_from_grid.csv: daily resets (UI parity; long-horizon accounting prefers cumulative meters).
- historic_EV_charging_power.csv: EV charging power (kW); validates EV dispatcher and charging optimization.
- historic_EV_session_charged_energy.csv: per-session energy (kWh); tracks individual charging sessions with resets.
- historic_EV_total_charged_energy.csv: cumulative EV energy (kWh); long-term EV charging accounting.
- nordpool_spot_price_today_tomorrow-01.yaml / nordpool_spot_price_today_tomorrow-02.yaml: Nordpool spot prices; -02 includes price spike (5.72 SEK/kWh).
- forecast_weather_met.no-01.yaml: weather forecast (Met.no format); cloud coverage and temperature for solar forecast validation.

Feed-in tariff (E.ON Sweden, SE4 region)
- Grid utility: 0.067 SEK/kWh (nätnytta)
- Energy purchase: Spot + 0.02 SEK/kWh
- Tax return (2025 only): 0.60 SEK/kWh
- Total feed-in 2025: Spot + 0.687 SEK/kWh
- Total feed-in 2026+: Spot + 0.087 SEK/kWh

Suggested scenarios
- Price spike day: validate peak classification and pre-peak charging (use nordpool-02 with 5.72 SEK/kWh spike).
- Consecutive peak hours: ensure reserve strategy holds up.
- Solar-rich day: confirm “free energy” accounting and default “never export.”
- Missing data stretches: planner should “hold” safely and surface diagnostics.
- EV charging optimization: test cost-based charging with realistic power/energy data.
- Export optimization: validate feed-in compensation calculations (spot + 0.687 for 2025, spot + 0.087 for 2026+).
- Weather-based solar forecasting: test forecast processing with Met.no data.
