"""Focused behavior tests for storage, quorum, job, and virtualization checks."""

from __future__ import annotations

import json

import cmk.agent_based.v2 as cmk_v2
from cmk.agent_based.v2 import Metric, Result, State


def _compat_check_levels(value, levels_upper=None, levels_lower=None, metric_name=None, label=None, boundaries=None, render_func=None):
    """Provide the fixed-level helper when another package installed a smaller Checkmk test stub."""

    del boundaries, render_func
    if metric_name:
        yield Metric(metric_name, value)
    if levels_upper and levels_upper[0] == "fixed":
        warn, crit = levels_upper[1]
        state = State.CRIT if value >= crit else State.WARN if value >= warn else State.OK
        yield Result(state, f"{label}: {value}")
    elif levels_lower and levels_lower[0] == "fixed":
        warn, crit = levels_lower[1]
        state = State.CRIT if value <= crit else State.WARN if value <= warn else State.OK
        yield Result(state, f"{label}: {value}")


# Full-repository collection loads many package-local conftest stubs into the
# same interpreter. Guarantee the one API helper needed by the S2D modules is
# present immediately before importing those production modules.
if not hasattr(cmk_v2, "check_levels"):
    cmk_v2.check_levels = _compat_check_levels

from s2d_hci.agent_based import s2d_hci_fast as fast
from s2d_hci.agent_based import s2d_hci_jobs as jobs
from s2d_hci.agent_based import s2d_hci_storage as storage


def _row(**values: object) -> list[str]:
    """Return one JSON string-table row."""

    return [json.dumps(values)]


def test_structured_quorum_failure_is_unknown() -> None:
    """A failed Get-ClusterQuorum call must never become a healthy quorum service."""

    section = fast.parse_s2d_hci_quorum(
        [_row(protocol_version=1, run_id="r", section="s2d_hci_quorum", success=False, error="access denied")]
    )
    item = next(iter(section))
    result = list(fast.check_s2d_hci_quorum(item, fast.STATE_DEFAULTS, section))[0]
    assert result.state == State.UNKNOWN
    assert "access denied" in result.summary


def test_duplicate_volume_labels_do_not_overwrite() -> None:
    """Distinct stable volume identities must survive identical display labels."""

    section = storage.parse_s2d_hci_volumes(
        [
            _row(protocol_version=1, run_id="r", identity="Data [D:]", filesystem_label="Data", health_status="Healthy"),
            _row(protocol_version=1, run_id="r", identity="Data [E:]", filesystem_label="Data", health_status="Healthy"),
        ]
    )
    assert set(section) == {"Data [D:]", "Data [E:]"}


def test_non_finite_storage_job_progress_emits_no_metric() -> None:
    """A non-finite percentage must not poison Checkmk metric processing."""

    section = jobs.parse_s2d_hci_storage_jobs(
        [_row(protocol_version=1, run_id="r", identity="job-a", name="Repair", job_state="Running", percent_complete="nan")]
    )
    output = list(jobs.check_s2d_hci_storage_jobs("job-a", jobs.STATE_DEFAULTS, section))
    assert not any(isinstance(value, Metric) for value in output)
