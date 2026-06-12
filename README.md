# VMware-to-OpenShift Virtualization Migration Agent

AI-powered migration agent that automates the VMware-to-OpenShift Virtualization
migration workflow. Built with [Google ADK](https://github.com/google/adk-python),
deployed on Red Hat OpenShift AI.

## Phased Deployment

This agent is deployed incrementally. Each phase adds one integration layer and
is demonstrable in a single working session.

| Phase | Title | What It Adds |
|-------|-------|-------------|
| **0** | Authentication & Connectivity | Agent deployed, probes all systems |
| **1** | **Working UI with Demo Mode** | 11 skills, sample data analysis, reports | **<-- Current** |
| 2 | Live VM Inventory | Read-only VMware inventory via MTV |
| 3 | Live Pre-Migration Assessment | AAP integration for Ansible playbooks |
| 4 | Automated Migration & Monitoring | MTV write access, HITL approval, log analysis |
| 5 | Post-Migration Validation & Report | Full validation, before/after comparison, sign-off |

## Current Phase: Phase 1

Phase 1 adds 11 domain analysis skills and report generation. The agent can
analyze bundled sample Ansible playbook output (pre-migration and post-migration)
and produce structured readiness reports with risk ratings, blockers, and
remediation steps. No customer systems are accessed beyond the LLM.

### Quick Start (Upgrade from Phase 0)

```bash
git checkout phase-1-demo-mode
./scripts/deploy-phase1.sh
```

### Demo Prompts

> What skills do you have available?

> Analyze the sample pre-migration output and produce a readiness assessment report

> Analyze the sample post-migration output and produce a validation report

> Assess migration risk for a RHEL 7 VM with 500GB disk and no backup

See [docs/phase-1-session-runbook.md](docs/phase-1-session-runbook.md) for the
full customer session walkthrough.

## License

Apache License 2.0. See [LICENSE](LICENSE).
