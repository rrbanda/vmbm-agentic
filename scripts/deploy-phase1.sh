#!/bin/bash
# =============================================================================
# Deploy Phase 1 -- Adds skills and report generation to the agent
# =============================================================================
# This is an INCREMENTAL update on top of Phase 0. It rebuilds the image
# (now includes skills) and restarts the agent.
#
# Usage: ./scripts/deploy-phase1.sh [namespace]
# Prerequisites: Phase 0 deployed and working
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
echo "  Phase 1: Adding Skills and Demo Mode"
echo "  Namespace: $NAMESPACE"
echo "=============================================="
echo ""

# --- Pre-flight ---
echo -e "${BLUE}[1/4] Pre-flight checks...${NC}"

if ! oc whoami &>/dev/null 2>&1; then
    echo -e "${RED}ERROR: Not logged into OpenShift.${NC}"
    exit 1
fi

# Check Phase 0 is deployed
if ! oc get deployment adk-web -n "$NAMESPACE" &>/dev/null 2>&1; then
    echo -e "${RED}ERROR: Phase 0 not deployed. Run deploy-phase0.sh first.${NC}"
    exit 1
fi

echo -e "${GREEN}  Phase 0 deployment found. Upgrading to Phase 1.${NC}"
echo ""

# --- Rebuild image with skills ---
echo -e "${BLUE}[2/4] Rebuilding agent image (now includes 11 skills)...${NC}"
echo "  This adds ~50 files of domain knowledge to the container."
echo ""

oc start-build adk-agent-build --from-dir="$REPO_DIR" --follow -n "$NAMESPACE" 2>&1 | tail -3

IMAGE=$(oc get istag adk-agent:phase0 -n "$NAMESPACE" -o jsonpath='{.image.dockerImageReference}' 2>/dev/null)
if [ -z "$IMAGE" ]; then
    echo -e "${RED}ERROR: Build failed.${NC}"
    exit 1
fi
echo -e "${GREEN}  Image rebuilt with skills${NC}"
echo ""

# --- Update deployment ---
echo -e "${BLUE}[3/4] Updating deployment...${NC}"

oc set image deployment/adk-web adk-api="$IMAGE" -n "$NAMESPACE" 2>/dev/null
oc set env deployment/adk-web -n "$NAMESPACE" -c adk-api SKILLS_DIR=/skills 2>/dev/null

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
echo -e "  ${GREEN}Phase 1 Deployment Complete${NC}"
echo "=============================================="
echo ""
echo "  Agent UI: https://$ROUTE"
echo ""
echo "  The agent now has 11 analysis skills loaded."
echo "  Try these prompts:"
echo ""
echo "    \"What skills do you have available?\""
echo ""
echo "    \"Analyze the sample pre-migration output and"
echo "     produce a readiness assessment report\""
echo ""
echo "    \"Assess migration risk for a RHEL 7 VM with"
echo "     500GB disk and no backup\""
echo ""
