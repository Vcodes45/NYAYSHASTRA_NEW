"""
NyayGuru AI Pro - Regulatory Filter Agent
Filters laws by jurisdiction and legal category.
"""

from typing import List, Dict, Any
import logging

from app.agents.base import BaseAgent, AgentContext
from app.schemas import AgentType, LegalDomain

logger = logging.getLogger(__name__)


# Regulatory jurisdiction mapping
JURISDICTION_ACTS = {
    LegalDomain.CRIMINAL: ["IPC", "BNS", "CrPC", "BNSS", "IEA", "BSA"],
    LegalDomain.CORPORATE: ["Companies Act", "SEBI Act", "IBC", "LLP Act", "Partnership Act", "Income Tax Act", "GST Act"],
    LegalDomain.IT_CYBER: ["IT Act", "DPDP Act", "Information Technology Act"],
    LegalDomain.ENVIRONMENT: ["Environment Protection Act", "Wildlife Protection Act",
                                "Forest Conservation Act", "Water Act", "Air Act", "NGT Act"],
    LegalDomain.CIVIL_FAMILY: ["CPC", "Hindu Marriage Act", "Special Marriage Act", "Hindu Succession Act",
                         "Indian Divorce Act", "Muslim Personal Law", "Domestic Violence Act", "Contract Act"],
    LegalDomain.PROPERTY: ["Transfer of Property Act", "Registration Act", "Stamp Act",
                           "RERA", "Land Acquisition Act"],
    LegalDomain.CONSTITUTIONAL: ["Constitution of India", "Representation of People Act", "RTI Act"],
    LegalDomain.TRAFFIC: ["Motor Vehicles Act", "Road Safety Rules"]
}


