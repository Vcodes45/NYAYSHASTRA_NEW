"""
NyayGuru AI Pro - Statute Retrieval Agent
Retrieves relevant IPC/BNS sections and handles cross-mapping.
NO MOCK DATA - Uses real database via StatuteService.
"""

from typing import List, Dict, Any, Optional
import logging

from app.agents.base import BaseAgent, AgentContext
from app.schemas import AgentType
from app.services.vector_store import VectorStoreService
from app.services.statute_service import StatuteService, get_statute_service

logger = logging.getLogger(__name__)


class StatuteRetrievalAgent(BaseAgent):
    """Agent for retrieving relevant statutes and sections from database."""
    
    def __init__(self, vector_store: Optional[VectorStoreService] = None, 
                 statute_service: Optional[StatuteService] = None):
        super().__init__()
        self.agent_type = AgentType.STATUTE
        self.name = "Statute Retrieval"
        self.name_hi = "विधि खोज"
        self.description = "Retrieves relevant IPC, BNS, and other statute sections"
        self.color = "#a855f7"
        
        self.vector_store = vector_store
        # Use provided service or get singleton
        self.statute_service = statute_service or get_statute_service()
    
    async def process(self, context: AgentContext) -> AgentContext:
        """Retrieve authoritative statute evidence via hybrid RAG (metadata + dense + BM25 + rerank)."""
        import asyncio
        from app.services.hybrid_search_service import get_hybrid_search_service, EmptyKnowledgeBaseError
        
        sections = [(e.get("act"), e["value"]) for e in context.entities if e["type"] == "section"]
        articles = [e["value"] for e in context.entities if e["type"] == "article"]
        act_codes = [e["value"] for e in context.entities if e["type"] == "act"]
        if context.specified_domain and context.specified_domain != "all":
            domain = context.specified_domain
        else:  # auto-detected domain is used as a metadata filter only when the classifier is confident
            domain = context.detected_domain if context.domain_confidence >= 0.6 else None
        
        try:
            search = await asyncio.to_thread(get_hybrid_search_service)
            evidence, diag = await asyncio.to_thread(
                search.search,
                context.query,
                domain=domain,
                act_codes=act_codes or None,
                sections=sections or None,
                articles=articles or None,
            )
            context.retrieval_diagnostics = {**diag, "collection": search.collection_name,
                                             "document_count": search.count()}
            context.missing_sections = await asyncio.to_thread(search.missing_sections, sections)
        except EmptyKnowledgeBaseError as e:
            logger.error(f"[RETRIEVAL] {e}")
            context.kb_empty = True
            context.add_error(self.name, str(e))
            evidence = []
        except Exception as e:
            logger.error(f"[RETRIEVAL] failed: {e}")
            context.add_error(self.name, f"retrieval failed: {e}")
            evidence = []
        
        context.evidence = evidence
        context.statutes = [self._to_statute(ev) for ev in evidence]
        
        # Cross-mappings are shown in the UI only (never fed to the SLM as evidence)
        ipc_sections = [s for s in context.statutes if s.get("act_code") == "IPC"]
        context.ipc_bns_mappings = await self._get_cross_mappings(ipc_sections)
        
        logger.info(f"[RETRIEVAL] {len(evidence)} evidence blocks: "
                    f"{[(s['act_code'], s['section_number']) for s in context.statutes]}")
        return context
    
    @staticmethod
    def _to_statute(ev: Dict[str, Any]) -> Dict[str, Any]:
        """Shape a retrieved chunk like the statute objects the frontend already renders."""
        meta = ev.get("metadata", {})
        return {
            "id": ev["id"],
            "section_number": meta.get("section") or meta.get("article", ""),
            "act_code": meta.get("act_code", ""),
            "act_name": meta.get("act_name", ""),
            "title_en": meta.get("section_title", ""),
            "content_en": ev["content"],
            "content": ev["content"],
            "domain": meta.get("legal_domain", ""),
            "chapter": meta.get("chapter", ""),
            "source": meta.get("source", ""),
            "source_url": meta.get("source_url", ""),
            "authority_level": meta.get("authority_level"),
            "status": meta.get("status", ""),
            "relevance_score": ev.get("rerank_score"),
            "rrf_score": ev.get("rrf_score"),
        }
    
    async def _get_cross_mappings(self, ipc_sections: List[Dict]) -> List[Dict]:
        """Get cross-mappings between IPC and BNS sections from database."""
        mappings = []
        
        for ipc in ipc_sections:
            section_num = ipc.get("section_number")
            if section_num:
                mapping = await self.statute_service.get_ipc_bns_mapping(section_num)
                if mapping:
                    # Format mapping for frontend
                    mappings.append({
                        "id": str(mapping.get("id", "")),
                        "ipc_section": mapping.get("ipc_section", ""),
                        "ipc_title": mapping.get("ipc_title", ""),
                        "ipc_content": mapping.get("ipc_content", ""),
                        "bns_section": mapping.get("bns_section", ""),
                        "bns_title": mapping.get("bns_title", ""),
                        "bns_content": mapping.get("bns_content", ""),
                        "changes": mapping.get("changes", []),
                        "punishment_change": {
                            "old": mapping.get("old_punishment", ""),
                            "new": mapping.get("new_punishment", ""),
                            "increased": mapping.get("punishment_increased", False)
                        } if mapping.get("punishment_changed") else None,
                        "mapping_type": mapping.get("mapping_type", "exact"),
                        # Seeded from mappings.csv, which has no recorded official provenance
                        "verified": False,
                    })
                    logger.info(f"Found mapping: IPC {section_num} -> BNS {mapping.get('bns_section')}")
        
        return mappings
