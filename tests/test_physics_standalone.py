"""Standalone tests for physics calculations without Home Assistant dependencies."""
import math
import pytest


# Copy physics functions here for standalone testing
def clearsky_ghi_haurwitz(zenith_deg: float) -> float:
    """Calculate clear-sky GHI using simplified Haurwitz model."""
    if zenith_deg >= 90.0:
        return 0.0
    
    z_rad = math.radians(zenith_deg)
    cos_z = math.cos(z_rad)
    
    if cos_z <= 0:
        return 0.0
    
    ghi_cs = 1098.0 * cos_z * math.exp(-0.059 / cos_z)
    return max(0.0, ghi_cs)


def cloud_to_ghi(ghi_clear: float, cloud_fraction: float) -> float:
    """Map cloud cover to GHI using Kasten-Czeplak model."""
    C = max(0.0, min(1.0, cloud_fraction))
    ghi = ghi_clear * (1.0 - 0.75 * (C ** 3.4))
    return max(0.0, ghi)


def erbs_decomposition(ghi: float, zenith_deg: float, dni_extra: float):
    """Decompose GHI into DHI and DNI using Erbs correlation."""
    if zenith_deg >= 90.0 or ghi <= 0:
        return 0.0, 0.0
    
    z_rad = math.radians(zenith_deg)
    cos_z = math.cos(z_rad)
    
    if cos_z <= 0:
        return 0.0, 0.0
    
    kt = ghi / max(dni_extra * cos_z, 1.0)
    kt = max(0.0, min(1.0, kt))
    
    if kt <= 0.22:
        Fd = 1.0 - 0.09 * kt
    elif kt <= 0.80:
        Fd = 0.9511 - 0.1604 * kt + 4.388 * kt**2 - 16.638 * kt**3 + 12.336 * kt**4
    else:
        Fd = 0.165
    
    Fd = max(0.0, min(1.0, Fd))
    dhi = Fd * ghi
    dni = max(0.0, (ghi - dhi) / max(cos_z, 1e-6))
    
    return dhi, dni


