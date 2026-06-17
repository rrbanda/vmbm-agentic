# Phase 4 -- Working Session Runbook

**Duration**: 30-45 minutes
**Format**: Screen share with customer
**Goal**: Customer sees the agent trigger a real migration with human approval, monitor progress, and troubleshoot using logs

---

## Before the Session

- [ ] Phase 3 deployed and working
- [ ] MTV token has write access (create Plan, NetworkMap, StorageMap, Migration CRs)
- [ ] Storage class available for VM disk PVCs
- [ ] Target namespace exists for migrated VMs
- [ ] At least one VM available for migration test

---

## Session Start (2 min)

**Say:**

> "Today we add migration execution. The agent can now trigger real VMware-to-OCP Virt migrations, but only with your explicit approval. Nothing executes without you clicking Confirm."

---

## Step 1: Deploy Phase 4 (2 min)

```bash
./scripts/deploy-phase4.sh <namespace> <registry>/vmbm-agent:phase4
```

---

## Step 2: Trigger Migration with Approval Gate (10 min)

**Type:**

```
Create a migration plan for <vm-name> in <mtv-namespace>
```

**Walk through:**
> "The agent prepared the migration plan. See the confirmation dialog? It shows the VM name and namespace. The migration is PAUSED until you approve."

**Click Confirm.** Then:

> "The agent created the NetworkMap, StorageMap, Plan, and Migration CRs on MTV. The migration has started."

---

## Step 3: Monitor Progress (5 min)

**Type:**

```
What is the current migration status?
```

**Shows:** Plan phase, VMs completed/running/failed, timestamps.

---

## Step 4: Read Logs (5 min)

**Type:**

```
Show me the forklift logs for the current migration
```

**If errors found, type:**

```
Diagnose the error using the mtv-log-analyzer skill
```

---

## Step 5: Verify Migrated VM (3 min)

**Type:**

```
Show me details of <vm-name> in <target-namespace>
```

**Shows:** The migrated VM on OCP Virt with CPU, memory, disks.

---

## Wrap-Up (3 min)

> "Today we proved the agent can execute real migrations with human oversight. In our final session (Phase 5), the agent will independently validate the migrated VM and produce a formal sign-off report."

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "Kubernetes API error: 403" on create | Token needs write access: `oc adm policy add-cluster-role-to-user edit <sa>` |
| Migration stuck at Ready | Check storage class: `oc get sc` and set `TARGET_STORAGE_CLASS` env var |
| "VM already migrated" | Agent detects existing plans. Clean up old plans or use a different VM. |
| Approval dialog not appearing | Check LLM supports tool calling (`--enable-auto-tool-choice`) |
