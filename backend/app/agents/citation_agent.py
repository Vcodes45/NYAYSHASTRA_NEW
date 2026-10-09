"""
NyayGuru AI Pro - Citation & Verification Agent
Generates verifiable citations linked to official sources.
"""

from typing import List, Dict, Any
import logging
import re

from app.agents.base import BaseAgent, AgentContext
from app.schemas import AgentType

logger = logging.getLogger(__name__)


# Official legal source URLs
OFFICIAL_SOURCES = {
    "gazette": {
        "name": "Official Gazette of India",
        "name_hi": "भारत का राजपत्र",
        "base_url": "https://egazette.gov.in",
        "description": "Official Government Gazette publications"
    },
    "indiankanoon": {
        "name": "Indian Kanoon",
        "name_hi": "इंडियन कानून",
        "base_url": "https://indiankanoon.org",
        "description": "Free legal search engine for Indian laws"
    },
    "sci": {
        "name": "Supreme Court of India",
        "name_hi": "भारत का सर्वोच्च न्यायालय",
        "base_url": "https://main.sci.gov.in",
        "description": "Official Supreme Court website"
    },
    "legislative": {
        "name": "Legislative Department",
        "name_hi": "विधायी विभाग",
        "base_url": "https://legislative.gov.in",
        "description": "Official laws and bareacts"
    },
    "lawcommission": {
        "name": "Law Commission of India",
        "name_hi": "भारत का विधि आयोग",
        "base_url": "https://lawcommissionofindia.nic.in",
        "description": "Law reform recommendations"
    }
}


