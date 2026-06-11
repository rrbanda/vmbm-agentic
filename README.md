# VMware-to-OpenShift Virtualization Migration Agent

AI-powered migration agent that automates the VMware-to-OpenShift Virtualization
migration workflow. Built with [Google ADK](https://github.com/google/adk-python),
deployed on Red Hat OpenShift AI.

## Phased Deployment

This agent is deployed incrementally. Each phase adds one integration layer and
is demonstrable in a single working session.

| Phase | Title | What It Adds |
|-------|-------|-------------|
| **0** | **Authentication & Connectivity** | Agent deployed, probes all systems | **<-- Current** |
| 1 | Working UI with Demo Mode | 11 skills, sample data analysis, reports |
| 2 | Live VM Inventory | Read-only VMware inventory via MTV |
| 3 | Live Pre-Migration Assessment | AAP integration for Ansible playbooks |
| 4 | Automated Migration & Monitoring | MTV write access, HITL approval, log analysis |
| 5 | Post-Migration Validation & Report | Full validation, before/after comparison, sign-off |

## Current Phase: Phase 0

Phase 0 proves that the agent can reach every system it needs. No data is read
or modified. The agent has a single tool (`check_connectivity`) that probes
LLM, MTV, OCP Virt, and AAP endpoints and reports their status.

### Quick Start

```bash
# 1. Check your environment
./scripts/env-check.sh

# 2. Generate configuration interactively
./scripts/gather-config.sh

# 3. Deploy the agent
./scripts/deploy-phase0.sh

# 4. Validate
./scripts/validate-phase0.sh
```

### Demo Prompt

> Check connectivity to all configured systems and show me the status of each integration.

See [docs/phase-0-guide.md](docs/phase-0-guide.md) for the full setup guide,
glossary, and architecture overview.

## License

Apache License 2.0. See [LICENSE](LICENSE).
