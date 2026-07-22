from pathlib import Path

AFFECTED_SERVER_SIDE_CALLS = (
    Path("agent_json/src/agent_json/server_side_calls/agent_json.py"),
    Path("pure/src/pure/server_side_calls/pure.py"),
    Path("unisphere_powermax/src/unisphere_powermax/server_side_calls/unisphere_powermax.py"),
    Path("dell_pmax/src/dell_pmax/server_side_calls/agent_pmax.py"),
    Path("cmdb_syncer/src/cmdb_syncer/server_side_calls/cmdb_syncer.py"),
    Path("spring_boot_actuator/src/spring_boot_actuator/server_side_calls/spring_boot_actuator.py"),
    Path("hitachi_hnas_rest/src/hitachi_hnas_rest/server_side_calls/agent.py"),
)


def test_server_side_calls_do_not_flatten_secrets():
    repository_root = Path(__file__).parents[2]
    for relative_path in AFFECTED_SERVER_SIDE_CALLS:
        source = (repository_root / relative_path).read_text(encoding="utf-8")
        assert ".unsafe(" not in source, f"Secret flattened in {relative_path}"
        assert "Secret" in source, f"Secret type missing from {relative_path}"
        assert "command_arguments" in source
