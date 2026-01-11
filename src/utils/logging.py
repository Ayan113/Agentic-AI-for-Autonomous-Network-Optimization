"""
Logging utilities with Rich console output.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .config import get_config


# Rich console for beautiful output
console = Console()


def setup_logging(log_level: Optional[str] = None) -> logging.Logger:
    """Set up logging with Rich handler."""
    config = get_config()
    level = log_level or config.system.log_level
    
    # Configure root logger
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)]
    )
    
    logger = logging.getLogger("network_optimizer")
    logger.setLevel(level)
    
    return logger


def get_logger(name: str = "network_optimizer") -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)


class AgentLogger:
    """Specialized logger for agents with visual formatting."""
    
    AGENT_COLORS = {
        "monitor": "cyan",
        "decision": "yellow",
        "action": "green",
        "coordinator": "magenta",
        "feedback": "blue"
    }
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.color = self.AGENT_COLORS.get(agent_name.lower(), "white")
        self.logger = get_logger(f"agent.{agent_name}")
    
    def info(self, message: str, **kwargs):
        """Log info message with agent styling."""
        styled = Text(f"[{self.agent_name.upper()}] ", style=f"bold {self.color}")
        styled.append(message)
        console.print(styled)
        self.logger.info(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        styled = Text(f"[{self.agent_name.upper()}] ⚠️ ", style=f"bold {self.color}")
        styled.append(message, style="yellow")
        console.print(styled)
        self.logger.warning(message, extra=kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        styled = Text(f"[{self.agent_name.upper()}] ❌ ", style=f"bold {self.color}")
        styled.append(message, style="red")
        console.print(styled)
        self.logger.error(message, extra=kwargs)
    
    def success(self, message: str):
        """Log success message."""
        styled = Text(f"[{self.agent_name.upper()}] ✅ ", style=f"bold {self.color}")
        styled.append(message, style="green")
        console.print(styled)
    
    def decision(self, decision: dict):
        """Log a decision with formatted panel."""
        panel = Panel(
            json.dumps(decision, indent=2),
            title=f"[bold {self.color}]{self.agent_name.upper()} Decision[/]",
            border_style=self.color
        )
        console.print(panel)


def log_metrics_table(metrics: dict, title: str = "Network Metrics"):
    """Display metrics in a formatted table."""
    table = Table(title=title, show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")
    table.add_column("Status", style="green")
    
    for key, value in metrics.items():
        if isinstance(value, float):
            formatted = f"{value:.2f}"
        else:
            formatted = str(value)
        
        # Determine status based on metric type
        status = "✅ Normal"
        if "loss" in key.lower() and isinstance(value, (int, float)) and value > 5:
            status = "⚠️ High"
        elif "latency" in key.lower() and isinstance(value, (int, float)) and value > 100:
            status = "⚠️ High"
        elif "cpu" in key.lower() and isinstance(value, (int, float)) and value > 80:
            status = "🔴 Critical"
        
        table.add_row(key, formatted, status)
    
    console.print(table)


def log_action_result(action: str, success: bool, details: str = ""):
    """Log an action result with visual feedback."""
    if success:
        console.print(f"[green]✅ Action Executed:[/] {action}")
    else:
        console.print(f"[red]❌ Action Failed:[/] {action}")
    
    if details:
        console.print(f"   [dim]{details}[/]")


class DecisionLogger:
    """Logger for persisting decisions to a JSON file."""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.decisions_file = self.data_dir / "decisions.json"
        self.performance_file = self.data_dir / "performance.json"
        
        # Initialize files if they don't exist
        for file in [self.decisions_file, self.performance_file]:
            if not file.exists():
                file.write_text("[]")
    
    def log_decision(self, decision: dict):
        """Log a decision to the decisions file."""
        decision["timestamp"] = datetime.now().isoformat()
        
        decisions = json.loads(self.decisions_file.read_text())
        decisions.append(decision)
        
        # Keep only last 1000 decisions
        if len(decisions) > 1000:
            decisions = decisions[-1000:]
        
        self.decisions_file.write_text(json.dumps(decisions, indent=2))
    
    def log_performance(self, metrics: dict):
        """Log performance metrics."""
        metrics["timestamp"] = datetime.now().isoformat()
        
        performance = json.loads(self.performance_file.read_text())
        performance.append(metrics)
        
        # Keep only last 1000 entries
        if len(performance) > 1000:
            performance = performance[-1000:]
        
        self.performance_file.write_text(json.dumps(performance, indent=2))
    
    def get_decisions(self, limit: int = 100) -> list[dict]:
        """Get recent decisions."""
        decisions = json.loads(self.decisions_file.read_text())
        return decisions[-limit:]
    
    def get_performance(self, limit: int = 100) -> list[dict]:
        """Get recent performance metrics."""
        performance = json.loads(self.performance_file.read_text())
        return performance[-limit:]
