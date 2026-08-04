#!/usr/bin/env python3
"""Generate code-derived operational reference sections for active MKP packages."""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import Any

START = "<!-- code-derived-reference:start -->"
END = "<!-- code-derived-reference:end -->"
SECTION_RE = re.compile(r"<<<([A-Za-z0-9_.-]+)(?::[^>]*)?>>>")
SPECIAL_AGENT_RE = re.compile(r"SpecialAgentConfig\(\s*name\s*=\s*[\"']([^\"']+)", re.S)
CHECK_NAME_RES = (
    re.compile(r"CheckPlugin\(\s*name\s*=\s*[\"']([^\"']+)", re.S),
    re.compile(r"register\.check_plugin\([^)]*?name\s*=\s*[\"']([^\"']+)", re.S),
)
NETWORK_CLIENT_RES = (
    re.compile(
        r"\b(?:requests|urllib(?:\.request)?|httpx|aiohttp|httplib2|"
        r"ServerProxy|pyodbc|socket|ftplib|smtplib)\b",
        re.I,
    ),
    re.compile(
        r"\b(?:curl_(?:init|exec|setopt|setopt_array|multi_init)|"
        r"file_get_contents\s*\(|fsockopen\s*\(|stream_socket_client\s*\(|"
        r"wp_remote_(?:get|post|request|head)\b|"
        r"fopen\s*\(\s*[\"']https?://)",
        re.I,
    ),
    re.compile(
        r"(?m)(?:^|[;&|]\s*|\$\()\s*(?:curl|wget|ssh|scp|sftp|ftp|nc|netcat|"
        r"snmpget|snmpwalk|openssl\s+s_client)\b",
        re.I,
    ),
    re.compile(
        r"\b(?:Invoke-WebRequest|Invoke-RestMethod|System\.Net\.WebClient|"
        r"System\.Net\.Http\.HttpClient|Test-NetConnection|New-PSSession)\b",
        re.I,
    ),
    re.compile(
        r"\b(?:Net::HTTP|HTTP::Tiny|LWP::UserAgent|Faraday|RestClient|"
        r"java\.net\.http|HttpURLConnection|OkHttpClient)\b",
        re.I,
    ),
)


