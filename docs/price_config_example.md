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

Export/Feed-in Price (SEK/kWh)

Based on E.ON Sweden contract (SE4 region):

**Components**:
1. Grid utility compensation (nätnytta): `0.067` SEK/kWh
2. Energy purchase from supplier: `spot_price + 0.02` SEK/kWh
3. Tax return (temporary, expires Dec 31, 2025): `0.60` SEK/kWh

**Total feed-in compensation**:
- **2025**: `spot_price + 0.687` SEK/kWh
- **2026 and beyond**: `spot_price + 0.087` SEK/kWh

**Formula**:
```
feed_in_price_2025 = spot_kwh + 0.067 + 0.02 + 0.60
feed_in_price_2026 = spot_kwh + 0.067 + 0.02
```

**Example** (spot price = 0.50 SEK/kWh):
- 2025: Feed-in = 0.50 + 0.687 = 1.187 SEK/kWh
- 2026: Feed-in = 0.50 + 0.087 = 0.587 SEK/kWh

**Important notes**:
- No VAT applied to exported energy (0%)
- Grid utility and energy purchase are separate line items on the bill
- Tax return is a government incentive that significantly impacts export economics
- Export becomes much less attractive after 2025 due to tax return expiration

Notes
- If export remuneration differs from spot, we can support an optional `electricity_export_price_effective` input; otherwise default to spot for conservative estimates.
- If VAT applies to fixed monthly fees and you amortize them into hourly price, include VAT in that amortized component (toggleable to avoid double-counting).
- For export optimization testing, use the documented feed-in formula above based on the period being tested (2025 vs 2026+).
