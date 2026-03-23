"""Deployments view for k8s-tui."""

from datetime import datetime, timezone

from textual.widgets import DataTable, Static
from textual.containers import Vertical


class DeploymentsView(Vertical):
    """View for listing and managing Kubernetes deployments."""

    DEFAULT_CSS = """
    DeploymentsView {
        height: 100%;
    }
    DeploymentsView DataTable {
        height: 1fr;
    }
    DeploymentsView .dep-status {
        height: 1;
        padding: 0 1;
        background: $boost;
    }
    """

    def __init__(self, kube_client, **kwargs):
        super().__init__(**kwargs)
        self.kube = kube_client

    def compose(self):
        yield Static("Loading deployments...", classes="dep-status", id="dep-status")
        table = DataTable(id="dep-table")
        table.cursor_type = "row"
        table.zebra_stripes = True
        yield table

    def on_mount(self) -> None:
        """Set up the table columns."""
        table = self.query_one("#dep-table", DataTable)
        table.add_columns(
            "Name", "Ready", "Up-to-Date", "Available", "Strategy", "Age"
        )

    def refresh_data(self) -> None:
        """Fetch and display deployments."""
        try:
            deployments = self.kube.list_deployments()
        except Exception as e:
            self._update_status(f"Error: {e}")
            return

        table = self.query_one("#dep-table", DataTable)
        table.clear()

        for dep in deployments:
            name = dep["name"]
            ready = f"{dep['ready']}/{dep['replicas']}"
            age = self._format_age(dep["age"])

            table.add_row(
                name,
                ready,
                str(dep.get("updated", 0)),
                str(dep.get("available", 0)),
                dep.get("strategy", "RollingUpdate"),
                age,
                key=name,
            )

        self._update_status(f"{len(deployments)} deployments in {self.kube.namespace}")

    def _format_age(self, timestamp: str) -> str:
        """Format timestamp to human-readable age."""
        if not timestamp:
            return "N/A"
        try:
            created = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            delta = now - created
            seconds = int(delta.total_seconds())
            if seconds < 60:
                return f"{seconds}s"
            elif seconds < 3600:
                return f"{seconds // 60}m"
            elif seconds < 86400:
                return f"{seconds // 3600}h"
            else:
                return f"{seconds // 86400}d"
        except (ValueError, TypeError):
            return str(timestamp)[:19]

    def _update_status(self, text: str):
        try:
            status = self.query_one("#dep-status", Static)
            status.update(text)
        except Exception:
            pass
