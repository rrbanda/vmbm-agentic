# Phase 1 -- Working Session Runbook

**Duration**: 30-45 minutes
**Format**: Screen share, walking the customer through the AI analysis capabilities
**Goal**: Customer sees the agent analyze real Ansible playbook output and produce structured reports -- all from bundled sample data, zero risk to their environment

---

## Before the Session (Your Prep)

- [ ] Phase 0 is deployed and working (connectivity check passes)
- [ ] This branch (`phase-1-demo-mode`) is checked out
- [ ] Have this runbook open as your script

---

## Session Start -- Context Setting (3 min)

**Say:**

> "Last session we proved the agent can reach all your systems. Today we activate the AI analysis engine. The agent will analyze real Ansible playbook output -- the same format your pre-migration assessment produces -- and generate a structured readiness report."
>
> "Everything today uses bundled sample data. We're not touching any of your VMs or running any playbooks. This is purely to show how the AI reasoning works."

---

## Step 1: Deploy Phase 1 (5 min)

**Say:** "Let me upgrade the agent with the analysis skills."

**Run:**

```bash
chmod +x scripts/deploy-phase1.sh
./scripts/deploy-phase1.sh
```

**Narrate:** "This rebuilds the image with 11 domain skills -- each one encodes specific migration knowledge that the AI uses to analyze playbook output."

---

## Step 2: Show Available Skills (3 min)

**Open the UI** and type:

```
What skills do you have available?
```

**Walk through the response:**

> "You can see 11 skills loaded:
> - `pre-migration-analyzer` -- knows your 36 pre-migration checks across 11 categories
> - `post-migration-validator` -- knows your 39 post-migration checks
> - `ansible-output-parser` -- understands the AAP output format including Slice headers and ignored errors
> - `assessment-report-generator` -- produces formal readiness reports
> - `risk-assessor` -- scores migration risk on 6 weighted factors
> - [etc.]
>
> Each skill is a Markdown file that teaches the AI how to think about that specific problem. It's your senior engineers' knowledge, codified."

---

## Step 3: Pre-Migration Assessment (10 min -- Hero Moment)

**Say:** "Now let's see the agent analyze a real pre-migration playbook output. This is bundled sample data from a RHEL 8.10 host."

**Type:**

```
Analyze the sample pre-migration output and produce a readiness assessment report
```

**Let it stream. Then narrate as it appears:**

> "The agent loaded the Ansible output parser, read the sample playbook output, and is now evaluating each of the 36 checks..."
>
> "Look at how it handles the kernel/grub consistency check -- it compared proccmdline_list against grubgen_list. That's the check that catches VMs that would fail to boot after migration."
>
> "Notice it classified the NetBackup error as INFO, not a failure -- because it recognized the `ignore_errors: true` pattern. A junior engineer might flag that as a blocker."
>
> "Final verdict: READY with LOW risk. 11 categories evaluated, zero blockers, two minor warnings."

**Key talking point for customer:**
> "This analysis takes your engineers 30-45 minutes per VM. The agent did it in under a minute. At 200 VMs per day, that's over 100 engineer-hours recovered daily."

---

## Step 4: Post-Migration Validation (5 min)

**Say:** "The same analysis works for post-migration. Let's validate a completed migration."

**Type:**

```
Analyze the sample post-migration output and produce a validation report
```

**Narrate highlights:**
> "Platform confirmed: OpenShift Virtualization. CPU and memory match pre-migration values. vCenter cleanup completed -- VM renamed, NICs disconnected. Guest agent swapped from VMware tools to qemu-guest-agent."

---

## Step 5: Risk Assessment (3 min)

**Say:** "The agent can also assess risk for VMs you're planning to migrate."

**Type:**

```
Assess migration risk for a RHEL 7 VM with 500GB disk, NFS mounts, and no recent backup
```

**Narrate:**
> "It evaluated 6 risk factors with weights: OS complexity (RHEL 7 is older), disk layout (500GB is large), network dependencies (NFS), application criticality, backup status (none -- HIGH risk), and historical success rate."

---

## Step 6: Connectivity Check Still Works (1 min)

**Say:** "The connectivity check from last session still works -- skills were added, nothing was removed."

**Type:**

```
Check connectivity to all configured systems
```

---

## Wrap-Up (5 min)

**Say:**

> "Today we proved that the AI analysis engine works:
> 1. It correctly parses Ansible playbook output in your format
> 2. It evaluates all 36 pre-migration checks with proper severity classification
> 3. It handles edge cases -- ignored errors, OS-specific task branching, kernel consistency
> 4. It produces structured, actionable reports with verdicts, risk ratings, and remediation
>
> All of this was against sample data. In our next session (Phase 2), we'll connect it to your live VMware inventory -- the agent will see your actual VMs with real names and real specs."

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "Skills directory does not exist" | Check `SKILLS_DIR` env var: `oc set env deployment/adk-web -c adk-api SKILLS_DIR=/skills` |
| Agent says "0 skills loaded" | Rebuild image: `./scripts/deploy-phase1.sh` |
| Pre-migration assessment times out | Check LLM route timeout: `oc annotate route <llm-route> -n <llm-ns> --overwrite haproxy.router.openshift.io/timeout=600s` |
| "save_report_artifact failed" | Storage issue: check `/app/.adk` is writable in the pod |
