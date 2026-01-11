"""
Learning module for performance improvement tracking.
"""

from datetime import datetime
from typing import Optional

from ..utils.config import get_config
from ..utils.logging import DecisionLogger


class PerformanceTracker:
    """
    Tracks and analyzes system performance over time.
    
    Provides insights for:
    - Action effectiveness by type
    - Network health trends
    - Decision quality metrics
    """
    
    def __init__(self):
        self.config = get_config().feedback
        self.decision_logger = DecisionLogger(get_config().system.data_dir)
        self.action_stats: dict[str, dict] = {}
        self.health_history: list[dict] = []
    
    def record_action_result(
        self,
        action: str,
        target: str,
        success: bool,
        effectiveness: float,
        improvement: float
    ):
        """Record the result of an action for learning."""
        if action not in self.action_stats:
            self.action_stats[action] = {
                "total_attempts": 0,
                "successful": 0,
                "total_effectiveness": 0,
                "total_improvement": 0,
                "best_improvement": 0,
                "worst_improvement": 0,
                "targets": {}
            }
        
        stats = self.action_stats[action]
        stats["total_attempts"] += 1
        
        if success:
            stats["successful"] += 1
        
        stats["total_effectiveness"] += effectiveness
        stats["total_improvement"] += improvement
        
        if improvement > stats["best_improvement"]:
            stats["best_improvement"] = improvement
        if improvement < stats["worst_improvement"]:
            stats["worst_improvement"] = improvement
        
        # Track per-target performance
        if target not in stats["targets"]:
            stats["targets"][target] = {
                "attempts": 0,
                "successful": 0,
                "avg_improvement": 0
            }
        
        target_stats = stats["targets"][target]
        target_stats["attempts"] += 1
        if success:
            target_stats["successful"] += 1
        
        # Update rolling average
        n = target_stats["attempts"]
        old_avg = target_stats["avg_improvement"]
        target_stats["avg_improvement"] = old_avg + (improvement - old_avg) / n
    
    def record_health_snapshot(self, health_score: float, anomaly_count: int):
        """Record a health snapshot for trend analysis."""
        self.health_history.append({
            "timestamp": datetime.now().isoformat(),
            "health_score": health_score,
            "anomaly_count": anomaly_count
        })
        
        # Keep only last 500 snapshots
        self.health_history = self.health_history[-500:]
    
    def get_action_recommendations(self, anomaly_type: str) -> list[dict]:
        """
        Get recommended actions for a specific anomaly type
        based on historical effectiveness.
        """
        # Map anomaly types to relevant actions
        anomaly_action_map = {
            "high_latency": ["optimize_routing", "reduce_traffic", "load_balance"],
            "high_packet_loss": ["reduce_traffic", "optimize_routing"],
            "high_cpu": ["load_balance", "restart_service", "scale_up"],
            "high_memory": ["clear_cache", "restart_service", "scale_up"],
            "low_bandwidth": ["request_bandwidth", "reduce_traffic"]
        }
        
        relevant_actions = anomaly_action_map.get(anomaly_type, [])
        recommendations = []
        
        for action in relevant_actions:
            stats = self.action_stats.get(action)
            if stats and stats["total_attempts"] > 0:
                success_rate = stats["successful"] / stats["total_attempts"]
                avg_effectiveness = stats["total_effectiveness"] / stats["total_attempts"]
                avg_improvement = stats["total_improvement"] / stats["total_attempts"]
                
                recommendations.append({
                    "action": action,
                    "historical_success_rate": success_rate,
                    "historical_effectiveness": avg_effectiveness,
                    "average_improvement": avg_improvement,
                    "confidence": min(1.0, stats["total_attempts"] / 10),  # More attempts = higher confidence
                    "recommended": success_rate > 0.5 and avg_improvement > 0
                })
            else:
                # No history, provide default recommendation
                recommendations.append({
                    "action": action,
                    "historical_success_rate": None,
                    "historical_effectiveness": None,
                    "average_improvement": None,
                    "confidence": 0,
                    "recommended": True  # Try it since we have no data
                })
        
        # Sort by effectiveness (actions with history first, then by effectiveness)
        recommendations.sort(
            key=lambda x: (
                x["recommended"],
                x["confidence"],
                x.get("historical_effectiveness") or 0
            ),
            reverse=True
        )
        
        return recommendations
    
    def get_action_statistics(self) -> dict:
        """Get comprehensive statistics for all actions."""
        result = {}
        
        for action, stats in self.action_stats.items():
            total = stats["total_attempts"]
            if total == 0:
                continue
            
            result[action] = {
                "total_attempts": total,
                "success_rate": stats["successful"] / total,
                "average_effectiveness": stats["total_effectiveness"] / total,
                "average_improvement": stats["total_improvement"] / total,
                "best_improvement": stats["best_improvement"],
                "worst_improvement": stats["worst_improvement"],
                "target_count": len(stats["targets"])
            }
        
        return result
    
    def get_health_trends(self, window: int = 50) -> dict:
        """Analyze health trends over recent history."""
        if len(self.health_history) < 2:
            return {"status": "insufficient data"}
        
        recent = self.health_history[-window:]
        
        # Calculate statistics
        health_scores = [h["health_score"] for h in recent]
        anomaly_counts = [h["anomaly_count"] for h in recent]
        
        avg_health = sum(health_scores) / len(health_scores)
        min_health = min(health_scores)
        max_health = max(health_scores)
        avg_anomalies = sum(anomaly_counts) / len(anomaly_counts)
        
        # Calculate trend
        if len(recent) >= 10:
            first_half = health_scores[:len(health_scores)//2]
            second_half = health_scores[len(health_scores)//2:]
            
            first_avg = sum(first_half) / len(first_half)
            second_avg = sum(second_half) / len(second_half)
            
            trend_delta = second_avg - first_avg
            
            if trend_delta > 5:
                trend = "improving"
            elif trend_delta < -5:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient data"
            trend_delta = 0
        
        return {
            "average_health": avg_health,
            "min_health": min_health,
            "max_health": max_health,
            "average_anomalies": avg_anomalies,
            "trend": trend,
            "trend_delta": trend_delta,
            "data_points": len(recent)
        }
    
    def get_learning_summary(self) -> dict:
        """Get a summary of what the system has learned."""
        action_stats = self.get_action_statistics()
        health_trends = self.get_health_trends()
        
        # Identify most and least effective actions
        if action_stats:
            sorted_actions = sorted(
                action_stats.items(),
                key=lambda x: x[1]["average_effectiveness"],
                reverse=True
            )
            
            most_effective = sorted_actions[:3] if len(sorted_actions) >= 3 else sorted_actions
            least_effective = sorted_actions[-3:] if len(sorted_actions) >= 3 else []
        else:
            most_effective = []
            least_effective = []
        
        return {
            "total_actions_tracked": len(action_stats),
            "total_action_executions": sum(s["total_attempts"] for s in action_stats.values()),
            "most_effective_actions": [
                {"action": a, "effectiveness": s["average_effectiveness"]}
                for a, s in most_effective
            ],
            "least_effective_actions": [
                {"action": a, "effectiveness": s["average_effectiveness"]}
                for a, s in least_effective
            ],
            "health_trend": health_trends.get("trend", "unknown"),
            "average_health": health_trends.get("average_health", 0)
        }
