#!/bin/bash
# =============================================================================
# Deploy Phase 2 -- Adds live VM inventory tools (read-only MTV access)
# =============================================================================
# Incremental update on top of Phase 1. Rebuilds the image with MTV tools
# and updates the agent configuration.
#
# Usage: ./scripts/deploy-phase2.sh [namespace]
# Prerequisites: Phase 1 deployed and working, MTV cluster accessible
# =============================================================================

set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

NAMESPACE=${1:-adk-web}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

echo ""
echo "=============================================="
echo "  Phase 2: Adding Live VM Inventory"
echo "  Namespace: $NAMESPACE"
echo "=============================================="
echo ""

# --- Pre-flight ---
echo -e "${BLUE}[1/4] Pre-flight checks...${NC}"

if ! oc whoami &>/dev/null 2>&1; then
    echo -e "${RED}ERROR: Not logged into OpenShift.${NC}"
    exit 1
fi

if ! oc get deployment adk-web -n "$NAMESPACE" &>/dev/null 2>&1; then
    echo -e "${RED}ERROR: Phase 1 not deployed. Run deploy-phase1.sh first.${NC}"
    exit 1
fi

echo -e "${GREEN}  Phase 1 deployment found. Upgrading to Phase 2.${NC}"
echo ""

# --- Rebuild image ---
echo -e "${BLUE}[2/4] Rebuilding agent image (now includes MTV/OCP Virt tools)...${NC}"
oc start-build adk-agent-build --from-dir="$REPO_DIR" --follow -n "$NAMESPACE" 2>&1 | tail -3

IMAGE=$(oc get istag adk-agent:phase0 -n "$NAMESPACE" -o jsonpath='{.image.dockerImageReference}' 2>/dev/null)
if [ -z "$IMAGE" ]; then
    echo -e "${RED}ERROR: Build failed.${NC}"
    exit 1
fi
echo -e "${GREEN}  Image rebuilt with VM inventory tools${NC}"
echo ""

# --- Update deployment ---
echo -e "${BLUE}[3/4] Updating deployment...${NC}"

oc set image deployment/adk-web adk-api="$IMAGE" -n "$NAMESPACE" 2>/dev/null

# Set MTV/Virt env vars if config exists
if [ -f "$REPO_DIR/config/agent.env" ]; then
    source "$REPO_DIR/config/agent.env"
    oc set env deployment/adk-web -n "$NAMESPACE" -c adk-api \
        MTV_API_URL="${MTV_API_URL:-}" \
        VIRT_API_URL="${VIRT_API_URL:-}" \
        MTV_INVENTORY_URL="${MTV_INVENTORY_URL:-}" \
        DEFAULT_MTV_NAMESPACE="${DEFAULT_MTV_NAMESPACE:-mtv-user1}" \
        DEFAULT_VIRT_NAMESPACE="${DEFAULT_VIRT_NAMESPACE:-vmimported-user1}" \
        MTV_OPERATOR_NAMESPACE="${MTV_OPERATOR_NAMESPACE:-openshift-mtv}" \
        2>/dev/null
fi

echo -e "${GREEN}  Deployment updated${NC}"
echo ""

# --- Restart ---
echo -e "${BLUE}[4/4] Restarting agent...${NC}"
oc scale deployment/adk-web --replicas=0 -n "$NAMESPACE" 2>/dev/null
sleep 8
oc scale deployment/adk-web --replicas=1 -n "$NAMESPACE" 2>/dev/null
oc rollout status deployment/adk-web -n "$NAMESPACE" --timeout=120s 2>/dev/null

ROUTE=$(oc get route adk-web -n "$NAMESPACE" -o jsonpath='{.spec.host}' 2>/dev/null)

echo ""
echo "=============================================="
echo -e "  ${GREEN}Phase 2 Deployment Complete${NC}"
echo "=============================================="
echo ""
echo "  Agent UI: https://$ROUTE"
echo ""
echo "  The agent can now discover live VMware VMs."
echo "  Try these prompts:"
echo ""
echo "    \"List the VMware VMs available for migration\""
echo ""
echo "    \"Show me details for <vm-name>\""
echo ""
echo "    \"What VMs have already been migrated?\""
echo ""
