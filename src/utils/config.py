"""
Configuration management for the Agentic AI Network Optimizer.
"""

import os
from pathlib import Path
from typing import Any, Optional
import yaml
from pydantic import BaseModel, Field


class MonitorAgentConfig(BaseModel):
    enabled: bool = True
    polling_interval: int = 5
    anomaly_threshold: float = 0.8


class DecisionAgentConfig(BaseModel):
    enabled: bool = True
    confidence_threshold: float = 0.7
    max_actions_per_cycle: int = 3


class ActionAgentConfig(BaseModel):
    enabled: bool = True
    dry_run: bool = False
    action_timeout: int = 30


class AgentsConfig(BaseModel):
    monitor: MonitorAgentConfig = Field(default_factory=MonitorAgentConfig)
    decision: DecisionAgentConfig = Field(default_factory=DecisionAgentConfig)
    action: ActionAgentConfig = Field(default_factory=ActionAgentConfig)


class NetworkSimulationConfig(BaseModel):
    enabled: bool = True
    nodes: int = 10
    base_latency: float = 20.0
    base_bandwidth: float = 1000.0
    base_packet_loss: float = 0.01
    event_probability: float = 0.3


class NetworkConfig(BaseModel):
    simulation: NetworkSimulationConfig = Field(default_factory=NetworkSimulationConfig)


class LLMConfig(BaseModel):
    provider: str = "mock"
    model: str = "gpt-4o-mini"
    temperature: float = 0.3
    max_tokens: int = 1024
    
    @property
    def api_key(self) -> Optional[str]:
        return os.getenv("OPENAI_API_KEY")


class FeedbackConfig(BaseModel):
    enabled: bool = True
    learning_rate: float = 0.1
    history_window: int = 100


class APIConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = ["*"]


class SystemConfig(BaseModel):
    name: str = "Network Optimizer Agent System"
    version: str = "1.0.0"
    log_level: str = "INFO"
    data_dir: str = "data"


class Config(BaseModel):
    system: SystemConfig = Field(default_factory=SystemConfig)
    agents: AgentsConfig = Field(default_factory=AgentsConfig)
    network: NetworkConfig = Field(default_factory=NetworkConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    feedback: FeedbackConfig = Field(default_factory=FeedbackConfig)
    api: APIConfig = Field(default_factory=APIConfig)


def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration from YAML file."""
    if config_path is None:
        # Look for config.yaml in the project root
        config_path = Path(__file__).parent.parent.parent / "config.yaml"
    else:
        config_path = Path(config_path)
    
    if config_path.exists():
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        return Config(**config_data)
    
    # Return default config if file doesn't exist
    return Config()


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reload_config(config_path: Optional[str] = None) -> Config:
    """Reload the configuration from file."""
    global _config
    _config = load_config(config_path)
    return _config
