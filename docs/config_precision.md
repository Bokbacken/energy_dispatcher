# Configuration Precision and Selectors

High-precision numeric inputs (SEK/kWh)
- Allow up to 6 decimals (e.g., 0.123456).
- Avoid spinner inputs that clamp to 0.001; use number selector in box mode with step 0.000001 or text+Decimal validation.
- Compute with Decimal internally; display with 2 decimals in UI.

Location defaults
- Use Home Assistant Home location by default; allow override via a map selector.

Rounding policy (display)
- Durations: ≥ 2h → 15‑min steps; < 2h → 5‑min steps.
- Power: 10/25/50/100 W step bands by magnitude.
- Prices and energy: 2 decimals; SOC: integer %.
