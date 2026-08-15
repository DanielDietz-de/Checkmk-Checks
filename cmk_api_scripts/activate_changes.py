#!/usr/bin/env python3
"""Activate pending Checkmk changes through the supported REST API.

Credentials are read from environment variables or an interactive prompt. The
script never stores automation secrets in source code or accepts them on the
command line, where other local users could inspect them.
"""

from __future__ import annotations

import argparse
import getpass
import ipaddress
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

import requests

DEFAULT_TIMEOUT = 30.0
MAX_ERROR_BODY = 1_000


class CheckmkApiError(RuntimeError):
    """Raised when the Checkmk REST API returns an unusable response."""


def _is_loopback(hostname: str | None) -> bool:
    """Handle is loopback for this module's workflow."""
    if hostname is None:
        return False
    if hostname.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


def validate_site_url(value: str, *, allow_http: bool = False) -> tuple[str, str]:
    """Return a normalized site URL and site ID after enforcing trust boundaries."""
    parsed = urlsplit(value.rstrip("/"))
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("site URL must use http or https")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("site URL must not contain credentials, a query, or a fragment")
    if not parsed.hostname:
        raise ValueError("site URL must include a host")
    path_parts = [part for part in parsed.path.split("/") if part]
    if len(path_parts) != 1:
        raise ValueError("site URL must end with exactly one Checkmk site ID")
    if parsed.scheme == "http" and not (_is_loopback(parsed.hostname) or allow_http):
        raise ValueError("remote Checkmk API access requires HTTPS; use --allow-http deliberately")
    return value.rstrip("/"), path_parts[0]


def _bounded_detail(response: requests.Response) -> str:
    """Handle bounded detail for this module's workflow."""
    text = response.text.strip().replace("\r", " ").replace("\n", " ")
    if len(text) > MAX_ERROR_BODY:
        text = text[:MAX_ERROR_BODY] + "..."
    return text or "no response body"


class CheckmkClient:
    """Minimal bounded client for pending-change activation."""

    def __init__(
        self,
        site_url: str,
        username: str,
        secret: str,
        *,
        verify: bool | str = True,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize the instance and its required state."""
        self.api_url = f"{site_url}/check_mk/api/1.0"
        self.timeout = timeout
        self.verify = verify
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {username} {secret}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

    def request(
        self,
        method: str,
        endpoint: str,
        *,
        expected: set[int],
        headers: dict[str, str] | None = None,
        payload: dict[str, object] | None = None,
    ) -> requests.Response:
        """Send one non-redirecting API request and enforce expected status codes."""
        try:
            response = self.session.request(
                method,
                f"{self.api_url}/{endpoint.lstrip('/')}",
                headers=headers,
                json=payload,
                timeout=self.timeout,
                verify=self.verify,
                allow_redirects=False,
            )
        except requests.RequestException as exc:
            raise CheckmkApiError(f"Checkmk API request failed: {exc}") from exc
        if response.status_code not in expected:
            raise CheckmkApiError(
                f"Checkmk API returned HTTP {response.status_code}: {_bounded_detail(response)}"
            )
        return response

    def pending_changes(self) -> tuple[list[object], str | None]:
        """Return pending changes and their concurrency ETag."""
        response = self.request(
            "GET",
            "domain-types/activation_run/collections/pending_changes",
            expected={200},
        )
        try:
            body = response.json()
        except ValueError as exc:
            raise CheckmkApiError("pending-changes response is not valid JSON") from exc
        changes = body.get("value") if isinstance(body, dict) else None
        if not isinstance(changes, list):
            raise CheckmkApiError("pending-changes response has no value list")
        return changes, response.headers.get("ETag")

    def activate(self, *, site: str, etag: str, force_foreign_changes: bool) -> str:
        """Start an activation run and return its identifier."""
        response = self.request(
            "POST",
            "domain-types/activation_run/actions/activate-changes/invoke",
            expected={200, 201, 202},
            headers={"If-Match": etag},
            payload={
                "redirect": False,
                "force_foreign_changes": force_foreign_changes,
                "sites": [site],
            },
        )
        try:
            body = response.json()
        except ValueError as exc:
            raise CheckmkApiError("activation response is not valid JSON") from exc
        activation_id = body.get("id") if isinstance(body, dict) else None
        if not isinstance(activation_id, str) or not activation_id:
            raise CheckmkApiError("activation response has no activation ID")
        return activation_id

    def wait(self, activation_id: str) -> None:
        """Wait for the activation run to finish successfully."""
        self.request(
            "GET",
            f"objects/activation_run/{activation_id}/actions/wait-for-completion/invoke",
            expected={200, 204},
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse args into its normalized representation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-url", default=os.environ.get("CHECKMK_SITE_URL"))
    parser.add_argument("--user", default=os.environ.get("CHECKMK_USER"))
    parser.add_argument("--site", help="Target site ID; defaults to the site URL path")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--ca-file", type=Path, help="Private CA bundle for TLS verification")
    parser.add_argument("--no-verify", action="store_true", help="Deliberately disable TLS checks")
    parser.add_argument("--allow-http", action="store_true", help="Allow clear-text HTTP remotely")
    parser.add_argument("--force-foreign-changes", action="store_true")
    args = parser.parse_args(argv)
    if not args.site_url:
        parser.error("--site-url or CHECKMK_SITE_URL is required")
    if not args.user:
        parser.error("--user or CHECKMK_USER is required")
    if args.timeout <= 0:
        parser.error("--timeout must be greater than zero")
    if args.ca_file and args.no_verify:
        parser.error("--ca-file and --no-verify are mutually exclusive")
    return args


def main(argv: list[str] | None = None) -> int:
    """Run the command-line entry point and return its result."""
    args = parse_args(argv)
    site_url, inferred_site = validate_site_url(args.site_url, allow_http=args.allow_http)
    site = args.site or inferred_site
    secret = os.environ.get("CHECKMK_SECRET") or getpass.getpass("Checkmk automation secret: ")
    if not secret:
        raise ValueError("automation secret must not be empty")
    verify: bool | str = False if args.no_verify else str(args.ca_file) if args.ca_file else True
    client = CheckmkClient(site_url, args.user, secret, verify=verify, timeout=args.timeout)
    changes, etag = client.pending_changes()
    if not changes:
        print("No pending changes.")
        return 0
    if not etag:
        raise CheckmkApiError("pending-changes response has no ETag")
    activation_id = client.activate(
        site=site,
        etag=etag,
        force_foreign_changes=args.force_foreign_changes,
    )
    client.wait(activation_id)
    print(f"Activated {len(changes)} pending change(s) on site {site}.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (CheckmkApiError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
