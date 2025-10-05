"""
DeepSeek LLM service adapter using OpenAI SDK with base_url override.
Provides streaming and non-streaming chat completion with intent classification.
"""

import os
import hashlib
import asyncio
import structlog
from typing import Dict, Any, List, Optional, AsyncIterator, Union
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionChunk
import time
from datetime import datetime, timezone

logger = structlog.get_logger()


class DeepSeekClient:
    """DeepSeek LLM client using OpenAI SDK with base_url override."""
    
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY environment variable is required")
        
        # Locked defaults per plan
        self.temperature = float(os.getenv("WB_LLM_TEMPERATURE", "0.3"))
        self.max_tokens = int(os.getenv("WB_LLM_MAX_TOKENS", "250"))
        self.streaming_enabled = os.getenv("WB_LLM_STREAMING", "true").lower() == "true"
        
        # Initialize OpenAI client with DeepSeek base URL
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=10.0,  # Total timeout ≤10s per plan
            max_retries=1  # 1 retry on 5xx per plan
        )
        
        logger.info(
            "DeepSeek client initialized",
            base_url=self.base_url,
            model=self.model,
            streaming_enabled=self.streaming_enabled,
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )
    
    def _mask_text(self, text: str, max_chars: int = 20) -> str:
        """Mask user text for logging (privacy-first)."""
        if len(text) <= max_chars:
            return f"[{len(text)} chars]"
        
        # Show first few chars + hash
        prefix = text[:max_chars//2]
        suffix = text[-max_chars//2:] if len(text) > max_chars else ""
        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        return f"{prefix}...{suffix}[{text_hash}]"
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        stream: Optional[bool] = None
    ) -> Union[str, AsyncIterator[str]]:
        """
        Generate chat completion with streaming support.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Override default max tokens
            stream: Override streaming setting
            
        Returns:
            str: Non-streaming response text
            AsyncIterator[str]: Streaming response chunks
        """
        start_time = time.time()
        tokens_used = 0
        stream_fallback = False
        
        # Use provided values or defaults
        tokens_limit = max_tokens or self.max_tokens
        use_streaming = stream if stream is not None else self.streaming_enabled
        
        masked_messages = [
            {
                "role": msg["role"],
                "content": self._mask_text(msg["content"]) if msg["role"] == "user" else f"[{len(msg['content'])} chars]"
            }
            for msg in messages
        ]
        
        logger.info(
            "Starting chat completion",
            messages=masked_messages,
            model=self.model,
            max_tokens=tokens_limit,
            streaming=use_streaming,
            temperature=self.temperature
        )
        
        try:
            if use_streaming:
                return await self._stream_completion(
                    messages, tokens_limit, start_time, tokens_used
                )
            else:
                return await self._non_streaming_completion(
                    messages, tokens_limit, start_time, tokens_used
                )
                
        except Exception as e:
            logger.error(
                "Chat completion failed",
                error=str(e),
                error_type=type(e).__name__,
                duration_ms=int((time.time() - start_time) * 1000)
            )
            raise
    
    async def _stream_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int,
        start_time: float,
        tokens_used: int
    ) -> AsyncIterator[str]:
        """Handle streaming completion with buffering."""
        first_chunk_received = False
        first_chunk_content = ""
        buffer = []
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=self.temperature,
                stream=True
            )
            
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    buffer.append(content)
                    
                    # Buffer first chunk for consistent diagnostics
                    if not first_chunk_received:
                        first_chunk_content = content
                        first_chunk_received = True
                        logger.info(
                            "First chunk buffered",
                            first_chunk_length=len(content),
                            duration_ms=int((time.time() - start_time) * 1000)
                        )
                    
                    yield content
            
            # Log completion
            total_content = "".join(buffer)
            tokens_used = len(total_content.split())  # Rough token estimate
            
            logger.info(
                "Streaming completion finished",
                total_chunks=len(buffer),
                total_length=len(total_content),
                estimated_tokens=tokens_used,
                duration_ms=int((time.time() - start_time) * 1000)
            )
            
        except Exception as e:
            logger.warning(
                "Streaming failed, attempting non-streaming fallback",
                error=str(e),
                stream_fallback=True
            )
            
            # Fail-open to non-streaming
            try:
                result = await self._non_streaming_completion(
                    messages, max_tokens, start_time, tokens_used
                )
                # Yield the entire result as a single chunk
                yield result
            except Exception as fallback_error:
                logger.error(
                    "Non-streaming fallback also failed",
                    error=str(fallback_error)
                )
                raise fallback_error
    
    async def _non_streaming_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int,
        start_time: float,
        tokens_used: int
    ) -> str:
        """Handle non-streaming completion."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=self.temperature,
            stream=False
        )
        
        content = response.choices[0].message.content
        tokens_used = response.usage.total_tokens if response.usage else len(content.split())
        
        logger.info(
            "Non-streaming completion finished",
            response_length=len(content),
            tokens_used=tokens_used,
            duration_ms=int((time.time() - start_time) * 1000)
        )
        
        return content
    
    async def classify_intent(self, text: str) -> Dict[str, Any]:
        """
        Classify user intent using LLM.
        
        Args:
            text: User input text
            
        Returns:
            Dict with intent, confidence, and args
        """
        start_time = time.time()
        
        classifier_prompt = """You are an intent classifier for a wellness assistant. Analyze the user's input and determine their intent.

