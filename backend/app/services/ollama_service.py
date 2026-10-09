"""
NyayaShastra - Local LLM Service via Ollama (Phase 3: The Brain)
Runs Llama-3-8B-Instruct (4-bit quantized) locally on your i7-13620H
No cloud APIs, no rate limits, full privacy
"""

import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
import json
import httpx

logger = logging.getLogger(__name__)


class OllamaService:
    """
    Service for interacting with locally running Ollama LLM (MEMORY-OPTIMIZED).
    Ollama provides a simple API for running LLMs on your machine.
    """
    
    # Generation parameters (GPU/Metal offload is left to Ollama; num_ctx comes from settings)
    DEFAULT_OPTIONS = {
        "num_predict": 512,
        "repeat_penalty": 1.15,  # 1.1 let the 3B model loop until num_predict on multi-source answers
        "repeat_last_n": 256,
        "temperature": 0.1,
        "top_k": 40,
        "top_p": 0.9,
    }
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None
    ):
        """Initialize Ollama service; defaults come from settings (OLLAMA_* env vars)."""
        from app.config import settings
        self.model_name = model_name or settings.ollama_model
        self.base_url = base_url or settings.ollama_base_url
        self.timeout = timeout or settings.ollama_timeout
        self.num_ctx = settings.ollama_num_ctx
        self.model_available = False
        self.last_usage: Dict[str, Any] = {}
        self._initialized = False
        
    async def initialize(self):
        """Check if Ollama is running and model is available."""
        if self._initialized:
            return
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Check if Ollama is running
                response = await client.get(f"{self.base_url}/api/tags")
                
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    model_names = [m.get("name") for m in models]
                    
                    logger.info(f"✅ Ollama is running at {self.base_url}")
                    logger.info(f"Available models: {', '.join(model_names)}")
                    
                    # Check if our model is available
                    if not any(name == self.model_name or name.split(':')[0] == self.model_name for name in model_names):
                        logger.warning(
                            f"⚠️  Model '{self.model_name}' not found. "
                            f"Download it with: ollama pull {self.model_name}"
                        )
                    else:
                        logger.info(f"✅ Model '{self.model_name}' is ready")
                        self.model_available = True

                    self._initialized = True
                else:
                    raise Exception(f"Ollama returned status {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            logger.error(
                "Make sure Ollama is running:\n"
                "1. Install Ollama: https://ollama.ai/download\n"
                "2. Start Ollama: ollama serve\n"
                f"3. Pull model: ollama pull {self.model_name}"
            )
            raise
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 1024,
        stream: bool = False
    ) -> str:
        """
        Generate text using Ollama.
        
        Args:
            prompt: User prompt
            system_prompt: System instructions
            temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            
        Returns:
            Generated text
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Build messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            # Prepare request with memory-safe options
            options = self.DEFAULT_OPTIONS.copy()
            options.update({
                "temperature": temperature,
                "num_predict": min(max_tokens, 1024),
                "num_ctx": self.num_ctx,
            })
            
            payload = {
                "model": self.model_name,
                "messages": messages,
                "stream": stream,
                "options": options
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    self.last_usage = {
                        "prompt_tokens": result.get("prompt_eval_count", 0),
                        "completion_tokens": result.get("eval_count", 0),
                        "total_duration_s": round(result.get("total_duration", 0) / 1e9, 3),
                    }
                    logger.info(f"[OLLAMA] model={self.model_name} {self.last_usage}")
                    return result.get("message", {}).get("content", "")
                else:
                    raise Exception(f"Ollama API returned status {response.status_code}: {response.text}")
                    
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise
    
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 1024
    ) -> AsyncGenerator[str, None]:
        """
        Generate text with streaming (for real-time UI updates).
        
        Args:
            prompt: User prompt
            system_prompt: System instructions
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Yields:
            Text chunks as they are generated
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Build messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            # Prepare request
            payload = {
                "model": self.model_name,
                "messages": messages,
                "stream": True,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                }
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json=payload
                ) as response:
                    if response.status_code != 200:
                        raise Exception(f"Ollama API returned status {response.status_code}")
                    
                    async for line in response.aiter_lines():
                        if line.strip():
                            try:
                                chunk = json.loads(line)
                                content = chunk.get("message", {}).get("content", "")
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                continue
                                
        except Exception as e:
            logger.error(f"Streaming generation failed: {e}")
            raise
    
    async def generate_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 512
    ) -> str:
        """
        Generate chat response from message history.
        Compatible with LLM service interface.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Prepare request with memory-safe options
            options = self.DEFAULT_OPTIONS.copy()
            options.update({
                "temperature": temperature,
                "num_predict": min(max_tokens, 1024),
                "num_ctx": self.num_ctx,
            })
            
            payload = {
                "model": self.model_name,
                "messages": messages,
                "stream": False,
                "options": options
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    self.last_usage = {
                        "prompt_tokens": result.get("prompt_eval_count", 0),
                        "completion_tokens": result.get("eval_count", 0),
                        "total_duration_s": round(result.get("total_duration", 0) / 1e9, 3),
                    }
                    logger.info(f"[OLLAMA] model={self.model_name} {self.last_usage}")
                    return result.get("message", {}).get("content", "")
                else:
                    raise Exception(f"Ollama API returned status {response.status_code}: {response.text}")
                    
        except Exception as e:
            logger.error(f"Chat generation failed: {e}")
            raise
    
    async def generate_with_context(
        self,
        query: str,
        contexts: List[Dict[str, Any]],
        system_instruction: str = None,
        temperature: float = 0.1
    ) -> str:
        """
        Generate response with retrieved contexts (RAG pipeline).
        
        Args:
            query: User query
            contexts: Retrieved context documents
            system_instruction: Custom system instruction
            temperature: Sampling temperature
            
        Returns:
            Generated answer
        """
        # Default system instruction for legal RAG
        if system_instruction is None:
            system_instruction = """You are NyayaShastra, an expert Indian legal AI assistant.

