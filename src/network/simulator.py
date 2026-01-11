"""
Network metrics simulator for testing and demonstration.
"""

import random
from datetime import datetime
from typing import Optional

from .metrics import NetworkMetrics, NodeMetrics
from ..utils.config import get_config


class NetworkEvent:
    """Represents a network event/scenario."""
    
    def __init__(self, name: str, probability: float, effects: dict):
        self.name = name
        self.probability = probability
        self.effects = effects
    
    def apply(self, metrics: NodeMetrics) -> NodeMetrics:
        """Apply event effects to node metrics."""
        data = metrics.model_dump()
        
        for key, modifier in self.effects.items():
            if key in data and isinstance(modifier, (int, float)):
                if isinstance(modifier, float) and -1 < modifier < 1:
                    # Treat as percentage change
                    data[key] *= (1 + modifier)
                else:
                    # Treat as absolute change
                    data[key] += modifier
        
        return NodeMetrics(**data)


# Predefined network events
NETWORK_EVENTS = [
    NetworkEvent(
        name="traffic_spike",
        probability=0.15,
        effects={
            "latency": 50,
            "bandwidth": -200,
            "cpu_usage": 20,
            "connections": 50
        }
    ),
    NetworkEvent(
        name="packet_storm",
        probability=0.08,
        effects={
            "packet_loss": 5,
            "latency": 30,
            "bandwidth": -100
        }
    ),
    NetworkEvent(
        name="memory_leak",
        probability=0.05,
        effects={
            "memory_usage": 25,
            "cpu_usage": 10
        }
    ),
    NetworkEvent(
        name="ddos_attempt",
        probability=0.03,
        effects={
            "latency": 100,
            "packet_loss": 10,
            "connections": 200,
            "cpu_usage": 40
        }
    ),
    NetworkEvent(
        name="link_degradation",
        probability=0.10,
        effects={
            "bandwidth": -300,
            "latency": 20
        }
    ),
    NetworkEvent(
        name="cpu_intensive_task",
        probability=0.12,
        effects={
            "cpu_usage": 35,
            "memory_usage": 15
        }
    ),
]


