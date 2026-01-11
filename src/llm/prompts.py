"""
Prompt templates for LLM-based network analysis and decision making.
"""

import json
from typing import Any


DECISION_SYSTEM_PROMPT = """You are an expert network operations AI assistant specializing in autonomous network monitoring and optimization. Your role is to analyze network metrics, identify issues, and recommend corrective actions.

## Your Capabilities
- Analyze network metrics (latency, bandwidth, packet loss, CPU, memory)
- Identify patterns and anomalies
- Recommend optimal corrective actions
- Learn from historical feedback to improve decisions

## Available Actions
1. **optimize_routing** - Optimize network routing paths to reduce latency
2. **reduce_traffic** - Throttle traffic to reduce congestion (params: throttle_percent)
3. **load_balance** - Redistribute load across nodes
4. **clear_cache** - Clear caches to free memory
5. **request_bandwidth** - Request additional bandwidth (params: increase_percent)
6. **restart_service** - Restart a problematic service
7. **alert** - Send alert to operations team
8. **scale_up** - Add more instances
9. **scale_down** - Remove excess instances

## Decision Guidelines
1. Prioritize stability over optimization
2. Prefer less invasive actions first
3. Consider cascading effects
4. Account for historical action effectiveness
5. Never take more than 3 actions per decision

## Response Format
Always respond with valid JSON in this structure:
```json
{
    "action_required": true/false,
    "reasoning": "Detailed explanation of your analysis",
    "recommended_actions": [
        {
            "action": "action_name",
            "target": "node_id",
            "priority": "critical/high/medium/low",
            "params": {},
            "expected_improvement": "Description of expected outcome"
        }
    ],
    "confidence": 0.0-1.0,
    "risk_assessment": "Description of risks",
    "expected_outcome": "Overall expected improvement"
}
```
"""


def format_decision_prompt(
    metrics: dict,
    anomalies: list[dict],
    health_score: float,
    feedback_history: list[dict] = None
) -> str:
    """Format the decision prompt with current metrics and context."""
    
    prompt_parts = [
        "## Current Network State",
        f"**Overall Health Score:** {health_score:.1f}/100",
        "",
        "### Metrics Summary"
    ]
    
    # Add metrics summary
    if metrics:
        nodes = metrics.get("nodes", [])
        if nodes:
            prompt_parts.append(f"**Node Count:** {len(nodes)}")
            
            # Calculate averages
            latencies = [n.get("latency", 0) for n in nodes]
            bandwidths = [n.get("bandwidth", 0) for n in nodes]
            packet_losses = [n.get("packet_loss", 0) for n in nodes]
            cpu_usages = [n.get("cpu_usage", 0) for n in nodes]
            memory_usages = [n.get("memory_usage", 0) for n in nodes]
            
            prompt_parts.extend([
                f"**Avg Latency:** {sum(latencies)/len(latencies):.1f}ms (max: {max(latencies):.1f}ms)",
                f"**Avg Bandwidth:** {sum(bandwidths)/len(bandwidths):.0f}Mbps (min: {min(bandwidths):.0f}Mbps)",
                f"**Avg Packet Loss:** {sum(packet_losses)/len(packet_losses):.2f}%",
                f"**Avg CPU:** {sum(cpu_usages)/len(cpu_usages):.1f}%",
                f"**Avg Memory:** {sum(memory_usages)/len(memory_usages):.1f}%",
            ])
    
    # Add anomalies
    if anomalies:
        prompt_parts.extend([
            "",
            "### Detected Anomalies",
            f"**Total:** {len(anomalies)} issues detected",
            ""
        ])
        
        for i, anomaly in enumerate(anomalies[:10], 1):  # Limit to 10
            severity = anomaly.get("severity", "unknown")
            severity_emoji = "🔴" if severity == "critical" else "⚠️"
            prompt_parts.append(
                f"{i}. {severity_emoji} **{anomaly.get('type', 'unknown')}** on `{anomaly.get('node', 'unknown')}`: "
                f"{anomaly.get('description', 'No description')}"
            )
    else:
        prompt_parts.extend([
            "",
            "### No Anomalies Detected",
            "All metrics are within normal ranges."
        ])
    
    # Add feedback history if available
    if feedback_history:
        prompt_parts.extend([
            "",
            "### Historical Feedback",
            "Recent action effectiveness:"
        ])
        
        for feedback in feedback_history[-5:]:
            success = "✅ Effective" if feedback.get("success") else "❌ Ineffective"
            prompt_parts.append(f"- {success}: {feedback.get('details', 'No details')}")
    
    # Add decision request
    prompt_parts.extend([
        "",
        "---",
        "",
        "## Decision Required",
        "Based on the current network state and historical feedback, analyze the situation and provide your recommendation.",
        "If action is required, specify the actions with targets and priorities.",
        "If no action is needed, explain why and confirm network stability."
    ])
    
    return "\n".join(prompt_parts)


def format_analysis_prompt(metrics: dict) -> str:
    """Format a prompt for general network analysis."""
    return f"""Analyze the following network metrics and provide insights:

{json.dumps(metrics, indent=2)}

Provide:
1. Overall network health assessment
2. Key observations
3. Potential concerns
4. Recommendations for proactive improvements
"""


def format_learning_prompt(
    action: str,
    pre_metrics: dict,
    post_metrics: dict,
    success: bool
) -> str:
    """Format a prompt for learning from action outcomes."""
    return f"""Analyze the effectiveness of a network optimization action:

## Action Taken
**Action:** {action}
**Outcome:** {"Successful" if success else "Failed"}

## Before Metrics
{json.dumps(pre_metrics, indent=2)}

## After Metrics  
{json.dumps(post_metrics, indent=2)}

Provide:
1. Assessment of action effectiveness
2. Metrics that improved
3. Metrics that worsened (if any)
4. Recommendations for future similar situations
"""
