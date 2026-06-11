#!/bin/bash
# =============================================================================
# Environment Check -- Validates prerequisites for the Migration Agent
# =============================================================================
# Run this FIRST before deploying. It checks your OpenShift cluster and
# connected systems to determine what's available and what's missing.
#
# Usage: ./scripts/env-check.sh
# =============================================================================

set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

pass_count=0
fail_count=0
warn_count=0

check_pass() { echo -e "  ${GREEN}PASS${NC} $1"; pass_count=$((pass_count+1)); }
check_fail() { echo -e "  ${RED}FAIL${NC} $1"; fail_count=$((fail_count+1)); }
check_warn() { echo -e "  ${YELLOW}WARN${NC} $1"; warn_count=$((warn_count+1)); }
check_info() { echo -e "  ${BLUE}INFO${NC} $1"; }

echo ""
echo "=============================================="
echo "  Migration Agent -- Environment Check"
echo "=============================================="
echo ""

# --- 1. CLI tools ---
echo "1. Checking CLI tools..."

if command -v oc &>/dev/null; then
    OC_VERSION=$(oc version --client -o json 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['releaseClientVersion'])" 2>/dev/null || oc version --client 2>/dev/null | head -1)
    check_pass "oc CLI installed ($OC_VERSION)"
else
    check_fail "oc CLI not found -- install from https://mirror.openshift.com/pub/openshift-v4/clients/ocp/"
fi

if command -v curl &>/dev/null; then
    check_pass "curl installed"
else
    check_fail "curl not found"
fi

if command -v python3 &>/dev/null; then
    check_pass "python3 installed ($(python3 --version 2>&1))"
else
    check_warn "python3 not found (needed for some validation scripts)"
fi

echo ""

# --- 2. OpenShift cluster ---
echo "2. Checking OpenShift cluster access..."

if oc whoami &>/dev/null 2>&1; then
    CLUSTER_USER=$(oc whoami 2>/dev/null)
    CLUSTER_URL=$(oc whoami --show-server 2>/dev/null)
    check_pass "Logged into OpenShift as '$CLUSTER_USER'"
    check_info "Cluster: $CLUSTER_URL"

    # Check cluster version
    OCP_VERSION=$(oc get clusterversion version -o jsonpath='{.status.desired.version}' 2>/dev/null || echo "unknown")
    check_info "OpenShift version: $OCP_VERSION"
else
    check_fail "Not logged into OpenShift -- run 'oc login' first"
    echo ""
    echo "Cannot continue without cluster access."
    exit 1
fi

echo ""

# --- 3. Operators ---
echo "3. Checking installed operators..."

# RHOAI
if oc get csv --all-namespaces 2>/dev/null | grep -qi "rhods-operator\|openshift-ai"; then
    RHOAI_VERSION=$(oc get csv --all-namespaces 2>/dev/null | grep -i "rhods-operator" | head -1 | awk '{print $4}' || echo "installed")
    check_pass "Red Hat OpenShift AI ($RHOAI_VERSION)"
else
    check_warn "Red Hat OpenShift AI not detected (needed for model serving)"
fi

# MTV / Forklift
if oc get csv --all-namespaces 2>/dev/null | grep -qi "mtv-operator\|forklift"; then
    MTV_VERSION=$(oc get csv --all-namespaces 2>/dev/null | grep -i "mtv-operator" | head -1 | awk '{print $4}' || echo "installed")
    check_pass "Migration Toolkit for Virtualization ($MTV_VERSION)"

    # Check for VMware provider
    if oc get providers.forklift.konveyor.io --all-namespaces 2>/dev/null | grep -q vsphere; then
        MTV_NS=$(oc get providers.forklift.konveyor.io --all-namespaces 2>/dev/null | grep vsphere | head -1 | awk '{print $1}')
        check_pass "VMware (vSphere) provider found in namespace '$MTV_NS'"
    else
        check_warn "No VMware provider configured yet -- needed for Phase 2+"
    fi
else
    check_warn "MTV/Forklift not detected (needed for Phase 2+ -- VMware migration)"
fi

# OCP Virt / KubeVirt
if oc get csv --all-namespaces 2>/dev/null | grep -qi "kubevirt\|virtualization"; then
    VIRT_VERSION=$(oc get csv --all-namespaces 2>/dev/null | grep -i "kubevirt-hyperconverged" | head -1 | awk '{print $4}' || echo "installed")
    check_pass "OpenShift Virtualization ($VIRT_VERSION)"
else
    check_warn "OpenShift Virtualization not detected (needed for Phase 4+ -- migration target)"
fi

echo ""

# --- 4. Storage ---
echo "4. Checking storage..."

SC_COUNT=$(oc get sc -o name 2>/dev/null | wc -l | tr -d ' ')
if [ "$SC_COUNT" -gt 0 ]; then
    DEFAULT_SC=$(oc get sc -o jsonpath='{.items[?(@.metadata.annotations.storageclass\.kubernetes\.io/is-default-class=="true")].metadata.name}' 2>/dev/null || echo "none")
    check_pass "$SC_COUNT storage class(es) available (default: $DEFAULT_SC)"
else
    check_warn "No storage classes found"
fi

echo ""

# --- 5. Namespaces ---
echo "5. Checking relevant namespaces..."

for ns in openshift-mtv openshift-cnv redhat-ods-operator; do
    if oc get namespace "$ns" &>/dev/null 2>&1; then
        check_info "Namespace '$ns' exists"
    fi
done

echo ""

# --- 6. Network connectivity ---
echo "6. Checking external connectivity..."

read -rp "  LLM API endpoint URL (or press Enter to skip): " LLM_URL
if [ -n "$LLM_URL" ]; then
    if curl -sk --max-time 10 "${LLM_URL%/}/models" &>/dev/null; then
        check_pass "LLM endpoint reachable: $LLM_URL"
    else
        check_fail "LLM endpoint not reachable: $LLM_URL"
    fi
fi

read -rp "  AAP Controller URL (or press Enter to skip): " AAP_URL_INPUT
if [ -n "$AAP_URL_INPUT" ]; then
    if curl -sk --max-time 10 "${AAP_URL_INPUT%/}/api/controller/v2/" &>/dev/null; then
        check_pass "AAP Controller reachable: $AAP_URL_INPUT"
    else
        check_fail "AAP Controller not reachable: $AAP_URL_INPUT"
    fi
fi

echo ""

# --- Summary ---
echo "=============================================="
echo "  Summary"
echo "=============================================="
echo -e "  ${GREEN}$pass_count passed${NC}  ${RED}$fail_count failed${NC}  ${YELLOW}$warn_count warnings${NC}"
echo ""

if [ "$fail_count" -gt 0 ]; then
    echo -e "  ${RED}Fix the failures above before proceeding.${NC}"
else
    echo -e "  ${GREEN}Environment is ready for agent deployment.${NC}"
    echo "  Next step: Run ./scripts/gather-config.sh to generate your configuration."
fi
echo ""
