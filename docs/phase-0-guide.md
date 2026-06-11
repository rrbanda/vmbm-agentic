# Phase 0: Authentication and Connectivity Verification

## Overview

Phase 0 is the foundation session. The goal is to prove that the deployed agent
can reach every system it needs before doing any migration work. No data is read
or modified -- this is purely a trust-building exercise.

The customer sees their infrastructure reflected in the agent's connectivity
status: which systems are reachable, which tokens are valid, and which
integrations are ready.

## What You'll See

The agent has a single tool: `check_connectivity`. When you ask it to check
system status, it probes each configured endpoint and returns a table:

| System | URL | Token | Status | Detail |
|--------|-----|-------|--------|--------|
| ADK Server | http://localhost:8000 | n/a | Connected | HTTP 200 |
| LLM Endpoint | https://... | Yes | Connected | HTTP 200 |
| MTV K8s API | https://... | Yes | Connected | 5+ namespaces |
| ... | ... | ... | ... | ... |

Systems that are not yet configured show as "Not Configured" rather than
failing. This is expected -- you'll enable them in later phases.

## Prerequisites

1. **OpenShift cluster** with `oc` CLI access
2. **A reachable LLM endpoint** (vLLM on RHOAI, Llama Stack, or any OpenAI-compatible endpoint)
3. **Tokens for systems you want to verify** (any subset works)

## Setup Steps

```bash
# 1. Clone the repo
git clone https://github.com/rrbanda/vmbm-agentic.git
cd vmbm-agentic

# 2. Check your environment
chmod +x scripts/*.sh
./scripts/env-check.sh

# 3. Generate configuration
./scripts/gather-config.sh

# 4. Deploy the agent
./scripts/deploy-phase0.sh

# 5. Validate
./scripts/validate-phase0.sh
```

## Demo Prompt

Open the ADK Web UI (URL shown after deployment) and type:

> Check connectivity to all configured systems and show me the status of
> each integration.

## What the Agent Can Do in Phase 0

- Check connectivity to LLM, MTV, OCP Virt, and AAP
- Explain what each system is used for in the migration workflow
- Report which systems are ready and which need configuration

## What the Agent Cannot Do Yet

- List VMware VMs (Phase 2)
- Run pre-migration assessments (Phase 3)
- Trigger migrations (Phase 4)
- Validate post-migration results (Phase 5)

These capabilities are added incrementally in subsequent phases.

## Glossary

| Term | Description |
|------|-------------|
| **ADK** | Google Agent Development Kit -- the framework for building AI agents |
| **MTV** | Migration Toolkit for Virtualization -- Red Hat's tool for migrating VMs from VMware to OpenShift |
| **Forklift** | The upstream project behind MTV |
| **KubeVirt** | The technology that runs VMs on Kubernetes (part of OpenShift Virtualization) |
| **OCP Virt** | OpenShift Virtualization -- the target platform for migrated VMs |
| **AAP** | Ansible Automation Platform -- runs pre/post migration validation playbooks |
| **RHOAI** | Red Hat OpenShift AI -- the AI/ML platform for model serving and agent deployment |
| **vLLM** | A high-performance LLM serving engine used on RHOAI |
| **LLM** | Large Language Model -- the AI model that powers the agent's reasoning |
| **Llama Stack** | An API gateway that provides OpenAI-compatible endpoints for LLM access |
| **Kagenti** | Red Hat's agent lifecycle operator for OpenShift AI |

## Architecture

```
┌──────────────────────────────────────────────────────┐
│  Red Hat OpenShift AI Cluster                        │
│                                                      │
│  ┌─────────────────────────────────────────────────┐ │
│  │  Pod: adk-web                                   │ │
│  │  ┌──────────────┐  ┌─────────────────────────┐ │ │
│  │  │  adk-web     │  │  adk-api                │ │ │
│  │  │  nginx:8080  │──│  ADK agent:8000         │ │ │
│  │  │  (UI + proxy)│  │  Tools:                 │ │ │
│  │  └──────────────┘  │   - check_connectivity  │ │ │
│  │                     │  Skills: (Phase 1+)     │ │ │
│  │                     └─────────────────────────┘ │ │
│  └─────────────────────────────────────────────────┘ │
│                           │                          │
│                    ┌──────┴──────┐                    │
│                    │ Probes to:  │                    │
│                    │ - LLM       │                    │
│                    │ - MTV API   │                    │
│                    │ - OCP Virt  │                    │
│                    │ - AAP       │                    │
│                    └─────────────┘                    │
└──────────────────────────────────────────────────────┘
```

## Next Phase

**Phase 1: Working UI with Demo Mode** -- The agent gets 11 analysis skills and
bundled sample data. It can analyze pre-migration assessment output and produce
readiness reports -- all without touching any customer systems.
