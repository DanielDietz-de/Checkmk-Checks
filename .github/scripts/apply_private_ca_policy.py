#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

HELPER = '''\n\ndef _resolve_ca_bundle(explicit_ca_file: str | None, no_cert_check: bool) -> str | bool:\n    """Resolve explicit or site-wide CA trust without enabling proxy inheritance."""\n    if explicit_ca_file and no_cert_check:\n        raise ValueError("--ca-file and --no-cert-check are mutually exclusive")\n    if no_cert_check:\n        return False\n\n    configured = (\n        explicit_ca_file\n        or os.environ.get("REQUESTS_CA_BUNDLE")\n        or os.environ.get("CURL_CA_BUNDLE")\n    )\n    if not configured:\n        return True\n\n    path = Path(configured).expanduser()\n    if not path.is_file():\n        raise ValueError(f"CA bundle does not exist or is not a file: {path}")\n    return str(path.resolve())\n'''

DOC = '''\n\n## TLS trust and private CAs\n\nTLS certificate verification remains enabled by default. To preserve Checkmk site isolation, the integration disables Requests proxy and `.netrc` inheritance with `trust_env = False` and passes certificate trust explicitly. The trust order is:\n\n1. the rule's **Custom CA bundle** (`ca_file`);\n2. `REQUESTS_CA_BUNDLE` from the Checkmk site environment;\n3. `CURL_CA_BUNDLE` from the Checkmk site environment;\n4. the operating system trust store.\n\nThe configured bundle must exist as a regular PEM file on the Checkmk server. An explicit certificate-verification opt-out, where supported, is mutually exclusive with a custom CA bundle and should be used only as a temporary compatibility measure. Environment CA variables are read deliberately even though proxy and `.netrc` inheritance remain disabled.\n\nTroubleshooting order: verify the endpoint name matches the certificate, confirm the PEM path is readable by the site user, test the CA chain with the same site environment, and use the verification opt-out only to isolate a trust-chain problem. Removing `ca_file` falls back automatically to the site variables and then to the system trust store.\n'''


def p(path: str) -> Path:
    return ROOT / path


def read(path: str) -> str:
    return p(path).read_text(encoding='utf-8')


def write(path: str, text: str) -> None:
    p(path).write_text(text, encoding='utf-8')


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f'{path}: expected text not found: {old[:80]!r}')
    write(path, text.replace(old, new, 1))


def ensure_import_os(path: str) -> None:
    text = read(path)
    if '\nimport os\n' in text or '\nfrom os import ' in text:
        return
    for marker in ('import argparse\n', 'import json\n', 'from __future__ import annotations\n'):
        if marker in text:
            write(path, text.replace(marker, marker + 'import os\n', 1))
            return
    raise RuntimeError(f'{path}: cannot place os import')


def ensure_helper(path: str) -> None:
    text = read(path)
    if 'def _resolve_ca_bundle(' in text:
        return
    marker = '    return lookup(Path(store_path), secret_id)\n'
    if marker not in text:
        raise RuntimeError(f'{path}: secret resolver marker missing')
    write(path, text.replace(marker, marker + HELPER, 1))


def ensure_doc(path: str) -> None:
    text = read(path)
    if '## TLS trust and private CAs' not in text:
        write(path, text.rstrip() + DOC + '\n')


def update_dell() -> None:
    path = 'dell_pmax/src/dell_pmax/libexec/agent_dellpmax'
    ensure_import_os(path); ensure_helper(path)
    replace_once(path, '    verify = False if args.no_cert_check else (args.ca_file or True)\n', '    verify = _resolve_ca_bundle(args.ca_file, args.no_cert_check)\n')
    ensure_doc('dell_pmax/README.md')


def update_semu() -> None:
    path = 'semu/src/semu/libexec/agent_semu'
    ensure_import_os(path); ensure_helper(path)
    replace_once(path, '    verify: bool | str = False if args.no_cert_check else (args.ca_file or True)\n', '    verify = _resolve_ca_bundle(args.ca_file, args.no_cert_check)\n')
    ensure_doc('semu/README.md')


