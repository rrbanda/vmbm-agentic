#!/bin/bash
# =============================================================================
# Deploy Phase 1 -- Adds skills and report generation
# =============================================================================
# Upgrades the agent from Phase 0 to Phase 1. Updates the image and
# adds SKILLS_DIR configuration.
#
# Usage: ./scripts/deploy-phase1.sh [namespace] [agent-image]
# Prerequisites: Phase 0 deployed and working
# =============================================================================

set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

NAMESPACE=${1:-adk-web}
AGENT_IMAGE=${2:-quay.io/rbrhssa/vmbm-agent:phase1}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

echo ""
echo "=============================================="
echo "  Phase 1: Adding Skills and Demo Mode"
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
    echo -e "${RED}ERROR: Phase 0 not deployed. Run deploy-phase0.sh first.${NC}"
    exit 1
fi
echo -e "${GREEN}  Phase 0 found. Upgrading to Phase 1.${NC}"
echo ""

echo -e "${BLUE}[2/3] Updating deployment...${NC}"
oc set image deployment/adk-web adk-api="$AGENT_IMAGE" -n "$NAMESPACE" 2>/dev/null
oc set env deployment/adk-web -n "$NAMESPACE" -c adk-api SKILLS_DIR=/skills 2>/dev/null
echo -e "${GREEN}  Deployment updated${NC}"
echo ""

echo -e "${BLUE}[3/3] Restarting agent...${NC}"
oc rollout restart deployment/adk-web -n "$NAMESPACE" 2>/dev/null
oc rollout status deployment/adk-web -n "$NAMESPACE" --timeout=120s 2>/dev/null

ROUTE=$(oc get route adk-web -n "$NAMESPACE" -o jsonpath='{.spec.host}' 2>/dev/null)

echo ""
echo "=============================================="
echo -e "  ${GREEN}Phase 1 Deployment Complete${NC}"
echo "=============================================="
echo ""
echo "  Agent UI: https://$ROUTE"
echo ""
echo "  Try: \"What skills do you have available?\""
echo "  Try: \"Analyze the sample pre-migration output\""
echo ""
