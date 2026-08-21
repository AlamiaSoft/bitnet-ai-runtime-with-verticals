from __future__ import annotations
import asyncio
from pathlib import Path
import typer
import uvicorn
from rich.console import Console
from rich.table import Table
from ..config import config
from ..inference.model_manager import ModelManager
from ..memory.db import DatabaseManager
from ..memory.indexer import DocumentIndexer
from ..memory.semantic_memory import SemanticMemory
from ..agent.agent import Agent
from ..memory.episodic_memory import EpisodicMemory
from ..tools.filesystem_tool import get_filesystem_tools
from ..tools.shell_tool import RunShellTool
from ..tools.registry import ToolRegistry
from ..plugins.vertical_registry import registry

# Auto-discover installed verticals dynamically (zero compile-time coupling)
registry.auto_discover("verticals")

app = typer.Typer(help="? BitNet AI Runtime: Local 1-bit & Edge AI Platform")
vertical_app = typer.Typer(help="?? Business Vertical Applications")
app.add_typer(vertical_app, name="vertical")

console = Console()

@app.command()
def serve(
    host: str = typer.Option(config.server.host, "--host", "-h", help="Host address"),
    port: int = typer.Option(config.server.port, "--port", "-p", help="Port number"),
):
    """Start the local FastAPI runtime server."""
    console.print(f"[bold green]Starting BitNet Local AI Server on http://{host}:{port}[/bold green]")
    uvicorn.run("bitnet_runtime.server.app:create_app", host=host, port=port, factory=True, reload=False)

@app.command()
def info():
    """Display hardware and runtime engine configuration."""
    model_mgr = ModelManager(config.inference)
    hw = model_mgr.get_hardware_info()

    table = Table(title="BitNet AI Runtime Environment")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="magenta")

    table.add_row("Runtime Name", config.runtime.name)
    table.add_row("Default Provider", config.inference.default_provider)
    table.add_row("Model Name", config.inference.model_name)
    table.add_row("CPU Count", str(hw["cpu_count"]))
    table.add_row("Architecture", f"{hw['machine']} ({hw['architecture']})")
    table.add_row("Platform", hw["platform"])

    console.print(table)

@app.command()
def run(prompt: str = typer.Argument(..., help="Prompt or task for the autonomous agent")):
    """Run an autonomous ReAct agent task locally."""
    async def _run():
        db = DatabaseManager(config.memory.db_path)
        model_mgr = ModelManager(config.inference)
        inf_engine = model_mgr.get_inference_engine()
        emb_engine = model_mgr.get_embedding_engine(config.memory.vector_dim)

        episodic = EpisodicMemory(db)
        semantic = SemanticMemory(db, emb_engine)

        tool_reg = ToolRegistry()
        tool_reg.register_many(get_filesystem_tools(config.agent.working_dir))
        if config.agent.enable_shell:
            tool_reg.register(RunShellTool(config.agent.working_dir))

        agent = Agent(
            name="CLIAgent",
            inference_engine=inf_engine,
            tool_registry=tool_reg,
            episodic_memory=episodic,
            semantic_memory=semantic,
        )

        console.print(f"[bold cyan]Task:[/bold cyan] {prompt}")
        res = await agent.run(prompt)
        console.print(f"[bold green]Final Answer:[/bold green]\n{res.final_answer}")

    asyncio.run(_run())

@app.command()
def ingest(
    path: str = typer.Argument(..., help="Path to file or directory to index"),
    recursive: bool = typer.Option(True, "--recursive", "-r", help="Recursive directory scan"),
):
    """Ingest files into the local semantic memory."""
    async def _run():
        db = DatabaseManager(config.memory.db_path)
        model_mgr = ModelManager(config.inference)
        emb_engine = model_mgr.get_embedding_engine(config.memory.vector_dim)
        sem_mem = SemanticMemory(db, emb_engine)
        indexer = DocumentIndexer(sem_mem)

        p = Path(path)
        if p.is_file():
            doc_id = await indexer.index_file(p)
            console.print(f"[green]Indexed single file:[/green] {p.name} (Doc ID: {doc_id})")
        elif p.is_dir():
            doc_ids = await indexer.index_directory(p, recursive=recursive)
            console.print(f"[green]Indexed {len(doc_ids)} documents from {path}[/green]")
        else:
            console.print(f"[red]Path not found:[/red] {path}")

    asyncio.run(_run())

