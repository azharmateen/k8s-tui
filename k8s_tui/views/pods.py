"""Pods view for k8s-tui."""

from datetime import datetime, timezone

from textual.widgets import DataTable, Static
from textual.containers import Vertical


class PodsView(Vertical):
    """View for listing and managing Kubernetes pods."""

    DEFAULT_CSS = """
    PodsView {
        height: 100%;
    }
    PodsView DataTable {
        height: 1fr;
    }
    PodsView .pod-status {
        height: 1;
        padding: 0 1;
        background: $boost;
    }
    """

    def __init__(self, kube_client, **kwargs):
        super().__init__(**kwargs)
        self.kube = kube_client

    def compose(self):
        yield Static("Loading pods...", classes="pod-status", id="pod-status")
        table = DataTable(id="pods-table")
        table.cursor_type = "row"
        table.zebra_stripes = True
        yield table

    def on_mount(self) -> None:
        """Set up the table columns."""
        table = self.query_one("#pods-table", DataTable)
        table.add_columns(
            "Name", "Status", "Ready", "Restarts", "Age", "Node", "IP"
        )

    def refresh_data(self) -> None:
        """Fetch and display pods."""
        try:
            pods = self.kube.list_pods()
        except Exception as e:
            self._update_status(f"Error: {e}")
            return

        table = self.query_one("#pods-table", DataTable)
        table.clear()

        for pod in pods:
            status = pod["status"]
            name = pod["name"]
            age = self._format_age(pod["age"])

            # Color the status
            styled_status = self._style_status(status)

            table.add_row(
                name,
                styled_status,
                pod["ready"],
                str(pod["restarts"]),
                age,
                pod["node"],
                pod["ip"],
                key=name,
            )

        self._update_status(f"{len(pods)} pods in {self.kube.namespace}")

    def _style_status(self, status: str) -> str:
        """Return styled status string."""
        # Textual DataTable doesn't support Rich markup directly,
        # but we can use the status text as-is.
        # In a full implementation, we'd use custom renderable or markup.
        status_icons = {
            "Running": "Running",
            "Pending": "Pending",
            "Succeeded": "Completed",
            "Failed": "FAILED",
            "CrashLoopBackOff": "CrashLoop",
            "ImagePullBackOff": "ImgPullErr",
            "ErrImagePull": "ImgPullErr",
            "Terminating": "Terminating",
            "ContainerCreating": "Creating",
            "Init": "Initializing",
        }
        return status_icons.get(status, status)

    def _format_age(self, timestamp: str) -> str:
        """Format a Kubernetes timestamp to a human-readable age."""
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
            return timestamp[:19] if len(timestamp) > 19 else timestamp

    def _update_status(self, text: str):
        """Update the status bar."""
        try:
            status = self.query_one("#pod-status", Static)
            status.update(text)
        except Exception:
            pass
