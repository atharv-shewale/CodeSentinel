"""
CodeSentinel Agents Module: LLM Gateway Abstraction.

Thin abstraction decoupling agents from LLM providers (Groq primary, swappable).
Features:
- Single interface: `generate(prompt, context, system_message) -> str`
- Bounded retry logic (max 2 retries) with exponential backoff on timeouts/errors.
- Swappable provider implementation (Groq, Mock, Custom).
- Agents MUST call this gateway and NEVER import a provider SDK directly.
"""

from abc import ABC, abstractmethod
import asyncio
from typing import Any, Dict, List, Optional
import httpx

from app.core.config import settings
from app.core.logging import logger


class LLMProviderError(Exception):
    """Raised when the LLM provider fails after all bounded retries."""
    def __init__(self, message: str, provider: str, retries: int = 2, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.provider = provider
        self.retries = retries
        self.original_error = original_error


class BaseLLMProvider(ABC):
    """Abstract Base Class for LLM Providers."""

    @abstractmethod
    async def generate_response(
        self,
        prompt: str,
        context: Optional[str] = None,
        system_message: Optional[str] = None,
    ) -> str:
        """Generate response from LLM."""
        pass


class GroqLLMProvider(BaseLLMProvider):
    """
    Groq LLM Provider using fast Llama-3 / Mixtral inference over OpenAI-compatible REST API.
    Includes bounded retry logic (max 2 retries) before failing.
    """

    MAX_RETRIES = 2
    BASE_URL = "https://api.groq.com/openai/v1"
    DEFAULT_MODEL = "llama-3.1-70b-versatile"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or getattr(settings, "GROQ_API_KEY", "") or getattr(settings, "OPENAI_API_KEY", "")
        self.model = model or self.DEFAULT_MODEL

    async def generate_response(
        self,
        prompt: str,
        context: Optional[str] = None,
        system_message: Optional[str] = None,
    ) -> str:
        sys_msg = system_message or (
            "You are CodeSentinel AI, a high-precision software engineering reasoning agent. "
            "Always ground your reasoning in the provided codebase context and cite specific files, "
            "functions, or requirement identifiers."
        )

        full_user_content = prompt
        if context:
            full_user_content = f"CONTEXT:\n{context}\n\nQUESTION/TASK:\n{prompt}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": full_user_content},
            ],
            "temperature": 0.1,
            "max_tokens": 1500,
        }

        attempt = 0
        last_exception = None

        while attempt <= self.MAX_RETRIES:
            try:
                attempt += 1
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.post(
                        f"{self.BASE_URL}/chat/completions",
                        json=payload,
                        headers=headers
                    )
                    if response.status_code == 200:
                        data = response.json()
                        choices = data.get("choices", [])
                        if choices:
                            return choices[0]["message"]["content"]
                        return ""
                    else:
                        error_text = response.text
                        logger.warning(
                            f"Groq API returned HTTP {response.status_code} (attempt {attempt}/{self.MAX_RETRIES + 1}): {error_text}"
                        )
                        last_exception = Exception(f"HTTP {response.status_code}: {error_text}")
            except (httpx.TimeoutException, httpx.RequestError, Exception) as e:
                logger.warning(
                    f"Groq API connection error on attempt {attempt}/{self.MAX_RETRIES + 1}: {str(e)}"
                )
                last_exception = e

            if attempt <= self.MAX_RETRIES:
                await asyncio.sleep(0.5 * (2 ** (attempt - 1)))  # Exponential backoff

        raise LLMProviderError(
            message=f"Groq LLM Provider request failed after {self.MAX_RETRIES} retries: {str(last_exception)}",
            provider="Groq",
            retries=self.MAX_RETRIES,
            original_error=last_exception
        )


class MockLLMProvider(BaseLLMProvider):
    """
    Mock LLM Provider for unit testing and deterministic responses.
    Synthesizes intelligent grounded responses by echoing retrieved evidence symbols.
    """

    def __init__(self, response_template: Optional[str] = None, fail_after_retries: bool = False):
        self.response_template = response_template
        self.fail_after_retries = fail_after_retries
        self.call_count = 0
        self.last_prompt = None
        self.last_context = None

    async def generate_response(
        self,
        prompt: str,
        context: Optional[str] = None,
        system_message: Optional[str] = None,
    ) -> str:
        self.call_count += 1
        self.last_prompt = prompt
        self.last_context = context

        if self.fail_after_retries:
            raise LLMProviderError(
                message="MockLLMProvider simulated timeout/failure after 2 retries.",
                provider="MockProvider",
                retries=2
            )

        if self.response_template:
            return self.response_template

        # Deterministic evidence-grounded synthesis
        # If context contains files, functions or requirements, include them in the synthesized response
        ctx_str = context or ""
        citations = []
        for line in ctx_str.splitlines():
            if "File:" in line:
                parts = line.split("File:", 1)
                citations.append(parts[1].strip())
            elif "Function:" in line:
                parts = line.split("Function:", 1)
                citations.append(parts[1].strip())
            elif "Requirement:" in line:
                parts = line.split("Requirement:", 1)
                ident = parts[1].strip().split()[0]
                citations.append(ident)

        if citations:
            cited_text = ", ".join(sorted(list(set(citations)))[:3])
            return (
                f"Based on retrieved evidence, the analysis references [{cited_text}]. "
                f"Addressing query: {prompt}"
            )

        return f"Analysis result for prompt: {prompt}"


class LLMGateway:
    """
    Central Gateway coordinating calls to the active LLM Provider.
    Agents interact exclusively with this gateway.
    """

    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        # Default to Mock provider for test safety, or Groq if configured
        self._provider: BaseLLMProvider = provider or MockLLMProvider()

    def set_provider(self, provider: BaseLLMProvider) -> None:
        """Swap underlying provider at runtime without modifying agent code."""
        self._provider = provider

    @property
    def current_provider(self) -> BaseLLMProvider:
        return self._provider

    async def generate(
        self,
        prompt: str,
        context: Optional[str] = None,
        system_message: Optional[str] = None,
    ) -> str:
        """Execute LLM generation via the active provider."""
        return await self._provider.generate_response(
            prompt=prompt,
            context=context,
            system_message=system_message
        )


# Global singleton instance
llm_gateway = LLMGateway()
