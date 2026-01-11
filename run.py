#!/usr/bin/env python3
"""
Agentic AI Network Optimizer - Main Entry Point

Usage:
    python run.py demo         # Run a single optimization cycle demo
    python run.py monitor      # Run continuous monitoring
    python run.py api          # Start the REST API server
    python run.py --help       # Show help
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def print_banner():
    """Print the application banner."""
    banner = """
╔═══════════════════════════════════════════════════════════════╗
║       🤖 AGENTIC AI NETWORK OPTIMIZER 🌐                      ║
║                                                               ║
║   Multi-Agent System for Autonomous Network Optimization      ║
║                                                               ║
║   Agents: Monitor | Decision (LLM) | Action | Coordinator     ║
╚═══════════════════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold cyan")


async def run_demo():
    """Run a single optimization cycle for demonstration."""
    from src.agents.coordinator import Coordinator
    from src.utils.logging import setup_logging
    
    setup_logging()
    console.print("\n[bold green]Running Demo Mode - Single Optimization Cycle[/]\n")
    
    coordinator = Coordinator()
    
    try:
        # Run a single cycle
        result = await coordinator.run_cycle()
        
        # Print summary
        console.print("\n")
        console.rule("[bold cyan]Demo Complete[/]")
        
        # Create summary table
        table = Table(title="Cycle Summary", show_header=True, header_style="bold magenta")
        table.add_column("Phase", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details")
        
        phases = result.get("phases", {})
        
        # Monitor phase
        monitor = phases.get("monitor", {})
        table.add_row(
            "Monitor",
            monitor.get("status", "unknown"),
            f"Health: {monitor.get('health_score', 0):.1f}, Anomalies: {monitor.get('anomaly_count', 0)}"
        )
        
        # Decision phase
        decision = phases.get("decision", {})
        table.add_row(
            "Decision",
            decision.get("status", "unknown"),
            f"Actions: {decision.get('actions_recommended', 0)}, Confidence: {decision.get('confidence', 0):.2f}"
        )
        
        # Action phase
        action = phases.get("action", {})
        if action.get("status") == "skipped":
            table.add_row("Action", "skipped", "No action required")
        else:
            summary = action.get("summary", {})
            table.add_row(
                "Action",
                action.get("status", "unknown"),
                f"Executed: {summary.get('successful', 0)}/{summary.get('total', 0)}"
            )
        
        # Feedback phase
        feedback = phases.get("feedback", {})
        if feedback.get("status") == "skipped":
            table.add_row("Feedback", "skipped", "No actions to evaluate")
        else:
            table.add_row(
                "Feedback",
                feedback.get("status", "unknown"),
                f"Improvement: {feedback.get('improvement_score', 0):.1f}"
            )
        
        console.print(table)
        
        console.print(f"\n[bold]Duration:[/] {result.get('duration_seconds', 0):.2f} seconds")
        console.print(f"[bold]Status:[/] {result.get('status', 'unknown')}")
        
    finally:
        await coordinator.stop()


async def run_monitor(interval: int = 10, cycles: int = 0):
    """Run continuous monitoring."""
    from src.agents.coordinator import Coordinator
    from src.utils.logging import setup_logging
    
    setup_logging()
    console.print(f"\n[bold green]Starting Continuous Monitoring[/]")
    console.print(f"Interval: {interval}s | Cycles: {'unlimited' if cycles == 0 else cycles}")
    console.print("[dim]Press Ctrl+C to stop[/]\n")
    
    coordinator = Coordinator()
    
    try:
        if cycles == 0:
            # Unlimited cycles
            await coordinator.run_continuous(interval)
        else:
            # Limited cycles
            for i in range(cycles):
                await coordinator.run_cycle()
                if i < cycles - 1:
                    await asyncio.sleep(interval)
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping monitoring...[/]")
    finally:
        await coordinator.stop()
        
        # Print final summary
        summary = coordinator.get_performance_summary()
        console.print("\n")
        console.rule("[bold cyan]Monitoring Session Summary[/]")
        console.print(f"[bold]Total Cycles:[/] {summary.get('total_cycles', 0)}")
        console.print(f"[bold]Success Rate:[/] {summary.get('success_rate', 0):.1%}")
        console.print(f"[bold]Actions Taken:[/] {summary.get('actions_taken', 0)}")
        console.print(f"[bold]Action Success Rate:[/] {summary.get('action_success_rate', 0):.1%}")


def run_api(host: str = "0.0.0.0", port: int = 8000):
    """Run the REST API server."""
    import uvicorn
    from src.utils.config import get_config
    
    config = get_config()
    host = host or config.api.host
    port = port or config.api.port
    
    console.print(f"\n[bold green]Starting REST API Server[/]")
    console.print(f"URL: http://{host}:{port}")
    console.print("[dim]Press Ctrl+C to stop[/]\n")
    
    uvicorn.run(
        "src.api.main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Agentic AI Network Optimizer",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Demo command
    demo_parser = subparsers.add_parser("demo", help="Run a single optimization cycle demo")
    
    # Monitor command
    monitor_parser = subparsers.add_parser("monitor", help="Run continuous monitoring")
    monitor_parser.add_argument(
        "-i", "--interval",
        type=int,
        default=10,
        help="Seconds between cycles (default: 10)"
    )
    monitor_parser.add_argument(
        "-n", "--cycles",
        type=int,
        default=0,
        help="Number of cycles to run (0 = unlimited)"
    )
    
    # API command
    api_parser = subparsers.add_parser("api", help="Start the REST API server")
    api_parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    api_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)"
    )
    
    args = parser.parse_args()
    
    print_banner()
    
    if args.command == "demo":
        asyncio.run(run_demo())
    elif args.command == "monitor":
        asyncio.run(run_monitor(args.interval, args.cycles))
    elif args.command == "api":
        run_api(args.host, args.port)
    else:
        parser.print_help()
        console.print("\n[yellow]Example usage:[/]")
        console.print("  python run.py demo      # Run a single cycle demo")
        console.print("  python run.py monitor   # Start continuous monitoring")
        console.print("  python run.py api       # Start REST API server")


if __name__ == "__main__":
    main()
