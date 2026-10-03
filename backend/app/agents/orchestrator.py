"""
NyayGuru AI Pro - Agent Orchestrator
Coordinates the multi-agent pipeline for legal query processing.
"""

import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime
import logging
import uuid

from app.agents.base import AgentContext, BaseAgent
# Agents will be imported lazily inside __init__ to save RAM
from app.schemas import AgentType, AgentStatus, AgentProcessingStep, ChatStreamChunk

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Orchestrates the multi-agent pipeline for legal queries."""
    
    def __init__(self, vector_store=None, llm_service=None, statute_service=None, case_service=None):
        """Initialize orchestrator with optional services."""
        # Lazy imports for agents
        from app.agents.query_agent import QueryUnderstandingAgent
        from app.agents.statute_agent import StatuteRetrievalAgent
        from app.agents.case_agent import CaseLawAgent
        from app.agents.regulatory_agent import RegulatoryFilterAgent
        from app.agents.citation_agent import CitationAgent
        from app.agents.summarization_agent import SummarizationAgent
        from app.agents.response_agent import ResponseSynthesisAgent
        
        self.vector_store = vector_store
        self.llm_service = llm_service
        self.statute_service = statute_service
        self.case_service = case_service
        
        # Initialize agents
        self.agents: List[BaseAgent] = [
            QueryUnderstandingAgent(),
            StatuteRetrievalAgent(vector_store=vector_store, statute_service=statute_service),
            CaseLawAgent(vector_store=vector_store, case_service=case_service),
            RegulatoryFilterAgent(),
            CitationAgent(),
            SummarizationAgent(llm_service=llm_service),
            ResponseSynthesisAgent(llm_service=llm_service)
        ]
        
        # Agent execution order
        self.agent_order = [
            AgentType.QUERY,
            AgentType.STATUTE,
            AgentType.CASE,
            AgentType.REGULATORY,
            AgentType.CITATION,
            AgentType.SUMMARY,
            AgentType.RESPONSE
        ]
    
    async def _ensure_services(self):
        """Ensure all services are initialized and shared with agents."""
        if not self.llm_service:
            try:
                from app.services.llm_service import get_llm_service
                self.llm_service = await get_llm_service()
                logger.info("✅ LLM service initialized in orchestrator")
                # Update agents that need LLM
                for agent in self.agents:
                    if hasattr(agent, 'llm_service') and not agent.llm_service:
                        agent.llm_service = self.llm_service
            except Exception as e:
                logger.error(f"Failed to initialize LLM service in orchestrator: {e}")
                logger.warning("Queries will use fallback responses")

        if not self.vector_store:
            try:
                from app.services.vector_store import get_vector_store
                self.vector_store = await get_vector_store()
                # Update agents that need vector store
                for agent in self.agents:
                    if hasattr(agent, 'vector_store') and not agent.vector_store:
                        agent.vector_store = self.vector_store
            except Exception as e:
                logger.warning(f"Vector store not available in orchestrator: {e}")

    async def process_query(self, query: str, language: str = "en", 
                           session_id: Optional[str] = None,
                           domain: Optional[str] = None) -> Dict[str, Any]:
        """Process a legal query through the full agent pipeline."""
        
        print(f"\n{'='*60}")
        print(f"[ORCHESTRATOR] ===== NEW QUERY =====")
        print(f"[ORCHESTRATOR] Query: {query[:100]}")
        print(f"[ORCHESTRATOR] Domain: {domain}")
        print(f"[ORCHESTRATOR] Language: {language}")
        print(f"{'='*60}\n")
        
        if not self.services_initialized:
            # If still warming up in background thread, tell the user gracefully
            import uuid
            from datetime import datetime
            return {
                "id": str(uuid.uuid4()),
                "session_id": session_id or str(uuid.uuid4()),
                "role": "assistant",
                "content": "⚠️ **NyayGuru AI Pro is currently warming up.**\n\nBecause this is a free-tier deployment, the heavy AI Language Models take a minute or two to load into memory. Please wait about 60 seconds and try your query again!",
                "content_hi": "⚠️ **न्यायगुरु एआई प्रो अभी शुरू हो रहा है।**\n\nचूंकि यह एक मुफ्त डिप्लॉयमेंट है, भारी एआई भाषा मॉडल को मेमोरी में लोड होने में एक या दो मिनट लगते हैं। कृपया लगभग 60 सेकंड प्रतीक्षा करें और फिर से प्रयास करें!",
                "citations": [],
                "statutes": [],
                "case_laws": [],
                "ipc_bns_mappings": [],
                "agent_pipeline": [],
                "detected_domain": "all",
                "detected_language": language,
                "execution_time_seconds": 0,
                "timestamp": datetime.now().isoformat()
            }
        
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Create context
        context = AgentContext(
            query=query,
            language=language,
            session_id=session_id,
            specified_domain=domain
        )
        
        start_time = datetime.now()
        
        # Execute agents in sequence
        for agent in self.agents:
            # If a domain mismatch was detected, skip all agents except the response agent
            if not context.is_relevant and agent.agent_type != AgentType.RESPONSE:
                print(f"[ORCHESTRATOR] Skipping agent {agent.name} due to domain mismatch/rejection")
                logger.info(f"Skipping agent {agent.name} due to domain mismatch/rejection")
                continue
            
            print(f"\n[ORCHESTRATOR] >>> Running agent: {agent.name}")
            try:
                context = await agent.execute(context)
                print(f"[ORCHESTRATOR] <<< Agent {agent.name} completed")
                print(f"[ORCHESTRATOR]     - statutes count: {len(context.statutes)}")
                print(f"[ORCHESTRATOR]     - case_laws count: {len(context.case_laws)}")
                print(f"[ORCHESTRATOR]     - is_relevant: {context.is_relevant}")
                logger.info(f"Agent {agent.name} completed")
            except Exception as e:
                print(f"[ORCHESTRATOR] !!! Agent {agent.name} FAILED: {e}")
                logger.error(f"Agent {agent.name} failed: {e}")
                context.add_error(agent.name, str(e))
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Build response
        response = self._build_response(context, execution_time)
        
        return response
    
    async def process_query_streaming(self, query: str, language: str = "en",
                                      session_id: Optional[str] = None,
                                      domain: Optional[str] = None) -> AsyncGenerator[ChatStreamChunk, None]:
        """Process query with streaming updates for real-time UI."""
        
        if not self.services_initialized:
            import uuid
            yield ChatStreamChunk(
                type="agent_start",
                data={"agent": "System"}
            )
            yield ChatStreamChunk(
                type="token",
                data={"text": "⚠️ **NyayGuru AI Pro is currently warming up.**\n\nBecause this is a free-tier deployment, the heavy AI Language Models take a minute or two to load into memory. Please wait about 60 seconds and try your query again!"}
            )
            yield ChatStreamChunk(
                type="complete",
                data={"session_id": session_id or str(uuid.uuid4())}
            )
            return
            
        await self._ensure_services()
        
        if not session_id:
            session_id = str(uuid.uuid4())
        
        context = AgentContext(
            query=query,
            language=language,
            session_id=session_id,
            specified_domain=domain
        )
        
        # Yield initial status
        yield ChatStreamChunk(
            type="start",
            data={"session_id": session_id, "query": query}
        )
        
        # Execute agents with streaming updates
        for agent in self.agents:
            # Yield agent start
            yield ChatStreamChunk(
                type="agent_status",
                data={
                    "agent": agent.agent_type.value,
                    "status": AgentStatus.PROCESSING.value,
                    "name": agent.name,
                    "name_hi": agent.name_hi
                }
            )
            
            # If a domain mismatch was detected, skip all agents except the response agent
            if not context.is_relevant and agent.agent_type != AgentType.RESPONSE:
                logger.info(f"Skipping agent {agent.name} during streaming due to domain mismatch")
                continue

            try:
                context = await agent.execute(context)
                
                # Yield agent completion
                yield ChatStreamChunk(
                    type="agent_status",
                    data={
                        "agent": agent.agent_type.value,
                        "status": AgentStatus.COMPLETED.value,
                        "name": agent.name
                    }
                )
                
                # Yield intermediate results
                if agent.agent_type == AgentType.STATUTE and context.statutes:
                    yield ChatStreamChunk(
                        type="statutes",
                        data={"statutes": context.statutes[:5]}
                    )
                
                if agent.agent_type == AgentType.CASE and context.case_laws:
                    yield ChatStreamChunk(
                        type="case_laws",
                        data={"case_laws": context.case_laws[:3]}
                    )
                
                if agent.agent_type == AgentType.CITATION and context.citations:
                    yield ChatStreamChunk(
                        type="citations",
                        data={"citations": context.citations}
                    )
                
            except Exception as e:
                yield ChatStreamChunk(
                    type="agent_status",
                    data={
                        "agent": agent.agent_type.value,
                        "status": AgentStatus.ERROR.value,
                        "error": str(e)
                    }
                )
            
            # Small delay for visual effect
            await asyncio.sleep(0.1)
        
        # Yield final response
        yield ChatStreamChunk(
            type="response",
            data={
                "content": context.response,
                "content_hi": context.response_hi,
                "citations": context.citations,
                "statutes": context.statutes,
                "case_laws": context.case_laws,
                "ipc_bns_mappings": context.ipc_bns_mappings
            }
        )
        
        yield ChatStreamChunk(
            type="complete",
            data={"session_id": session_id}
        )
    
    def _build_response(self, context: AgentContext, execution_time: float) -> Dict[str, Any]:
        """Build final response from context."""
        return {
            "id": str(uuid.uuid4()),
            "session_id": context.session_id,
            "query": context.original_query,
            "language": context.language,
            "detected_language": context.detected_language,
            "detected_domain": context.detected_domain,
            "response": {
                "content": context.response,
                "content_hi": context.response_hi
            },
            "statutes": context.statutes,
            "case_laws": context.case_laws,
            "ipc_bns_mappings": context.ipc_bns_mappings,
            "citations": context.citations,
            "agent_pipeline": [step.model_dump() for step in context.agent_steps],
            "errors": context.errors,
            "execution_time_seconds": execution_time,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_agent_info(self) -> List[Dict[str, Any]]:
        """Get information about all agents."""
        return [agent.get_info() for agent in self.agents]


# Singleton orchestrator instance
_orchestrator: Optional[AgentOrchestrator] = None


def get_orchestrator() -> AgentOrchestrator:
    """Get or create the orchestrator singleton."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator


def init_orchestrator(vector_store=None, llm_service=None, 
                      statute_service=None, case_service=None) -> AgentOrchestrator:
    """Initialize orchestrator with services."""
    global _orchestrator
    _orchestrator = AgentOrchestrator(
        vector_store=vector_store,
        llm_service=llm_service,
        statute_service=statute_service,
        case_service=case_service
    )
    return _orchestrator
