"""
API routes for the Agentic AI Network Optimizer.
"""

import asyncio
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from ..network.simulator import NetworkSimulator
from ..utils.logging import DecisionLogger
from ..utils.config import get_config


router = APIRouter()


def get_coordinator():
    """Get the coordinator instance - lazy import to avoid circular dependency."""
    from .main import coordinator
    if coordinator is None:
        from ..agents.coordinator import Coordinator
        return Coordinator()
    return coordinator


# Request/Response models
class ScenarioRequest(BaseModel):
    scenario: str


class CycleRequest(BaseModel):
    count: int = 1


# Routes
@router.get("/info")
async def api_info():
    """API information endpoint."""
    return {
        "name": "Agentic AI Network Optimizer",
        "version": get_config().system.version,
        "status": "running",
        "endpoints": {
            "/status": "System status and agent health",
            "/metrics": "Current network metrics",
            "/decisions": "Decision history",
            "/performance": "Performance metrics",
            "/cycle": "Run optimization cycle",
            "/simulate": "Trigger network scenario"
        }
    }


@router.get("/status")
async def get_status():
    """Get the current status of all agents."""
    coordinator = get_coordinator()
    return coordinator.get_system_status()


@router.get("/metrics")
async def get_metrics():
    """Get current network metrics."""
    coordinator = get_coordinator()
    
    if coordinator.monitor.last_metrics:
        return {
            "metrics": coordinator.monitor.last_metrics.model_dump(),
            "summary": coordinator.monitor.last_metrics.get_summary(),
            "health": coordinator.monitor.last_metrics.get_overall_health()
        }
    
    # If no metrics yet, generate fresh ones
    metrics_message = await coordinator.monitor.process()
    if metrics_message:
        return metrics_message.payload
    
    return {"message": "No metrics available"}


@router.get("/decisions")
async def get_decisions(limit: int = 20):
    """Get recent decision history."""
    logger = DecisionLogger(get_config().system.data_dir)
    decisions = logger.get_decisions(limit)
    
    return {
        "count": len(decisions),
        "decisions": decisions
    }


@router.get("/performance")
async def get_performance():
    """Get performance metrics and trends."""
    coordinator = get_coordinator()
    logger = DecisionLogger(get_config().system.data_dir)
    
    return {
        "summary": coordinator.get_performance_summary(),
        "cycle_history": coordinator.get_cycle_history(10),
        "feedback_trends": coordinator.feedback.get_performance_trends(),
        "recent_performance": logger.get_performance(20)
    }


@router.get("/anomalies")
async def get_anomalies():
    """Get detected anomalies history."""
    coordinator = get_coordinator()
    return {
        "history": coordinator.monitor.get_anomaly_history()
    }


@router.get("/actions")
async def get_actions():
    """Get action history and available actions."""
    coordinator = get_coordinator()
    
    return {
        "available_actions": coordinator.action.executor.get_available_actions(),
        "execution_history": coordinator.action.get_action_history(),
        "success_rate": coordinator.action.get_success_rate()
    }


@router.post("/cycle")
async def run_cycle(background_tasks: BackgroundTasks, request: Optional[CycleRequest] = None):
    """Run one or more optimization cycles."""
    coordinator = get_coordinator()
    count = request.count if request else 1
    
    if count > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 cycles allowed per request")
    
    results = []
    for i in range(count):
        result = await coordinator.run_cycle()
        results.append(result)
    
    return {
        "cycles_run": count,
        "results": results
    }


@router.post("/simulate")
async def simulate_scenario(request: ScenarioRequest):
    """Trigger a network simulation scenario."""
    simulator = NetworkSimulator()
    
    valid_scenarios = ["high_traffic", "outage", "gradual_degradation", "recovery", "normal"]
    
    if request.scenario not in valid_scenarios:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid scenario. Valid options: {valid_scenarios}"
        )
    
    result = simulator.trigger_scenario(request.scenario)
    
    # Also trigger this on the coordinator's monitor simulator
    coordinator = get_coordinator()
    if coordinator.monitor.simulator:
        coordinator.monitor.simulator.trigger_scenario(request.scenario)
    
    return {
        "scenario": request.scenario,
        "result": result
    }


@router.get("/events")
async def get_events():
    """Get network event history."""
    coordinator = get_coordinator()
    
    if coordinator.monitor.simulator:
        return {
            "events": coordinator.monitor.simulator.get_event_history()
        }
    
    return {"events": [], "message": "Simulator not enabled"}


@router.post("/start")
async def start_monitoring(background_tasks: BackgroundTasks, interval: int = 10):
    """Start continuous monitoring in the background."""
    coordinator = get_coordinator()
    
    if coordinator._running:
        return {"status": "already running"}
    
    async def run_continuous():
        await coordinator.run_continuous(interval)
    
    background_tasks.add_task(run_continuous)
    
    return {
        "status": "started",
        "interval": interval,
        "message": "Continuous monitoring started in background"
    }


@router.post("/stop")
async def stop_monitoring():
    """Stop continuous monitoring."""
    coordinator = get_coordinator()
    await coordinator.stop()
    
    return {
        "status": "stopped",
        "message": "Monitoring stopped"
    }


@router.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy"}
