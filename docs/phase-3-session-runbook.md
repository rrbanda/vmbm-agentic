# Phase 3 -- Working Session Runbook

**Duration**: 30-45 minutes
**Format**: Screen share with customer
**Goal**: Customer sees the agent trigger a real Ansible pre-migration assessment on their VM and analyze the actual output

---

## Before the Session

- [ ] Phase 2 deployed and working (live VM inventory)
- [ ] AAP Controller URL and token configured
- [ ] Pre-migration assessment playbook deployed as a Job Template in AAP
- [ ] Template ID known (or discoverable via list_job_templates)
- [ ] This branch (`phase-3-aap-assessment`) checked out

---

## Session Start (2 min)

**Say:**

> "In previous sessions we showed the AI analyzing sample data and discovering your real VMs. Today we connect to your Ansible Automation Platform. The agent will trigger your actual pre-migration assessment playbook on a real VM and analyze the live output."

---

## Step 1: Deploy Phase 3 (3 min)

```bash
./scripts/deploy-phase3.sh
```

**Narrate:** "This adds the AAP integration tools. The agent can now launch Ansible playbooks, poll their status, and retrieve the output."

---

## Step 2: Confirm AAP Connectivity (3 min)

**Type:**

```
List the available AAP job templates
```

**Walk through:** "These are the job templates configured in your AAP. You can see the pre-migration assessment template with its ID."

---

## Step 3: Run Live Pre-Migration Assessment (15 min -- Hero Moment)

**Say:** "Now let's run the real pre-migration assessment on one of your VMs."

**Type (use a real VM name from Phase 2):**

```
Run a pre-migration assessment for <vm-name>
```

**Narrate as it runs:**

> "The agent just launched the pre-migration playbook on AAP..."
>
> "It's polling the job status... waiting for the playbook to complete..."
>
> "Job completed. Now it's retrieving the full playbook output..."
>
> "Loading the Ansible output parser skill..."
>
> "Analyzing the output against all 36 pre-migration checks..."
>
> "Generating the readiness report..."

**When the report appears:**

> "This is your real VM's readiness status -- not sample data. Notice the blockers and warnings reflect the actual state of this VM in your environment."

---

## Step 4: Compare with Sample (3 min)

**Say:** "Let's compare with the sample data analysis from Phase 1."

**Type:**

```
Analyze the sample pre-migration output
```

**Point out:** "See how the findings are different? The sample VM was READY with LOW risk. Your real VM may have different blockers based on its actual configuration."

---

## Step 5: All Previous Capabilities Still Work (2 min)

```
List VMware VMs in <namespace>
```

```
Check connectivity to all configured systems
```

---

## Wrap-Up (5 min)

**Say:**

> "Today we proved the full assessment loop works end-to-end:
> 1. The agent triggered your real Ansible playbook via AAP
> 2. It waited for completion and retrieved the actual output
> 3. It analyzed 36 checks from the real VM state
> 4. It produced a formal readiness report with real blockers and remediation
>
> In our next session (Phase 4), we'll add migration execution -- the agent will be able to trigger actual VMware-to-OCP Virt migrations, with a mandatory human approval gate."

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "AAP not configured" | Set AAP_URL and AAP_TOKEN: `oc set env deployment/adk-web -c adk-api AAP_URL=<url>` + create aap-agent-token Secret |
| "Failed to launch job: 404" | Template ID doesn't exist. Use `list_job_templates` to find the correct ID |
| "Failed to launch job: 403" | AAP token doesn't have permission to launch templates. Check AAP user permissions. |
| "Job still running after 5+ minutes" | Playbook may be slow. Agent will keep polling. If stuck, check AAP UI directly. |
| "Failed to get job output: 403" | Token can launch but can't read output. Check AAP RBAC for stdout access. |
