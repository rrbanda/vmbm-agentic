"""VMware-to-OpenShift Virtualization Migration Agent.

Phase 1: Working UI with Demo Mode.

The agent has 11 domain skills loaded and can analyze bundled sample
Ansible playbook output to produce full readiness reports. It can also
verify system connectivity (from Phase 0).

No external systems are required beyond an LLM endpoint.

Configuration via environment variables:
  ADK_MODEL    - LLM model string (e.g., openai/gpt-oss-120b)
  AGENT_MODE   - Always 'single' for PoC sessions
  AGENT_NAME   - Root agent name (default: migration_agent)
  SKILLS_DIR   - Path to skills directory (default: /skills)
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
    """Discover and load all skills from subdirectories containing SKILL.md."""
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
# Callbacks for logging
# ---------------------------------------------------------------------------
def _before_tool_callback(tool, args, tool_context):
    """Log every tool call for observability."""
    log.info("TOOL_CALL: %s(%s)", tool.name, args)
    return None


def _after_tool_callback(tool, args, tool_context, tool_response):
    """Log tool results."""
    status = "error" if isinstance(tool_response, dict) and "error" in tool_response else "ok"
    log.info("TOOL_RESULT: %s -> %s", tool.name, status)
    return None


# ---------------------------------------------------------------------------
# Phase 1 instruction
# ---------------------------------------------------------------------------
_PHASE1_INSTRUCTION = (
    "You are a VMware-to-OpenShift Virtualization migration agent.\n\n"
    "## Current Phase: Phase 1 -- Demo Mode\n\n"
    "You have 11 domain skills loaded for migration analysis. You can analyze "
    "Ansible playbook output (pre-migration and post-migration), produce readiness "
    "reports, assess risk, plan batches, and troubleshoot failures.\n\n"
    "## Skills\n"
    "Use `list_skills` to see all available skills. Use `load_skill` to read a "
    "skill's full instructions. Use `load_skill_resource` to read reference files "
    "within a skill (checklists, task maps, sample data).\n\n"
    "Key skills:\n"
    "- `pre-migration-analyzer` -- 36 readiness checks across 11 categories\n"
    "- `post-migration-validator` -- 39 post-migration checks\n"
    "- `ansible-output-parser` -- parses AAP/Ansible Tower output format\n"
    "- `assessment-report-generator` -- formal readiness report with remediation\n"
    "- `completion-report-generator` -- migration completion report with before/after\n"
    "- `mtv-log-analyzer` -- diagnoses MTV migration failures\n"
    "- `risk-assessor` -- weighted 6-factor risk scoring\n"
    "- `batch-planner` -- groups VMs into migration batches\n"
    "- `capacity-analyzer` -- cluster capacity headroom analysis\n"
    "- `migration-workflow` -- end-to-end orchestration guide\n"
    "- `migration-kb-builder` -- knowledge base management\n\n"
    "## Sample Data (Demo Mode)\n"
    "When asked to analyze sample output:\n"
    "- Pre-migration: `load_skill_resource` with skill `pre-migration-analyzer`, "
    "resource `references/samples/pre-migration-playbook-output.txt`\n"
    "- Post-migration: `load_skill_resource` with skill `post-migration-validator`, "
    "resource `references/samples/post-migration-playbook-output.txt`\n\n"
    "## Analyzing Playbook Output\n"
    "When asked to analyze pre-migration or post-migration output:\n"
    "1. Load the `ansible-output-parser` skill to understand the output format\n"
    "2. Load the appropriate task map via `load_skill_resource`:\n"
    "   - Pre-migration: `references/premigration-task-map.md` (in ansible-output-parser skill)\n"
    "   - Post-migration: `references/postmigration-task-map.md` (in ansible-output-parser skill)\n"
    "3. Load the `pre-migration-analyzer` or `post-migration-validator` skill\n"
    "4. Load the `assessment-report-generator` skill for report formatting\n"
    "5. Save the report using `save_report_artifact`\n\n"
    "## Reports\n"
    "After generating any report, call `save_report_artifact(report_content, filename)` "
    "to save it as a downloadable artifact in the UI.\n\n"
    "## Connectivity\n"
    "You can still check system connectivity using `check_connectivity` (from Phase 0).\n\n"
    "## What You Cannot Do Yet\n"
    "- List live VMware VMs (Phase 2)\n"
    "- Trigger live AAP playbooks (Phase 3)\n"
    "- Execute migrations (Phase 4)\n"
    "- Validate migrated VMs on OCP Virt (Phase 5)\n\n"
    "These capabilities are added in subsequent phases."
)

# ---------------------------------------------------------------------------
# Build the agent
# ---------------------------------------------------------------------------
log.info("Building Phase 1 agent: demo mode with %d skills", len(skills))

tools = [check_connectivity, save_report_artifact]
if skills:
    tools.append(SkillToolset(skills=skills))

root_agent = LlmAgent(
    model=LiteLlm(model=ADK_MODEL),
    name=AGENT_NAME,
    description=(
        "VMware-to-OpenShift Virtualization migration agent. "
        "Phase 1: Demo mode with 11 analysis skills and report generation. "
        "Analyzes bundled sample playbook output without touching customer systems."
    ),
    instruction=_PHASE1_INSTRUCTION,
    tools=tools,
    generate_content_config=_GENERATE_CONFIG,
    before_tool_callback=_before_tool_callback,
    after_tool_callback=_after_tool_callback,
)

log.info("Phase 1 agent ready: %s (tools: %d, skills: %d)", root_agent.name, len(tools), len(skills))
