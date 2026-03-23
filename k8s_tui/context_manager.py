"""Manage kubectl contexts and namespaces."""

from typing import Any


class ContextManager:
    """Manage switching between kubectl contexts and namespaces."""

    def __init__(self, kube_client):
        self.kube = kube_client
        self._contexts_cache: list[str] | None = None
        self._namespaces_cache: list[str] | None = None

    @property
    def current_context(self) -> str:
        """Get the current kubectl context."""
        return self.kube.current_context

    @property
    def current_namespace(self) -> str:
        """Get the current namespace."""
        return self.kube.namespace

    def list_contexts(self, force_refresh: bool = False) -> list[str]:
        """List available kubectl contexts."""
        if self._contexts_cache is None or force_refresh:
            self._contexts_cache = self.kube.list_contexts()
        return self._contexts_cache

    def list_namespaces(self, force_refresh: bool = False) -> list[str]:
        """List available namespaces."""
        if self._namespaces_cache is None or force_refresh:
            self._namespaces_cache = self.kube.list_namespaces()
        return self._namespaces_cache

    def switch_context(self, context: str) -> bool:
        """Switch to a different kubectl context."""
        self.kube.set_context(context)
        # Reset namespace cache since namespaces differ per cluster
        self._namespaces_cache = None
        self.kube.namespace = "default"
        return True

    def switch_namespace(self, namespace: str) -> bool:
        """Switch to a different namespace."""
        self.kube.namespace = namespace
        return True

    def next_context(self) -> str:
        """Switch to the next context in the list."""
        contexts = self.list_contexts()
        if not contexts:
            return self.current_context

        try:
            idx = contexts.index(self.current_context)
            next_idx = (idx + 1) % len(contexts)
        except ValueError:
            next_idx = 0

        target = contexts[next_idx]
        self.switch_context(target)
        return target

    def next_namespace(self) -> str:
        """Switch to the next namespace in the list."""
        namespaces = self.list_namespaces()
        if not namespaces:
            return self.current_namespace

        try:
            idx = namespaces.index(self.current_namespace)
            next_idx = (idx + 1) % len(namespaces)
        except ValueError:
            next_idx = 0

        target = namespaces[next_idx]
        self.switch_namespace(target)
        return target

    def get_context_info(self) -> dict[str, Any]:
        """Get comprehensive context information."""
        return {
            "context": self.current_context,
            "namespace": self.current_namespace,
            "available_contexts": len(self.list_contexts()),
            "available_namespaces": len(self.list_namespaces()),
        }
