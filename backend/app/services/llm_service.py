"""
NyayGuru AI Pro - LLM Service
Local Ollama SLM (default) with opt-in Groq/Gemini/OpenAI providers.
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


class LLMUnavailableError(RuntimeError):
    """Raised when no configured LLM provider could produce output."""


class LLMService:
    """LLM generation service. Local Ollama SLM is the default; cloud providers are opt-in."""
    
    CLOUD_PROVIDERS = ("groq", "gemini", "openai")
    
    def __init__(self):
        self.gemini_api_key = settings.gemini_api_key
        self.gemini_model = settings.gemini_model
        self.groq_api_key = settings.groq_api_key
        self.groq_model = settings.groq_model
        self.openai_api_key = settings.openai_api_key
        self.openai_model = settings.openai_model
        self._initialized = False
        self.provider = None
        self.ollama = None
        self.cloud_provider = None
    
    @property
    def model_name(self) -> Optional[str]:
        if self.provider == "ollama" and self.ollama:
            return self.ollama.model_name
        return {"groq": self.groq_model, "gemini": self.gemini_model,
                "openai": self.openai_model}.get(self.provider)
    
    @property
    def last_usage(self) -> Dict[str, Any]:
        return self.ollama.last_usage if self.provider == "ollama" and self.ollama else {}
    
    def _configured_cloud_provider(self) -> Optional[str]:
        keys = {"groq": self.groq_api_key, "gemini": self.gemini_api_key, "openai": self.openai_api_key}
        if settings.llm_provider in self.CLOUD_PROVIDERS:
            return settings.llm_provider if keys[settings.llm_provider] else None
        return next((p for p in self.CLOUD_PROVIDERS if keys[p]), None)
    
    async def initialize(self):
        """Initialize LLM provider. Cloud is used only if explicitly selected or allowed as fallback."""
        if self._initialized:
            return
        
        self.cloud_provider = self._configured_cloud_provider()
        
        if settings.llm_provider == "ollama":
            from app.services.ollama_service import OllamaService
            self.ollama = OllamaService()
            try:
                await self.ollama.initialize()
                if not self.ollama.model_available:
                    raise LLMUnavailableError(f"Ollama model '{self.ollama.model_name}' not found")
                self.provider = "ollama"
                logger.info(f"[LLM] provider=ollama model={self.ollama.model_name}")
            except Exception as e:
                logger.error(f"[LLM] Local SLM unavailable: {e}")
                if settings.allow_cloud_fallback and self.cloud_provider:
                    self.provider = self.cloud_provider
                    logger.warning(f"[LLM] Falling back to cloud provider: {self.provider}")
                else:
                    self.provider = None
        else:
            self.provider = self.cloud_provider
            logger.info(f"[LLM] provider={self.provider} (cloud explicitly configured)")
        
        if not self.provider:
            logger.warning("[LLM] No LLM provider available - responses will be retrieval-only")
        
        self._initialized = True
    
    def get_status(self) -> str:
        """Get current LLM provider status."""
        if not self._initialized:
            return "not_initialized"
        return self.provider or "none"
    
    async def _with_fallback(self, local_call, cloud_call):
        """Run local SLM call; use the cloud only when explicitly allowed."""
        if self.provider == "ollama":
            try:
                return await local_call()
            except Exception as e:
                logger.error(f"[OLLAMA] generation failed: {e}")
                if not (settings.allow_cloud_fallback and self.cloud_provider):
                    raise LLMUnavailableError(str(e)) from e
                logger.warning(f"[LLM] Cloud fallback to {self.cloud_provider}")
                return await cloud_call(self.cloud_provider)
        if self.provider in self.CLOUD_PROVIDERS:
            return await cloud_call(self.provider)
        raise LLMUnavailableError("No LLM provider configured")
    
    async def generate(self, prompt: str, max_tokens: int = 512,
                      temperature: float = 0.1) -> str:
        """Generate text from a single prompt."""
        async def local():
            return await self.ollama.generate(prompt, temperature=temperature, max_tokens=max_tokens)
        
        async def cloud(provider):
            fn = {"gemini": self._gemini_generate, "groq": self._groq_generate,
                  "openai": self._openai_generate}[provider]
            return await fn(prompt, max_tokens, temperature)
        
        return await self._with_fallback(local, cloud)

    async def generate_chat(self, messages: List[Dict[str, str]], 
                           max_tokens: int = 512, 
                           temperature: float = 0.1) -> str:
        """Generate response for a list of chat messages."""
        async def local():
            return await self.ollama.generate_chat(messages, temperature=temperature, max_tokens=max_tokens)
        
        return await self._with_fallback(
            local, lambda provider: self._cloud_chat(provider, messages, max_tokens, temperature)
        )
    
    async def _cloud_chat(self, provider: str, messages: List[Dict[str, str]],
                          max_tokens: int, temperature: float) -> str:
        """OpenAI-compatible chat call to an explicitly enabled cloud provider."""
        base, key, model = {
            "gemini": (GEMINI_API_BASE, self.gemini_api_key, self.gemini_model),
            "groq": (GROQ_API_BASE, self.groq_api_key, self.groq_model),
            "openai": ("https://api.openai.com/v1", self.openai_api_key, self.openai_model),
        }[provider]
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{base}/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"model": model, "messages": messages,
                      "max_tokens": max_tokens, "temperature": temperature}
            )
        if response.status_code != 200:
            raise LLMUnavailableError(f"{provider} chat API error {response.status_code}: {response.text[:200]}")
        return response.json()["choices"][0]["message"]["content"]
    
    async def _gemini_generate(self, prompt: str, max_tokens: int, 
                             temperature: float) -> str:
        """Generate using Gemini API with retry on transient errors."""
        max_retries = 2
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
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
                            return self._generate_fallback_response(prompt)
                    elif response.status_code in (429, 503) and attempt < max_retries - 1:
                        wait_time = 2
                        logger.warning(f"Gemini API returned {response.status_code}, retrying in {wait_time}s")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"Gemini API error: {response.status_code} - {response.text[:200]}")
                        return self._generate_fallback_response(prompt)
                        
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Gemini attempt {attempt + 1} failed: {e}, retrying...")
                    await asyncio.sleep(2)
                else:
                    logger.error(f"Gemini failed after {max_retries} attempts: {e}")
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
        """Controlled message when a cloud provider fails (never a fabricated legal answer)."""
        logger.warning("[LLM] Generation unavailable - returning controlled message")
        return ("The legal language model is currently unavailable, so I cannot generate a "
                "reliable answer. Please try again later.")


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
1. ALWAYS cite specific sections, subsections, and document filenames (if applicable) for EVERY claim you make.
2. Reference relevant case law with proper citations and year.
3. Explain legal concepts in simple, accessible language.
4. YOU MUST ALWAYS provide both the old IPC section AND the new BNS section references side-by-side for every criminal law mentioned (e.g. "Section 302 of IPC (now Section 103 of BNS)").
5. Include a disclaimer that the information is for educational purposes.
6. Be accurate and avoid speculation.
7. Recommend consulting a qualified legal professional for specific matters.

Format your responses with:
- Clear headings and subheadings using ** for bold
- Bullet points for key information
- Bold text for important terms
- Proper legal citations for every rule mentioned
- A dedicated "Citations & Sources" section at the end of your response"""


# Singleton instance
_llm_service: Optional[LLMService] = None


async def get_llm_service() -> LLMService:
    """Get or create LLM service singleton."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
        await _llm_service.initialize()
    return _llm_service