def update_spring() -> None:
    agent = 'spring_boot_actuator/src/spring_boot_actuator/libexec/agent_spring_boot_actuator'
    ensure_import_os(agent); ensure_helper(agent)
    replace_once(agent, '    parser.add_argument("--no-cert-check", action="store_true")\n', '    parser.add_argument("--ca-file", help="Private CA bundle used for TLS verification")\n    parser.add_argument("--no-cert-check", action="store_true")\n')
    replace_once(agent, '    health = fetch_health(args.url, args.username, args.password or "", not args.no_cert_check)\n', '    verify = _resolve_ca_bundle(args.ca_file, args.no_cert_check)\n    health = fetch_health(args.url, args.username, args.password or "", verify)\n')
    server = 'spring_boot_actuator/src/spring_boot_actuator/server_side_calls/spring_boot_actuator.py'
    replace_once(server, '    verify_ssl: bool = True\n', '    verify_ssl: bool = True\n    ca_file: Optional[str] = None\n')
    replace_once(server, '    if not params.verify_ssl:\n        arguments.append("--no-cert-check")\n', '    if params.ca_file and not params.verify_ssl:\n        raise ValueError("ca_file and verify_ssl=False are mutually exclusive")\n    if params.ca_file:\n        arguments.extend(["--ca-file", params.ca_file])\n    elif not params.verify_ssl:\n        arguments.append("--no-cert-check")\n')
    rules = 'spring_boot_actuator/src/spring_boot_actuator/rulesets/spring_boot_actuator.py'
    replace_once(rules, '            "verify_ssl": DictElement(\n', '            "ca_file": DictElement(\n                parameter_form=String(\n                    title=Title("Custom CA bundle"),\n                    help_text=Help(\n                        "Optional path on the Checkmk server to a PEM CA bundle. "\n                        "It overrides REQUESTS_CA_BUNDLE and CURL_CA_BUNDLE."\n                    ),\n                    custom_validate=(LengthInRange(min_value=1),),\n                ),\n                required=False,\n            ),\n            "verify_ssl": DictElement(\n')
    ensure_doc('spring_boot_actuator/README.md')


def update_unisphere() -> None:
    agent = 'unisphere_powermax/src/unisphere_powermax/libexec/agent_unisphere_powermax'
    ensure_helper(agent)
    replace_once(agent, "    parser.add_argument('--no_cert_check',\n        help='do not verify ssl certificates', action='store_true')\n", "    parser.add_argument('--ca-file', dest='ca_file',\n        help='private CA bundle used for TLS verification')\n    parser.add_argument('--no_cert_check',\n        help='do not verify ssl certificates', action='store_true')\n")
    replace_once(agent, '                f"{args.hostname}:{args.port}", not args.no_cert_check, api_version, args.debug)\n', '                f"{args.hostname}:{args.port}",\n                _resolve_ca_bundle(args.ca_file, args.no_cert_check),\n                api_version, args.debug)\n')
    server = 'unisphere_powermax/src/unisphere_powermax/server_side_calls/unisphere_powermax.py'
    replace_once(server, '    no_cert_check: Optional[bool] = None\n', '    no_cert_check: Optional[bool] = None\n    ca_file: Optional[str] = None\n')
    replace_once(server, '    for option in (\n', '    if params.ca_file and params.no_cert_check:\n        raise ValueError("ca_file and no_cert_check are mutually exclusive")\n    if params.ca_file:\n        args.extend(("--ca-file", params.ca_file))\n    elif params.no_cert_check:\n        args.append("--no_cert_check")\n\n    for option in (\n')
    replace_once(server, '        "enable_remote_sym_checks",\n        "no_cert_check",\n', '        "enable_remote_sym_checks",\n')
    rules = 'unisphere_powermax/src/unisphere_powermax/rulesets/rulesets.py'
    replace_once(rules, '                "no_cert_check": DictElement(\n', '                "ca_file": DictElement(\n                    parameter_form=String(\n                        title=Title("Custom CA bundle"),\n                        help_text=Help(\n                            "Optional path on the Checkmk server to a PEM CA bundle. "\n                            "It overrides REQUESTS_CA_BUNDLE and CURL_CA_BUNDLE."\n                        ),\n                    ),\n                ),\n                "no_cert_check": DictElement(\n')
    ensure_doc('unisphere_powermax/README.md')


