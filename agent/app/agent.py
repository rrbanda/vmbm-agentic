"""VMware-to-OpenShift Virtualization Migration Agent.

Phase 3: Live Pre-Migration Assessment via AAP.

The agent can now trigger real Ansible pre-migration assessment playbooks
on the customer's VMs via AAP, poll until completion, retrieve the output,
and analyze it through the 36-check framework.

Previous phase capabilities (connectivity, skills, VM inventory) remain.
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

aap_url = os.environ.get("AAP_URL", "")
if aap_url:
    log.info("AAP integration enabled: %s", aap_url)
else:
    log.info("AAP integration disabled (AAP_URL not set)")

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
# Phase 3 instruction
# ---------------------------------------------------------------------------
_pre_template_hint = (
    f"The pre-migration AAP job template ID is {PRE_MIGRATION_TEMPLATE_ID}. "
    "Use `launch_job(template_id)` with the VM hostname as extra_vars to trigger it. "
    if PRE_MIGRATION_TEMPLATE_ID else
    "No PRE_MIGRATION_TEMPLATE_ID is configured. Use `list_job_templates()` to "
    "discover available templates, then use `launch_job(template_id)` to trigger one. "
)

_PHASE3_INSTRUCTION = (
    "You are a VMware-to-OpenShift Virtualization migration agent.\n\n"
    "## Current Phase: Phase 3 -- Live Pre-Migration Assessment via AAP\n\n"
    "You can now trigger real Ansible pre-migration assessment playbooks on the "
    "customer's VMs via Ansible Automation Platform (AAP).\n\n"
    "## AAP Tools\n"
    "- `list_job_templates()` -- List available AAP job templates (confirms connectivity)\n"
    "- `launch_job(template_id, extra_vars)` -- Trigger an Ansible playbook\n"
    "  - extra_vars is a JSON string, e.g., '{\"target_host\": \"vm-name\"}'\n"
    "- `get_job_status(job_id)` -- Poll job progress (terminal: successful, failed, error, canceled)\n"
    "- `get_job_output(job_id)` -- Retrieve full playbook stdout when job is complete\n\n"
    f"## Pre-Migration Assessment\n{_pre_template_hint}\n"
    "When asked to assess a VM:\n"
    "1. Launch the pre-migration job template with the VM hostname\n"
    "2. Poll `get_job_status` until the job completes\n"
    "3. Retrieve the output with `get_job_output`\n"
    "4. Load the `ansible-output-parser` skill to parse the output\n"
    "5. Load `pre-migration-analyzer` skill for the 36-check evaluation\n"
    "6. Generate a readiness report using `assessment-report-generator` skill\n"
    "7. Save the report with `save_report_artifact`\n\n"
    "## VM Discovery Tools (from Phase 2)\n"
    f"- `list_vmware_vms(namespace)` -- List VMware VMs (default: {DEFAULT_MTV_NAMESPACE})\n"
    f"- `list_migrated_vms(namespace)` -- List OCP Virt VMs (default: {DEFAULT_VIRT_NAMESPACE})\n"
    "- `get_vm_details(namespace, vm_name)` -- Detailed VM spec\n"
    "- `get_migration_status(namespace)` -- MTV plan status\n\n"
    "## Skills (from Phase 1)\n"
    "Use `list_skills` to see all 11 available skills.\n"
    "Key skills for assessment: ansible-output-parser, pre-migration-analyzer, "
    "assessment-report-generator, risk-assessor.\n\n"
    "## Sample Data (Demo Mode)\n"
    "When AAP is not configured or for demo purposes:\n"
    "- Pre-migration: `load_skill_resource` with skill `pre-migration-analyzer`, "
    "resource `references/samples/pre-migration-playbook-output.txt`\n"
    "- Post-migration: `load_skill_resource` with skill `post-migration-validator`, "
    "resource `references/samples/post-migration-playbook-output.txt`\n\n"
    "## Connectivity\n"
    "Use `check_connectivity` to verify all system connections.\n\n"
    "## What You Cannot Do Yet\n"
    "- Execute migrations (Phase 4)\n"
    "- Read forklift pod logs (Phase 4)\n"
)

# ---------------------------------------------------------------------------
# Build the agent
# ---------------------------------------------------------------------------
log.info("Building Phase 3 agent: live AAP pre-migration assessment")

tools = [
    check_connectivity,
    save_report_artifact,
    list_vmware_vms,
    list_migrated_vms,
    get_vm_details,
    get_migration_status,
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
        "Phase 3: Live pre-migration assessment via AAP. "
        "Triggers real Ansible playbooks, analyzes output, generates reports."
    ),
    instruction=_PHASE3_INSTRUCTION,
    tools=tools,
    generate_content_config=_GENERATE_CONFIG,
    before_tool_callback=_before_tool_callback,
    after_tool_callback=_after_tool_callback,
)

log.info("Phase 3 agent ready: %s (tools: %d, skills: %d)", root_agent.name, len(tools), len(skills))
