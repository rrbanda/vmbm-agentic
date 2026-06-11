#!/bin/bash
# =============================================================================
# Deploy Phase 0 -- Deploys the migration agent for connectivity verification
# =============================================================================
# Usage: ./scripts/deploy-phase0.sh [namespace]
# =============================================================================

set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

NAMESPACE=${1:-adk-web}

echo ""
echo "=============================================="
echo "  Phase 0: Deploying Migration Agent"
echo "  Namespace: $NAMESPACE"
echo "=============================================="
echo ""

# --- Pre-flight checks ---
echo -e "${BLUE}Pre-flight checks...${NC}"

if ! oc whoami &>/dev/null 2>&1; then
    echo -e "${RED}ERROR: Not logged into OpenShift. Run 'oc login' first.${NC}"
    exit 1
fi

if [ ! -f config/agent.env ]; then
    echo -e "${RED}ERROR: config/agent.env not found. Run ./scripts/gather-config.sh first.${NC}"
    exit 1
fi

echo -e "${GREEN}Pre-flight OK${NC}"
echo ""

# --- Create namespace ---
echo -e "${BLUE}Creating namespace '$NAMESPACE'...${NC}"
oc create namespace "$NAMESPACE" --dry-run=client -o yaml | oc apply -f - 2>/dev/null
echo ""

# --- Apply secrets ---
if [ -f config/secrets.sh ]; then
    echo -e "${BLUE}Creating secrets...${NC}"
    bash config/secrets.sh "$NAMESPACE"
    echo ""
fi

# --- Update deployment YAML with values from config ---
echo -e "${BLUE}Preparing deployment manifest...${NC}"

# Read values from agent.env
source config/agent.env

# Create a working copy of the YAML
cp deploy/openshift.yaml /tmp/phase0-deploy.yaml

# Replace placeholders
sed -i.bak "s|REPLACE_LLM_API_BASE|${OPENAI_API_BASE}|g" /tmp/phase0-deploy.yaml
sed -i.bak "s|REPLACE_ADK_MODEL|${ADK_MODEL}|g" /tmp/phase0-deploy.yaml

# Set MTV/Virt/AAP URLs if configured
if [ -n "${MTV_API_URL:-}" ]; then
    sed -i.bak "s|value: \"\"  # MTV_API_URL|value: \"${MTV_API_URL}\"|g" /tmp/phase0-deploy.yaml
fi
if [ -n "${VIRT_API_URL:-}" ]; then
    sed -i.bak "s|value: \"\"  # VIRT_API_URL|value: \"${VIRT_API_URL}\"|g" /tmp/phase0-deploy.yaml
fi
if [ -n "${AAP_URL:-}" ]; then
    sed -i.bak "s|value: \"\"  # AAP_URL|value: \"${AAP_URL}\"|g" /tmp/phase0-deploy.yaml
fi

rm -f /tmp/phase0-deploy.yaml.bak

# --- Apply ---
echo -e "${BLUE}Deploying to OpenShift...${NC}"
oc apply -f /tmp/phase0-deploy.yaml -n "$NAMESPACE"
echo ""

# --- Wait for rollout ---
echo -e "${BLUE}Waiting for pod to be ready...${NC}"
oc rollout status deployment/adk-web -n "$NAMESPACE" --timeout=120s

# --- Set route timeout ---
oc annotate route adk-web -n "$NAMESPACE" --overwrite haproxy.router.openshift.io/timeout=600s 2>/dev/null || true

# --- Get route ---
ROUTE=$(oc get route adk-web -n "$NAMESPACE" -o jsonpath='{.spec.host}' 2>/dev/null)

echo ""
echo "=============================================="
echo -e "  ${GREEN}Phase 0 Deployment Complete${NC}"
echo "=============================================="
echo ""
echo "  Agent UI:  https://$ROUTE"
echo "  Agent API: https://$ROUTE/api/list-apps"
echo ""
echo "  Next step: Open the UI and try this prompt:"
echo ""
echo "    \"Check connectivity to all configured systems"
echo "     and show me the status of each integration.\""
echo ""
echo "  Or run: ./scripts/validate-phase0.sh"
echo ""
