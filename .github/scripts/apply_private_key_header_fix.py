#!/usr/bin/env python3
"""Apply the reviewed broad PEM private-key header remediation."""

from pathlib import Path


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"expected exactly one {label} block in {path}")
    path.write_text(text.replace(old, new), encoding="utf-8")


audit_path = Path("tools/ci/full_repository_audit.py")
replace_once(
    audit_path,
    '''PRIVATE_KEYS = (
    "-----BEGIN " + "PRIVATE KEY-----",
    "-----BEGIN RSA " + "PRIVATE KEY-----",
    "-----BEGIN OPENSSH " + "PRIVATE KEY-----",
    "-----BEGIN EC " + "PRIVATE KEY-----",
)
''',
    '''PRIVATE_KEY_HEADER_RE = re.compile(
    r"-----BEGIN (?:(?:[A-Z0-9]+(?:[ -][A-Z0-9]+)*) )?PRIVATE KEY-----"
)
''',
    "private-key marker definition",
)
replace_once(
    audit_path,
    '''    for marker in PRIVATE_KEYS:
        if marker in text:
            line = text[: text.index(marker)].count("\\n") + 1
            result.append(
                finding(
                    "critical",
                    "security.private-key-material",
                    root,
                    path,
                    line,
                    "private-key material appears to be committed",
                    "revoke and remove the key from history",
                )
            )
''',
    '''    for match in PRIVATE_KEY_HEADER_RE.finditer(text):
        line = text[: match.start()].count("\\n") + 1
        result.append(
            finding(
                "critical",
                "security.private-key-material",
                root,
                path,
                line,
                "private-key material appears to be committed",
                "revoke and remove the key from history",
            )
        )
''',
    "private-key scan loop",
)

test_path = Path("tests/test_ci_full_repository_audit.py")
replace_once(
    test_path,
    '''    def test_benign_binary_file_is_scanned_without_false_positive(self):
''',
    '''    def test_detects_encrypted_and_dsa_private_key_headers(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_root(temporary)
            key_directory = root / "certificates"
            key_directory.mkdir(parents=True)
            encrypted = key_directory / "encrypted.pem"
            encrypted.write_text(
                "-----BEGIN " + "ENCRYPTED PRIVATE KEY-----\\nredacted\\n",
                encoding="utf-8",
            )
            dsa = key_directory / "legacy-dsa.key"
            dsa.write_text(
                "-----BEGIN " + "DSA PRIVATE KEY-----\\nredacted\\n",
                encoding="utf-8",
            )

            report = audit.build_report(root, set())
            credential_findings = {
                (item["path"], item["rule_id"])
                for item in report["findings"]
            }
            self.assertIn(
                ("certificates/encrypted.pem", "security.private-key-material"),
                credential_findings,
            )
            self.assertIn(
                ("certificates/legacy-dsa.key", "security.private-key-material"),
                credential_findings,
            )

    def test_benign_binary_file_is_scanned_without_false_positive(self):
''',
    "private-key header regression tests",
)
