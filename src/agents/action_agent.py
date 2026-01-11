"""
Action Agent - Executes corrective actions on the network.
"""

import asyncio
import random
from datetime import datetime
from typing import Optional

from .base_agent import AgentMessage, BaseAgent
from ..network.actions import ActionExecutor, ActionResult
from ..utils.config import get_config


class ActionAgent(BaseAgent):
    """
    Agent responsible for executing network actions.
    
    Responsibilities:
    - Receive action recommendations from Decision Agent
    - Execute actions (simulated or real)
    - Report action results for feedback loop
    """
    
    def __init__(self):
        super().__init__("action")
        self.config = get_config().agents.action
        self.executor = ActionExecutor(dry_run=self.config.dry_run)
        self.action_history: list[dict] = []
        self.pending_actions: list[dict] = []
    
    async def process(self, message: Optional[AgentMessage] = None) -> Optional[AgentMessage]:
        """Process decisions and execute actions."""
        
        if not message:
            return None
        
        if message.message_type == "decision":
            return await self._execute_actions(message.payload)
        elif message.message_type == "cancel_action":
            return await self._cancel_action(message.payload)
        elif message.message_type == "get_history":
            return await self.send_message(
                message.sender,
                "history_response",
                {"history": self.action_history[-20:]}
            )
        
        return None
    
    async def _execute_actions(self, decision: dict) -> AgentMessage:
        """Execute the recommended actions from a decision."""
        
        if not decision.get("action_required"):
            self.logger.info("No action required")
            return await self.send_message(
                "coordinator",
                "action_result",
                {
                    "executed": False,
                    "reason": "No action was required",
                    "results": []
                }
            )
        
        actions = decision.get("recommended_actions", [])
        if not actions:
            self.logger.info("No specific actions recommended")
            return await self.send_message(
                "coordinator",
                "action_result",
                {
                    "executed": False,
                    "reason": "No specific actions were recommended",
                    "results": []
                }
            )
        
        self.logger.info(f"Executing {len(actions)} actions...")
        results = []
        
        for action in actions:
            action_name = action.get("action", "unknown")
            target = action.get("target", "unknown")
            priority = action.get("priority", "medium")
            params = action.get("params", {})
            
            self.logger.info(f"Executing: {action_name} on {target} (priority: {priority})")
            
            try:
                # Execute with timeout
                result = await asyncio.wait_for(
                    self.executor.execute(
                        action=action_name,
                        target=target,
                        params=params
                    ),
                    timeout=self.config.action_timeout
                )
                
                if result.success:
                    self.logger.success(f"Action completed: {action_name}")
                else:
                    self.logger.warning(f"Action failed: {action_name} - {result.message}")
                
                results.append({
                    "action": action_name,
                    "target": target,
                    "success": result.success,
                    "message": result.message,
                    "metrics_before": result.metrics_before,
                    "metrics_after": result.metrics_after,
                    "timestamp": datetime.now().isoformat()
                })
                
            except asyncio.TimeoutError:
                self.logger.error(f"Action timed out: {action_name}")
                results.append({
                    "action": action_name,
                    "target": target,
                    "success": False,
                    "message": "Action timed out",
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                self.logger.error(f"Action error: {action_name} - {str(e)}")
                results.append({
                    "action": action_name,
                    "target": target,
                    "success": False,
                    "message": str(e),
                    "timestamp": datetime.now().isoformat()
                })
        
        # Record in history
        self._record_actions(decision, results)
        
        # Calculate overall success
        successful = sum(1 for r in results if r.get("success"))
        total = len(results)
        
        return await self.send_message(
            "coordinator",
            "action_result",
            {
                "executed": True,
                "results": results,
                "summary": {
                    "total": total,
                    "successful": successful,
                    "failed": total - successful,
                    "success_rate": successful / total if total > 0 else 0
                }
            }
        )
    
    async def _cancel_action(self, payload: dict) -> AgentMessage:
        """Cancel a pending or running action."""
        action_id = payload.get("action_id")
        self.logger.warning(f"Cancelling action: {action_id}")
        
        # Implementation would depend on the action execution model
        return await self.send_message(
            "coordinator",
            "cancel_result",
            {"action_id": action_id, "cancelled": True}
        )
    
    def _record_actions(self, decision: dict, results: list[dict]):
        """Record executed actions in history."""
        record = {
            "timestamp": datetime.now().isoformat(),
            "decision_reasoning": decision.get("reasoning", ""),
            "decision_confidence": decision.get("confidence", 0),
            "results": results
        }
        
        self.action_history.append(record)
        
        # Keep only last 100 records
        self.action_history = self.action_history[-100:]
    
    def get_action_history(self) -> list[dict]:
        """Get the history of executed actions."""
        return self.action_history
    
    def get_success_rate(self) -> float:
        """Calculate overall success rate of actions."""
        if not self.action_history:
            return 1.0
        
        total_actions = 0
        successful_actions = 0
        
        for record in self.action_history:
            for result in record.get("results", []):
                total_actions += 1
                if result.get("success"):
                    successful_actions += 1
        
        return successful_actions / total_actions if total_actions > 0 else 1.0
