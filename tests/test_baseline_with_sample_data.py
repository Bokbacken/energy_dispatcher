"""
Test baseline calculation using real sample data from fixtures.

This test validates that the baseline calculation correctly handles:
1. All house energy consumption
2. Exclusion of EV charging
3. Exclusion of battery grid charging (battery - PV)
4. Exclusion of both EV and battery grid charging

Based on the sample data (Oct 4-11, 2025, 167.9 hours / 7.0 days), expected values are:
- All House energy: ~1.65 kWh/h (1650 W)
- Exclude EV: ~1.36 kWh/h (1360 W)
- Exclude Battery (grid only): ~1.20 kWh/h (1200 W)
- Exclude EV and Battery (grid only): ~0.90 kWh/h (900 W)

Note: "Exclude Battery (grid only)" means excluding battery charging that occurred
during periods with no solar generation (forced grid charging at night), not simply
subtracting all battery charging or using the formula (battery - PV).
"""
import pytest
import csv
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.energy_dispatcher.coordinator import EnergyDispatcherCoordinator


@pytest.fixture
def fixtures_path():
    """Return path to test fixtures."""
    return Path(__file__).parent / "fixtures"


def load_csv_states(filepath):
    """Load CSV file and create mock state objects."""
    states = []
    with open(filepath, 'r') as f:
        reader = csv.reader(f)
        first_row = True
        for row in reader:
            if first_row:
                # Skip header if present
                if row[0].lower() == 'entity_id' or 'sensor' not in row[0].lower():
                    first_row = False
                    continue
                first_row = False
            
            try:
                # row[0] = entity_id, row[1] = state, row[2] = last_changed
                state = MagicMock()
                state.state = row[1]
                state.last_changed = datetime.fromisoformat(row[2].replace('Z', '+00:00'))
                states.append(state)
            except (ValueError, IndexError):
                pass
    
    return states


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    hass.data = {}
    hass.states = MagicMock()
    return hass


@pytest.fixture
def coordinator(mock_hass):
    """Create a coordinator instance with mocked dependencies."""
    coordinator = EnergyDispatcherCoordinator(mock_hass)
    coordinator.entry_id = "test_entry"
    
    # Mock the store with configuration
    mock_hass.data["energy_dispatcher"] = {
        "test_entry": {
            "config": {
                "runtime_lookback_hours": 168,  # ~7 days to cover all sample data
                "runtime_counter_entity": "sensor.house_energy",
                "evse_total_energy_sensor": "sensor.ev_energy",
                "batt_total_charged_energy_entity": "sensor.battery_charged_energy",
                "pv_total_energy_entity": "sensor.pv_total_energy",
                "runtime_exclude_ev": True,
                "runtime_exclude_batt_grid": True,
            },
        }
    }
    
    return coordinator


