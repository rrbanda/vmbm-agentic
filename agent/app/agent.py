"""VMware-to-OpenShift Virtualization Migration Agent.

Phase 4: Automated Migration and Monitoring.

The agent can now trigger real VMware-to-OCP Virt migrations using MTV,
with a mandatory human approval gate. It can monitor migration progress
in real time and read forklift/virt-v2v logs for troubleshooting.

Single-agent mode is used for step-by-step demo control.
Previous phase capabilities (connectivity, skills, VM inventory, AAP) remain.
"""

import logging
import os
import pathlib

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.skills import load_skill_from_dir
from google.adk.tools import FunctionTool
from google.adk.tools.skill_toolset import SkillToolset
from google.genai import types

from .connectivity_tools import check_connectivity
from .report_tools import save_report_artifact
from .cluster_clients import DEFAULT_MTV_NAMESPACE, DEFAULT_VIRT_NAMESPACE
from .ocp_tools import (
    create_migration_plan,
    get_migration_status,
    get_pod_logs,
    get_vm_details,
    list_migrated_vms,
    list_vmware_vms,
)
from .aap_tools import (
    PRE_MIGRATION_TEMPLATE_ID,
    POST_MIGRATION_TEMPLATE_ID,
    get_job_output,
    get_job_status,
    launch_job,
    list_job_templates,
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
# Phase 4 instruction
# ---------------------------------------------------------------------------
_PHASE4_INSTRUCTION = (
    "You are a VMware-to-OpenShift Virtualization migration agent.\n\n"
    "## Current Phase: Phase 4 -- Automated Migration and Monitoring\n\n"
    "You can now trigger real VMware-to-OCP Virt migrations using MTV and "
    "monitor them in real time. The create_migration_plan tool requires "
    "human approval before executing.\n\n"
    "## Migration Tools\n"
    f"- `create_migration_plan(namespace, vm_name)` -- Creates NetworkMap, StorageMap, Plan, "
    "and Migration CRs to migrate a VM. **Requires human approval** before executing.\n"
    f"- `get_migration_status(namespace)` -- Check MTV plan/migration progress (default: {DEFAULT_MTV_NAMESPACE})\n"
    "- `get_pod_logs(namespace, pod_pattern, tail_lines)` -- Read forklift/virt-v2v/CDI pod logs\n\n"
    "## VM Discovery Tools (from Phase 2)\n"
    f"- `list_vmware_vms(namespace)` -- List VMware VMs (default: {DEFAULT_MTV_NAMESPACE})\n"
    f"- `list_migrated_vms(namespace)` -- List OCP Virt VMs (default: {DEFAULT_VIRT_NAMESPACE})\n"
    "- `get_vm_details(namespace, vm_name)` -- Detailed VM spec\n\n"
    "## AAP Tools (from Phase 3)\n"
    "- `list_job_templates()` -- List AAP templates\n"
    "- `launch_job(template_id, extra_vars)` -- Trigger Ansible playbook\n"
    "- `get_job_status(job_id)` -- Poll job progress\n"
    "- `get_job_output(job_id)` -- Retrieve playbook output\n\n"
    "## Migration Workflow\n"
    "When asked to migrate a VM:\n"
    "1. Call `create_migration_plan(namespace, vm_name)` -- this will pause for approval\n"
    "2. After approval, the tool creates the MTV resources and starts the migration\n"
    "3. Use `get_migration_status(namespace)` to monitor progress\n"
    "4. If errors occur, use `get_pod_logs(namespace, 'forklift')` to read logs\n"
    "5. Load the `mtv-log-analyzer` skill to diagnose failures\n\n"
    "## Skills\n"
    "Use `list_skills` to see all 11 available skills.\n"
    "Key skills for troubleshooting: mtv-log-analyzer (12 failure patterns).\n\n"
    "## Connectivity\n"
    "Use `check_connectivity` to verify all system connections.\n\n"
    "## What You Cannot Do Yet\n"
    "- Run post-migration validation playbooks (Phase 5)\n"
    "- Generate completion reports with before/after comparison (Phase 5)\n"
)

# ---------------------------------------------------------------------------
# Build the agent
# ---------------------------------------------------------------------------
log.info("Building Phase 4 agent: migration execution and monitoring")

tools = [
    check_connectivity,
    save_report_artifact,
    list_vmware_vms,
    list_migrated_vms,
    get_vm_details,
    get_migration_status,
    FunctionTool(create_migration_plan, require_confirmation=True),
    get_pod_logs,
    list_job_templates,
    launch_job,
    get_job_status,
    get_job_output,
]
if skills:
    tools.append(SkillToolset(skills=skills))

root_agent = LlmAgent(
    model=LiteLlm(model=ADK_MODEL),
    name=AGENT_NAME,
    description=(
        "VMware-to-OpenShift Virtualization migration agent. "
        "Phase 4: Migration execution with human approval gate, "
        "real-time monitoring, and log-based troubleshooting."
    ),
    instruction=_PHASE4_INSTRUCTION,
    tools=tools,
    generate_content_config=_GENERATE_CONFIG,
    before_tool_callback=_before_tool_callback,
    after_tool_callback=_after_tool_callback,
)

log.info("Phase 4 agent ready: %s (tools: %d, skills: %d)", root_agent.name, len(tools), len(skills))
