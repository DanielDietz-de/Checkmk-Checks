#!/usr/bin/env python3
"""Finalize the shared private-CA policy for integrations already using a fallback."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "quobyte/src/quobyte/libexec/agent_quobyte"

text = PATH.read_text(encoding="utf-8")
old = '''def _resolve_ca_bundle(explicit_ca_file: str | None) -> str | bool:
    """Resolve explicit or site-wide CA trust without enabling proxy inheritance."""
    configured = (
        explicit_ca_file
        or os.environ.get("REQUESTS_CA_BUNDLE")
        or os.environ.get("CURL_CA_BUNDLE")
    )
    if not configured:
        return True

    path = Path(configured).expanduser()
    if not path.is_file():
        raise ValueError(f"CA bundle does not exist or is not a file: {path}")
    return str(path.resolve())
'''
new = '''def _resolve_ca_bundle(
    explicit_ca_file: str | None, no_cert_check: bool = False
) -> str | bool:
    """Resolve explicit or site-wide CA trust without enabling proxy inheritance."""
    if explicit_ca_file and no_cert_check:
        raise ValueError("--ca-file and --no-cert-check are mutually exclusive")
    if no_cert_check:
        return False

    configured = (
        explicit_ca_file
        or os.environ.get("REQUESTS_CA_BUNDLE")
        or os.environ.get("CURL_CA_BUNDLE")
    )
    if not configured:
        return True

    path = Path(configured).expanduser()
    if not path.is_file():
        raise ValueError(f"CA bundle does not exist or is not a file: {path}")
    return str(path.resolve())
'''
if new not in text:
    if old not in text:
        raise RuntimeError("Quobyte CA helper did not match the expected implementation")
    text = text.replace(old, new, 1)

old_request = '''            auth=self.auth,
            timeout=self.timeout,
            allow_redirects=False,
'''
new_request = '''            auth=self.auth,
            verify=self.session.verify,
            timeout=self.timeout,
            allow_redirects=False,
'''
if new_request not in text:
    if old_request not in text:
        raise RuntimeError("Quobyte request did not match the expected implementation")
    text = text.replace(old_request, new_request, 1)

PATH.write_text(text, encoding="utf-8")
print("Finalized Quobyte private-CA policy")
