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

Suggested scenarios
- Price spike day: validate peak classification and pre-peak charging.
- Consecutive peak hours: ensure reserve strategy holds up.
- Solar-rich day: confirm “free energy” accounting and default “never export.”
- Missing data stretches: planner should “hold” safely and surface diagnostics.
