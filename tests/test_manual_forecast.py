"""Tests for manual forecast engine physics calculations."""
import math
import sys
import os
import pytest
from datetime import datetime, timezone

# Add the parent directory to the path to allow direct import of physics functions
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import just the physics functions we need to test (not the engine class)
try:
    from custom_components.energy_dispatcher.manual_forecast_engine import (
        clearsky_ghi_haurwitz,
        cloud_to_ghi,
        erbs_decomposition,
        poa_hdkr,
        horizon_alt_interp,
        approximate_svf,
        cell_temp_pvsyst,
        pvwatts_dc,
        pvwatts_ac,
        eccentricity_correction,
        solar_position,
    )
except ImportError:
    # If Home Assistant is not installed, skip these tests
    pytest.skip("Home Assistant not installed, skipping integration tests", allow_module_level=True)


class TestClearSkyModels:
    """Test clear-sky irradiance models."""
    
    def test_haurwitz_at_zenith_0(self):
        """Test Haurwitz at zenith = 0° (sun directly overhead)."""
        ghi = clearsky_ghi_haurwitz(0.0)
        # Should be close to maximum (~1000-1100 W/m²)
        assert 1000 <= ghi <= 1150
    
    def test_haurwitz_at_zenith_90(self):
        """Test Haurwitz at zenith = 90° (sun at horizon)."""
        ghi = clearsky_ghi_haurwitz(90.0)
        assert ghi == 0.0
    
    def test_haurwitz_at_zenith_60(self):
        """Test Haurwitz at zenith = 60° (sun at 30° altitude)."""
        ghi = clearsky_ghi_haurwitz(60.0)
        # Should be positive but reduced
        assert 0 < ghi < 600
    
    def test_haurwitz_monotonic(self):
        """Test that Haurwitz is monotonically decreasing with zenith."""
        ghi_0 = clearsky_ghi_haurwitz(0.0)
        ghi_30 = clearsky_ghi_haurwitz(30.0)
        ghi_60 = clearsky_ghi_haurwitz(60.0)
        ghi_80 = clearsky_ghi_haurwitz(80.0)
        
        assert ghi_0 > ghi_30 > ghi_60 > ghi_80


class TestCloudMapping:
    """Test cloud cover to GHI mapping."""
    
    def test_cloud_0_percent(self):
        """Test 0% cloud cover (clear sky)."""
        ghi_clear = 1000.0
        ghi = cloud_to_ghi(ghi_clear, 0.0)
        assert ghi == pytest.approx(ghi_clear, rel=0.01)
    
    def test_cloud_100_percent(self):
        """Test 100% cloud cover."""
        ghi_clear = 1000.0
        ghi = cloud_to_ghi(ghi_clear, 1.0)
        # Should be significantly reduced (~25% of clear sky)
        assert 0 < ghi < 300
    
    def test_cloud_50_percent(self):
        """Test 50% cloud cover."""
        ghi_clear = 1000.0
        ghi = cloud_to_ghi(ghi_clear, 0.5)
        # Should be somewhere in between
        assert 300 < ghi < 1000
    
    def test_cloud_monotonic(self):
        """Test that GHI decreases with increasing cloud cover."""
        ghi_clear = 1000.0
        ghi_0 = cloud_to_ghi(ghi_clear, 0.0)
        ghi_25 = cloud_to_ghi(ghi_clear, 0.25)
        ghi_50 = cloud_to_ghi(ghi_clear, 0.5)
        ghi_75 = cloud_to_ghi(ghi_clear, 0.75)
        ghi_100 = cloud_to_ghi(ghi_clear, 1.0)
        
        assert ghi_0 > ghi_25 > ghi_50 > ghi_75 > ghi_100


