"""Ollama LLM provider with streaming support."""

import logging
import sys
from typing import List, Dict, Any, Optional, Generator
import ollama

from ..settings import settings

logger = logging.getLogger(__name__)


class OllamaProvider:
    """Ollama LLM provider for local inference with streaming support."""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        Initialize Ollama provider.
        
        Args:
            base_url: Ollama server URL (defaults to settings)
            model: Model name (defaults to settings)
        """
        self.base_url = base_url or settings.ollama.base_url
        self.model = model or settings.ollama.model
        
        # Configure ollama client
        self.client = ollama.Client(host=self.base_url)
        
        logger.info(f"Initialized Ollama provider: {self.model} at {self.base_url}")
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[List[Dict[str, str]]] = None,
        stream: bool = False,
    ) -> str:
        """
        Generate a response using Ollama.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            context: Conversation context as list of message dicts
            stream: Whether to stream the response (collects and returns full text)
            
        Returns:
            Generated response text
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Add context messages
        if context:
            messages.extend(context)
        
        # Add current prompt
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = self.client.chat(
                model=self.model,
                messages=messages,
                stream=stream,
            )
            
            if stream:
                # Collect streamed chunks
                full_response = ""
                for chunk in response:
                    if "message" in chunk and "content" in chunk["message"]:
                        full_response += chunk["message"]["content"]
                return full_response
            else:
                return response["message"]["content"]
                
        except Exception as e:
            logger.error(f"Error generating response with Ollama: {e}")
            raise
    
    def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[List[Dict[str, str]]] = None,
    ) -> Generator[str, None, None]:
        """
        Generate a streaming response using Ollama.
        
        Yields tokens as they are generated for real-time display.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            context: Conversation context as list of message dicts
            
        Yields:
            String tokens as they are generated
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Add context messages
        if context:
            messages.extend(context)
        
        # Add current prompt
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = self.client.chat(
                model=self.model,
                messages=messages,
                stream=True,
            )
            
            for chunk in response:
                if "message" in chunk and "content" in chunk["message"]:
                    token = chunk["message"]["content"]
                    yield token
                    
        except Exception as e:
            logger.error(f"Error in streaming response: {e}")
            raise
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
    ) -> str:
        """
        Chat with Ollama using message history.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            stream: Whether to stream the response
            
        Returns:
            Generated response text
        """
        try:
            response = self.client.chat(
                model=self.model,
                messages=messages,
                stream=stream,
            )
            
            if stream:
                full_response = ""
                for chunk in response:
                    if "message" in chunk and "content" in chunk["message"]:
                        full_response += chunk["message"]["content"]
                return full_response
            else:
                return response["message"]["content"]
                
        except Exception as e:
            logger.error(f"Error in Ollama chat: {e}")
            raise
