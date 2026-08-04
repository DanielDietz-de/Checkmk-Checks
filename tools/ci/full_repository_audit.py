#!/usr/bin/env python3
"""Audit all active Checkmk package source and documentation.

The audit is read-only and deterministic. Reviewed legacy findings can be
recorded by fingerprint, while new findings at a chosen severity fail CI.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = 1
SEVERITY = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
SOURCE_SUFFIXES = {".py", ".sh", ".bash", ".php", ".rb", ".ps1"}
EXCLUDED_SOURCE_PARTS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "dist", "tests", "testdata"}
CREDENTIAL_NAME_RE = re.compile(r"(?:^|_)(?:SECRET|PASSWORD|TOKEN|API_KEY|ACCESS_KEY)(?:_|$)", re.I)
ROOT_DOCS = ("README.md", "SECURITY.md", "CONTRIBUTING.md", "MAINTENANCE.md", "SUPPORT.md", "LICENSE")
REQUIRED_ROOT_DOCUMENTS = ROOT_DOCS
META_FIELDS = ("name", "title", "description", "version", "version.min_required", "version.packaged", "version.usable_until", "files")
DOC_SECTIONS = {
    "installation": ("install", "deployment", "setup"),
    "configuration": ("config", "rule", "parameter"),
    "validation": ("test", "validation", "verify"),
    "troubleshooting": ("troubleshoot", "diagnos", "known limitation"),
    "security": ("security", "credential", "permission", "tls"),
}
PRIVATE_KEYS = ("-----BEGIN PRIVATE KEY-----", "-----BEGIN RSA PRIVATE KEY-----", "-----BEGIN OPENSSH PRIVATE KEY-----", "-----BEGIN EC PRIVATE KEY-----")
TOKEN_PATTERNS = (
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access-key identifier"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{30,}\b"), "GitHub token"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"), "Slack token"),
)
POLICY_FILES = {"tools/ci/full_repository_audit.py", "tools/ci/repository_guard.py", "tools/ci/pin_supply_chain.py"}


@dataclass(frozen=True, order=True)
class Finding:
    severity: str
    rule_id: str
    path: str
    line: int
    message: str
    remediation: str

    @property
    def fingerprint(self) -> str:
        value = "\0".join((self.rule_id, self.path, str(self.line), self.message))
        return hashlib.sha256(value.encode()).hexdigest()

    def render(self, baseline: set[str]) -> dict[str, Any]:
        result = asdict(self)
        result.update(fingerprint=self.fingerprint, baseline=self.fingerprint in baseline)
        return result


class AuditError(RuntimeError):
    """Repository content cannot be audited reliably."""


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise AuditError(f"cannot read {path}: {exc}") from exc


def metadata(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(read(path)) if path.name == "info.json" else ast.literal_eval(read(path))
    except (json.JSONDecodeError, SyntaxError, ValueError, TypeError) as exc:
        raise AuditError(f"cannot parse metadata {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise AuditError(f"metadata {path} is not an object")
    return value


def packages(root: Path) -> list[tuple[Path, dict[str, Any]]]:
    result = []
    for directory in sorted(root.iterdir()):
        if not directory.is_dir() or directory.name.startswith("."):
            continue
        info, info_json = directory / "src/info", directory / "src/info.json"
        primary = info if info.is_file() else info_json
        if primary.is_file():
            result.append((directory, metadata(primary)))
    return result


def finding(severity: str, rule: str, root: Path, path: Path, line: int, message: str, remediation: str) -> Finding:
    return Finding(severity, rule, path.relative_to(root).as_posix(), line, message, remediation)


def audit_root_docs(root: Path) -> list[Finding]:
    result = []
    for name in ROOT_DOCS:
        path = root / name
        if not path.is_file():
            result.append(finding("high", "docs.root-missing", root, path, 1, f"required repository document is missing: {name}", f"add and maintain {name}"))
    readme = root / "README.md"
    if readme.is_file():
        text = read(readme).lower()
        for section in ("security", "installation", "compatibility", "support"):
            if section not in text:
                result.append(finding("medium", "docs.root-section-missing", root, readme, 1, f"root README does not explain {section}", f"add a clear {section} section"))
    return result


def audit_package(root: Path, package: Path, primary: dict[str, Any]) -> list[Finding]:
    result = []
    info, info_json = package / "src/info", package / "src/info.json"
    primary_path = info if info.is_file() else info_json
    if info.is_file() and info_json.is_file():
        try:
            secondary = metadata(info_json)
        except AuditError as exc:
            result.append(finding("high", "metadata.secondary-unreadable", root, info_json, 1, str(exc), "repair or remove the secondary metadata file"))
        else:
            for field in META_FIELDS:
                if primary.get(field) != secondary.get(field):
                    result.append(finding("medium", "metadata.representation-mismatch", root, info_json, 1, f"{field} differs between src/info and src/info.json", "synchronize both metadata representations"))
    for field in META_FIELDS:
        value = primary.get(field)
        if field == "files":
            valid = isinstance(value, dict) and bool(value)
        elif field == "version.usable_until":
            valid = field in primary and (value is None or isinstance(value, str) and bool(value.strip()))
        else:
            valid = isinstance(value, str) and bool(value.strip())
        if not valid:
            result.append(finding("medium", "docs.metadata-incomplete", root, primary_path, 1, f"package metadata field {field!r} is missing or invalid", f"document {field} in canonical metadata without inventing unsupported compatibility claims"))
    readme = package / "README.md"
    if not readme.is_file():
        return result + [finding("high", "docs.package-readme-missing", root, readme, 1, "active package has no README", "add package installation, configuration, validation, security, and troubleshooting guidance")]
    text = read(readme)
    normalized = text.lower()
    if len(text.strip()) < 200:
        result.append(finding("medium", "docs.package-readme-thin", root, readme, 1, "package README contains fewer than 200 non-whitespace characters", "expand operational guidance and limitations"))
    for section, terms in DOC_SECTIONS.items():
        if not any(term in normalized for term in terms):
            result.append(finding("low", "docs.package-section-missing", root, readme, 1, f"package README does not appear to cover {section}", f"add a {section} section or state why it is not applicable"))
    return result


def audit_secret_boundary(root: Path, package: Path) -> list[Finding]:
    """Verify that safe Checkmk Secret references are resolved by the executable."""
    server_files = sorted((package / "src").glob("*/server_side_calls/*.py"))
    if not server_files:
        return []
    server_text = "\n".join(read(path) for path in server_files)
    # A single occurrence can be an unused import in legacy modules. Multiple uses
    # indicate a Secret annotation, command argument, or typed argv collection.
    if server_text.count("Secret") < 2 or ".unsafe(" in server_text:
        return []
    agents = sorted((package / "src").glob("*/libexec/agent_*"))
    if not agents:
        return []
    agent_text = "\n".join(read(path) for path in agents)
    if "password_store" in agent_text and any(token in agent_text for token in ("lookup", "resolve_secret", "dereference_secret")):
        return []
    return [
        finding(
            "high",
            "security.secret-reference-unresolved",
            root,
            server_files[0],
            1,
            "server-side calls pass a safe Secret reference but the executable does not resolve the Checkmk password store",
            "accept an explicit *-id option and resolve it inside the special agent",
        )
    ]


def source_language(path: Path) -> str | None:
    if path.suffix.lower() in SOURCE_SUFFIXES:
        return path.suffix.lower()
    if path.suffix:
        return None
    try:
        with path.open("rb") as handle:
            first = handle.readline(512).decode("utf-8", errors="replace").lower()
    except OSError:
        return None
    return "script" if first.startswith("#!") and any(item in first for item in ("python", "/sh", "bash", "ruby", "php")) else None


def source_files(root: Path, active: Iterable[tuple[Path, dict[str, Any]]]) -> Iterable[Path]:
    del active  # discovery covers packaged, archived, tooling, and standalone utility source
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in EXCLUDED_SOURCE_PARTS for part in relative.parts):
            continue
        if source_language(path):
            yield path


def call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def audit_python(root: Path, path: Path, text: str) -> list[Finding]:
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as exc:
        return [finding("high", "code.python-syntax", root, path, exc.lineno or 1, exc.msg, "fix the syntax error or remove the file")]
    result = []
    if ast.get_docstring(tree, clean=False) is None:
        result.append(finding("low", "docs.module-docstring-missing", root, path, 1, "Python source file has no module docstring", "describe purpose, inputs, outputs, and safety boundaries"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            value = node.value
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                literal = value.value.strip()
                for target in targets:
                    if not isinstance(target, ast.Name) or not CREDENTIAL_NAME_RE.search(target.id):
                        continue
                    looks_like_env_name = target.id.upper().endswith("_ENV") and bool(
                        re.fullmatch(r"[A-Z][A-Z0-9_]+", literal)
                    )
                    looks_like_option = literal.startswith("--")
                    looks_like_placeholder = literal.lower() in {
                        "example", "placeholder", "changeme", "change-me", "secret", "password", "token"
                    }
                    if len(literal) >= 8 and not (looks_like_env_name or looks_like_option or looks_like_placeholder):
                        result.append(
                            finding(
                                "critical",
                                "security.hardcoded-credential",
                                root,
                                path,
                                getattr(node, "lineno", 1),
                                f"credential-like constant {target.id} contains a literal value",
                                "remove the value, rotate any matching credential, and read it from a secret store at runtime",
                            )
                        )
        if not isinstance(node, ast.Call):
            continue
        name, line = call_name(node.func), getattr(node, "lineno", 1)
        if name == "disable_warnings" or name.endswith(".disable_warnings"):
            result.append(
                finding(
                    "high",
                    "security.tls-warning-suppression",
                    root,
                    path,
                    line,
                    "TLS warnings are disabled globally",
                    "remove global warning suppression and configure trust explicitly",
                )
            )
        if name in {"eval", "exec"}:
            result.append(finding("critical", "security.dynamic-code-execution", root, path, line, f"built-in {name}() executes dynamic code", "replace dynamic execution with explicit parsing and validation"))
        if name in {"os.system", "os.popen", "commands.getoutput", "commands.getstatusoutput"}:
            result.append(finding("high", "security.shell-execution", root, path, line, f"{name} invokes a shell", "use subprocess with a validated argument list and no shell"))
        if name.startswith("subprocess."):
            for keyword in node.keywords:
                if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                    result.append(finding("high", "security.subprocess-shell", root, path, getattr(keyword.value, "lineno", line), "subprocess call enables shell execution", "pass a validated argument list without a shell"))
        for keyword in node.keywords:
            if keyword.arg == "verify" and isinstance(keyword.value, ast.Constant) and keyword.value.value is False:
                result.append(finding("high", "security.tls-verification-disabled", root, path, getattr(keyword.value, "lineno", line), "TLS certificate verification is disabled", "enable verification and support an explicit private CA bundle"))
        if name.endswith((".get", ".post", ".put", ".patch", ".delete", ".request")) and (name.startswith("requests.") or ".session." in name.lower() or name.startswith("session.")):
            if not any(keyword.arg == "timeout" for keyword in node.keywords):
                result.append(finding("medium", "security.network-timeout-missing", root, path, line, f"network call {name} has no explicit timeout", "set a bounded connect/read timeout"))
        if name in {"pickle.load", "pickle.loads", "marshal.load", "marshal.loads"}:
            result.append(finding("high", "security.unsafe-deserialization", root, path, line, f"{name} accepts executable or unsafe data", "use bounded JSON with schema validation"))
    return result


def audit_text(root: Path, path: Path, text: str) -> list[Finding]:
    result, policy = [], path.relative_to(root).as_posix() in POLICY_FILES
    for number, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith(("#", "//")):
            continue
        if not policy and ("." + "unsafe(") in line:
            result.append(finding("high", "security.secret-flattening", root, path, number, "Checkmk Secret is flattened to plaintext", "preserve Checkmk secret-aware handling"))
        if not policy and (("urllib3." + "disable_warnings") in line or ("requests.packages.urllib3." + "disable_warnings") in line):
            result.append(finding("high", "security.tls-warning-suppression", root, path, number, "TLS warnings are disabled globally", "configure certificate trust explicitly"))
    if policy:
        return result
    for marker in PRIVATE_KEYS:
        if marker in text:
            line = text[: text.index(marker)].count("\n") + 1
            result.append(finding("critical", "security.private-key-material", root, path, line, "private-key material appears to be committed", "revoke and remove the key from history"))
    for pattern, label in TOKEN_PATTERNS:
        match = pattern.search(text)
        if match:
            line = text[: match.start()].count("\n") + 1
            result.append(finding("critical", "security.token-material", root, path, line, f"possible committed {label}", "revoke and remove the credential from history"))
    return result


def audit_source(root: Path, path: Path) -> list[Finding]:
    try:
        text = read(path)
    except AuditError as exc:
        return [finding("high", "code.unreadable", root, path, 1, str(exc), "store source as valid UTF-8 text")]
    result = audit_text(root, path, text)
    lines = text.splitlines()
    first = lines[0].lower() if lines else ""
    if path.suffix.lower() == ".py" or first.startswith("#!") and "python" in first:
        result += audit_python(root, path, text)
    return result


def audit_hygiene(root: Path) -> list[Finding]:
    result = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in {".git", ".venv", "venv", "__pycache__"} for part in path.parts):
            continue
        if path.suffix in {".pyc", ".pyo"}:
            result.append(finding("medium", "hygiene.bytecode-tracked", root, path, 1, "compiled Python bytecode is present", "remove generated bytecode and keep it ignored"))
        if path.name in {".env", "id_rsa", "id_ed25519"}:
            result.append(finding("critical", "security.sensitive-file-name", root, path, 1, f"sensitive file name is present: {path.name}", "remove it, rotate credentials, and use a secret store"))
    return result


def load_baseline(path: Path | None) -> set[str]:
    if path is None or not path.exists():
        return set()
    try:
        value = json.loads(read(path))
    except json.JSONDecodeError as exc:
        raise AuditError(f"cannot parse baseline {path}: {exc}") from exc
    fingerprints = value.get("fingerprints") if isinstance(value, dict) and value.get("schema_version") == SCHEMA_VERSION else None
    if not isinstance(fingerprints, list) or not all(isinstance(item, str) for item in fingerprints):
        raise AuditError(f"invalid baseline {path}")
    return set(fingerprints)


def build_report(root: Path, baseline: set[str]) -> dict[str, Any]:
    active = packages(root)
    findings = audit_root_docs(root)
    for package, data in active:
        findings += audit_package(root, package, data)
        findings += audit_secret_boundary(root, package)
    sources = list(source_files(root, active))
    for path in sources:
        findings += audit_source(root, path)
    findings += audit_hygiene(root)
    unique = sorted(set(findings), key=lambda item: (item.path, item.line, item.rule_id, item.message))
    all_counts = {key: 0 for key in SEVERITY}
    new_counts = {key: 0 for key in SEVERITY}
    for item in unique:
        all_counts[item.severity] += 1
        if item.fingerprint not in baseline:
            new_counts[item.severity] += 1
    return {"schema_version": SCHEMA_VERSION, "active_packages": len(active), "source_files": len(sources), "summary": {"all": all_counts, "new": new_counts, "total": len(unique)}, "findings": [item.render(baseline) for item in unique]}


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--write-baseline", type=Path)
    parser.add_argument("--fail-on", choices=("none", *SEVERITY), default="high")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = arguments(argv)
    try:
        root = args.root.resolve()
        baseline_path = args.baseline if args.baseline is None or args.baseline.is_absolute() else root / args.baseline
        report = build_report(root, load_baseline(baseline_path))
    except AuditError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = args.output if args.output.is_absolute() else root / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    if args.write_baseline:
        target = args.write_baseline if args.write_baseline.is_absolute() else root / args.write_baseline
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({"schema_version": SCHEMA_VERSION, "fingerprints": sorted(item["fingerprint"] for item in report["findings"])}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.fail_on == "none":
        return 0
    threshold = SEVERITY[args.fail_on]
    return int(any(not item["baseline"] and SEVERITY[item["severity"]] >= threshold for item in report["findings"]))


if __name__ == "__main__":
    raise SystemExit(main())
