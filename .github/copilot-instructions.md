# Repository custom instructions for GitHub Copilot

Project context:
- This repository contains a Home Assistant HACS integration under `custom_components/energy_dispatcher`.

Language and UX
- All user-facing strings (UI labels, config flow prompts, options, service descriptions, diagnostics messages, logs shown to users) must be clear and descriptive.
- Provide both English (en) and Swedish (sv) variants for all user-facing strings. Flag any hardcoded strings missing translations.
- Keep terminology consistent across the integration.

Internationalization (i18n)
- Do not hardcode user-facing text in Python or YAML. Use Home Assistant's translations (see `custom_components/energy_dispatcher/translations/`).
- Ensure keys exist in both `translations/en.json` and `translations/sv.json`.
- Use parameterized strings instead of concatenation for better translation handling.

Units and numeric inputs
- Always state expected units in labels or help text, and keep units consistent across the UI.
  - Examples: "Max power (kW)", "Battery capacity (kWh)", "Utilization target (%)", "Price threshold (SEK/kWh)", "Balance factor (decimal 0–1)".
- Percentages vs decimals: Prefer percentages (0–100%) for end users. If a decimal is required, explicitly say "decimal 0–1".
- Validate ranges and steps; display clear, actionable errors in both languages (e.g., "Value must be between 0 and 100%").
- Display units alongside values in messages, notifications, and logs that are user-facing.

Naming and API ergonomics
- Publicly exposed names (config entries, services, entity names, options) must be descriptive and self-explanatory in English and Swedish.
- Avoid ambiguous abbreviations; prefer explicit names. Use common abbreviations only when standard (e.g., ID).

Dashboard UX and target audience
- Prioritize ease of use and understanding. The integration targets normal users, not power users.
- Avoid jargon and internal terms; prefer everyday language and brief labels.
- Provide sensible defaults and short, helpful help texts. Keep advanced options optional and well explained.
- Present key metrics with appropriate units, consistent decimal precision, and readable formatting.

Review workflow
- Investigate the previous 2–5 merged PRs, especially those touching the same files/paths as this change.
- If a regression is suspected, cite the related PR numbers and specific files/lines that changed, and propose a concrete fix or revert.
- Prefer diffs or comparisons that show the change timeline (e.g., compare against the last known good commit).
- Cross-reference any linked issues or bug reports; ensure the PR description explains the root cause and prevents recurrence (tests, validation, clearer config, etc.).

Accessibility and clarity
- Messages should be unambiguous and actionable. Provide helpful error/validation text in both languages.

When suggesting changes
- Propose concrete English and Swedish text and point to exact files/lines when possible.
- If a string lacks units or is ambiguous for typical users, recommend clearer wording and include the unit.

Version handling
- Always bump version number in manifest.json to prepare for a new release
