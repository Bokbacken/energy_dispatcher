# Price Configuration Example (SEK/kWh)

This captures your current price composition and how the integration computes the hourly total price with high precision (up to 6 decimals internally), while displaying 2 decimals.

Inputs (from your setup)
- Nordpool Spot Price Sensor: `nordpool_kwh_se4_sek_3_10_0`
- Energy Tax (SEK/kWh): `0.439`
- Grid Transfer Fee (SEK/kWh): `0.2456`
- Supplier Surcharge (SEK/kWh, variable): `0.1042`
- Supplier Surcharge (SEK/month, fixed): `0` (set if you split the surcharge into a fixed part)
- VAT Rate (0–1): `0.25`
- Fixed Monthly Fee (SEK): `656`
- Include Fixed Fee in Hourly Price: `false` (if true, see amortization below)

Computation (per hour)
- subtotal_kwh = spot_kwh + energy_tax_kwh + grid_transfer_fee_kwh + supplier_variable_surcharge_kwh
- vat_component = subtotal_kwh × VAT_rate
- fixed_fee_amortized_kwh:
  - If Include Fixed Fee in Hourly Price = true:
    - fixed_fee_amortized_kwh = (fixed_monthly_fee + supplier_fixed_monthly_surcharge) / amortization_kwh_per_month
    - amortization_kwh_per_month default = 300.0 (user-configurable)
  - Else: fixed_fee_amortized_kwh = 0
- total_price_kwh = subtotal_kwh + vat_component + fixed_fee_amortized_kwh

Display policy
- Show prices as 2 decimals (SEK/kWh) in UI.
- Use Decimal internally with up to 6 decimals for accuracy.

Notes
- If export remuneration differs from spot, we can support an optional `electricity_export_price_effective` input; otherwise default to spot for conservative estimates.
- If VAT applies to fixed monthly fees and you amortize them into hourly price, include VAT in that amortized component (toggleable to avoid double-counting).
