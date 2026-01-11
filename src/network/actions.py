"""
Network action definitions and execution.
"""

import asyncio
import random
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class ActionType(str, Enum):
    OPTIMIZE_ROUTING = "optimize_routing"
    REDUCE_TRAFFIC = "reduce_traffic"
    LOAD_BALANCE = "load_balance"
    CLEAR_CACHE = "clear_cache"
    REQUEST_BANDWIDTH = "request_bandwidth"
    RESTART_SERVICE = "restart_service"
    ALERT = "alert"
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"


@dataclass
class ActionResult:
    """Result of an action execution."""
    success: bool
    message: str
    action: str
    target: str
    metrics_before: Optional[dict] = None
    metrics_after: Optional[dict] = None
    duration_ms: float = 0


class ActionExecutor:
    """Executes network actions (simulated or real)."""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.execution_history: list[dict] = []
        
        # Action success probabilities (for simulation)
        self.success_rates = {
            ActionType.OPTIMIZE_ROUTING: 0.85,
            ActionType.REDUCE_TRAFFIC: 0.90,
            ActionType.LOAD_BALANCE: 0.80,
            ActionType.CLEAR_CACHE: 0.95,
            ActionType.REQUEST_BANDWIDTH: 0.70,
            ActionType.RESTART_SERVICE: 0.75,
            ActionType.ALERT: 1.0,
            ActionType.SCALE_UP: 0.85,
            ActionType.SCALE_DOWN: 0.90,
        }
        
        # Action durations (ms) for simulation
        self.action_durations = {
            ActionType.OPTIMIZE_ROUTING: (500, 2000),
            ActionType.REDUCE_TRAFFIC: (200, 500),
            ActionType.LOAD_BALANCE: (1000, 5000),
            ActionType.CLEAR_CACHE: (100, 300),
            ActionType.REQUEST_BANDWIDTH: (1000, 3000),
            ActionType.RESTART_SERVICE: (5000, 15000),
            ActionType.ALERT: (50, 100),
            ActionType.SCALE_UP: (10000, 30000),
            ActionType.SCALE_DOWN: (5000, 10000),
        }
    
    async def execute(
        self,
        action: str,
        target: str,
        params: dict = None
    ) -> ActionResult:
        """Execute an action on a network target."""
        params = params or {}
        start_time = datetime.now()
        
        # Get action type
        try:
            action_type = ActionType(action)
        except ValueError:
            return ActionResult(
                success=False,
                message=f"Unknown action type: {action}",
                action=action,
                target=target
            )
        
        if self.dry_run:
            return await self._dry_run_action(action_type, target, params)
        
        # Simulate action execution
        result = await self._simulate_action(action_type, target, params)
        
        # Record execution
        duration = (datetime.now() - start_time).total_seconds() * 1000
        result.duration_ms = duration
        
        self.execution_history.append({
            "timestamp": start_time.isoformat(),
            "action": action,
            "target": target,
            "params": params,
            "success": result.success,
            "duration_ms": duration
        })
        
        # Keep only last 100 executions
        self.execution_history = self.execution_history[-100:]
        
        return result
    
    async def _dry_run_action(
        self,
        action_type: ActionType,
        target: str,
        params: dict
    ) -> ActionResult:
        """Perform a dry run of an action."""
        return ActionResult(
            success=True,
            message=f"[DRY RUN] Would execute {action_type.value} on {target}",
            action=action_type.value,
            target=target
        )
    
    async def _simulate_action(
        self,
        action_type: ActionType,
        target: str,
        params: dict
    ) -> ActionResult:
        """Simulate action execution with realistic timing and outcomes."""
        
        # Simulate execution time
        min_dur, max_dur = self.action_durations.get(action_type, (100, 500))
        duration = random.uniform(min_dur, max_dur)
        await asyncio.sleep(duration / 1000)  # Convert to seconds
        
        # Determine success
        success_rate = self.success_rates.get(action_type, 0.8)
        success = random.random() < success_rate
        
        # Generate result message
        if success:
            message = self._get_success_message(action_type, target, params)
        else:
            message = self._get_failure_message(action_type, target)
        
        return ActionResult(
            success=success,
            message=message,
            action=action_type.value,
            target=target,
            duration_ms=duration
        )
    
    def _get_success_message(
        self,
        action_type: ActionType,
        target: str,
        params: dict
    ) -> str:
        """Generate a success message for an action."""
        messages = {
            ActionType.OPTIMIZE_ROUTING: f"Successfully optimized routing for {target}. New path established.",
            ActionType.REDUCE_TRAFFIC: f"Traffic reduced on {target} by {params.get('throttle_percent', 20)}%.",
            ActionType.LOAD_BALANCE: f"Load balanced across nodes from {target}. Traffic redistributed.",
            ActionType.CLEAR_CACHE: f"Cache cleared on {target}. Memory freed.",
            ActionType.REQUEST_BANDWIDTH: f"Bandwidth increased on {target} by {params.get('increase_percent', 50)}%.",
            ActionType.RESTART_SERVICE: f"Service on {target} restarted successfully.",
            ActionType.ALERT: f"Alert sent for {target}.",
            ActionType.SCALE_UP: f"Scaled up {target}. New instance launched.",
            ActionType.SCALE_DOWN: f"Scaled down {target}. Instance terminated.",
        }
        return messages.get(action_type, f"Action {action_type.value} completed on {target}")
    
    def _get_failure_message(
        self,
        action_type: ActionType,
        target: str
    ) -> str:
        """Generate a failure message for an action."""
        failures = {
            ActionType.OPTIMIZE_ROUTING: f"Failed to optimize routing for {target}: No alternate path found.",
            ActionType.REDUCE_TRAFFIC: f"Failed to reduce traffic on {target}: Minimum threshold reached.",
            ActionType.LOAD_BALANCE: f"Failed to load balance from {target}: No available capacity.",
            ActionType.CLEAR_CACHE: f"Failed to clear cache on {target}: Service unavailable.",
            ActionType.REQUEST_BANDWIDTH: f"Failed to increase bandwidth on {target}: Provider limit reached.",
            ActionType.RESTART_SERVICE: f"Failed to restart service on {target}: Dependencies not ready.",
            ActionType.ALERT: f"Failed to send alert for {target}: Notification service error.",
            ActionType.SCALE_UP: f"Failed to scale up {target}: Resource quota exceeded.",
            ActionType.SCALE_DOWN: f"Failed to scale down {target}: Minimum instances reached.",
        }
        return failures.get(action_type, f"Action {action_type.value} failed on {target}")
    
    def get_available_actions(self) -> list[dict]:
        """Get list of available actions with descriptions."""
        descriptions = {
            ActionType.OPTIMIZE_ROUTING: "Optimize network routing to reduce latency",
            ActionType.REDUCE_TRAFFIC: "Throttle traffic to reduce congestion",
            ActionType.LOAD_BALANCE: "Redistribute load across multiple nodes",
            ActionType.CLEAR_CACHE: "Clear caches to free memory",
            ActionType.REQUEST_BANDWIDTH: "Request additional bandwidth allocation",
            ActionType.RESTART_SERVICE: "Restart a service to clear issues",
            ActionType.ALERT: "Send an alert to operations team",
            ActionType.SCALE_UP: "Scale up resources by adding instances",
            ActionType.SCALE_DOWN: "Scale down resources by removing instances",
        }
        
        return [
            {
                "action": action.value,
                "description": descriptions.get(action, ""),
                "success_rate": self.success_rates.get(action, 0.8),
                "estimated_duration_ms": sum(self.action_durations.get(action, (100, 500))) / 2
            }
            for action in ActionType
        ]
    
    def get_execution_history(self, limit: int = 20) -> list[dict]:
        """Get recent execution history."""
        return self.execution_history[-limit:]
