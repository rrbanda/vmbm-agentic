#!/bin/bash
# =============================================================================
# Deploy Phase 0 -- Deploys the migration agent for connectivity verification
# =============================================================================
# This script handles everything:
#   - Creates the namespace
#   - Builds the agent image on OpenShift (no local podman needed)
#   - Creates secrets from config/secrets.sh
#   - Deploys the agent with correct env vars from config/agent.env
#   - Waits for the pod to be ready
#   - Prints the UI URL
#
# Usage: ./scripts/deploy-phase0.sh [namespace]
# Prerequisites: Run ./scripts/gather-config.sh first
# =============================================================================

set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

NAMESPACE=${1:-adk-web}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

echo ""
echo "=============================================="
echo "  Phase 0: Deploying Migration Agent"
echo "  Namespace: $NAMESPACE"
echo "=============================================="
echo ""

# =============================================================================
# Pre-flight checks
# =============================================================================
echo -e "${BLUE}[1/7] Pre-flight checks...${NC}"

if ! oc whoami &>/dev/null 2>&1; then
    echo -e "${RED}ERROR: Not logged into OpenShift. Run 'oc login' first.${NC}"
    exit 1
fi
echo "  Logged in as: $(oc whoami)"
echo "  Cluster: $(oc whoami --show-server)"

if [ ! -f "$REPO_DIR/config/agent.env" ]; then
    echo -e "${RED}ERROR: config/agent.env not found.${NC}"
    echo "  Run ./scripts/gather-config.sh first to generate configuration."
    exit 1
fi

echo -e "${GREEN}  Pre-flight OK${NC}"
echo ""

# =============================================================================
# Create namespace
# =============================================================================
echo -e "${BLUE}[2/7] Creating namespace '$NAMESPACE'...${NC}"
oc create namespace "$NAMESPACE" --dry-run=client -o yaml | oc apply -f - 2>/dev/null || true
echo -e "${GREEN}  Namespace ready${NC}"
echo ""

# =============================================================================
# Create secrets
# =============================================================================
echo -e "${BLUE}[3/7] Creating secrets...${NC}"
if [ -f "$REPO_DIR/config/secrets.sh" ]; then
    bash "$REPO_DIR/config/secrets.sh" "$NAMESPACE"
    echo -e "${GREEN}  Secrets created${NC}"
else
    echo -e "${YELLOW}  No secrets.sh found -- skipping (tokens can be added later)${NC}"
fi
echo ""

# =============================================================================
# Build agent image on OpenShift (no local container runtime needed)
# =============================================================================
echo -e "${BLUE}[4/7] Building agent image on OpenShift...${NC}"
echo "  This builds the container image directly on the cluster."
echo "  No local podman/docker required."
echo ""

# Create BuildConfig if it doesn't exist
if ! oc get bc adk-agent-build -n "$NAMESPACE" &>/dev/null 2>&1; then
    echo "  Creating BuildConfig..."
    oc new-build --strategy=docker --binary --name=adk-agent-build \
        --to='adk-agent:phase0' -n "$NAMESPACE" 2>/dev/null
    oc patch bc/adk-agent-build -n "$NAMESPACE" \
        -p '{"spec":{"strategy":{"dockerStrategy":{"dockerfilePath":"deploy/Dockerfile.agent"}}}}' 2>/dev/null
fi

# Start the build
echo "  Uploading source and building... (this takes ~90 seconds)"
oc start-build adk-agent-build --from-dir="$REPO_DIR" --follow -n "$NAMESPACE" 2>&1 | tail -3

# Get the image reference
IMAGE=$(oc get istag adk-agent:phase0 -n "$NAMESPACE" -o jsonpath='{.image.dockerImageReference}' 2>/dev/null)
if [ -z "$IMAGE" ]; then
    echo -e "${RED}ERROR: Image build failed. Check 'oc get builds -n $NAMESPACE' for details.${NC}"
    exit 1
fi
echo -e "${GREEN}  Image built: ${IMAGE##*@}${NC}"
echo ""

# =============================================================================
# Grant image pull access
# =============================================================================
echo -e "${BLUE}[5/7] Configuring image pull access...${NC}"
oc policy add-role-to-user system:image-puller "system:serviceaccount:${NAMESPACE}:default" \
    -n "$NAMESPACE" 2>/dev/null || true
echo -e "${GREEN}  Pull access granted${NC}"
echo ""