def manifest(path: Path) -> dict[str, Any]:
    value = ast.literal_eval(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected dictionary")
    return value


def source_texts(package: Path) -> list[tuple[Path, str]]:
    result: list[tuple[Path, str]] = []
    for path in sorted((package / "src").rglob("*")):
        if not path.is_file() or path.name in {"info", "info.json"} or "__pycache__" in path.parts:
            continue
        try:
            result.append((path, path.read_text(encoding="utf-8")))
        except (OSError, UnicodeError):
            continue
    return result


def detects_network_access(files: list[tuple[Path, str]]) -> bool:
    """Conservatively detect network clients across supported source languages."""
    return any(regex.search(text) for _, text in files for regex in NETWORK_CLIENT_RES)


def component_lines(package: Path, files: list[tuple[Path, str]]) -> list[str]:
    buckets: dict[str, list[str]] = {
        "Agent-based checks": [],
        "Server-side calls": [],
        "Rulesets": [],
        "Executables": [],
        "Graphing": [],
        "Bakery": [],
        "Notifications": [],
        "Check manuals": [],
        "Other packaged source": [],
    }
    mapping = {
        "agent_based": "Agent-based checks",
        "server_side_calls": "Server-side calls",
        "rulesets": "Rulesets",
        "libexec": "Executables",
        "graphing": "Graphing",
        "bakery": "Bakery",
        "notifications": "Notifications",
        "checkman": "Check manuals",
    }
    for path, _ in files:
        rel = path.relative_to(package).as_posix()
        category = next((label for part, label in mapping.items() if part in path.parts), "Other packaged source")
        buckets[category].append(f"`{rel}`")
    lines = []
    for label, paths in buckets.items():
        if paths:
            preview = ", ".join(paths[:8])
            suffix = f" and {len(paths) - 8} more" if len(paths) > 8 else ""
            lines.append(f"- **{label}:** {preview}{suffix}.")
    return lines


def derive_reference(root: Path, package: Path, data: dict[str, Any]) -> str:
    files = source_texts(package)
    joined = "\n".join(text for _, text in files)
    sections = sorted(set(SECTION_RE.findall(joined)))
    agents = sorted(set(SPECIAL_AGENT_RE.findall(joined)))
    checks: set[str] = set()
    for regex in CHECK_NAME_RES:
        checks.update(regex.findall(joined))
    tests = sorted(path.relative_to(package).as_posix() for path in (package / "tests").rglob("test*.py")) if (package / "tests").is_dir() else []
    artifacts = sorted(path.name for path in package.glob("*.mkp"))
    checksums = sorted(path.name for path in package.glob("*.mkp.sha256"))
    handles_credentials = bool(re.search(r"\b(?:Password|Secret)\s*[\[(]", joined)) or "password_store" in joined
    has_server_side_calls = any("server_side_calls" in path.parts for path, _ in files)
    has_notifications = any("notifications" in path.parts for path, _ in files)
    resolves_password_store = "password_store" in joined and bool(
        re.search(r"\b(?:lookup|resolve_secret|dereference_secret)\b", joined)
    )
    notification_context_secret = "get_password_from_env_or_context" in joined
    network_access = detects_network_access(files)
    tls_optout = bool(re.search(r"no[-_]cert[-_]check|no[-_]verify|verify_ssl\s*=|verify\s*=\s*False", joined, re.I))
    local_automation = "automation.secret" in joined
    version = data.get("version")
    min_version = data.get("version.min_required")
    until = data.get("version.usable_until")
    until_text = str(until) if until is not None else "not asserted; validate on the target release"

    lines = [
        START,
        "## Code-derived operational reference",
        "",
        "This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.",
        "",
        "### Installation",
        "",
        f"- Canonical package: `{data.get('name')}` version `{version}`; minimum Checkmk version `{min_version}`; maximum asserted version: {until_text}.",
        f"- Canonical manifest: `{package.name}/src/info`; it declares {sum(len(v) for v in data.get('files', {}).values() if isinstance(v, list))} packaged files.",
    ]
    if artifacts:
        lines.append(f"- Repository MKP artifacts present: {', '.join(f'`{item}`' for item in artifacts[:6])}{' (additional historical artifacts omitted)' if len(artifacts) > 6 else ''}.")
    else:
        lines.append("- No committed MKP artifact is present; build and validate the package from `src/` before installation.")
    if checksums:
        lines.append(f"- Checksum files present: {', '.join(f'`{item}`' for item in checksums[:6])}{' (additional files omitted)' if len(checksums) > 6 else ''}.")
    else:
        lines.append("- No committed checksum file is present; do not distribute an unverified locally built artifact.")
    lines += [
        "- Source under `src/` is authoritative; generated MKP files and this reference must match it.",
        "",
        "### Configuration and components",
        "",
        *component_lines(package, files),
    ]
    if agents:
        lines.append(f"- Registered special-agent names: {', '.join(f'`{item}`' for item in agents)}.")
    if checks:
        lines.append(f"- Registered check plug-in names: {', '.join(f'`{item}`' for item in sorted(checks))}.")
    if not agents and not checks:
        lines.append("- No special-agent or agent-based check registration was detected; use the component paths above to identify the package entry point.")
    lines += ["", "### Validation", ""]
    if tests:
        lines.append(f"- Package-specific tests: {', '.join(f'`{item}`' for item in tests[:12])}{' and additional tests' if len(tests) > 12 else ''}.")
    else:
        lines.append("- No package-specific Python test file is present. Assurance is therefore limited to repository-wide syntax, manifest, packaging, security, and Checkmk registration gates until focused fixtures are added.")
    lines.append("- Any behavior change must update or add focused tests before the generated documentation is refreshed.")
    lines += ["", "### Security", ""]
    if handles_credentials and has_server_side_calls:
        if resolves_password_store:
            lines.append("- Server-side calls preserve Checkmk password-store references and the executable resolves them at runtime; direct plaintext options, where present, are limited to isolated command-line diagnostics.")
        else:
            lines.append("- Server-side calls handle credentials. Verify in code that Checkmk password-store references remain opaque until the executable resolves them.")
    elif handles_credentials and has_notifications:
        if notification_context_secret:
            lines.append("- The notification obtains its credential from the Checkmk notification context or environment at runtime; no credential is stored in package source or generated documentation.")
        else:
            lines.append("- The notification handles a credential at runtime. Verify its retrieval and logging boundary in the notification source.")
    elif handles_credentials:
        lines.append("- The source handles credentials or tokens. Inspect the executable data path to ensure credentials are supplied at runtime, remain out of logs, and do not cross redirects or untrusted proxies.")
    else:
        lines.append("- No Checkmk password or secret form was detected in the current package source.")
    if network_access:
        lines.append("- The source performs network or remote-system access. Keep timeouts bounded, validate responses, and prevent authenticated redirects or unintended environment-proxy use.")
    else:
        lines.append(
            "- Static analysis did not identify a supported direct remote-network client. "
            "This is not proof of network isolation; review extensionless and non-Python "
            "executables before deployment."
        )
    if tls_optout:
        lines.append("- An explicit TLS-verification opt-out is present. Verification remains the secure default; use the opt-out only as a documented temporary exception and prefer a private CA bundle.")
    if local_automation:
        lines.append("- The source reads the local Checkmk automation secret. It must only transmit that credential to a validated loopback site URL.")
    lines += ["", "### Troubleshooting", ""]
    if sections:
        lines.append(f"- Emitted Checkmk sections detected in source: {', '.join(f'`{item}`' for item in sections[:20])}{' and additional sections' if len(sections) > 20 else ''}.")
    else:
        lines.append("- No literal Checkmk section header was detected. Inspect the executable or notification exit status and the Checkmk log relevant to the component type.")
    if agents:
        lines.append("- For special agents, inspect the generated command without exposing secrets, run it as the site user, and verify that every emitted section has a matching parser/check registration.")
    else:
        lines.append("- Verify deployment path, permissions, registration name, and the exact input/output contract represented by the source files above.")
    lines += [END, ""]
    return "\n".join(lines)


def update_readme(readme: Path, block: str) -> str:
    original = readme.read_text(encoding="utf-8").rstrip() + "\n"
    if START in original:
        prefix, rest = original.split(START, 1)
        if END not in rest:
            raise ValueError(f"{readme}: generated reference start marker has no end marker")
        _, suffix = rest.split(END, 1)
        return prefix.rstrip() + "\n\n" + block + suffix.lstrip("\n")
    return original.rstrip() + "\n\n" + block


def run(root: Path, *, write: bool) -> list[str]:
    stale: list[str] = []
    for info in sorted(root.glob("*/src/info")):
        package = info.parent.parent
        readme = package / "README.md"
        if not readme.exists():
            stale.append(f"{readme.relative_to(root)}: missing")
            continue
        expected = update_readme(readme, derive_reference(root, package, manifest(info)))
        actual = readme.read_text(encoding="utf-8")
        if actual == expected:
            continue
        if write:
            readme.write_text(expected, encoding="utf-8")
        else:
            stale.append(f"{readme.relative_to(root)}: code-derived reference is stale")
    return stale


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--write", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        stale = run(args.root.resolve(), write=args.write)
    except (OSError, SyntaxError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if stale:
        print("\n".join(stale), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