def update_veritas() -> None:
    agent = 'veritas_flex/src/veritas_flex/libexec/agent_veritas'
    ensure_import_os(agent); ensure_helper(agent)
    replace_once(agent, '        self._refresh_token = None\n', '        self._refresh_token = None\n        self.verify: bool | str = True\n')
    replacements = {
        'data=json.dumps(auth), timeout=5, allow_redirects=False': 'data=json.dumps(auth), verify=self.verify, timeout=5, allow_redirects=False',
        'self.session.get(node_url, timeout=10, allow_redirects=False)': 'self.session.get(node_url, verify=self.verify, timeout=10, allow_redirects=False)',
        'self.session.get(instance_url, timeout=10, allow_redirects=False)': 'self.session.get(instance_url, verify=self.verify, timeout=10, allow_redirects=False)',
        'self.session.get(hardware_health_url, timeout=10, allow_redirects=False)': 'self.session.get(hardware_health_url, verify=self.verify, timeout=10, allow_redirects=False)',
        'self.session.get(services_health_url, timeout=10, allow_redirects=False)': 'self.session.get(services_health_url, verify=self.verify, timeout=10, allow_redirects=False)',
        'self.session.post(logout_url, timeout=10, allow_redirects=False)': 'self.session.post(logout_url, verify=self.verify, timeout=10, allow_redirects=False)',
    }
    text = read(agent)
    for old, new in replacements.items():
        if new not in text:
            if old not in text: raise RuntimeError(f'{agent}: missing request pattern {old}')
            text = text.replace(old, new)
    write(agent, text)
    replace_once(agent, "    parser.add_argument('-d', '--debug',\n                        action='store_true')\n", "    parser.add_argument('--ca-file', help='Private CA bundle used for TLS verification')\n    parser.add_argument('--no-cert-check', action='store_true',\n                        help='Explicitly disable TLS verification')\n    parser.add_argument('-d', '--debug',\n                        action='store_true')\n")
    replace_once(agent, "    flex.setup_logging(args.debug)\n    flex.url = f'https://{args.url}/api/'\n", "    flex.setup_logging(args.debug)\n    flex.verify = _resolve_ca_bundle(args.ca_file, args.no_cert_check)\n    flex.url = f'https://{args.url}/api/'\n")
    server = 'veritas_flex/src/veritas_flex/server_side_calls/veritas.py'
    replace_once(server, 'from pydantic import BaseModel\n', 'from typing import Optional\n\nfrom pydantic import BaseModel\n')
    replace_once(server, '    password: Secret\n', '    password: Secret\n    ca_file: Optional[str] = None\n    no_cert_check: bool = False\n')
    replace_once(server, 'def generate_veritas_command(params: VeritasParams, host_config: HostConfig):\n    yield SpecialAgentCommand(\n        command_arguments=(\n            params.api_url,\n            "-u", params.username,\n            "--password-id", params.password,\n        )\n    )\n', 'def generate_veritas_command(params: VeritasParams, host_config: HostConfig):\n    if params.ca_file and params.no_cert_check:\n        raise ValueError("ca_file and no_cert_check are mutually exclusive")\n    arguments: list[str | Secret] = [\n        params.api_url, "-u", params.username, "--password-id", params.password\n    ]\n    if params.ca_file:\n        arguments.extend(("--ca-file", params.ca_file))\n    elif params.no_cert_check:\n        arguments.append("--no-cert-check")\n    yield SpecialAgentCommand(command_arguments=arguments)\n')
    rules = 'veritas_flex/src/veritas_flex/rulesets/agent.py'
    replace_once(rules, '    DefaultValue,\n)', '    DefaultValue,\n    BooleanChoice,\n)')
    replace_once(rules, '            "password": DictElement(\n', '            "ca_file": DictElement(\n                parameter_form=String(\n                    title=Title("Custom CA bundle"),\n                    help_text=Help(\n                        "Optional path on the Checkmk server to a PEM CA bundle. "\n                        "It overrides REQUESTS_CA_BUNDLE and CURL_CA_BUNDLE."\n                    ),\n                    custom_validate=(LengthInRange(min_value=1),),\n                ),\n                required=False,\n            ),\n            "no_cert_check": DictElement(\n                parameter_form=BooleanChoice(\n                    title=Title("Disable TLS certificate verification"),\n                    help_text=Help(\n                        "Temporary compatibility option. Prefer a custom CA bundle."\n                    ),\n                ),\n                required=False,\n            ),\n            "password": DictElement(\n')
    ensure_doc('veritas_flex/README.md')


