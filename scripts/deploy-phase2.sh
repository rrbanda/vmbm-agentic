#!/bin/bash
# =============================================================================
# Deploy Phase 2 -- Adds live VM inventory (read-only MTV access)
# =============================================================================
# Usage: ./scripts/deploy-phase2.sh [namespace] [agent-image]
# Prerequisites: Phase 1 deployed and working, MTV cluster accessible
# =============================================================================

set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

NAMESPACE=${1:-adk-web}
AGENT_IMAGE=${2:-quay.io/rbrhssa/vmbm-agent:phase2}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

echo ""
echo "=============================================="
echo "  Phase 2: Adding Live VM Inventory"
echo "  Namespace: $NAMESPACE"
echo "  Image: $AGENT_IMAGE"
echo "=============================================="
echo ""

echo -e "${BLUE}[1/3] Pre-flight checks...${NC}"
if ! oc whoami &>/dev/null 2>&1; then
    echo -e "${RED}ERROR: Not logged into OpenShift.${NC}"
    exit 1
fi
if ! oc get deployment adk-web -n "$NAMESPACE" &>/dev/null 2>&1; then
    echo -e "${RED}ERROR: Previous phase not deployed.${NC}"
    exit 1
fi
echo -e "${GREEN}  Deployment found. Upgrading to Phase 2.${NC}"
echo ""

echo -e "${BLUE}[2/3] Updating deployment...${NC}"
oc set image deployment/adk-web adk-api="$AGENT_IMAGE" -n "$NAMESPACE" 2>/dev/null

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

echo -e "${BLUE}[3/3] Restarting agent...${NC}"
oc rollout restart deployment/adk-web -n "$NAMESPACE" 2>/dev/null
oc rollout status deployment/adk-web -n "$NAMESPACE" --timeout=120s 2>/dev/null

ROUTE=$(oc get route adk-web -n "$NAMESPACE" -o jsonpath='{.spec.host}' 2>/dev/null)

echo ""
echo "=============================================="
echo -e "  ${GREEN}Phase 2 Deployment Complete${NC}"
echo "=============================================="
echo ""
echo "  Agent UI: https://$ROUTE"
echo ""
echo "  Try: \"List VMware VMs available for migration\""
echo ""
