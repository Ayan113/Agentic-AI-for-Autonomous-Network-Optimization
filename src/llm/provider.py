"""
LLM provider abstraction for network optimization decisions.
"""

import json
import os
from abc import ABC, abstractmethod
from typing import Optional

from ..utils.config import get_config


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """Generate a response from the LLM."""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI API provider."""
    
    def __init__(self):
        from openai import AsyncOpenAI
        
        self.config = get_config().llm
        api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        self.client = AsyncOpenAI(api_key=api_key)
    
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """Generate a response using OpenAI."""
        response = await self.client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature or self.config.temperature,
            max_tokens=max_tokens or self.config.max_tokens
        )
        
        return response.choices[0].message.content


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing without API access."""
    
    def __init__(self):
        self.config = get_config().llm
    
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """Generate a mock response based on the input."""
        
        # Parse the user prompt to understand what's being analyzed
        prompt_lower = user_prompt.lower()
        
        # Detect if there are anomalies mentioned
        has_anomalies = any(word in prompt_lower for word in [
            "anomaly", "anomalies", "high latency", "packet loss",
            "high cpu", "high memory", "low bandwidth", "critical"
        ])
        
        # Extract node IDs if mentioned
        import re
        node_pattern = re.findall(r'node_\d+', prompt_lower)
        affected_nodes = list(set(node_pattern))[:3] if node_pattern else ["node_0"]
        
        if has_anomalies:
            # Generate action recommendations based on detected issues
            actions = []
            
            if "latency" in prompt_lower:
                actions.append({
                    "action": "optimize_routing",
                    "target": affected_nodes[0] if affected_nodes else "node_0",
                    "priority": "high",
                    "params": {"optimize_path": True},
                    "expected_improvement": "Reduce latency by 20-40%"
                })
            
            if "packet" in prompt_lower or "loss" in prompt_lower:
                actions.append({
                    "action": "reduce_traffic",
                    "target": affected_nodes[0] if affected_nodes else "node_0",
                    "priority": "critical",
                    "params": {"throttle_percent": 25},
                    "expected_improvement": "Reduce packet loss by 50%"
                })
            
            if "cpu" in prompt_lower:
                actions.append({
                    "action": "load_balance",
                    "target": affected_nodes[0] if affected_nodes else "node_0",
                    "priority": "high",
                    "params": {"redistribute": True},
                    "expected_improvement": "Reduce CPU load by 30%"
                })
            
            if "memory" in prompt_lower:
                actions.append({
                    "action": "clear_cache",
                    "target": affected_nodes[0] if affected_nodes else "node_0",
                    "priority": "medium",
                    "params": {"aggressive": True},
                    "expected_improvement": "Free 20-30% memory"
                })
            
            if "bandwidth" in prompt_lower:
                actions.append({
                    "action": "request_bandwidth",
                    "target": affected_nodes[0] if affected_nodes else "node_0",
                    "priority": "medium",
                    "params": {"increase_percent": 50},
                    "expected_improvement": "Increase available bandwidth by 50%"
                })
            
            # If no specific issues detected but anomalies mentioned
            if not actions:
                actions.append({
                    "action": "optimize_routing",
                    "target": affected_nodes[0] if affected_nodes else "node_0",
                    "priority": "medium",
                    "params": {"optimize_path": True},
                    "expected_improvement": "General network optimization"
                })
            
            response = {
                "action_required": True,
                "reasoning": f"Analysis detected network anomalies affecting {len(affected_nodes)} node(s). "
                            f"The issues indicate potential congestion or resource constraints. "
                            f"Recommended actions prioritize immediate stability improvements.",
                "recommended_actions": actions[:3],  # Limit to 3 actions
                "confidence": 0.85,
                "risk_assessment": "Medium - Actions are low-risk and reversible",
                "expected_outcome": "Network health improvement of 15-30%"
            }
        else:
            # No issues detected
            response = {
                "action_required": False,
                "reasoning": "Network metrics are within acceptable ranges. No immediate action required. "
                            "Continue monitoring for any emerging patterns.",
                "recommended_actions": [],
                "confidence": 0.95,
                "risk_assessment": "Low - Network is operating normally",
                "expected_outcome": "Maintain current stability"
            }
        
        return f"```json\n{json.dumps(response, indent=2)}\n```"


def get_llm_provider() -> LLMProvider:
    """Get the configured LLM provider."""
    config = get_config().llm
    
    if config.provider == "openai":
        try:
            return OpenAIProvider()
        except (ImportError, ValueError) as e:
            print(f"Warning: Could not initialize OpenAI provider: {e}")
            print("Falling back to mock provider")
            return MockLLMProvider()
    else:
        return MockLLMProvider()
