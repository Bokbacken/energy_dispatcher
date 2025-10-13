"""Unit tests for config_flow schema validation."""
import pytest
from unittest.mock import MagicMock

from custom_components.energy_dispatcher.config_flow import (
    _schema_user,
    DEFAULTS,
    EnergyDispatcherConfigFlow,
)
from custom_components.energy_dispatcher.const import (
    CONF_FS_LAT,
    CONF_FS_LON,
    CONF_FS_PLANES,
    CONF_FS_HORIZON,
    CONF_FS_APIKEY,
    CONF_NORDPOOL_ENTITY,
    CONF_BATT_SOC_ENTITY,
)


class TestConfigFlowSchema:
    """Test config flow schema validation."""

    def test_schema_creation_with_none_defaults(self):
        """Test that schema can be created with defaults=None (first-time setup)."""
        schema = _schema_user(defaults=None, hass=None)
        assert schema is not None

    def test_schema_creation_with_defaults_dict(self):
        """Test that schema can be created with DEFAULTS dict."""
        schema = _schema_user(defaults=DEFAULTS, hass=None)
        assert schema is not None

    def test_schema_creation_with_user_input(self):
        """Test that schema can be created with user_input (validation error case)."""
        user_input = {
            CONF_NORDPOOL_ENTITY: "sensor.nordpool_price",
            "forecast_source": "manual_physics",
        }
        schema = _schema_user(defaults=user_input, hass=None)
        assert schema is not None

    def test_all_required_fields_in_defaults(self):
        """Test that all vol.Required fields have entries in DEFAULTS."""
        # These are the required fields in the schema
        required_fields = [
            CONF_NORDPOOL_ENTITY,
            "batt_cap_kwh",
            CONF_BATT_SOC_ENTITY,
        ]
        
        for field in required_fields:
            assert field in DEFAULTS, f"Required field {field} missing from DEFAULTS"

    def test_all_optional_fields_used_in_schema_are_in_defaults(self):
        """Test that all optional fields used in schema have DEFAULTS entries."""
        # Import the optional fields that were missing in v0.8.24
        from custom_components.energy_dispatcher.config_flow import (
            CONF_HUAWEI_DEVICE_ID,
            CONF_EVSE_START_SWITCH,
            CONF_EVSE_STOP_SWITCH,
            CONF_EVSE_CURRENT_NUMBER,
        )
        from custom_components.energy_dispatcher.const import (
            CONF_BATT_MAX_CHARGE_POWER_ENTITY,
            CONF_BATT_MAX_DISCH_POWER_ENTITY,
        )
        
        optional_fields = [
            CONF_HUAWEI_DEVICE_ID,
            CONF_EVSE_START_SWITCH,
            CONF_EVSE_STOP_SWITCH,
            CONF_EVSE_CURRENT_NUMBER,
            CONF_FS_LAT,
            CONF_FS_LON,
            CONF_FS_PLANES,
            CONF_FS_HORIZON,
            CONF_FS_APIKEY,
            CONF_BATT_MAX_CHARGE_POWER_ENTITY,
            CONF_BATT_MAX_DISCH_POWER_ENTITY,
        ]
        
        for field in optional_fields:
            assert field in DEFAULTS, f"Optional field {field} missing from DEFAULTS"

    def test_latitude_step_is_valid(self):
        """Test that latitude NumberSelector has valid step value (>= 0.001)."""
        from homeassistant.helpers import selector
        
        # This should not raise an error
        config = {"min": -90, "max": 90, "step": 0.001, "mode": "box"}
        ns = selector.NumberSelector(config)
        assert ns is not None

    def test_longitude_step_is_valid(self):
        """Test that longitude NumberSelector has valid step value (>= 0.001)."""
        from homeassistant.helpers import selector
        
        # This should not raise an error
        config = {"min": -180, "max": 180, "step": 0.001, "mode": "box"}
        ns = selector.NumberSelector(config)
        assert ns is not None

    def test_invalid_step_value_raises_error(self):
        """Test that step values < 0.001 raise an error."""
        from homeassistant.helpers import selector
        
        # This should raise an error because step is too small
        config = {"min": -90, "max": 90, "step": 0.0001, "mode": "box"}
        with pytest.raises(Exception):
            selector.NumberSelector(config)

    def test_defaults_have_correct_types(self):
        """Test that DEFAULTS entries have correct types."""
        assert isinstance(DEFAULTS[CONF_NORDPOOL_ENTITY], str)
        assert isinstance(DEFAULTS[CONF_BATT_SOC_ENTITY], str)
        assert isinstance(DEFAULTS[CONF_FS_LAT], (int, float))
        assert isinstance(DEFAULTS[CONF_FS_LON], (int, float))
        assert isinstance(DEFAULTS[CONF_FS_PLANES], str)
        assert isinstance(DEFAULTS[CONF_FS_HORIZON], str)
        assert isinstance(DEFAULTS[CONF_FS_APIKEY], str)
        assert isinstance(DEFAULTS["batt_cap_kwh"], (int, float))


class TestConfigFlowAsync:
    """Test async config flow methods."""

    @pytest.mark.asyncio
    async def test_async_step_user_first_time(self):
        """Test async_step_user on first-time setup (no user_input)."""
        flow = EnergyDispatcherConfigFlow()
        
        # Mock hass attribute
        flow.hass = None
        
        result = await flow.async_step_user(user_input=None)
        
        assert result["type"] == "form"
        assert result["step_id"] == "user"
        assert "data_schema" in result

    @pytest.mark.asyncio
    async def test_async_step_user_with_validation_error(self):
        """Test async_step_user with validation error (invalid lat/lon)."""
        flow = EnergyDispatcherConfigFlow()
        flow.hass = None
        
        user_input = {
            CONF_NORDPOOL_ENTITY: "sensor.price",
            CONF_BATT_SOC_ENTITY: "sensor.battery",
            "batt_cap_kwh": 15.0,
            CONF_FS_LAT: "invalid",  # Will cause validation error
            CONF_FS_LON: 13.0,
        }
        
        result = await flow.async_step_user(user_input=user_input)
        
        # Should return form with errors
        assert result["type"] == "form"
        assert "errors" in result
        assert result["errors"].get("base") == "invalid_latlon"

    @pytest.mark.asyncio
    async def test_async_step_user_success(self):
        """Test async_step_user with valid input."""
        flow = EnergyDispatcherConfigFlow()
        flow.hass = None
        
        # Mock async_create_entry
        flow.async_create_entry = MagicMock(return_value={"type": "create_entry"})
        
        user_input = {
            CONF_NORDPOOL_ENTITY: "sensor.price",
            CONF_BATT_SOC_ENTITY: "sensor.battery",
            "batt_cap_kwh": 15.0,
            CONF_FS_LAT: 56.6967,
            CONF_FS_LON: 13.0196,
        }
        
        result = await flow.async_step_user(user_input=user_input)
        
        # Should create entry
        assert flow.async_create_entry.called