def update_sms() -> None:
    agent = 'notify_sms_eagle/src/notifications/sms_eagle'
    text = read(agent)
    if 'import os\n' not in text: text = text.replace('import ipaddress\n', 'import ipaddress\nimport os\n', 1)
    if 'from pathlib import Path\n' not in text: text = text.replace('import sys\n', 'import sys\nfrom pathlib import Path\n', 1)
    write(agent, text)
    if 'def _resolve_ca_bundle(' not in read(agent): replace_once(agent, '\ndef _is_loopback(', HELPER + '\n\ndef _is_loopback(')
    replace_once(agent, '            "ssl_verify": _as_bool(context.get("PARAMETER_SSL_VERIFY"), default=True),\n', '            "ssl_verify": _as_bool(context.get("PARAMETER_SSL_VERIFY"), default=True),\n            "ca_file": context.get("PARAMETER_CA_FILE") or None,\n')
    replace_once(agent, '        self.context = context\n        self.session = requests.Session()\n', '        self.config["verify"] = _resolve_ca_bundle(\n            self.config["ca_file"], not self.config["ssl_verify"]\n        )\n        self.context = context\n        self.session = requests.Session()\n')
    replace_once(agent, '                verify=self.config["ssl_verify"],\n', '                verify=self.config["verify"],\n')
    rules = 'notify_sms_eagle/src/sms_eagle/rulesets/notification_parameter.py'
    replace_once(rules, '            "ssl_verify": DictElement(\n', '            "ca_file": DictElement(\n                parameter_form=String(\n                    title=Title("Custom CA bundle"),\n                    help_text=Help(\n                        "Optional path on the Checkmk server to a PEM CA bundle. "\n                        "It overrides REQUESTS_CA_BUNDLE and CURL_CA_BUNDLE."\n                    ),\n                ),\n                required=False,\n            ),\n            "ssl_verify": DictElement(\n')
    ensure_doc('notify_sms_eagle/README.md')


def update_alarms() -> None:
    agent = 'alarms/src/notifications/alarms'
    text = read(agent).replace('from os import environ\n', 'import os\nfrom os import environ\nfrom pathlib import Path\n', 1)
    if 'def _resolve_ca_bundle(' not in text:
        anchor = 'from requests import Session\n'
        if anchor not in text: raise RuntimeError('alarms import anchor missing')
        text = text.replace(anchor, anchor + HELPER + '\n', 1)
    text = text.replace('    API_ALARM = environ.get("NOTIFY_PARAMETER_ALARM", "alarm1")\n', '    API_ALARM = environ.get("NOTIFY_PARAMETER_ALARM", "alarm1")\n    API_CA_FILE = environ.get("NOTIFY_PARAMETER_CA_FILE") or None\n', 1)
    text = text.replace('    session.headers["Accept"] = "application/json"\n', '    session.headers["Accept"] = "application/json"\n    verify = _resolve_ca_bundle(API_CA_FILE, False)\n', 1)
    text = text.replace('        timeout=10,\n        allow_redirects=False,\n', '        timeout=10,\n        verify=verify,\n        allow_redirects=False,\n', 1)
    write(agent, text)
    rules = 'alarms/src/alarms/rulesets/alarms.py'
    replace_once(rules, '            "alarm": DictElement(\n', '            "ca_file": DictElement(\n                parameter_form=String(\n                    title=Title("Custom CA bundle"),\n                    help_text=Help(\n                        "Optional path on the Checkmk server to a PEM CA bundle for HTTPS. "\n                        "It overrides REQUESTS_CA_BUNDLE and CURL_CA_BUNDLE."\n                    ),\n                    field_size=60,\n                ),\n                required=False,\n            ),\n            "alarm": DictElement(\n')
    ensure_doc('alarms/README.md')


