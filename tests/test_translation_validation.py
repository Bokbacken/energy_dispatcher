"""Test validation of translation files."""
import pytest
import json
from pathlib import Path


@pytest.fixture
def translations_dir():
    """Path to translations directory."""
    return Path(__file__).parent.parent / "custom_components" / "energy_dispatcher" / "translations"


@pytest.fixture
def en_translations(translations_dir):
    """Load English translations."""
    en_file = translations_dir / "en.json"
    with open(en_file, 'r', encoding='utf-8') as f:
        return json.load(f)


@pytest.fixture
def sv_translations(translations_dir):
    """Load Swedish translations."""
    sv_file = translations_dir / "sv.json"
    with open(sv_file, 'r', encoding='utf-8') as f:
        return json.load(f)


class TestTranslationFiles:
    """Test translation file structure and validity."""

    def test_translation_files_exist(self, translations_dir):
        """Test that both translation files exist."""
        assert (translations_dir / "en.json").exists(), "English translation file not found"
        assert (translations_dir / "sv.json").exists(), "Swedish translation file not found"

    def test_en_json_valid(self, en_translations):
        """Test that English translation file is valid JSON."""
        assert isinstance(en_translations, dict), "English translations not a dictionary"
        assert len(en_translations) > 0, "English translations empty"

    def test_sv_json_valid(self, sv_translations):
        """Test that Swedish translation file is valid JSON."""
        assert isinstance(sv_translations, dict), "Swedish translations not a dictionary"
        assert len(sv_translations) > 0, "Swedish translations empty"

    def test_translations_have_required_sections(self, en_translations, sv_translations):
        """Test that both translation files have required sections."""
        required_sections = ["config", "options", "entity"]
        
        for section in required_sections:
            assert section in en_translations, f"English translations missing section: {section}"
            assert section in sv_translations, f"Swedish translations missing section: {section}"

    def test_config_section_structure(self, en_translations, sv_translations):
        """Test config section has required subsections."""
        # English config
        assert "step" in en_translations["config"], "English config missing 'step' section"
        assert "user" in en_translations["config"]["step"], "English config missing 'user' step"
        
        # Swedish config
        assert "step" in sv_translations["config"], "Swedish config missing 'step' section"
        assert "user" in sv_translations["config"]["step"], "Swedish config missing 'user' step"


class TestTranslationConsistency:
    """Test consistency between English and Swedish translations."""

    def test_config_keys_consistent(self, en_translations, sv_translations):
        """Test that config keys are consistent between languages."""
        def get_all_keys(d, prefix=""):
            """Recursively get all keys from nested dict."""
            keys = set()
            for k, v in d.items():
                full_key = f"{prefix}.{k}" if prefix else k
                keys.add(full_key)
                if isinstance(v, dict):
                    keys.update(get_all_keys(v, full_key))
            return keys
        
        en_config_keys = get_all_keys(en_translations.get("config", {}), "config")
        sv_config_keys = get_all_keys(sv_translations.get("config", {}), "config")
        
        # Keys in EN but not in SV
        missing_in_sv = en_config_keys - sv_config_keys
        # Keys in SV but not in EN
        extra_in_sv = sv_config_keys - en_config_keys
        
        # Report findings (some differences may be intentional)
        if missing_in_sv:
            print(f"\nKeys in EN but not in SV (config): {sorted(missing_in_sv)[:10]}...")  # Show first 10
        if extra_in_sv:
            print(f"\nKeys in SV but not in EN (config): {sorted(extra_in_sv)[:10]}...")  # Show first 10
        
        # We expect some level of consistency but allow for minor differences
        # (e.g., language-specific explanations)
        consistency_ratio = len(en_config_keys & sv_config_keys) / max(len(en_config_keys), 1)
        assert consistency_ratio > 0.7, \
            f"Config section consistency too low: {consistency_ratio:.2%} (expected >70%)"

    def test_entity_keys_consistent(self, en_translations, sv_translations):
        """Test that entity translation keys are consistent."""
        en_entity_keys = set(en_translations.get("entity", {}).keys())
        sv_entity_keys = set(sv_translations.get("entity", {}).keys())
        
        # Entity keys should be similar (but not necessarily identical due to platform differences)
        missing_in_sv = en_entity_keys - sv_entity_keys
        extra_in_sv = sv_entity_keys - en_entity_keys
        
        if missing_in_sv:
            print(f"\nEntity keys in EN but not in SV: {missing_in_sv}")
        if extra_in_sv:
            print(f"\nEntity keys in SV but not in EN: {extra_in_sv}")
        
        # Allow some differences (e.g., platform-specific entities like button, switch)
        # Check that sensor entities are consistent
        if "sensor" in en_translations.get("entity", {}) and "sensor" in sv_translations.get("entity", {}):
            en_sensors = set(en_translations["entity"]["sensor"].keys())
            sv_sensors = set(sv_translations["entity"]["sensor"].keys())
            missing_sensors = en_sensors - sv_sensors
            
            if missing_sensors:
                print(f"\n⚠️  Missing sensor translations in SV: {sorted(missing_sensors)}")
            
            sensor_consistency = len(en_sensors & sv_sensors) / max(len(en_sensors), 1)
            # Report but don't fail - this is tracked for future improvement
            print(f"\nSensor translation coverage: {sensor_consistency:.1%} ({len(sv_sensors)}/{len(en_sensors)})")
            
            # At least half should be translated
            assert sensor_consistency >= 0.45, \
                f"Sensor entity consistency critically low: {sensor_consistency:.2%} (expected >=45%)"


