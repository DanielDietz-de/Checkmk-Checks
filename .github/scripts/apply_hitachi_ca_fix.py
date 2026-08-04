#!/usr/bin/env python3
"""Apply the reviewed Hitachi HNAS private-CA compatibility remediation."""

from pathlib import Path


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"expected exactly one {label} block in {path}")
    path.write_text(text.replace(old, new), encoding="utf-8")


agent = Path("hitachi_hnas_rest/src/hitachi_hnas_rest/libexec/agent_hitachi_hnas_rest")
replace_once(
    agent,
    "import json\nimport sys\n",
    "import json\nimport os\nimport sys\n",
    "agent imports",
)
replace_once(
    agent,
    '''    return lookup(Path(store_path), secret_id)\n\n\n\nclass AgentHitachiHnasRest:\n''',
    '''    return lookup(Path(store_path), secret_id)\n\n\ndef _resolve_ca_bundle(explicit_ca_file: str | None, no_cert_check: bool) -> str | bool:\n    """Resolve explicit or site-wide CA trust without enabling proxy inheritance."""\n    if explicit_ca_file and no_cert_check:\n        raise ValueError("--ca-file and --no-cert-check are mutually exclusive")\n    if no_cert_check:\n        return False\n\n    configured = (\n        explicit_ca_file\n        or os.environ.get("REQUESTS_CA_BUNDLE")\n        or os.environ.get("CURL_CA_BUNDLE")\n    )\n    if not configured:\n        return True\n\n    path = Path(configured).expanduser()\n    if not path.is_file():\n        raise ValueError(f"CA bundle does not exist or is not a file: {path}")\n    return str(path.resolve())\n\n\nclass AgentHitachiHnasRest:\n''',
    "CA resolver",
)
replace_once(
    agent,
    '''        self.timeout = args.timeout\n        self.verify = False if args.no_cert_check else (args.ca_file or True)\n\n        # One session for all requests; environment proxies are not trusted for credentials.\n''',
    '''        self.timeout = args.timeout\n        self.verify = _resolve_ca_bundle(args.ca_file, args.no_cert_check)\n\n        # One session for all requests. Proxy and netrc inheritance stay disabled;\n        # established site CA-bundle variables are handled explicitly above.\n''',
    "constructor trust policy",
)
replace_once(
    agent,
    '''        # verify is passed per request: a session-level setting would be\n        # overridden by REQUESTS_CA_BUNDLE, which OMD sites always set\n''',
    '''        # Certificate trust is passed explicitly because trust_env remains disabled.\n''',
    "request trust comment",
)
replace_once(
    agent,
    '''    if args.password_id:\n        args.password = _resolve_secret_reference(args.password_id)\n\n    if not args.api_key and not (args.user and args.password):\n''',
    '''    if args.password_id:\n        args.password = _resolve_secret_reference(args.password_id)\n    if args.ca_file and args.no_cert_check:\n        parser.error("--ca-file and --no-cert-check are mutually exclusive")\n\n    if not args.api_key and not (args.user and args.password):\n''',
    "CLI conflict validation",
)

server = Path("hitachi_hnas_rest/src/hitachi_hnas_rest/server_side_calls/agent.py")
replace_once(
    server,
    '''    if params.get("no_cert_check"):\n        args.append("--no-cert-check")\n\n    yield SpecialAgentCommand(command_arguments=args)\n''',
    '''    ca_file = params.get("ca_file")\n    no_cert_check = bool(params.get("no_cert_check"))\n    if ca_file and no_cert_check:\n        raise ValueError("ca_file and no_cert_check are mutually exclusive")\n    if ca_file:\n        args.extend(("--ca-file", ca_file))\n    elif no_cert_check:\n        args.append("--no-cert-check")\n\n    yield SpecialAgentCommand(command_arguments=args)\n''',
    "server-side TLS arguments",
)

ruleset = Path("hitachi_hnas_rest/src/hitachi_hnas_rest/rulesets/agent.py")
replace_once(
    ruleset,
    '''            "no_cert_check": DictElement(\n                parameter_form=BooleanChoice(\n''',
    '''            "ca_file": DictElement(\n                parameter_form=String(\n                    title=Title("Custom CA bundle"),\n                    help_text=Help(\n                        "Optional absolute path on the Checkmk server to a PEM CA "\n                        "bundle for a private HNAS certificate. This overrides "\n                        "REQUESTS_CA_BUNDLE and CURL_CA_BUNDLE."\n                    ),\n                    custom_validate=(LengthInRange(min_value=1),),\n                ),\n                required=False,\n            ),\n            "no_cert_check": DictElement(\n                parameter_form=BooleanChoice(\n''',
    "ruleset CA field",
)
replace_once(
    ruleset,
    '''                        "Disable the verification of the TLS certificate. "\n                        "Needed for self-signed certificates."\n''',
    '''                        "Disable TLS certificate verification only as a temporary "\n                        "exception. Prefer the custom CA bundle for private trust."\n''',
    "ruleset TLS help",
)

