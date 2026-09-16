#!/usr/bin/env python3
"""Graphing definitions for Synology M365 metrics.

The initial framework emits metrics from the check plug-in. Explicit metric and
combined-graph registrations will be added after the first real NAS payload has
been accepted so units, ranges, and labels are based on observed data.
"""
