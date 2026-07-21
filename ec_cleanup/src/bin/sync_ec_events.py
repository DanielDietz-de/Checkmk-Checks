#!/usr/bin/env python3
"""Safely reconcile Checkmk Event Console events with current host/service state."""

from __future__ import annotations

import argparse
import ipaddress
import json
import sys
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from os import environ
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit

import requests
import urllib3


@dataclass(frozen=True)
class EventCandidate:
    event_id: int
    site_id: str
    host_name: str
    service_description: str


class CheckmkApiError(RuntimeError):
    """Raised when the Checkmk REST API cannot complete an operation."""


def _is_loopback_host(hostname: str | None) -> bool:
    if hostname is None:
        return False
    if hostname.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


def validate_local_site_url(address: str, site: str) -> None:
    parsed = urlsplit(address)
    if parsed.scheme not in {"http", "https"}:
        raise RuntimeError("local site URL must use http or https")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise RuntimeError("local site URL must not contain credentials, a query, or a fragment")
    if not _is_loopback_host(parsed.hostname):
        raise RuntimeError(
            "the local automation secret may only be sent to localhost or a loopback address"
        )
    if parsed.path.rstrip("/") != f"/{site}":
        raise RuntimeError(f"local automation credentials require the local site path /{site}")


class Checkmk:
    def __init__(self, config: dict[str, Any]):
        self.address = str(config["address"]).rstrip("/")
        self.username = str(config["username"])
        self.password = str(config["password"])
        self.rule_filter = str(config["rule_filter"])
        self.verify = bool(config["verify"])
        self.timeout = float(config.get("timeout", 15.0))
        self.status_cache: dict[tuple[str, str], int | None] = {}
        self.session = requests.Session()
        self.session.trust_env = bool(config.get("trust_env", True))
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.username} {self.password}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )
        if not self.verify:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def _url(self, endpoint: str) -> str:
        return f"{self.address}/check_mk/api/1.0/{endpoint.lstrip('/')}"

    def request_json(
        self,
        endpoint: str,
        *,
        method: str = "GET",
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
        expected_statuses: Iterable[int] = (200,),
    ) -> dict[str, Any]:
        try:
            response = self.session.request(
                method,
                self._url(endpoint),
                params=params,
                json=payload,
                verify=self.verify,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise CheckmkApiError(f"Checkmk API request failed: {exc}") from exc

        expected = set(expected_statuses)
        if response.status_code not in expected:
            detail = response.text.strip()
            if len(detail) > 500:
                detail = detail[:500] + "..."
            raise CheckmkApiError(
                f"Checkmk API returned HTTP {response.status_code} for {endpoint}: "
                f"{detail or 'no response body'}"
            )

        if not response.content:
            return {}
        try:
            data = response.json()
        except ValueError as exc:
            raise CheckmkApiError(f"Checkmk API returned invalid JSON for {endpoint}") from exc
        if not isinstance(data, dict):
            raise CheckmkApiError(f"Checkmk API returned a non-object JSON response for {endpoint}")
        return data

    def get_events(self) -> list[EventCandidate]:
        query = {"op": "=", "left": "event_rule_id", "right": self.rule_filter}
        data = self.request_json(
            "domain-types/event_console/collections/all",
            params={"query": json.dumps(query, separators=(",", ":")), "phase": "open"},
        )
        values = data.get("value", [])
        if not isinstance(values, list):
            raise CheckmkApiError("Event Console response has no valid value list")

        events: list[EventCandidate] = []
        for raw_event in values:
            if not isinstance(raw_event, dict):
                continue
            extensions = raw_event.get("extensions")
            if not isinstance(extensions, dict):
                continue
            try:
                events.append(
                    EventCandidate(
                        event_id=int(raw_event["id"]),
                        site_id=str(extensions["site_id"]),
                        host_name=str(extensions["host"]),
                        service_description=str(extensions["application"]),
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
        return events

    def get_service_state(self, host_name: str, service_description: str) -> int | None:
        cache_id = (host_name, service_description)
        if cache_id in self.status_cache:
            return self.status_cache[cache_id]

        endpoint = f"objects/host/{quote(host_name, safe='')}/actions/show_service/invoke"
        try:
            data = self.request_json(
                endpoint,
                params={"service_description": service_description, "columns": "state"},
            )
        except CheckmkApiError:
            self.status_cache[cache_id] = None
            return None
        extensions = data.get("extensions")
        state = extensions.get("state") if isinstance(extensions, dict) else None
        try:
            parsed = int(state)
        except (TypeError, ValueError):
            parsed = None
        self.status_cache[cache_id] = parsed
        return parsed

    def get_host_state(self, host_name: str) -> int | None:
        cache_id = (host_name, "HOST")
        if cache_id in self.status_cache:
            return self.status_cache[cache_id]

        endpoint = f"objects/host/{quote(host_name, safe='')}"
        try:
            data = self.request_json(endpoint, params={"columns": "state"})
        except CheckmkApiError:
            self.status_cache[cache_id] = None
            return None
        extensions = data.get("extensions")
        state = extensions.get("state") if isinstance(extensions, dict) else None
        try:
            parsed = int(state)
        except (TypeError, ValueError):
            parsed = None
        self.status_cache[cache_id] = parsed
        return parsed

    def close_event(self, event_id: int, site_id: str) -> None:
        self.request_json(
            "domain-types/event_console/actions/delete/invoke",
            method="POST",
            payload={
                "filter_type": "by_id",
                "event_id": event_id,
                "site_id": site_id,
            },
            expected_statuses=(200, 204),
        )

    def find_candidates(self) -> list[EventCandidate]:
        candidates: list[EventCandidate] = []
        for event in self.get_events():
            if event.service_description == "HOST":
                state = self.get_host_state(event.host_name)
            else:
                state = self.get_service_state(event.host_name, event.service_description)

            description = f"{event.host_name}, {event.service_description}"
            if state is None:
                print(f"NOT FOUND -> ID {event.event_id} ({description})")
            elif state == 0:
                print(f"OK -> ID {event.event_id} ({description})")
                candidates.append(event)
            else:
                print(f"ACTIVE -> ID {event.event_id} ({description}), state {state}")
        return candidates

    def sync_ec_data(
        self,
        *,
        execute: bool,
        assume_yes: bool = False,
        input_fn: Callable[[str], str] = input,
    ) -> int:
        candidates = self.find_candidates()
        if not candidates:
            print("No Event Console events are eligible for cleanup.")
            return 0

        print(f"{len(candidates)} event(s) are eligible for cleanup.")
        if not execute:
            print("Dry run only. Re-run with --execute to archive these events.")
            return 0

        if not assume_yes:
            confirmation = input_fn(
                f"Type DELETE {len(candidates)} to archive exactly these events: "
            ).strip()
            if confirmation != f"DELETE {len(candidates)}":
                print("Confirmation did not match; no events were changed.")
                return 1

        failures = 0
        for event in candidates:
            try:
                self.close_event(event.event_id, event.site_id)
                print(f"Archived event ID {event.event_id} on site {event.site_id}")
            except CheckmkApiError as exc:
                failures += 1
                print(f"Failed to archive event ID {event.event_id}: {exc}", file=sys.stderr)
        return 2 if failures else 0


def get_automation_password() -> str:
    omd_root = environ.get("OMD_ROOT")
    if not omd_root:
        raise RuntimeError("OMD_ROOT is not set; provide --user and --password explicitly")
    secret_path = Path(omd_root) / "var/check_mk/web/automation/automation.secret"
    return secret_path.read_text(encoding="utf-8").strip()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Archive open Event Console events whose Checkmk host or service is already OK"
    )
    parser.add_argument("--user", help="Checkmk API username")
    parser.add_argument("--rule-filter", required=True, help="Event Console rule ID to inspect")
    parser.add_argument("--password", help="Password or automation secret")
    parser.add_argument("--site-url", help="Checkmk site URL, for example https://host/site")
    parser.add_argument("--timeout", type=float, default=15.0, help="API timeout in seconds")
    parser.add_argument("--no-verify", action="store_true", help="Disable TLS verification")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Archive eligible events; without this flag the script is read-only",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the exact confirmation prompt; requires --execute",
    )
    args = parser.parse_args(argv)
    if args.yes and not args.execute:
        parser.error("--yes requires --execute")
    if args.timeout <= 0:
        parser.error("--timeout must be greater than zero")
    if bool(args.user) != bool(args.password):
        parser.error("--user and --password must be provided together")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    site = environ.get("OMD_SITE")

    if args.site_url:
        address = args.site_url.rstrip("/")
        verify = not args.no_verify
    else:
        if not site:
            raise RuntimeError("OMD_SITE is not set; provide --site-url")
        address = f"http://localhost/{site}"
        verify = False

    if args.user:
        user = args.user
        password = args.password
        trust_env = True
    else:
        if not site:
            raise RuntimeError(
                "OMD_SITE is not set; explicit --user and --password are required for a remote URL"
            )
        validate_local_site_url(address, site)
        user = "automation"
        password = get_automation_password()
        trust_env = False

    cmk = Checkmk(
        {
            "address": address,
            "username": user,
            "password": password,
            "verify": verify,
            "rule_filter": args.rule_filter,
            "timeout": args.timeout,
            "trust_env": trust_env,
        }
    )
    return cmk.sync_ec_data(execute=args.execute, assume_yes=args.yes)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (CheckmkApiError, OSError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
