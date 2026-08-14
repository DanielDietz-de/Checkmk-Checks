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


if not hasattr(cmk_v2, "check_levels"):
    cmk_v2.check_levels = _compat_check_levels

from s2d_hci.agent_based import s2d_hci_fast as fast
from s2d_hci.agent_based import s2d_hci_health as health
from s2d_hci.agent_based import s2d_hci_jobs as jobs
from s2d_hci.agent_based import s2d_hci_storage as storage
from s2d_hci.agent_based import s2d_hci_virtualization as virtualization


def _row(**values: object) -> list[str]:
    """Serialize one mapping into the single-row Checkmk string-table representation consumed by package parsers."""

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


def test_checkpoint_defaults_include_complete_state_policy() -> None:
    """Verify checkpoint defaults contain every required state-policy key so Checkmk 2.5 can validate the referenced ruleset."""

    assert set(virtualization.STATE_DEFAULTS) <= set(virtualization.CHECKPOINT_DEFAULTS)
    assert virtualization.CHECKPOINT_DEFAULTS["levels_upper_age_hours"] == ("fixed", (24.0, 72.0))


def test_healthy_storage_with_ok_operational_state_is_ok() -> None:
    """Healthy plus OK must remain an OK storage state instead of becoming UNKNOWN when vendor fields are evaluated together."""

    section = storage.parse_s2d_hci_storage_pools(
        [_row(protocol_version=1, run_id="r", identity="pool-a", friendly_name="Pool A", health_status="Healthy", operational_status="OK")]
    )
    result = list(storage.check_s2d_hci_storage_pools("pool-a", storage.STATE_DEFAULTS, section))[-1]
    assert result.state == State.OK


def test_storage_health_uses_worst_independent_component_state() -> None:
    """A healthy object with degraded operational status must WARN while a genuinely unhealthy object must CRIT."""

    degraded = storage.parse_s2d_hci_storage_pools(
        [_row(protocol_version=1, run_id="r", identity="pool-a", friendly_name="Pool A", health_status="Healthy", operational_status="Degraded")]
    )
    degraded_result = list(storage.check_s2d_hci_storage_pools("pool-a", storage.STATE_DEFAULTS, degraded))[-1]
    assert degraded_result.state == State.WARN

    unhealthy = health.parse_s2d_hci_storage_subsystems(
        [_row(protocol_version=1, run_id="r", identity="sub-a", friendly_name="Subsystem A", health_status="Unhealthy", operational_status="OK")]
    )
    unhealthy_result = list(health.check_s2d_hci_storage_subsystems("sub-a", health.STATE_DEFAULTS, unhealthy))[0]
    assert unhealthy_result.state == State.CRIT


def test_virtual_disk_none_detached_reason_is_not_critical() -> None:
    """The normal Storage Spaces DetachedReason=None sentinel must not create a false CRIT service."""

    for detached_reason in ("None", "0", 0, None):
        section = storage.parse_s2d_hci_virtual_disks(
            [
                _row(
                    protocol_version=1,
                    run_id="r",
                    identity="vdisk-a",
                    friendly_name="Virtual Disk A",
                    health_status="Healthy",
                    operational_status="OK",
                    detached_reason=detached_reason,
                )
            ]
        )
        result = list(storage.check_s2d_hci_virtual_disks("vdisk-a", storage.STATE_DEFAULTS, section))[-1]
        assert result.state == State.OK


def test_virtual_disk_real_detached_reason_is_critical() -> None:
    """A real Storage Spaces detach reason must remain a CRIT condition."""

    section = storage.parse_s2d_hci_virtual_disks(
        [
            _row(
                protocol_version=1,
                run_id="r",
                identity="vdisk-a",
                friendly_name="Virtual Disk A",
                health_status="Healthy",
                operational_status="OK",
                detached_reason="Insufficient Redundancy",
            )
        ]
    )
    result = list(storage.check_s2d_hci_virtual_disks("vdisk-a", storage.STATE_DEFAULTS, section))[0]
    assert result.state == State.CRIT
    assert "insufficient redundancy" in result.summary.lower()


def test_differencing_disk_warns_without_parent_path() -> None:
    """The non-sensitive has_parent flag must preserve differencing-disk warnings when path collection remains disabled."""

    section = virtualization.parse_s2d_hci_virtualization_hard_disks(
        [_row(protocol_version=1, run_id="r", identity="SCSI0:0", name="SCSI0:0", has_parent=True, vhd_type="Differencing")]
    )
    result = list(virtualization.check_s2d_hci_virtualization_hard_disks("SCSI0:0", virtualization.STATE_DEFAULTS, section))[0]
    assert result.state == State.WARN
    assert "parent" in result.summary.lower()


def test_pass_through_disk_is_not_a_vhd_metadata_failure() -> None:
    """A valid pathless pass-through attachment must remain OK and must not require VHD metadata."""

    section = virtualization.parse_s2d_hci_virtualization_hard_disks(
        [
            _row(
                protocol_version=1,
                run_id="r",
                identity="SCSI0:1",
                name="SCSI0:1",
                attachment_type="pass_through",
                disk_number=3,
            )
        ]
    )
    result = list(virtualization.check_s2d_hci_virtualization_hard_disks("SCSI0:1", virtualization.STATE_DEFAULTS, section))[0]
    assert result.state == State.OK
    assert "metadata unavailable" not in result.summary.lower()