Your role:
- Provide accurate legal information based ONLY on the provided context
- Cite specific sections and laws
- Use clear, professional language
- Support both English and Hindi (Hinglish)
- If the answer is not in the context, clearly state "I don't have enough information"

Critical rules:
- NEVER make up legal information
- ALWAYS cite sources (section numbers, act names)
- Be precise and factual
- Avoid speculation or opinions"""
        
        # Build context text
        context_text = "\n\n".join([
            f"[Context {i+1}]\n{ctx.get('content', '')}\n"
            f"Source: {ctx.get('metadata', {}).get('source', 'N/A')}\n"
            f"Sections: {ctx.get('metadata', {}).get('sections', 'N/A')}"
            for i, ctx in enumerate(contexts[:5])  # Use top 5 contexts
        ])
        
        # Build prompt
        prompt = f"""Using ONLY the following legal contexts, answer the user's question.

CONTEXTS:
{context_text}

USER QUESTION: {query}

INSTRUCTIONS:
1. Answer based ONLY on the provided contexts
2. Cite specific sections and laws
3. If the answer is not in the contexts, say "I don't have sufficient information"
4. Be precise and professional

YOUR ANSWER:"""
        
        return await self.generate(
            prompt=prompt,
            system_prompt=system_instruction,
            temperature=temperature,
            max_tokens=1024
        )


# Singleton instance
_ollama_service: Optional[OllamaService] = None


async def get_ollama_service() -> OllamaService:
    """Get or create the singleton Ollama service."""
    global _ollama_service
    if _ollama_service is None:
        _ollama_service = OllamaService()
        await _ollama_service.initialize()
    return _ollama_service


async def is_ollama_available() -> bool:
    """Check if Ollama is available and running."""
    try:
        service = OllamaService()
        await service.initialize()
        return True
    except:
        return False


if __name__ == "__main__":
    import asyncio
    
    async def test_ollama():
        """Test Ollama service."""
        try:
            print("🧪 Testing Ollama service...\n")
            
            service = await get_ollama_service()
            
            # Test simple generation
            print("Test 1: Simple generation")
            query = "What is IPC Section 302?"
            print(f"Query: {query}")
            
            response = await service.generate(
                prompt=query,
                system_prompt="You are a helpful legal assistant. Be concise.",
                temperature=0.1
            )
            
            print(f"Response: {response}\n")
            
            # Test RAG generation
            print("Test 2: RAG generation with context")
            contexts = [
                {
                    "content": "Section 302 IPC: Punishment for murder. Whoever commits murder shall be punished with death or imprisonment for life, and shall also be liable to fine.",
                    "metadata": {"source": "IPC.pdf", "sections": "302"}
                }
            ]
            
            query = "What is the punishment for murder?"
            print(f"Query: {query}")
            
            response = await service.generate_with_context(
                query=query,
                contexts=contexts
            )
            
            print(f"Response: {response}\n")
            
            print("✅ All tests passed!")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
    
    asyncio.run(test_ollama())
