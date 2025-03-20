"""Utilities for working with OpenAI and Claude models."""

import logging
import json
import os
from typing import Dict, Any, Optional, List, ClassVar
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage
from langchain_core.callbacks.manager import (
    CallbackManagerForLLMRun,
    AsyncCallbackManagerForLLMRun,
)
from langchain_core.outputs import ChatResult
from langchain_core.callbacks import BaseCallbackHandler
from openai import OpenAI

# Set up module-level logger
logger = logging.getLogger("llm_utils")


class ResponseLoggingHandler(BaseCallbackHandler):
    """Callback handler that logs the full response from the LLM."""

    def on_llm_end(self, response: ChatResult, **kwargs: Any) -> None:
        """Run when LLM ends running."""
        try:
            # Log the full response
            response_dict = response.dict()
            logger.debug(
                f"LLM Response: {json.dumps(response_dict, indent=2, default=str)}"
            )
        except Exception as e:
            logger.debug(f"Error logging LLM response: {e}")
            logger.debug(f"Raw response: {response}")


# Custom OpenAI client that ensures max_tokens is used
class CustomOpenAIClient(OpenAI):
    """Custom OpenAI client that ensures max_tokens is used instead of max_completion_tokens."""

    def __init__(self, max_tokens: int = 8192, **kwargs):
        """Initialize with max_tokens."""
        super().__init__(**kwargs)
        self.max_tokens = max_tokens

    def create(self, *args, **kwargs):
        """Override to ensure max_tokens is used in the create method."""
        # Ensure max_tokens is set
        kwargs["max_tokens"] = self.max_tokens

        # Remove max_completion_tokens if it exists
        if "max_completion_tokens" in kwargs:
            del kwargs["max_completion_tokens"]

        # Call the appropriate method
        if (
            hasattr(self, "chat")
            and hasattr(self.chat, "completions")
            and hasattr(self.chat.completions, "create")
        ):
            return self.chat.completions.create(*args, **kwargs)
        else:
            return super().create(*args, **kwargs)

    def post(self, url, *args, **kwargs):
        """Override to ensure max_tokens is used in the request body."""
        # Check if there's a json parameter in kwargs
        if "json" in kwargs and isinstance(kwargs["json"], dict):
            request_body = kwargs["json"]

            # Replace max_completion_tokens with max_tokens
            if "max_completion_tokens" in request_body:
                request_body["max_tokens"] = self.max_tokens
                del request_body["max_completion_tokens"]
            else:
                # Ensure max_tokens is set
                request_body["max_tokens"] = self.max_tokens

        return super().post(url, *args, **kwargs)


class CustomChatOpenAI(ChatOpenAI):
    """Custom ChatOpenAI class that handles both OpenAI and Claude models."""

    # Define max_tokens as a class variable with proper type annotation
    DEFAULT_MAX_TOKENS: ClassVar[int] = 8192

    def __init__(self, **kwargs):
        """Initialize the custom ChatOpenAI with support for both OpenAI and Claude models."""
        # Set max_tokens in kwargs
        kwargs["max_tokens"] = self.DEFAULT_MAX_TOKENS

        # Remove max_completion_tokens if it exists to avoid conflicts
        if "max_completion_tokens" in kwargs:
            del kwargs["max_completion_tokens"]

        # Add our custom callback handler for response logging
        callbacks = kwargs.get("callbacks", [])
        if not isinstance(callbacks, list):
            callbacks = [callbacks] if callbacks else []

        callbacks.append(ResponseLoggingHandler())
        kwargs["callbacks"] = callbacks

        # Determine which base URL to use based on the model
        model = kwargs.get("model", "")
        is_claude_model = "claude" in model.lower() or "anthropic" in model.lower()

        # Set the appropriate base URL based on model type
        if is_claude_model:
            # Use Claude API URL
            base_url = os.environ.get("CLAUDE_BASE_URL")
            logger.info(f"Using Claude model: {model} with base URL: {base_url}")
        else:
            # Use OpenAI API URL
            base_url = os.environ.get("OPENAI_BASE_URL")
            logger.info(f"Using OpenAI model: {model} with base URL: {base_url}")

        # Set the base URL in kwargs
        if base_url:
            kwargs["openai_api_base"] = base_url

        # Initialize the parent class
        super().__init__(**kwargs)

        # Replace the client with our custom client for all models
        if hasattr(self, "client"):
            # Set up headers for the LLM proxy
            default_headers = getattr(self.client, "default_headers", {}).copy()
            default_headers["x-app-id"] = "ai-readme-generation"

            self.client = CustomOpenAIClient(
                max_tokens=self.DEFAULT_MAX_TOKENS,
                api_key=getattr(self.client, "api_key", None),
                base_url=getattr(self.client, "base_url", None),
                default_headers=default_headers,
            )

    def _prepare_request_body(
        self, messages: List[BaseMessage], **kwargs: Any
    ) -> Dict[str, Any]:
        """Override to ensure max_tokens is included in the request body."""
        # Call the parent method to prepare the base request
        request_body = super()._prepare_request_body(messages, **kwargs)

        # Explicitly add max_tokens to the request body
        request_body["max_tokens"] = self.DEFAULT_MAX_TOKENS

        # Remove max_completion_tokens if it exists
        if "max_completion_tokens" in request_body:
            del request_body["max_completion_tokens"]

        return request_body

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Override to ensure max_tokens is set."""
        # Ensure max_tokens is set in kwargs
        kwargs["max_tokens"] = self.DEFAULT_MAX_TOKENS

        # Remove max_completion_tokens if it exists
        if "max_completion_tokens" in kwargs:
            del kwargs["max_completion_tokens"]

        # Call the parent method to make the actual request
        return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Override to ensure max_tokens is set."""
        # Ensure max_tokens is set in kwargs
        kwargs["max_tokens"] = self.DEFAULT_MAX_TOKENS

        # Remove max_completion_tokens if it exists
        if "max_completion_tokens" in kwargs:
            del kwargs["max_completion_tokens"]

        # Call the parent method to make the actual request
        return await super()._agenerate(
            messages, stop=stop, run_manager=run_manager, **kwargs
        )