class RegulatoryFilterAgent(BaseAgent):
    """Agent for filtering by jurisdiction and regulatory category."""
    
    def __init__(self):
        super().__init__()
        self.agent_type = AgentType.REGULATORY
        self.name = "Regulatory Filter"
        self.name_hi = "नियामक फ़िल्टर"
        self.description = "Filters laws by jurisdiction and legal category"
        self.color = "#ffc107"
    
    async def process(self, context: AgentContext) -> AgentContext:
        """Filter and categorize retrieved legal information."""
        
        # 1. Determine applicable jurisdiction/domain
        domain = self._determine_domain(context)
        context.jurisdiction = domain
        
        # 2. Get applicable acts for this domain
        if domain in [d.value for d in LegalDomain]:
            domain_enum = LegalDomain(domain)
            context.applicable_acts = JURISDICTION_ACTS.get(domain_enum, [])
        
        # 3. Filter statutes by relevance to domain
        filtered_statutes = self._filter_statutes_by_domain(context.statutes, domain)
        context.statutes = filtered_statutes
        
        # 4. Filter case laws by domain
        filtered_cases = self._filter_cases_by_domain(context.case_laws, domain)
        context.case_laws = filtered_cases
        
        # 5. Add regulatory notes
        context.regulatory_notes = self._get_regulatory_notes(domain, context)
        
        logger.info(f"Applied regulatory filter for domain: {domain}")
        logger.info(f"Applicable acts: {context.applicable_acts}")
        
        return context
    
    def _determine_domain(self, context: AgentContext) -> str:
        """Determine the legal domain from context."""
        # Use detected domain from query agent
        if context.detected_domain:
            return context.detected_domain
        
        # Infer from statutes
        if context.statutes:
            act_codes = set(s.get("act_code", "") for s in context.statutes)
            
            if "IPC" in act_codes or "BNS" in act_codes:
                return LegalDomain.CRIMINAL.value
            elif "IT" in act_codes:
                return LegalDomain.IT_CYBER.value
            elif "Companies" in str(act_codes):
                return LegalDomain.CORPORATE.value
        
        return LegalDomain.CRIMINAL.value
    
    def _filter_statutes_by_domain(self, statutes: List[Dict], domain: str) -> List[Dict]:
        """Filter statutes by domain relevance."""
        if not statutes:
            return []
        # RAG evidence is already reranked; keep its order
        if any("rrf_score" in st for st in statutes):
            return statutes
        
        # Score and sort by relevance to domain
        for statute in statutes:
            score = 0
            statute_domain = statute.get("domain", "")
            
            # Exact domain match
            if statute_domain == domain:
                score += 10
            
            # Act code relevance
            act_code = statute.get("act_code", "")
            try:
                domain_enum = LegalDomain(domain)
                if act_code in JURISDICTION_ACTS.get(domain_enum, []):
                    score += 5
            except ValueError:
                pass
            
            statute["relevance_score"] = score
        
        # Sort by relevance
        statutes.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        
        return statutes
    
    def _filter_cases_by_domain(self, cases: List[Dict], domain: str) -> List[Dict]:
        """Filter case laws by domain relevance."""
        if not cases:
            return []
        
        for case in cases:
            score = 0
            case_domain = case.get("domain", "")
            
            if case_domain == domain:
                score += 10
            
            # Landmark cases get bonus
            if case.get("is_landmark"):
                score += 5
            
            case["relevance_score"] = score
        
        cases.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        
        return cases
    
    def _get_regulatory_notes(self, domain: str, context: AgentContext) -> Dict[str, Any]:
        """Get regulatory notes for the domain."""
        notes = {
            "domain": domain,
            "applicable_acts": [],
            "key_authorities": [],
            "filing_requirements": [],
            "time_limits": []
        }
        
        # Domain-specific notes
        domain_notes = {
            LegalDomain.CRIMINAL.value: {
                "applicable_acts": ["Indian Penal Code (IPC)", "Bhartiya Nyaya Sanhita (BNS)", 
                                   "Criminal Procedure Code (CrPC)", "Bhartiya Nagarik Suraksha Sanhita (BNSS)"],
                "key_authorities": ["Police", "Magistrate", "Sessions Court", "High Court", "Supreme Court"],
                "filing_requirements": ["FIR for cognizable offences", "Private complaint for non-cognizable"],
                "time_limits": ["Limitation periods vary by offence severity"]
            },
            LegalDomain.CORPORATE.value: {
                "applicable_acts": ["Companies Act, 2013", "SEBI Regulations", "IBC, 2016", "Income Tax Act"],
                "key_authorities": ["Registrar of Companies", "SEBI", "NCLT", "NCLAT"],
                "filing_requirements": ["Annual returns", "Board resolutions", "Statutory registers"],
                "time_limits": ["Annual return within 60 days of AGM"]
            },
            LegalDomain.IT_CYBER.value: {
                "applicable_acts": ["Information Technology Act, 2000", "IT Rules, 2021", "DPDP Act, 2023"],
                "key_authorities": ["Cyber Crime Cells", "Adjudicating Officer", "CERT-In"],
                "filing_requirements": ["Cyber crime complaints online or at cyber cells"],
                "time_limits": ["Data breach notification within 6 hours to CERT-In"]
            },
            LegalDomain.CIVIL_FAMILY.value: {
                "applicable_acts": ["Hindu Marriage Act", "Special Marriage Act", 
                                   "Domestic Violence Act", "Hindu Succession Act", "CPC"],
                "key_authorities": ["Family Court", "District Court", "High Court"],
                "filing_requirements": ["Marriage registration", "Divorce petition", "Civil Suit"],
                "time_limits": ["1 year cooling off period for mutual divorce"]
            },
            LegalDomain.TRAFFIC.value: {
                "applicable_acts": ["Motor Vehicles Act", "Road Safety Rules"],
                "key_authorities": ["Traffic Police", "RTO", "Magistrate Court"],
                "filing_requirements": ["Challan payment", "Contesting challan in court"],
                "time_limits": ["Payment within specified days of challan issuance"]
            }
        }
        
        if domain in domain_notes:
            notes.update(domain_notes[domain])
        
        return notes
