"""Integration tests for price provider using real sample data.

These tests validate the price enrichment calculations and Nordpool
parsing against real historical data from tests/fixtures/.
"""
import pytest
import yaml
from datetime import datetime
from pathlib import Path
from typing import List, Tuple
from unittest.mock import MagicMock

from custom_components.energy_dispatcher.price_provider import (
    PriceProvider,
    PriceFees,
    _enriched_spot,
)
from custom_components.energy_dispatcher.models import PricePoint


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_price_csv(filename: str) -> List[Tuple[datetime, float]]:
    """Load price data from CSV file."""
    import csv
    from tests.data_quality_report import parse_timestamp
    
    prices = []
    csv_path = FIXTURES_DIR / filename
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            ts = parse_timestamp(row['timestamp'])
            val = float(row['value'])
            if ts:
                prices.append((ts, val))
    
    return sorted(prices, key=lambda x: x[0])


def load_nordpool_yaml() -> dict:
    """Load Nordpool YAML sample data."""
    yaml_path = FIXTURES_DIR / "nordpool_spot_price_today_tomorrow.yaml"
    
    with open(yaml_path, 'r') as f:
        data = yaml.safe_load(f)
    
    return data


@pytest.fixture
def standard_swedish_fees():
    """Standard Swedish electricity fees for testing."""
    return PriceFees(
        tax=0.385,        # Energy tax (SEK/kWh)
        transfer=0.39,    # Grid transfer fee (SEK/kWh)
        surcharge=0.055,  # Surcharge (SEK/kWh)
        vat=0.25,         # 25% VAT
        fixed_monthly=400.0,  # Fixed monthly cost (SEK)
        include_fixed=True,
    )


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    hass.states = MagicMock()
    return hass


class TestEnrichedSpotCalculation:
    """Test the enriched spot price calculation formula."""
    
    def test_enriched_spot_basic(self, standard_swedish_fees):
        """Test basic enriched spot calculation with standard fees."""
        spot_price = 1.0  # SEK/kWh
        
        enriched = _enriched_spot(spot_price, standard_swedish_fees)
        
        # Formula: (spot + tax + transfer + surcharge) * (1 + VAT) + fixed
        # (1.0 + 0.385 + 0.39 + 0.055) * 1.25 + (400/720)
        # = 1.83 * 1.25 + 0.556
        # = 2.2875 + 0.556
        # = 2.844 SEK/kWh (rounded to 6 decimals)
        
        expected = (1.0 + 0.385 + 0.39 + 0.055) * 1.25 + (400.0 / 720.0)
        assert enriched == pytest.approx(expected, abs=0.001)
        assert enriched == pytest.approx(2.844, abs=0.01)
    
    def test_enriched_spot_without_fixed(self):
        """Test enriched calculation without fixed monthly cost."""
        fees = PriceFees(
            tax=0.385,
            transfer=0.39,
            surcharge=0.055,
            vat=0.25,
            fixed_monthly=400.0,
            include_fixed=False,  # Exclude fixed cost
        )
        
        spot_price = 1.0
        enriched = _enriched_spot(spot_price, fees)
        
        # Should not include fixed cost
        expected = (1.0 + 0.385 + 0.39 + 0.055) * 1.25
        assert enriched == pytest.approx(expected, abs=0.001)
        assert enriched == pytest.approx(2.2875, abs=0.001)
    
    def test_enriched_spot_high_price(self, standard_swedish_fees):
        """Test with high spot price (price spike scenario)."""
        spot_price = 5.0  # High price
        
        enriched = _enriched_spot(spot_price, standard_swedish_fees)
        
        # Fixed costs become less significant at high prices
        expected = (5.0 + 0.385 + 0.39 + 0.055) * 1.25 + (400.0 / 720.0)
        assert enriched == pytest.approx(expected, abs=0.001)
        assert enriched > 7.0  # Should be over 7 SEK/kWh
    
    def test_enriched_spot_negative_price(self, standard_swedish_fees):
        """Test with negative spot price (rare but can happen)."""
        spot_price = -0.5  # Negative price
        
        enriched = _enriched_spot(spot_price, standard_swedish_fees)
        
        # Even with negative spot, fees and VAT still apply
        expected = (-0.5 + 0.385 + 0.39 + 0.055) * 1.25 + (400.0 / 720.0)
        assert enriched == pytest.approx(expected, abs=0.001)
        # Should still be positive due to fees and fixed cost
        assert enriched > 0
    
    def test_enriched_spot_rounding(self, standard_swedish_fees):
        """Test that enriched price is rounded to 6 decimals."""
        spot_price = 1.123456789
        
        enriched = _enriched_spot(spot_price, standard_swedish_fees)
        
        # Check that result has at most 6 decimal places
        str_enriched = f"{enriched:.10f}"
        decimal_part = str_enriched.split('.')[1]
        # Should have at most 6 significant decimals
        assert enriched == round(enriched, 6)