@app.command()
def search(
    query: str = typer.Argument(..., help="Query to search in memory"),
    top_k: int = typer.Option(3, "--top-k", "-k", help="Number of results"),
):
    """Search local semantic memory."""
    async def _run():
        db = DatabaseManager(config.memory.db_path)
        model_mgr = ModelManager(config.inference)
        emb_engine = model_mgr.get_embedding_engine(config.memory.vector_dim)
        sem_mem = SemanticMemory(db, emb_engine)

        results = await sem_mem.query(query, top_k=top_k)
        if not results:
            console.print("[yellow]No relevant memory chunks found.[/yellow]")
            return

        table = Table(title=f"Memory Search: '{query}'")
        table.add_column("Score", style="green", width=8)
        table.add_column("Source", style="cyan", width=25)
        table.add_column("Content Snippet", style="white")

        for r in results:
            src = r.metadata.get("title") or r.metadata.get("source_path", "unknown")
            table.add_row(f"{r.score:.2f}", str(src)[:24], r.text_content[:120] + "...")

        console.print(table)

    asyncio.run(_run())

# --- Dynamic Vertical Commands ---

@vertical_app.command("list-plugins")
def list_vertical_plugins():
    """List all dynamically discovered vertical plugins."""
    manifests = registry.list_manifests()
    table = Table(title="Installed Vertical Plugins")
    table.add_column("Name", style="cyan")
    table.add_column("Title", style="magenta")
    table.add_column("Version", style="yellow")
    table.add_column("Description", style="white")

    for m in manifests:
        table.add_row(m.name, m.title, m.version, m.description)
    console.print(table)

@vertical_app.command("employee")
def vertical_employee(
    action: str = typer.Argument(..., help="Action: 'triage', 'briefing', 'list'"),
    name: str = typer.Option("Customer Lead", "--name", "-n"),
    inquiry: str = typer.Option("Interested in your commercial services", "--inquiry", "-i"),
):
    """Run AI Employee in a Box tasks."""
    async def _run():
        worker = registry.get_vertical_instance("employee")
        if not worker:
            console.print("[red]Error: 'employee' vertical plugin is not installed.[/red]")
            return
        await worker.initialize()
        if action == "triage":
            res = await worker.triage_inbound_lead(name=name, inquiry_text=inquiry)
            console.print(f"[green]Lead Triaged:[/green] {res}")
        elif action == "briefing":
            briefing = await worker.generate_morning_briefing()
            console.print(f"[bold cyan]Morning Briefing:[/bold cyan]\n{briefing}")
        elif action == "list":
            leads = worker.crm.list_leads()
            table = Table(title="CRM Leads")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="magenta")
            table.add_column("Priority", style="yellow")
            table.add_column("Sentiment", style="green")
            for l in leads:
                table.add_row(l.id, l.name, l.priority, l.sentiment or "-")
            console.print(table)
    asyncio.run(_run())

@vertical_app.command("memory")
def vertical_memory(question: str = typer.Argument(..., help="Question to ask Personal Memory OS")):
    """Ask questions to Personal Memory OS."""
    async def _run():
        mem_os = registry.get_vertical_instance("memory")
        if not mem_os:
            console.print("[red]Error: 'memory' vertical plugin is not installed.[/red]")
            return
        await mem_os.initialize()
        res = await mem_os.ask(question)
        console.print(f"[bold green]Answer:[/bold green]\n{res['answer']}")
        if res.get("citations"):
            console.print(f"\n[cyan]Citations:[/cyan] {res['citations']}")
    asyncio.run(_run())

@vertical_app.command("computer")
def vertical_computer(target: str = typer.Option(".", "--target", "-t", help="Directory to inspect")):
    """Run AI Computer Operator repository audit."""
    async def _run():
        operator = registry.get_vertical_instance("computer")
        if not operator:
            console.print("[red]Error: 'computer' vertical plugin is not installed.[/red]")
            return
        await operator.initialize()
        audit = await operator.inspect_and_audit(target)
        console.print(f"[bold cyan]Project Audit:[/bold cyan]\n{audit['recommendations']}")
    asyncio.run(_run())

@vertical_app.command("whatsapp")
def vertical_whatsapp(message: str = typer.Argument(..., help="Customer incoming message")):
    """Simulate WhatsApp Employee incoming message."""
    async def _run():
        bot = registry.get_vertical_instance("whatsapp")
        if not bot:
            console.print("[red]Error: 'whatsapp' vertical plugin is not installed.[/red]")
            return
        await bot.initialize()
        res = await bot.handle_message("user_123", message)
        console.print(f"[bold green]Bot Reply:[/bold green]\n{res['reply']}")
    asyncio.run(_run())

@vertical_app.command("qa")
def vertical_qa(urls: str = typer.Option("http://127.0.0.1:8000/health", "--urls", "-u", help="Comma-separated URLs to check")):
    """Run AI QA Box endpoint checks."""
    async def _run():
        qa = registry.get_vertical_instance("qa")
        if not qa:
            console.print("[red]Error: 'qa' vertical plugin is not installed.[/red]")
            return
        await qa.initialize()
        target_list = [u.strip() for u in urls.split(",") if u.strip()]
        res = await qa.run_endpoint_checks(target_list)
        console.print(res["report_markdown"])
    asyncio.run(_run())

if __name__ == "__main__":
    app()
