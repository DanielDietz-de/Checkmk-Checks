# Miscellaneous development utilities

This directory contains non-package helper material. It is not installed by an
MKP and is not part of a supported package API.

Current executable helpers:

- `convert_snmpwalk_to_cmk.py` — converts SNMP walk data for Checkmk development.
- `downtime_with_childs.sh` — legacy downtime helper.
- `feiertage.py` — holiday-data helper.
- `magic_factor_calc.py` — calculation helper.
- `problem_history/local_check.py` — local-check example.
- `skeleton/snmp_check.py` — parseable SNMP check skeleton.

No utility may contain credentials or production endpoints. Security-sensitive
API automation belongs in `cmk_api_scripts/`, where credentials are supplied at
runtime and requests use explicit transport boundaries.