# =============================================================================
# Deploy the agent
# =============================================================================
echo -e "${BLUE}[6/7] Deploying agent...${NC}"

# Load config values
source "$REPO_DIR/config/agent.env"

# Apply the base manifests (ConfigMap, Service, Route)
oc apply -f "$REPO_DIR/deploy/openshift.yaml" -n "$NAMESPACE" 2>/dev/null

# Patch the deployment to use our built image instead of quay.io placeholder
oc set image deployment/adk-web adk-api="$IMAGE" -n "$NAMESPACE" 2>/dev/null

# Set all env vars from agent.env (overwrites placeholders in YAML)
oc set env deployment/adk-web -n "$NAMESPACE" -c adk-api \
    OPENAI_API_BASE="${OPENAI_API_BASE:-}" \
    OPENAI_API_KEY="${OPENAI_API_KEY:-not-needed}" \
    ADK_MODEL="${ADK_MODEL:-openai/gpt-oss-120b}" \
    AGENT_NAME="${AGENT_NAME:-migration_agent}" \
    AGENT_MODE="${AGENT_MODE:-single}" \
    ADK_TEMPERATURE="${ADK_TEMPERATURE:-0.2}" \
    ADK_MAX_OUTPUT_TOKENS="${ADK_MAX_OUTPUT_TOKENS:-4096}" \
    MTV_API_URL="${MTV_API_URL:-}" \
    VIRT_API_URL="${VIRT_API_URL:-}" \
    MTV_INVENTORY_URL="${MTV_INVENTORY_URL:-}" \
    AAP_URL="${AAP_URL:-}" \
    DEFAULT_MTV_NAMESPACE="${DEFAULT_MTV_NAMESPACE:-mtv-user1}" \
    DEFAULT_VIRT_NAMESPACE="${DEFAULT_VIRT_NAMESPACE:-vmimported-user1}" \
    MTV_OPERATOR_NAMESPACE="${MTV_OPERATOR_NAMESPACE:-openshift-mtv}" \
    2>/dev/null

# Set route timeout for long LLM calls
oc annotate route adk-web -n "$NAMESPACE" --overwrite \
    haproxy.router.openshift.io/timeout=600s 2>/dev/null || true

echo -e "${GREEN}  Deployment configured${NC}"
echo ""

# =============================================================================
# Wait for rollout
# =============================================================================
echo -e "${BLUE}[7/7] Waiting for pod to be ready...${NC}"

# Scale cycle to ensure clean start with new image
oc scale deployment/adk-web --replicas=0 -n "$NAMESPACE" 2>/dev/null
sleep 5
oc scale deployment/adk-web --replicas=1 -n "$NAMESPACE" 2>/dev/null

if oc rollout status deployment/adk-web -n "$NAMESPACE" --timeout=120s 2>/dev/null; then
    echo -e "${GREEN}  Pod is ready (2/2 containers running)${NC}"
else
    echo -e "${RED}  Rollout timed out. Check: oc get pods -n $NAMESPACE${NC}"
    exit 1
fi
echo ""

# =============================================================================
# Summary
# =============================================================================
ROUTE=$(oc get route adk-web -n "$NAMESPACE" -o jsonpath='{.spec.host}' 2>/dev/null)
API_CHECK=$(curl -sk --max-time 10 "https://$ROUTE/api/list-apps" 2>/dev/null || echo "")

echo "=============================================="
echo -e "  ${GREEN}Phase 0 Deployment Complete${NC}"
echo "=============================================="
echo ""
echo "  Agent UI:     https://$ROUTE"
echo "  Agent API:    https://$ROUTE/api/list-apps"
if echo "$API_CHECK" | grep -q "app"; then
    echo -e "  Health:       ${GREEN}Healthy${NC}"
else
    echo -e "  Health:       ${YELLOW}Starting up (may take 15-20s for first response)${NC}"
fi
echo ""
echo "  ┌─────────────────────────────────────────────────────────────┐"
echo "  │  Open the UI and try this prompt:                           │"
echo "  │                                                             │"
echo "  │  \"Check connectivity to all configured systems and show    │"
echo "  │   me the status of each integration.\"                      │"
echo "  │                                                             │"
echo "  └─────────────────────────────────────────────────────────────┘"
echo ""
echo "  Or run: ./scripts/validate-phase0.sh $NAMESPACE"
echo ""
