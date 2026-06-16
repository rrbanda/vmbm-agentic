#!/bin/bash
# =============================================================================
# Deploy Phase 3 -- Adds AAP integration for live pre-migration assessment
# =============================================================================
# Usage: ./scripts/deploy-phase3.sh [namespace] [agent-image]
# Prerequisites: Phase 2 deployed, AAP Controller reachable
# =============================================================================

set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

NAMESPACE=${1:-adk-web}
AGENT_IMAGE=${2:-quay.io/rbrhssa/vmbm-agent:phase3}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

echo ""
echo "=============================================="
echo "  Phase 3: Adding AAP Integration"
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
echo -e "${GREEN}  Deployment found. Upgrading to Phase 3.${NC}"
echo ""

echo -e "${BLUE}[2/3] Updating deployment...${NC}"
oc set image deployment/adk-web adk-api="$AGENT_IMAGE" -n "$NAMESPACE" 2>/dev/null

if [ -f "$REPO_DIR/config/agent.env" ]; then
    source "$REPO_DIR/config/agent.env"
    oc set env deployment/adk-web -n "$NAMESPACE" -c adk-api \
        AAP_URL="${AAP_URL:-}" \
        AAP_API_PREFIX="${AAP_API_PREFIX:-/api/controller/v2}" \
        PRE_MIGRATION_TEMPLATE_ID="${PRE_MIGRATION_TEMPLATE_ID:-}" \
        POST_MIGRATION_TEMPLATE_ID="${POST_MIGRATION_TEMPLATE_ID:-}" \
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
echo -e "  ${GREEN}Phase 3 Deployment Complete${NC}"
echo "=============================================="
echo ""
echo "  Agent UI: https://$ROUTE"
echo ""
echo "  Try: \"List the available AAP job templates\""
echo "  Try: \"Run a pre-migration assessment for <vm-name>\""
echo ""
