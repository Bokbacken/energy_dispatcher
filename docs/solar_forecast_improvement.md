# Solar Forecast Improvement in Energy Dispatcher

## Overview
This release introduces major improvements to solar forecasting in Energy Dispatcher, making predictions more accurate and adaptable to local weather conditions.

## Key Features

- **Cloud Compensation:**  
  The solar forecast now incorporates real-time or forecasted cloudiness from your chosen weather entity. This means predictions better match actual sunlight by adjusting solar output based on cloud cover.

- **Configurable Factors:**  
  Users can fine-tune how much output is lost at 0% and 100% cloud cover using two simple config options. This makes the model flexible for different panel types, installation angles, and local climate.

- **Comparison Graphs:**  
  Both raw and compensated forecasts are available as sensors in Home Assistant. You can plot them together to visualize the impact of cloudiness and see instant improvements in prediction accuracy.

## How It Works

- The integration fetches your solar forecast from Forecast.Solar as before.
- It reads current or forecasted “cloudiness” from a selected weather entity.
- The forecast is adjusted using your parameters for 0% and 100% cloud cover.
- Both the raw and compensated forecasts are exposed as sensors for easy comparison.

### Example

If you set:
- `cloud_0_factor`: 250% (output at 0% cloud cover)
- `cloud_100_factor`: 20% (output at full cloud cover)

A forecast hour with 50% cloudiness:
- Adjusted output = 250% - (230% * 0.5) = 135% of raw forecast.

## Benefits

- **More Accurate Planning:**  
  Your automation can use the compensated forecast for smarter battery and EV scheduling.
- **Easy Testing:**  
  Compare both forecasts side-by-side to tune compensation and optimize for your installation.

## How to Use

1. In configuration, select your weather entity and set the cloud compensation factors.
2. Add the new solar forecast sensors to your dashboard for comparison.
3. Enjoy smarter automation and more reliable scheduling!

---

*For support or to report issues, please open a ticket on GitHub.*