def write_policy_test() -> None:
    p('tests/test_ci_private_ca_policy.py').write_text('''from __future__ import annotations\n\nimport ast\nimport os\nfrom pathlib import Path\nimport tempfile\nimport unittest\n\nROOT = Path(__file__).resolve().parents[1]\nAGENTS = [\n    "dell_pmax/src/dell_pmax/libexec/agent_dellpmax",\n    "semu/src/semu/libexec/agent_semu",\n    "spring_boot_actuator/src/spring_boot_actuator/libexec/agent_spring_boot_actuator",\n    "unisphere_powermax/src/unisphere_powermax/libexec/agent_unisphere_powermax",\n    "veritas_flex/src/veritas_flex/libexec/agent_veritas",\n    "notify_sms_eagle/src/notifications/sms_eagle",\n    "alarms/src/notifications/alarms",\n    "hitachi_hnas_rest/src/hitachi_hnas_rest/libexec/agent_hitachi_hnas_rest",\n    "quobyte/src/quobyte/libexec/agent_quobyte",\n]\nCONFIGS = [\n    "dell_pmax/src/dell_pmax/rulesets/agent_dellpmax.py",\n    "semu/src/semu/rulesets/ruleset.py",\n    "spring_boot_actuator/src/spring_boot_actuator/rulesets/spring_boot_actuator.py",\n    "unisphere_powermax/src/unisphere_powermax/rulesets/rulesets.py",\n    "veritas_flex/src/veritas_flex/rulesets/agent.py",\n    "notify_sms_eagle/src/sms_eagle/rulesets/notification_parameter.py",\n    "alarms/src/alarms/rulesets/alarms.py",\n    "hitachi_hnas_rest/src/hitachi_hnas_rest/rulesets/agent.py",\n    "quobyte/src/quobyte/rulesets/agent.py",\n]\n\ndef helper(path: Path):\n    tree = ast.parse(path.read_text(encoding="utf-8"))\n    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_resolve_ca_bundle")\n    namespace = {"os": os, "Path": Path}\n    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), namespace)\n    return namespace["_resolve_ca_bundle"]\n\nclass PrivateCaPolicyTests(unittest.TestCase):\n    def test_all_external_sessions_preserve_ca_fallbacks(self):\n        for relative in AGENTS:\n            text = (ROOT / relative).read_text(encoding="utf-8")\n            with self.subTest(relative=relative):\n                self.assertIn("trust_env = False", text)\n                self.assertIn("REQUESTS_CA_BUNDLE", text)\n                self.assertIn("CURL_CA_BUNDLE", text)\n                self.assertIn("def _resolve_ca_bundle", text)\n\n    def test_rules_expose_custom_ca_bundle(self):\n        for relative in CONFIGS:\n            with self.subTest(relative=relative):\n                self.assertIn("ca_file", (ROOT / relative).read_text(encoding="utf-8"))\n\n    def test_helper_precedence_and_failure_modes(self):\n        old_requests = os.environ.pop("REQUESTS_CA_BUNDLE", None)\n        old_curl = os.environ.pop("CURL_CA_BUNDLE", None)\n        try:\n            for relative in AGENTS:\n                resolve = helper(ROOT / relative)\n                self.assertIs(resolve(None, False), True)\n                self.assertIs(resolve(None, True), False)\n                with self.assertRaises(ValueError): resolve("/tmp/ca.pem", True)\n                with tempfile.TemporaryDirectory() as directory:\n                    base = Path(directory)\n                    explicit, requests, curl = base / "explicit.pem", base / "requests.pem", base / "curl.pem"\n                    for item in (explicit, requests, curl): item.write_text("test", encoding="utf-8")\n                    os.environ["REQUESTS_CA_BUNDLE"] = str(requests)\n                    os.environ["CURL_CA_BUNDLE"] = str(curl)\n                    self.assertEqual(resolve(str(explicit), False), str(explicit.resolve()))\n                    self.assertEqual(resolve(None, False), str(requests.resolve()))\n                    del os.environ["REQUESTS_CA_BUNDLE"]\n                    self.assertEqual(resolve(None, False), str(curl.resolve()))\n                    del os.environ["CURL_CA_BUNDLE"]\n                with self.assertRaises(ValueError): resolve("/definitely/missing/private-ca.pem", False)\n        finally:\n            if old_requests is not None: os.environ["REQUESTS_CA_BUNDLE"] = old_requests\n            else: os.environ.pop("REQUESTS_CA_BUNDLE", None)\n            if old_curl is not None: os.environ["CURL_CA_BUNDLE"] = old_curl\n            else: os.environ.pop("CURL_CA_BUNDLE", None)\n\nif __name__ == "__main__": unittest.main()\n''', encoding='utf-8')


def mark_local_exception() -> None:
    path = 'service_counter/src/service_counter/libexec/agent_service_counter'
    text = read(path)
    marker = '        self._session.trust_env = False\n'
    replacement = '        # Local-only HTTP call to the site API: no TLS CA policy applies.\n        self._session.trust_env = False\n'
    if replacement not in text:
        if marker not in text: raise RuntimeError('local service counter marker missing')
        write(path, text.replace(marker, replacement, 1))


def main() -> None:
    update_dell(); update_semu(); update_spring(); update_unisphere(); update_veritas(); update_sms(); update_alarms()
    write_policy_test(); mark_local_exception()
    print('Applied consistent private-CA policy')


if __name__ == '__main__':
    main()
