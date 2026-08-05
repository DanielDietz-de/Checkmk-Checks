"""Repository-wide credential-boundary regression tests."""

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).parents[2]


def test_server_side_calls_never_flatten_checkmk_secrets() -> None:
    """Credential-bearing command builders must leave substitution to Checkmk."""
    offenders = []
    for path in sorted(REPOSITORY_ROOT.glob("*/src/*/server_side_calls/*.py")):
        source = path.read_text(encoding="utf-8")
        if ".unsafe(" in source:
            offenders.append(path.relative_to(REPOSITORY_ROOT).as_posix())
    assert offenders == []


def test_safe_secret_references_are_resolved_inside_agents() -> None:
    """Agents receiving safe references must resolve the password store themselves."""
    unresolved = []
    for package in sorted(path.parent.parent for path in REPOSITORY_ROOT.glob("*/src/info")):
        server_files = sorted((package / "src").glob("*/server_side_calls/*.py"))
        if not server_files:
            continue
        server_text = "\n".join(path.read_text(encoding="utf-8") for path in server_files)
        if server_text.count("Secret") < 2 or ".unsafe(" in server_text:
            continue
        agents = sorted((package / "src").glob("*/libexec/agent_*"))
        if not agents:
            continue
        agent_text = "\n".join(path.read_text(encoding="utf-8") for path in agents)
        resolves = "password_store" in agent_text and any(
            token in agent_text for token in ("lookup", "resolve_secret", "dereference_secret")
        )
        if not resolves:
            unresolved.append(package.name)
    assert unresolved == []
