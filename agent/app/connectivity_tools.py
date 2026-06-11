"""Connectivity verification tools for the migration agent.

Provides a FunctionTool that probes each configured external system
and returns a structured status table. All probes are lightweight
and read-only -- no data is modified.

This is the only tool available in Phase 0, used to build trust by
showing the customer their infrastructure reflected in the agent's
connectivity status.

Probed systems:
  - ADK Server (self-check)
  - LLM Endpoint (model list or minimal completion)
  - MTV Kubernetes API (namespace list)
  - MTV Forklift Inventory Route (HTTP GET)
  - OCP Virt Kubernetes API (namespace list)
  - AAP Controller (auth-only /me endpoint)
"""

import logging
import os
from datetime import datetime, timezone

log = logging.getLogger(__name__)

try:
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    requests = None

try:
    from kubernetes import client, config
    K8S_AVAILABLE = True
except ImportError:
    K8S_AVAILABLE = False


def _probe_http(url: str, headers: dict | None = None, timeout: int = 10) -> tuple[bool, str]:
    """Probe an HTTP endpoint. Returns (success, detail)."""
    if not requests:
        return False, "requests library not installed"
    try:
        resp = requests.get(url, headers=headers or {}, verify=False, timeout=timeout)
        if resp.status_code < 400:
            return True, f"HTTP {resp.status_code}"
        return False, f"HTTP {resp.status_code}: {resp.text[:100]}"
    except requests.exceptions.ConnectionError:
        return False, "Connection refused or unreachable"
    except requests.exceptions.Timeout:
        return False, f"Timeout after {timeout}s"
    except Exception as e:
        return False, str(e)[:100]


def _probe_k8s(api_url: str, token: str, ca_path: str = "") -> tuple[bool, str]:
    """Probe a Kubernetes API server. Returns (success, detail)."""
    if not K8S_AVAILABLE:
        return False, "kubernetes library not installed"
    try:
        conf = client.Configuration()
        conf.host = api_url.rstrip("/")
        conf.api_key = {"authorization": f"Bearer {token}"}
        conf.verify_ssl = bool(ca_path)
        if ca_path and os.path.isfile(ca_path):
            conf.ssl_ca_cert = ca_path

        api_client = client.ApiClient(configuration=conf)
        v1 = client.CoreV1Api(api_client=api_client)
        ns_list = v1.list_namespace(limit=1, _request_timeout=10)
        count = len(ns_list.items)
        api_client.close()
        return True, f"Connected ({count}+ namespaces)"
    except Exception as e:
        detail = str(e)
        if "401" in detail or "Unauthorized" in detail:
            return False, "Authentication failed (invalid token)"
        if "403" in detail or "Forbidden" in detail:
            return False, "Token valid but insufficient permissions"
        return False, detail[:100]


def _read_token(env_var: str) -> str:
    """Read a token from env var, supporting file-path indirection."""
    val = os.environ.get(env_var, "")
    if val and os.path.isfile(val):
        try:
            with open(val) as f:
                return f.read().strip()
        except OSError:
            return ""
    return val