transport_test = Path("hitachi_hnas_rest/tests/test_hitachi_hnas_rest_transport.py")
transport_test.write_text(
    '''"""Regression tests for Hitachi HNAS transport and private-CA handling."""\n\nfrom __future__ import annotations\n\nimport importlib.machinery\nimport importlib.util\nfrom pathlib import Path\n\nimport pytest\n\nPACKAGE_ROOT = Path(__file__).resolve().parents[1]\nAGENT = PACKAGE_ROOT / "src/hitachi_hnas_rest/libexec/agent_hitachi_hnas_rest"\nSERVER_SIDE = PACKAGE_ROOT / "src/hitachi_hnas_rest/server_side_calls/agent.py"\nRULESET = PACKAGE_ROOT / "src/hitachi_hnas_rest/rulesets/agent.py"\n\n\ndef _load_agent():\n    loader = importlib.machinery.SourceFileLoader("hitachi_hnas_agent_test", str(AGENT))\n    spec = importlib.util.spec_from_loader(loader.name, loader)\n    assert spec is not None\n    module = importlib.util.module_from_spec(spec)\n    loader.exec_module(module)\n    return module\n\n\ndef test_ca_bundle_flows_from_ruleset_to_agent() -> None:\n    server_source = SERVER_SIDE.read_text(encoding="utf-8")\n    ruleset_source = RULESET.read_text(encoding="utf-8")\n    agent_source = AGENT.read_text(encoding="utf-8")\n\n    assert 'params.get("ca_file")' in server_source\n    assert '"--ca-file"' in server_source\n    assert '"ca_file": DictElement(' in ruleset_source\n    assert 'parser.add_argument("--ca-file"' in agent_source\n    assert 'os.environ.get("REQUESTS_CA_BUNDLE")' in agent_source\n    assert 'os.environ.get("CURL_CA_BUNDLE")' in agent_source\n\n\ndef test_requests_ca_bundle_is_preserved_with_proxy_isolation(\n    monkeypatch: pytest.MonkeyPatch, tmp_path: Path\n) -> None:\n    module = _load_agent()\n    bundle = tmp_path / "site-ca.pem"\n    bundle.write_text("site CA\\n", encoding="utf-8")\n    monkeypatch.setenv("REQUESTS_CA_BUNDLE", str(bundle))\n    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.invalid:8080")\n\n    assert module._resolve_ca_bundle(None, False) == str(bundle.resolve())\n\n\ndef test_curl_ca_bundle_is_the_compatible_fallback(\n    monkeypatch: pytest.MonkeyPatch, tmp_path: Path\n) -> None:\n    module = _load_agent()\n    bundle = tmp_path / "curl-ca.pem"\n    bundle.write_text("curl CA\\n", encoding="utf-8")\n    monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)\n    monkeypatch.setenv("CURL_CA_BUNDLE", str(bundle))\n\n    assert module._resolve_ca_bundle(None, False) == str(bundle.resolve())\n\n\ndef test_explicit_ca_bundle_overrides_environment(\n    monkeypatch: pytest.MonkeyPatch, tmp_path: Path\n) -> None:\n    module = _load_agent()\n    environment_bundle = tmp_path / "environment.pem"\n    explicit_bundle = tmp_path / "explicit.pem"\n    environment_bundle.write_text("environment CA\\n", encoding="utf-8")\n    explicit_bundle.write_text("explicit CA\\n", encoding="utf-8")\n    monkeypatch.setenv("REQUESTS_CA_BUNDLE", str(environment_bundle))\n\n    assert module._resolve_ca_bundle(str(explicit_bundle), False) == str(\n        explicit_bundle.resolve()\n    )\n\n\ndef test_tls_opt_out_is_explicit_and_conflicts_are_rejected(tmp_path: Path) -> None:\n    module = _load_agent()\n    bundle = tmp_path / "private.pem"\n    bundle.write_text("private CA\\n", encoding="utf-8")\n\n    assert module._resolve_ca_bundle(None, True) is False\n    with pytest.raises(ValueError, match="mutually exclusive"):\n        module._resolve_ca_bundle(str(bundle), True)\n\n\ndef test_missing_ca_bundle_is_rejected(tmp_path: Path) -> None:\n    module = _load_agent()\n    with pytest.raises(ValueError, match="CA bundle does not exist"):\n        module._resolve_ca_bundle(str(tmp_path / "missing.pem"), False)\n''',
    encoding="utf-8",
)

readme = Path("hitachi_hnas_rest/README.md")
replace_once(
    readme,
    '''3. Configure the rule *Hitachi HNAS via REST API* under\n   *Setup > Agents > Other integrations*.\n\nAuthentication is done either via the `X-Api-Key` header (recommended\n''',
    '''3. Configure the rule *Hitachi HNAS via REST API* under\n   *Setup > Agents > Other integrations*. For a private certificate authority,\n   provide the absolute PEM CA-bundle path instead of disabling verification.\n\nAuthentication is done either via the `X-Api-Key` header (recommended\n''',
    "README setup",
)
replace_once(
    readme,
    '''- An explicit TLS-verification opt-out is present. Verification remains the secure default; use the opt-out only as a documented temporary exception and prefer a private CA bundle.\n''',
    '''- Certificate verification remains the secure default. Trust precedence is rule `ca_file`, `REQUESTS_CA_BUNDLE`, `CURL_CA_BUNDLE`, then the system trust store; environment proxies and netrc credentials remain disabled. The verification opt-out is only a documented temporary exception.\n''',
    "README security",
)
