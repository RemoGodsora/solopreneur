import sys
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from core.validator import ContractValidator
from core.models import ViolationType
from core.healer import SelfHealingEngine

app = typer.Typer(
    help="SchemaSentinel: Autonomous Data Contract Enforcement",
    no_args_is_help=True
)
console = Console()

@app.command("test")
def test_dataset(
    contract: str = typer.Option(..., "--contract", "-c", help="Path to contract YAML file"),
    data: str = typer.Option(..., "--data", "-d", help="Path to data file (CSV, Parquet, JSON)"),
    strict: bool = typer.Option(True, "--strict/--no-strict", help="Exit with code 1 on violations")
):
    """Validate a dataset against a declarative data contract."""
    console.print(Panel(
        f"[bold cyan]SchemaSentinel Inspector[/bold cyan]\n"
        f"Contract: [yellow]{contract}[/yellow]\n"
        f"Target:   [green]{data}[/green]",
        expand=False
    ))

    try:
        validator = ContractValidator(contract)
        result = validator.validate_file(data)
    except Exception as e:
        console.print(f"[bold red]Initialization Error:[/bold red] {e}")
        raise typer.Exit(code=2)

    if result.is_valid:
        console.print(f"\n✅ [bold green]CONTRACT PASSED[/bold green] - Inspected {result.total_rows_inspected} rows across '{result.contract_name}'. Zero violations detected.\n")
        return

    # Render Violations Table
    console.print(f"\n❌ [bold red]CONTRACT BREACH DETECTED[/bold red] - Inspected {result.total_rows_inspected} rows across '{result.contract_name}'.")
    
    table = Table(title="Detected Schema & Data Violations", show_header=True, header_style="bold magenta")
    table.add_column("Type", style="bold red", width=22)
    table.add_column("Column", style="cyan", width=16)
    table.add_column("Breached Rows", justify="right", style="yellow", width=14)
    table.add_column("Details", style="white")

    for v in result.violations:
        col_display = v.column if v.column else "-"
        table.add_row(
            v.violation_type.value,
            col_display,
            str(v.failed_rows_count),
            v.details
        )

    console.print(table)
    console.print(f"\n[bold yellow]Total Issues:[/bold yellow] {len(result.violations)} violations found.\n")

    if strict:
        raise typer.Exit(code=1)

@app.command("heal")
def heal_dataset(
    contract: str = typer.Option(..., "--contract", "-c", help="Path to contract YAML file"),
    data: str = typer.Option(..., "--data", "-d", help="Path to drifted data file"),
    output_sql: str = typer.Option("data/healed_view.sql", "--output", "-o", help="Path to save self-healing SQL view")
):
    """Analyze schema drift and synthesize a self-healing DuckDB SQL adapter."""
    console.print(Panel(
        f"[bold cyan]SchemaSentinel Healer[/bold cyan]\n"
        f"Contract: [yellow]{contract}[/yellow]\n"
        f"Drifted:  [red]{data}[/red]",
        expand=False
    ))

    try:
        validator = ContractValidator(contract)
        result = validator.validate_file(data)
    except Exception as e:
        console.print(f"[bold red]Error loading contract/data:[/bold red] {e}")
        raise typer.Exit(code=2)

    if result.is_valid:
        console.print("[bold green]Dataset already fully complies with the contract. No healing needed.[/bold green]")
        return

    console.print(f"[yellow]Detected {len(result.violations)} violations. Synthesizing healing view...[/yellow]")
    
    healer = SelfHealingEngine(validator.contract)
    view_sql = healer.generate_healing_view(data, result)

    # Save SQL file
    out_path = Path(output_sql)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(view_sql)

    console.print(f"\n✅ [bold green]Self-Healing View Generated:[/bold green] [cyan]{output_sql}[/cyan]\n")
    console.print(Panel(view_sql, title="Synthesized DuckDB Adapter", expand=False, style="green"))

    # Test-execute the healed view directly in DuckDB
    test_conn = validator.conn
    test_conn.execute(view_sql)
    healed_rows = test_conn.execute(f"SELECT COUNT(*) FROM v_{validator.contract.dataset}_healed;").fetchone()[0]

    # Fetch rows and column headers natively without pandas/numpy
    query_result = test_conn.execute(f"SELECT * FROM v_{validator.contract.dataset}_healed LIMIT 3;")
    col_names = [desc[0] for desc in query_result.description]
    sample_rows = query_result.fetchall()

    console.print(f"✨ [bold green]Verification:[/bold green] Successfully queried {healed_rows} clean rows through adapter!\n")

    # Render verified data table
    sample_table = Table(title="Healed View Preview (DuckDB)", show_header=True, header_style="bold green")
    for col in col_names:
        sample_table.add_column(col, style="cyan")

    for row in sample_rows:
        sample_table.add_row(*[str(val) for val in row])

    console.print(sample_table)

if __name__ == "__main__":
    app()