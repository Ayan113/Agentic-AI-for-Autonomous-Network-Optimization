"""
Feedback loop for learning from action outcomes.
"""

from datetime import datetime
from typing import Any, Optional

from ..network.metrics import MetricsDelta, NetworkMetrics, NodeMetrics
from ..utils.config import get_config
from ..utils.logging import AgentLogger, DecisionLogger


class FeedbackLoop:
    """
    Evaluates action effectiveness and maintains learning context.
    
    Responsibilities:
    - Compare pre/post action metrics
    - Calculate improvement scores
    - Maintain feedback history for decision making
    - Track overall system performance trends
    """
    
    def __init__(self):
        self.config = get_config().feedback
        self.logger = AgentLogger("feedback")
        self.decision_logger = DecisionLogger(get_config().system.data_dir)
        self.feedback_history: list[dict] = []
        self.performance_trends: list[dict] = []
    
    async def evaluate(
        self,
        action_results: list[dict],
        pre_metrics: Optional[dict],
        post_metrics: Optional[dict]
    ) -> dict:
        """
        Evaluate the effectiveness of executed actions.
        
        Args:
            action_results: Results from action execution
            pre_metrics: Metrics before actions
            post_metrics: Metrics after actions
            
        Returns:
            Feedback evaluation with scores and insights
        """
        self.logger.info("Evaluating action effectiveness...")
        
        if not action_results:
            return {
                "overall_success": True,
                "improvement_score": 0,
                "details": "No actions to evaluate",
                "action_feedback": []
            }
        
        # Calculate metrics improvements
        improvements = []
        if pre_metrics and post_metrics:
            improvements = self._calculate_improvements(pre_metrics, post_metrics)
        
        # Evaluate each action
        action_feedback = []
        for result in action_results:
            action = result.get("action", "unknown")
            target = result.get("target", "unknown")
            success = result.get("success", False)
            
            # Find relevant improvement for this target
            target_improvement = next(
                (imp for imp in improvements if imp.get("node_id") == target),
                None
            )
            
            effectiveness = self._calculate_effectiveness(
                action=action,
                success=success,
                improvement=target_improvement
            )
            
            feedback = {
                "action": action,
                "target": target,
                "execution_success": success,
                "effectiveness_score": effectiveness["score"],
                "effectiveness_rating": effectiveness["rating"],
                "improvement_details": target_improvement,
                "timestamp": datetime.now().isoformat()
            }
            
            action_feedback.append(feedback)
            
            # Log individual feedback
            if effectiveness["score"] > 0.7:
                self.logger.success(f"{action} on {target}: {effectiveness['rating']}")
            elif effectiveness["score"] > 0.4:
                self.logger.info(f"{action} on {target}: {effectiveness['rating']}")
            else:
                self.logger.warning(f"{action} on {target}: {effectiveness['rating']}")
        
        # Calculate overall success
        avg_effectiveness = sum(
            fb["effectiveness_score"] for fb in action_feedback
        ) / len(action_feedback) if action_feedback else 0
        
        # Calculate overall health improvement
        health_improvement = 0
        if pre_metrics and post_metrics:
            pre_health = self._get_health_from_metrics(pre_metrics)
            post_health = self._get_health_from_metrics(post_metrics)
            health_improvement = post_health - pre_health
        
        overall_feedback = {
            "overall_success": avg_effectiveness > 0.5,
            "improvement_score": health_improvement,
            "average_effectiveness": avg_effectiveness,
            "action_feedback": action_feedback,
            "details": self._generate_summary(action_feedback, health_improvement),
            "timestamp": datetime.now().isoformat()
        }
        
        # Store in history
        self._record_feedback(overall_feedback)
        
        return overall_feedback
    
    def _calculate_improvements(
        self,
        pre_metrics: dict,
        post_metrics: dict
    ) -> list[dict]:
        """Calculate metric changes between snapshots."""
        improvements = []
        
        pre_nodes = {n["node_id"]: n for n in pre_metrics.get("nodes", [])}
        post_nodes = {n["node_id"]: n for n in post_metrics.get("nodes", [])}
        
        for node_id, pre_node in pre_nodes.items():
            if node_id not in post_nodes:
                continue
            
            post_node = post_nodes[node_id]
            
            improvement = {
                "node_id": node_id,
                "latency_change": post_node.get("latency", 0) - pre_node.get("latency", 0),
                "bandwidth_change": post_node.get("bandwidth", 0) - pre_node.get("bandwidth", 0),
                "packet_loss_change": post_node.get("packet_loss", 0) - pre_node.get("packet_loss", 0),
                "cpu_change": post_node.get("cpu_usage", 0) - pre_node.get("cpu_usage", 0),
                "memory_change": post_node.get("memory_usage", 0) - pre_node.get("memory_usage", 0)
            }
            
            # Calculate improvement score (negative changes in latency/loss/cpu/memory are good)
            score = 0
            if improvement["latency_change"] < 0:
                score += min(30, abs(improvement["latency_change"]) * 0.5)
            if improvement["packet_loss_change"] < 0:
                score += min(25, abs(improvement["packet_loss_change"]) * 5)
            if improvement["bandwidth_change"] > 0:
                score += min(20, improvement["bandwidth_change"] * 0.05)
            if improvement["cpu_change"] < 0:
                score += min(15, abs(improvement["cpu_change"]) * 0.5)
            if improvement["memory_change"] < 0:
                score += min(10, abs(improvement["memory_change"]) * 0.4)
            
            improvement["improvement_score"] = score
            improvement["improved"] = score > 0
            
            improvements.append(improvement)
        
        return improvements
    
    def _calculate_effectiveness(
        self,
        action: str,
        success: bool,
        improvement: Optional[dict]
    ) -> dict:
        """Calculate effectiveness of a single action."""
        if not success:
            return {
                "score": 0.1,
                "rating": "Failed - Action did not execute successfully"
            }
        
        if not improvement:
            return {
                "score": 0.5,
                "rating": "Unknown - Could not measure improvement"
            }
        
        score = improvement.get("improvement_score", 0) / 100
        score = min(1.0, max(0, score))
        
        # Adjust based on action type expectations
        action_weights = {
            "optimize_routing": {"latency_change": -1, "expected_improvement": 20},
            "reduce_traffic": {"latency_change": -1, "packet_loss_change": -1, "expected_improvement": 15},
            "load_balance": {"cpu_change": -1, "expected_improvement": 15},
            "clear_cache": {"memory_change": -1, "expected_improvement": 10},
            "request_bandwidth": {"bandwidth_change": 1, "expected_improvement": 15},
            "restart_service": {"cpu_change": -1, "memory_change": -1, "expected_improvement": 20}
        }
        
        weights = action_weights.get(action, {})
        if weights:
            # Check if expected metrics improved
            for metric, direction in weights.items():
                if metric in improvement and metric != "expected_improvement":
                    change = improvement[metric]
                    if (direction < 0 and change < 0) or (direction > 0 and change > 0):
                        score += 0.1
        
        score = min(1.0, score)
        
        if score >= 0.8:
            rating = "Highly Effective - Significant improvement observed"
        elif score >= 0.6:
            rating = "Effective - Noticeable improvement"
        elif score >= 0.4:
            rating = "Partially Effective - Minor improvement"
        elif score >= 0.2:
            rating = "Limited Effect - Minimal improvement"
        else:
            rating = "Ineffective - No improvement observed"
        
        return {"score": score, "rating": rating}
    
    def _get_health_from_metrics(self, metrics: dict) -> float:
        """Calculate health score from metrics dict."""
        nodes = metrics.get("nodes", [])
        if not nodes:
            return 100.0
        
        scores = []
        for node in nodes:
            score = 100.0
            latency = node.get("latency", 0)
            if latency > 50:
                score -= min(25, (latency - 50) * 0.25)
            
            score -= node.get("packet_loss", 0) * 4
            
            bandwidth = node.get("bandwidth", 0)
            if bandwidth < 500:
                score -= min(15, (500 - bandwidth) * 0.03)
            
            cpu = node.get("cpu_usage", 0)
            if cpu > 70:
                score -= min(20, (cpu - 70) * 0.67)
            
            memory = node.get("memory_usage", 0)
            if memory > 70:
                score -= min(15, (memory - 70) * 0.5)
            
            scores.append(max(0, score))
        
        return sum(scores) / len(scores)
    
    def _generate_summary(
        self,
        action_feedback: list[dict],
        health_improvement: float
    ) -> str:
        """Generate a human-readable summary of feedback."""
        if not action_feedback:
            return "No actions were taken."
        
        successful = sum(1 for fb in action_feedback if fb["effectiveness_score"] > 0.5)
        total = len(action_feedback)
        
        if health_improvement > 5:
            health_note = f"Network health improved by {health_improvement:.1f} points."
        elif health_improvement > 0:
            health_note = f"Minor health improvement of {health_improvement:.1f} points."
        elif health_improvement > -5:
            health_note = "Network health remained stable."
        else:
            health_note = f"Warning: Health decreased by {abs(health_improvement):.1f} points."
        
        return f"{successful}/{total} actions were effective. {health_note}"
    
    def _record_feedback(self, feedback: dict):
        """Record feedback for future reference."""
        self.feedback_history.append(feedback)
        
        # Keep only last N entries based on config
        window = self.config.history_window
        self.feedback_history = self.feedback_history[-window:]
        
        # Log performance metrics
        self.decision_logger.log_performance({
            "improvement_score": feedback.get("improvement_score", 0),
            "average_effectiveness": feedback.get("average_effectiveness", 0),
            "success": feedback.get("overall_success", False)
        })
        
        # Update trends
        self._update_trends(feedback)
    
    def _update_trends(self, feedback: dict):
        """Update performance trends."""
        self.performance_trends.append({
            "timestamp": datetime.now().isoformat(),
            "improvement": feedback.get("improvement_score", 0),
            "effectiveness": feedback.get("average_effectiveness", 0)
        })
        
        # Keep only last 50 trend points
        self.performance_trends = self.performance_trends[-50:]
    
    def get_feedback_context(self) -> list[dict]:
        """Get feedback context for decision making."""
        # Return simplified feedback for LLM context
        return [
            {
                "success": fb.get("overall_success"),
                "improvement": fb.get("improvement_score", 0),
                "details": fb.get("details", ""),
                "actions": [
                    {
                        "action": af.get("action"),
                        "effective": af.get("effectiveness_score", 0) > 0.5
                    }
                    for af in fb.get("action_feedback", [])
                ]
            }
            for fb in self.feedback_history[-10:]
        ]
    
    def get_performance_trends(self) -> dict:
        """Get performance trend analysis."""
        if len(self.performance_trends) < 2:
            return {"message": "Insufficient data for trend analysis"}
        
        recent = self.performance_trends[-10:]
        
        avg_improvement = sum(t["improvement"] for t in recent) / len(recent)
        avg_effectiveness = sum(t["effectiveness"] for t in recent) / len(recent)
        
        # Calculate trend direction
        if len(recent) >= 5:
            first_half = recent[:len(recent)//2]
            second_half = recent[len(recent)//2:]
            
            first_avg = sum(t["improvement"] for t in first_half) / len(first_half)
            second_avg = sum(t["improvement"] for t in second_half) / len(second_half)
            
            if second_avg > first_avg + 1:
                trend = "improving"
            elif second_avg < first_avg - 1:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient data"
        
        return {
            "average_improvement": avg_improvement,
            "average_effectiveness": avg_effectiveness,
            "trend": trend,
            "data_points": len(self.performance_trends),
            "recent_entries": len(recent)
        }
