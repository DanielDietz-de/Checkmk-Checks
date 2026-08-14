# GitHub Actions runner policy

Ordinary repository Linux CI runs on the privately managed runner farm with the explicit selector:

```yaml
runs-on: [self-hosted, linux]
```

The repository guard enforces this boundary through `tools/ci/check_workflow_runners.py`. Generic `linux` selectors are not accepted because they do not explicitly establish self-hosted execution. GitHub-hosted labels are rejected unless the exact workflow path and exact runner image are present in the small reviewed exception inventory described below.

## Self-hosted Linux runner contract

Each eligible Linux runner must expose both labels:

- `self-hosted`
- `linux`

The selector deliberately does not require an architecture label. This matches the validated local runner-farm contract while still enforcing both the privately managed execution boundary and a Linux execution environment.

The following ordinary workflows use the self-hosted Linux farm:

- repository security and supply-chain guard;
- repository MKP tests, builds, Checkmk runtime validation, and publication dry run;
- validated MKP publication;
- weekly validation dispatch.

## Pinned hosted-runner exceptions

Hosted execution is permitted only where the execution environment is itself part of the validation or trust boundary. Exceptions are hard-coded by exact workflow path and exact runner image; adding or changing an exception requires code review and regression-test changes.

Current exceptions are:

- `.github/workflows/s2d-hci-windows-ci.yml` → `windows-2025`. This workflow must parse the S2D/HCI PowerShell package with **Windows PowerShell 5.1** and run PSScriptAnalyzer on Windows. The validated self-hosted farm is Linux-only, so moving this job to that farm would remove the platform compatibility gate rather than merely relocate it.
- `.github/workflows/final-audit-orchestrator.yml` → `ubuntu-24.04`.
- `.github/workflows/final-audit-runner.yml` → `ubuntu-24.04`.

The final-audit workflows are temporary trusted-bootstrap workflows and deliberately use ephemeral GitHub-hosted Linux runners. They are not a general precedent for hosted CI. When those workflows are removed, their exception entries must be removed as well.

No workflow may mix self-hosted and GitHub-hosted labels in one selector. Labels such as `ubuntu-latest`, `windows-latest`, or any hosted image outside the exact exception inventory fail the repository guard.

## Runtime prerequisites for the Linux farm

The runner image or host must provide:

- a supported GitHub Actions runner service;
- Git and Bash;
- Python 3 bootstrap support for `actions/setup-python`;
- GitHub CLI (`gh`) for publication and scheduled-dispatch workflows;
- Docker Engine with permission for the runner service account to start, inspect, log, and remove containers;
- sufficient local disk space for Checkmk container images, MKP artifacts, and temporary build output;
- outbound HTTPS access required by the pinned GitHub Actions, Python package installation, GitHub artifact service, GitHub API, and Docker Hub image pulls.

The Checkmk runtime-validation matrix starts Docker containers directly on the runner. Rootless or socket-proxied Docker is acceptable only when it supports the commands used by `.github/workflows/repository-mkp-ci.yml`.

## Operational checks

Before enabling a Linux runner for this repository, verify:

```bash
git --version
bash --version
python3 --version
gh --version
docker version
docker run --rm hello-world
```

The runner service account must be able to execute the Docker commands without interactive privilege escalation.

## Capacity and isolation

The runtime-validation matrix can execute multiple Docker-backed jobs concurrently. Runner-farm concurrency should be limited according to available CPU, memory, disk, and Docker image-cache capacity. Use ephemeral runners or reliable post-job workspace cleanup where possible, especially because workflows process pull-request content.

Repository workflows use read-only contents permissions except where a deliberately separate publication or audit workflow requires write access. Do not add broadly scoped persistent credentials to runner hosts. Hosted exceptions use only the workflow-scoped GitHub token and must retain their existing least-privilege permissions and bootstrap checks.
