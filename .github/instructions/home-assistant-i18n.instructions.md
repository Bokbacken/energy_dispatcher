---
applyTo:
  - custom_components/energy_dispatcher/**/*.py
  - custom_components/energy_dispatcher/translations/*.json
---

# Path-specific instructions for the Home Assistant integration

Scope
- These instructions apply to the Energy Dispatcher integration under `custom_components/energy_dispatcher`.

i18n and user-facing text
- Use Home Assistant’s translation system. Do not hardcode user-facing text in `.py` files.
- Add or update keys in `translations/en.json` and `translations/sv.json` for all user-visible strings (config flow prompts, options, entity names, diagnostics, services).
- Prefer placeholders/formatting over concatenation, e.g., `"remaining_time": "Remaining time: {minutes} min"` / `"Återstående tid: {minutes} min"`.

Units and numeric inputs
- Always specify expected units in labels or help text and keep them consistent (e.g., "kW", "kWh", "%", "SEK/kWh").
- Prefer percentages (0–100%) for user inputs; if a decimal is required, explicitly state "decimal 0–1".
- Validate min/max and step; surface clear validation messages in both languages.
- When displaying values (notifications, diagnostics, logs surfaced to users), include the unit.

Config and options flow specifics
- Use appropriate selectors (e.g., number) with `min`, `max`, and `step` tuned for the unit.
- Put the unit in the translation text for the field label or helper text.
- Provide friendly defaults and concise help text oriented to non-technical users.

Entities and dashboard exposure
- For sensors/entities, set appropriate `device_class`, `state_class`, and `unit_of_measurement` so dashboards show units correctly.
- Exposed names and attributes should prioritize clarity for normal users; avoid jargon.
- Keep decimal precision consistent and reasonable for the unit (e.g., kW with 2 decimals, % as integers unless precision is necessary).

Review focus
- For PRs or fixes, check the last 2–5 merged PRs that touched `custom_components/energy_dispatcher/**` or `translations/**` for potential regression sources.
- If the regression likely originated there, cite the PR numbers and specific files/lines, and propose a targeted fix (or revert) with rationale.

Review guidance
- If you encounter hardcoded strings, suggest moving them to translations with proposed keys and `en`/`sv` values.
- If an input or display string lacks units or uses unclear units, propose improved wording with units for both languages.
- Point to exact lines and propose diffs when practical.

Examples

Translations (add keys as needed):
```json
{
  "config": {
    "step": {
      "user": {
        "data": {
          "max_power_kw": "Max power (kW)",
          "battery_capacity_kwh": "Battery capacity (kWh)",
          "utilization_target_percent": "Utilization target (%)",
          "price_threshold_sek_per_kwh": "Price threshold (SEK/kWh)",
          "balance_factor_decimal": "Balance factor (decimal 0–1)"
        },
        "description": "Configure Energy Dispatcher settings."
      }
    },
    "error": {
      "percent_range": "Value must be between 0 and 100%.",
      "decimal_range": "Value must be between 0.0 and 1.0."
    }
  }
}
```

Swedish:
```json
{
  "config": {
    "step": {
      "user": {
        "data": {
          "max_power_kw": "Maxeffekt (kW)",
          "battery_capacity_kwh": "Batterikapacitet (kWh)",
          "utilization_target_percent": "Utnyttjandemål (%)",
          "price_threshold_sek_per_kwh": "Prisgräns (SEK/kWh)",
          "balance_factor_decimal": "Balansfaktor (decimal 0–1)"
        },
        "description": "Konfigurera inställningar för Energy Dispatcher."
      }
    },
    "error": {
      "percent_range": "Värdet måste vara mellan 0 och 100 %.",
      "decimal_range": "Värdet måste vara mellan 0,0 och 1,0."
    }
  }
}
```
