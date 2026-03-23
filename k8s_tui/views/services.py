"""Services view for k8s-tui."""

from datetime import datetime, timezone

from textual.widgets import DataTable, Static
from textual.containers import Vertical


class ServicesView(Vertical):
    """View for listing Kubernetes services."""

    DEFAULT_CSS = """
    ServicesView {
        height: 100%;
    }
    ServicesView DataTable {
        height: 1fr;
    }
    ServicesView .svc-status {
        height: 1;
        padding: 0 1;
        background: $boost;
    }
    """

    def __init__(self, kube_client, **kwargs):
        super().__init__(**kwargs)
        self.kube = kube_client

    def compose(self):
        yield Static("Loading services...", classes="svc-status", id="svc-status")
        table = DataTable(id="svc-table")
        table.cursor_type = "row"
        table.zebra_stripes = True
        yield table

    def on_mount(self) -> None:
        """Set up the table columns."""
        table = self.query_one("#svc-table", DataTable)
        table.add_columns(
            "Name", "Type", "Cluster IP", "External IP", "Ports", "Age"
        )

    def refresh_data(self) -> None:
        """Fetch and display services."""
        try:
            services = self.kube.list_services()
        except Exception as e:
            self._update_status(f"Error: {e}")
            return

        table = self.query_one("#svc-table", DataTable)
        table.clear()

        for svc in services:
            name = svc["name"]
            age = self._format_age(svc["age"])
            external = svc.get("external_ip") or "<none>"

            table.add_row(
                name,
                svc["type"],
                svc["cluster_ip"],
                external,
                svc["ports"],
                age,
                key=name,
            )

        self._update_status(f"{len(services)} services in {self.kube.namespace}")

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
            status = self.query_one("#svc-status", Static)
            status.update(text)
        except Exception:
            pass
