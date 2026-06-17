# Phase 5 -- Working Session Runbook

**Duration**: 30-45 minutes
**Format**: Screen share with customer
**Goal**: Customer sees the agent validate a migrated VM and produce a formal sign-off report

---

## Before the Session

- [ ] Phase 4 completed (at least one VM successfully migrated)
- [ ] AAP post-migration validation playbook available (optional -- can use sample data)
- [ ] OCP Virt accessible (already configured in Phase 4)

---

## Session Start (2 min)

**Say:**

> "This is our final phase. The agent will independently validate a migrated VM -- checking 39 post-migration criteria -- and produce a formal completion report that compares before and after state. This is the report your team uses for sign-off."

---

## Step 1: Deploy Phase 5 (2 min)

```bash
./scripts/deploy-phase5.sh <namespace> <registry>/vmbm-agent:phase5
```

---

## Step 2: Run Post-Migration Validation (10 min)

**If AAP post-migration template is configured:**

```
Run post-migration validation for <vm-name> in <namespace>
```

**If AAP is not configured (use sample data):**

```
Analyze the sample post-migration output and produce a validation report
```

**Walk through the 39 checks:**
- Platform verification (OpenShift Virtualization confirmed)
- ACM registration
- Pre/post fact comparison (CPU, memory, network)
- vCenter cleanup (renamed, NICs disconnected, powered off)
- Guest agent swap (VMware tools removed, qemu-ga installed)
- CMDB update
- Backup re-enrollment

---

## Step 3: Verify Migrated VM on OCP Virt (3 min)

```
Show me details of <vm-name> in <target-namespace>
```

**Compare with source:**

```
List VMware VMs in <mtv-namespace>
```

---

## Step 4: Generate Completion Report (5 min)

```
Generate the migration completion report for <vm-name>
```

**The report includes:**
- Migration summary (source, target, cluster, AZ)
- Before/after comparison table
- Pre-migration assessment summary
- Migration timeline
- Post-migration validation results
- Outstanding items
- Sign-off section

**Point out:** "This report appears as a downloadable artifact in the UI."

---

## Step 5: Full Workflow Recap (5 min)

**Say:**

> "Let me show you everything working together."

```
Check connectivity to all configured systems
```

```
List VMware VMs available for migration
```

```
What is the current migration status?
```

> "Over these 6 sessions, we've proven the complete migration workflow:
> Phase 0: Connectivity verification
> Phase 1: AI analysis engine with skills
> Phase 2: Live VMware inventory
> Phase 3: Ansible playbook integration
> Phase 4: Migration execution with human approval
> Phase 5: Validation and formal sign-off reporting
>
> The agent handles the repetitive analysis. Your engineers focus on decisions."

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "AAP not configured" for post-migration | Use sample data or set `POST_MIGRATION_TEMPLATE_ID` |
| Validation report missing before/after data | The agent needs both VMware inventory and OCP Virt VM details. Ensure both are accessible. |
| Report artifact not saving | Check `/app/.adk` is writable: verify `emptyDir` volume is mounted |
