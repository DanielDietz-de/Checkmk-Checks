# Security model

## Privilege boundary

The package monitors local Windows cluster, storage, and Hyper-V state. The collectors must remain read-only and should run with the minimum identity capable of querying the applicable Microsoft cmdlets.

Do not solve a permission problem by granting domain administrator, enterprise administrator, cluster administrator, local administrator, or unrestricted Hyper-V administrator membership without a documented and reviewed necessity.

## Collector restrictions

Packaged collectors must not contain or invoke state-changing operations such as:

- cluster, storage, VM, virtual switch, checkpoint, replication, service, registry, firewall, or operating-system configuration changes;
- software installation or update operations;
- remote PowerShell sessions;
- dynamic expression evaluation;
- credential retrieval, storage, or transmission;
- arbitrary external command paths derived from collector data.

Operational installation tools are intentionally mutating but must support review and `ShouldProcess`, constrain paths, and never handle a password.

## Secret handling

The package requires no Checkmk password-store field and no network credential. The JSON spool configuration contains only local paths and a path-confinement flag. Never add passwords, tokens, private keys, certificates, domain secrets, or account recovery material to source, rules, JSON, agent output, or fixtures.

The gMSA path uses the Windows Scheduled Tasks `ServiceAccount` logon type and therefore does not store an account password in the task or package.

## Filesystem controls

Recommended principles:

- administrators and the trusted deployment system own package deployment;
- ordinary users cannot modify collector, wrapper, or configuration files;
- the gMSA can read/execute required scripts and write only within the spool directory;
- the Checkmk agent can read spool output;
- inheritance is reviewed rather than assumed;
- symbolic links or reparse points are not used to escape the protected agent root.

The spool wrapper canonicalizes paths and requires them to remain below the Checkmk agent and spool roots. Keep `require_paths_under_agent_root` enabled.

## Data sensitivity

Agent output may include:

- cluster, node, network, VM, and virtual switch names;
- IP addresses and MAC addresses;
- disk serial numbers, identifiers, and firmware;
- local or cluster storage paths;
- replication peer names;
- capacity and performance details.

Treat raw output and support bundles as infrastructure-sensitive. Sanitize them before public disclosure and delete temporary copies after use.

## Input validation

Checkmk parsers treat every collector row as untrusted input. They parse JSON, ignore malformed rows, handle invalid numeric values without exceptions, and map unknown state strings to UNKNOWN. They do not execute data, construct shell commands, or perform network requests.

## Supply chain and packaging

The target repository’s CI is authoritative for deterministic MKP construction, syntax validation, documentation synchronization, package registration, security auditing, and clean-site Checkmk validation. Do not distribute a locally built package without reproducing these gates and generating a matching SHA-256 checksum.

The package-specific PolyForm Internal Use license must remain present in the package directory and be reviewed before redistribution.

## Security review checklist

For every change:

1. verify collectors remain read-only;
2. review new cmdlets and .NET calls for side effects;
3. verify path inputs remain canonicalized and confined;
4. confirm no secret or sensitive fixture was added;
5. add malformed-input and state-mapping tests;
6. review agent output for unnecessary sensitive fields;
7. run repository security and documentation gates;
8. validate under the actual least-privilege identity.

Report vulnerabilities through the root repository’s private security-reporting process, not a public issue.