def check_connectivity() -> dict:
    """Check connectivity to all configured external systems.

    Probes each system the migration agent needs to communicate with
    and returns a structured status table. All probes are read-only
    and lightweight -- no data is modified.

    Returns:
        Dictionary with 'systems' list (each with name, url, token_present,
        status, detail) and a 'summary' string.
    """
    systems = []
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # 1. ADK Server (self-check)
    adk_ok, adk_detail = _probe_http("http://localhost:8000/list-apps")
    systems.append({
        "name": "ADK Server",
        "url": "http://localhost:8000",
        "token_present": "n/a",
        "status": "Connected" if adk_ok else "Failed",
        "detail": adk_detail,
    })

    # 2. LLM Endpoint
    llm_base = os.environ.get("OPENAI_API_BASE", "")
    llm_key = os.environ.get("OPENAI_API_KEY", "")
    if llm_base:
        headers = {}
        if llm_key and llm_key != "not-needed":
            headers["Authorization"] = f"Bearer {llm_key}"
        models_url = f"{llm_base.rstrip('/')}/models"
        llm_ok, llm_detail = _probe_http(models_url, headers=headers)
        systems.append({
            "name": "LLM Endpoint",
            "url": llm_base,
            "token_present": "Yes" if llm_key else "No",
            "status": "Connected" if llm_ok else "Failed",
            "detail": llm_detail,
        })
    else:
        systems.append({
            "name": "LLM Endpoint",
            "url": "(not configured)",
            "token_present": "No",
            "status": "Not Configured",
            "detail": "Set OPENAI_API_BASE to enable",
        })

    # 3. MTV Kubernetes API
    mtv_url = os.environ.get("MTV_API_URL", "")
    mtv_token = _read_token("MTV_API_TOKEN")
    mtv_ca = os.environ.get("MTV_API_CA", "")
    if mtv_url:
        mtv_ok, mtv_detail = _probe_k8s(mtv_url, mtv_token, mtv_ca)
        systems.append({
            "name": "MTV Kubernetes API",
            "url": mtv_url,
            "token_present": "Yes" if mtv_token else "No",
            "status": "Connected" if mtv_ok else "Failed",
            "detail": mtv_detail,
        })
    else:
        systems.append({
            "name": "MTV Kubernetes API",
            "url": "(not configured)",
            "token_present": "No",
            "status": "Not Configured",
            "detail": "Set MTV_API_URL and MTV_API_TOKEN to enable",
        })

    # 4. MTV Forklift Inventory Route
    inv_url = os.environ.get("MTV_INVENTORY_URL", "")
    inv_token = _read_token("MTV_INVENTORY_TOKEN") or mtv_token
    if inv_url:
        headers = {"Authorization": f"Bearer {inv_token}"} if inv_token else {}
        inv_ok, inv_detail = _probe_http(inv_url, headers=headers)
        systems.append({
            "name": "MTV Inventory Route",
            "url": inv_url,
            "token_present": "Yes" if inv_token else "No",
            "status": "Connected" if inv_ok else "Failed",
            "detail": inv_detail,
        })
    elif mtv_url:
        systems.append({
            "name": "MTV Inventory Route",
            "url": "(auto-discover from Route CR)",
            "token_present": "Yes" if mtv_token else "No",
            "status": "Will auto-discover",
            "detail": "Route will be resolved at runtime from openshift-mtv namespace",
        })
    else:
        systems.append({
            "name": "MTV Inventory Route",
            "url": "(not configured)",
            "token_present": "No",
            "status": "Not Configured",
            "detail": "Requires MTV_API_URL or MTV_INVENTORY_URL",
        })

    # 5. OCP Virt Kubernetes API
    virt_url = os.environ.get("VIRT_API_URL", "") or mtv_url
    virt_token = _read_token("VIRT_API_TOKEN") or mtv_token
    virt_ca = os.environ.get("VIRT_API_CA", "") or mtv_ca
    if virt_url:
        virt_ok, virt_detail = _probe_k8s(virt_url, virt_token, virt_ca)
        label = "OCP Virt Kubernetes API"
        if virt_url == mtv_url:
            label += " (same as MTV)"
        systems.append({
            "name": label,
            "url": virt_url,
            "token_present": "Yes" if virt_token else "No",
            "status": "Connected" if virt_ok else "Failed",
            "detail": virt_detail,
        })
    else:
        systems.append({
            "name": "OCP Virt Kubernetes API",
            "url": "(not configured)",
            "token_present": "No",
            "status": "Not Configured",
            "detail": "Set VIRT_API_URL or MTV_API_URL to enable",
        })

    # 6. AAP Controller
    aap_url = os.environ.get("AAP_URL", "")
    aap_token = _read_token("AAP_TOKEN")
    aap_prefix = os.environ.get("AAP_API_PREFIX", "/api/controller/v2")
    if aap_url:
        me_url = f"{aap_url.rstrip('/')}{aap_prefix.rstrip('/')}/me/"
        headers = {"Authorization": f"Bearer {aap_token}"} if aap_token else {}
        aap_ok, aap_detail = _probe_http(me_url, headers=headers)
        systems.append({
            "name": "AAP Controller",
            "url": aap_url,
            "token_present": "Yes" if aap_token else "No",
            "status": "Connected" if aap_ok else "Failed",
            "detail": aap_detail,
        })
    else:
        systems.append({
            "name": "AAP Controller",
            "url": "(not configured)",
            "token_present": "No",
            "status": "Not Configured",
            "detail": "Set AAP_URL and AAP_TOKEN to enable",
        })

    # Summary
    connected = sum(1 for s in systems if s["status"] == "Connected")
    configured = sum(1 for s in systems if s["status"] != "Not Configured")
    total = len(systems)

    if connected == total:
        summary = f"All {total} systems are reachable. The agent is fully connected and ready for Phase 1."
    elif connected == configured:
        not_configured = total - configured
        summary = (
            f"{connected} of {total} systems are connected. "
            f"{not_configured} system(s) are not yet configured -- "
            "this is expected if those integrations are planned for later phases."
        )
    else:
        failed = configured - connected
        summary = (
            f"{connected} of {configured} configured systems are reachable. "
            f"{failed} system(s) failed connectivity checks -- "
            "review the details above for each failed system."
        )

    return {
        "timestamp": timestamp,
        "systems": systems,
        "connected": connected,
        "configured": configured,
        "total": total,
        "summary": summary,
    }
