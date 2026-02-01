"""CLI interface for the data generator."""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.table import Table

from .config import load_config, SimulationConfig
from .validators import validate_config, ValidationError
from .simulation import Simulator
from .writers import OutputManager


console = Console()


def print_banner():
    """Print application banner."""
    banner = """
╔══════════════════════════════════════════════════════════════════╗
║           Idle Champions: Synthetic Data Generator               ║
╚══════════════════════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold blue")


def print_config_summary(config: SimulationConfig):
    """Print configuration summary."""
    table = Table(title="Simulation Parameters", show_header=False)
    table.add_column("Parameter", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Seed", str(config.seed))
    table.add_row("Start Date", config.start_date)
    table.add_row("Duration", f"{config.duration_days} days")
    table.add_row("Total Installs", f"{config.total_installs:,}")
    table.add_row("Output Format", config.output_format)

    # Bad traffic
    bad_traffic = config.bad_traffic_config
    if bad_traffic:
        table.add_row("Bad Traffic", f"Day {bad_traffic['day']}, {bad_traffic['volume']:,} installs")

    console.print(table)


def print_validation_errors(errors: list[str]):
    """Print validation errors."""
    console.print("\n[red bold]Configuration Validation Failed:[/red bold]")
    for error in errors:
        console.print(f"  [red]• {error}[/red]")


@click.command()
@click.option(
    "--config", "-c",
    type=click.Path(exists=True, path_type=Path),
    default="configs/default.yaml",
    help="Base configuration file",
)
@click.option(
    "--override", "-o",
    type=click.Path(exists=True, path_type=Path),
    multiple=True,
    help="Override configuration file(s)",
)
@click.option(
    "--output", "-O",
    type=click.Path(path_type=Path),
    default="./output",
    help="Output directory",
)
@click.option(
    "--seed", "-s",
    type=int,
    default=None,
    help="Override random seed",
)
@click.option(
    "--validate-only", "-v",
    is_flag=True,
    help="Only validate configuration, don't generate",
)
@click.option(
    "--dry-run", "-d",
    is_flag=True,
    help="Show parameters without generating",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Verbose output",
)
@click.option(
    "--format", "-f",
    type=click.Choice(["jsonl", "parquet", "both"]),
    default=None,
    help="Output format (overrides config)",
)
def main(
    config: Path,
    override: tuple[Path, ...],
    output: Path,
    seed: Optional[int],
    validate_only: bool,
    dry_run: bool,
    verbose: bool,
    format: Optional[str],
):
    """Generate synthetic game analytics data.

    Examples:

        python generate.py

        python generate.py --config configs/default.yaml

        python generate.py --override configs/overrides/bad_traffic.yaml

        python generate.py --seed 12345 --output ./my_output

        python generate.py --validate-only
    """
    print_banner()

    # Load configuration
    console.print("[CONFIG] Loading configs...", style="bold")
    try:
        config_dict = load_config(config, list(override) if override else None)
        console.print(f"  ✓ Base: {config}", style="green")
        for ov in override:
            console.print(f"  ✓ Override: {ov}", style="green")
    except Exception as e:
        console.print(f"  [red]✗ Failed to load config: {e}[/red]")
        sys.exit(1)

    # Override seed if provided
    if seed is not None:
        config_dict["simulation"]["seed"] = seed

    # Override format if provided
    if format is not None:
        config_dict["output"]["format"] = format

    # Validate
    console.print("\n[VALIDATE] Validating configuration...", style="bold")
    errors = validate_config(config_dict)

    if errors:
        print_validation_errors(errors)
        sys.exit(1)
    else:
        console.print("  ✓ Schema validation passed", style="green")
        console.print("  ✓ Share sums validated", style="green")
        console.print("  ✓ Retention order validated", style="green")
        console.print("  ✓ All validations passed", style="green bold")

    if validate_only:
        console.print("\n[green]Configuration is valid.[/green]")
        sys.exit(0)

    # Create config wrapper
    sim_config = SimulationConfig(config_dict)

    # Print summary
    console.print("\n[PARAMS] Simulation parameters:", style="bold")
    print_config_summary(sim_config)

    if dry_run:
        console.print("\n[yellow]Dry run - no data generated.[/yellow]")
        sys.exit(0)

    # Create output directory
    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = output / f"run_{run_timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"\n[GENERATE] Starting simulation...", style="bold")
    console.print(f"  Output: {run_dir}", style="dim")

    # Initialize output manager
    output_manager = OutputManager(
        output_dir=run_dir,
        output_format=sim_config.output_format,
        compression=sim_config.output_compression,
        batch_size=sim_config.output_batch_size,
        include_metadata=sim_config.include_metadata,
    )

    start_time = datetime.now()

    # Run simulation with progress
    with output_manager:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(
                "[cyan]Simulating...",
                total=sim_config.duration_days,
            )

            def progress_callback(day: int, total: int, events: int):
                progress.update(
                    task,
                    completed=day,
                    description=f"[cyan]Day {day}/{total} | {events:,} events",
                )

            simulator = Simulator(
                config=sim_config,
                output_manager=output_manager,
                progress_callback=progress_callback,
            )
            simulator.run()

        # Finalize
        end_date = (
            datetime.fromisoformat(sim_config.start_date)
            + timedelta(days=sim_config.duration_days - 1)
        ).strftime("%Y-%m-%d")

        output_manager.finalize(end_date, datetime.now())

    elapsed = datetime.now() - start_time
    total_events = output_manager.get_total_events()

    # Print summary
    console.print("\n[OUTPUT] Results:", style="bold")

    # List output files
    for file in run_dir.iterdir():
        size = file.stat().st_size
        if size > 1024 * 1024 * 1024:
            size_str = f"{size / (1024**3):.2f} GB"
        elif size > 1024 * 1024:
            size_str = f"{size / (1024**2):.2f} MB"
        elif size > 1024:
            size_str = f"{size / 1024:.2f} KB"
        else:
            size_str = f"{size} bytes"

        console.print(f"  ✓ {file.name} ({size_str})", style="green")

    console.print(f"\n[DONE] Completed in {elapsed}", style="bold green")
    console.print(f"  Total events: {total_events:,}")
    console.print(f"  Output: {run_dir}/")


if __name__ == "__main__":
    main()
