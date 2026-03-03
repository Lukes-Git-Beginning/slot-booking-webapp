# -*- coding: utf-8 -*-
"""
Finanzberatung Checklist Config Tests
Tests for app/config/finanz_checklist.py
"""

import pytest


class TestContractTypes:
    """Test CONTRACT_TYPES definitions."""

    def test_contract_types_count(self):
        """Test that all ~40 contract types are defined."""
        from app.config.finanz_checklist import CONTRACT_TYPES
        assert len(CONTRACT_TYPES) >= 37  # minimum expected

    def test_all_types_have_required_keys(self):
        """Test that every contract type has label, icon, category, fields."""
        from app.config.finanz_checklist import CONTRACT_TYPES

        for type_key, ct in CONTRACT_TYPES.items():
            assert 'label' in ct, f"{type_key} missing 'label'"
            assert 'icon' in ct, f"{type_key} missing 'icon'"
            assert 'category' in ct, f"{type_key} missing 'category'"
            assert 'fields' in ct, f"{type_key} missing 'fields'"
            assert len(ct['fields']) > 0, f"{type_key} has empty fields"

    def test_all_fields_have_structure(self):
        """Test that every field has name, label, priority, type."""
        from app.config.finanz_checklist import CONTRACT_TYPES

        for type_key, ct in CONTRACT_TYPES.items():
            for field in ct['fields']:
                assert 'name' in field, f"{type_key}: field missing 'name'"
                assert 'label' in field, f"{type_key}: field missing 'label'"
                assert 'priority' in field, f"{type_key}: field missing 'priority'"
                assert 'type' in field, f"{type_key}: field missing 'type'"

    def test_all_priorities_valid(self):
        """Test that all field priorities are muss/soll/kann."""
        from app.config.finanz_checklist import (
            CONTRACT_TYPES, PRIORITY_MUSS, PRIORITY_SOLL, PRIORITY_KANN,
        )

        valid = {PRIORITY_MUSS, PRIORITY_SOLL, PRIORITY_KANN}
        for type_key, ct in CONTRACT_TYPES.items():
            for field in ct['fields']:
                assert field['priority'] in valid, (
                    f"{type_key}.{field['name']}: invalid priority '{field['priority']}'"
                )

    def test_all_field_types_valid(self):
        """Test that all field types are recognized."""
        from app.config.finanz_checklist import (
            CONTRACT_TYPES,
            FIELD_TYPE_TEXT, FIELD_TYPE_CURRENCY, FIELD_TYPE_NUMBER,
            FIELD_TYPE_DATE, FIELD_TYPE_PERCENT, FIELD_TYPE_BOOLEAN,
        )

        valid = {
            FIELD_TYPE_TEXT, FIELD_TYPE_CURRENCY, FIELD_TYPE_NUMBER,
            FIELD_TYPE_DATE, FIELD_TYPE_PERCENT, FIELD_TYPE_BOOLEAN,
        }
        for type_key, ct in CONTRACT_TYPES.items():
            for field in ct['fields']:
                assert field['type'] in valid, (
                    f"{type_key}.{field['name']}: invalid type '{field['type']}'"
                )

    def test_every_type_has_gesellschaft(self):
        """Test that most contract types include 'gesellschaft' as a field."""
        from app.config.finanz_checklist import CONTRACT_TYPES

        # Legacy/Unterlagen types don't have gesellschaft (not insurance contracts)
        skip_types = {
            'renteninfo', 'steuerbescheid', 'gehaltsabrechnung',
            'kontoauszug', 'depot', 'sonstige',
        }
        for type_key, ct in CONTRACT_TYPES.items():
            if type_key in skip_types:
                continue
            field_names = [f['name'] for f in ct['fields']]
            assert 'gesellschaft' in field_names, (
                f"{type_key} missing 'gesellschaft' field"
            )


class TestChecklistCategories:
    """Test CHECKLIST_CATEGORIES groupings."""

    def test_all_categories_exist(self):
        """Test expected categories are defined."""
        from app.config.finanz_checklist import CHECKLIST_CATEGORIES

        expected = {
            'sachversicherung', 'kfz', 'altersvorsorge',
            'absicherung', 'gesundheit', 'sonstiges', 'unterlagen',
        }
        assert set(CHECKLIST_CATEGORIES.keys()) == expected

    def test_categories_have_structure(self):
        """Test that categories have label, icon, types."""
        from app.config.finanz_checklist import CHECKLIST_CATEGORIES

        for cat_key, cat in CHECKLIST_CATEGORIES.items():
            assert 'label' in cat, f"{cat_key} missing 'label'"
            assert 'icon' in cat, f"{cat_key} missing 'icon'"
            assert 'types' in cat, f"{cat_key} missing 'types'"
            assert len(cat['types']) > 0, f"{cat_key} has no types"

    def test_all_category_types_exist_in_contract_types(self):
        """Test that every type referenced in categories exists in CONTRACT_TYPES."""
        from app.config.finanz_checklist import CHECKLIST_CATEGORIES, CONTRACT_TYPES

        for cat_key, cat in CHECKLIST_CATEGORIES.items():
            for type_key in cat['types']:
                assert type_key in CONTRACT_TYPES, (
                    f"Category {cat_key} references unknown type '{type_key}'"
                )

    def test_contract_type_categories_match(self):
        """Test that a contract type's 'category' field matches its category group."""
        from app.config.finanz_checklist import CHECKLIST_CATEGORIES, CONTRACT_TYPES

        for cat_key, cat in CHECKLIST_CATEGORIES.items():
            for type_key in cat['types']:
                ct = CONTRACT_TYPES[type_key]
                assert ct['category'] == cat_key, (
                    f"Type '{type_key}' has category '{ct['category']}' "
                    f"but is listed under '{cat_key}'"
                )


