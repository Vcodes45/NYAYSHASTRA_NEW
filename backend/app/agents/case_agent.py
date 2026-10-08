"""
NyayGuru AI Pro - Case Law Intelligence Agent
Retrieves relevant case laws and judgments from database.
NO MOCK DATA - Uses real database via CaseService.
"""

from typing import List, Dict, Any, Optional
import logging

from app.agents.base import BaseAgent, AgentContext
from app.schemas import AgentType
from app.services.vector_store import VectorStoreService
from app.services.case_service import CaseService, get_case_service

logger = logging.getLogger(__name__)


class CaseLawAgent(BaseAgent):
    """Agent for retrieving relevant case laws from database."""
    
    def __init__(self, vector_store: Optional[VectorStoreService] = None,
                 case_service: Optional[CaseService] = None):
        super().__init__()
        self.agent_type = AgentType.CASE
        self.name = "Case Law Intelligence"
        self.name_hi = "न्यायिक मामले"
        self.description = "Retrieves relevant Supreme Court and High Court judgments"
        self.color = "#22c55e"
        
        self.vector_store = vector_store
        # Use provided service or get singleton
        self.case_service = case_service or get_case_service()
    
    async def process(self, context: AgentContext) -> AgentContext:
        """Retrieve relevant case laws based on context from database."""
        
        # Ensure vector store is available
        if not self.vector_store:
            try:
                from app.services.vector_store import get_vector_store
                self.vector_store = await get_vector_store()
            except Exception as e:
                logger.warning(f"Vector store not available in CaseLawAgent: {e}")
        
        case_laws = []
        
        # 1. Get cases related to statutes found
        if context.statutes:
            for statute in context.statutes[:3]:  # Top 3 statutes
                section = statute.get("section_number")
                # Case DB is keyed by IPC section numbers; never match e.g. BNS 103 to IPC 103
                if section and statute.get("act_code") == "IPC":
                    related_cases = await self.case_service.get_cases_by_section(
                        section_number=section,
                        limit=2
                    )
                    if related_cases:
                        for c in related_cases:
                            if c not in case_laws:
                                case_laws.append(c)
                        logger.info(f"Found {len(related_cases)} cases for section {section}")
        
        # 2. Search by domain (use specified_domain if available)
        search_domain = context.specified_domain if context.specified_domain and context.specified_domain != "all" else context.detected_domain
        
        if search_domain and not case_laws:
            domain_cases = await self.case_service.search_cases(
                query=context.query,
                domain=search_domain,
                limit=3
            )
            case_laws.extend(domain_cases)
            logger.info(f"Found {len(domain_cases)} cases for domain {search_domain}")
        
        # Landmark cases are no longer appended unconditionally: unrelated authorities mislead users.
        
        # 4. Semantic search if vector store available - with domain filter
        if self.vector_store:
            query = context.reformulated_query or context.query
            semantic_cases = await self.vector_store.search_cases(
                query=query,
                domain=search_domain if search_domain and search_domain != "all" else None,
                limit=3
            )
            existing_ids = {c.get("id") for c in case_laws}
            for case in semantic_cases:
                if case.get("id") not in existing_ids:
                    case_laws.append(case)
        
        # Update context
        context.case_laws = case_laws[:5]  # Limit to 5 cases
        
        logger.info(f"Retrieved {len(context.case_laws)} case laws from database")
        
        return context
