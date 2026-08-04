# Additional Azure Monitoring

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.4.0p18-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.4.0p18-blue)
<!-- compatibility-badges:end -->

Complementary special agent for Azure networking resources. Runs standalone or alongside the built-in Checkmk Azure integration and emits piggyback sections so extra services appear on the same hosts.

Covered resource types:

- Azure Firewalls (main, IP configs, rule collections, policies)
- Virtual Network Gateways (main, IP configs, BGP, VPN clients, remote peerings)
- Virtual Network Gateway Connections
- Virtual Networks (main, subnets, peerings)

## How it works

The special agent [`agent_azure_extra`](src/azure_extra/libexec/agent_azure_extra) authenticates against `login.microsoftonline.com` using a client credentials flow, enumerates resource groups via the Azure Resource Manager REST API, and then iterates over the supported resource types (see `RESOURCE_CONFIGS`). For each discovered resource it emits piggyback output (`<<<<<resource_name>>>>`) containing a JSON blob under section headers such as `<<<azure_extra_azurefirewalls:sep(0)>>>`, `<<<azure_extra_virtualnetworks:sep(0)>>>`, `<<<azure_extra_virtualnetworkgateways:sep(0)>>>` and `<<<azure_extra_connections:sep(0)>>>`.

The agent based plugins parse the JSON and create services based on `provisioningState`, SKU, BGP state, peering state, rule counts, etc. `Succeeded` maps to OK, `Failed` / `Canceled` to CRIT, anything else to WARN.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/azure_extra/libexec/agent_azure_extra` | Special agent script (REST client for Azure ARM). |
| `src/azure_extra/rulesets/agent.py` | WATO special agent rule. |
| `src/azure_extra/server_side_calls/agent.py` | Builds the command line for the special agent. |
| `src/azure_extra/agent_based/azure_extra_azurefirewalls.py` | Services for firewalls, IP configs, rule collections, policies. |
| `src/azure_extra/agent_based/azure_extra_virtualnetworks.py` | Services for virtual networks, subnets, peerings. |
| `src/azure_extra/agent_based/azure_extra_virtualnetworkgateways.py` | Services for VPN gateways, BGP, VPN clients, peerings. |
| `src/azure_extra/agent_based/azure_extra_connections.py` | Services for VPN gateway connections. |

## Installation

1. Install the MKP on the Checkmk site.
2. Create an Azure App Registration with read access on the relevant subscription (Reader role is typically sufficient for ARM metadata).
3. Create a dedicated host for the Azure tenant and attach the rule *KR Azure Extra* under *Setup -> Agents -> Other integrations*.
4. Make sure the Checkmk site can reach `login.microsoftonline.com` and `management.azure.com` (use the proxy option if required).

## Configuration

Rule: **Setup -> Agents -> Other integrations -> KR Azure Extra**

| Parameter | Type | Meaning |
| --- | --- | --- |
| `tenant_id` | String | Azure Active Directory tenant ID. |
| `client_id` | String | App registration client ID. |
| `client_secret` | Password | App registration client secret. |
| `subscription_id` | String | Subscription to enumerate. |
| `proxy_url` | String (optional) | HTTP(S) proxy URL. |

## Services & metrics

Examples of service name patterns created by the check plugins:

- `Azure Firewall %s`, `Azure Firewall IP Config %s`, `Azure Firewall Rule Collection %s`, `Azure Firewall Policy %s`
- `Azure VNet %s`, `Azure VNet Subnet %s`, `Azure VNet Peering %s`
- `Azure VNet Gateway %s`, `Azure VNet Gateway BGP %s`, `Azure VNet Gateway VPN Client %s`, `Azure VNet Gateway Remote Peering %s`
- `Azure Connection %s`

State is derived from `provisioningState` and resource specific fields; these checks currently do not report numeric metrics.

## Known limitations

- Metric collection (`microsoft.insights/metrics`) is defined in the agent but commented out; only ARM property data is shipped.
- Hosts are identified via piggyback using Azure resource names, so they must exist as Checkmk hosts (or be auto-created) for services to appear.

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `azure_extras` version `1.3.0`; minimum Checkmk version `2.4.0p18`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `azure_extras/src/info`; it declares 10 packaged files.
- Repository MKP artifacts present: `azure_extras-1.0.0.mkp`, `azure_extras-1.0.1.mkp`, `azure_extras-1.2.0.mkp`, `azure_extras-1.3.0.mkp`.
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Agent-based checks:** `src/azure_extra/agent_based/azure_extra_azurefirewalls.py`, `src/azure_extra/agent_based/azure_extra_connections.py`, `src/azure_extra/agent_based/azure_extra_dnsresolvers.py`, `src/azure_extra/agent_based/azure_extra_virtualnetworkgateways.py`, `src/azure_extra/agent_based/azure_extra_virtualnetworks.py`.
- **Server-side calls:** `src/azure_extra/server_side_calls/agent.py`.
- **Rulesets:** `src/azure_extra/rulesets/agent.py`.
- **Executables:** `src/azure_extra/libexec/agent_azure_extra`.
- **Check manuals:** `src/azure_extra/checkman/azure_vpn_gateway_bgp`, `src/azure_extra/checkman/azure_vpn_gateway_bgp_tunnel`.
- Registered special-agent names: `azure_extra`.
- Registered check plug-in names: `azure_extra_connections`, `azure_extra_dnsresolvers`, `azure_extra_virtualnetworks`, `azure_extra_virtualnetworks_peerings`, `azure_extra_virtualnetworks_subnets`, `azure_firewall`, `azure_firewall_ipconfig`, `azure_firewall_metrics`, `azure_firewall_policy`, `azure_firewall_rules`, `azure_vpn_gateway`, `azure_vpn_gateway_bgp`, `azure_vpn_gateway_bgp_tunnel`, `azure_vpn_gateway_ipconfig`, `azure_vpn_gateway_metrics`, `azure_vpn_gateway_natrule`, `azure_vpn_gateway_policygroup`, `azure_vpn_gateway_remotepeering`, `azure_vpn_gateway_vpnclient`.

### Validation

- Package-specific tests: `tests/test_azure_extras_secret_command_arguments.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- Server-side calls preserve Checkmk password-store references and the executable resolves them at runtime; direct plaintext options, where present, are limited to isolated command-line diagnostics.
- The source performs network or remote-system access. Keep timeouts bounded, validate responses, and prevent authenticated redirects or unintended environment-proxy use.

### Troubleshooting

- No literal Checkmk section header was detected. Inspect the executable or notification exit status and the Checkmk log relevant to the component type.
- For special agents, inspect the generated command without exposing secrets, run it as the site user, and verify that every emitted section has a matching parser/check registration.
<!-- code-derived-reference:end -->
