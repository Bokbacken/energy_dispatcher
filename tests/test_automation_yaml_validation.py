"""Test validation of automation YAML examples."""
import pytest
import re
import yaml
from pathlib import Path


@pytest.fixture
def automation_doc_path():
    """Path to automation examples document."""
    return Path(__file__).parent.parent / "docs" / "ai_optimization_automation_examples.md"


def extract_yaml_blocks(md_file):
    """Extract YAML code blocks from markdown file."""
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all YAML code blocks (```yaml ... ```)
    pattern = r'```yaml\n(.*?)\n```'
    matches = re.findall(pattern, content, re.DOTALL)
    
    return matches


def is_automation(yaml_data):
    """Check if YAML represents a Home Assistant automation."""
    return (
        isinstance(yaml_data, dict) and
        'alias' in yaml_data and
        'action' in yaml_data
    )


class TestAutomationYAMLValidation:
    """Test automation YAML syntax and structure."""

    def test_document_exists(self, automation_doc_path):
        """Test that automation examples document exists."""
        assert automation_doc_path.exists(), f"Document not found: {automation_doc_path}"

    def test_extract_yaml_blocks(self, automation_doc_path):
        """Test that YAML blocks can be extracted from document."""
        yaml_blocks = extract_yaml_blocks(automation_doc_path)
        assert len(yaml_blocks) > 0, "No YAML blocks found in document"
        assert len(yaml_blocks) >= 12, f"Expected at least 12 automation examples, found {len(yaml_blocks)}"

    def test_all_yaml_blocks_valid_syntax(self, automation_doc_path):
        """Test that all YAML blocks have valid syntax."""
        yaml_blocks = extract_yaml_blocks(automation_doc_path)
        
        invalid_blocks = []
        for i, yaml_content in enumerate(yaml_blocks, 1):
            try:
                yaml.safe_load(yaml_content)
            except yaml.YAMLError as e:
                # Skip Jinja template examples (they contain {% %} which isn't valid YAML alone)
                if '{% set' in yaml_content or '{%' in yaml_content[:50]:
                    continue
                invalid_blocks.append((i, str(e)))
        
        assert len(invalid_blocks) == 0, f"Invalid YAML blocks: {invalid_blocks}"

    def test_automation_structure(self, automation_doc_path):
        """Test that automation examples have proper structure."""
        yaml_blocks = extract_yaml_blocks(automation_doc_path)
        
        automations = []
        for yaml_content in yaml_blocks:
            try:
                data = yaml.safe_load(yaml_content)
                if is_automation(data):
                    automations.append(data)
            except yaml.YAMLError:
                # Skip invalid YAML (helper scripts, templates, etc.)
                continue
        
        assert len(automations) >= 12, f"Expected at least 12 automations, found {len(automations)}"
        
        for automation in automations:
            # Required fields
            assert 'alias' in automation, f"Automation missing 'alias': {automation}"
            assert 'action' in automation, f"Automation missing 'action': {automation.get('alias')}"
            
            # Action should be a list
            assert isinstance(automation['action'], list), \
                f"Automation action should be a list: {automation.get('alias')}"

    def test_automation_names_are_unique(self, automation_doc_path):
        """Test that all automation names (aliases) are unique."""
        yaml_blocks = extract_yaml_blocks(automation_doc_path)
        
        automation_names = []
        for yaml_content in yaml_blocks:
            try:
                data = yaml.safe_load(yaml_content)
                if is_automation(data) and 'alias' in data:
                    automation_names.append(data['alias'])
            except yaml.YAMLError:
                continue
        
        duplicates = [name for name in automation_names if automation_names.count(name) > 1]
        assert len(duplicates) == 0, f"Duplicate automation names: {set(duplicates)}"

    def test_automations_have_descriptions(self, automation_doc_path):
        """Test that automations have description fields."""
        yaml_blocks = extract_yaml_blocks(automation_doc_path)
        
        missing_descriptions = []
        for yaml_content in yaml_blocks:
            try:
                data = yaml.safe_load(yaml_content)
                if is_automation(data):
                    if 'description' not in data:
                        missing_descriptions.append(data.get('alias', 'Unknown'))
            except yaml.YAMLError:
                continue
        
        # Descriptions are recommended but not required, so just warn
        if missing_descriptions:
            print(f"\nWarning: Automations without descriptions: {missing_descriptions}")

    def test_specific_automation_examples(self, automation_doc_path):
        """Test that specific key automations are present."""
        yaml_blocks = extract_yaml_blocks(automation_doc_path)
        
        automation_names = []
        for yaml_content in yaml_blocks:
            try:
                data = yaml.safe_load(yaml_content)
                if is_automation(data) and 'alias' in data:
                    automation_names.append(data['alias'])
            except yaml.YAMLError:
                continue
        
        # Check for key automation examples
        expected_automations = [
            'Smart Dishwasher Alert',
            'Auto-Schedule Washing Machine',
            'Smart Water Heater Control',
            'Smart EV Charging',
            'Dynamic Battery Reserve',
            'High-Value Export Alert',
        ]
        
        for expected in expected_automations:
            assert expected in automation_names, \
                f"Expected automation '{expected}' not found in document"

    def test_automation_trigger_types(self, automation_doc_path):
        """Test that automations use various trigger types."""
        yaml_blocks = extract_yaml_blocks(automation_doc_path)
        
        trigger_platforms = set()
        for yaml_content in yaml_blocks:
            try:
                data = yaml.safe_load(yaml_content)
                if is_automation(data) and 'trigger' in data:
                    for trigger in data['trigger']:
                        if isinstance(trigger, dict) and 'platform' in trigger:
                            trigger_platforms.add(trigger['platform'])
            except yaml.YAMLError:
                continue
        
        # Verify diverse trigger types are used
        assert 'template' in trigger_platforms, "No template triggers found"
        assert 'time' in trigger_platforms or 'time_pattern' in trigger_platforms, \
            "No time-based triggers found"

    def test_automation_uses_energy_dispatcher_entities(self, automation_doc_path):
        """Test that automations reference Energy Dispatcher entities."""
        yaml_blocks = extract_yaml_blocks(automation_doc_path)
        
        entity_references = []
        for yaml_content in yaml_blocks:
            # Look for energy_dispatcher entity references
            if 'energy_dispatcher' in yaml_content:
                entity_references.append(yaml_content)
        
        assert len(entity_references) >= 10, \
            f"Expected at least 10 blocks referencing energy_dispatcher entities, found {len(entity_references)}"

    def test_automations_have_mode_set(self, automation_doc_path):
        """Test that automations have mode configured."""
        yaml_blocks = extract_yaml_blocks(automation_doc_path)
        
        automations_without_mode = []
        for yaml_content in yaml_blocks:
            try:
                data = yaml.safe_load(yaml_content)
                if is_automation(data):
                    if 'mode' not in data:
                        automations_without_mode.append(data.get('alias', 'Unknown'))
            except yaml.YAMLError:
                continue
        
        # Mode is recommended for clarity
        if automations_without_mode:
            print(f"\nWarning: Automations without mode: {automations_without_mode}")


