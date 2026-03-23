"""CLI entry point for k8s-tui."""

import click


@click.command()
@click.option("-n", "--namespace", default=None, help="Initial namespace (default: current context)")
@click.option("-c", "--context", default=None, help="Kubernetes context to use")
@click.option("--kubeconfig", default=None, help="Path to kubeconfig file")
@click.version_option(package_name="k8s-tui")
def main(namespace, context, kubeconfig):
    """Launch the Kubernetes terminal UI.

    A beautiful TUI for managing Kubernetes clusters.
    Navigate pods, deployments, services, and more from your terminal.
    """
    from k8s_tui.app import K8sTuiApp

    app = K8sTuiApp(
        initial_namespace=namespace,
        initial_context=context,
        kubeconfig=kubeconfig,
    )
    app.run()


if __name__ == "__main__":
    main()