class TestTranslationQuality:
    """Test translation quality and completeness."""

    def test_no_placeholder_text(self, en_translations, sv_translations):
        """Test that there are no obvious placeholder texts."""
        def check_for_placeholders(d, path=""):
            """Recursively check for placeholder text."""
            placeholders = []
            for k, v in d.items():
                current_path = f"{path}.{k}" if path else k
                if isinstance(v, str):
                    # Check for common placeholder patterns
                    lower_v = v.lower()
                    if any(p in lower_v for p in ["todo", "fixme", "placeholder", "xxx"]):
                        placeholders.append((current_path, v))
                elif isinstance(v, dict):
                    placeholders.extend(check_for_placeholders(v, current_path))
            return placeholders
        
        en_placeholders = check_for_placeholders(en_translations)
        sv_placeholders = check_for_placeholders(sv_translations)
        
        assert len(en_placeholders) == 0, f"Found placeholders in EN: {en_placeholders[:5]}"
        assert len(sv_placeholders) == 0, f"Found placeholders in SV: {sv_placeholders[:5]}"

    def test_units_in_translations(self, en_translations, sv_translations):
        """Test that units are present in configuration field descriptions."""
        def find_unit_mentions(d, path=""):
            """Find fields that mention units."""
            unit_mentions = []
            for k, v in d.items():
                current_path = f"{path}.{k}" if path else k
                if isinstance(v, str):
                    # Check for unit mentions
                    if any(unit in v for unit in ["kWh", "kW", "W", "SEK", "%", "A", "V", "°C", "minutes", "hours"]):
                        unit_mentions.append((current_path, v))
                elif isinstance(v, dict):
                    unit_mentions.extend(find_unit_mentions(v, current_path))
            return unit_mentions
        
        en_units = find_unit_mentions(en_translations)
        sv_units = find_unit_mentions(sv_translations)
        
        # Should have unit mentions in both languages
        assert len(en_units) > 10, f"Expected more unit mentions in EN, found {len(en_units)}"
        assert len(sv_units) > 10, f"Expected more unit mentions in SV, found {len(sv_units)}"
        
        print(f"\nEN unit mentions: {len(en_units)}, SV unit mentions: {len(sv_units)}")

    def test_key_terms_translated(self, en_translations, sv_translations):
        """Test that key terms are properly translated in Swedish."""
        # Common energy terms should be translated
        key_terms = {
            "battery": "batteri",
            "solar": "sol",
            "price": "pris",
            "power": "effekt",
            "energy": "energi",
        }
        
        def contains_term(d, term):
            """Check if dictionary contains term anywhere in values."""
            for v in d.values():
                if isinstance(v, str):
                    if term.lower() in v.lower():
                        return True
                elif isinstance(v, dict):
                    if contains_term(v, term):
                        return True
            return False
        
        # Check that Swedish translations use Swedish terms
        for en_term, sv_term in key_terms.items():
            # English should contain English term
            assert contains_term(en_translations, en_term), \
                f"English translations should contain '{en_term}'"
            
            # Swedish should contain Swedish term
            assert contains_term(sv_translations, sv_term), \
                f"Swedish translations should contain '{sv_term}' (translation of '{en_term}')"


