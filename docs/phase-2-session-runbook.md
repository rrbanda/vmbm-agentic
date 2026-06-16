# Phase 2 -- Working Session Runbook

**Duration**: 30 minutes
**Format**: Screen share with customer
**Goal**: Customer sees their real VMware VMs reflected in the agent's inventory -- live from their vCenter, not sample data

---

## Before the Session

- [ ] Phase 1 deployed and working (skills + sample analysis)
- [ ] MTV cluster token configured (from gather-config.sh or manually via `oc set env`)
- [ ] This branch (`phase-2-live-inventory`) checked out

---

## Session Start (2 min)

**Say:**

> "Last session we showed the AI analyzing sample Ansible output. Today we connect the agent to your live VMware environment. It will see your actual VMs -- real names, real specs, real power states. All read-only, nothing is modified."

---

## Step 1: Deploy Phase 2 (3 min)

```bash
./scripts/deploy-phase2.sh
```

**Narrate:** "This adds the VMware inventory tools. The agent can now query your MTV Forklift provider to discover VMs on your vSphere environment."

---

## Step 2: Discover VMware VMs (5 min)

**Type:**

```
List the VMware VMs available for migration
```

**Walk through the response:**

> "These are your real VMs from vCenter. You can see the name, power state, OS type, CPU count, memory, and disk size for each one. This is the same data your Python migration script reads from the spreadsheet -- but the agent gets it directly from the Forklift inventory API."

---

## Step 3: VM Details (3 min)

**Type (use a real VM name from step 2):**

```
Show me the details for <vm-name>
```

**Point out:** CPU cores, memory, disks, interfaces, labels, creation timestamp.

---

## Step 4: Already Migrated VMs (3 min)

**Type:**

```
What VMs have already been migrated to OCP Virtualization?
```

**Point out:** These are VMs that already exist on KubeVirt -- from previous migrations.

---

## Step 5: Migration Status (2 min)

**Type:**

```
What is the current migration status?
```

Shows any existing migration plans and their completion state.

---

## Step 6: Combine with Skills (5 min)

**Say:** "Now here's where it gets interesting -- the agent can combine live inventory data with its analysis skills."

**Type:**

```
Assess migration risk for <vm-name> based on its VMware inventory properties
```

The agent reads the VM's specs from the live inventory and applies the risk-assessor skill.

---

## Step 7: Connectivity + Skills Still Work (2 min)

```
Check connectivity to all configured systems
```

```
What skills do you have available?
```

---

## Wrap-Up (5 min)

**Say:**

> "Today we proved the agent can see your real VMware VMs. In our next session (Phase 3), we'll connect it to your Ansible Automation Platform so it can trigger pre-migration assessment playbooks and analyze the real output -- not sample data."

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "No VMware provider found" | Check `DEFAULT_MTV_NAMESPACE` env var matches the namespace with the vSphere provider |
| "Kubernetes API error: 401" | MTV token expired. Regenerate and update: `oc set env deployment/adk-web -c adk-api MTV_API_TOKEN=<new-token>` |
| "Kubernetes API error: 403" | Token doesn't have read access. Grant: `oc adm policy add-cluster-role-to-user cluster-reader <sa>` |
| "Error querying VMware inventory" | Check MTV inventory route is accessible from the agent pod |
