"""
Network metrics models.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class NodeMetrics(BaseModel):
    """Metrics for a single network node."""
    node_id: str
    latency: float = Field(description="Latency in milliseconds")
    bandwidth: float = Field(description="Available bandwidth in Mbps")
    packet_loss: float = Field(description="Packet loss percentage")
    cpu_usage: float = Field(description="CPU usage percentage")
    memory_usage: float = Field(description="Memory usage percentage")
    connections: int = Field(description="Number of active connections")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    def is_healthy(self) -> bool:
        """Check if the node is in healthy state."""
        return (
            self.latency < 100 and
            self.bandwidth > 100 and
            self.packet_loss < 5 and
            self.cpu_usage < 80 and
            self.memory_usage < 85
        )
    
    def get_health_score(self) -> float:
        """Calculate health score for this node (0-100)."""
        score = 100.0
        
        # Latency penalty
        if self.latency > 50:
            score -= min(25, (self.latency - 50) * 0.25)
        
        # Packet loss penalty
        score -= self.packet_loss * 4
        
        # Bandwidth penalty
        if self.bandwidth < 500:
            score -= min(15, (500 - self.bandwidth) * 0.03)
        
        # CPU penalty
        if self.cpu_usage > 70:
            score -= min(20, (self.cpu_usage - 70) * 0.67)
        
        # Memory penalty
        if self.memory_usage > 70:
            score -= min(15, (self.memory_usage - 70) * 0.5)
        
        return max(0, score)


class NetworkMetrics(BaseModel):
    """Aggregated metrics for the entire network."""
    nodes: list[NodeMetrics] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)
    
    def get_summary(self) -> dict:
        """Get summary statistics across all nodes."""
        if not self.nodes:
            return {}
        
        latencies = [n.latency for n in self.nodes]
        bandwidths = [n.bandwidth for n in self.nodes]
        packet_losses = [n.packet_loss for n in self.nodes]
        cpu_usages = [n.cpu_usage for n in self.nodes]
        memory_usages = [n.memory_usage for n in self.nodes]
        
        return {
            "node_count": len(self.nodes),
            "avg_latency": sum(latencies) / len(latencies),
            "max_latency": max(latencies),
            "min_bandwidth": min(bandwidths),
            "avg_bandwidth": sum(bandwidths) / len(bandwidths),
            "avg_packet_loss": sum(packet_losses) / len(packet_losses),
            "max_packet_loss": max(packet_losses),
            "avg_cpu": sum(cpu_usages) / len(cpu_usages),
            "max_cpu": max(cpu_usages),
            "avg_memory": sum(memory_usages) / len(memory_usages),
            "max_memory": max(memory_usages),
            "healthy_nodes": sum(1 for n in self.nodes if n.is_healthy()),
            "unhealthy_nodes": sum(1 for n in self.nodes if not n.is_healthy())
        }
    
    def get_overall_health(self) -> float:
        """Calculate overall network health (0-100)."""
        if not self.nodes:
            return 100.0
        
        scores = [n.get_health_score() for n in self.nodes]
        return sum(scores) / len(scores)
    
    def get_critical_nodes(self) -> list[NodeMetrics]:
        """Get nodes with critical issues."""
        return [n for n in self.nodes if n.get_health_score() < 50]
    
    def get_warning_nodes(self) -> list[NodeMetrics]:
        """Get nodes with warnings."""
        return [n for n in self.nodes if 50 <= n.get_health_score() < 75]


class MetricsDelta(BaseModel):
    """Change in metrics between two points in time."""
    node_id: str
    latency_change: float
    bandwidth_change: float
    packet_loss_change: float
    cpu_change: float
    memory_change: float
    improved: bool = False
    
    @classmethod
    def calculate(cls, before: NodeMetrics, after: NodeMetrics) -> "MetricsDelta":
        """Calculate the delta between two metric snapshots."""
        latency_change = after.latency - before.latency
        bandwidth_change = after.bandwidth - before.bandwidth
        packet_loss_change = after.packet_loss - before.packet_loss
        cpu_change = after.cpu_usage - before.cpu_usage
        memory_change = after.memory_usage - before.memory_usage
        
        # Overall improvement if negative changes in latency/loss/cpu/memory
        # and positive change in bandwidth
        improved = (
            latency_change < 0 or
            packet_loss_change < 0 or
            bandwidth_change > 0 or
            cpu_change < 0 or
            memory_change < 0
        )
        
        return cls(
            node_id=after.node_id,
            latency_change=latency_change,
            bandwidth_change=bandwidth_change,
            packet_loss_change=packet_loss_change,
            cpu_change=cpu_change,
            memory_change=memory_change,
            improved=improved
        )
