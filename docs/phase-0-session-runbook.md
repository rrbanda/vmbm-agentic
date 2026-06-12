# Phase 0 -- Working Session Runbook

**Duration**: 30-45 minutes
**Format**: Screen share, walking the customer through each step
**Goal**: Agent deployed on customer's cluster, connectivity verified to all systems

---

## Before the Session (Your Prep)

- [ ] Confirm customer has provided: OpenShift cluster access (API URL + admin credentials)
- [ ] Confirm LLM endpoint URL is known (vLLM inference service on RHOAI)
- [ ] Have the repo cloned locally: `git clone https://github.com/rrbanda/vmbm-agentic.git && cd vmbm-agentic && git checkout phase-0-connectivity`
- [ ] Have this runbook open as your script

---

## Session Start -- Context Setting (5 min)

**Say to customer:**

> "Today we're going to deploy the migration agent on your OpenShift cluster and verify it can reach all the systems it needs -- your LLM, your MTV cluster, your OCP Virt environment, and your AAP. We won't read or modify any data today. This is purely a connectivity and trust verification session."

> "The agent is deployed incrementally in phases. Phase 0 -- what we're doing today -- proves the foundation works. In future sessions, we'll add VM discovery, assessment, migration execution, and reporting -- each as a separate, controlled step."

---

## Step 1: Environment Check (5 min)

**Say:** "Let's first make sure your cluster has everything we need."

**Run (on your machine or customer's terminal):**

```bash
cd vmbm-agentic
chmod +x scripts/*.sh
./scripts/env-check.sh
```

**Walk through the output with the customer:**
- "Here we can see your OpenShift version..."
- "RHOAI is installed -- that's where the LLM runs..."
- "MTV is installed -- that's the migration engine..."
- "OCP Virt is installed -- that's the target platform..."

**If anything fails:** Address it together. Common issues:
- Not logged in: `oc login https://<cluster-api>:6443 -u <user> -p <password>`
- Operator not installed: Note it as "planned for a later phase"

---

## Step 2: Gather Configuration (5 min)

**Say:** "Now I'll collect the specific endpoints and credentials for your environment."

**Run:**

```bash
./scripts/gather-config.sh
```

**Walk through each prompt:**

| Prompt | What to tell customer |
|--------|----------------------|
| LLM API base URL | "This is your vLLM inference service endpoint on RHOAI" |
| LLM API key | "If your vLLM doesn't require a key, we use 'not-needed'" |
| Model name | "This should match what your ServingRuntime exposes" |
| MTV cluster API URL | "This is the cluster where Forklift/MTV runs. Leave empty if it's this same cluster." |
| MTV bearer token | "A service account token with read access to the MTV namespace" |
| AAP Controller URL | "Your Ansible Automation Platform URL. We can skip this for today." |

**Say:** "Good -- configuration is saved. No secrets are stored in the repo."

---

## Step 3: Deploy the Agent (5-10 min)

**Say:** "Now we'll deploy the agent. This builds the container image directly on your cluster -- no external registries needed."

**Run:**

```bash
./scripts/deploy-phase0.sh
```

**Narrate as it runs:**
- "[1/7] Pre-flight checks... making sure we're logged in"
- "[2/7] Creating namespace... this is where the agent will live"
- "[3/7] Creating secrets... tokens are stored as Kubernetes Secrets"
- "[4/7] Building the image... this compiles the agent code into a container, right here on your cluster. Takes about 90 seconds."
- "[5/7] Configuring pull access..."
- "[6/7] Deploying... two containers: the web UI and the agent API"
- "[7/7] Waiting for ready..."

**When it completes, the script shows the UI URL.**

---

## Step 4: Verify Connectivity (5 min)

**Say:** "The agent is running. Let's verify it can reach everything."

**Option A: Via script (good for recording evidence)**

```bash
./scripts/validate-phase0.sh
```

**Option B: Via the UI (better for live demo)**

1. Open the URL shown by the deploy script
2. Click "New Session"
3. Type:

```
Check connectivity to all configured systems and show me the status of each integration.
```

**Walk through the response with the customer:**

> "You can see the agent has verified 6 systems:
> - The ADK server itself is healthy
> - The LLM endpoint is responding -- this is gpt-oss-120b on your RHOAI
> - The MTV Kubernetes API is connected -- this means we can discover your VMware VMs in the next phase
> - [etc. for each system]"
>
> "Systems marked 'Not Configured' are expected -- those integrations are for later phases."

---

## Step 5: Additional Prompts to Try (5 min)

Let the customer try these to build confidence:

```
What systems are you connected to?
```

```
What can you do right now?
```

```
What capabilities will be added in future phases?
```

The agent will explain its current Phase 0 limitations and what's coming next.

---

## Wrap-Up (5 min)

**Say:**

> "Today we proved three things:
> 1. The agent runs securely on your cluster -- no data leaves your environment
> 2. It can authenticate to all the systems it needs for migration
> 3. It tells you transparently what it can and cannot do
>
> In our next session (Phase 1), we'll activate the analysis skills and show the agent analyzing real Ansible playbook output -- producing a full migration readiness report with risk ratings, blockers, and remediation steps. All using bundled sample data, so still zero risk to your environment.
>
> Any questions?"

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Build fails with "permission denied" | `oc adm policy add-role-to-user edit system:serviceaccount:<ns>:builder -n <ns>` |
| Pod stuck in `ImagePullBackOff` | Run `oc policy add-role-to-user system:image-puller system:serviceaccount:<ns>:default -n <ns>` |
| LLM shows "Failed" in connectivity | Check the LLM route timeout: `oc annotate route <llm-route> -n <llm-ns> --overwrite haproxy.router.openshift.io/timeout=600s` |
| Agent shows "Not Configured" for MTV | Expected if MTV credentials weren't provided. Will be configured in Phase 2. |
| "504 Gateway Timeout" on complex prompts | Increase the LLM route timeout (see above) |
| Pod shows 0/2 containers | Check logs: `oc logs <pod-name> -c adk-api -n <ns>` |

---

## Files Reference

| File | Purpose |
|------|---------|
| `scripts/env-check.sh` | Validates cluster prerequisites |
| `scripts/gather-config.sh` | Collects environment values interactively |
| `scripts/deploy-phase0.sh` | Full deploy lifecycle (build + deploy + configure) |
| `scripts/validate-phase0.sh` | Automated connectivity test via agent API |
| `config/agent.env` | Generated environment configuration (gitignored) |
| `config/secrets.sh` | Generated secret creation script (gitignored) |
| `docs/phase-0-guide.md` | Technical reference + glossary + architecture |
