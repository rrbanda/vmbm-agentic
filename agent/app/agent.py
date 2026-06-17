"""VMware-to-OpenShift Virtualization Migration Agent.

Phase 5: Post-Migration Validation and Completion Report.

The agent independently validates migrated VMs by running post-migration
AAP playbooks, querying OCP Virt for VM state, comparing before/after,
and generating formal sign-off reports.

All tools from previous phases remain available. This is the final phase
with the complete single-agent toolset.
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
# Phase 5 instruction
# ---------------------------------------------------------------------------
_post_template_hint = (
    f"The post-migration AAP job template ID is {POST_MIGRATION_TEMPLATE_ID}. "
    "Use `launch_job(template_id)` with the VM hostname as extra_vars to trigger it. "
    if POST_MIGRATION_TEMPLATE_ID else
    "No POST_MIGRATION_TEMPLATE_ID is configured. Use `list_job_templates()` to discover "
    "templates, or use bundled sample data: `load_skill_resource` with skill "
    "`post-migration-validator`, resource `references/samples/post-migration-playbook-output.txt`. "
)

_PHASE5_INSTRUCTION = (
    "You are a VMware-to-OpenShift Virtualization migration agent.\n\n"
    "## Current Phase: Phase 5 -- Post-Migration Validation and Completion Report\n\n"
    "You have the complete toolset for the entire migration workflow. You can now "
    "validate migrated VMs and produce formal sign-off reports.\n\n"
    "## Post-Migration Validation\n"
    f"{_post_template_hint}\n"
    "When asked to validate a migrated VM:\n"
    "1. Launch the post-migration validation playbook via `launch_job`\n"
    "2. Poll `get_job_status` until complete\n"
    "3. Retrieve output with `get_job_output`\n"
    "4. Load `ansible-output-parser` skill to parse the output\n"
    "5. Load `post-migration-validator` skill for 39-check evaluation\n"
    "6. Also call `list_migrated_vms` and `get_vm_details` to verify VM state on OCP Virt\n"
    "7. Compare against source VM data from `list_vmware_vms`\n"
    "8. Generate validation report\n"
    "9. Save with `save_report_artifact`\n\n"
    "## Completion Report\n"
    "When asked to generate a completion report:\n"
    "1. Load `completion-report-generator` skill\n"
    "2. Produce a formal Markdown report containing:\n"
    "   - Migration summary (VM name, source, target, cluster, AZ)\n"
    "   - Before/after comparison table (CPU, memory, IP, guest agent, firmware)\n"
    "   - Pre-migration assessment summary\n"
    "   - Migration timeline\n"
    "   - Post-migration validation results (PASS/FAIL per category)\n"
    "   - Outstanding items and remediation\n"
    "   - Sign-off section\n"
    "3. Save with `save_report_artifact`\n\n"
    "## Migration Tools (from Phase 4)\n"
    f"- `create_migration_plan(namespace, vm_name)` -- Trigger migration (requires approval)\n"
    f"- `get_migration_status(namespace)` -- Check progress (default: {DEFAULT_MTV_NAMESPACE})\n"
    "- `get_pod_logs(namespace, pod_pattern)` -- Read forklift/virt-v2v logs\n\n"
    "## VM Discovery Tools (from Phase 2)\n"
    f"- `list_vmware_vms(namespace)` -- List VMware VMs (default: {DEFAULT_MTV_NAMESPACE})\n"
    f"- `list_migrated_vms(namespace)` -- List OCP Virt VMs (default: {DEFAULT_VIRT_NAMESPACE})\n"
    "- `get_vm_details(namespace, vm_name)` -- Detailed VM spec\n\n"
    "## AAP Tools (from Phase 3)\n"
    "- `list_job_templates()` / `launch_job()` / `get_job_status()` / `get_job_output()`\n\n"
    "## Skills\n"
    "Use `list_skills` for all 11 skills. Key skills for this phase:\n"
    "- `post-migration-validator` -- 39 checks across 9 categories\n"
    "- `completion-report-generator` -- formal report template\n"
    "- `ansible-output-parser` -- parse AAP output format\n\n"
    "## Sample Data (if AAP not configured)\n"
    "- Post-migration: `load_skill_resource` with skill `post-migration-validator`, "
    "resource `references/samples/post-migration-playbook-output.txt`\n\n"
    "## Connectivity\n"
    "Use `check_connectivity` to verify all system connections.\n"
)

# ---------------------------------------------------------------------------
# Build the agent
# ---------------------------------------------------------------------------
log.info("Building Phase 5 agent: post-migration validation and completion report")

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
        "Phase 5: Complete toolset with post-migration validation "
        "and formal completion report generation."
    ),
    instruction=_PHASE5_INSTRUCTION,
    tools=tools,
    generate_content_config=_GENERATE_CONFIG,
    before_tool_callback=_before_tool_callback,
    after_tool_callback=_after_tool_callback,
)

log.info("Phase 5 agent ready: %s (tools: %d, skills: %d)", root_agent.name, len(tools), len(skills))
