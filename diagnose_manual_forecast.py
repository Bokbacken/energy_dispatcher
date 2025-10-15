"""Diagnose manual forecast calculations vs fixture data."""
import os
import sys
import yaml
from datetime import datetime
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from custom_components.energy_dispatcher.manual_forecast_engine import (
        clearsky_ghi_haurwitz,
        cloud_to_ghi,
        erbs_decomposition,
        poa_hdkr,
        solar_position,
    )
    from custom_components.energy_dispatcher.models import Plane
except ImportError as e:
    print(f"Error importing: {e}")
    sys.exit(1)


def load_weather_fixture():
    """Load weather fixture from YAML file."""
    fixture_path = Path(__file__).parent / "tests" / "fixtures" / "forecast_weather_met.no-01.yaml"
    with open(fixture_path, 'r') as f:
        data = yaml.safe_load(f)
    return data['weather.met_no']['forecast']


def parse_datetime(dt_str):
    """Parse datetime string from fixture."""
    return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))


def main():
    """Run diagnostic analysis."""
    print("="*100)
    print("MANUAL FORECAST DIAGNOSTIC - Comparing to Fixture Weather Data")
    print("="*100)
    
    # Load fixture
    try:
        forecast = load_weather_fixture()
        print(f"\n✓ Loaded {len(forecast)} hours of weather data from fixture")
    except Exception as e:
        print(f"\n✗ Error loading fixture: {e}")
        return
    
    # Use Swedish coordinates
    lat = 56.7
    lon = 13.0
    
    # Test plane configuration (5 kWp, 45° tilt, south-facing)
    plane = Plane(dec=45, az=180, kwp=5.0)
    
    print(f"\nLocation: {lat}°N, {lon}°E")
    print(f"Panel: {plane.kwp} kWp, {plane.dec}° tilt, {plane.az}° azimuth (south)")
    
    # Analyze first 24 hours
    daytime_hours = []
    nighttime_hours = []
    
    for i, hour_data in enumerate(forecast[:24]):
        dt = parse_datetime(hour_data['datetime'])
        cloud_cover = hour_data['cloud_coverage'] / 100.0
        temperature = hour_data['temperature']
        wind_speed = hour_data['wind_speed']
        
        # Calculate solar position
        alt, az, zenith = solar_position(lat, lon, dt)
        
        if alt <= 0:
            nighttime_hours.append(dt)
            continue
        
        # Calculate clear-sky GHI using Haurwitz model
        ghi_clear = clearsky_ghi_haurwitz(zenith)
        
        # Apply cloud cover to get actual GHI
        ghi_cloudy = cloud_to_ghi(ghi_clear, cloud_cover)
        
        # Decompose GHI to DNI/DHI
        dhi, dni = erbs_decomposition(ghi_cloudy, zenith, 1367.0)
        
        # Calculate POA irradiance
        poa = poa_hdkr(ghi_cloudy, dhi, dni, zenith, az, plane.dec, plane.az)
        
        # Simple power calculation
        # For a 5 kWp system at STC (1000 W/m², 25°C):
        # - Peak power is 5000 W
        # - This corresponds to ~1000 W/m² irradiance
        # So: power = poa / 1000 * 5000
        power_w = (poa / 1000.0) * plane.kwp * 1000.0
        
        daytime_hours.append({
            'datetime': dt,
            'altitude': alt,
            'azimuth': az,
            'zenith': zenith,
            'cloud_cover': cloud_cover,
            'ghi_clear': ghi_clear,
            'ghi_cloudy': ghi_cloudy,
            'dni': dni,
            'dhi': dhi,
            'poa': poa,
            'power_w': power_w,
        })
    
    print(f"\n{'='*100}")
    print(f"RESULTS: Found {len(daytime_hours)} daytime hours, {len(nighttime_hours)} nighttime hours")
    print(f"{'='*100}\n")
    
    if daytime_hours:
        print(f"{'Time':<20} {'Alt°':<6} {'Cloud%':<7} {'GHI_clear':<10} {'GHI_cloudy':<11} {'POA':<10} {'Power':<10}")
        print("-" * 100)
        
        for r in daytime_hours:
            dt_str = r['datetime'].strftime('%Y-%m-%d %H:%M')
            print(f"{dt_str:<20} {r['altitude']:5.1f}° {r['cloud_cover']*100:5.1f}% "
                  f"{r['ghi_clear']:8.1f} W {r['ghi_cloudy']:9.1f} W "
                  f"{r['poa']:8.1f} W {r['power_w']:8.1f} W")
        
        # Summary
        total_energy_kwh = sum(r['power_w'] for r in daytime_hours) / 1000.0
        avg_power_w = sum(r['power_w'] for r in daytime_hours) / len(daytime_hours)
        max_power_w = max(r['power_w'] for r in daytime_hours)
        
        print(f"\n{'='*100}")
        print(f"SUMMARY:")
        print(f"  Daytime hours: {len(daytime_hours)}")
        print(f"  Average power: {avg_power_w:.1f} W")
        print(f"  Peak power: {max_power_w:.1f} W")
        print(f"  Total energy (hourly sum): {total_energy_kwh:.2f} kWh")
        print(f"{'='*100}\n")
        
        # Analyze cloud model behavior
        print(f"{'='*100}")
        print("CLOUD MODEL ANALYSIS")
        print(f"{'='*100}\n")
        
        if daytime_hours:
            first_daytime = daytime_hours[0]
            cloud = first_daytime['cloud_cover']
            ghi_clear = first_daytime['ghi_clear']
            
            print(f"Example: {first_daytime['datetime'].strftime('%Y-%m-%d %H:%M')}")
            print(f"  Cloud cover: {cloud*100:.1f}%")
            print(f"  Clear-sky GHI: {ghi_clear:.1f} W/m²")
            print()
            
            # Compare different cloud models
            linear = ghi_clear * (1 - cloud)
            quadratic = ghi_clear * (1 - cloud**2)
            kasten = cloud_to_ghi(ghi_clear, cloud)
            
            print(f"  Linear model (1-C):      {linear:7.1f} W/m² ({linear/ghi_clear*100:5.1f}% of clear)")
            print(f"  Quadratic (1-C²):        {quadratic:7.1f} W/m² ({quadratic/ghi_clear*100:5.1f}% of clear)")
            print(f"  Kasten-Czeplak (C^3.4):  {kasten:7.1f} W/m² ({kasten/ghi_clear*100:5.1f}% of clear)")
            print()
            
            print("PROBLEM IDENTIFIED:")
            print(f"  For {cloud*100:.1f}% cloud cover:")
            print(f"    - Kasten gives only {kasten/linear*100:.1f}% of what linear model would give")
            print(f"    - This is VERY aggressive cloud reduction")
            print()
            print("  The Kasten-Czeplak model (C^3.4) is appropriate for:")
            print("    - Instantaneous irradiance measurements")
            print("    - Clear/partly cloudy conditions")
            print()
            print("  But it may be TOO aggressive for:")
            print("    - Forecasts (which tend to overestimate cloud cover)")
            print("    - Heavy cloud cover (>80%)")
            print()
            print("RECOMMENDATION:")
            print("  Consider using a more moderate cloud model, such as:")
            print("    - Quadratic (C²) for forecasts")
            print("    - Or: 0.25 + 0.75*(1-C)^2  (gives 25% transmission even at 100% cloud)")
            print(f"{'='*100}")
    else:
        print("No daytime hours found in fixture (October data - short days at 56.7°N)")
        print("\nThis is EXPECTED for October 13-14 at this latitude:")
        print("  - Sunrise around 7:30 AM")
        print("  - Sunset around 6:00 PM")
        print("  - Fixture starts at 19:00 (7 PM) - after sunset")
        print("\nTo properly test, we need fixture data covering daytime hours!")


if __name__ == "__main__":
    main()
