"""VMware-to-OpenShift Virtualization Migration Agent.

Phase 2: Live VM Inventory (Read-Only MTV Access).

The agent can now discover real VMware VMs via the MTV Forklift inventory
and view migrated VMs on OCP Virtualization. All access is read-only --
no migrations are triggered.

Previous phase capabilities (connectivity check, skills, reports) remain.
"""

import logging
import os
import pathlib

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.skills import load_skill_from_dir
from google.adk.tools.skill_toolset import SkillToolset
from google.genai import types

from .connectivity_tools import check_connectivity
from .report_tools import save_report_artifact
from .cluster_clients import DEFAULT_MTV_NAMESPACE, DEFAULT_VIRT_NAMESPACE
from .ocp_tools import (
    get_migration_status,
    get_vm_details,
    list_migrated_vms,
    list_vmware_vms,
)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
ADK_MODEL = os.environ.get("ADK_MODEL", "openai/gpt-oss-120b")
AGENT_NAME = os.environ.get("AGENT_NAME", "migration_agent")
SKILLS_DIR = pathlib.Path(os.environ.get("SKILLS_DIR", "/skills"))

# ---------------------------------------------------------------------------
# LLM generation config
# ---------------------------------------------------------------------------
_GENERATE_CONFIG = types.GenerateContentConfig(
    temperature=float(os.environ.get("ADK_TEMPERATURE", "0.2")),
)

# ---------------------------------------------------------------------------
# Skill discovery
# ---------------------------------------------------------------------------
def _discover_skills(skills_dir: pathlib.Path) -> list:
    skills = []
    if not skills_dir.exists():
        log.warning("Skills directory %s does not exist", skills_dir)
        return skills
    for entry in sorted(skills_dir.iterdir()):
        if entry.is_dir() and (entry / "SKILL.md").exists():
            try:
                skill = load_skill_from_dir(entry)
                skills.append(skill)
                log.info("Loaded skill: %s", entry.name)
            except Exception as e:
                log.warning("Failed to load skill from %s: %s", entry, e)
    return skills


skills = _discover_skills(SKILLS_DIR)
log.info("Discovered %d skills from %s", len(skills), SKILLS_DIR)

# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------
def _before_tool_callback(tool, args, tool_context):
    log.info("TOOL_CALL: %s(%s)", tool.name, args)
    return None

def _after_tool_callback(tool, args, tool_context, tool_response):
    status = "error" if isinstance(tool_response, dict) and "error" in tool_response else "ok"
    log.info("TOOL_RESULT: %s -> %s", tool.name, status)
    return None

# ---------------------------------------------------------------------------
# Phase 2 instruction
# ---------------------------------------------------------------------------
_PHASE2_INSTRUCTION = (
    "You are a VMware-to-OpenShift Virtualization migration agent.\n\n"
    "## Current Phase: Phase 2 -- Live VM Inventory\n\n"
    "You can now discover real VMware VMs from the customer's environment "
    "and view VMs that have already been migrated to OCP Virtualization. "
    "All access is read-only -- you cannot trigger migrations yet.\n\n"
    "## VM Discovery Tools\n"
    f"- `list_vmware_vms(namespace)` -- List VMs on VMware vSphere via MTV inventory (default namespace: {DEFAULT_MTV_NAMESPACE})\n"
    f"- `list_migrated_vms(namespace)` -- List VMs already on OCP Virtualization (default namespace: {DEFAULT_VIRT_NAMESPACE})\n"
    "- `get_vm_details(namespace, vm_name)` -- Get detailed VM spec (CPU, memory, disks, interfaces)\n"
    "- `get_migration_status(namespace)` -- Check MTV migration plan status\n\n"
    "## Skills (from Phase 1)\n"
    "Use `list_skills` to see all available analysis skills.\n"
    "Key skills: pre-migration-analyzer, post-migration-validator, "
    "ansible-output-parser, assessment-report-generator, risk-assessor.\n\n"
    "## Sample Data (Demo Mode)\n"
    "When asked to analyze sample output:\n"
    "- Pre-migration: `load_skill_resource` with skill `pre-migration-analyzer`, "
    "resource `references/samples/pre-migration-playbook-output.txt`\n"
    "- Post-migration: `load_skill_resource` with skill `post-migration-validator`, "
    "resource `references/samples/post-migration-playbook-output.txt`\n\n"
    "## Reports\n"
    "After generating any report, call `save_report_artifact(report_content, filename)` "
    "to save it as a downloadable artifact.\n\n"
    "## Connectivity\n"
    "Use `check_connectivity` to verify system connections.\n\n"
    "## What You Cannot Do Yet\n"
    "- Trigger live AAP playbooks (Phase 3)\n"
    "- Execute migrations (Phase 4)\n"
    "- Read pod logs for troubleshooting (Phase 4)\n"
)

# ---------------------------------------------------------------------------
# Build the agent
# ---------------------------------------------------------------------------
log.info("Building Phase 2 agent: live VM inventory (read-only)")

tools = [
    check_connectivity,
    save_report_artifact,
    list_vmware_vms,
    list_migrated_vms,
    get_vm_details,
    get_migration_status,
]
if skills:
    tools.append(SkillToolset(skills=skills))

root_agent = LlmAgent(
    model=LiteLlm(model=ADK_MODEL),
    name=AGENT_NAME,
    description=(
        "VMware-to-OpenShift Virtualization migration agent. "
        "Phase 2: Live VM inventory via MTV Forklift (read-only). "
        "Discovers real VMware VMs and views migrated VMs on OCP Virt."
    ),
    instruction=_PHASE2_INSTRUCTION,
    tools=tools,
    generate_content_config=_GENERATE_CONFIG,
    before_tool_callback=_before_tool_callback,
    after_tool_callback=_after_tool_callback,
)

log.info("Phase 2 agent ready: %s (tools: %d, skills: %d)", root_agent.name, len(tools), len(skills))
