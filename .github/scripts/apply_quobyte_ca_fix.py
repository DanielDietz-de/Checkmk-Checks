#!/usr/bin/env python3
"""Apply the reviewed Quobyte private-CA compatibility remediation."""

from pathlib import Path


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"expected exactly one {label} block in {path}")
    path.write_text(text.replace(old, new), encoding="utf-8")


agent = Path("quobyte/src/quobyte/libexec/agent_quobyte")
replace_once(
    agent,
    "import argparse\nfrom pathlib import Path\n",
    "import argparse\nimport os\nfrom pathlib import Path\n",
    "agent imports",
)
replace_once(
    agent,
    '''    return lookup(Path(store_path), secret_id)\n\n\n\nclass Quobyte():\n''',
    '''    return lookup(Path(store_path), secret_id)\n\n\ndef _resolve_ca_bundle(explicit_ca_file: str | None) -> str | bool:\n    """Resolve explicit or site-wide CA trust without enabling proxy inheritance."""\n    configured = (\n        explicit_ca_file\n        or os.environ.get("REQUESTS_CA_BUNDLE")\n        or os.environ.get("CURL_CA_BUNDLE")\n    )\n    if not configured:\n        return True\n\n    path = Path(configured).expanduser()\n    if not path.is_file():\n        raise ValueError(f"CA bundle does not exist or is not a file: {path}")\n    return str(path.resolve())\n\n\nclass Quobyte():\n''',
    "CA resolver",
)
replace_once(
    agent,
    '''    def __init__(self, api_host, user, password, timeout):\n        """\n        Init\n        """\n        self.api_host = api_host\n        self.auth = HTTPBasicAuth(user, password)\n        self.session = requests.Session()\n        self.session.trust_env = False\n        self.timeout = 15.0\n        if timeout:\n            self.timeout = float(timeout)\n''',
    '''    def __init__(self, api_host, user, password, timeout, ca_file=None):\n        """Initialize an isolated HTTP session with explicit certificate trust."""\n        self.api_host = api_host\n        self.auth = HTTPBasicAuth(user, password)\n        self.session = requests.Session()\n        # Do not inherit ambient proxies or netrc credentials. Preserve only the\n        # established Checkmk site CA-bundle variables through explicit handling.\n        self.session.trust_env = False\n        self.session.verify = _resolve_ca_bundle(ca_file)\n        self.timeout = 15.0\n        if timeout:\n            self.timeout = float(timeout)\n''',
    "Quobyte constructor",
)
replace_once(
    agent,
    '''    password_group.add_argument("--password-id", help="Checkmk password-store reference")\n    parser.add_argument("--timeout", type=float, default=15.0)\n''',
    '''    password_group.add_argument("--password-id", help="Checkmk password-store reference")\n    parser.add_argument(\n        "--ca-file",\n        help=(\n            "Optional PEM CA bundle. Overrides REQUESTS_CA_BUNDLE and "\n            "CURL_CA_BUNDLE while environment proxies remain disabled."\n        ),\n    )\n    parser.add_argument("--timeout", type=float, default=15.0)\n''',
    "CA command-line option",
)
replace_once(
    agent,
    '''    qb = Quobyte(arguments.api_url, arguments.username, arguments.password, arguments.timeout)\n''',
    '''    qb = Quobyte(\n        arguments.api_url,\n        arguments.username,\n        arguments.password,\n        arguments.timeout,\n        arguments.ca_file,\n    )\n''',
    "Quobyte construction",
)

server = Path("quobyte/src/quobyte/server_side_calls/quobyte.py")
replace_once(
    server,
    '''    password: Secret\n    timeout: float = 15.0\n\n\ndef generate_quobyte_command(params: QuobyteParams, host_config: HostConfig):\n    yield SpecialAgentCommand(\n        command_arguments=(\n            "--api-url",\n            params.api_url,\n            "--username",\n            params.username,\n            "--password-id",\n            params.password,\n            "--timeout",\n            str(params.timeout),\n        )\n    )\n''',
    '''    password: Secret\n    timeout: float = 15.0\n    ca_file: str | None = None\n\n\ndef generate_quobyte_command(params: QuobyteParams, host_config: HostConfig):\n    """Build a secret-aware command with optional explicit private-CA trust."""\n    command_arguments = [\n        "--api-url",\n        params.api_url,\n        "--username",\n        params.username,\n        "--password-id",\n        params.password,\n        "--timeout",\n        str(params.timeout),\n    ]\n    if params.ca_file:\n        command_arguments.extend(["--ca-file", params.ca_file])\n\n    yield SpecialAgentCommand(command_arguments=command_arguments)\n''',
    "server-side CA wiring",
)

