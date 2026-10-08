"""
NyayGuru AI Pro - Base Agent Class
Abstract base class for all legal AI agents.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
import asyncio
import logging

from app.schemas import AgentType, AgentStatus, AgentProcessingStep


logger = logging.getLogger(__name__)


class AgentContext:
    """Shared context passed between agents."""
    
    def __init__(self, query: str, language: str = "en", session_id: Optional[str] = None, specified_domain: Optional[str] = None):
        self.query = query
        self.original_query = query
        self.language = language
        self.session_id = session_id
        self.specified_domain = specified_domain
        
        # Detected information
        self.detected_language: Optional[str] = None
        self.detected_domain: Optional[str] = None
        self.domain_confidence: float = 0.0
        self.reformulated_query: Optional[str] = None
        self.keywords: List[str] = []
        self.entities: List[Dict[str, Any]] = []
        
        # Relevance guardrails
        self.is_relevant: bool = True
        self.rejection_message: Optional[str] = None
        
        # Retrieved data
        self.evidence: List[Dict[str, Any]] = []  # reranked RAG chunks (source of truth for the SLM)
        self.retrieval_diagnostics: Dict[str, Any] = {}
        self.kb_empty: bool = False
        self.missing_sections: List[Any] = []  # explicit (act, section) refs absent from an indexed act
        self.grounding: Dict[str, Any] = {}
        self.statutes: List[Dict[str, Any]] = []
        self.case_laws: List[Dict[str, Any]] = []
        self.citations: List[Dict[str, Any]] = []
        self.ipc_bns_mappings: List[Dict[str, Any]] = []
        
        # Regulatory filtering
        self.jurisdiction: Optional[str] = None
        self.applicable_acts: List[str] = []
        
        # Document data (if any)
        self.document_summary: Optional[Dict[str, Any]] = None
        
        # Final response
        self.response: Optional[str] = None
        self.response_hi: Optional[str] = None
        
        # Agent pipeline tracking
        self.agent_steps: List[AgentProcessingStep] = []
        
        # Error tracking
        self.errors: List[Dict[str, Any]] = []
    
    def add_agent_step(self, agent: AgentType, status: AgentStatus, result_summary: Optional[str] = None):
        """Add an agent processing step."""
        step = AgentProcessingStep(
            agent=agent,
            status=status,
            started_at=datetime.now() if status == AgentStatus.PROCESSING else None,
            completed_at=datetime.now() if status == AgentStatus.COMPLETED else None,
            result_summary=result_summary
        )
        
        # Update existing or add new
        for i, existing in enumerate(self.agent_steps):
            if existing.agent == agent:
                self.agent_steps[i] = step
                return
        self.agent_steps.append(step)
    
    def add_error(self, agent: str, error: str):
        """Add an error to context."""
        self.errors.append({
            "agent": agent,
            "error": error,
            "timestamp": datetime.now().isoformat()
        })


class BaseAgent(ABC):
    """Abstract base class for all agents."""
    
    def __init__(self):
        self.agent_type: AgentType = AgentType.QUERY
        self.name: str = "Base Agent"
        self.name_hi: str = "बेस एजेंट"
        self.description: str = "Base agent class"
        self.color: str = "#00d4ff"
    
    @abstractmethod
    async def process(self, context: AgentContext) -> AgentContext:
        """Process the context and return updated context."""
        pass
    
    async def execute(self, context: AgentContext) -> AgentContext:
        """Execute the agent with proper status tracking."""
        try:
            # Mark as processing
            context.add_agent_step(self.agent_type, AgentStatus.PROCESSING)
            logger.info(f"Agent {self.name} started processing")
            
            # Run the actual processing
            result = await self.process(context)
            
            # Mark as completed
            context.add_agent_step(
                self.agent_type, 
                AgentStatus.COMPLETED,
                f"{self.name} completed successfully"
            )
            logger.info(f"Agent {self.name} completed")
            
            return result
            
        except Exception as e:
            logger.error(f"Agent {self.name} failed: {str(e)}")
            context.add_agent_step(self.agent_type, AgentStatus.ERROR, str(e))
            context.add_error(self.name, str(e))
            return context
    
    def get_info(self) -> Dict[str, Any]:
        """Get agent information."""
        return {
            "id": self.agent_type.value,
            "name": self.name,
            "name_hi": self.name_hi,
            "description": self.description,
            "color": self.color
        }
