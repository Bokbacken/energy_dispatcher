Energy Dispatcher Inställningar
Uppdatera din Energy Dispatcher-konfiguration. Alla inställningar från den initiala uppsättningen finns tillgängliga här.

Nordpool Spot Price Sensor	nordpool_kwh_se4_sek_3_10_0
Energy Tax (SEK/kWh)	0.439
Grid Transfer Fee (SEK/kWh)	0.2456
Supplier Surcharge (SEK/kWh)	0.1042
VAT Rate (0-1)	0.25
Fixed Monthly Fee (SEK)	656
Include Fixed Fee in Hourly Price	False
Battery Capacity (kWh)	30 kWh
Battery Capacity Sensor (kWh)	Rated ESS capacity EMMA
Battery State of Charge Sensor (%)	State of capacity EMMA
Max Charge Power (W)	10000 W
Max Discharge Power (W)	10000 W
Battery Adapter Type	huawei
Huawei Device ID	5e572c76e307b4cc612e683a04bdb60a
Battery Energy Charged Today (kWh)	Energy charged today EMMA
Battery Energy Discharged Today (kWh)	Energy discharged today EMMA
EV Charging Mode	manual
EV Battery Capacity (kWh)	75 kWh
EV Current State of Charge (%)	40 %
EV Target State of Charge (%)	80 %
EVSE Start Switch/Button Entity	Starta laddning Utomhus ▸ 43201610a-1
EVSE Stop Switch/Button Entity	Stoppa laddning Utomhus ▸ 43201610a-1
EVSE Current Control Entity	Strömgräns Utomhus ▸ 43201610a-1
EVSE Minimum Current (A)	6 A
EVSE Maximum Current (A)	16 A
EVSE Number of Phases	3
EVSE Voltage (V)	230 V
EVSE Charging Power Sensor (W or kW)	Laddningseffekt Utomhus ▸ 43201610a-1
EVSE Session Energy Sensor (kWh or Wh)	Energiförbrukning (nuvarande laddning) Utomhus ▸ 43201610a-1
EVSE Total Energy Counter (kWh)	Total energiförbrukning Utomhus ▸ 43201610a-1
Enable Solar Forecasting	True
Forecast Source	forecast_solar
Latitude	56.6967208731
Longitude	13.0196173488
Solar Panel Array Configuration (JSON)	[{"dec":45,"az":"W","kwp":9.43},{"dec":45,"az":"E","kwp":4.92}]
Horizon Values (comma-separated)	18,16,11,7,5,4,3,2,2,4,7,10
Forecast.Solar API Key (Optional)	q37Xt5h6p6Frq5uN
Weather Entity	met.no Forecast
Clear Sky Factor (0% clouds)	160
Overcast Factor (100% clouds)	30
Manual Forecast Time Step	15
Diffuse Sky View Factor	0.95
Temperature Coefficient (%/°C)	-0.38
Inverter AC Capacity (kW)	10	kW
Enable Manual Calibration	True
PV Current Power Sensor (W or kW	PV output power EMMA
PV Energy Today Sensor (kWh or Wh)	PV yield today EMMA
PV Total Energy Counter (kWh)	Total PV energy yield EMMA
Battery Total Charged Energy Counter (kWh)	Total charged energy EMMA
House Energy Counter (kWh)	Total energy consumption EMMA
Grid Import Today Sensor (kWh)	Supply from grid today EMMA
Historical Lookback Period (hours)	96 hours
Use Time-of-Day Weighting	True
Exclude EV Charging from Baseline	True
Exclude Battery Grid Charging from Baseline	True
Battery SOC Floor (%)	5 %
Battery SOC Ceiling (%)	100 %
Auto-create Dashboard	True


