"""
Decision Agent - LLM-powered decision making for network optimization.
"""

import json
from datetime import datetime
from typing import Optional

from .base_agent import AgentMessage, BaseAgent
from ..llm.provider import LLMProvider, get_llm_provider
from ..llm.prompts import DECISION_SYSTEM_PROMPT, format_decision_prompt
from ..utils.config import get_config
from ..utils.logging import DecisionLogger


class DecisionAgent(BaseAgent):
    """
    Agent responsible for making optimization decisions using LLM.
    
    Responsibilities:
    - Analyze network metrics and anomalies
    - Use LLM to reason about optimal actions
    - Generate action recommendations
    - Consider historical feedback for better decisions
    """
    
    def __init__(self):
        super().__init__("decision")
        self.config = get_config().agents.decision
        self.llm: LLMProvider = get_llm_provider()
        self.decision_logger = DecisionLogger(get_config().system.data_dir)
        self.decision_history: list[dict] = []
        self.feedback_context: list[dict] = []
    
    async def process(self, message: Optional[AgentMessage] = None) -> Optional[AgentMessage]:
        """Process metrics report and generate decisions."""
        
        if not message:
            return None
        
        if message.message_type == "metrics_report":
            return await self._analyze_and_decide(message.payload)
        elif message.message_type == "feedback":
            await self._incorporate_feedback(message.payload)
            return None
        elif message.message_type == "get_decisions":
            return await self.send_message(
                message.sender,
                "decisions_response",
                {"decisions": self.decision_history[-10:]}
            )
        
        return None
    
    async def _analyze_and_decide(self, metrics_report: dict) -> AgentMessage:
        """Analyze metrics and generate action decisions."""
        self.logger.info("Analyzing network state and generating decisions...")
        
        metrics = metrics_report.get("metrics", {})
        anomalies = metrics_report.get("anomalies", [])
        health_score = metrics_report.get("health_score", 100)
        
        # If no anomalies and health is good, no action needed
        if not anomalies and health_score > 90:
            self.logger.success("Network is healthy, no action required")
            decision = {
                "action_required": False,
                "reasoning": "Network metrics are within normal ranges",
                "health_score": health_score,
                "recommended_actions": []
            }
            self._log_decision(decision, metrics_report)
            return await self.send_message(
                "coordinator",
                "decision",
                decision
            )
        
        # Use LLM to analyze and decide
        prompt = format_decision_prompt(
            metrics=metrics,
            anomalies=anomalies,
            health_score=health_score,
            feedback_history=self.feedback_context[-5:]  # Last 5 feedback entries
        )
        
        try:
            llm_response = await self.llm.generate(
                system_prompt=DECISION_SYSTEM_PROMPT,
                user_prompt=prompt
            )
            
            # Parse LLM response
            decision = self._parse_llm_decision(llm_response)
            
        except Exception as e:
            self.logger.error(f"LLM analysis failed: {str(e)}")
            # Fallback to rule-based decision
            decision = self._fallback_decision(anomalies, health_score)
        
        # Log the decision
        self.logger.decision(decision)
        self._log_decision(decision, metrics_report)
        
        return await self.send_message(
            "coordinator",
            "decision",
            decision
        )
    
    def _parse_llm_decision(self, llm_response: str) -> dict:
        """Parse the LLM response into a structured decision."""
        try:
            # Try to extract JSON from the response
            # Look for JSON block in the response
            if "```json" in llm_response:
                json_start = llm_response.find("```json") + 7
                json_end = llm_response.find("```", json_start)
                json_str = llm_response[json_start:json_end].strip()
            elif "{" in llm_response:
                json_start = llm_response.find("{")
                json_end = llm_response.rfind("}") + 1
                json_str = llm_response[json_start:json_end]
            else:
                raise ValueError("No JSON found in response")
            
            decision = json.loads(json_str)
            
            # Ensure required fields
            decision.setdefault("action_required", True)
            decision.setdefault("reasoning", "LLM analysis")
            decision.setdefault("recommended_actions", [])
            decision.setdefault("confidence", 0.7)
            
            # Limit actions per cycle
            max_actions = self.config.max_actions_per_cycle
            decision["recommended_actions"] = decision["recommended_actions"][:max_actions]
            
            return decision
            
        except (json.JSONDecodeError, ValueError) as e:
            self.logger.warning(f"Failed to parse LLM response: {e}")
            # Return a basic decision based on the text
            return {
                "action_required": True,
                "reasoning": llm_response[:500],
                "recommended_actions": [],
                "confidence": 0.5,
                "parse_error": True
            }
    
    def _fallback_decision(self, anomalies: list[dict], health_score: float) -> dict:
        """Generate rule-based decisions when LLM fails."""
        self.logger.warning("Using fallback rule-based decision")
        
        actions = []
        
        for anomaly in anomalies[:3]:  # Limit to top 3
            anomaly_type = anomaly.get("type", "")
            node = anomaly.get("node", "unknown")
            
            if anomaly_type == "high_latency":
                actions.append({
                    "action": "optimize_routing",
                    "target": node,
                    "priority": "high" if anomaly.get("severity") == "critical" else "medium",
                    "params": {"optimize_path": True}
                })
            elif anomaly_type == "high_packet_loss":
                actions.append({
                    "action": "reduce_traffic",
                    "target": node,
                    "priority": "critical",
                    "params": {"throttle_percent": 30}
                })
            elif anomaly_type == "high_cpu":
                actions.append({
                    "action": "load_balance",
                    "target": node,
                    "priority": "high",
                    "params": {"redistribute": True}
                })
            elif anomaly_type == "high_memory":
                actions.append({
                    "action": "clear_cache",
                    "target": node,
                    "priority": "medium",
                    "params": {"aggressive": anomaly.get("severity") == "critical"}
                })
            elif anomaly_type == "low_bandwidth":
                actions.append({
                    "action": "request_bandwidth",
                    "target": node,
                    "priority": "medium",
                    "params": {"increase_percent": 50}
                })
        
        return {
            "action_required": len(actions) > 0,
            "reasoning": f"Rule-based decision triggered by {len(anomalies)} anomalies",
            "recommended_actions": actions,
            "confidence": 0.6,
            "health_score": health_score,
            "fallback": True
        }
    
    async def _incorporate_feedback(self, feedback: dict):
        """Incorporate feedback from previous actions."""
        self.logger.info("Incorporating feedback from previous actions")
        
        self.feedback_context.append({
            "timestamp": datetime.now().isoformat(),
            **feedback
        })
        
        # Keep only last 20 feedback entries
        self.feedback_context = self.feedback_context[-20:]
        
        # Log feedback for learning
        if feedback.get("success"):
            self.logger.success(f"Previous action was effective: {feedback.get('details', '')}")
        else:
            self.logger.warning(f"Previous action was not effective: {feedback.get('details', '')}")
    
    def _log_decision(self, decision: dict, context: dict):
        """Log decision for persistence and learning."""
        log_entry = {
            "decision": decision,
            "context": {
                "health_score": context.get("health_score"),
                "anomaly_count": len(context.get("anomalies", [])),
            },
            "feedback_context_size": len(self.feedback_context)
        }
        
        self.decision_history.append(log_entry)
        self.decision_logger.log_decision(log_entry)
        
        # Keep only last 100 in memory
        self.decision_history = self.decision_history[-100:]
    
    def update_feedback_context(self, feedback: list[dict]):
        """Update the feedback context directly."""
        self.feedback_context = feedback[-20:]