class NetworkSimulator:
    """Simulates network metrics with realistic patterns and events."""
    
    def __init__(self):
        self.config = get_config().network.simulation
        self.nodes: list[str] = [f"node_{i}" for i in range(self.config.nodes)]
        self.base_state = self._initialize_base_state()
        self.active_events: dict[str, list[NetworkEvent]] = {}
        self.event_history: list[dict] = []
    
    def _initialize_base_state(self) -> dict[str, NodeMetrics]:
        """Initialize base metrics for all nodes."""
        base_state = {}
        
        for node_id in self.nodes:
            base_state[node_id] = NodeMetrics(
                node_id=node_id,
                latency=self.config.base_latency + random.uniform(-5, 5),
                bandwidth=self.config.base_bandwidth + random.uniform(-100, 100),
                packet_loss=self.config.base_packet_loss + random.uniform(0, 0.5),
                cpu_usage=random.uniform(20, 50),
                memory_usage=random.uniform(30, 60),
                connections=random.randint(10, 100)
            )
        
        return base_state
    
    def generate_metrics(self) -> NetworkMetrics:
        """Generate current network metrics with potential events."""
        nodes = []
        
        for node_id in self.nodes:
            # Start with base state + some noise
            base = self.base_state[node_id]
            metrics = NodeMetrics(
                node_id=node_id,
                latency=max(1, base.latency + random.gauss(0, 5)),
                bandwidth=max(10, base.bandwidth + random.gauss(0, 50)),
                packet_loss=max(0, base.packet_loss + random.gauss(0, 0.5)),
                cpu_usage=max(5, min(100, base.cpu_usage + random.gauss(0, 5))),
                memory_usage=max(10, min(100, base.memory_usage + random.gauss(0, 3))),
                connections=max(0, base.connections + random.randint(-10, 10))
            )
            
            # Apply random events based on probability
            if random.random() < self.config.event_probability:
                event = self._trigger_random_event(node_id)
                if event:
                    metrics = event.apply(metrics)
                    self._record_event(node_id, event)
            
            # Apply any active events
            if node_id in self.active_events:
                for event in self.active_events[node_id]:
                    metrics = event.apply(metrics)
            
            # Clamp values to valid ranges
            metrics = self._clamp_metrics(metrics)
            nodes.append(metrics)
        
        return NetworkMetrics(nodes=nodes)
    
    def _trigger_random_event(self, node_id: str) -> Optional[NetworkEvent]:
        """Potentially trigger a random network event."""
        for event in NETWORK_EVENTS:
            if random.random() < event.probability:
                return event
        return None
    
    def _record_event(self, node_id: str, event: NetworkEvent):
        """Record an event in history."""
        self.event_history.append({
            "timestamp": datetime.now().isoformat(),
            "node_id": node_id,
            "event": event.name,
            "effects": event.effects
        })
        
        # Keep only last 100 events
        self.event_history = self.event_history[-100:]
    
    def _clamp_metrics(self, metrics: NodeMetrics) -> NodeMetrics:
        """Clamp metrics to valid ranges."""
        return NodeMetrics(
            node_id=metrics.node_id,
            latency=max(1, min(500, metrics.latency)),
            bandwidth=max(10, min(2000, metrics.bandwidth)),
            packet_loss=max(0, min(50, metrics.packet_loss)),
            cpu_usage=max(5, min(100, metrics.cpu_usage)),
            memory_usage=max(10, min(100, metrics.memory_usage)),
            connections=max(0, min(1000, metrics.connections))
        )
    
    def trigger_scenario(self, scenario: str) -> dict:
        """Trigger a specific network scenario."""
        scenarios = {
            "high_traffic": self._scenario_high_traffic,
            "outage": self._scenario_outage,
            "gradual_degradation": self._scenario_gradual_degradation,
            "recovery": self._scenario_recovery,
            "normal": self._scenario_normal
        }
        
        if scenario not in scenarios:
            return {"error": f"Unknown scenario: {scenario}"}
        
        return scenarios[scenario]()
    
    def _scenario_high_traffic(self) -> dict:
        """Simulate high traffic across the network."""
        affected_nodes = random.sample(self.nodes, k=min(5, len(self.nodes)))
        
        event = NetworkEvent(
            name="high_traffic_scenario",
            probability=1.0,
            effects={
                "latency": 80,
                "bandwidth": -400,
                "cpu_usage": 30,
                "connections": 100
            }
        )
        
        for node_id in affected_nodes:
            if node_id not in self.active_events:
                self.active_events[node_id] = []
            self.active_events[node_id].append(event)
        
        return {
            "scenario": "high_traffic",
            "affected_nodes": affected_nodes,
            "message": f"High traffic scenario triggered on {len(affected_nodes)} nodes"
        }
    
    def _scenario_outage(self) -> dict:
        """Simulate a node outage."""
        affected_node = random.choice(self.nodes)
        
        event = NetworkEvent(
            name="outage_scenario",
            probability=1.0,
            effects={
                "latency": 400,
                "packet_loss": 40,
                "bandwidth": -800
            }
        )
        
        self.active_events[affected_node] = [event]
        
        return {
            "scenario": "outage",
            "affected_nodes": [affected_node],
            "message": f"Outage scenario triggered on {affected_node}"
        }
    
    def _scenario_gradual_degradation(self) -> dict:
        """Simulate gradual network degradation."""
        for node_id in self.nodes:
            base = self.base_state[node_id]
            self.base_state[node_id] = NodeMetrics(
                node_id=node_id,
                latency=base.latency * 1.2,
                bandwidth=base.bandwidth * 0.9,
                packet_loss=base.packet_loss + 1,
                cpu_usage=base.cpu_usage + 5,
                memory_usage=base.memory_usage + 3,
                connections=base.connections
            )
        
        return {
            "scenario": "gradual_degradation",
            "affected_nodes": self.nodes,
            "message": "Gradual degradation applied to all nodes"
        }
    
    def _scenario_recovery(self) -> dict:
        """Clear all active events and restore base state."""
        self.active_events.clear()
        self.base_state = self._initialize_base_state()
        
        return {
            "scenario": "recovery",
            "affected_nodes": self.nodes,
            "message": "Network recovered to normal state"
        }
    
    def _scenario_normal(self) -> dict:
        """Reset to normal operation."""
        self.active_events.clear()
        
        return {
            "scenario": "normal",
            "affected_nodes": [],
            "message": "Network operating normally"
        }
    
    def apply_action_effect(self, node_id: str, action: str, success: bool) -> dict:
        """Apply the effects of an action on the network state."""
        if node_id not in self.base_state:
            return {"error": f"Unknown node: {node_id}"}
        
        if not success:
            return {"effect": "none", "reason": "Action failed"}
        
        base = self.base_state[node_id]
        
        # Apply positive effects based on action type
        action_effects = {
            "optimize_routing": {
                "latency": -20,
                "packet_loss": -0.5
            },
            "reduce_traffic": {
                "bandwidth": 100,
                "latency": -10,
                "cpu_usage": -10
            },
            "load_balance": {
                "cpu_usage": -15,
                "latency": -5
            },
            "clear_cache": {
                "memory_usage": -20,
                "cpu_usage": -5
            },
            "request_bandwidth": {
                "bandwidth": 200
            },
            "restart_service": {
                "cpu_usage": -30,
                "memory_usage": -25,
                "latency": -15
            }
        }
        
        effects = action_effects.get(action, {})
        
        # Apply effects to base state
        new_base = base.model_dump()
        for key, change in effects.items():
            if key in new_base:
                new_base[key] = max(0, new_base[key] + change)
        
        self.base_state[node_id] = NodeMetrics(**new_base)
        
        # Clear active events for this node
        if node_id in self.active_events:
            del self.active_events[node_id]
        
        return {
            "node_id": node_id,
            "action": action,
            "effects_applied": effects
        }
    
    def get_event_history(self) -> list[dict]:
        """Get recent event history."""
        return self.event_history
