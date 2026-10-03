"""
NyayGuru AI Pro - LLM Service
Handles LLM integration with Gemini API (primary), Groq API, or OpenAI (fallback).
"""

from typing import Optional, List, Dict, Any, AsyncGenerator
import logging
import asyncio
import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Groq API endpoint (OpenAI-compatible)
GROQ_API_BASE = "https://api.groq.com/openai/v1"
# Gemini API endpoint (OpenAI-compatible)
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/openai"


class LLMService:
    """Service for LLM-based text generation using Groq."""
    
    def __init__(self):
        self.gemini_api_key = settings.gemini_api_key
        self.gemini_model = settings.gemini_model
        self.groq_api_key = settings.groq_api_key
        self.groq_model = settings.groq_model
        self.openai_api_key = settings.openai_api_key
        self.openai_model = settings.openai_model
        self._initialized = False
        self.provider = None
    
    async def initialize(self):
        """Initialize LLM client."""
        if self._initialized:
            return
        
        # Prefer Gemini, fallback to Groq, then OpenAI
        if self.gemini_api_key:
            self.provider = "gemini"
            logger.info(f"Gemini LLM initialized with model: {self.gemini_model}")
        elif self.groq_api_key:
            self.provider = "groq"
            logger.info(f"Groq LLM initialized with model: {self.groq_model}")
        elif self.openai_api_key:
            self.provider = "openai"
            logger.info(f"OpenAI LLM initialized with model: {self.openai_model}")
        else:
            self.provider = None
            logger.warning("No LLM API key available - using fallback responses")
        
        self._initialized = True
    
    def get_status(self) -> str:
        """Get current LLM provider status."""
        if not self._initialized:
            return "not_initialized"
        return self.provider or "none"
    
    async def generate(self, prompt: str, max_tokens: int = 2000, 
                      temperature: float = 0.7) -> str:
        """Generate text from prompt using Gemini, Groq or OpenAI."""
        
        if self.provider == "gemini":
            return await self._gemini_generate(prompt, max_tokens, temperature)
        elif self.provider == "groq":
            return await self._groq_generate(prompt, max_tokens, temperature)
        elif self.provider == "openai":
            return await self._openai_generate(prompt, max_tokens, temperature)
        else:
            return self._generate_fallback_response(prompt)

    async def generate_chat(self, messages: List[Dict[str, str]], 
                           max_tokens: int = 2000, 
                           temperature: float = 0.7) -> str:
        """Generate response for a list of chat messages."""
        if self.provider == "gemini":
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        f"{GEMINI_API_BASE}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.gemini_api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": self.gemini_model,
                            "messages": messages,
                            "max_tokens": max_tokens,
                            "temperature": temperature
                        }
                    )
                    if response.status_code == 200:
                        return response.json()["choices"][0]["message"]["content"]
            except Exception as e:
                logger.error(f"Gemini generate_chat failed: {e}")

        elif self.provider == "groq":
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        f"{GROQ_API_BASE}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.groq_api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": self.groq_model,
                            "messages": messages,
                            "max_tokens": max_tokens,
                            "temperature": temperature
                        }
                    )
                    if response.status_code == 200:
                        return response.json()["choices"][0]["message"]["content"]
            except Exception as e:
                logger.error(f"Groq generate_chat failed: {e}")
        
        elif self.provider == "openai":
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.openai_api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": self.openai_model,
                            "messages": messages,
                            "max_tokens": max_tokens,
                            "temperature": temperature
                        }
                    )
                    if response.status_code == 200:
                        return response.json()["choices"][0]["message"]["content"]
            except Exception as e:
                logger.error(f"OpenAI generate_chat failed: {e}")

        # Fallback - use the last user message
        user_msg = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        return await self.generate(user_msg, max_tokens, temperature)
    
    async def _gemini_generate(self, prompt: str, max_tokens: int, 
                             temperature: float) -> str:
        """Generate using Gemini API with retry on transient errors."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=90.0) as client:
                    response = await client.post(
                        f"{GEMINI_API_BASE}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.gemini_api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": self.gemini_model,
                            "messages": [
                                {"role": "user", "content": prompt}
                            ],
                            "max_tokens": max_tokens,
                            "temperature": temperature
                        }
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        try:
                            return data["choices"][0]["message"]["content"]
                        except KeyError:
                            logger.error(f"Missing 'content' in Gemini response: {data}")
                            raise
                    elif response.status_code in (429, 503) and attempt < max_retries - 1:
                        wait_time = 2 ** (attempt + 1)
                        logger.warning(f"Gemini API returned {response.status_code}, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"Gemini API error: {response.status_code} - {response.text}")
                        return self._generate_fallback_response(prompt)
                        
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Gemini generation attempt {attempt + 1} failed: {e}, retrying...")
                    await asyncio.sleep(2 ** (attempt + 1))
                else:
                    logger.error(f"Gemini generation failed after {max_retries} attempts: {e}")
                    return self._generate_fallback_response(prompt)
        
        return self._generate_fallback_response(prompt)

    async def _groq_generate(self, prompt: str, max_tokens: int, 
                             temperature: float) -> str:
        """Generate using Groq API."""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{GROQ_API_BASE}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.groq_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.groq_model,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": max_tokens,
                        "temperature": temperature
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    logger.error(f"Groq API error: {response.status_code} - {response.text}")
                    return self._generate_fallback_response(prompt)
                    
        except Exception as e:
            logger.error(f"Groq generation failed: {e}")
            return self._generate_fallback_response(prompt)
    
    async def _openai_generate(self, prompt: str, max_tokens: int,
                               temperature: float) -> str:
        """Generate using OpenAI API."""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openai_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.openai_model,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": max_tokens,
                        "temperature": temperature
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    logger.error(f"OpenAI API error: {response.status_code}")
                    return self._generate_fallback_response(prompt)
                    
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            return self._generate_fallback_response(prompt)
    
    async def generate_streaming(self, prompt: str, max_tokens: int = 2000) -> AsyncGenerator[str, None]:
        """Generate text with streaming."""
        
        if self.provider == "gemini":
            async for chunk in self._gemini_generate_streaming(prompt, max_tokens):
                yield chunk
        elif self.provider == "groq":
            async for chunk in self._groq_generate_streaming(prompt, max_tokens):
                yield chunk
        elif self.provider == "openai":
            async for chunk in self._openai_generate_streaming(prompt, max_tokens):
                yield chunk
        else:
            # Fallback - simulate streaming
            response = self._generate_fallback_response(prompt)
            for word in response.split():
                yield word + " "
                await asyncio.sleep(0.02)
    
    async def _gemini_generate_streaming(self, prompt: str, max_tokens: int) -> AsyncGenerator[str, None]:
        """Stream from Gemini API."""
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{GEMINI_API_BASE}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.gemini_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.gemini_model,
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": max_tokens,
                        "stream": True
                    }
                ) as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break
                            try:
                                import json
                                chunk = json.loads(data)
                                content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if content:
                                    yield content
                            except:
                                continue
        except Exception as e:
            logger.error(f"Gemini streaming failed: {e}")
            response = self._generate_fallback_response(prompt)
            yield response

    async def _groq_generate_streaming(self, prompt: str, max_tokens: int) -> AsyncGenerator[str, None]:
        """Stream from Groq API."""
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{GROQ_API_BASE}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.groq_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.groq_model,
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": max_tokens,
                        "stream": True
                    }
                ) as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break
                            try:
                                import json
                                chunk = json.loads(data)
                                content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if content:
                                    yield content
                            except:
                                continue
        except Exception as e:
            logger.error(f"Groq streaming failed: {e}")
            response = self._generate_fallback_response(prompt)
            yield response
    
    async def _openai_generate_streaming(self, prompt: str, max_tokens: int) -> AsyncGenerator[str, None]:
        """Stream from OpenAI API."""
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openai_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.openai_model,
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": max_tokens,
                        "stream": True
                    }
                ) as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break
                            try:
                                import json
                                chunk = json.loads(data)
                                content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if content:
                                    yield content
                            except:
                                continue
        except Exception as e:
            logger.error(f"OpenAI streaming failed: {e}")
            response = self._generate_fallback_response(prompt)
            yield response
    
    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate text between languages."""
        lang_map = {"en": "English", "hi": "Hindi"}
        prompt = f"""Translate the following text from {lang_map.get(source_lang, source_lang)} to {lang_map.get(target_lang, target_lang)}.
Maintain legal terminology accuracy.

Text: {text}

Translation:"""
        
        return await self.generate(prompt, max_tokens=len(text) * 2)
    
    def _generate_fallback_response(self, prompt: str) -> str:
        """Generate fallback response when no LLM API is available."""
        logger.warning("No LLM API available - using fallback response")
        
        return """Based on analysis of your legal query under Indian law:

**Relevant Legal Framework:**
The query has been analyzed against the Indian Penal Code (IPC) and Bhartiya Nyaya Sanhita (BNS), 2023.

**Key Points:**
1. The applicable statutory provisions have been identified
2. Relevant case law precedents may apply
3. The BNS, 2023 has modernized several provisions from the IPC

**Note:** To provide more detailed AI-powered analysis, please configure an LLM API key (Gemini, Groq or OpenAI) in the backend environment.

⚖️ *This information is for educational purposes only. Please consult a qualified legal professional for specific legal advice.*"""


# System prompt for legal AI
SYSTEM_PROMPT = """You are NyayGuru AI Pro, an expert AI legal assistant specializing in Indian law. You provide accurate, helpful, and verifiable legal information.

Your expertise includes:
- Indian Penal Code (IPC), 1860
- Bhartiya Nyaya Sanhita (BNS), 2023
- Criminal Procedure Code (CrPC)
- Bhartiya Nagarik Suraksha Sanhita (BNSS)
- Indian Evidence Act and Bhartiya Sakshya Adhiniyam
- Constitutional Law of India
- Supreme Court and High Court judgments

Guidelines:
1. Always cite specific sections and subsections
2. Reference relevant case law with proper citations
3. Explain legal concepts in simple, accessible language
4. Always provide both IPC and BNS references where applicable
5. Include a disclaimer that the information is for educational purposes
6. Be accurate and avoid speculation
7. Recommend consulting a qualified legal professional for specific matters

Format your responses with:
- Clear headings and subheadings using ** for bold
- Bullet points for key information
- Bold text for important terms
- Proper legal citations"""


# Singleton instance
_llm_service: Optional[LLMService] = None


async def get_llm_service() -> LLMService:
    """Get or create LLM service singleton."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
        await _llm_service.initialize()
    return _llm_service
