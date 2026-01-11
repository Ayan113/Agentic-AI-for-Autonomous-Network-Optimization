"""
Monitor Agent - Collects and analyzes network metrics.
"""

import asyncio
import random
from datetime import datetime
from typing import Optional

from .base_agent import AgentMessage, BaseAgent
from ..network.metrics import NetworkMetrics, NodeMetrics
from ..network.simulator import NetworkSimulator
from ..utils.config import get_config
from ..utils.logging import log_metrics_table


class MonitorAgent(BaseAgent):
    """
    Agent responsible for monitoring network metrics.
    
    Responsibilities:
    - Collect metrics from network nodes (simulated or real)
    - Detect anomalies and threshold breaches
    - Report metrics to the coordinator
    """
    
    def __init__(self):
        super().__init__("monitor")
        self.config = get_config().agents.monitor
        self.network_config = get_config().network.simulation
        self.simulator = NetworkSimulator() if self.network_config.enabled else None
        self.last_metrics: Optional[NetworkMetrics] = None
        self.anomaly_history: list[dict] = []
    
    async def process(self, message: Optional[AgentMessage] = None) -> Optional[AgentMessage]:
        """Process incoming messages and collect metrics."""
        
        # Handle specific message types
        if message:
            if message.message_type == "collect_metrics":
                return await self._collect_and_report()
            elif message.message_type == "get_status":
                return await self.send_message(
                    message.sender,
                    "status_response",
                    self.get_status()
                )
        
        # Default: collect metrics
        return await self._collect_and_report()
    
    async def _collect_and_report(self) -> AgentMessage:
        """Collect metrics and report to coordinator."""
        self.logger.info("Collecting network metrics...")
        
        # Get metrics from simulator or external source
        if self.simulator:
            metrics = self.simulator.generate_metrics()
        else:
            metrics = await self._fetch_external_metrics()
        
        self.last_metrics = metrics
        
        # Detect anomalies
        anomalies = self._detect_anomalies(metrics)
        
        # Log metrics summary
        summary = metrics.get_summary()
        log_metrics_table(summary, "Network Metrics Summary")
        
        if anomalies:
            self.logger.warning(f"Detected {len(anomalies)} anomalies!")
            for anomaly in anomalies:
                self.logger.warning(f"  - {anomaly['type']}: {anomaly['description']}")
        else:
            self.logger.success("All metrics within normal range")
        
        # Build response message for coordinator
        return await self.send_message(
            "coordinator",
            "metrics_report",
            {
                "metrics": metrics.model_dump(),
                "anomalies": anomalies,
                "timestamp": datetime.now().isoformat(),
                "health_score": self._calculate_health_score(metrics)
            }
        )
    
    def _detect_anomalies(self, metrics: NetworkMetrics) -> list[dict]:
        """Detect anomalies in the network metrics."""
        anomalies = []
        threshold = self.config.anomaly_threshold
        
        for node in metrics.nodes:
            # High latency
            if node.latency > 100:
                anomalies.append({
                    "type": "high_latency",
                    "node": node.node_id,
                    "value": node.latency,
                    "threshold": 100,
                    "severity": "warning" if node.latency < 200 else "critical",
                    "description": f"Node {node.node_id} latency is {node.latency:.1f}ms"
                })
            
            # High packet loss
            if node.packet_loss > 5:
                anomalies.append({
                    "type": "high_packet_loss",
                    "node": node.node_id,
                    "value": node.packet_loss,
                    "threshold": 5,
                    "severity": "critical",
                    "description": f"Node {node.node_id} packet loss is {node.packet_loss:.2f}%"
                })
            
            # Low bandwidth
            if node.bandwidth < 100:
                anomalies.append({
                    "type": "low_bandwidth",
                    "node": node.node_id,
                    "value": node.bandwidth,
                    "threshold": 100,
                    "severity": "warning",
                    "description": f"Node {node.node_id} bandwidth is {node.bandwidth:.0f}Mbps"
                })
            
            # High CPU usage
            if node.cpu_usage > 80:
                anomalies.append({
                    "type": "high_cpu",
                    "node": node.node_id,
                    "value": node.cpu_usage,
                    "threshold": 80,
                    "severity": "warning" if node.cpu_usage < 95 else "critical",
                    "description": f"Node {node.node_id} CPU at {node.cpu_usage:.1f}%"
                })
            
            # High memory usage
            if node.memory_usage > 85:
                anomalies.append({
                    "type": "high_memory",
                    "node": node.node_id,
                    "value": node.memory_usage,
                    "threshold": 85,
                    "severity": "warning" if node.memory_usage < 95 else "critical",
                    "description": f"Node {node.node_id} memory at {node.memory_usage:.1f}%"
                })
        
        # Store anomaly history
        if anomalies:
            self.anomaly_history.append({
                "timestamp": datetime.now().isoformat(),
                "count": len(anomalies),
                "anomalies": anomalies
            })
            # Keep only last 100 entries
            self.anomaly_history = self.anomaly_history[-100:]
        
        return anomalies
    
    def _calculate_health_score(self, metrics: NetworkMetrics) -> float:
        """Calculate overall network health score (0-100)."""
        scores = []
        
        for node in metrics.nodes:
            node_score = 100.0
            
            # Deduct for latency
            if node.latency > 50:
                node_score -= min(30, (node.latency - 50) * 0.3)
            
            # Deduct for packet loss
            node_score -= node.packet_loss * 5
            
            # Deduct for low bandwidth
            if node.bandwidth < 500:
                node_score -= min(20, (500 - node.bandwidth) * 0.04)
            
            # Deduct for high CPU
            if node.cpu_usage > 70:
                node_score -= min(20, (node.cpu_usage - 70) * 0.7)
            
            # Deduct for high memory
            if node.memory_usage > 70:
                node_score -= min(15, (node.memory_usage - 70) * 0.5)
            
            scores.append(max(0, node_score))
        
        return sum(scores) / len(scores) if scores else 100.0
    
    async def _fetch_external_metrics(self) -> NetworkMetrics:
        """Fetch metrics from external sources (placeholder)."""
        # This would be replaced with real metric ingestion
        # e.g., SNMP, Prometheus, network APIs
        self.logger.warning("External metrics not configured, using mock data")
        return NetworkMetrics(
            nodes=[
                NodeMetrics(
                    node_id=f"node_{i}",
                    latency=random.uniform(10, 50),
                    bandwidth=random.uniform(500, 1000),
                    packet_loss=random.uniform(0, 2),
                    cpu_usage=random.uniform(20, 60),
                    memory_usage=random.uniform(30, 70),
                    connections=random.randint(10, 100)
                )
                for i in range(5)
            ]
        )
    
    def get_anomaly_history(self) -> list[dict]:
        """Get the history of detected anomalies."""
        return self.anomaly_history