class TestPriceProviderRealData:
    """Test PriceProvider with real sample data."""
    
    def test_spot_price_ranges(self):
        """Test that spot prices are in reasonable ranges."""
        spot_prices = load_price_csv("historic_energy_spot_price.csv")
        
        assert len(spot_prices) > 0, "No spot price data loaded"
        
        values = [price for _, price in spot_prices]
        min_price = min(values)
        max_price = max(values)
        avg_price = sum(values) / len(values)
        
        # Swedish spot prices typically range from -1 to 10 SEK/kWh
        # (can go negative occasionally)
        assert min_price >= -1.0, f"Spot price too low: {min_price}"
        assert max_price <= 10.0, f"Spot price too high: {max_price}"
        assert 0.0 <= avg_price <= 3.0, f"Average spot price unusual: {avg_price}"
        
        print(f"\nSpot price stats: min={min_price:.3f}, max={max_price:.3f}, avg={avg_price:.3f}")
    
    def test_full_price_enrichment_validation(self, standard_swedish_fees):
        """Validate that calculated enriched prices match historical full prices."""
        spot_prices = load_price_csv("historic_energy_spot_price.csv")
        full_prices = load_price_csv("historic_energy_full_price.csv")
        
        # Create lookup dict for full prices
        full_price_dict = {ts: price for ts, price in full_prices}
        
        # Check enriched calculation for matching timestamps
        matches = 0
        close_matches = 0
        differences = []
        
        for ts, spot in spot_prices:
            if ts in full_price_dict:
                calculated_enriched = _enriched_spot(spot, standard_swedish_fees)
                actual_full = full_price_dict[ts]
                
                diff = abs(calculated_enriched - actual_full)
                differences.append(diff)
                matches += 1
                
                # Allow 10% tolerance due to possible fee differences
                if diff / actual_full <= 0.10:
                    close_matches += 1
        
        assert matches > 0, "No matching timestamps found"
        
        avg_diff = sum(differences) / len(differences)
        max_diff = max(differences)
        
        # Print statistics for validation
        print(f"\nPrice enrichment validation:")
        print(f"  Matches: {matches}")
        print(f"  Close matches (±10%): {close_matches} ({100*close_matches/matches:.1f}%)")
        print(f"  Avg difference: {avg_diff:.3f} SEK/kWh")
        print(f"  Max difference: {max_diff:.3f} SEK/kWh")
        
        # At least 70% should match within 10% tolerance
        # (fees may vary by contract)
        assert close_matches / matches >= 0.70, \
            f"Only {100*close_matches/matches:.1f}% of prices match within tolerance"
    
    def test_price_continuity(self):
        """Test that price data has reasonable continuity (hourly intervals)."""
        spot_prices = load_price_csv("historic_energy_spot_price.csv")
        
        # Check intervals between consecutive prices
        intervals = []
        for i in range(len(spot_prices) - 1):
            ts1, _ = spot_prices[i]
            ts2, _ = spot_prices[i + 1]
            interval_seconds = (ts2 - ts1).total_seconds()
            intervals.append(interval_seconds)
        
        # Most intervals should be 3600 seconds (1 hour)
        hour_intervals = sum(1 for i in intervals if 3500 <= i <= 3700)
        
        assert hour_intervals / len(intervals) >= 0.90, \
            "Less than 90% of intervals are approximately hourly"


