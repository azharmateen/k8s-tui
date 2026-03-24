# k8s-tui

[![Built with Claude Code](https://img.shields.io/badge/Built%20with-Claude%20Code-blue?logo=anthropic&logoColor=white)](https://claude.ai/code)


Beautiful Kubernetes terminal UI. kubectl + Lens in your terminal.

```bash
pip install k8s-tui
k8s-tui
```

## Why k8s-tui?

`kubectl get pods` shows you text. Lens needs Electron and 500MB of RAM. `k8s-tui` gives you a full Kubernetes dashboard in your terminal with real-time data, keyboard navigation, and log streaming -- all in under 20MB.

## Features

- **Pods View** - Name, status, ready count, restarts, age, node, IP. Color-coded by status.
- **Deployments View** - Replicas, available, up-to-date, strategy, age.
- **Services View** - Type, cluster IP, external IP, ports, age.
- **Log Viewer** - Stream pod logs with search, filter, and syntax highlighting.
- **Context Switching** - Cycle through kubectl contexts and namespaces with hotkeys.
- **Sidebar Navigation** - Tree view for all resource types.
- **Keyboard-First** - Full keyboard navigation, no mouse required.

## Quickstart

```bash
# Install
pip install k8s-tui

# Launch (uses current kubectl context)
k8s-tui

# Launch with specific namespace
k8s-tui -n production

# Launch with specific context
k8s-tui -c my-cluster

# Use custom kubeconfig
k8s-tui --kubeconfig ~/.kube/staging-config
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `1` | Switch to Pods view |
| `2` | Switch to Deployments view |
| `3` | Switch to Services view |
| `l` | Switch to Logs view |
| `r` | Refresh all data |
| `n` | Cycle namespace |
| `c` | Cycle context |
| `/` | Search/filter |
| `q` | Quit |

## Log Viewer

Type a pod name and press Enter to stream its logs. Use the filter input to search within logs. Log lines are color-coded:

- **Red** - Errors, fatals, panics
- **Yellow** - Warnings
- **Cyan** - Info messages
- **Dim** - Debug messages

## Architecture

```
k8s-tui (Textual App)
    |
    +-- Sidebar (Tree) -- Resource type navigation
    |
    +-- TabbedContent
    |     +-- PodsView (DataTable)
    |     +-- DeploymentsView (DataTable)
    |     +-- ServicesView (DataTable)
    |     +-- LogsView (RichLog + Input)
    |
    +-- ContextManager -- Context/namespace switching
    |
    +-- KubeClient -- kubectl subprocess wrapper
```

## Requirements

- Python 3.9+
- `kubectl` installed and configured with at least one context
- Terminal that supports 256 colors (most modern terminals)

## License

MIT
