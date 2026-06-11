"""VMware-to-OpenShift Virtualization Migration Agent.

Phase 0: Connectivity verification only.

This is the initial deployment of the migration agent. It has a single
tool (check_connectivity) that probes all configured external systems
and returns a status table. No data is read or modified.

Future phases will add migration tools, skills, and pipeline capabilities
incrementally.

Configuration via environment variables:
  ADK_MODEL    - LLM model string (e.g., openai/gpt-oss-120b)
  AGENT_MODE   - Always 'single' for PoC sessions (pipeline added in later phases)
  AGENT_NAME   - Root agent name (default: migration_agent)
"""

import logging
import os

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.genai import types

from .connectivity_tools import check_connectivity

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
ADK_MODEL = os.environ.get("ADK_MODEL", "openai/gpt-oss-120b")
AGENT_NAME = os.environ.get("AGENT_NAME", "migration_agent")

# ---------------------------------------------------------------------------
# LLM generation config
# ---------------------------------------------------------------------------
_GENERATE_CONFIG = types.GenerateContentConfig(
    temperature=float(os.environ.get("ADK_TEMPERATURE", "0.2")),
    max_output_tokens=int(os.environ.get("ADK_MAX_OUTPUT_TOKENS", "4096")),
)

# ---------------------------------------------------------------------------
# Phase 0 instruction
# ---------------------------------------------------------------------------
_PHASE0_INSTRUCTION = (
    "You are a VMware-to-OpenShift Virtualization migration agent in setup mode.\n\n"
    "## Current Phase: Phase 0 -- Connectivity Verification\n\n"
    "Your only capability right now is verifying connectivity to external systems.\n"
    "Use the `check_connectivity` tool to probe all configured integrations and "
    "report their status.\n\n"
    "## How to Respond\n"
    "When asked about connectivity, system status, or readiness:\n"
    "1. Call `check_connectivity()` to probe all systems\n"
    "2. Present the results as a clear, formatted status table\n"
    "3. Summarize what is connected, what is not configured, and what failed\n"
    "4. Explain what each system is used for in the migration workflow\n\n"
    "## System Descriptions\n"
    "- **ADK Server**: The agent runtime itself (self-check)\n"
    "- **LLM Endpoint**: The large language model that powers the agent's reasoning\n"
    "- **MTV Kubernetes API**: Migration Toolkit for Virtualization -- manages VMware providers, "
    "migration plans, and VM transfers\n"
    "- **MTV Inventory Route**: Forklift inventory API -- provides VMware VM discovery (names, "
    "CPU, memory, disk, OS)\n"
    "- **OCP Virt Kubernetes API**: OpenShift Virtualization -- the target platform where VMs "
    "are migrated to\n"
    "- **AAP Controller**: Ansible Automation Platform -- runs pre-migration assessment and "
    "post-migration validation playbooks\n\n"
    "## What You Cannot Do Yet\n"
    "In this phase, you cannot list VMs, run assessments, trigger migrations, or generate "
    "reports. These capabilities will be added in subsequent phases.\n\n"
    "If asked about capabilities you don't have yet, explain that they are planned for "
    "future phases and suggest checking connectivity first to ensure the foundation is ready."
)

# ---------------------------------------------------------------------------
# Build the agent
# ---------------------------------------------------------------------------
log.info("Building Phase 0 agent: connectivity verification only")

root_agent = LlmAgent(
    model=LiteLlm(model=ADK_MODEL),
    name=AGENT_NAME,
    description=(
        "VMware-to-OpenShift Virtualization migration agent. "
        "Phase 0: Connectivity verification and system readiness check."
    ),
    instruction=_PHASE0_INSTRUCTION,
    tools=[check_connectivity],
    generate_content_config=_GENERATE_CONFIG,
)

log.info("Phase 0 agent ready: %s", root_agent.name)
