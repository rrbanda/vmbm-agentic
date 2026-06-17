#!/bin/bash
# =============================================================================
# Deploy Phase 4 -- Adds migration execution and monitoring
# =============================================================================
# Usage: ./scripts/deploy-phase4.sh [namespace] [agent-image]
# Prerequisites: Phase 3 deployed, MTV write access configured
# =============================================================================

set -euo pipefail
GREEN='\033[0;32m'; RED='\033[0;31m'; BLUE='\033[0;34m'; NC='\033[0m'

NAMESPACE=${1:-adk-web}
AGENT_IMAGE=${2:-quay.io/rbrhssa/vmbm-agent:phase4}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

echo ""
echo "=============================================="
echo "  Phase 4: Adding Migration Execution"
echo "  Namespace: $NAMESPACE"
echo "  Image: $AGENT_IMAGE"
echo "=============================================="
echo ""

echo -e "${BLUE}[1/3] Pre-flight checks...${NC}"
if ! oc whoami &>/dev/null 2>&1; then echo -e "${RED}ERROR: Not logged in.${NC}"; exit 1; fi
if ! oc get deployment adk-web -n "$NAMESPACE" &>/dev/null 2>&1; then echo -e "${RED}ERROR: Previous phase not deployed.${NC}"; exit 1; fi
echo -e "${GREEN}  Upgrading to Phase 4.${NC}"
echo ""

echo -e "${BLUE}[2/3] Updating deployment...${NC}"
oc set image deployment/adk-web adk-api="$AGENT_IMAGE" -n "$NAMESPACE" 2>/dev/null
echo -e "${GREEN}  Deployment updated${NC}"
echo ""

echo -e "${BLUE}[3/3] Restarting agent...${NC}"
oc rollout restart deployment/adk-web -n "$NAMESPACE" 2>/dev/null
oc rollout status deployment/adk-web -n "$NAMESPACE" --timeout=120s 2>/dev/null

ROUTE=$(oc get route adk-web -n "$NAMESPACE" -o jsonpath='{.spec.host}' 2>/dev/null)

echo ""
echo "=============================================="
echo -e "  ${GREEN}Phase 4 Deployment Complete${NC}"
echo "=============================================="
echo ""
echo "  Agent UI: https://$ROUTE"
echo ""
echo "  Try: \"Create a migration plan for <vm-name> in <namespace>\""
echo "       (requires human approval before executing)"
echo ""
echo "  Try: \"What is the current migration status?\""
echo "  Try: \"Show me the forklift logs\""
echo ""
