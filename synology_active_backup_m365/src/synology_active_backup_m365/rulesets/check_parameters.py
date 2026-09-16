#!/usr/bin/env python3
"""Future service-parameter rules for Synology M365 backup jobs.

Threshold rules for last-success age, runtime, skipped items, no-data behavior,
and expected task IDs will be registered after the first live API payload has
been validated. Keeping this module in the framework fixes the package layout
without prematurely declaring production threshold semantics.
"""
