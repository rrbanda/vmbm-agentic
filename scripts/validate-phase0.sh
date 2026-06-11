#!/bin/bash
# =============================================================================
# Validate Phase 0 -- Tests the deployed agent's connectivity
# =============================================================================
# Usage: ./scripts/validate-phase0.sh [namespace]
# =============================================================================

set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

NAMESPACE=${1:-adk-web}

echo ""
echo "=============================================="
echo "  Phase 0: Validation"
echo "=============================================="
echo ""

# --- Get route ---
ROUTE=$(oc get route adk-web -n "$NAMESPACE" -o jsonpath='{.spec.host}' 2>/dev/null)
if [ -z "$ROUTE" ]; then
    echo -e "${RED}ERROR: Route not found. Is the agent deployed in namespace '$NAMESPACE'?${NC}"
    exit 1
fi
BASE="https://$ROUTE/api"

echo -e "${BLUE}Agent URL: $BASE${NC}"
echo ""

# --- Check API health ---
echo "1. Checking API health..."
HEALTH=$(curl -sk --max-time 10 "$BASE/list-apps" 2>&1)
if echo "$HEALTH" | grep -q "app"; then
    echo -e "   ${GREEN}PASS${NC} ADK API server is responding"
else
    echo -e "   ${RED}FAIL${NC} ADK API not responding: $HEALTH"
    exit 1
fi

# --- Check version ---
echo "2. Checking ADK version..."
VERSION=$(curl -sk --max-time 10 "$BASE/version" 2>&1)
echo -e "   ${BLUE}INFO${NC} $VERSION"

# --- Create session and run connectivity check ---
echo "3. Running connectivity check via agent..."
echo ""

SID=$(curl -sk -X POST "$BASE/apps/app/users/validator/sessions" \
  -H "Content-Type: application/json" -d '{}' 2>/dev/null | \
  python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null)

if [ -z "$SID" ]; then
    echo -e "   ${RED}FAIL${NC} Could not create session"
    exit 1
fi

echo "   Session: $SID"
echo "   Sending: 'Check connectivity to all configured systems'"
echo ""

RESP=$(curl -sk --max-time 60 -N -X POST "$BASE/run_sse" \
  -H "Content-Type: application/json" \
  -d "{
    \"app_name\": \"app\",
    \"user_id\": \"validator\",
    \"session_id\": \"$SID\",
    \"new_message\": {
      \"role\": \"user\",
      \"parts\": [{\"text\": \"Check connectivity to all configured systems and show me the status of each integration.\"}]
    }
  }" 2>&1)

# Extract text response
TEXT=$(echo "$RESP" | grep -o '"text":"[^"]*' | tail -1 | sed 's/"text":"//')

if [ -n "$TEXT" ]; then
    echo -e "   ${GREEN}PASS${NC} Agent responded with connectivity status"
    echo ""
    echo "   -----------------------------------------------"
    echo "   Agent Response (summary):"
    echo "   $TEXT" | head -c 500
    echo ""
    echo "   -----------------------------------------------"
else
    # Check if tool was called
    if echo "$RESP" | grep -q "check_connectivity"; then
        echo -e "   ${BLUE}INFO${NC} Agent called check_connectivity tool (response may still be streaming)"
    else
        echo -e "   ${RED}FAIL${NC} No response from agent"
    fi
fi

echo ""
echo "=============================================="
echo "  Validation Complete"
echo "=============================================="
echo ""
echo "  Open the full UI at: https://$ROUTE"
echo ""
