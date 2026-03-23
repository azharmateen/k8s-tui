"""Kubernetes API client using kubectl subprocess."""

import json
import os
import subprocess
from typing import Any


class KubeClient:
    """Kubernetes client that wraps kubectl commands."""

    def __init__(self, kubeconfig: str | None = None):
        self.kubeconfig = kubeconfig or os.environ.get("KUBECONFIG", "")
        self._namespace = "default"
        self._context = self._get_current_context()

    @property
    def namespace(self) -> str:
        return self._namespace

    @namespace.setter
    def namespace(self, value: str):
        self._namespace = value

    @property
    def current_context(self) -> str:
        return self._context

    def set_context(self, context: str):
        """Switch kubectl context."""
        self._run(["kubectl", "config", "use-context", context])
        self._context = context

    def list_contexts(self) -> list[str]:
        """List all available kubectl contexts."""
        result = self._run_json(["kubectl", "config", "get-contexts", "-o", "name"])
        if isinstance(result, str):
            return [c.strip() for c in result.split("\n") if c.strip()]
        return []

    def list_namespaces(self) -> list[str]:
        """List all namespaces."""
        data = self._run_json(["kubectl", "get", "namespaces", "-o", "json"])
        if not isinstance(data, dict):
            return ["default"]
        items = data.get("items", [])
        return [item["metadata"]["name"] for item in items]

    def list_pods(self) -> list[dict[str, Any]]:
        """List pods in the current namespace."""
        data = self._get_resources("pods")
        pods = []
        for item in data.get("items", []):
            meta = item.get("metadata", {})
            status = item.get("status", {})
            spec = item.get("spec", {})

            # Calculate restarts
            container_statuses = status.get("containerStatuses", [])
            restarts = sum(cs.get("restartCount", 0) for cs in container_statuses)

            # Determine phase/status
            phase = status.get("phase", "Unknown")
            reason = status.get("reason", "")

            # Check for container-level issues
            for cs in container_statuses:
                waiting = cs.get("state", {}).get("waiting", {})
                if waiting:
                    reason = waiting.get("reason", "")
                    if reason:
                        phase = reason

            # Ready containers
            ready_count = sum(1 for cs in container_statuses if cs.get("ready", False))
            total_count = len(container_statuses) or len(spec.get("containers", []))

            pods.append({
                "name": meta.get("name", ""),
                "namespace": meta.get("namespace", ""),
                "status": reason or phase,
                "ready": f"{ready_count}/{total_count}",
                "restarts": restarts,
                "age": meta.get("creationTimestamp", ""),
                "node": spec.get("nodeName", ""),
                "ip": status.get("podIP", ""),
                "labels": meta.get("labels", {}),
            })

        return pods

    def list_deployments(self) -> list[dict[str, Any]]:
        """List deployments in the current namespace."""
        data = self._get_resources("deployments")
        deployments = []
        for item in data.get("items", []):
            meta = item.get("metadata", {})
            status = item.get("status", {})
            spec = item.get("spec", {})

            deployments.append({
                "name": meta.get("name", ""),
                "namespace": meta.get("namespace", ""),
                "replicas": spec.get("replicas", 0),
                "ready": status.get("readyReplicas", 0),
                "available": status.get("availableReplicas", 0),
                "updated": status.get("updatedReplicas", 0),
                "age": meta.get("creationTimestamp", ""),
                "strategy": spec.get("strategy", {}).get("type", ""),
                "labels": meta.get("labels", {}),
            })

        return deployments

    def list_services(self) -> list[dict[str, Any]]:
        """List services in the current namespace."""
        data = self._get_resources("services")
        services = []
        for item in data.get("items", []):
            meta = item.get("metadata", {})
            spec = item.get("spec", {})

            ports = []
            for port in spec.get("ports", []):
                port_str = f"{port.get('port', '')}"
                if port.get("targetPort"):
                    port_str += f":{port['targetPort']}"
                if port.get("nodePort"):
                    port_str += f":{port['nodePort']}"
                port_str += f"/{port.get('protocol', 'TCP')}"
                ports.append(port_str)

            services.append({
                "name": meta.get("name", ""),
                "namespace": meta.get("namespace", ""),
                "type": spec.get("type", "ClusterIP"),
                "cluster_ip": spec.get("clusterIP", ""),
                "external_ip": ", ".join(spec.get("externalIPs", [])) or self._get_lb_ip(item),
                "ports": ", ".join(ports),
                "age": meta.get("creationTimestamp", ""),
                "selector": spec.get("selector", {}),
            })

        return services

    def list_ingresses(self) -> list[dict[str, Any]]:
        """List ingresses in the current namespace."""
        data = self._get_resources("ingresses")
        ingresses = []
        for item in data.get("items", []):
            meta = item.get("metadata", {})
            spec = item.get("spec", {})
            status = item.get("status", {})

            hosts = []
            for rule in spec.get("rules", []):
                if rule.get("host"):
                    hosts.append(rule["host"])

            lb_ingress = status.get("loadBalancer", {}).get("ingress", [])
            addresses = [i.get("ip", i.get("hostname", "")) for i in lb_ingress]

            ingresses.append({
                "name": meta.get("name", ""),
                "namespace": meta.get("namespace", ""),
                "hosts": ", ".join(hosts),
                "address": ", ".join(addresses),
                "class": spec.get("ingressClassName", ""),
                "age": meta.get("creationTimestamp", ""),
            })

        return ingresses

    def list_configmaps(self) -> list[dict[str, Any]]:
        """List configmaps in the current namespace."""
        data = self._get_resources("configmaps")
        items = []
        for item in data.get("items", []):
            meta = item.get("metadata", {})
            items.append({
                "name": meta.get("name", ""),
                "namespace": meta.get("namespace", ""),
                "data_keys": len(item.get("data", {})),
                "age": meta.get("creationTimestamp", ""),
            })
        return items

    def list_nodes(self) -> list[dict[str, Any]]:
        """List cluster nodes."""
        data = self._run_json(["kubectl", "get", "nodes", "-o", "json"] + self._kubeconfig_args())
        if not isinstance(data, dict):
            return []

        nodes = []
        for item in data.get("items", []):
            meta = item.get("metadata", {})
            status = item.get("status", {})

            conditions = {c["type"]: c["status"] for c in status.get("conditions", [])}
            ready = "Ready" if conditions.get("Ready") == "True" else "NotReady"

            info = status.get("nodeInfo", {})

            nodes.append({
                "name": meta.get("name", ""),
                "status": ready,
                "roles": self._get_node_roles(meta.get("labels", {})),
                "version": info.get("kubeletVersion", ""),
                "os": info.get("osImage", ""),
                "arch": info.get("architecture", ""),
                "age": meta.get("creationTimestamp", ""),
            })

        return nodes

    def get_pod_logs(self, pod_name: str, container: str | None = None,
                     tail: int = 100, follow: bool = False) -> str:
        """Get logs for a pod."""
        cmd = ["kubectl", "logs", pod_name, "-n", self._namespace,
               f"--tail={tail}"]
        if container:
            cmd.extend(["-c", container])
        cmd.extend(self._kubeconfig_args())

        return self._run_text(cmd)

    def get_resource_yaml(self, resource_type: str, name: str) -> str:
        """Get the YAML manifest of a specific resource."""
        cmd = ["kubectl", "get", resource_type, name,
               "-n", self._namespace, "-o", "yaml"]
        cmd.extend(self._kubeconfig_args())
        return self._run_text(cmd)

    def delete_pod(self, pod_name: str) -> str:
        """Delete a pod."""
        cmd = ["kubectl", "delete", "pod", pod_name, "-n", self._namespace]
        cmd.extend(self._kubeconfig_args())
        return self._run_text(cmd)

    def scale_deployment(self, name: str, replicas: int) -> str:
        """Scale a deployment."""
        cmd = ["kubectl", "scale", "deployment", name,
               f"--replicas={replicas}", "-n", self._namespace]
        cmd.extend(self._kubeconfig_args())
        return self._run_text(cmd)

    def _get_resources(self, resource_type: str) -> dict:
        """Get resources as JSON dict."""
        cmd = ["kubectl", "get", resource_type, "-n", self._namespace, "-o", "json"]
        cmd.extend(self._kubeconfig_args())
        result = self._run_json(cmd)
        if isinstance(result, dict):
            return result
        return {"items": []}

    def _get_current_context(self) -> str:
        """Get the current kubectl context."""
        try:
            result = self._run_text(
                ["kubectl", "config", "current-context"] + self._kubeconfig_args()
            )
            return result.strip()
        except Exception:
            return "unknown"

    def _get_lb_ip(self, svc_item: dict) -> str:
        """Extract LoadBalancer external IP."""
        ingress = svc_item.get("status", {}).get("loadBalancer", {}).get("ingress", [])
        return ", ".join(i.get("ip", i.get("hostname", "")) for i in ingress) if ingress else ""

    def _get_node_roles(self, labels: dict) -> str:
        """Extract node roles from labels."""
        roles = []
        for key in labels:
            if key.startswith("node-role.kubernetes.io/"):
                role = key.split("/")[-1]
                if role:
                    roles.append(role)
        return ", ".join(roles) if roles else "worker"

    def _kubeconfig_args(self) -> list[str]:
        """Build kubeconfig arguments."""
        if self.kubeconfig:
            return ["--kubeconfig", self.kubeconfig]
        return []

    def _run_json(self, cmd: list[str]) -> dict | str:
        """Run a command and parse JSON output."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    return result.stdout
            return result.stderr or ""
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            return str(e)

    def _run_text(self, cmd: list[str]) -> str:
        """Run a command and return text output."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15,
            )
            return result.stdout if result.returncode == 0 else result.stderr
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            return str(e)

    def _run(self, cmd: list[str]) -> bool:
        """Run a command and return success status."""
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