class TestAutomationCoverage:
    """Test that automation examples cover all major features."""

    def test_appliance_scheduling_automations(self, automation_doc_path):
        """Test that appliance scheduling automations are present."""
        content = automation_doc_path.read_text()
        
        # Check for appliance-related automations
        assert 'dishwasher' in content.lower(), "No dishwasher automation found"
        assert 'washing_machine' in content.lower() or 'washing machine' in content.lower(), \
            "No washing machine automation found"
        assert 'water_heater' in content.lower() or 'water heater' in content.lower(), \
            "No water heater automation found"

    def test_ev_charging_automations(self, automation_doc_path):
        """Test that EV charging automations are present."""
        content = automation_doc_path.read_text()
        
        assert 'ev' in content.lower() or 'electric vehicle' in content.lower(), \
            "No EV charging automation found"

    def test_battery_management_automations(self, automation_doc_path):
        """Test that battery management automations are present."""
        content = automation_doc_path.read_text()
        
        assert 'battery' in content.lower(), "No battery automation found"
        assert 'battery_reserve' in content.lower() or 'battery reserve' in content.lower(), \
            "No battery reserve automation found"

    def test_export_management_automations(self, automation_doc_path):
        """Test that export management automations are present."""
        content = automation_doc_path.read_text()
        
        assert 'export' in content.lower(), "No export automation found"

    def test_notification_automations(self, automation_doc_path):
        """Test that notification automations are present."""
        content = automation_doc_path.read_text()
        
        assert 'notify' in content.lower(), "No notification automation found"
        assert 'notification' in content.lower() or 'alert' in content.lower(), \
            "No alert/notification patterns found"

    def test_cost_tracking_automations(self, automation_doc_path):
        """Test that cost tracking automations are present."""
        content = automation_doc_path.read_text()
        
        assert 'savings' in content.lower() or 'cost' in content.lower(), \
            "No cost tracking automation found"
        assert 'report' in content.lower() or 'summary' in content.lower(), \
            "No reporting automation found"
