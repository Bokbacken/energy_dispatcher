"""Tests for vehicle manager."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from custom_components.energy_dispatcher.vehicle_manager import VehicleManager
from custom_components.energy_dispatcher.models import (
    VehicleConfig,
    ChargerConfig,
    ChargingMode,
)


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    return MagicMock()


@pytest.fixture
def manager(mock_hass):
    """Create a VehicleManager instance."""
    return VehicleManager(mock_hass)


@pytest.fixture
def tesla_config():
    """Tesla Model Y LR configuration."""
    return VehicleConfig.tesla_model_y_lr_2022()


@pytest.fixture
def ioniq_config():
    """Hyundai Ioniq configuration."""
    return VehicleConfig.hyundai_ioniq_electric_2019()


@pytest.fixture
def charger_3phase():
    """3-phase charger configuration."""
    return ChargerConfig.generic_3phase_16a()


class TestVehicleManagement:
    """Test vehicle management functionality."""

    def test_add_vehicle(self, manager, tesla_config):
        """Test adding a vehicle."""
        manager.add_vehicle(tesla_config)
        
        vehicle = manager.get_vehicle(tesla_config.id)
        assert vehicle is not None
        assert vehicle.name == "Tesla Model Y Long Range"
        assert vehicle.battery_kwh == 75.0
        
        # Should create initial state
        state = manager.get_vehicle_state(tesla_config.id)
        assert state is not None
        assert state.current_soc == 80.0

    def test_add_multiple_vehicles(self, manager, tesla_config, ioniq_config):
        """Test adding multiple vehicles."""
        manager.add_vehicle(tesla_config)
        manager.add_vehicle(ioniq_config)
        
        vehicles = manager.get_vehicles()
        assert len(vehicles) == 2
        
        tesla = manager.get_vehicle(tesla_config.id)
        ioniq = manager.get_vehicle(ioniq_config.id)
        
        assert tesla.battery_kwh == 75.0
        assert ioniq.battery_kwh == 28.0

    def test_remove_vehicle(self, manager, tesla_config):
        """Test removing a vehicle."""
        manager.add_vehicle(tesla_config)
        assert manager.get_vehicle(tesla_config.id) is not None
        
        manager.remove_vehicle(tesla_config.id)
        assert manager.get_vehicle(tesla_config.id) is None

    def test_update_vehicle_state(self, manager, tesla_config):
        """Test updating vehicle state."""
        manager.add_vehicle(tesla_config)
        
        manager.update_vehicle_state(
            tesla_config.id,
            current_soc=50.0,
            target_soc=90.0,
            charging_mode=ChargingMode.ASAP,
        )
        
        state = manager.get_vehicle_state(tesla_config.id)
        assert state.current_soc == 50.0
        assert state.target_soc == 90.0
        assert state.charging_mode == ChargingMode.ASAP


class TestChargerManagement:
    """Test charger management functionality."""

    def test_add_charger(self, manager, charger_3phase):
        """Test adding a charger."""
        manager.add_charger(charger_3phase)
        
        charger = manager.get_charger(charger_3phase.id)
        assert charger is not None
        assert charger.max_current == 16
        assert charger.phases == 3

    def test_add_multiple_chargers(self, manager):
        """Test adding multiple chargers."""
        charger1 = ChargerConfig.generic_3phase_16a()
        charger2 = ChargerConfig.generic_1phase_16a()
        
        manager.add_charger(charger1)
        manager.add_charger(charger2)
        
        chargers = manager.get_chargers()
        assert len(chargers) == 2

    def test_remove_charger(self, manager, charger_3phase):
        """Test removing a charger."""
        manager.add_charger(charger_3phase)
        assert manager.get_charger(charger_3phase.id) is not None
        
        manager.remove_charger(charger_3phase.id)
        assert manager.get_charger(charger_3phase.id) is None

    def test_associate_vehicle_charger(self, manager, tesla_config, charger_3phase):
        """Test associating a vehicle with a charger."""
        manager.add_vehicle(tesla_config)
        manager.add_charger(charger_3phase)
        
        manager.associate_vehicle_charger(tesla_config.id, charger_3phase.id)
        
        vehicle = manager.get_vehicle(tesla_config.id)
        assert vehicle.charger_id == charger_3phase.id
        
        associated_vehicle = manager.get_vehicle_for_charger(charger_3phase.id)
        assert associated_vehicle.id == tesla_config.id


class TestChargingSession:
    """Test charging session functionality."""

    def test_start_session(self, manager, tesla_config, charger_3phase):
        """Test starting a charging session."""
        manager.add_vehicle(tesla_config)
        manager.add_charger(charger_3phase)
        manager.update_vehicle_state(tesla_config.id, current_soc=40.0, target_soc=80.0)
        
        session = manager.start_charging_session(
            tesla_config.id,
            charger_3phase.id,
        )
        
        assert session is not None
        assert session.vehicle_id == tesla_config.id
        assert session.charger_id == charger_3phase.id
        assert session.start_soc == 40.0
        assert session.target_soc == 80.0
        assert session.active is True

    def test_end_session(self, manager, tesla_config, charger_3phase):
        """Test ending a charging session."""
        manager.add_vehicle(tesla_config)
        manager.add_charger(charger_3phase)
        manager.update_vehicle_state(tesla_config.id, current_soc=40.0, target_soc=80.0)
        
        manager.start_charging_session(tesla_config.id, charger_3phase.id)
        manager.update_vehicle_state(tesla_config.id, current_soc=80.0)
        
        session = manager.end_charging_session(tesla_config.id, energy_delivered=30.0)
        
        assert session is not None
        assert session.active is False
        assert session.end_soc == 80.0
        assert session.energy_delivered == 30.0

    def test_session_with_deadline(self, manager, tesla_config, charger_3phase):
        """Test session with deadline."""
        manager.add_vehicle(tesla_config)
        manager.add_charger(charger_3phase)
        
        deadline = datetime.now() + timedelta(hours=8)
        session = manager.start_charging_session(
            tesla_config.id,
            charger_3phase.id,
            deadline=deadline,
            mode=ChargingMode.DEADLINE,
        )
        
        assert session.deadline == deadline
        assert session.mode == ChargingMode.DEADLINE

    def test_multiple_sessions(self, manager, tesla_config, ioniq_config, charger_3phase):
        """Test multiple active sessions."""
        charger2 = ChargerConfig.generic_1phase_16a()
        
        manager.add_vehicle(tesla_config)
        manager.add_vehicle(ioniq_config)
        manager.add_charger(charger_3phase)
        manager.add_charger(charger2)
        
        session1 = manager.start_charging_session(tesla_config.id, charger_3phase.id)
        session2 = manager.start_charging_session(ioniq_config.id, charger2.id)
        
        active_sessions = manager.get_all_active_sessions()
        assert len(active_sessions) == 2


class TestCalculations:
    """Test calculation functions."""

    def test_calculate_required_energy(self, manager, tesla_config):
        """Test energy requirement calculation."""
        manager.add_vehicle(tesla_config)
        manager.update_vehicle_state(tesla_config.id, current_soc=40.0, target_soc=80.0)
        
        required = manager.calculate_required_energy(tesla_config.id)
        # 40% of 75 kWh = 30 kWh
        assert required == pytest.approx(30.0)

    def test_calculate_charging_time(self, manager, tesla_config):
        """Test charging time calculation."""
        manager.add_vehicle(tesla_config)
        manager.update_vehicle_state(tesla_config.id, current_soc=40.0, target_soc=80.0)
        
        # 16A, 3-phase, 230V, 92% efficiency
        # Power = 230 * 16 * 3 * 0.92 / 1000 = 10.166 kW
        # Time = 30 kWh / 10.166 kW ≈ 2.95 hours
        hours = manager.calculate_charging_time(tesla_config.id, 16)
        assert hours == pytest.approx(2.95, rel=0.01)

    def test_calculate_charging_time_single_phase(self, manager, ioniq_config):
        """Test charging time for single-phase vehicle."""
        manager.add_vehicle(ioniq_config)
        manager.update_vehicle_state(ioniq_config.id, current_soc=20.0, target_soc=100.0)
        
        # 80% of 28 kWh = 22.4 kWh needed
        # 16A, 1-phase, 230V, 88% efficiency
        # Power = 230 * 16 * 1 * 0.88 / 1000 = 3.238 kW
        # Time = 22.4 / 3.238 ≈ 6.92 hours
        hours = manager.calculate_charging_time(ioniq_config.id, 16)
        assert hours == pytest.approx(6.92, rel=0.01)


class TestVehiclePresets:
    """Test vehicle preset configurations."""

    def test_tesla_model_y_preset(self):
        """Test Tesla Model Y LR preset."""
        tesla = VehicleConfig.tesla_model_y_lr_2022()
        
        assert tesla.brand == "Tesla"
        assert tesla.model == "Model Y Long Range 2022"
        assert tesla.battery_kwh == 75.0
        assert tesla.max_charge_current == 16
        assert tesla.phases == 3
        assert tesla.voltage == 230
        assert tesla.default_target_soc == 80.0
        assert tesla.charging_efficiency == 0.92
        assert tesla.has_api is False

    def test_hyundai_ioniq_preset(self):
        """Test Hyundai Ioniq preset."""
        ioniq = VehicleConfig.hyundai_ioniq_electric_2019()
        
        assert ioniq.brand == "Hyundai"
        assert ioniq.model == "Ioniq Electric 2019"
        assert ioniq.battery_kwh == 28.0
        assert ioniq.max_charge_current == 16
        assert ioniq.phases == 1
        assert ioniq.voltage == 230
        assert ioniq.default_target_soc == 100.0
        assert ioniq.charging_efficiency == 0.88
        assert ioniq.has_api is False


class TestChargerPresets:
    """Test charger preset configurations."""

    def test_3phase_charger_preset(self):
        """Test 3-phase charger preset."""
        charger = ChargerConfig.generic_3phase_16a()
        
        assert charger.brand == "Generic"
        assert charger.max_current == 16
        assert charger.min_current == 6
        assert charger.phases == 3
        assert charger.voltage == 230

    def test_1phase_charger_preset(self):
        """Test 1-phase charger preset."""
        charger = ChargerConfig.generic_1phase_16a()
        
        assert charger.brand == "Generic"
        assert charger.max_current == 16
        assert charger.phases == 1
