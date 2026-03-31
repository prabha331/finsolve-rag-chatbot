"""
Unit tests for the RBAC service.

Pure logic tests — no HTTP client or database needed.
"""

import pytest

from app.services.rbac_service import (
    ROLE_PERMISSIONS,
    get_allowed_sources,
    is_role_valid,
)


# ---------------------------------------------------------------------------
# get_allowed_sources
# ---------------------------------------------------------------------------


class TestGetAllowedSources:
    """Tests for role-to-collection mapping."""

    def test_employee_can_only_access_handbook(self) -> None:
        assert get_allowed_sources("employee") == ["employee_handbook"]

    def test_hr_can_access_handbook_and_hr(self) -> None:
        result = get_allowed_sources("hr")
        assert "employee_handbook" in result
        assert "hr" in result
        assert len(result) == 2

    def test_finance_can_access_handbook_and_finance(self) -> None:
        result = get_allowed_sources("finance")
        assert "employee_handbook" in result
        assert "finance" in result
        assert len(result) == 2

    def test_marketing_can_access_handbook_and_marketing(self) -> None:
        result = get_allowed_sources("marketing")
        assert "employee_handbook" in result
        assert "marketing" in result
        assert len(result) == 2

    def test_engineering_can_access_handbook_and_engineering(self) -> None:
        result = get_allowed_sources("engineering")
        assert "employee_handbook" in result
        assert "engineering" in result
        assert len(result) == 2

    def test_c_level_can_access_all_five_departments(self) -> None:
        result = get_allowed_sources("c_level")
        expected = {"employee_handbook", "hr", "finance", "marketing", "engineering"}
        assert set(result) == expected
        assert len(result) == 5

    def test_unknown_role_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unknown role"):
            get_allowed_sources("admin")

    def test_empty_string_role_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            get_allowed_sources("")

    def test_case_sensitive_role_matching(self) -> None:
        """Role names are lowercase; mixed-case variants must be rejected."""
        with pytest.raises(ValueError):
            get_allowed_sources("Finance")

    def test_returns_list_not_set(self) -> None:
        """Return type must be a list (order is preserved for prompt building)."""
        result = get_allowed_sources("finance")
        assert isinstance(result, list)

    def test_every_role_includes_employee_handbook(self) -> None:
        """All roles must be able to access the employee handbook."""
        for role in ROLE_PERMISSIONS:
            sources = get_allowed_sources(role)
            assert "employee_handbook" in sources, (
                f"Role '{role}' is missing 'employee_handbook' access"
            )


# ---------------------------------------------------------------------------
# is_role_valid
# ---------------------------------------------------------------------------


class TestIsRoleValid:
    """Tests for the role existence check."""

    @pytest.mark.parametrize("role", ["employee", "hr", "finance", "marketing", "engineering", "c_level"])
    def test_known_roles_return_true(self, role: str) -> None:
        assert is_role_valid(role) is True

    @pytest.mark.parametrize("role", ["admin", "superuser", "guest", "", "FINANCE", "C_Level"])
    def test_unknown_or_malformed_roles_return_false(self, role: str) -> None:
        assert is_role_valid(role) is False

    def test_return_type_is_bool(self) -> None:
        assert isinstance(is_role_valid("finance"), bool)
        assert isinstance(is_role_valid("unknown"), bool)


# ---------------------------------------------------------------------------
# ROLE_PERMISSIONS structure
# ---------------------------------------------------------------------------


class TestRolePermissionsStructure:
    """Sanity checks on the ROLE_PERMISSIONS constant itself."""

    def test_all_expected_roles_are_present(self) -> None:
        expected_roles = {"employee", "hr", "finance", "marketing", "engineering", "c_level"}
        assert set(ROLE_PERMISSIONS.keys()) == expected_roles

    def test_all_values_are_non_empty_lists(self) -> None:
        for role, sources in ROLE_PERMISSIONS.items():
            assert isinstance(sources, list), f"Role '{role}' sources is not a list"
            assert len(sources) > 0, f"Role '{role}' has no allowed sources"

    def test_c_level_has_most_access(self) -> None:
        """c_level must have strictly more access than every other role."""
        c_level_sources = set(get_allowed_sources("c_level"))
        for role in ROLE_PERMISSIONS:
            if role == "c_level":
                continue
            assert set(get_allowed_sources(role)).issubset(c_level_sources), (
                f"Role '{role}' has access to sources not in c_level"
            )