def horizon_alt_interp(horizon12_deg, sun_az_deg: float) -> float:
    """Interpolate horizon altitude at a given azimuth."""
    if not horizon12_deg or len(horizon12_deg) != 12:
        return 0.0
    
    az = sun_az_deg % 360.0
    i0 = int(az // 30) % 12
    i1 = (i0 + 1) % 12
    frac = (az - 30 * i0) / 30.0
    
    h0 = horizon12_deg[i0]
    h1 = horizon12_deg[i1]
    
    return h0 * (1 - frac) + h1 * frac


def approximate_svf(horizon12_deg) -> float:
    """Approximate sky-view factor from 12-point horizon profile."""
    if not horizon12_deg:
        return 1.0
    
    avg_sin = sum(math.sin(math.radians(max(0, h))) for h in horizon12_deg) / len(horizon12_deg)
    svf = 1.0 - avg_sin
    
    return max(0.7, min(1.0, svf))


def cell_temp_pvsyst(poa: float, temp_amb: float, wind_speed: float = 1.0) -> float:
    """Calculate cell temperature using simplified PVsyst-like model."""
    noct = 45.0
    delta_t = (noct - 20.0) * (poa / 800.0)
    wind_factor = max(0.7, 1.0 - 0.03 * (wind_speed - 1.0))
    tcell = temp_amb + delta_t * wind_factor
    return tcell


def pvwatts_dc(poa: float, tcell: float, pdc0_w: float, gamma_pdc_per_c: float = -0.0038) -> float:
    """Calculate DC power output using PVWatts model."""
    temp_factor = 1.0 + gamma_pdc_per_c * (tcell - 25.0)
    pdc = pdc0_w * (poa / 1000.0) * temp_factor
    return max(0.0, pdc)


def pvwatts_ac(pdc_w: float, pac_max_w=None, eta_inv_nom: float = 0.96) -> float:
    """Calculate AC power output with inverter efficiency and clipping."""
    pac = pdc_w * eta_inv_nom
    if pac_max_w is not None:
        pac = min(pac, pac_max_w)
    return max(0.0, pac)


def eccentricity_correction(day_of_year: int) -> float:
    """Calculate Earth-Sun distance correction factor."""
    B = 2 * math.pi * (day_of_year - 1) / 365.0
    E0 = 1.000110 + 0.034221 * math.cos(B) + 0.001280 * math.sin(B)
    E0 += 0.000719 * math.cos(2 * B) + 0.000077 * math.sin(2 * B)
    return E0


# Tests
class TestClearSkyModels:
    """Test clear-sky irradiance models."""
    
    def test_haurwitz_at_zenith_0(self):
        """Test Haurwitz at zenith = 0° (sun directly overhead)."""
        ghi = clearsky_ghi_haurwitz(0.0)
        assert 1000 <= ghi <= 1150
    
    def test_haurwitz_at_zenith_90(self):
        """Test Haurwitz at zenith = 90° (sun at horizon)."""
        ghi = clearsky_ghi_haurwitz(90.0)
        assert ghi == 0.0
    
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
        assert 0 < ghi < 300
    
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
    
    def test_erbs_reasonable_split(self):
        """Test that Erbs produces reasonable DNI/DHI split."""
        ghi = 800.0
        zenith = 30.0
        dni_extra = 1367.0
        
        dhi, dni = erbs_decomposition(ghi, zenith, dni_extra)
        
        assert dhi >= 0.0
        assert dni >= 0.0
        assert dhi <= ghi
        
        cos_z = math.cos(math.radians(zenith))
        reconstructed = dni * cos_z + dhi
        assert reconstructed == pytest.approx(ghi, abs=50)


class TestHorizonBlocking:
    """Test horizon interpolation."""
    
    def test_horizon_interp_north(self):
        """Test interpolation at North (0°)."""
        horizon12 = [10.0] * 12
        h = horizon_alt_interp(horizon12, 0.0)
        assert h == pytest.approx(10.0)
    
    def test_horizon_interp_between_points(self):
        """Test interpolation between points."""
        horizon12 = [10.0, 20.0] + [0.0] * 10
        h = horizon_alt_interp(horizon12, 15.0)
        assert h == pytest.approx(15.0, rel=0.01)
    
    def test_svf_all_zero(self):
        """Test SVF with no horizon obstruction."""
        horizon12 = [0.0] * 12
        svf = approximate_svf(horizon12)
        assert svf == pytest.approx(1.0, rel=0.01)


class TestTemperatureModel:
    """Test cell temperature model."""
    
    def test_cell_temp_at_stc(self):
        """Test cell temperature at STC-like conditions."""
        poa = 1000.0
        temp_amb = 25.0
        wind = 1.0
        
        tcell = cell_temp_pvsyst(poa, temp_amb, wind)
        assert tcell > temp_amb
        assert 30 < tcell < 60
    
    def test_cell_temp_increases_with_irradiance(self):
        """Test that cell temp increases with irradiance."""
        temp_amb = 20.0
        wind = 1.0
        
        tcell_low = cell_temp_pvsyst(200.0, temp_amb, wind)
        tcell_high = cell_temp_pvsyst(1000.0, temp_amb, wind)
        
        assert tcell_high > tcell_low


class TestPVWattsModel:
    """Test PVWatts DC and AC models."""
    
    def test_pvwatts_dc_at_stc(self):
        """Test DC power at STC conditions."""
        poa = 1000.0
        tcell = 25.0
        pdc0 = 5000.0
        
        pdc = pvwatts_dc(poa, tcell, pdc0)
        assert pdc == pytest.approx(pdc0, rel=0.01)
    
    def test_pvwatts_dc_temp_coefficient(self):
        """Test that DC decreases with temperature."""
        poa = 1000.0
        pdc0 = 5000.0
        
        pdc_25 = pvwatts_dc(poa, 25.0, pdc0)
        pdc_50 = pvwatts_dc(poa, 50.0, pdc0)
        
        assert pdc_50 < pdc_25
    
    def test_pvwatts_ac_clipping(self):
        """Test AC clipping at inverter limit."""
        pdc = 10000.0
        pac_max = 5000.0
        
        pac = pvwatts_ac(pdc, pac_max)
        assert pac == pac_max


class TestEccentricityCorrection:
    """Test eccentricity correction factor."""
    
    def test_eccentricity_range(self):
        """Test that eccentricity is close to 1.0."""
        e0_jan = eccentricity_correction(1)
        e0_jul = eccentricity_correction(182)
        
        assert 0.96 < e0_jan < 1.04
        assert 0.96 < e0_jul < 1.04
        
        # Earth is closest to sun in January
        assert e0_jan > 1.0
        # Earth is farthest from sun in July
        assert e0_jul < 1.0
