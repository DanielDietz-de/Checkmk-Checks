# Support

## Operational questions and defects

Use a GitHub issue for reproducible installation, configuration, compatibility, discovery, check-result, packaging, or documentation problems.

Include:

- package name and version;
- Checkmk edition and exact version;
- installation method;
- relevant rule configuration with all secrets removed;
- expected and actual behavior;
- sanitized agent, special-agent, SNMP, or Checkmk diagnostic output;
- reproducible steps;
- whether the problem occurs in a clean test site;
- recent package or Checkmk upgrades.

Do not include credentials, private keys, bearer tokens, authorization headers, customer data, internal inventories, full production URLs, or unsanitized configuration backups.

## Security reports

Do not use a public support issue for a vulnerability. Follow [`SECURITY.md`](SECURITY.md).

## Compatibility

The package metadata and README define supported Checkmk versions. A package outside its declared range may fail to load, register, discover, parse, or produce correct states. Such use is unsupported until the package is deliberately ported and validated.

Vendor firmware, API, MIB, and operating-system differences can affect behavior even inside a declared Checkmk range. Provide sanitized representative data when reporting such a defect.

## Scope of support

This repository is community-maintained and has no guaranteed response or resolution time. Package-specific operational guidance, tests, and current workflow results are the primary evidence available to users.