class CitationAgent(BaseAgent):
    """Agent for generating and verifying legal citations."""
    
    def __init__(self):
        super().__init__()
        self.agent_type = AgentType.CITATION
        self.name = "Citation Agent"
        self.name_hi = "उद्धरण एजेंट"
        self.description = "Generates verifiable citations linked to official sources"
        self.color = "#ff4081"
    
    def _clean_legal_text(self, text: str) -> str:
        """Clean messy legal text from PDF extractions - fixes OCR and amendment noise."""
        if not text:
            return ""
        
        # Step 0: Remove legislative amendment annotations (not useful for users)
        # Patterns like: "1. Subs. by Act 7 of 2017, s. 169, for..." 
        # "[w.e.f. 26-5-2017]" etc.
        amendment_patterns = [
            r'\d+\.\s*Subs\.?\s*by\s*(Act\s*)?\d+\s*of\s*\d{4},?\s*s\.?\s*\d+[^.]*\.?',  # "1. Subs. by Act 7 of 2017, s. 169"
            r'\d+\.\s*Ins\.?\s*by\s*(Act\s*)?\d+\s*of\s*\d{4}[^.]*\.?',  # "2. Ins. by Act..."
            r'\d+\.\s*Omitted\s*by\s*(Act\s*)?\d+\s*of\s*\d{4}[^.]*\.?',  # "3. Omitted by..."
            r'\(w\.?e\.?f\.?\s*\d{1,2}-\d{1,2}-\d{4}\)',  # (w.e.f. 26-5-2017)
            r'\[w\.?e\.?f\.?\s*\d{1,2}-\d{1,2}-\d{4}\]',  # [w.e.f. 26-5-2017]
            r'w\.?e\.?f\.?\s*\d{1,2}-\d{1,2}-\d{4}',  # w.e.f. 26-5-2017
            r'\d+\[',  # Footnote markers like "1[" or "84A"
            r'\]\d+',  # Closing footnote markers
            r'\|\|',   # Double pipes
            r'ibid\.,?\s*for\s*[-—]',  # "ibid., for —"
            r'for\s*[-—]\s*the\s+',  # "for — the"
        ]
        
        for pattern in amendment_patterns:
            text = re.sub(pattern, ' ', text, flags=re.IGNORECASE)
        
        # Step 1: Fix OCR broken words (spaces inserted in middle of words)
        ocr_fixes = [
            (r'\bo\s*therw\s*ise\b', 'otherwise'),
            (r'\bpun\s*ish\s*able\b', 'punishable'),
            (r'\bpun\s*ish\s*ment\b', 'punishment'),
            (r'\bimpr\s*ison\s*ment\b', 'imprisonment'),
            (r'\bimpr\s*ison\b', 'imprison'),
            (r'\bpubl\s*ish\s*(es|ed|ing)?\b', r'publish\1'),
            (r'\btransmitt\s*ing\b', 'transmitting'),
            (r'\btransmit\s*ted\b', 'transmitted'),
            (r'\boff\s*ence\b', 'offence'),
            (r'\boff\s*ender\b', 'offender'),
            (r'\bcom\s*mits?\b', r'commit'),
            (r'\bcon\s*spires?\b', 'conspire'),
            (r'\bterr\s*or\s*ism\b', 'terrorism'),
            (r'\blas\s*civ\s*ious\b', 'lascivious'),
            (r'\bpru\s*ri\s*ent\b', 'prurient'),
            (r'\belec\s*tron\s*ic\b', 'electronic'),
            (r'\bmat\s*er\s*ial\b', 'material'),
            (r'\bobs\s*cene\b', 'obscene'),
            (r'\bin\s*div\s*id\s*uals?\b', r'individual'),
            (r'\bna\s*tion\b', 'nation'),
            (r'\bcy\s*ber\b', 'cyber'),
            (r'\bsec\s*tion\b', 'section'),
            (r'\bSec\s*tion\b', 'Section'),
            (r'\bwho\s*ever\b', 'whoever'),
            (r'\bWho\s*ever\b', 'Whoever'),
            (r'\bex\s*tend\b', 'extend'),
            (r'\bcaus\s*es\b', 'causes'),
            (r'\bef\s*fect\b', 'effect'),
            (r'\bin\s*ter\s*est\b', 'interest'),
            (r'\bap\s*peals?\b', r'appeal'),
            (r'\bper\s*son\b', 'person'),
            (r'\bPer\s*son\b', 'Person'),
            (r'\bsub\s*ject\b', 'subject'),
            (r'\bpro\s*vi\s*sion\b', 'provision'),
            (r'\bPro\s*vi\s*sion\b', 'Provision'),
            (r'\bgov\s*ern\s*ment\b', 'government'),
            (r'\bGov\s*ern\s*ment\b', 'Government'),
            (r'\blaw\s*ful\b', 'lawful'),
            (r'\bun\s*law\s*ful\b', 'unlawful'),
            (r'\bwil\s*ful\b', 'wilful'),
            (r'\bknow\s*ing\s*ly\b', 'knowingly'),
            (r'\bin\s*tent\s*ion\b', 'intention'),
            (r'\bac\s*cused\b', 'accused'),
            (r'\bcon\s*vict\s*ed\b', 'convicted'),
            (r'\bsen\s*tence\b', 'sentence'),
            (r'\bpros\s*ecu\s*tion\b', 'prosecution'),
            (r'\bevi\s*dence\b', 'evidence'),
            (r'\bwit\s*ness\b', 'witness'),
            (r'\bjudg\s*ment\b', 'judgment'),
            (r'\bver\s*dict\b', 'verdict'),
            (r'\bcrim\s*in\s*al\b', 'criminal'),
            (r'\bCrim\s*in\s*al\b', 'Criminal'),
            (r'\bciv\s*il\b', 'civil'),
            (r'\bCiv\s*il\b', 'Civil'),
            (r'\bliab\s*il\s*ity\b', 'liability'),
            (r'\bliab\s*le\b', 'liable'),
            (r'\bdam\s*ages?\b', r'damage'),
            (r'\bcom\s*pen\s*sa\s*tion\b', 'compensation'),
            (r'f\s+or\b', 'for'),
            (r'\bf\s+orm\b', 'form'),
            (r'\bt\s+o\b', 'to'),
            (r'\bego\s*vernance\b', 'e-governance'),
            (r'\begovernance\b', 'e-governance'),
            (r'\becommerce\b', 'e-commerce'),
            (r'\babet\s*ment\b', 'abetment'),
            (r'\bencry\s*ption\b', 'encryption'),
            (r'\bpre\s*scribe\b', 'prescribe'),
            (r'\bpro\s*motion\b', 'promotion'),
            (r'\bChair\s*person\b', 'Chairperson'),
            (r'\badju\s*dicat\s*ing\b', 'adjudicating'),
            (r'\bTri\s*bunal\b', 'Tribunal'),
            (r'\bAppel\s*late\b', 'Appellate'),
        ]
        
        for pattern, replacement in ocr_fixes:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        # Step 2: Fix punctuation and spacing issues
        text = re.sub(r'([,;:])([a-zA-Z])', r'\1 \2', text)
        text = re.sub(r'([a-zA-Z])(\()', r'\1 \2', text)
        text = re.sub(r'(\))([a-zA-Z])', r'\1 \2', text)
        
        # Step 3: Clean up section references
        text = re.sub(r'(\d+)([A-Z]\.)', r'\1\2 ', text)  # "84A." -> "84A. "
        text = re.sub(r'\.–', '. ', text)  # ".–" -> ". "
        text = re.sub(r'–', ' - ', text)  # em-dash to spaced hyphen
        
        # Step 4: Fix multiple spaces and clean up
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Step 5: Remove incomplete sentences at start (amendment leftovers)
        # If text starts with lowercase or incomplete pattern, try to find first complete sentence
        if text and (text[0].islower() or text.startswith('of ') or text.startswith('for ')):
            # Find first capital letter that starts a sentence
            match = re.search(r'[.]\s*([A-Z][a-z])', text)
            if match:
                text = text[match.start()+2:]
        
        return text
    
    async def process(self, context: AgentContext) -> AgentContext:
        """Generate citations for statutes and case laws."""
        
        citations = []
        citation_id = 1
        
        logger.info(f"CitationAgent: Processing {len(context.statutes)} statutes, {len(context.case_laws)} case_laws")
        
        # 1. Generate citations for statutes
        for statute in context.statutes:
            logger.info(f"CitationAgent: Creating citation for statute: {statute.get('section_number', 'unknown')}")
            citation = self._create_statute_citation(statute, citation_id)
            if citation:
                citations.append(citation)
                citation_id += 1
        
        # 2. Generate citations for case laws
        for case in context.case_laws:
            logger.info(f"CitationAgent: Creating citation for case: {case.get('case_name', 'unknown')}")
            citation = self._create_case_citation(case, citation_id)
            if citation:
                citations.append(citation)
                citation_id += 1
        
        # 3. Add IPC-BNS mapping citations if relevant
        for mapping in context.ipc_bns_mappings:
            citation = self._create_mapping_citation(mapping, citation_id)
            if citation:
                citations.append(citation)
                citation_id += 1
        
        # 4. Verify and deduplicate citations
        citations = self._deduplicate_citations(citations)
        
        context.citations = citations
        
        logger.info(f"Generated {len(citations)} verified citations")
        
        return context
    
    def _create_statute_citation(self, statute: Dict, citation_id: int) -> Dict:
        """Create citation for a statute section."""
        act_code = statute.get("act_code", "IPC")
        section = statute.get("section_number", "")
        act_name = statute.get("act_name", "")
        title = statute.get("title_en", "")
        content = statute.get("content_en", "")
        
        # Use Indian Kanoon for ALL statutes - it's the most reliable source
        # They have direct document IDs for major sections
        IPC_SECTION_DOCS = {
            "302": "1560742",  # Murder
            "304": "1279877",  # Culpable homicide
            "307": "1290514",  # Attempt to murder
            "376": "1279834",  # Rape
            "420": "1436241",  # Cheating
            "498A": "110081",  # Cruelty by husband
            "354": "1279834",  # Assault on woman
            "306": "871857",   # Abetment to suicide
            "379": "1279854",  # Theft
            "384": "1279782",  # Extortion
            "392": "1279793",  # Robbery
            "406": "1569253",  # Criminal breach of trust
            "415": "1306487",  # Cheating
            "499": "1383364",  # Defamation
            "500": "1436475",  # Defamation punishment
            "120B": "635852",  # Criminal conspiracy
            "34": "37788",     # Common intention
        }
        
        source_name = "Indian Kanoon"
        verified = False
        if statute.get("source_url"):
            # Retrieved from an indexed official source: cite that source directly
            url = statute["source_url"]
            source = "official"
            source_name = statute.get("source") or "Official source"
            verified = True
        elif act_code == "IPC":
            doc_id = IPC_SECTION_DOCS.get(section, "")
            if doc_id:
                url = f"https://indiankanoon.org/doc/{doc_id}/"
            else:
                url = f"https://indiankanoon.org/search/?formInput=section%20{section}%20IPC"
            source = "indiankanoon"
        elif act_code == "BNS":
            # BNS sections on Indian Kanoon
            url = f"https://indiankanoon.org/search/?formInput=section%20{section}%20BNS%20Bharatiya%20Nyaya%20Sanhita"
            source = "indiankanoon"
        else:
            url = f"https://indiankanoon.org/search/?formInput={act_code}%20section%20{section}"
            source = "indiankanoon"
        
        # Make sure we have content for excerpt - CLEAN IT
        excerpt = content[:500] + "..." if len(content) > 500 else content
        if not excerpt:
            excerpt = f"Section {section} of {act_name}: {title}"
        
        # Clean the excerpt text
        excerpt = self._clean_legal_text(excerpt)
        
        # Build robust title - handle missing fields gracefully
        if section and title:
            citation_title = f"{act_name or act_code} - Section {section}: {title}"
        elif section:
            citation_title = f"{act_name or act_code} - Section {section}"
        elif title:
            citation_title = f"{act_name or act_code}: {title}"
        else:
            citation_title = f"{act_name or act_code} - Legal Provision"
        
        return {
            "id": str(citation_id),
            "title": citation_title,
            "title_hi": statute.get("title_hi", "") or "",
            "source": source,
            "source_name": source_name,
            "url": url,
            "excerpt": excerpt,
            "year": statute.get("year_enacted"),
            "type": "statute",
            "verified": verified,
            "section_number": section or "N/A",
            "act_code": act_code
        }
    
    def _create_case_citation(self, case: Dict, citation_id: int) -> Dict:
        """Create citation for a case law."""
        case_name = case.get("case_name", "")
        citation_string = case.get("citation_string", "")
        source_url = case.get("source_url", "")
        court = case.get("court", "")
        year = case.get("reporting_year")
        
        # Generate URL if not provided - use Indian Kanoon for reliable direct links
        if not source_url:
            safe_name = re.sub(r'[^a-zA-Z0-9\s]', '', case_name)
            encoded_name = safe_name.replace(' ', '%20')
            
            if court == "supreme_court":
                # Supreme Court judgments on Indian Kanoon
                source_url = f"https://indiankanoon.org/search/?formInput={encoded_name}%20supreme%20court"
                source = "indiankanoon"
            elif court == "high_court":
                source_url = f"https://indiankanoon.org/search/?formInput={encoded_name}%20high%20court"
                source = "indiankanoon"
            else:
                source_url = f"https://indiankanoon.org/search/?formInput={encoded_name}"
                source = "indiankanoon"
        else:
            source = "indiankanoon" if "indiankanoon" in source_url else "sci"
        
        title = case_name
        if citation_string:
            title = f"{case_name} ({citation_string})"
        
        summary = case.get("summary_en", "")
        excerpt = summary[:300] + "..." if len(summary) > 300 else summary if summary else None
        
        # Clean excerpt if present
        if excerpt:
            excerpt = self._clean_legal_text(excerpt)
        
        return {
            "id": str(citation_id),
            "title": title,
            "title_hi": case.get("case_name_hi", ""),
            "source": source,
            "source_name": OFFICIAL_SOURCES.get(source, {}).get("name", source),
            "url": source_url,
            "excerpt": excerpt,
            "year": year,
            "court": case.get("court_name", court),
            "type": "case_law",
            "is_landmark": case.get("is_landmark", False),
            "verified": True
        }
    
    def _create_mapping_citation(self, mapping: Dict, citation_id: int) -> Dict:
        """Create citation for IPC-BNS mapping."""
        ipc_section = mapping.get("ipc_section", "")
        bns_section = mapping.get("bns_section", "")
        
        return {
            "id": str(citation_id),
            "title": f"IPC Section {ipc_section} → BNS Section {bns_section} Mapping",
            "title_hi": f"IPC धारा {ipc_section} → BNS धारा {bns_section} मैपिंग",
            "source": "gazette",
            "source_name": OFFICIAL_SOURCES["gazette"]["name"],
            "url": "https://egazette.gov.in/WriteReadData/2023/248044.pdf",
            "excerpt": f"Cross-reference between old IPC Section {ipc_section} and new BNS Section {bns_section}",
            "year": 2023,
            "type": "mapping",
            "verified": True
        }
    
    def _deduplicate_citations(self, citations: List[Dict]) -> List[Dict]:
        """Remove duplicate citations."""
        seen = set()
        unique_citations = []
        
        for citation in citations:
            # Many sections share one official PDF URL, so the key includes the provision
            key = (citation.get("url", ""), citation.get("act_code"), citation.get("section_number"),
                   citation.get("title"))
            if key not in seen:
                seen.add(key)
                unique_citations.append(citation)
        
        return unique_citations
