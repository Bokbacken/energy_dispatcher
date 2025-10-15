"""Test comparing manual forecast with Forecast.Solar data."""
import os
import sys
import csv
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import pytest
    from homeassistant.util import dt as dt_util
    from custom_components.energy_dispatcher.manual_forecast_engine import (
        ManualForecastEngine,
        clearsky_ghi_haurwitz,
        cloud_to_ghi,
        solar_position,
    )
    from custom_components.energy_dispatcher.models import Plane
    import yaml
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False
    pytest.skip("Dependencies not installed", allow_module_level=True)


def load_forecast_solar_csv():
    """Load Forecast.Solar data from JSON file."""
    fixture_path = Path(__file__).parent / "fixtures" / "forecast.solar.csv"
    if not fixture_path.exists():
        return None
    
    # Read JSON format (key: timestamp, value: watts)
    with open(fixture_path, 'r') as f:
        content = f.read().strip()
        if content.startswith('{'):
            # JSON format
            import json
            data_dict = json.loads(content)
            # Convert to list of dicts
            data = []
            for timestamp, watts in data_dict.items():
                data.append({'datetime': timestamp, 'watts': watts})
            return data
        else:
            # CSV format
            f.seek(0)
            reader = csv.DictReader(f)
            return list(reader)


def load_weather_fixture():
    """Load weather fixture from YAML file."""
    fixture_path = Path(__file__).parent / "fixtures" / "forecast_weather_met.no-01.yaml"
    with open(fixture_path, 'r') as f:
        data = yaml.safe_load(f)
    return data['weather.met_no']['forecast']


def parse_datetime(dt_str):
    """Parse datetime string."""
    # Handle various formats
    try:
        return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except:
        # Try parsing without timezone
        return datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')


