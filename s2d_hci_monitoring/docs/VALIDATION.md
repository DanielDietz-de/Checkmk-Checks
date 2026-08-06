# Validation and release evidence

## Automated package tests

The package-specific tests validate:

- canonical manifest identity, compatibility, duplicate detection, and file existence;
- preservation of the package-specific license;
- cluster node and drain-state mapping;
- CSV metrics and virtual-disk failure handling;
- storage-job state, progress metrics, and malformed percentage input;
- unsupported health cmdlet behavior;
- Hyper-V host module availability;
- workload state, CPU, and memory-pressure metrics;
- integration service, replication, virtual NIC, and differencing-disk behavior.

Run focused tests from the repository root:

```bash
python3 -m pytest -q s2d_hci_monitoring/tests
```

The repository also collects all package tests together and runs each package independently to detect import and fixture isolation problems.

## Repository gates

The normal Checkmk-Checks CI must validate at least:

```bash
python3 tools/ci/sync_repository_facts.py
python3 tools/ci/sync_package_metadata.py
python3 tools/ci/generate_package_reference.py
python3 tools/ci/manage_module_docstrings.py
python3 tools/ci/check_python_syntax.py
python3 tools/ci/full_repository_audit.py --fail-on low
python3 -m pytest -q s2d_hci_monitoring/tests
```

The affected-package workflow then builds a deterministic MKP, verifies its file inventory and checksum, and loads the package in clean Checkmk 2.5 validation sites. Checkmk 2.4 is intentionally outside this package’s compatibility range.

## Required live validation

Automated tests do not reproduce every Microsoft object type or operating-system build. Before production rollout, validate on representative systems containing the roles that will be monitored.

### Cluster state

- healthy and down node;
- paused or draining node;
- quorum resource present and absent;
- cluster network and interface state;
- offline cluster group or resource.

### Storage

- healthy CSV with known free percentage;
- free-space threshold crossing;
- healthy and degraded pool or virtual disk;
- detached virtual disk;
- physical disk warning or failure state;
- active, completed, suspended, and failed storage job;
- unavailable optional storage-health cmdlet.

### Hyper-V

- running and intentionally off VM;
- dynamic and static memory VM;
- high CPU or memory pressure threshold crossing;
- healthy and unhealthy integration service;
- replication enabled and not enabled;
- retained checkpoint with known age;
- disconnected virtual NIC;
- differencing disk with parent chain;
- collector execution under the intended gMSA.

## Acceptance criteria

A release candidate is acceptable when:

- all repository and package checks pass;
- the MKP inventory exactly matches `src/info`;
- all plug-ins register in the declared Checkmk releases;
- raw Windows output contains valid, bounded sections;
- no collector changes monitored state;
- service discovery is stable and duplicate-free;
- state mappings match documented operator expectations;
- metrics have correct names and units;
- expensive collectors fit timeout and cache budgets;
- gMSA spool output expires when the task stops;
- rollback has been tested or is operationally credible.

## Evidence recording

Record the following in the deployment change or release record:

- package version, source commit, MKP checksum, and Checkmk version;
- Windows Server builds and installed roles tested;
- collector runtime and output size per script;
- identity and permissions used for each collection path;
- representative services and state transitions observed;
- known unsupported cmdlets or features;
- rollback package and host-side file versions.

Do not commit production output or sensitive screenshots to the public repository.