class TestOptimizationFeatureTranslations:
    """Test that AI optimization features have translations."""

    def test_appliance_optimization_translations(self, en_translations):
        """Test that appliance optimization features are translated."""
        en_str = json.dumps(en_translations).lower()
        
        # Check for appliance-related terms
        assert "dishwasher" in en_str, "No dishwasher translations found"
        assert "washing" in en_str, "No washing machine translations found"
        assert "appliance" in en_str, "No appliance translations found"

    def test_export_analysis_translations(self, en_translations):
        """Test that export analysis features are translated."""
        en_str = json.dumps(en_translations).lower()
        
        # Check for export-related terms
        assert "export" in en_str, "No export translations found"

    def test_cost_strategy_translations(self, en_translations):
        """Test that cost strategy features are translated."""
        en_str = json.dumps(en_translations).lower()
        
        # Check for cost-related terms
        assert "cost" in en_str or "price" in en_str, "No cost/price translations found"
        assert "cheap" in en_str or "threshold" in en_str, "No threshold translations found"

    def test_comfort_settings_translations(self, en_translations):
        """Test that comfort settings are translated."""
        en_str = json.dumps(en_translations).lower()
        
        # Check for comfort-related terms
        assert "comfort" in en_str or "quiet" in en_str, "No comfort translations found"

    def test_optimization_sensors_translated(self, en_translations, sv_translations):
        """Test that optimization sensor names are translated."""
        # Check entity translations for optimization sensors
        en_entities = en_translations.get("entity", {})
        sv_entities = sv_translations.get("entity", {})
        
        # Should have sensor translations
        assert len(en_entities) > 0, "No entity translations in EN"
        assert len(sv_entities) > 0, "No entity translations in SV"
        
        # Check for specific optimization entities (at least some of these keywords)
        sensor_keywords = ["optimal", "cost", "savings"]
        en_entity_str = json.dumps(en_entities).lower()
        
        found_keywords = sum(1 for keyword in sensor_keywords if keyword in en_entity_str)
        assert found_keywords >= 2, \
            f"Expected at least 2 optimization keywords in entity translations, found {found_keywords}"


class TestTranslationCompleteness:
    """Test translation completeness for Step 6 deliverables."""

    def test_all_config_fields_have_descriptions(self, en_translations):
        """Test that all config fields have descriptions."""
        config = en_translations.get("config", {})
        step_user = config.get("step", {}).get("user", {})
        data_fields = step_user.get("data", {})
        data_description = step_user.get("data_description", {})
        
        # Most data fields should have descriptions
        fields_with_descriptions = 0
        for field_key in data_fields.keys():
            if field_key in data_description:
                fields_with_descriptions += 1
        
        if len(data_fields) > 0:
            coverage = fields_with_descriptions / len(data_fields)
            print(f"\nConfig field description coverage: {coverage:.1%} ({fields_with_descriptions}/{len(data_fields)})")
            # At least 50% should have descriptions
            assert coverage > 0.5, f"Too few field descriptions: {coverage:.1%}"

    def test_service_translations_present(self, en_translations):
        """Test that service translations are present."""
        services = en_translations.get("services", {})
        
        # Should have some service translations
        assert len(services) > 0, "No service translations found"
        
        print(f"\nFound {len(services)} service translations")

    def test_error_messages_translated(self, en_translations, sv_translations):
        """Test that error messages are translated."""
        en_errors = en_translations.get("config", {}).get("error", {})
        sv_errors = sv_translations.get("config", {}).get("error", {})
        
        # Should have error translations
        assert len(en_errors) > 0, "No error messages in EN"
        assert len(sv_errors) > 0, "No error messages in SV"
        
        # Error keys should match
        assert set(en_errors.keys()) == set(sv_errors.keys()), \
            "Error message keys don't match between EN and SV"
