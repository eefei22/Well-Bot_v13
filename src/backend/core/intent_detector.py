"""
Intent detection module with hybrid regex + LLM approach.
Provides fast-path regex patterns and LLM classifier fallback.
"""

import re
import time
import structlog
from typing import Dict, Any, Optional
from src.backend.services.deepseek import classify_intent

logger = structlog.get_logger()


class IntentDetector:
    """Hybrid intent detector with regex fast-paths and LLM fallback."""
    
    def __init__(self):
        # Compile regex patterns (case-insensitive, word-boundary anchored)
        self.patterns = {
            "journal.start": re.compile(r"\bstart\s+journal\b", re.IGNORECASE),
            "todo.list": re.compile(r"\bshow\s+(my\s+)?to-?do\b", re.IGNORECASE),
            "todo.add": re.compile(r"\badd\s+to-?do\b", re.IGNORECASE),
            "quote.get": re.compile(r"\b(give\s+me\s+a\s+)?quote\b", re.IGNORECASE),
            "meditation.play": re.compile(r"\b(start\s+)?meditation\b", re.IGNORECASE),
            "session.end": re.compile(r"\b(bye|talk\s+later|goodbye)\b", re.IGNORECASE),
        }
        
        logger.info("Intent detector initialized", patterns=list(self.patterns.keys()))
    
    def _mask_text(self, text: str, max_chars: int = 20) -> str:
        """Mask user text for logging (privacy-first)."""
        if len(text) <= max_chars:
            return f"[{len(text)} chars]"
        
        # Show first few chars + hash
        prefix = text[:max_chars//2]
        suffix = text[-max_chars//2:] if len(text) > max_chars else ""
        import hashlib
        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        return f"{prefix}...{suffix}[{text_hash}]"
    
    async def detect_intent(self, text: str) -> Dict[str, Any]:
        """
        Detect user intent using hybrid approach.
        
        Args:
            text: User input text
            
        Returns:
            Dict with intent, confidence, and args
        """
        start_time = time.time()
        masked_text = self._mask_text(text)
        
        # Try regex fast-paths first
        regex_result = self._try_regex_patterns(text)
        if regex_result:
            logger.info(
                "Intent detected via regex",
                intent=regex_result["intent"],
                confidence=regex_result["confidence"],
                duration_ms=int((time.time() - start_time) * 1000),
                masked_text=masked_text
            )
            return regex_result
        
        # Fallback to LLM classifier
        logger.info(
            "No regex match, using LLM classifier",
            masked_text=masked_text
        )
        
        try:
            llm_result = await classify_intent(text)
            
            logger.info(
                "Intent detected via LLM",
                intent=llm_result["intent"],
                confidence=llm_result["confidence"],
                duration_ms=int((time.time() - start_time) * 1000),
                masked_text=masked_text
            )
            
            return llm_result
            
        except Exception as e:
            logger.error(
                "LLM classification failed, defaulting to small_talk",
                error=str(e),
                duration_ms=int((time.time() - start_time) * 1000),
                masked_text=masked_text
            )
            
            # Fail-open to small_talk
            return {
                "intent": "small_talk",
                "confidence": 0.3,
                "args": {}
            }
    
    def _try_regex_patterns(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Try regex patterns for fast-path intent detection.
        
        Args:
            text: User input text
            
        Returns:
            Intent result if pattern matches, None otherwise
        """
        for intent_name, pattern in self.patterns.items():
            if pattern.search(text):
                # Special handling for todo.add - check if content follows verb
                if intent_name == "todo.add":
                    # Look for content after "add to-do" or "add todo"
                    add_match = re.search(r"\badd\s+to-?do\s+(.+)", text, re.IGNORECASE)
                    if not add_match or not add_match.group(1).strip():
                        # No content after verb, fallback to classifier
                        continue
                
                # Extract args based on intent
                args = self._extract_args_from_text(text, intent_name)
                
                return {
                    "intent": intent_name,
                    "confidence": 0.95,  # High confidence for regex matches
                    "args": args
                }
        
        return None
    
    def _extract_args_from_text(self, text: str, intent: str) -> Dict[str, Any]:
        """
        Extract relevant arguments from text based on intent.
        
        Args:
            text: User input text
            intent: Detected intent
            
        Returns:
            Dict of extracted arguments
        """
        args = {}
        
        if intent == "todo.add":
            # Extract todo content
            add_match = re.search(r"\badd\s+to-?do\s+(.+)", text, re.IGNORECASE)
            if add_match:
                args["content"] = add_match.group(1).strip()
        
        elif intent == "gratitude.add":
            # Extract gratitude content
            gratitude_match = re.search(r"\b(gratitude|grateful|thankful)\s+(.+)", text, re.IGNORECASE)
            if gratitude_match:
                args["content"] = gratitude_match.group(2).strip()
        
        elif intent == "journal.start":
            # Extract journal topic if mentioned
            topic_match = re.search(r"\babout\s+(.+)", text, re.IGNORECASE)
            if topic_match:
                args["topic"] = topic_match.group(1).strip()
        
        elif intent == "todo.complete":
            # Extract todo item to complete
            complete_match = re.search(r"\b(complete|finish|done)\s+(.+)", text, re.IGNORECASE)
            if complete_match:
                args["item"] = complete_match.group(2).strip()
        
        elif intent == "todo.delete":
            # Extract todo item to delete
            delete_match = re.search(r"\b(delete|remove)\s+(.+)", text, re.IGNORECASE)
            if delete_match:
                args["item"] = delete_match.group(2).strip()
        
        return args


# Global detector instance
_detector: Optional[IntentDetector] = None


def get_intent_detector() -> IntentDetector:
    """Get the global intent detector instance."""
    global _detector
    if _detector is None:
        _detector = IntentDetector()
    return _detector


async def detect_intent(text: str) -> Dict[str, Any]:
    """Convenience function for intent detection."""
    detector = get_intent_detector()
    return await detector.detect_intent(text)
