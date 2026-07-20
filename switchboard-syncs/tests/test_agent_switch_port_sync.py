from __future__ import annotations

import importlib.machinery
import importlib.util
import sys
from pathlib import Path

import pytest

AGENT = (
    Path(__file__).parents[1]
    / "src/switch_port_sync/libexec/agent_switch_port_sync"
)
loader = importlib.machinery.SourceFileLoader("agent_switch_port_sync", str(AGENT))
spec = importlib.util.spec_from_loader(loader.name, loader)
assert spec is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
loader.exec_module(module)


def service(
    *,
    description: str = "Interface 01",
    output: str,
    state: int = 0,
    stale: bool = False,
    host_state: int = 0,
):
    return module.InterfaceService(
        description=description,
        core_state=state,
        plugin_output=output,
        long_plugin_output="",
        has_been_checked=True,
        stale=stale,
        last_check=1,
        host_state=host_state,
    )


def test_operational_up_is_up() -> None:
    assert module.interface_state(service(output="Operational state: up"))[0] == "up"


def test_operational_down_is_down() -> None:
    assert (
        module.interface_state(service(output="Operational state: down", state=2))[0]
        == "down"
    )


def test_non_link_critical_is_not_assumed_down() -> None:
    assert module.interface_state(service(output="Input errors: 5", state=2))[0] == "unknown"


def test_stale_and_host_down_are_unresolved() -> None:
    assert module.interface_state(service(output="Operational state: up", stale=True))[0] == "stale"
    assert module.interface_state(service(output="Operational state: up", host_state=1))[0] == "unknown"


def test_union_produces_missing_peer_record() -> None:
    payload = module.build_payload(
        pair_name="pair",
        host_a="a",
        host_b="b",
        service_regex_text=r"^Interface (?P<item>.+)$",
        services_a=[service(output="Operational state: up")],
        services_b=[],
    )
    assert payload["records"][0]["host_a"]["state"] == "up"
    assert payload["records"][0]["host_b"]["state"] == "missing"


def test_duplicate_mapping_is_rejected() -> None:
    with pytest.raises(ValueError, match="Multiple interface services"):
        module.build_payload(
            pair_name="pair",
            host_a="a",
            host_b="b",
            service_regex_text=r"^Interface (?P<item>.+)$",
            services_a=[
                service(description="Interface 01", output="Operational state: up"),
                service(description="Interface 01", output="Operational state: up"),
            ],
            services_b=[],
        )


def test_same_host_pair_is_rejected() -> None:
    with pytest.raises(ValueError, match="must be different"):
        module.build_payload(
            pair_name="pair",
            host_a="a",
            host_b="a",
            service_regex_text=r"^Interface (?P<item>.+)$",
            services_a=[],
            services_b=[],
        )


def test_regex_requires_capture_group() -> None:
    with pytest.raises(ValueError, match="capture group"):
        module.build_payload(
            pair_name="pair",
            host_a="a",
            host_b="b",
            service_regex_text=r"^Interface .+$",
            services_a=[],
            services_b=[],
        )