ruleset = Path("quobyte/src/quobyte/rulesets/agent.py")
replace_once(
    ruleset,
    '''            "timeout": DictElement(\n                parameter_form = TimeSpan(\n''',
    '''            "ca_file": DictElement(\n                parameter_form = String(\n                    title = Title("Custom CA bundle"),\n                    help_text = Help(\n                        "Optional absolute path on the Checkmk server to a PEM CA "\n                        "bundle for a private Quobyte certificate. This overrides "\n                        "REQUESTS_CA_BUNDLE and CURL_CA_BUNDLE."\n                    ),\n                    custom_validate=(LengthInRange(min_value=1),),\n                ),\n                required = False,\n            ),\n            "timeout": DictElement(\n                parameter_form = TimeSpan(\n''',
    "ruleset CA field",
)

test = Path("quobyte/tests/test_quobyte_secret_command_arguments.py")
test.write_text(
    '''"""Regression tests for Quobyte secret and TLS command boundaries."""\n\nfrom __future__ import annotations\n\nimport ast\nimport importlib.machinery\nimport importlib.util\nfrom pathlib import Path\n\nimport pytest\n\nPACKAGE_ROOT = Path(__file__).resolve().parents[1]\nSERVER_SIDE_CALL = PACKAGE_ROOT / "src/quobyte/server_side_calls/quobyte.py"\nRULESET = PACKAGE_ROOT / "src/quobyte/rulesets/agent.py"\nAGENT = PACKAGE_ROOT / "src/quobyte/libexec/agent_quobyte"\n\n\ndef _load_agent():\n    loader = importlib.machinery.SourceFileLoader("quobyte_agent_test", str(AGENT))\n    spec = importlib.util.spec_from_loader(loader.name, loader)\n    assert spec is not None\n    module = importlib.util.module_from_spec(spec)\n    loader.exec_module(module)\n    return module\n\n\ndef test_server_side_call_preserves_secret_object() -> None:\n    text = SERVER_SIDE_CALL.read_text(encoding="utf-8")\n    tree = ast.parse(text)\n    assert not any(\n        isinstance(node, ast.Call)\n        and isinstance(node.func, ast.Attribute)\n        and node.func.attr == "unsafe"\n        for node in ast.walk(tree)\n    )\n    assert "Secret" in text\n\n\ndef test_ca_bundle_flows_from_ruleset_to_agent() -> None:\n    server_source = SERVER_SIDE_CALL.read_text(encoding="utf-8")\n    ruleset_source = RULESET.read_text(encoding="utf-8")\n    agent_source = AGENT.read_text(encoding="utf-8")\n\n    assert "ca_file: str | None = None" in server_source\n    assert '"--ca-file"' in server_source\n    assert '"ca_file": DictElement(' in ruleset_source\n    assert 'parser.add_argument(\\n        "--ca-file"' in agent_source\n    assert 'os.environ.get("REQUESTS_CA_BUNDLE")' in agent_source\n    assert 'os.environ.get("CURL_CA_BUNDLE")' in agent_source\n\n\ndef test_requests_ca_bundle_is_preserved_without_proxy_inheritance(\n    monkeypatch: pytest.MonkeyPatch, tmp_path: Path\n) -> None:\n    module = _load_agent()\n    bundle = tmp_path / "site-ca.pem"\n    bundle.write_text("test CA bundle\\n", encoding="utf-8")\n    monkeypatch.setenv("REQUESTS_CA_BUNDLE", str(bundle))\n    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.invalid:8080")\n\n    client = module.Quobyte("https://quobyte.invalid", "user", "secret", 5.0)\n\n    assert client.session.trust_env is False\n    assert client.session.verify == str(bundle.resolve())\n\n\ndef test_curl_ca_bundle_is_the_compatible_fallback(\n    monkeypatch: pytest.MonkeyPatch, tmp_path: Path\n) -> None:\n    module = _load_agent()\n    bundle = tmp_path / "curl-ca.pem"\n    bundle.write_text("test CA bundle\\n", encoding="utf-8")\n    monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)\n    monkeypatch.setenv("CURL_CA_BUNDLE", str(bundle))\n\n    client = module.Quobyte("https://quobyte.invalid", "user", "secret", 5.0)\n\n    assert client.session.verify == str(bundle.resolve())\n\n\ndef test_explicit_ca_bundle_overrides_environment(\n    monkeypatch: pytest.MonkeyPatch, tmp_path: Path\n) -> None:\n    module = _load_agent()\n    environment_bundle = tmp_path / "environment-ca.pem"\n    explicit_bundle = tmp_path / "explicit-ca.pem"\n    environment_bundle.write_text("environment CA\\n", encoding="utf-8")\n    explicit_bundle.write_text("explicit CA\\n", encoding="utf-8")\n    monkeypatch.setenv("REQUESTS_CA_BUNDLE", str(environment_bundle))\n\n    client = module.Quobyte(\n        "https://quobyte.invalid",\n        "user",\n        "secret",\n        5.0,\n        str(explicit_bundle),\n    )\n\n    assert client.session.verify == str(explicit_bundle.resolve())\n\n\ndef test_missing_ca_bundle_is_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:\n    module = _load_agent()\n    monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)\n    monkeypatch.delenv("CURL_CA_BUNDLE", raising=False)\n\n    with pytest.raises(ValueError, match="CA bundle does not exist"):\n        module.Quobyte(\n            "https://quobyte.invalid",\n            "user",\n            "secret",\n            5.0,\n            str(tmp_path / "missing.pem"),\n        )\n''',
    encoding="utf-8",
)

