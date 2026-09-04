from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from halberd import __version__
from halberd.library.atomic_schema import RiskLevel

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="halberd")
def cli():
    """Halberd BAS - Open-source Breach and Attack Simulation"""
    pass


@cli.command("list")
@click.option("--type", "list_type", type=click.Choice(["all", "atomic", "chains"]), default="all")
def list_library(list_type: str):
    """List available techniques and attack chains."""
    from halberd.library.loader import load_all_atomics, load_all_chains

    if list_type in ("all", "atomic"):
        techniques = load_all_atomics()
        table = Table(title=f"Atomic Techniques ({len(techniques)})")
        table.add_column("ID", style="cyan")
        table.add_column("Name")
        table.add_column("Tactic", style="dim")
        table.add_column("Platforms")
        table.add_column("Risk")
        table.add_column("Tests", justify="right")

        risk_colors = {"safe": "green", "low": "cyan", "medium": "yellow", "high": "red"}
        for t in techniques:
            table.add_row(
                t.id,
                t.name,
                t.tactic,
                ", ".join(p.value for p in t.platforms),
                f"[{risk_colors.get(t.risk.value, 'white')}]{t.risk.value}[/]",
                str(len(t.tests)),
            )
        console.print(table)

    if list_type in ("all", "chains"):
        chains = load_all_chains()
        table = Table(title=f"Attack Chains ({len(chains)})")
        table.add_column("ID", style="cyan")
        table.add_column("Name")
        table.add_column("Tactics", style="dim")
        table.add_column("Steps", justify="right")
        table.add_column("Source", style="dim")

        for c in chains:
            table.add_row(
                c.id,
                c.name,
                ", ".join(c.mitre_tactics),
                str(len(c.steps)),
                c.import_source or "built-in",
            )
        console.print(table)


@cli.command("run")
@click.argument("target_id")
@click.option("--dry-run", is_flag=True, help="Show what would execute without running")
@click.option("--max-risk", type=click.Choice(["safe", "low", "medium", "high"]), default="medium")
@click.option("--allow-root", is_flag=True, help="Allow running as root")
@click.option("--timeout", type=int, default=60, help="Per-test timeout in seconds")
def run_test(target_id: str, dry_run: bool, max_risk: str, allow_root: bool, timeout: int):
    """Run an atomic technique or attack chain by ID."""
    from halberd.agent.runner import run_technique, run_chain
    from halberd.agent.sandbox import Sandbox
    from halberd.library.loader import load_chain

    sandbox = Sandbox(
        max_risk=RiskLevel(max_risk),
        allow_root=allow_root,
        dry_run=dry_run,
    )

    if target_id.startswith("chain-"):
        chain = load_chain(target_id)
        console.print(f"[bold]Running chain:[/] {chain.name} ({len(chain.steps)} steps)")
        results = run_chain(chain, sandbox, timeout=timeout)
    else:
        console.print(f"[bold]Running technique:[/] {target_id}")
        results = run_technique(target_id, sandbox, timeout=timeout)

    table = Table(title="Results")
    table.add_column("Technique")
    table.add_column("Test")
    table.add_column("Status")
    table.add_column("Duration")
    table.add_column("Output", max_width=60)

    status_styles = {
        "success": "green",
        "failed": "yellow",
        "error": "red",
        "skipped": "dim",
        "dry-run": "magenta",
    }

    for r in results:
        style = status_styles.get(r.status, "white")
        output = r.output.strip()[:200] if r.output else r.error.strip()[:200] if r.error else ""
        table.add_row(
            r.technique_id,
            r.test_name,
            f"[{style}]{r.status}[/]",
            f"{r.duration:.2f}s",
            output,
        )
    console.print(table)

    passed = sum(1 for r in results if r.status == "success")
    total = len(results)
    console.print(f"\n[bold]{passed}/{total}[/] tests passed")


@cli.command("import")
@click.argument("source")
@click.option("--type", "source_type", type=click.Choice(["auto", "file", "url"]), default="auto")
def import_chain(source: str, source_type: str):
    """Import an attack chain from a file or URL."""
    from halberd.library.importer import import_chain as do_import, FileImporter, URLImporter

    backend = None
    if source_type == "file":
        backend = FileImporter()
    elif source_type == "url":
        backend = URLImporter()

    try:
        chain = do_import(source, backend=backend, save=True)
        console.print(f"[green]Imported:[/] {chain.id} - {chain.name} ({len(chain.steps)} steps)")
    except NotImplementedError as e:
        console.print(f"[yellow]{e}[/]")
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")


@cli.command("server")
@click.option("--host", default="127.0.0.1", help="Bind address")
@click.option("--port", type=int, default=8000, help="Port")
@click.option("--reload", "do_reload", is_flag=True, help="Auto-reload on changes")
def start_server(host: str, port: int, do_reload: bool):
    """Start the Halberd web server and dashboard."""
    import uvicorn

    console.print(f"[bold]Starting Halberd server on {host}:{port}[/]")
    console.print(f"Dashboard: http://{host}:{port}")
    console.print(f"API docs:  http://{host}:{port}/docs")

    uvicorn.run(
        "halberd.server.app:create_app",
        factory=True,
        host=host,
        port=port,
        reload=do_reload,
    )


@cli.command("agent")
@click.option("--server-url", required=True, help="Halberd server URL")
@click.option("--api-key", required=True, help="API key for authentication")
@click.option("--max-risk", type=click.Choice(["safe", "low", "medium", "high"]), default="medium")
@click.option("--allow-root", is_flag=True)
@click.option("--poll-interval", type=int, default=30, help="Polling interval in seconds")
def start_agent(server_url: str, api_key: str, max_risk: str, allow_root: bool, poll_interval: int):
    """Start the agent in polling mode (connects to a Halberd server)."""
    from halberd.agent.client import AgentClient
    from halberd.agent.sandbox import Sandbox

    sandbox = Sandbox(max_risk=RiskLevel(max_risk), allow_root=allow_root)
    client = AgentClient(
        server_url=server_url,
        api_key=api_key,
        sandbox=sandbox,
        poll_interval=poll_interval,
    )

    console.print(f"[bold]Starting Halberd agent[/]")
    console.print(f"Server: {server_url}")
    console.print(f"Max risk: {max_risk}")
    client.run_loop()


@cli.command("coverage")
def show_coverage():
    """Show ATT&CK coverage summary from the technique library."""
    from halberd.library.loader import load_all_atomics

    techniques = load_all_atomics()

    tactics: dict[str, list] = {}
    for t in techniques:
        tactics.setdefault(t.tactic, []).append(t)

    table = Table(title="ATT&CK Coverage by Tactic")
    table.add_column("Tactic")
    table.add_column("Techniques", justify="right")
    table.add_column("IDs")

    for tactic, techs in sorted(tactics.items()):
        table.add_row(
            tactic,
            str(len(techs)),
            ", ".join(t.id for t in techs),
        )
    console.print(table)
    console.print(f"\n[bold]Total:[/] {len(techniques)} techniques across {len(tactics)} tactics")


if __name__ == "__main__":
    cli()
