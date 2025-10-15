"""Test comparing manual forecast calculations with fixture weather data."""
import os
import sys
import yaml
import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from homeassistant.util import dt as dt_util
    from custom_components.energy_dispatcher.manual_forecast_engine import (
        ManualForecastEngine,
        clearsky_ghi_haurwitz,
        cloud_to_ghi,
        erbs_decomposition,
        poa_hdkr,
        solar_position,
    )
    from custom_components.energy_dispatcher.models import Plane
    HAS_HA = True
except ImportError:
    HAS_HA = False
    pytest.skip("Home Assistant not installed, skipping integration tests", allow_module_level=True)


def load_weather_fixture():
    """Load weather fixture from YAML file."""
    fixture_path = Path(__file__).parent / "fixtures" / "forecast_weather_met.no-01.yaml"
    with open(fixture_path, 'r') as f:
        data = yaml.safe_load(f)
    return data['weather.met_no']['forecast']


def parse_datetime(dt_str):
    """Parse datetime string from fixture."""
    # Parse ISO format datetime string
    return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))


class TestManualForecastVsFixture:
    """Test manual forecast calculations against fixture weather data."""
    
    def test_load_fixture(self):
        """Test that fixture loads correctly."""
        forecast = load_weather_fixture()
        assert len(forecast) > 0
        
        # Check first entry
        first = forecast[0]
        assert 'datetime' in first
        assert 'cloud_coverage' in first
        assert 'temperature' in first
        assert 'wind_speed' in first
        
        print(f"\nFixture loaded: {len(forecast)} hours")
        print(f"First hour: {first['datetime']}")
        print(f"Cloud coverage: {first['cloud_coverage']}%")
        print(f"Temperature: {first['temperature']}°C")
        print(f"Wind speed: {first['wind_speed']} m/s")
    
    def test_manual_forecast_calculation_with_fixture_data(self):
        """Test manual forecast calculations using fixture weather data."""
        forecast = load_weather_fixture()
        
        # Use Swedish coordinates (similar to test setup)
        lat = 56.7
        lon = 13.0
        
        # Test plane configuration (5 kWp, 45° tilt, south-facing)
        planes = [Plane(dec=45, az=180, kwp=5.0)]
        
        results = []
        
        for i, hour_data in enumerate(forecast[:24]):  # Test first 24 hours
            dt = parse_datetime(hour_data['datetime'])
            cloud_cover = hour_data['cloud_coverage'] / 100.0  # Convert to 0-1
            temperature = hour_data['temperature']
            wind_speed = hour_data['wind_speed']
            
            # Calculate solar position
            alt, az, zenith = solar_position(lat, lon, dt)
            
            # Skip nighttime hours (sun below horizon)
            if alt <= 0:
                results.append({
                    'datetime': dt,
                    'altitude': alt,
                    'cloud_cover': cloud_cover,
                    'ghi_clear': 0,
                    'ghi_cloudy': 0,
                    'power_w': 0,
                    'note': 'Night (sun below horizon)'
                })
                continue
            
            # Calculate clear-sky GHI using Haurwitz model
            ghi_clear = clearsky_ghi_haurwitz(zenith)
            
            # Apply cloud cover to get actual GHI
            ghi_cloudy = cloud_to_ghi(ghi_clear, cloud_cover)
            
            # Decompose GHI to DNI/DHI using Erbs model
            dhi, dni = erbs_decomposition(ghi_cloudy, zenith, 1367.0)
            
            # Calculate POA irradiance for the plane
            poa = poa_hdkr(ghi_cloudy, dhi, dni, zenith, az, planes[0].dec, planes[0].az)
            
            # Simple DC power calculation (without temperature effects for now)
            # Assume standard PV efficiency of ~15% for simplicity
            area_m2 = planes[0].kwp / 0.15  # Approximate panel area
            power_dc = poa * area_m2 * 0.15  # DC power in W
            
            # Simple AC conversion (96% efficiency)
            power_ac = power_dc * 0.96
            
            results.append({
                'datetime': dt,
                'altitude': alt,
                'azimuth': az,
                'zenith': zenith,
                'cloud_cover': cloud_cover,
                'temperature': temperature,
                'wind_speed': wind_speed,
                'ghi_clear': ghi_clear,
                'ghi_cloudy': ghi_cloudy,
                'dni': dni,
                'dhi': dhi,
                'poa': poa,
                'power_w': power_ac,
                'note': 'Day'
            })
        
        # Print detailed results for analysis
        print("\n" + "="*100)
        print("MANUAL FORECAST CALCULATION RESULTS VS FIXTURE DATA")
        print("="*100)
        print(f"\nLocation: Lat {lat}°, Lon {lon}°")
        print(f"Panel: {planes[0].kwp} kWp, {planes[0].dec}° tilt, {planes[0].az}° azimuth (south)")
        print("\n")
        
        # Find daytime hours
        daytime_results = [r for r in results if r['altitude'] > 0]
        
        if daytime_results:
            print(f"Found {len(daytime_results)} daytime hours in fixture data\n")
            print(f"{'Time':<20} {'Alt°':<6} {'Cloud%':<7} {'GHI_clear':<10} {'GHI_cloudy':<11} {'POA':<10} {'Power':<10}")
            print("-" * 100)
            
            for r in daytime_results:
                dt_str = r['datetime'].strftime('%Y-%m-%d %H:%M')
                print(f"{dt_str:<20} {r['altitude']:5.1f}° {r['cloud_cover']*100:5.1f}% "
                      f"{r['ghi_clear']:8.1f} W {r['ghi_cloudy']:9.1f} W "
                      f"{r['poa']:8.1f} W {r['power_w']:8.1f} W")
            
            # Summary statistics
            total_energy_kwh = sum(r['power_w'] for r in daytime_results) / 1000.0
            avg_power_w = sum(r['power_w'] for r in daytime_results) / len(daytime_results)
            max_power_w = max(r['power_w'] for r in daytime_results)
            
            print("\n" + "="*100)
            print(f"SUMMARY:")
            print(f"  Total daytime hours: {len(daytime_results)}")
            print(f"  Average power: {avg_power_w:.1f} W")
            print(f"  Peak power: {max_power_w:.1f} W")
            print(f"  Total energy (if each hour): {total_energy_kwh:.2f} kWh")
            print("="*100)
        else:
            print("No daytime hours found in fixture data (all hours at night)")
        
        # Basic assertion: we should be able to calculate values
        assert len(results) > 0
    
    def test_compare_manual_vs_forecast_solar_api(self):
        """
        Compare manual calculations to what Forecast.Solar API would return.
        
        This test documents the expected differences between:
        1. Manual physics-based forecast using weather data
        2. Forecast.Solar API (if we had it)
        
        The purpose is to identify why manual calculations might be "way off".
        """
        forecast = load_weather_fixture()
        
        # Get first daytime hour from fixture
        for hour_data in forecast:
            dt = parse_datetime(hour_data['datetime'])
            lat = 56.7
            lon = 13.0
            
            alt, az, zenith = solar_position(lat, lon, dt)
            
            if alt > 0:  # Found a daytime hour
                cloud_cover = hour_data['cloud_coverage'] / 100.0
                
                print(f"\n" + "="*80)
                print(f"COMPARISON: Manual vs Forecast.Solar API")
                print("="*80)
                print(f"Time: {dt}")
                print(f"Location: {lat}°N, {lon}°E")
                print(f"Sun altitude: {alt:.1f}°")
                print(f"Cloud coverage: {cloud_cover*100:.1f}%")
                print()
                
                # Calculate clear-sky GHI
                ghi_clear = clearsky_ghi_haurwitz(zenith)
                print(f"Clear-sky GHI (Haurwitz): {ghi_clear:.1f} W/m²")
                
                # Apply cloud cover
                ghi_cloudy = cloud_to_ghi(ghi_clear, cloud_cover)
                print(f"Cloudy GHI (Kasten-Czeplak): {ghi_cloudy:.1f} W/m²")
                print(f"Cloud reduction: {(1 - ghi_cloudy/ghi_clear)*100:.1f}%")
                print()
                
                print("POTENTIAL ISSUES:")
                print("1. Haurwitz model is simple - may overestimate clear-sky GHI")
                print("2. Kasten-Czeplak cloud model uses C^3.4 - very aggressive reduction")
                print("3. No atmospheric correction (elevation, aerosols, water vapor)")
                print("4. No temporal smoothing of cloud cover transitions")
                print("5. Forecast.Solar uses actual satellite data, not weather forecast")
                print()
                
                # Show what different cloud models would give
                print("CLOUD MODEL COMPARISON for same clear-sky GHI:")
                simple_linear = ghi_clear * (1 - cloud_cover)
                moderate = ghi_clear * (1 - cloud_cover**2)
                kasten = ghi_cloudy  # This is C^3.4
                
                print(f"  Linear (1-C):     {simple_linear:.1f} W/m² ({simple_linear/ghi_clear*100:.1f}% of clear)")
                print(f"  Moderate (1-C²):  {moderate:.1f} W/m² ({moderate/ghi_clear*100:.1f}% of clear)")
                print(f"  Kasten (C^3.4):   {kasten:.1f} W/m² ({kasten/ghi_clear*100:.1f}% of clear)")
                print()
                print(f"For {cloud_cover*100:.1f}% cloud cover, Kasten gives {kasten/simple_linear*100:.1f}% of linear model")
                
                break
        
        assert True  # This is a diagnostic test


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