readme = Path("quobyte/README.md")
replace_once(
    readme,
    '''The special agent [`agent_quobyte`](src/quobyte/libexec/agent_quobyte) is\ninvoked with API URL, username, password and timeout. It POSTs JSON-RPC\ncalls and emits the following sections:\n''',
    '''The special agent [`agent_quobyte`](src/quobyte/libexec/agent_quobyte) is\ninvoked with API URL, username, password, timeout and an optional explicit\nCA bundle. It POSTs JSON-RPC calls and emits the following sections:\n''',
    "README invocation description",
)
replace_once(
    readme,
    '''| `src/quobyte/server_side_calls/quobyte.py` | Server-side-call wiring: passes `api_url username password timeout` as positional arguments. |\n''',
    '''| `src/quobyte/server_side_calls/quobyte.py` | Server-side-call wiring: preserves the password-store reference and passes URL, user, timeout and optional CA bundle as named arguments. |\n''',
    "README package table",
)
replace_once(
    readme,
    '''   and the matching password; optionally override the timeout.\n''',
    '''   and the matching password; optionally override the timeout and provide\n   an absolute PEM CA-bundle path for a private certificate authority.\n''',
    "README installation",
)
replace_once(
    readme,
    '''| `password` | `Password` (required) | API password. |\n| `timeout` | `TimeSpan` (optional, default 2.5 s) | Request timeout. |\n''',
    '''| `password` | `Password` (required) | API password stored through Checkmk's password store. |\n| `ca_file` | `String` (optional) | Absolute PEM CA-bundle path on the Checkmk server. Overrides `REQUESTS_CA_BUNDLE`, then `CURL_CA_BUNDLE`. |\n| `timeout` | `TimeSpan` (optional, default 2.5 s) | Request timeout. |\n''',
    "README parameter table",
)
replace_once(
    readme,
    '''## Known limitations\n\n- Credentials are passed as positional CLI arguments to the agent\n  (`api_url username password timeout`); they therefore appear in the\n  agent process arguments on the Checkmk server.\n- The `timeout` default in the server-side call model is `"15.0"` as a\n  string and only the ruleset default of 2.5 s takes effect; do not rely\n  on the Python type annotation.\n- Quota parsing assumes a single `current_usage` entry per quota - the\n''',
    '''## Known limitations\n\n- Ambient proxy and netrc settings are intentionally ignored. Certificate\n  trust is retained explicitly with this precedence: rule `ca_file`,\n  `REQUESTS_CA_BUNDLE`, `CURL_CA_BUNDLE`, then the system trust store.\n- Quota parsing assumes a single `current_usage` entry per quota - the\n''',
    "README limitations",
)
