"""Pod log viewer for k8s-tui."""

from textual.widgets import Static, Input, RichLog
from textual.containers import Vertical, Horizontal


class LogsView(Vertical):
    """View for streaming and searching pod logs."""

    DEFAULT_CSS = """
    LogsView {
        height: 100%;
    }
    LogsView .log-toolbar {
        height: 3;
        padding: 0 1;
        background: $boost;
    }
    LogsView Input {
        width: 1fr;
    }
    LogsView .log-info {
        height: 1;
        padding: 0 1;
        color: $text-muted;
    }
    LogsView RichLog {
        height: 1fr;
        background: $surface;
        border: solid $primary-background;
    }
    """

    def __init__(self, kube_client, **kwargs):
        super().__init__(**kwargs)
        self.kube = kube_client
        self._current_pod = None
        self._all_lines: list[str] = []

    def compose(self):
        with Horizontal(classes="log-toolbar"):
            yield Input(placeholder="Pod name (type and press Enter)", id="pod-input")
            yield Input(placeholder="Filter text...", id="log-filter")
        yield Static("No pod selected. Type a pod name above.", classes="log-info", id="log-info")
        yield RichLog(highlight=True, markup=True, wrap=True, id="log-output")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        if event.input.id == "pod-input":
            pod_name = event.value.strip()
            if pod_name:
                self._fetch_logs(pod_name)
        elif event.input.id == "log-filter":
            self._apply_filter(event.value.strip())

    def _fetch_logs(self, pod_name: str, tail: int = 200) -> None:
        """Fetch logs for a specific pod."""
        self._current_pod = pod_name
        info = self.query_one("#log-info", Static)
        info.update(f"Fetching logs for {pod_name}...")

        try:
            logs = self.kube.get_pod_logs(pod_name, tail=tail)
        except Exception as e:
            info.update(f"Error: {e}")
            return

        self._all_lines = logs.split("\n")

        log_output = self.query_one("#log-output", RichLog)
        log_output.clear()

        line_count = 0
        for line in self._all_lines:
            if line.strip():
                styled = self._style_log_line(line)
                log_output.write(styled)
                line_count += 1

        info.update(f"Pod: {pod_name} | {line_count} lines | tail={tail}")

    def _apply_filter(self, filter_text: str) -> None:
        """Filter displayed log lines."""
        if not self._all_lines:
            return

        log_output = self.query_one("#log-output", RichLog)
        log_output.clear()

        count = 0
        for line in self._all_lines:
            if not line.strip():
                continue
            if filter_text and filter_text.lower() not in line.lower():
                continue
            styled = self._style_log_line(line)
            log_output.write(styled)
            count += 1

        info = self.query_one("#log-info", Static)
        if filter_text:
            info.update(f"Pod: {self._current_pod} | {count} lines matching '{filter_text}'")
        else:
            info.update(f"Pod: {self._current_pod} | {count} lines")

    def _style_log_line(self, line: str) -> str:
        """Apply basic styling to log lines using Rich markup."""
        lower = line.lower()

        # Highlight error lines
        if any(kw in lower for kw in ["error", "err ", "fatal", "panic", "exception"]):
            return f"[bold red]{self._escape(line)}[/]"

        # Highlight warning lines
        if any(kw in lower for kw in ["warn", "warning"]):
            return f"[yellow]{self._escape(line)}[/]"

        # Highlight info lines
        if any(kw in lower for kw in ["info", "inf "]):
            return f"[cyan]{self._escape(line)}[/]"

        # Highlight debug lines
        if any(kw in lower for kw in ["debug", "dbg "]):
            return f"[dim]{self._escape(line)}[/]"

        return self._escape(line)

    def _escape(self, text: str) -> str:
        """Escape Rich markup characters."""
        return text.replace("[", "\\[").replace("]", "\\]")

    def refresh_data(self) -> None:
        """Refresh logs if a pod is selected."""
        if self._current_pod:
            self._fetch_logs(self._current_pod)
