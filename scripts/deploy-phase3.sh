#!/bin/bash
# =============================================================================
# Deploy Phase 3 -- Adds AAP integration for live pre-migration assessment
# =============================================================================
# Incremental update on top of Phase 2. Rebuilds the image with AAP tools.
#
# Usage: ./scripts/deploy-phase3.sh [namespace]
# Prerequisites: Phase 2 deployed, AAP Controller reachable
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
echo "  Phase 3: Adding AAP Integration"
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
    echo -e "${RED}ERROR: Previous phase not deployed.${NC}"
    exit 1
fi

echo -e "${GREEN}  Deployment found. Upgrading to Phase 3.${NC}"
echo ""

# --- Rebuild image ---
echo -e "${BLUE}[2/4] Rebuilding agent image (now includes AAP tools)...${NC}"
oc start-build adk-agent-build --from-dir="$REPO_DIR" --follow -n "$NAMESPACE" 2>&1 | tail -3

IMAGE=$(oc get istag adk-agent:phase0 -n "$NAMESPACE" -o jsonpath='{.image.dockerImageReference}' 2>/dev/null)
if [ -z "$IMAGE" ]; then
    echo -e "${RED}ERROR: Build failed.${NC}"
    exit 1
fi
echo -e "${GREEN}  Image rebuilt with AAP tools${NC}"
echo ""

# --- Update deployment ---
echo -e "${BLUE}[3/4] Updating deployment...${NC}"

oc set image deployment/adk-web adk-api="$IMAGE" -n "$NAMESPACE" 2>/dev/null

# Set AAP env vars if config exists
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

# --- Restart ---
echo -e "${BLUE}[4/4] Restarting agent...${NC}"
oc scale deployment/adk-web --replicas=0 -n "$NAMESPACE" 2>/dev/null
sleep 8
oc scale deployment/adk-web --replicas=1 -n "$NAMESPACE" 2>/dev/null
oc rollout status deployment/adk-web -n "$NAMESPACE" --timeout=120s 2>/dev/null

ROUTE=$(oc get route adk-web -n "$NAMESPACE" -o jsonpath='{.spec.host}' 2>/dev/null)

echo ""
echo "=============================================="
echo -e "  ${GREEN}Phase 3 Deployment Complete${NC}"
echo "=============================================="
echo ""
echo "  Agent UI: https://$ROUTE"
echo ""
echo "  The agent can now trigger AAP playbooks."
echo "  Try these prompts:"
echo ""
echo "    \"List the available AAP job templates\""
echo ""
echo "    \"Run a pre-migration assessment for <vm-name>\""
echo ""