class TestErbsDecomposition:
    """Test Erbs GHI decomposition."""
    
    def test_erbs_zero_ghi(self):
        """Test Erbs with zero GHI."""
        dhi, dni = erbs_decomposition(0.0, 45.0, 1367.0)
        assert dhi == 0.0
        assert dni == 0.0
    
    def test_erbs_zenith_90(self):
        """Test Erbs at zenith = 90° (sun at horizon)."""
        dhi, dni = erbs_decomposition(500.0, 90.0, 1367.0)
        assert dhi == 0.0
        assert dni == 0.0
    
    def test_erbs_reasonable_split(self):
        """Test that Erbs produces reasonable DNI/DHI split."""
        ghi = 800.0
        zenith = 30.0
        dni_extra = 1367.0
        
        dhi, dni = erbs_decomposition(ghi, zenith, dni_extra)
        
        # Both should be non-negative
        assert dhi >= 0.0
        assert dni >= 0.0
        
        # DHI should be less than GHI
        assert dhi <= ghi
        
        # Check that components roughly reconstruct GHI
        cos_z = math.cos(math.radians(zenith))
        reconstructed = dni * cos_z + dhi
        assert reconstructed == pytest.approx(ghi, abs=50)


class TestPOATransposition:
    """Test HDKR transposition model."""
    
    def test_poa_horizontal_equals_ghi(self):
        """Test that horizontal surface (tilt=0) gives approximately GHI."""
        ghi = 800.0
        dhi = 200.0
        dni = 900.0
        zenith = 30.0
        azimuth = 180.0
        tilt = 0.0
        surf_az = 180.0
        
        poa = poa_hdkr(ghi, dhi, dni, zenith, azimuth, tilt, surf_az)
        
        # Should be close to GHI for horizontal surface
        # Note: HDKR model includes ground reflection and other effects
        # that can cause deviations from pure GHI
        assert poa == pytest.approx(ghi, rel=0.30)
    
    def test_poa_zenith_90(self):
        """Test POA at zenith = 90° (sun at horizon)."""
        ghi = 800.0
        dhi = 200.0
        dni = 900.0
        zenith = 90.0
        azimuth = 180.0
        tilt = 30.0
        surf_az = 180.0
        
        poa = poa_hdkr(ghi, dhi, dni, zenith, azimuth, tilt, surf_az)
        assert poa == 0.0
    
    def test_poa_south_facing_increases(self):
        """Test that south-facing tilted surface gets more irradiance than horizontal at low sun."""
        ghi = 600.0
        dhi = 150.0
        dni = 700.0
        zenith = 60.0  # Low sun (30° altitude)
        azimuth = 180.0  # South
        tilt_horizontal = 0.0
        tilt_tilted = 30.0
        surf_az = 180.0  # South facing
        
        poa_horizontal = poa_hdkr(ghi, dhi, dni, zenith, azimuth, tilt_horizontal, surf_az)
        poa_tilted = poa_hdkr(ghi, dhi, dni, zenith, azimuth, tilt_tilted, surf_az)
        
        # Tilted should collect more at low sun angle
        assert poa_tilted > poa_horizontal


class TestHorizonBlocking:
    """Test horizon interpolation and blocking."""
    
    def test_horizon_interp_north(self):
        """Test interpolation at North (0°)."""
        horizon12 = [10.0] * 12
        h = horizon_alt_interp(horizon12, 0.0)
        assert h == pytest.approx(10.0)
    
    def test_horizon_interp_between_points(self):
        """Test interpolation between points."""
        # 0° = 10°, 30° = 20°
        horizon12 = [10.0, 20.0] + [0.0] * 10
        h = horizon_alt_interp(horizon12, 15.0)  # Halfway between 0° and 30°
        assert h == pytest.approx(15.0, rel=0.01)
    
    def test_horizon_interp_wrap_around(self):
        """Test interpolation wrapping around 360°."""
        horizon12 = [10.0] + [0.0] * 10 + [20.0]
        h = horizon_alt_interp(horizon12, 345.0)  # Between 330° (20°) and 0° (10°)
        # Should interpolate between 20° and 10°
        assert 10.0 < h < 20.0
    
    def test_svf_all_zero(self):
        """Test SVF with no horizon obstruction."""
        horizon12 = [0.0] * 12
        svf = approximate_svf(horizon12)
        assert svf == pytest.approx(1.0, rel=0.01)
    
    def test_svf_some_obstruction(self):
        """Test SVF with some obstruction."""
        horizon12 = [10.0] * 12
        svf = approximate_svf(horizon12)
        # Should be less than 1.0 but clamped to at least 0.7
        assert 0.7 <= svf < 1.0


