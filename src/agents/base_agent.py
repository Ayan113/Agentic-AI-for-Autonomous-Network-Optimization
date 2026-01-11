"""
Base agent class for the multi-agent system.
"""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field

from ..utils.logging import AgentLogger


class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


class AgentMessage(BaseModel):
    """Message passed between agents."""
    sender: str
    recipient: str
    message_type: str
    payload: dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    correlation_id: Optional[str] = None


class BaseAgent(ABC):
    """Abstract base class for all agents in the system."""
    
    def __init__(self, name: str):
        self.name = name
        self.status = AgentStatus.IDLE
        self.logger = AgentLogger(name)
        self.message_queue: asyncio.Queue[AgentMessage] = asyncio.Queue()
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self.stats = {
            "messages_received": 0,
            "messages_sent": 0,
            "cycles_completed": 0,
            "errors": 0,
            "last_active": None
        }
    
    @abstractmethod
    async def process(self, message: Optional[AgentMessage] = None) -> Optional[AgentMessage]:
        """
        Main processing logic for the agent.
        Should be implemented by subclasses.
        
        Args:
            message: Optional incoming message to process
            
        Returns:
            Optional response message
        """
        pass
    
    async def start(self):
        """Start the agent's processing loop."""
        self._running = True
        self.status = AgentStatus.RUNNING
        self.logger.info(f"Agent started")
        
        try:
            while self._running:
                try:
                    # Check for incoming messages with timeout
                    try:
                        message = await asyncio.wait_for(
                            self.message_queue.get(),
                            timeout=1.0
                        )
                        self.stats["messages_received"] += 1
                    except asyncio.TimeoutError:
                        message = None
                    
                    # Process (with or without message)
                    response = await self.process(message)
                    
                    self.stats["cycles_completed"] += 1
                    self.stats["last_active"] = datetime.now().isoformat()
                    
                    if response:
                        return response
                        
                except Exception as e:
                    self.stats["errors"] += 1
                    self.logger.error(f"Error in processing: {str(e)}")
                    self.status = AgentStatus.ERROR
                    await asyncio.sleep(5)  # Back off on error
                    self.status = AgentStatus.RUNNING
                    
        except asyncio.CancelledError:
            self.logger.info("Agent cancelled")
        finally:
            self._running = False
            self.status = AgentStatus.IDLE
    
    async def stop(self):
        """Stop the agent gracefully."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self.logger.info("Agent stopped")
    
    async def send_message(self, recipient: str, message_type: str, payload: dict) -> AgentMessage:
        """Create and return a message to be sent to another agent."""
        message = AgentMessage(
            sender=self.name,
            recipient=recipient,
            message_type=message_type,
            payload=payload
        )
        self.stats["messages_sent"] += 1
        return message
    
    async def receive_message(self, message: AgentMessage):
        """Receive a message from another agent."""
        await self.message_queue.put(message)
    
    def get_status(self) -> dict:
        """Get the current status of the agent."""
        return {
            "name": self.name,
            "status": self.status.value,
            "stats": self.stats
        }
    
    def pause(self):
        """Pause the agent."""
        self.status = AgentStatus.PAUSED
        self.logger.info("Agent paused")
    
    def resume(self):
        """Resume the agent."""
        self.status = AgentStatus.RUNNING
        self.logger.info("Agent resumed")
