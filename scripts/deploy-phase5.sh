#!/bin/bash
# =============================================================================
# Deploy Phase 5 -- Adds post-migration validation and completion reports
# =============================================================================
# Usage: ./scripts/deploy-phase5.sh [namespace] [agent-image]
# Prerequisites: Phase 4 deployed, at least one VM migrated
# =============================================================================

set -euo pipefail
GREEN='\033[0;32m'; RED='\033[0;31m'; BLUE='\033[0;34m'; NC='\033[0m'

NAMESPACE=${1:-adk-web}
AGENT_IMAGE=${2:-quay.io/rbrhssa/vmbm-agent:phase5}

echo ""
echo "=============================================="
echo "  Phase 5: Adding Post-Migration Validation"
echo "  Namespace: $NAMESPACE"
echo "  Image: $AGENT_IMAGE"
echo "=============================================="
echo ""

echo -e "${BLUE}[1/3] Pre-flight checks...${NC}"
if ! oc whoami &>/dev/null 2>&1; then echo -e "${RED}ERROR: Not logged in.${NC}"; exit 1; fi
if ! oc get deployment adk-web -n "$NAMESPACE" &>/dev/null 2>&1; then echo -e "${RED}ERROR: Previous phase not deployed.${NC}"; exit 1; fi
echo -e "${GREEN}  Upgrading to Phase 5.${NC}"
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
echo -e "  ${GREEN}Phase 5 Deployment Complete${NC}"
echo "=============================================="
echo ""
echo "  Agent UI: https://$ROUTE"
echo ""
echo "  Try: \"Run post-migration validation for <vm-name>\""
echo "  Try: \"Generate the migration completion report\""
echo ""
