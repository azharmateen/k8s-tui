"""Main Textual application for k8s-tui."""

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.css.query import NoMatches
from textual.widgets import Footer, Header, Static, Tree, Label, TabbedContent, TabPane

from k8s_tui.k8s_client import KubeClient
from k8s_tui.views.pods import PodsView
from k8s_tui.views.deployments import DeploymentsView
from k8s_tui.views.services import ServicesView
from k8s_tui.views.logs import LogsView
from k8s_tui.context_manager import ContextManager


class K8sTuiApp(App):
    """Kubernetes Terminal UI Application."""

    CSS = """
    Screen {
        layout: grid;
        grid-size: 4 3;
        grid-rows: auto 1fr auto;
        grid-columns: 1fr 3fr;
    }

    Header {
        column-span: 4;
    }

    Footer {
        column-span: 4;
    }

    #sidebar {
        width: 100%;
        height: 100%;
        background: $surface;
        border-right: solid $primary-background;
        padding: 0;
    }

    #sidebar Tree {
        width: 100%;
        height: 100%;
        padding: 0 1;
    }

    #main-content {
        width: 100%;
        height: 100%;
        column-span: 3;
    }

    #status-bar {
        height: 1;
        background: $primary-background;
        color: $text;
        padding: 0 1;
        column-span: 4;
    }

    .resource-table {
        height: 100%;
        width: 100%;
    }

    TabbedContent {
        height: 100%;
    }

    TabPane {
        height: 100%;
        padding: 0;
    }

    .detail-panel {
        height: 100%;
        background: $surface;
        padding: 1;
    }

    #context-info {
        height: 1;
        background: $boost;
        padding: 0 1;
        column-span: 4;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("n", "switch_namespace", "Namespace"),
        Binding("c", "switch_context", "Context"),
        Binding("1", "show_pods", "Pods"),
        Binding("2", "show_deployments", "Deployments"),
        Binding("3", "show_services", "Services"),
        Binding("l", "show_logs", "Logs"),
        Binding("/", "search", "Search"),
    ]

    def __init__(
        self,
        initial_namespace: str | None = None,
        initial_context: str | None = None,
        kubeconfig: str | None = None,
    ):
        super().__init__()
        self.kube = KubeClient(kubeconfig=kubeconfig)
        self.ctx_manager = ContextManager(self.kube)
        self._initial_namespace = initial_namespace
        self._initial_context = initial_context

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Horizontal():
            with Vertical(id="sidebar"):
                yield self._build_sidebar_tree()

            with Vertical(id="main-content"):
                with TabbedContent(id="tabs"):
                    with TabPane("Pods", id="tab-pods"):
                        yield PodsView(self.kube, id="pods-view")
                    with TabPane("Deployments", id="tab-deployments"):
                        yield DeploymentsView(self.kube, id="deployments-view")
                    with TabPane("Services", id="tab-services"):
                        yield ServicesView(self.kube, id="services-view")
                    with TabPane("Logs", id="tab-logs"):
                        yield LogsView(self.kube, id="logs-view")

        yield Label(id="context-info")
        yield Footer()

    def _build_sidebar_tree(self) -> Tree:
        """Build the resource type navigation tree."""
        tree: Tree = Tree("Kubernetes", id="resource-tree")
        tree.root.expand()

        workloads = tree.root.add("Workloads", expand=True)
        workloads.add_leaf("Pods")
        workloads.add_leaf("Deployments")
        workloads.add_leaf("StatefulSets")
        workloads.add_leaf("DaemonSets")
        workloads.add_leaf("Jobs")
        workloads.add_leaf("CronJobs")

        network = tree.root.add("Network", expand=True)
        network.add_leaf("Services")
        network.add_leaf("Ingresses")
        network.add_leaf("Endpoints")

        config = tree.root.add("Config", expand=True)
        config.add_leaf("ConfigMaps")
        config.add_leaf("Secrets")

        storage = tree.root.add("Storage")
        storage.add_leaf("PersistentVolumeClaims")
        storage.add_leaf("PersistentVolumes")
        storage.add_leaf("StorageClasses")

        cluster = tree.root.add("Cluster")
        cluster.add_leaf("Nodes")
        cluster.add_leaf("Namespaces")
        cluster.add_leaf("Events")

        return tree

    def on_mount(self) -> None:
        """Initialize on mount."""
        self.title = "k8s-tui"
        self.sub_title = "Kubernetes Terminal UI"

        if self._initial_context:
            self.kube.set_context(self._initial_context)
        if self._initial_namespace:
            self.kube.namespace = self._initial_namespace

        self._update_context_info()
        self.refresh_all()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle sidebar tree selection."""
        label = str(event.node.label)
        tab_map = {
            "Pods": "tab-pods",
            "Deployments": "tab-deployments",
            "Services": "tab-services",
        }

        tab_id = tab_map.get(label)
        if tab_id:
            try:
                tabs = self.query_one("#tabs", TabbedContent)
                tabs.active = tab_id
            except NoMatches:
                pass

    def _update_context_info(self):
        """Update the context/namespace info bar."""
        context = self.kube.current_context
        namespace = self.kube.namespace
        try:
            info_label = self.query_one("#context-info", Label)
            info_label.update(
                f"Context: {context}  |  Namespace: {namespace}"
            )
        except NoMatches:
            pass

    @work(thread=True)
    def refresh_all(self):
        """Refresh all views."""
        try:
            pods_view = self.query_one("#pods-view", PodsView)
            pods_view.refresh_data()
        except NoMatches:
            pass

        try:
            dep_view = self.query_one("#deployments-view", DeploymentsView)
            dep_view.refresh_data()
        except NoMatches:
            pass

        try:
            svc_view = self.query_one("#services-view", ServicesView)
            svc_view.refresh_data()
        except NoMatches:
            pass

    def action_refresh(self) -> None:
        """Refresh all resource views."""
        self.refresh_all()
        self.notify("Refreshing...")

    def action_show_pods(self) -> None:
        try:
            tabs = self.query_one("#tabs", TabbedContent)
            tabs.active = "tab-pods"
        except NoMatches:
            pass

    def action_show_deployments(self) -> None:
        try:
            tabs = self.query_one("#tabs", TabbedContent)
            tabs.active = "tab-deployments"
        except NoMatches:
            pass

    def action_show_services(self) -> None:
        try:
            tabs = self.query_one("#tabs", TabbedContent)
            tabs.active = "tab-services"
        except NoMatches:
            pass

    def action_show_logs(self) -> None:
        try:
            tabs = self.query_one("#tabs", TabbedContent)
            tabs.active = "tab-logs"
        except NoMatches:
            pass

    def action_switch_namespace(self) -> None:
        """Switch namespace."""
        namespaces = self.kube.list_namespaces()
        if namespaces:
            # Cycle through namespaces
            current = self.kube.namespace
            try:
                idx = namespaces.index(current)
                next_ns = namespaces[(idx + 1) % len(namespaces)]
            except ValueError:
                next_ns = namespaces[0]
            self.kube.namespace = next_ns
            self._update_context_info()
            self.refresh_all()
            self.notify(f"Namespace: {next_ns}")

    def action_switch_context(self) -> None:
        """Switch kubectl context."""
        contexts = self.kube.list_contexts()
        if contexts:
            current = self.kube.current_context
            try:
                idx = contexts.index(current)
                next_ctx = contexts[(idx + 1) % len(contexts)]
            except ValueError:
                next_ctx = contexts[0]
            self.kube.set_context(next_ctx)
            self._update_context_info()
            self.refresh_all()
            self.notify(f"Context: {next_ctx}")

    def action_search(self) -> None:
        """Open search (placeholder)."""
        self.notify("Search: press / and type to filter")
