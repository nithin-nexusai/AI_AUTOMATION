"""OpenRouter LLM client for chat completion with tool calling.

This module provides an async client for interacting with OpenRouter API,
which provides access to multiple LLM providers with an OpenAI-compatible interface.
"""

import json
import logging
from typing import Any

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from app.config import get_settings

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Base exception for LLM-related errors."""
    pass


class LLMConnectionError(LLMError):
    """Raised when connection to LLM API fails."""
    pass


class LLMRateLimitError(LLMError):
    """Raised when rate limit is exceeded."""
    pass


class LLMResponseError(LLMError):
    """Raised when LLM returns an invalid or unexpected response."""
    pass


class OpenRouterClient:
    """Async client for OpenRouter API.

    OpenRouter provides access to multiple LLM providers (OpenAI, Anthropic, Google, etc.)
    with an OpenAI-compatible API interface.

    Usage:
        client = OpenRouterClient()
        response = await client.chat_completion(
            messages=[{"role": "user", "content": "Hello"}]
        )
    """

    def __init__(self) -> None:
        """Initialize the OpenRouter client with settings from config."""
        settings = get_settings()

        if not settings.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY is not configured")

        self._api_key = settings.openrouter_api_key
        self._model = settings.openrouter_model or "google/gemini-2.0-flash-001"
        self._base_url = "https://openrouter.ai/api/v1"
        self._client = httpx.AsyncClient(timeout=60.0)
        self._settings = settings

    @property
    def model(self) -> str:
        """Get the configured model name."""
        return self._model

    @retry(
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException, LLMRateLimitError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        stream: bool = False,
    ) -> dict[str, Any]:
        """Send a chat completion request to OpenRouter.

        Args:
            messages: List of message objects with role and content.
            tools: Optional list of tool definitions for function calling.
            tool_choice: Optional tool choice strategy.
            temperature: Sampling temperature (0.0-2.0). Default 0.7.
            max_tokens: Maximum tokens in response. Default 1024.
            stream: Whether to stream the response. Default False (not implemented).

        Returns:
            dict containing the API response with the following structure:
            {
                "content": str | None,  # Text response if any
                "tool_calls": list | None,  # Tool calls if any
                "finish_reason": str,  # "stop", "tool_calls", etc.
                "usage": dict,  # Token usage statistics
            }

        Raises:
            LLMConnectionError: If connection to API fails after retries.
            LLMRateLimitError: If rate limit is exceeded.
            LLMResponseError: If API returns an unexpected response.
            LLMError: For other API errors.
        """
        try:
            url = f"{self._base_url}/chat/completions"

            headers = {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://chicx.in",
                "X-Title": "CHICX WhatsApp Bot",
            }

            request_body: dict[str, Any] = {
                "model": self._model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            if tools:
                request_body["tools"] = tools
                if tool_choice:
                    request_body["tool_choice"] = tool_choice

            logger.debug(
                "Sending chat completion request to OpenRouter",
                extra={
                    "model": self._model,
                    "message_count": len(messages),
                    "has_tools": bool(tools),
                },
            )

            response = await self._client.post(url, headers=headers, json=request_body)

            if response.status_code == 429:
                raise LLMRateLimitError("OpenRouter API rate limit exceeded")

            if response.status_code != 200:
                error_text = response.text
                logger.error(f"OpenRouter API error: {response.status_code} - {error_text}")
                raise LLMError(f"OpenRouter API error: {response.status_code} - {error_text}")

            data = response.json()

            # Extract response (OpenAI format)
            result = {
                "content": None,
                "tool_calls": None,
                "finish_reason": "stop",
                "usage": data.get("usage", {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                }),
            }

            choices = data.get("choices", [])
            if choices:
                choice = choices[0]
                message = choice.get("message", {})

                result["content"] = message.get("content")
                result["finish_reason"] = choice.get("finish_reason", "stop")

                # Handle tool calls
                if message.get("tool_calls"):
                    result["tool_calls"] = message["tool_calls"]
                    result["finish_reason"] = "tool_calls"

            logger.debug(
                "Chat completion successful",
                extra={
                    "finish_reason": result["finish_reason"],
                    "has_content": bool(result["content"]),
                    "tool_call_count": len(result["tool_calls"]) if result["tool_calls"] else 0,
                    "total_tokens": result["usage"].get("total_tokens", 0),
                },
            )

            return result

        except httpx.ConnectError as e:
            logger.error(f"Connection error to OpenRouter API: {e}")
            raise LLMConnectionError(f"Failed to connect to OpenRouter API: {e}") from e
        except httpx.TimeoutException as e:
            logger.error(f"Timeout connecting to OpenRouter API: {e}")
            raise LLMConnectionError(f"Timeout connecting to OpenRouter API: {e}") from e
        except LLMError:
            raise
        except Exception as e:
            logger.exception(f"Unexpected error in chat completion: {e}")
            raise LLMResponseError(f"Unexpected error: {e}") from e

    async def chat_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        tool_executor: "ToolExecutor",
        max_iterations: int = 5,
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        """Execute a conversation with automatic tool calling.

        This method handles the tool calling loop automatically, executing
        tools and feeding results back to the LLM until it produces a final
        response or reaches the iteration limit.

        Args:
            messages: Initial conversation messages.
            tools: List of tool definitions.
            tool_executor: Callable that executes tools and returns results.
            max_iterations: Maximum tool calling iterations. Default 5.
            temperature: Sampling temperature. Default 0.7.

        Returns:
            dict with final response including:
            {
                "content": str,  # Final text response
                "tool_calls_made": list,  # All tool calls executed
                "iterations": int,  # Number of iterations used
                "usage": dict,  # Aggregated token usage
            }

        Raises:
            LLMError: If an error occurs during the conversation.
        """
        conversation = list(messages)  # Copy to avoid mutation
        tool_calls_made: list[dict[str, Any]] = []
        total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        iterations = 0

        while iterations < max_iterations:
            iterations += 1

            response = await self.chat_completion(
                messages=conversation,
                tools=tools if iterations < max_iterations else None,
                temperature=temperature,
            )

            # Aggregate token usage
            for key in total_usage:
                total_usage[key] += response["usage"].get(key, 0)

            # Check if we have tool calls to execute
            if response["tool_calls"]:
                # Add assistant message with tool calls
                conversation.append({
                    "role": "assistant",
                    "content": response["content"],
                    "tool_calls": response["tool_calls"],
                })

                # Execute each tool and add results
                for tool_call in response["tool_calls"]:
                    tool_name = tool_call["function"]["name"]
                    try:
                        arguments = json.loads(tool_call["function"]["arguments"])
                    except json.JSONDecodeError:
                        arguments = {}

                    logger.info(f"Executing tool: {tool_name}", extra={"arguments": arguments})

                    # Execute the tool
                    result = await tool_executor.execute(tool_name, arguments)

                    tool_calls_made.append({
                        "name": tool_name,
                        "arguments": arguments,
                        "result": result,
                    })

                    # Add tool result to conversation
                    conversation.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": json.dumps(result) if isinstance(result, dict) else str(result),
                    })
            else:
                # No tool calls - we have a final response
                return {
                    "content": response["content"],
                    "tool_calls_made": tool_calls_made,
                    "iterations": iterations,
                    "usage": total_usage,
                }

        # Reached max iterations - return last response
        logger.warning(f"Reached max iterations ({max_iterations}) in tool calling loop")
        return {
            "content": response.get("content") or "I apologize, but I need more information to help you.",
            "tool_calls_made": tool_calls_made,
            "iterations": iterations,
            "usage": total_usage,
        }

    async def close(self) -> None:
        """Close the client and release resources."""
        await self._client.aclose()

    async def __aenter__(self) -> "OpenRouterClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()


class ToolExecutor:
    """Protocol for tool execution.

    Implementations should provide the execute method that takes a tool name
    and arguments, and returns the tool's result.
    """

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Execute a tool with the given arguments.

        Args:
            tool_name: Name of the tool to execute.
            arguments: Dictionary of arguments for the tool.

        Returns:
            The result of the tool execution.

        Raises:
            NotImplementedError: Must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement execute()")


# Singleton instance for application-wide use
_client_instance: OpenRouterClient | None = None


def get_llm_client() -> OpenRouterClient:
    """Get or create the global LLM client instance.

    Returns:
        The singleton OpenRouterClient instance.

    Note:
        This creates a single instance that is reused across the application.
        The client is thread-safe for async operations.
    """
    global _client_instance
    if _client_instance is None:
        _client_instance = OpenRouterClient()
    return _client_instance


async def shutdown_llm_client() -> None:
    """Shutdown the global LLM client instance.

    Call this during application shutdown to properly release resources.
    """
    global _client_instance
    if _client_instance is not None:
        await _client_instance.close()
        _client_instance = None