Available intents:
- small_talk: General conversation, questions, greetings, casual chat
- journal.start: Starting a journaling session
- gratitude.add: Adding a gratitude entry
- todo.add: Adding a to-do item
- todo.list: Showing to-do list
- todo.complete: Completing a to-do item
- todo.delete: Deleting a to-do item
- quote.get: Getting a spiritual quote
- meditation.play: Starting meditation
- session.end: Ending the session

Respond with JSON only in this exact format:
{"intent": "intent_name", "confidence": 0.0-1.0, "args": {"key": "value"}}

User input: {text}"""

        messages = [
            {"role": "system", "content": classifier_prompt.format(text=text)},
            {"role": "user", "content": text}
        ]
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=100,  # Small response for classification
                temperature=0.1,  # Low temperature for consistent classification
                stream=False
            )
            
            content = response.choices[0].message.content.strip()
            
            # Parse JSON response
            import json
            try:
                result = json.loads(content)
                
                # Validate required fields
                if not all(key in result for key in ["intent", "confidence", "args"]):
                    raise ValueError("Missing required fields in classifier response")
                
                # Ensure confidence is float
                result["confidence"] = float(result["confidence"])
                
                logger.info(
                    "Intent classified",
                    intent=result["intent"],
                    confidence=result["confidence"],
                    args=result["args"],
                    duration_ms=int((time.time() - start_time) * 1000),
                    masked_text=self._mask_text(text)
                )
                
                return result
                
            except json.JSONDecodeError as e:
                logger.error(
                    "Failed to parse classifier JSON",
                    response=content,
                    error=str(e)
                )
                # Fallback to small_talk
                return {
                    "intent": "small_talk",
                    "confidence": 0.5,
                    "args": {}
                }
                
        except Exception as e:
            logger.error(
                "Intent classification failed",
                error=str(e),
                duration_ms=int((time.time() - start_time) * 1000),
                masked_text=self._mask_text(text)
            )
            # Fail-open to small_talk
            return {
                "intent": "small_talk",
                "confidence": 0.3,
                "args": {}
            }


# Global client instance
_client: Optional[DeepSeekClient] = None


def get_deepseek_client() -> DeepSeekClient:
    """Get the global DeepSeek client instance."""
    global _client
    if _client is None:
        _client = DeepSeekClient()
    return _client


async def chat_completion(
    messages: List[Dict[str, str]],
    max_tokens: Optional[int] = None,
    stream: Optional[bool] = None
) -> Union[str, AsyncIterator[str]]:
    """Convenience function for chat completion."""
    client = get_deepseek_client()
    return await client.chat_completion(messages, max_tokens, stream)


async def classify_intent(text: str) -> Dict[str, Any]:
    """Convenience function for intent classification."""
    client = get_deepseek_client()
    return await client.classify_intent(text)
