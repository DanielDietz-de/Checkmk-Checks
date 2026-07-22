#!/usr/bin/env python3
# Copyright (C) 2026 Kuhn & Rueß GmbH - License: GNU General Public License v2
#
# Override of the built-in ``cmk.plugins.lib.cisco_ucs`` detection.
#
# The upstream module gates all cisco_ucs_* checks (v2 and legacy) behind a
# fixed whitelist of sysObjectIDs (.1.3.6.1.2.1.1.2.0). Standalone Cisco IMC
# (CIMC) appliance servers and newer UCS C-series models -- e.g. SNS-8355-K9 /
# UCS C225 M8 -- report a sysObjectID that is not on that list, so none of the
# cisco_ucs_* services get discovered even though the device fully serves the
# CISCO-UNIFIED-COMPUTING-MIB (.1.3.6.1.4.1.9.9.719).
#
# This shadowing module lives at the same namespace path under ~/local and is
# therefore imported instead of the built-in one. It loads the genuine upstream
# module by file location, re-exports every public symbol unchanged, and only
# broadens DETECT so it additionally matches any device that exposes the UCS
# compute rack-unit table. Loading upstream dynamically (instead of copying its
# code) keeps Operability/Presence/Fault/... in sync across Checkmk updates.
import importlib.util as _ilu
import os as _os

import cmk.plugins.lib as _pkg
from cmk.agent_based.v2 import any_of as _any_of, exists as _exists

_here = _os.path.realpath(_os.path.dirname(__file__))
_upstream_src = None
for _entry in _pkg.__path__:
    if _os.path.realpath(_entry) == _here:
        continue  # skip this local override directory
    _candidate = _os.path.join(_entry, "cisco_ucs.py")
    if _os.path.isfile(_candidate):
        _upstream_src = _candidate
        break
if _upstream_src is None:
    raise ImportError("cisco_ucs override: built-in cisco_ucs.py not found")

_spec = _ilu.spec_from_file_location("cmk.plugins.lib._cisco_ucs_upstream", _upstream_src)
_upstream = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_upstream)

# Re-export everything public from upstream (Operability, Presence, Fault,
# FaultSeverity, check_cisco_fault, ...) so all importers keep working.
for _name in dir(_upstream):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_upstream, _name)

# Broadened detection: keep the upstream sysObjectID whitelist, and additionally
# match any device that serves the UCS compute rack-unit operability column
# (cucsComputeRackUnitOperability) -- standalone CIMC / C-series appliances.
DETECT = _any_of(
    _upstream.DETECT,
    _exists(".1.3.6.1.4.1.9.9.719.1.9.35.1.43.*"),
)
