#!/bin/bash
# =============================================================================
# Deploy Phase 0 -- Deploys the migration agent for connectivity verification
# =============================================================================
# Deploys the pre-built agent image. Customer mirrors the image to their
# internal registry before running this script.
#
# Usage: ./scripts/deploy-phase0.sh [namespace] [agent-image] [web-image]
# Prerequisites: Run ./scripts/gather-config.sh first
# =============================================================================

set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

NAMESPACE=${1:-adk-web}
AGENT_IMAGE=${2:-quay.io/rbrhssa/vmbm-agent:phase0}
WEB_IMAGE=${3:-quay.io/rbrhssa/adk-web:oidc}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

echo ""
echo "=============================================="
echo "  Phase 0: Deploying Migration Agent"
echo "  Namespace: $NAMESPACE"
echo "  Agent image: $AGENT_IMAGE"
echo "  Web image: $WEB_IMAGE"
echo "=============================================="
echo ""

# =============================================================================
# Pre-flight checks
# =============================================================================
echo -e "${BLUE}[1/5] Pre-flight checks...${NC}"

if ! oc whoami &>/dev/null 2>&1; then
    echo -e "${RED}ERROR: Not logged into OpenShift. Run 'oc login' first.${NC}"
    exit 1
fi
echo "  Logged in as: $(oc whoami)"

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
echo -e "${BLUE}[2/5] Creating namespace '$NAMESPACE'...${NC}"
oc create namespace "$NAMESPACE" --dry-run=client -o yaml | oc apply -f - 2>/dev/null || true
echo -e "${GREEN}  Namespace ready${NC}"
echo ""

# =============================================================================
# Create secrets
# =============================================================================
echo -e "${BLUE}[3/5] Creating secrets...${NC}"
if [ -f "$REPO_DIR/config/secrets.sh" ]; then
    bash "$REPO_DIR/config/secrets.sh" "$NAMESPACE"
    echo -e "${GREEN}  Secrets created${NC}"
else
    echo -e "${YELLOW}  No secrets.sh found -- skipping${NC}"
fi
echo ""

# =============================================================================
# Deploy
# =============================================================================
echo -e "${BLUE}[4/5] Deploying agent...${NC}"

# Load config values
source "$REPO_DIR/config/agent.env"

# Apply the base manifests
oc apply -f "$REPO_DIR/deploy/openshift.yaml" -n "$NAMESPACE" 2>/dev/null

# Set the images
oc set image deployment/adk-web \
    adk-web="$WEB_IMAGE" \
    adk-api="$AGENT_IMAGE" \
    -n "$NAMESPACE" 2>/dev/null

# Set all env vars from agent.env
oc set env deployment/adk-web -n "$NAMESPACE" -c adk-api \
    OPENAI_API_BASE="${OPENAI_API_BASE:-}" \
    OPENAI_API_KEY="${OPENAI_API_KEY:-not-needed}" \
    ADK_MODEL="${ADK_MODEL:-openai/gpt-oss-120b}" \
    AGENT_NAME="${AGENT_NAME:-migration_agent}" \
    AGENT_MODE="${AGENT_MODE:-single}" \
    ADK_TEMPERATURE="${ADK_TEMPERATURE:-0.2}" \
    MTV_API_URL="${MTV_API_URL:-}" \
    VIRT_API_URL="${VIRT_API_URL:-}" \
    MTV_INVENTORY_URL="${MTV_INVENTORY_URL:-}" \
    AAP_URL="${AAP_URL:-}" \
    DEFAULT_MTV_NAMESPACE="${DEFAULT_MTV_NAMESPACE:-mtv-user1}" \
    DEFAULT_VIRT_NAMESPACE="${DEFAULT_VIRT_NAMESPACE:-vmimported-user1}" \
    MTV_OPERATOR_NAMESPACE="${MTV_OPERATOR_NAMESPACE:-openshift-mtv}" \
    2>/dev/null

# Set route timeout
oc annotate route adk-web -n "$NAMESPACE" --overwrite \
    haproxy.router.openshift.io/timeout=600s 2>/dev/null || true

echo -e "${GREEN}  Deployment configured${NC}"
echo ""

# =============================================================================
# Wait for rollout
# =============================================================================
echo -e "${BLUE}[5/5] Waiting for pod to be ready...${NC}"

if oc rollout status deployment/adk-web -n "$NAMESPACE" --timeout=120s 2>/dev/null; then
    echo -e "${GREEN}  Pod is ready${NC}"
else
    echo -e "${YELLOW}  Rollout still in progress. Check: oc get pods -n $NAMESPACE${NC}"
fi
echo ""

# =============================================================================
# Summary
# =============================================================================
ROUTE=$(oc get route adk-web -n "$NAMESPACE" -o jsonpath='{.spec.host}' 2>/dev/null)

echo "=============================================="
echo -e "  ${GREEN}Phase 0 Deployment Complete${NC}"
echo "=============================================="
echo ""
echo "  Agent UI: https://$ROUTE"
echo ""
echo "  Try: \"Check connectivity to all configured systems\""
echo ""