class TestBaselineWithSampleData:
    """Test baseline calculation with real sample data."""
    
    @pytest.mark.asyncio
    async def test_baseline_all_house_energy(self, coordinator, mock_hass, fixtures_path):
        """Test baseline with all house energy (no exclusions)."""
        # Load sample data
        house_states = load_csv_states(fixtures_path / "historic_total_house_energy_consumption.csv")
        
        # Disable exclusions
        mock_hass.data["energy_dispatcher"]["test_entry"]["config"]["runtime_exclude_ev"] = False
        mock_hass.data["energy_dispatcher"]["test_entry"]["config"]["runtime_exclude_batt_grid"] = False
        
        history_data = {
            "sensor.house_energy": house_states,
        }
        
        with patch('homeassistant.components.recorder.history'):
            mock_hass.async_add_executor_job = AsyncMock(return_value=history_data)
            
            result = await coordinator._calculate_48h_baseline()
            
            assert result is not None
            assert "overall" in result
            assert result["overall"] is not None
            
            # Expected: ~1.65 kWh/h (allow ±5% tolerance)
            assert 1.57 <= result["overall"] <= 1.73, f"Expected ~1.65 kWh/h, got {result['overall']:.3f} kWh/h"
    
    @pytest.mark.asyncio
    async def test_baseline_exclude_ev(self, coordinator, mock_hass, fixtures_path):
        """Test baseline with EV charging excluded."""
        # Load sample data
        house_states = load_csv_states(fixtures_path / "historic_total_house_energy_consumption.csv")
        ev_states = load_csv_states(fixtures_path / "historic_EV_total_charged_energy.csv")
        
        # Enable EV exclusion only
        mock_hass.data["energy_dispatcher"]["test_entry"]["config"]["runtime_exclude_ev"] = True
        mock_hass.data["energy_dispatcher"]["test_entry"]["config"]["runtime_exclude_batt_grid"] = False
        
        history_data = {
            "sensor.house_energy": house_states,
            "sensor.ev_energy": ev_states,
        }
        
        with patch('homeassistant.components.recorder.history'):
            mock_hass.async_add_executor_job = AsyncMock(return_value=history_data)
            
            result = await coordinator._calculate_48h_baseline()
            
            assert result is not None
            assert result["overall"] is not None
            
            # Expected: ~1.36 kWh/h (allow ±5% tolerance)
            assert 1.29 <= result["overall"] <= 1.43, f"Expected ~1.36 kWh/h, got {result['overall']:.3f} kWh/h"
    
    @pytest.mark.asyncio
    async def test_baseline_exclude_battery_grid(self, coordinator, mock_hass, fixtures_path):
        """Test baseline with battery grid charging excluded (not solar)."""
        # Load sample data
        house_states = load_csv_states(fixtures_path / "historic_total_house_energy_consumption.csv")
        batt_states = load_csv_states(fixtures_path / "historic_total_charged_energy_to_batteries.csv")
        pv_states = load_csv_states(fixtures_path / "historic_total_energy_from_pv.csv")
        
        # Enable battery grid exclusion only
        mock_hass.data["energy_dispatcher"]["test_entry"]["config"]["runtime_exclude_ev"] = False
        mock_hass.data["energy_dispatcher"]["test_entry"]["config"]["runtime_exclude_batt_grid"] = True
        
        history_data = {
            "sensor.house_energy": house_states,
            "sensor.battery_charged_energy": batt_states,
            "sensor.pv_total_energy": pv_states,
        }
        
        with patch('homeassistant.components.recorder.history'):
            mock_hass.async_add_executor_job = AsyncMock(return_value=history_data)
            
            result = await coordinator._calculate_48h_baseline()
            
            assert result is not None
            assert result["overall"] is not None
            
            # Expected: ~1.20 kWh/h (allow ±5% tolerance)
            # This should be higher than excluding all battery charging (~0.998)
            assert 1.14 <= result["overall"] <= 1.26, f"Expected ~1.20 kWh/h, got {result['overall']:.3f} kWh/h"
            # Verify it's NOT the wrong calculation (excluding all battery charging would be ~0.998)
            assert result["overall"] > 1.05, "Should not be excluding all battery charging, only grid charging"
    
    @pytest.mark.asyncio
    async def test_baseline_exclude_ev_and_battery_grid(self, coordinator, mock_hass, fixtures_path):
        """Test baseline with both EV and battery grid charging excluded."""
        # Load sample data
        house_states = load_csv_states(fixtures_path / "historic_total_house_energy_consumption.csv")
        ev_states = load_csv_states(fixtures_path / "historic_EV_total_charged_energy.csv")
        batt_states = load_csv_states(fixtures_path / "historic_total_charged_energy_to_batteries.csv")
        pv_states = load_csv_states(fixtures_path / "historic_total_energy_from_pv.csv")
        
        # Enable both exclusions
        mock_hass.data["energy_dispatcher"]["test_entry"]["config"]["runtime_exclude_ev"] = True
        mock_hass.data["energy_dispatcher"]["test_entry"]["config"]["runtime_exclude_batt_grid"] = True
        
        history_data = {
            "sensor.house_energy": house_states,
            "sensor.ev_energy": ev_states,
            "sensor.battery_charged_energy": batt_states,
            "sensor.pv_total_energy": pv_states,
        }
        
        with patch('homeassistant.components.recorder.history'):
            mock_hass.async_add_executor_job = AsyncMock(return_value=history_data)
            
            result = await coordinator._calculate_48h_baseline()
            
            assert result is not None
            assert result["overall"] is not None
            
            # Expected: ~0.90 kWh/h (allow ±8% tolerance due to aggregation differences)
            assert 0.83 <= result["overall"] <= 0.97, f"Expected ~0.90 kWh/h, got {result['overall']:.3f} kWh/h"
            # Verify it's NOT the wrong calculation (excluding all battery would be ~0.742)
            assert result["overall"] > 0.75, "Should not be excluding all battery charging, only grid charging"
