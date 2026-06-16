"""OCP Virt / MTV read-only tools for the migration agent.

Phase 2: Live VM inventory -- read-only access to VMware inventory
via MTV Forklift and KubeVirt VMs on OCP Virt. No data is modified.

Migration execution tools (create_migration_plan, get_pod_logs) are
added in later phases.
"""

import logging
import os

try:
    import requests
    import urllib3
except ImportError:
    requests = None
    urllib3 = None

from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential, retry_if_exception_type

log = logging.getLogger(__name__)

_RETRYABLE = (requests.exceptions.ConnectionError, requests.exceptions.Timeout) if requests else ()

_ocp_ca = os.environ.get("OCP_CA_BUNDLE", "").strip()
if _ocp_ca.lower() == "true":
    _OCP_VERIFY = True
elif _ocp_ca and os.path.isfile(_ocp_ca):
    _OCP_VERIFY = _ocp_ca
else:
    _OCP_VERIFY = False
    if urllib3:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

FORKLIFT_GROUP = "forklift.konveyor.io"
FORKLIFT_VERSION = "v1beta1"
KUBEVIRT_GROUP = "kubevirt.io"
KUBEVIRT_VERSION = "v1"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=15), retry=retry_if_exception_type(_RETRYABLE), reraise=True)
def _http_get(url: str, headers: dict, timeout: int = 30) -> requests.Response:
    resp = requests.get(url, headers=headers, verify=_OCP_VERIFY, timeout=timeout)
    resp.raise_for_status()
    return resp

from .cluster_clients import (  # noqa: E402
    K8S_AVAILABLE,
    ApiException,
    DEFAULT_MTV_NAMESPACE,
    DEFAULT_VIRT_NAMESPACE,
    MTV_INVENTORY_ROUTE_NAME,
    MTV_INVENTORY_URL,
    MTV_OPERATOR_NAMESPACE,
    _get_inventory_token,
    mtv_custom_api,
    virt_custom_api,
)

_K8S_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


def _is_retryable_k8s(exc: BaseException) -> bool:
    return isinstance(exc, ApiException) and exc.status in _K8S_RETRYABLE_STATUSES


_k8s_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception(_is_retryable_k8s),
    reraise=True,
    before_sleep=lambda rs: log.warning(
        "K8s API call failed (status %s), retrying attempt %d...",
        getattr(rs.outcome.exception(), "status", "?"), rs.attempt_number,
    ),
)


@_k8s_retry
def _k8s_list(api, **kwargs):
    return api.list_namespaced_custom_object(**kwargs)


@_k8s_retry
def _k8s_get(api, **kwargs):
    return api.get_namespaced_custom_object(**kwargs)


def _resolve_inventory(mtv_api, provider_uid: str) -> tuple[str, str]:
    """Resolve the Forklift inventory base URL and auth token."""
    token = _get_inventory_token()

    if MTV_INVENTORY_URL:
        return MTV_INVENTORY_URL.rstrip("/"), token

    inv_route = _k8s_get(mtv_api,
        group="route.openshift.io", version="v1",
        namespace=MTV_OPERATOR_NAMESPACE, plural="routes",
        name=MTV_INVENTORY_ROUTE_NAME,
    )
    inv_url = f"https://{inv_route['spec']['host']}"
    return inv_url, token


def list_vmware_vms(namespace: str = "") -> dict:
    """List VMs from VMware vSphere via the MTV Forklift inventory.

    Queries the MTV inventory API to discover VMware VMs available for
    migration. Returns VM names, power state, OS, CPU, memory, and disk info.

    Args:
        namespace: MTV namespace with the VMware provider.

    Returns:
        Dictionary with 'vms' list containing VM details from VMware inventory.
    """
    namespace = namespace or DEFAULT_MTV_NAMESPACE

    if not K8S_AVAILABLE:
        return {"error": "kubernetes Python client not installed"}

    try:
        api = mtv_custom_api()
        providers = _k8s_list(api,
            group=FORKLIFT_GROUP, version=FORKLIFT_VERSION,
            namespace=namespace, plural="providers",
        )
        vmware_provider = next(
            (p for p in providers.get("items", [])
             if p.get("spec", {}).get("type") == "vsphere"), None
        )
        if not vmware_provider:
            return {"error": f"No VMware provider found in namespace {namespace}"}

        provider_uid = vmware_provider["metadata"]["uid"]
        provider_name = vmware_provider["metadata"]["name"]

        inv_url, token = _resolve_inventory(api, provider_uid)

        resp = _http_get(
            f"{inv_url}/providers/vsphere/{provider_uid}/vms",
            headers={"Authorization": f"Bearer {token}"},
        )
        vms = resp.json()

        return {
            "provider": provider_name,
            "namespace": namespace,
            "vm_count": len(vms),
            "vms": [
                {
                    "name": vm.get("name"),
                    "id": vm.get("id"),
                    "power_state": vm.get("powerState"),
                    "cpu_count": vm.get("cpuCount"),
                    "memory_mb": vm.get("memoryMB"),
                    "guest_os": vm.get("guestName", "Unknown"),
                    "firmware": vm.get("firmware", "bios"),
                    "disk_count": len(vm.get("disks", [])),
                    "total_disk_gb": round(sum(d.get("capacity", 0) for d in vm.get("disks", [])) / (1024**3), 1),
                    "networks": [n.get("id") for n in vm.get("networks", [])],
                }
                for vm in vms
            ],
        }
    except ApiException as e:
        return {"error": f"Kubernetes API error: {e.status} {e.reason}"}
    except Exception as e:
        return {"error": f"Error querying VMware inventory: {str(e)}"}


