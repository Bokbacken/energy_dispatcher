"""Compare manual forecast with Forecast.Solar data."""
import json
import yaml
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

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


def load_forecast_solar():
    """Load Forecast.Solar data from JSON file."""
    fixture_path = Path(__file__).parent / "tests" / "fixtures" / "forecast.solar.csv"
    with open(fixture_path, 'r') as f:
        content = f.read().strip()
        data_dict = json.loads(content)
        # Convert to list
        data = []
        for timestamp, watts in data_dict.items():
            data.append({'datetime': timestamp, 'watts': watts})
        return data


def load_weather_fixture():
    """Load weather fixture from YAML file."""
    fixture_path = Path(__file__).parent / "tests" / "fixtures" / "forecast_weather_met.no-01.yaml"
    with open(fixture_path, 'r') as f:
        data = yaml.safe_load(f)
    return data['weather.met_no']['forecast']


def parse_datetime(dt_str):
    """Parse datetime string."""
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        # Remove timezone for comparison
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt
    except:
        try:
            return datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
        except:
            return datetime.strptime(dt_str, '%Y-%m-%d %H:%M')


def main():
    """Run comparison."""
    print("="*100)
    print("COMPARISON: Manual Forecast vs Forecast.Solar")
    print("="*100)
    
    # Load data
    try:
        forecast_solar_data = load_forecast_solar()
        print(f"\n✓ Loaded {len(forecast_solar_data)} entries from Forecast.Solar")
    except Exception as e:
        print(f"\n✗ Error loading Forecast.Solar data: {e}")
        return
    
    try:
        weather_data = load_weather_fixture()
        print(f"✓ Loaded {len(weather_data)} hours of weather data")
    except Exception as e:
        print(f"\n✗ Error loading weather data: {e}")
        return
    
    # Swedish coordinates
    lat = 56.7
    lon = 13.0
    
    # 5 kWp system, 45° tilt, south-facing
    plane = Plane(dec=45, az=180, kwp=5.0)
    
    print(f"\nLocation: {lat}°N, {lon}°E")
    print(f"Panel: {plane.kwp} kWp, {plane.dec}° tilt, {plane.az}° azimuth\n")
    
    # Build weather lookup by date+hour
    weather_lookup = {}
    for hour_data in weather_data:
        dt = parse_datetime(hour_data['datetime'])
        # Round to hour
        dt_hour = dt.replace(minute=0, second=0, microsecond=0)
        weather_lookup[dt_hour] = hour_data
    
    print(f"\nWeather data covers: {min(weather_lookup.keys())} to {max(weather_lookup.keys())}")
    print(f"Total weather hours available: {len(weather_lookup)}")
    
    comparisons = []
    
    # Process Forecast.Solar data
    for entry in forecast_solar_data:
        try:
            dt = parse_datetime(entry['datetime'])
            fs_watts = float(entry['watts'])
            
            # Round to hour for weather lookup
            dt_hour = dt.replace(minute=0, second=0, microsecond=0)
            
            # Find matching weather data
            weather = weather_lookup.get(dt_hour)
            if not weather:
                # Try to find nearest hour
                for offset in range(-3, 4):
                    if offset == 0:
                        continue
                    nearby = dt_hour + timedelta(hours=offset)
                    if nearby in weather_lookup:
                        weather = weather_lookup[nearby]
                        break
            
            if not weather:
                # Skip this entry - no matching weather data
                continue
            
            # Calculate manual forecast
            cloud_cover = weather['cloud_coverage'] / 100.0
            temp = weather.get('temperature', 15)
            wind = weather.get('wind_speed', 5)
            
            # Solar position
            alt, az, zenith = solar_position(lat, lon, dt)
            
            if alt <= 0:
                manual_watts = 0
            else:
                # Clear-sky GHI
                ghi_clear = clearsky_ghi_haurwitz(zenith)
                
                # Apply cloud cover
                ghi_cloudy = cloud_to_ghi(ghi_clear, cloud_cover)
                
                # Decompose to DNI/DHI
                dhi, dni = erbs_decomposition(ghi_cloudy, zenith, 1367.0)
                
                # Calculate POA
                poa = poa_hdkr(ghi_cloudy, dhi, dni, zenith, az, plane.dec, plane.az)
                
                # Simple power calculation
                # For 5 kWp at STC (1000 W/m²), power = poa/1000 * 5000
                manual_watts = (poa / 1000.0) * plane.kwp * 1000.0
            
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
                    'ghi_clear': ghi_clear if alt > 0 else 0,
                    'ghi_cloudy': ghi_cloudy if alt > 0 else 0,
                })
        except Exception as e:
            print(f"Error processing entry {entry}: {e}")
            continue
    
    if not comparisons:
        print("No matching data to compare")
        return
    
    # Print comparison table
    print(f"\n{'Time':<22} {'Cloud%':<8} {'Alt°':<6} {'F.Solar':<10} {'Manual':<10} {'Ratio':<8} {'Status'}")
    print("-" * 100)
    
    for c in comparisons[:30]:  # Show first 30
        dt_str = c['datetime'].strftime('%Y-%m-%d %H:%M:%S')
        status = "✓ Good" if 0.5 <= c['ratio'] <= 2.0 else "✗ Off"
        print(f"{dt_str:<22} {c['cloud_cover']*100:>5.1f}%  {c['altitude']:5.1f}° "
              f"{c['forecast_solar']:>8.0f} W {c['manual']:>8.0f} W {c['ratio']:>6.2f}x  {status}")
    
    if len(comparisons) > 30:
        print(f"... ({len(comparisons) - 30} more entries)")
    
    # Summary statistics
    ratios = [c['ratio'] for c in comparisons]
    avg_ratio = sum(ratios) / len(ratios)
    min_ratio = min(ratios)
    max_ratio = max(ratios)
    median_ratio = sorted(ratios)[len(ratios) // 2]
    
    # Count by range
    good_count = sum(1 for r in ratios if 0.67 <= r <= 1.5)
    fair_count = sum(1 for r in ratios if (0.5 <= r < 0.67) or (1.5 < r <= 2.0))
    off_count = sum(1 for r in ratios if r < 0.5 or r > 2.0)
    
    print("\n" + "="*100)
    print("SUMMARY:")
    print(f"  Total comparisons: {len(comparisons)}")
    print(f"  Average ratio (Manual/F.Solar): {avg_ratio:.2f}x")
    print(f"  Median ratio: {median_ratio:.2f}x")
    print(f"  Min ratio: {min_ratio:.2f}x")
    print(f"  Max ratio: {max_ratio:.2f}x")
    print()
    print(f"  Within ±33%: {good_count} ({good_count/len(comparisons)*100:.1f}%)")
    print(f"  Within ±50%: {good_count + fair_count} ({(good_count + fair_count)/len(comparisons)*100:.1f}%)")
    print(f"  Outside ±100%: {off_count} ({off_count/len(comparisons)*100:.1f}%)")
    print()
    
    if avg_ratio > 2.0:
        print("⚠ WARNING: Manual forecast is averaging MORE THAN 2x Forecast.Solar")
        print("  → Cloud model may still be too optimistic")
    elif avg_ratio < 0.5:
        print("⚠ WARNING: Manual forecast is averaging LESS THAN 0.5x Forecast.Solar")
        print("  → Cloud model may be too pessimistic")
    elif 0.75 <= avg_ratio <= 1.33:
        print("✓ GOOD: Manual forecast is within ±33% of Forecast.Solar on average")
    else:
        print("⚠ FAIR: Manual forecast is within 50-200% of Forecast.Solar")
    
    print("="*100)
    
    # Show some detailed examples
    print("\nDETAILED EXAMPLES (showing cloud model behavior):\n")
    
    # Group by cloud cover ranges
    cloudy = [c for c in comparisons if c['cloud_cover'] > 0.7]
    partly_cloudy = [c for c in comparisons if 0.3 < c['cloud_cover'] <= 0.7]
    clear = [c for c in comparisons if c['cloud_cover'] <= 0.3]
    
    for label, group in [("Clear (<30% cloud)", clear), ("Partly cloudy (30-70%)", partly_cloudy), ("Cloudy (>70%)", cloudy)]:
        if group:
            avg_r = sum(c['ratio'] for c in group) / len(group)
            print(f"{label}: {len(group)} samples, avg ratio = {avg_r:.2f}x")
            # Show one example
            example = group[len(group)//2]
            print(f"  Example: {example['datetime'].strftime('%Y-%m-%d %H:%M')}")
            print(f"    Cloud: {example['cloud_cover']*100:.0f}%, Alt: {example['altitude']:.1f}°")
            print(f"    GHI clear: {example['ghi_clear']:.0f} W/m², cloudy: {example['ghi_cloudy']:.0f} W/m²")
            print(f"    Forecast.Solar: {example['forecast_solar']:.0f} W, Manual: {example['manual']:.0f} W")
            print(f"    Ratio: {example['ratio']:.2f}x")
            print()


if __name__ == "__main__":
    main()