class TestNordpoolParsing:
    """Test Nordpool YAML parsing."""
    
    def test_nordpool_yaml_structure(self):
        """Test that Nordpool YAML has expected structure."""
        data = load_nordpool_yaml()
        
        # Should have raw_today
        assert 'raw_today' in data, "Missing raw_today in Nordpool data"
        assert isinstance(data['raw_today'], list), "raw_today should be a list"
        assert len(data['raw_today']) > 0, "raw_today should not be empty"
        
        # raw_tomorrow may be empty (before ~14:00 each day)
        if 'raw_tomorrow' in data:
            assert isinstance(data['raw_tomorrow'], list), "raw_tomorrow should be a list"
        
        # Check structure of first price point
        first_price = data['raw_today'][0]
        assert 'start' in first_price, "Missing 'start' in price point"
        assert 'value' in first_price, "Missing 'value' in price point"
    
    def test_nordpool_price_parsing(self, mock_hass, standard_swedish_fees):
        """Test parsing Nordpool data through PriceProvider."""
        nordpool_data = load_nordpool_yaml()
        
        # Create a mock state object
        mock_state = MagicMock()
        mock_state.attributes = nordpool_data
        mock_hass.states.get.return_value = mock_state
        
        # Create provider
        provider = PriceProvider(
            mock_hass,
            "sensor.nordpool_kwh_se3_sek_3_10_025",
            standard_swedish_fees
        )
        
        # Get prices
        prices = provider.get_hourly_prices()
        
        assert len(prices) > 0, "No prices parsed from Nordpool data"
        assert all(isinstance(p, PricePoint) for p in prices), \
            "All results should be PricePoint objects"
        
        # Check that times are sorted
        times = [p.time for p in prices]
        assert times == sorted(times), "Prices should be sorted by time"
        
        # Check that enriched prices are calculated
        for price in prices:
            assert price.enriched_sek_per_kwh > price.spot_sek_per_kwh, \
                "Enriched price should be higher than spot (due to fees)"
            assert price.enriched_sek_per_kwh > 0, \
                "Enriched price should be positive"
        
        print(f"\nParsed {len(prices)} prices from Nordpool data")
        print(f"First price: {prices[0].time}, spot={prices[0].spot_sek_per_kwh:.3f}, " \
              f"enriched={prices[0].enriched_sek_per_kwh:.3f}")


class TestPriceGapHandling:
    """Test handling of gaps in price data."""
    
    def test_gap_detection(self):
        """Test that we can detect gaps in price data."""
        spot_prices = load_price_csv("historic_energy_spot_price.csv")
        
        # Look for gaps > 2 hours
        large_gaps = []
        for i in range(len(spot_prices) - 1):
            ts1, _ = spot_prices[i]
            ts2, _ = spot_prices[i + 1]
            gap_hours = (ts2 - ts1).total_seconds() / 3600
            
            if gap_hours > 2.0:
                large_gaps.append((ts1, ts2, gap_hours))
        
        # According to sample data report, there's 1 large gap (5 hours)
        assert len(large_gaps) >= 1, "Expected at least 1 large gap in sample data"
        
        if large_gaps:
            print(f"\nFound {len(large_gaps)} gap(s) in price data:")
            for start, end, hours in large_gaps:
                print(f"  {start} → {end} ({hours:.1f}h)")
    
    def test_price_availability_window(self):
        """Test identification of continuous price availability windows."""
        spot_prices = load_price_csv("historic_energy_spot_price.csv")
        
        # Find largest continuous window (gap < 2 hours)
        windows = []
        current_start = spot_prices[0][0]
        
        for i in range(len(spot_prices) - 1):
            ts1, _ = spot_prices[i]
            ts2, _ = spot_prices[i + 1]
            gap_hours = (ts2 - ts1).total_seconds() / 3600
            
            if gap_hours > 2.0:
                # End of window
                duration = (ts1 - current_start).total_seconds() / 3600
                windows.append((current_start, ts1, duration))
                current_start = ts2
        
        # Add final window
        final_duration = (spot_prices[-1][0] - current_start).total_seconds() / 3600
        windows.append((current_start, spot_prices[-1][0], final_duration))
        
        # Find longest window
        longest = max(windows, key=lambda w: w[2])
        
        # According to sample data report, longest window should be ~160h
        assert longest[2] > 100, f"Longest continuous window should be >100h, got {longest[2]:.1f}h"
        
        print(f"\nLongest continuous price window:")
        print(f"  Start: {longest[0]}")
        print(f"  End: {longest[1]}")
        print(f"  Duration: {longest[2]:.1f} hours")


# Run with: pytest tests/test_price_provider_with_data.py -v -s
