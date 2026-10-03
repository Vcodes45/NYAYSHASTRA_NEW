"""
NyayGuru AI Pro - Query Understanding Agent
Analyzes user queries to detect language, legal domain, and reformulate for precision.
"""

import re
from typing import List, Dict, Any, Optional
import logging

from app.agents.base import BaseAgent, AgentContext
from app.schemas import AgentType, LegalDomain

logger = logging.getLogger(__name__)


# Legal domain keywords moved to bm25_service.py corpus

# IPC/BNS section patterns
SECTION_PATTERN = re.compile(r'(?:section|sec|धारा|§)\s*(\d+[a-zA-Z]?)', re.IGNORECASE)
IPC_PATTERN = re.compile(r'\b(?:ipc|indian penal code|भारतीय दंड संहिता)\b', re.IGNORECASE)
BNS_PATTERN = re.compile(r'\b(?:bns|bhartiya nyaya sanhita|भारतीय न्याय संहिता)\b', re.IGNORECASE)


class QueryUnderstandingAgent(BaseAgent):
    """Agent for understanding and analyzing user queries."""
    
    def __init__(self):
        super().__init__()
        self.agent_type = AgentType.QUERY
        self.name = "Query Understanding"
        self.name_hi = "प्रश्न समझ"
        self.description = "Analyzes queries for language, domain, and intent"
        self.color = "#00d4ff"
        self.domain_classifier = None # Async init

    async def _init_classifier(self):
        if not self.domain_classifier:
            from app.services.bm25_service import get_domain_classifier
            self.domain_classifier = await get_domain_classifier()
    
    async def process(self, context: AgentContext) -> AgentContext:
        """Process the query to understand intent and context."""
        
        query = context.query.lower()
        
        # 1. Detect language
        context.detected_language = self._detect_language(context.query)
        logger.info(f"Detected language: {context.detected_language}")
        
        # 2. Extract section numbers
        sections = self._extract_sections(context.query)
        if sections:
            context.entities.extend([{"type": "section", "value": s} for s in sections])
            logger.info(f"Extracted sections: {sections}")
        
        # 3. Use LLM for intelligent domain detection
        from app.services.llm_router import LLMRouter
        from app.services.llm_service import get_llm_service
        
        # Initialize LLM router
        if not hasattr(self, 'llm_router'):
            llm = await get_llm_service()
            self.llm_router = LLMRouter(llm)
        
        if context.specified_domain and context.specified_domain != "all":
            # User selected a specific domain - verify it matches the query
            is_match, suggested_domain = await self.llm_router.verify_domain_match(
                query, context.specified_domain
            )
            
            if not is_match:
                # Domain mismatch - inform user
                context.detected_domain = suggested_domain
                context.is_relevant = False
                context.rejection_message = (
                    f"⚠️ Your query appears to be about **{suggested_domain}** law, "
                    f"but you've selected **{context.specified_domain}** domain. "
                    f"Please switch to the correct domain for accurate results."
                )
                logger.warning(f"[DOMAIN] Mismatch - query is {suggested_domain}, user selected {context.specified_domain}")
            else:
                context.detected_domain = context.specified_domain
                context.is_relevant = True
                logger.info(f"[DOMAIN] Using specified domain: {context.detected_domain}")
        else:
            # Auto-detect domain using LLM
            detected_domain, confidence = await self.llm_router.detect_domain(query)
            context.detected_domain = detected_domain
            context.is_relevant = True
            logger.info(f"[DOMAIN] Auto-detected: {detected_domain} (confidence: {confidence:.2f})")
        
        # 4. Detect if IPC or BNS specific
        is_ipc = bool(IPC_PATTERN.search(context.query))
        is_bns = bool(BNS_PATTERN.search(context.query))
        
        if is_ipc:
            context.applicable_acts.append("IPC")
        if is_bns:
            context.applicable_acts.append("BNS")
            
        # Add acts based on domain if none specified
        if not context.applicable_acts and context.detected_domain:
            from app.agents.regulatory_agent import JURISDICTION_ACTS
            try:
                # Convert string to LegalDomain enum to match keys in JURISDICTION_ACTS
                domain_enum = LegalDomain(context.detected_domain)
                context.applicable_acts.extend(JURISDICTION_ACTS.get(domain_enum, []))
            except Exception as e:
                logger.warning(f"Error getting acts for domain {context.detected_domain}: {e}")
        
        # If still no acts and sections found, default to both criminal codes
        if not context.applicable_acts and sections:
            context.applicable_acts.extend(["IPC", "BNS"])
        
        # 5. Extract keywords
        context.keywords = self._extract_keywords(context.query)
        
        # 6. Reformulate query for better retrieval
        context.reformulated_query = self._reformulate_query(context)
        
        return context
    
    def _detect_language(self, text: str) -> str:
        """Detect the language of the text using Unicode script detection.
        Supports multiple Indian and international languages."""
        
        # Language detection based on Unicode character ranges
        language_patterns = {
            # Indian Languages
            "hi": r'[\u0900-\u097F]',  # Devanagari (Hindi, Marathi, Sanskrit)
            "ta": r'[\u0B80-\u0BFF]',  # Tamil
            "te": r'[\u0C00-\u0C7F]',  # Telugu
            "bn": r'[\u0980-\u09FF]',  # Bengali
            "gu": r'[\u0A80-\u0AFF]',  # Gujarati
            "kn": r'[\u0C80-\u0CFF]',  # Kannada
            "ml": r'[\u0D00-\u0D7F]',  # Malayalam
            "pa": r'[\u0A00-\u0A7F]',  # Punjabi (Gurmukhi)
            "or": r'[\u0B00-\u0B7F]',  # Odia
            "as": r'[\u0980-\u09FF]',  # Assamese (uses Bengali script)
            # Other Languages
            "ar": r'[\u0600-\u06FF]',  # Arabic
            "ur": r'[\u0600-\u06FF]',  # Urdu (uses Arabic script)
            "zh": r'[\u4E00-\u9FFF]',  # Chinese
            "ja": r'[\u3040-\u30FF]',  # Japanese (Hiragana + Katakana)
            "ko": r'[\uAC00-\uD7AF]',  # Korean
            "th": r'[\u0E00-\u0E7F]',  # Thai
            "ru": r'[\u0400-\u04FF]',  # Russian (Cyrillic)
            "es": r'[áéíóúñ¿¡]',  # Spanish
            "fr": r'[àâçéèêëïîôùûü]',  # French
            "de": r'[äöüß]',  # German
        }
        
        # Count characters for each language
        char_counts = {}
        for lang, pattern in language_patterns.items():
            count = len(re.findall(pattern, text, re.IGNORECASE))
            if count > 0:
                char_counts[lang] = count
        
        # Count English characters
        english_chars = len(re.findall(r'[a-zA-Z]', text))
        
        # If any non-English language has more characters, use that language
        if char_counts:
            max_lang = max(char_counts, key=char_counts.get)
            if char_counts[max_lang] > english_chars * 0.3:  # At least 30% of English chars
                return max_lang
        
        return "en"  # Default to English
    
    def _extract_sections(self, text: str) -> List[str]:
        """Extract section numbers from query."""
        matches = SECTION_PATTERN.findall(text)
        
        # Also look for standalone numbers that might be sections
        standalone = re.findall(r'\b(\d{2,3}[a-zA-Z]?)\b', text)
        
        # Common IPC sections
        common_sections = {"302", "307", "376", "420", "498", "304", "306", "323", "354", "506", "379", "380"}
        
        for num in standalone:
            if num in common_sections and num not in matches:
                matches.append(num)
        
        return list(set(matches))
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from query."""
        # Remove common words
        stop_words = {"what", "is", "the", "of", "for", "in", "and", "or", "a", "an",
                      "to", "how", "can", "under", "about", "which", "क्या", "है", 
                      "के", "का", "की", "में", "और", "या", "एक", "कैसे"}
        
        words = re.findall(r'\b\w+\b', text.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        return keywords[:10]  # Return top 10 keywords
    
    def _reformulate_query(self, context: AgentContext) -> str:
        """Reformulate query for better retrieval."""
        parts = []
        
        # Add domain context
        if context.detected_domain:
            parts.append(f"[{context.detected_domain}]")
        
        # Add original query
        parts.append(context.query)
        
        # Add section context if found
        sections = [e["value"] for e in context.entities if e["type"] == "section"]
        if sections:
            parts.append(f"(Sections: {', '.join(sections)})")
        
        return " ".join(parts)
    
    def _classify_by_keywords(self, query: str) -> str:
        """Simple keyword-based domain classification as reliable fallback."""
        query_lower = query.lower()
        
        # Criminal law keywords (highest priority for legal queries)
        criminal_keywords = [
            'murder', 'culpable homicide', 'attempt to murder', 'assault', 'theft', 'robbery', 
            'burglary', 'rape', 'sexual assault', 'kidnapping', 'abduction', 'extortion',
            'cheating', 'fraud', 'forgery', 'defamation', 'trespass', 'hurt', 'grievous hurt',
            'wrongful restraint', 'wrongful confinement', 'criminal intimidation', 
            'mischief', 'rioting', 'unlawful assembly', 'affray', 'ipc', 'crpc', 'bns', 'bnss',
            'section 302', 'section 307', 'section 420', 'section 498a', 'bail', 'cognizable',
            'non-cognizable', 'bailable', 'non-bailable', 'fir', 'charge sheet', 'criminal case',
            'punishment', 'sentence', 'imprisonment', 'fine', 'accused', 'crime', 'offense'
        ]
        
        # Corporate/Company law keywords
        corporate_keywords = [
            'company', 'companies act', 'director', 'shareholder', 'board meeting',
            'annual general meeting', 'agm', 'egm', 'memorandum', 'articles of association',
            'incorporation', 'winding up', 'merger', 'acquisition', 'debenture', 'dividend',
            'company secretary', 'corporate governance', 'sebi', 'securities'
        ]
        
        # Traffic law keywords
        traffic_keywords = [
            'traffic', 'motor vehicle', 'driving license', 'challan', 'traffic violation',
            'speed limit', 'drunk driving', 'hit and run', 'motor vehicles act', 
            'traffic rules', 'red light', 'helmet', 'seat belt', 'vehicle'
        ]
        
        # IT/Cyber law keywords
        it_keywords = [
            'cyber', 'cybercrime', 'hacking', 'data breach', 'phishing', 'identity theft',
            'information technology act', 'it act', 'digital signature', 'electronic record',
            'cyber security', 'online fraud', 'social media', 'data protection'
        ]
        
        # Environment law keywords
        environment_keywords = [
            'environment', 'pollution', 'forest', 'wildlife', 'emission', 'waste',
            'environment protection act', 'air pollution', 'water pollution', 'noise pollution',
            'green tribunal', 'ngt', 'environmental clearance', 'biodiversity'
        ]
        
        # Constitutional law keywords
        constitutional_keywords = [
            'constitution', 'fundamental rights', 'directive principles', 'article',
            'amendment', 'supreme court', 'high court', 'writ', 'habeas corpus',
            'mandamus', 'certiorari', 'prohibition', 'quo warranto', 'judicial review'
        ]
        
        # Property law keywords
        property_keywords = [
            'property', 'land', 'immovable property', 'sale deed', 'transfer of property',
            'lease', 'mortgage', 'easement', 'possession', 'title', 'registration',
            'stamp duty', 'conveyance', 'gift deed', 'partition', 'inheritance'
        ]
        
        # Civil law keywords
        civil_keywords = [
            'contract', 'agreement', 'breach of contract', 'damages', 'specific performance',
            'injunction', 'suit', 'plaintiff', 'defendant', 'civil procedure code', 'cpc',
            'decree', 'appeal', 'revision', 'limitation', 'tort', 'negligence', 'nuisance'
        ]
        
        # Check each domain (order matters - more specific first)
        if any(keyword in query_lower for keyword in criminal_keywords):
            return "criminal"
        elif any(keyword in query_lower for keyword in corporate_keywords):
            return "corporate"
        elif any(keyword in query_lower for keyword in traffic_keywords):
            return "traffic"
        elif any(keyword in query_lower for keyword in it_keywords):
            return "it_cyber"
        elif any(keyword in query_lower for keyword in environment_keywords):
            return "environment"
        elif any(keyword in query_lower for keyword in constitutional_keywords):
            return "constitutional"
        elif any(keyword in query_lower for keyword in property_keywords):
            return "property"
        elif any(keyword in query_lower for keyword in civil_keywords):
            return "civil"
        
        # Default to criminal for legal queries, general otherwise
        return "criminal" if any(word in query_lower for word in ['law', 'legal', 'section', 'act', 'case']) else "general"