def list_migrated_vms(namespace: str = "") -> dict:
    """List VMs that have been migrated to OCP Virtualization.

    Args:
        namespace: Namespace with migrated VMs.

    Returns:
        Dictionary with 'vms' list containing migrated VM details.
    """
    namespace = namespace or DEFAULT_VIRT_NAMESPACE

    if not K8S_AVAILABLE:
        return {"error": "kubernetes Python client not installed"}

    try:
        api = virt_custom_api()
        vms = _k8s_list(api,
            group=KUBEVIRT_GROUP, version=KUBEVIRT_VERSION,
            namespace=namespace, plural="virtualmachines",
        )
        result = []
        for vm in vms.get("items", []):
            spec = vm.get("spec", {})
            domain = spec.get("template", {}).get("spec", {}).get("domain", {})
            status = vm.get("status", {})
            result.append({
                "name": vm["metadata"]["name"],
                "namespace": namespace,
                "running": spec.get("running", False),
                "status": status.get("printableStatus", "Unknown"),
                "cpu_cores": domain.get("cpu", {}).get("cores"),
                "memory": domain.get("resources", {}).get("requests", {}).get("memory"),
                "created": vm["metadata"].get("creationTimestamp"),
            })
        return {"namespace": namespace, "vm_count": len(result), "vms": result}
    except ApiException as e:
        return {"error": f"Kubernetes API error: {e.status} {e.reason}"}
    except Exception as e:
        return {"error": f"Error: {str(e)}"}


def get_vm_details(namespace: str, vm_name: str) -> dict:
    """Get detailed info about a specific VM on OCP Virtualization.

    Args:
        namespace: Namespace containing the VM.
        vm_name: Name of the VirtualMachine resource.

    Returns:
        Dictionary with full VM spec, status, disks, interfaces, conditions.
    """
    if not K8S_AVAILABLE:
        return {"error": "kubernetes Python client not installed"}

    try:
        api = virt_custom_api()
        vm = _k8s_get(api,
            group=KUBEVIRT_GROUP, version=KUBEVIRT_VERSION,
            namespace=namespace, plural="virtualmachines", name=vm_name,
        )
        spec = vm.get("spec", {})
        domain = spec.get("template", {}).get("spec", {}).get("domain", {})
        devices = domain.get("devices", {})
        status = vm.get("status", {})

        return {
            "name": vm_name, "namespace": namespace,
            "running": spec.get("running", False),
            "status": status.get("printableStatus", "Unknown"),
            "cpu_cores": domain.get("cpu", {}).get("cores"),
            "cpu_sockets": domain.get("cpu", {}).get("sockets"),
            "memory": domain.get("resources", {}).get("requests", {}).get("memory"),
            "disks": [{"name": d.get("name"), "bus": d.get("disk", {}).get("bus")} for d in devices.get("disks", [])],
            "interfaces": [{"name": i.get("name"), "model": i.get("model")} for i in devices.get("interfaces", [])],
            "volumes": [v.get("name") for v in spec.get("template", {}).get("spec", {}).get("volumes", [])],
            "conditions": [{"type": c.get("type"), "status": c.get("status")} for c in status.get("conditions", [])],
            "labels": vm["metadata"].get("labels", {}),
            "created": vm["metadata"].get("creationTimestamp"),
        }
    except ApiException as e:
        if e.status == 404:
            return {"error": f"VM '{vm_name}' not found in namespace '{namespace}'"}
        return {"error": f"Kubernetes API error: {e.status} {e.reason}"}
    except Exception as e:
        return {"error": f"Error: {str(e)}"}


def get_migration_status(namespace: str = "") -> dict:
    """Get status of MTV migrations in a namespace.

    Args:
        namespace: Namespace with MTV plans/migrations.

    Returns:
        Dictionary with 'plans' and 'migrations' lists showing status.
    """
    namespace = namespace or DEFAULT_MTV_NAMESPACE

    if not K8S_AVAILABLE:
        return {"error": "kubernetes Python client not installed"}

    try:
        api = mtv_custom_api()
        plans = _k8s_list(api,
            group=FORKLIFT_GROUP, version=FORKLIFT_VERSION,
            namespace=namespace, plural="plans",
        )
        migrations = _k8s_list(api,
            group=FORKLIFT_GROUP, version=FORKLIFT_VERSION,
            namespace=namespace, plural="migrations",
        )

        plan_list = []
        for p in plans.get("items", []):
            conditions = p.get("status", {}).get("conditions", [])
            migration_status = p.get("status", {}).get("migration", {})
            vms = migration_status.get("vms", [])
            plan_list.append({
                "name": p["metadata"]["name"],
                "vm_count": len(p.get("spec", {}).get("vms", [])),
                "phase": next((c["type"] for c in conditions if c.get("status") == "True"), "Unknown"),
                "vms_completed": sum(1 for v in vms if v.get("phase") == "Completed"),
                "vms_running": sum(1 for v in vms if v.get("phase") == "Running"),
                "vms_failed": sum(1 for v in vms if v.get("phase") == "Failed"),
            })

        migration_list = []
        for m in migrations.get("items", []):
            conditions = m.get("status", {}).get("conditions", [])
            migration_list.append({
                "name": m["metadata"]["name"],
                "plan": m.get("spec", {}).get("plan", {}).get("name"),
                "phase": next((c["type"] for c in conditions if c.get("status") == "True"), "Unknown"),
                "started": m["metadata"].get("creationTimestamp"),
            })

        return {
            "namespace": namespace,
            "plans": plan_list, "plan_count": len(plan_list),
            "migrations": migration_list, "migration_count": len(migration_list),
        }
    except ApiException as e:
        return {"error": f"Kubernetes API error: {e.status} {e.reason}"}
    except Exception as e:
        return {"error": f"Error: {str(e)}"}
