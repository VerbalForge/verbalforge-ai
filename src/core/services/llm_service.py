"""LLM service for managing LLM communication with OpenAI and Azure OpenAI"""

import logging
import time
from typing import Optional
from openai import AsyncOpenAI, AsyncAzureOpenAI
from ..models.responses import LLMResponse
from ..models.enums import LLMProvider
from ..utils.providers_config import get_api_key, get_model_config

logger = logging.getLogger(__name__)


class LLMService:
    """Service for managing LLM provider communication"""

    def __init__(self, provider: Optional[str] = None):
        """Initialize LLM service

        Args:
            provider: LLM provider to use ('openai' or 'azure_openai')
        """
        self.provider_type = provider or self._detect_provider()
        self._client = None
        self._model_config = get_model_config(self.provider_type)
        self._usage_stats = {
            "total_requests": 0,
            "total_tokens": 0,
            "estimated_total_cost": 0.0,
        }
        logger.info(f"LLMService initialized with provider: {self.provider_type}")
        self._initialize_client()

    def _detect_provider(self) -> str:
        """Detect available LLM provider from environment"""
        from ..utils.settings import settings

        logger.info("Auto-detecting LLM provider from environment")

        if settings.openai_api_key:
            logger.info("Found OpenAI API key, using OpenAI provider")
            return LLMProvider.OPENAI.value
        elif settings.azure_openai_api_key:
            logger.info("Found Azure OpenAI API key, using Azure OpenAI provider")
            return LLMProvider.AZURE_OPENAI.value
        else:
            raise ValueError("No API keys found. Please set OPENAI_API_KEY or AZURE_OPENAI_API_KEY")

    def _initialize_client(self):
        """Initialize the appropriate OpenAI client"""
        api_key = get_api_key(self.provider_type)

        if not api_key:
            raise ValueError(f"No API key found for provider: {self.provider_type}")

        if self.provider_type == LLMProvider.OPENAI.value:
            logger.info("Initializing AsyncOpenAI client")
            self._client = AsyncOpenAI(api_key=api_key)
        elif self.provider_type == LLMProvider.AZURE_OPENAI.value:
            logger.info("Initializing AsyncAzureOpenAI client")
            self._client = AsyncAzureOpenAI(
                api_key=api_key,
                api_version=self._model_config.get("api_version"),
                azure_endpoint=self._model_config.get("azure_endpoint"),
            )
        else:
            raise ValueError(f"Unsupported provider: {self.provider_type}")

    async def generate_response(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Generate response from LLM

        Args:
            system_prompt: System-level instructions
            user_prompt: User query/request

        Returns:
            LLMResponse with content and metadata
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return await self.generate_with_history(messages)

    async def generate_with_history(self, messages: list) -> LLMResponse:
        """Generate response from LLM with conversation history

        Args:
            messages: List of message dicts with 'role' and 'content'
                     e.g., [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]

        Returns:
            LLMResponse with content and metadata
        """
        start_time = time.time()

        try:
            logger.info(f"Generating response using {self.provider_type}")

            # DEBUG: Log the messages being sent to LLM
            logger.debug("=" * 80)
            logger.debug(f"MESSAGES SENT TO LLM ({len(messages)} messages):")
            for i, msg in enumerate(messages):
                logger.debug(f"Message {i+1} ({msg['role']}):")
                logger.debug(msg['content'][:200] + "..." if len(msg['content']) > 200 else msg['content'])
            logger.debug("=" * 80)

            # Get model name (handle Azure deployment vs OpenAI model)
            if self.provider_type == LLMProvider.AZURE_OPENAI.value:
                model = self._model_config.get("azure_deployment")
            else:
                model = self._model_config.get("model")

            # Call LLM API
            response = await self._client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=self._model_config.get("temperature", 0.7),
            )

            # Extract response data
            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            cost_estimate = self._estimate_cost(tokens_used, model)

            response_time = time.time() - start_time

            llm_response = LLMResponse(
                content=content,
                tokens_used=tokens_used,
                model=model,
                cost_estimate=cost_estimate,
                response_time=response_time,
            )

            self._update_usage_stats(llm_response)

            logger.info(
                f"Response generated successfully in {response_time:.2f}s - "
                f"Tokens: {tokens_used}, Cost: ${cost_estimate:.4f}"
            )

            return llm_response

        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"LLM API call failed after {elapsed_time:.2f}s: {e}")
            raise

    def _estimate_cost(self, tokens: int, model: str) -> float:
        """Estimate cost based on token count and model

        Args:
            tokens: Total tokens used
            model: Model name

        Returns:
            Estimated cost in USD
        """
        # Rough cost estimates (update these based on actual pricing)
        cost_per_1k_tokens = {
            "gpt-4": 0.03,
            "gpt-4-turbo": 0.01,
            "gpt-4o": 0.005,
            "gpt-3.5-turbo": 0.002,
        }

        # Find matching cost
        cost_rate = 0.01  # Default
        for model_key, rate in cost_per_1k_tokens.items():
            if model_key in model.lower():
                cost_rate = rate
                break

        return (tokens / 1000) * cost_rate

    def _update_usage_stats(self, response: LLMResponse):
        """Update internal usage statistics"""
        self._usage_stats["total_requests"] += 1
        self._usage_stats["total_tokens"] += response.tokens_used
        self._usage_stats["estimated_total_cost"] += response.cost_estimate or 0.0

    def get_usage_stats(self) -> dict:
        """Get usage statistics

        Returns:
            Dictionary with usage metrics
        """
        return {
            **self._usage_stats,
            "provider": self.provider_type,
        }

    def _get_model_name(self) -> str:
        """Get the model name being used"""
        if self.provider_type == LLMProvider.AZURE_OPENAI.value:
            return self._model_config.get("azure_deployment", "unknown")
        return self._model_config.get("model", "unknown")
