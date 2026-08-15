from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[2]
_VALIDATOR_PATH = REPOSITORY / ".github/scripts/validate_repository_mkps.py"


def _load_validator():
    """Handle load validator for this module's workflow."""
    name = "validate_repository_mkps_for_tests"
    spec = importlib.util.spec_from_file_location(name, _VALIDATOR_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _known_warning_output() -> str:
    """Handle known warning output for this module's workflow."""
    return """Agent based plugins loading succeeded, Active checks loading succeeded, Special agents loading succeeded, Rule specs loading succeeded, Rule specs forms creation succeeded, Referenced rule specs validation succeeded, Loaded rule specs usage failed(!!)
CheckParameters rule set 'alertmanager_rule_state' is not used anywhere. Ensure the correct spelling at the referencing plug-in or deprecate the ruleset
CheckParameters rule set 'alertmanager_rule_state_summary' is not used anywhere. Ensure the correct spelling at the referencing plug-in or deprecate the ruleset(!!)
"""


def test_accepts_only_exact_pinned_checkmk_builtin_warning() -> None:
    """Verify that accepts only exact pinned checkmk builtin warning."""
    validator = _load_validator()
    result = validator.CommandResult(returncode=2, output=_known_warning_output())

    assert validator._is_known_checkmk_builtin_ruleset_warning(result, "2.4.0p34")
    assert validator._is_known_checkmk_builtin_ruleset_warning(result, "2.5.0p9")


def test_rejects_known_warning_on_other_checkmk_versions() -> None:
    """Verify that rejects known warning on other checkmk versions."""
    validator = _load_validator()
    result = validator.CommandResult(returncode=2, output=_known_warning_output())

    assert not validator._is_known_checkmk_builtin_ruleset_warning(result, "2.4.0p35")
    assert not validator._is_known_checkmk_builtin_ruleset_warning(result, "2.5.0p10")


def test_rejects_extra_or_changed_validation_failures() -> None:
    """Verify that rejects extra or changed validation failures."""
    validator = _load_validator()
    changed = _known_warning_output() + (
        "CheckParameters rule set 'repository_rule' is not used anywhere. "
        "Ensure the correct spelling at the referencing plug-in or deprecate the ruleset\n"
    )

    assert not validator._is_known_checkmk_builtin_ruleset_warning(
        validator.CommandResult(returncode=2, output=changed),
        "2.5.0p9",
    )
    assert not validator._is_known_checkmk_builtin_ruleset_warning(
        validator.CommandResult(returncode=1, output=_known_warning_output()),
        "2.5.0p9",
    )


def test_compatibility_window_is_inclusive() -> None:
    """Verify that compatibility window is inclusive."""
    validator = _load_validator()

    assert validator._supports_target("2.0.0", "2.2.99", "2.0.0")
    assert validator._supports_target("2.0.0", "2.2.99", "2.2.99")
    assert validator._supports_target("2.0.0", "2.2.99", "2.1.0p20")
    assert not validator._supports_target("2.0.0", "2.2.99", "1.6.0p30")
    assert not validator._supports_target("2.0.0", "2.2.99", "2.3.0")