class TestComputeCompleteness:
    """Test completeness calculation."""

    def test_empty_data_returns_zero_muss(self):
        """Test completeness with no extracted data."""
        from app.config.finanz_checklist import compute_completeness

        result = compute_completeness('bu', {})
        assert result['muss_filled'] == 0
        assert result['muss_total'] > 0
        assert result['percent_muss'] == 0

    def test_full_data_returns_100(self):
        """Test completeness with all fields filled."""
        from app.config.finanz_checklist import (
            compute_completeness, get_fields_for_type,
        )

        fields = get_fields_for_type('privathaftpflicht')
        extracted = {f['name']: {'value': 'test'} for f in fields}

        result = compute_completeness('privathaftpflicht', extracted)
        assert result['percent_muss'] == 100
        assert result['percent_total'] == 100

    def test_partial_data(self):
        """Test completeness with partial data."""
        from app.config.finanz_checklist import compute_completeness

        extracted = {
            'gesellschaft': {'value': 'Allianz'},
            'beitrag': {'value': '50.00'},
        }

        result = compute_completeness('privathaftpflicht', extracted)
        assert result['muss_filled'] == 2
        assert 0 < result['percent_total'] < 100

    def test_unknown_type_returns_100(self):
        """Test completeness for unknown type returns 100%."""
        from app.config.finanz_checklist import compute_completeness

        result = compute_completeness('nonexistent_type', {})
        assert result['percent_muss'] == 100
        assert result['percent_total'] == 100


class TestGetFieldStatus:
    """Test field Ampel-Status logic."""

    def test_missing_muss_field_red(self):
        """Test that missing MUSS field returns red."""
        from app.config.finanz_checklist import get_field_status, PRIORITY_MUSS

        field = {'name': 'gesellschaft', 'priority': PRIORITY_MUSS, 'type': 'text'}
        assert get_field_status(field, None) == 'red'

    def test_missing_soll_field_yellow(self):
        """Test that missing SOLL field returns yellow."""
        from app.config.finanz_checklist import get_field_status, PRIORITY_SOLL

        field = {'name': 'tarifname', 'priority': PRIORITY_SOLL, 'type': 'text'}
        assert get_field_status(field, None) == 'yellow'

    def test_missing_kann_field_gray(self):
        """Test that missing KANN field returns gray."""
        from app.config.finanz_checklist import get_field_status, PRIORITY_KANN

        field = {'name': 'dynamik', 'priority': PRIORITY_KANN, 'type': 'text'}
        assert get_field_status(field, None) == 'gray'

    def test_high_confidence_green(self):
        """Test that high-confidence value returns green."""
        from app.config.finanz_checklist import get_field_status, PRIORITY_MUSS

        field = {'name': 'gesellschaft', 'priority': PRIORITY_MUSS, 'type': 'text'}
        data = {'value': 'Allianz', 'confidence': 0.95}
        assert get_field_status(field, data) == 'green'

    def test_low_confidence_yellow(self):
        """Test that low-confidence value returns yellow."""
        from app.config.finanz_checklist import get_field_status, PRIORITY_MUSS

        field = {'name': 'gesellschaft', 'priority': PRIORITY_MUSS, 'type': 'text'}
        data = {'value': 'Allianz?', 'confidence': 0.5}
        assert get_field_status(field, data) == 'yellow'

    def test_empty_value_muss_red(self):
        """Test that empty value for MUSS returns red."""
        from app.config.finanz_checklist import get_field_status, PRIORITY_MUSS

        field = {'name': 'gesellschaft', 'priority': PRIORITY_MUSS, 'type': 'text'}
        data = {'value': '', 'confidence': 0.9}
        assert get_field_status(field, data) == 'red'


class TestHelperFunctions:
    """Test helper functions."""

    def test_get_all_type_keys(self):
        """Test that all type keys are returned."""
        from app.config.finanz_checklist import get_all_type_keys, CONTRACT_TYPES

        keys = get_all_type_keys()
        assert len(keys) == len(CONTRACT_TYPES)
        assert 'bu' in keys
        assert 'privathaftpflicht' in keys

    def test_get_fields_for_type(self):
        """Test getting fields for a known type."""
        from app.config.finanz_checklist import get_fields_for_type

        fields = get_fields_for_type('bu')
        assert len(fields) > 0
        field_names = [f['name'] for f in fields]
        assert 'gesellschaft' in field_names
        assert 'rentenhoehe' in field_names

    def test_get_fields_for_unknown_type(self):
        """Test getting fields for unknown type returns empty list."""
        from app.config.finanz_checklist import get_fields_for_type

        assert get_fields_for_type('nonexistent') == []

    def test_get_muss_fields(self):
        """Test getting only MUSS fields."""
        from app.config.finanz_checklist import get_muss_fields, PRIORITY_MUSS

        muss = get_muss_fields('bu')
        assert len(muss) > 0
        for field in muss:
            assert field['priority'] == PRIORITY_MUSS

    def test_get_category_for_type(self):
        """Test getting category for a type."""
        from app.config.finanz_checklist import get_category_for_type

        assert get_category_for_type('bu') == 'absicherung'
        assert get_category_for_type('riester') == 'altersvorsorge'
        assert get_category_for_type('nonexistent') is None

    def test_get_types_by_category(self):
        """Test getting types for a category."""
        from app.config.finanz_checklist import get_types_by_category

        types = get_types_by_category('kfz')
        assert 'kfz_auto' in types
        assert 'kfz_motorrad' in types
        assert get_types_by_category('nonexistent') == []
