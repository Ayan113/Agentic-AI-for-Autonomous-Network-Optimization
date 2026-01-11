"""
Agent Coordinator - Orchestrates the multi-agent system.
"""

import asyncio
from datetime import datetime
from typing import Optional

from .base_agent import AgentMessage, AgentStatus, BaseAgent
from .monitor_agent import MonitorAgent
from .decision_agent import DecisionAgent
from .action_agent import ActionAgent
from ..feedback.loop import FeedbackLoop
from ..utils.config import get_config
from ..utils.logging import AgentLogger, DecisionLogger, console


class Coordinator(BaseAgent):
    """
    Orchestrates communication between agents and manages the optimization loop.
    
    Flow:
    1. Monitor Agent collects metrics
    2. Decision Agent analyzes and recommends actions
    3. Action Agent executes recommendations
    4. Feedback Loop evaluates results
    5. Repeat
    """
    
    def __init__(self):
        super().__init__("coordinator")
        self.config = get_config()
        
        # Initialize agents
        self.monitor = MonitorAgent()
        self.decision = DecisionAgent()
        self.action = ActionAgent()
        self.feedback = FeedbackLoop()
        
        # Coordination state
        self.cycle_count = 0
        self.last_cycle_time: Optional[datetime] = None
        self.cycle_history: list[dict] = []
        self._running = False
        
        self.logger.info("Coordinator initialized with all agents")
    
    async def process(self, message: Optional[AgentMessage] = None) -> Optional[AgentMessage]:
        """Process a single optimization cycle."""
        return await self.run_cycle()
    
    async def run_cycle(self) -> dict:
        """Run a single Monitor → Decide → Act cycle."""
        self.cycle_count += 1
        cycle_start = datetime.now()
        
        console.rule(f"[bold cyan]Optimization Cycle {self.cycle_count}[/]")
        self.logger.info(f"Starting optimization cycle {self.cycle_count}")
        
        cycle_result = {
            "cycle": self.cycle_count,
            "start_time": cycle_start.isoformat(),
            "phases": {}
        }
        
        try:
            # Phase 1: Monitor
            self.logger.info("Phase 1: Collecting metrics...")
            metrics_message = await self.monitor.process()
            cycle_result["phases"]["monitor"] = {
                "status": "completed",
                "health_score": metrics_message.payload.get("health_score") if metrics_message else None,
                "anomaly_count": len(metrics_message.payload.get("anomalies", [])) if metrics_message else 0
            }
            
            if not metrics_message:
                raise Exception("Monitor agent returned no metrics")
            
            # Phase 2: Decision
            self.logger.info("Phase 2: Analyzing and deciding...")
            
            # Inject feedback context into decision agent
            feedback_context = self.feedback.get_feedback_context()
            self.decision.update_feedback_context(feedback_context)
            
            decision_message = await self.decision.process(metrics_message)
            
            decision_payload = decision_message.payload if decision_message else {}
            cycle_result["phases"]["decision"] = {
                "status": "completed",
                "action_required": decision_payload.get("action_required", False),
                "actions_recommended": len(decision_payload.get("recommended_actions", [])),
                "confidence": decision_payload.get("confidence", 0)
            }
            
            # Phase 3: Action
            if decision_message and decision_payload.get("action_required"):
                self.logger.info("Phase 3: Executing actions...")
                action_message = await self.action.process(decision_message)
                
                action_payload = action_message.payload if action_message else {}
                cycle_result["phases"]["action"] = {
                    "status": "completed",
                    "executed": action_payload.get("executed", False),
                    "summary": action_payload.get("summary", {})
                }
                
                # Phase 4: Feedback
                if action_message and action_payload.get("executed"):
                    self.logger.info("Phase 4: Recording feedback...")
                    
                    # Wait briefly for effects to manifest
                    await asyncio.sleep(1)
                    
                    # Collect post-action metrics
                    post_metrics = await self.monitor.process()
                    
                    feedback = await self.feedback.evaluate(
                        action_results=action_payload.get("results", []),
                        pre_metrics=metrics_message.payload.get("metrics"),
                        post_metrics=post_metrics.payload.get("metrics") if post_metrics else None
                    )
                    
                    cycle_result["phases"]["feedback"] = {
                        "status": "completed",
                        "improvement_score": feedback.get("improvement_score", 0),
                        "success": feedback.get("overall_success", False)
                    }
                    
                    # Send feedback to decision agent
                    feedback_message = AgentMessage(
                        sender="coordinator",
                        recipient="decision",
                        message_type="feedback",
                        payload=feedback
                    )
                    await self.decision.process(feedback_message)
            else:
                self.logger.info("Phase 3: No actions needed, skipping...")
                cycle_result["phases"]["action"] = {"status": "skipped"}
                cycle_result["phases"]["feedback"] = {"status": "skipped"}
            
            cycle_result["status"] = "completed"
            
        except Exception as e:
            self.logger.error(f"Cycle failed: {str(e)}")
            cycle_result["status"] = "failed"
            cycle_result["error"] = str(e)
        
        # Record cycle completion
        cycle_end = datetime.now()
        cycle_result["end_time"] = cycle_end.isoformat()
        cycle_result["duration_seconds"] = (cycle_end - cycle_start).total_seconds()
        
        self.cycle_history.append(cycle_result)
        self.last_cycle_time = cycle_end
        
        # Keep only last 100 cycles
        self.cycle_history = self.cycle_history[-100:]
        
        console.rule(f"[bold green]Cycle {self.cycle_count} Complete[/]")
        
        return cycle_result
    
    async def run_continuous(self, interval: Optional[int] = None):
        """Run continuous optimization cycles."""
        if interval is None:
            interval = self.config.agents.monitor.polling_interval
        
        self._running = True
        self.status = AgentStatus.RUNNING
        self.logger.info(f"Starting continuous monitoring (interval: {interval}s)")
        
        try:
            while self._running:
                await self.run_cycle()
                
                if self._running:
                    self.logger.info(f"Waiting {interval} seconds until next cycle...")
                    await asyncio.sleep(interval)
                    
        except asyncio.CancelledError:
            self.logger.info("Continuous monitoring cancelled")
        finally:
            self._running = False
            self.status = AgentStatus.IDLE
    
    async def stop(self):
        """Stop the coordinator and all agents."""
        self._running = False
        self.logger.info("Stopping coordinator...")
        
        await self.monitor.stop()
        await self.decision.stop()
        await self.action.stop()
        
        self.status = AgentStatus.IDLE
        self.logger.info("All agents stopped")
    
    def get_system_status(self) -> dict:
        """Get the status of all agents."""
        return {
            "coordinator": self.get_status(),
            "monitor": self.monitor.get_status(),
            "decision": self.decision.get_status(),
            "action": self.action.get_status(),
            "feedback": {
                "learning_entries": len(self.feedback.get_feedback_context())
            },
            "cycles": {
                "total": self.cycle_count,
                "last_cycle": self.last_cycle_time.isoformat() if self.last_cycle_time else None
            }
        }
    
    def get_cycle_history(self, limit: int = 10) -> list[dict]:
        """Get recent cycle history."""
        return self.cycle_history[-limit:]
    
    def get_performance_summary(self) -> dict:
        """Get performance summary across all cycles."""
        if not self.cycle_history:
            return {"message": "No cycles completed yet"}
        
        completed_cycles = [c for c in self.cycle_history if c.get("status") == "completed"]
        failed_cycles = [c for c in self.cycle_history if c.get("status") == "failed"]
        
        # Calculate averages
        durations = [c.get("duration_seconds", 0) for c in completed_cycles]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        # Count actions
        actions_taken = 0
        successful_actions = 0
        for cycle in completed_cycles:
            action_phase = cycle.get("phases", {}).get("action", {})
            if action_phase.get("executed"):
                summary = action_phase.get("summary", {})
                actions_taken += summary.get("total", 0)
                successful_actions += summary.get("successful", 0)
        
        return {
            "total_cycles": len(self.cycle_history),
            "completed_cycles": len(completed_cycles),
            "failed_cycles": len(failed_cycles),
            "success_rate": len(completed_cycles) / len(self.cycle_history) if self.cycle_history else 0,
            "average_cycle_duration": avg_duration,
            "actions_taken": actions_taken,
            "successful_actions": successful_actions,
            "action_success_rate": successful_actions / actions_taken if actions_taken > 0 else 1.0
        }