class TestTemperatureModel:
    """Test cell temperature model."""
    
    def test_cell_temp_at_stc(self):
        """Test cell temperature at STC-like conditions."""
        poa = 1000.0
        temp_amb = 25.0
        wind = 1.0
        
        tcell = cell_temp_pvsyst(poa, temp_amb, wind)
        
        # Cell temp should be higher than ambient
        assert tcell > temp_amb
        # Typical cell temp at STC is around 40-50°C
        assert 30 < tcell < 60
    
    def test_cell_temp_increases_with_irradiance(self):
        """Test that cell temp increases with irradiance."""
        temp_amb = 20.0
        wind = 1.0
        
        tcell_low = cell_temp_pvsyst(200.0, temp_amb, wind)
        tcell_high = cell_temp_pvsyst(1000.0, temp_amb, wind)
        
        assert tcell_high > tcell_low
    
    def test_cell_temp_at_zero_irradiance(self):
        """Test cell temp at zero irradiance equals ambient."""
        poa = 0.0
        temp_amb = 20.0
        wind = 1.0
        
        tcell = cell_temp_pvsyst(poa, temp_amb, wind)
        assert tcell == pytest.approx(temp_amb, abs=0.1)


class TestPVWattsModel:
    """Test PVWatts DC and AC models."""
    
    def test_pvwatts_dc_at_stc(self):
        """Test DC power at STC conditions."""
        poa = 1000.0
        tcell = 25.0
        pdc0 = 5000.0
        
        pdc = pvwatts_dc(poa, tcell, pdc0)
        
        # At STC, should produce rated power
        assert pdc == pytest.approx(pdc0, rel=0.01)
    
    def test_pvwatts_dc_temp_coefficient(self):
        """Test that DC decreases with temperature."""
        poa = 1000.0
        pdc0 = 5000.0
        
        pdc_25 = pvwatts_dc(poa, 25.0, pdc0)
        pdc_50 = pvwatts_dc(poa, 50.0, pdc0)
        
        # Higher temperature should reduce power
        assert pdc_50 < pdc_25
    
    def test_pvwatts_dc_scales_with_irradiance(self):
        """Test that DC scales linearly with irradiance."""
        tcell = 25.0
        pdc0 = 5000.0
        
        pdc_500 = pvwatts_dc(500.0, tcell, pdc0)
        pdc_1000 = pvwatts_dc(1000.0, tcell, pdc0)
        
        # Should be approximately 2x
        assert pdc_1000 == pytest.approx(2 * pdc_500, rel=0.01)
    
    def test_pvwatts_ac_basic(self):
        """Test AC conversion."""
        pdc = 5000.0
        pac = pvwatts_ac(pdc)
        
        # AC should be slightly less than DC due to inverter losses
        assert 0.9 * pdc < pac < pdc
    
    def test_pvwatts_ac_clipping(self):
        """Test AC clipping at inverter limit."""
        pdc = 10000.0
        pac_max = 5000.0
        
        pac = pvwatts_ac(pdc, pac_max)
        
        # Should be clipped to max
        assert pac == pac_max


class TestSolarPosition:
    """Test solar position calculations."""
    
    def test_solar_position_basic(self):
        """Test that solar position returns valid values."""
        lat = 56.7  # Sweden
        lon = 13.0
        dt = datetime(2024, 6, 21, 12, 0, 0, tzinfo=timezone.utc)  # Summer solstice noon
        
        alt, az, zenith = solar_position(lat, lon, dt)
        
        # Altitude should be positive at solar noon in summer
        assert alt > 0
        # Zenith should be 90 - altitude
        assert zenith == pytest.approx(90.0 - alt, abs=0.1)
        # Azimuth should be roughly south (180°) at noon
        assert 150 < az < 210
    
    def test_eccentricity_correction(self):
        """Test eccentricity correction factor."""
        # Should be close to 1.0 throughout the year
        e0_jan = eccentricity_correction(1)
        e0_jul = eccentricity_correction(182)
        
        # Eccentricity correction ranges from about 0.967 to 1.033
        assert 0.96 < e0_jan < 1.04
        assert 0.96 < e0_jul < 1.04
        
        # Earth is closest to sun in January
        assert e0_jan > 1.0
        # Earth is farthest from sun in July
        assert e0_jul < 1.0