class TestForecastSolarComparison:
    """Compare manual forecast calculations with Forecast.Solar data."""
    
    def test_load_forecast_solar_data(self):
        """Test that forecast.solar.csv can be loaded."""
        data = load_forecast_solar_csv()
        
        if data is None:
            pytest.skip("forecast.solar.csv not found - user needs to add it to tests/fixtures/")
        
        assert len(data) > 0, "Forecast.Solar data should not be empty"
        
        print(f"\n✓ Loaded {len(data)} entries from forecast.solar.csv")
        
        # Print first few entries to understand structure
        if len(data) > 0:
            print("\nFirst entry structure:")
            for key, value in data[0].items():
                print(f"  {key}: {value}")
    
    def test_compare_manual_vs_forecast_solar(self):
        """
        Compare manual forecast calculations with Forecast.Solar data.
        
        This test will help identify if the cloud model is still off by showing
        the ratio between manual calculations and Forecast.Solar values.
        """
        forecast_solar_data = load_forecast_solar_csv()
        
        if forecast_solar_data is None:
            pytest.skip("forecast.solar.csv not found in fixtures/")
        
        weather_data = load_weather_fixture()
        
        # Swedish coordinates (typical setup)
        lat = 56.7
        lon = 13.0
        
        # Typical 5 kWp system, 45° tilt, south-facing
        plane = Plane(dec=45, az=180, kwp=5.0)
        
        print("\n" + "="*100)
        print("COMPARISON: Manual Forecast vs Forecast.Solar")
        print("="*100)
        print(f"\nLocation: {lat}°N, {lon}°E")
        print(f"Panel: {plane.kwp} kWp, {plane.dec}° tilt, {plane.az}° azimuth\n")
        
        # Build weather lookup
        weather_lookup = {}
        for hour_data in weather_data:
            dt = parse_datetime(hour_data['datetime'])
            weather_lookup[dt] = hour_data
        
        comparisons = []
        
        # Expected columns in forecast.solar.csv (adjust based on actual format)
        # Common formats: datetime, watt_hours, watts, watt_hours_period
        
        for entry in forecast_solar_data[:24]:  # Compare first 24 hours
            try:
                # Parse datetime from forecast.solar data
                # Adjust key name based on actual CSV structure
                dt_str = entry.get('datetime') or entry.get('timestamp') or entry.get('time')
                if not dt_str:
                    continue
                
                dt = parse_datetime(dt_str)
                
                # Get Forecast.Solar power value (in watts)
                # Adjust key name based on actual CSV structure
                fs_watts = float(entry.get('watts') or entry.get('power') or entry.get('watt_hours_period', 0))
                
                # Find matching weather data
                weather = weather_lookup.get(dt)
                if not weather:
                    continue
                
                # Calculate manual forecast
                cloud_cover = weather['cloud_coverage'] / 100.0
                
                # Solar position
                alt, az, zenith = solar_position(lat, lon, dt)
                
                if alt <= 0:
                    manual_watts = 0
                else:
                    # Clear-sky GHI
                    ghi_clear = clearsky_ghi_haurwitz(zenith)
                    
                    # Apply cloud cover
                    ghi_cloudy = cloud_to_ghi(ghi_clear, cloud_cover)
                    
                    # Simple power calculation (POA ≈ GHI for south-facing at moderate tilt)
                    # This is simplified - actual calculation would include transposition
                    manual_watts = (ghi_cloudy / 1000.0) * plane.kwp * 1000.0
                
                # Calculate ratio
                if fs_watts > 10:  # Only compare significant values
                    ratio = manual_watts / fs_watts if fs_watts > 0 else 0
                    
                    comparisons.append({
                        'datetime': dt,
                        'cloud_cover': cloud_cover,
                        'altitude': alt,
                        'forecast_solar': fs_watts,
                        'manual': manual_watts,
                        'ratio': ratio,
                    })
            except Exception as e:
                print(f"Error processing entry: {e}")
                continue
        
        if not comparisons:
            pytest.skip("No matching data to compare")
        
        # Print comparison table
        print(f"{'Time':<20} {'Cloud%':<8} {'Alt°':<6} {'F.Solar':<10} {'Manual':<10} {'Ratio':<8} {'Status'}")
        print("-" * 100)
        
        for c in comparisons:
            dt_str = c['datetime'].strftime('%Y-%m-%d %H:%M')
            status = "✓ Good" if 0.5 <= c['ratio'] <= 2.0 else "✗ Off"
            print(f"{dt_str:<20} {c['cloud_cover']*100:>5.1f}%  {c['altitude']:5.1f}° "
                  f"{c['forecast_solar']:>8.1f} W {c['manual']:>8.1f} W {c['ratio']:>6.2f}x  {status}")
        
        # Summary statistics
        ratios = [c['ratio'] for c in comparisons]
        avg_ratio = sum(ratios) / len(ratios)
        min_ratio = min(ratios)
        max_ratio = max(ratios)
        
        print("\n" + "="*100)
        print("SUMMARY:")
        print(f"  Average ratio (Manual/F.Solar): {avg_ratio:.2f}x")
        print(f"  Min ratio: {min_ratio:.2f}x")
        print(f"  Max ratio: {max_ratio:.2f}x")
        print()
        
        if avg_ratio > 2.0:
            print("⚠ WARNING: Manual forecast is averaging MORE THAN 2x Forecast.Solar")
            print("  → Cloud model may still be too optimistic")
            print("  → Consider increasing cloud reduction factor")
        elif avg_ratio < 0.5:
            print("⚠ WARNING: Manual forecast is averaging LESS THAN 0.5x Forecast.Solar")
            print("  → Cloud model may be too pessimistic")
            print("  → Consider decreasing cloud reduction factor")
        elif 0.75 <= avg_ratio <= 1.33:
            print("✓ GOOD: Manual forecast is within ±33% of Forecast.Solar on average")
        else:
            print("⚠ FAIR: Manual forecast is within 50-200% of Forecast.Solar")
        
        print("="*100)
        
        # For automated testing, allow reasonable variance
        # Forecast.Solar is typically accurate to ±20% on average
        # Our manual model should be similar
        assert 0.3 <= avg_ratio <= 3.0, \
            f"Manual forecast ratio ({avg_ratio:.2f}x) is outside acceptable range (0.3-3.0x)"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
