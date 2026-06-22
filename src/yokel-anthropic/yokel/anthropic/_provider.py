from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, Callable, cast

from yokel.core.errors import AuthError, ProviderError
from yokel.core.models import Response, Tool, ToolCall, ToolChoice, Usage
from yokel.providers import ProviderInterface

import anthropic

if TYPE_CHECKING:
    from yokel.core.configuration.interfaces import IConfigurationSection


class AnthropicProvider(ProviderInterface):
    """Adapts the `anthropic` SDK to the yokel `ProviderInterface` contract."""

    default_max_tokens: int = 4096

    def __init__(
        self,
        value_store: IConfigurationSection | None = None,
        *,
        api_key: str | None = None,
        api_key_resolver: Callable[[], str | None] | None = None,
    ) -> None:
        """Resolve an API key and construct the underlying anthropic client.

        Args:
            value_store: Optional configuration section consulted for the
                "anthropic_api_key" key if no explicit key/resolver resolves one.
            api_key: An explicit API key. Tried first.
            api_key_resolver: A zero-arg callable tried before value_store and
                the ANTHROPIC_API_KEY environment variable.

        Raises:
            AuthError: No API key could be resolved from any source.
        """
        resolved_key = self.__resolve_api_key(value_store, api_key, api_key_resolver)
        self._conf: dict[str, Any] = {"api_key": resolved_key}
        self._client = anthropic.Anthropic(api_key=resolved_key)

    @property
    def conf(self) -> dict[str, Any]:
        """The resolved configuration this provider was constructed with."""
        return self._conf

    @conf.setter
    def conf(self, value: dict[str, Any]) -> None:
        """Override the resolved configuration after construction."""
        self._conf = value

    def send(
        self,
        messages: tuple[dict[str, Any], ...],
        model: str,
        system: str | None,
        max_tokens: int,
        *,
        tools: tuple[Tool, ...] = (),
        tool_choice: ToolChoice | None = None,
    ) -> Response:
        """Issue one non-streaming `client.messages.create()` call.

        Args:
            messages: Ordered conversation turns as raw dicts (role + content).
            model: The model identifier to target (e.g. ``"claude-sonnet-4-6"``).
            system: Optional system prompt; omitted from the request when None.
            max_tokens: Upper bound on tokens the provider may generate.
            tools: Already-resolved tool declarations to offer the model;
                translated to the SDK's tools= kwarg, omitted when empty.
            tool_choice: Optional normalized tool_choice; translated to the
                SDK's tool_choice= kwarg, omitted when None.

        Returns:
            A normalised Response containing the generated text, model id,
            stop reason, token usage, any requested tool calls, and the
            provider's native response content.

        Raises:
            AuthError: The request was rejected for authentication or
                permission reasons.
            ProviderError: The provider returned an upstream HTTP or
                connection-level error.
        """
        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [
                {"role": message["role"], "content": message["content"]}
                for message in messages
            ],
        }
        if system is not None:
            kwargs["system"] = system

        if tools:
            kwargs["tools"] = [self.__encode_tool(tool) for tool in tools]

        if tool_choice is not None:
            kwargs["tool_choice"] = self.__encode_tool_choice(tool_choice)

        try:
            resp = self._client.messages.create(**kwargs)
        except (anthropic.AuthenticationError, anthropic.PermissionDeniedError) as exc:
            raise AuthError(str(exc)) from exc
        except anthropic.APIConnectionError as exc:
            raise ProviderError(
                str(exc), status_code=0, provider_message=str(exc)
            ) from exc
        except anthropic.APIStatusError as exc:
            raise ProviderError(
                str(exc), status_code=exc.status_code, provider_message=str(exc)
            ) from exc

        return self.__to_response(resp)

    def encode_assistant_turn(self, response: Response) -> dict[str, Any]:
        """Re-encode a Response as the content of an Anthropic assistant turn.

        Args:
            response: The Response whose assistant turn is being replayed.

        Returns:
            The provider-native "content" block list: a leading text block
            when `response.text` is non-empty, followed by one "tool_use"
            block per `response.tool_calls`, in Anthropic's native shape --
            accepted unchanged as a replayed assistant turn.
        """
        blocks: list[dict[str, Any]] = []
        if response.text:
            blocks.append({"type": "text", "text": response.text})

        blocks.extend(
            {
                "type": "tool_use",
                "id": call.id,
                "name": call.name,
                "input": call.input,
            }
            for call in response.tool_calls
        )
        return {"content": blocks}

    @staticmethod
    def __resolve_api_key(
        value_store: IConfigurationSection | None,
        api_key: str | None,
        api_key_resolver: Callable[[], str | None] | None,
    ) -> str:
        """Resolve an API key: explicit arg -> resolver -> value_store -> env."""
        if api_key is not None:
            return api_key

        if api_key_resolver is not None:
            from_resolver = api_key_resolver()
            if from_resolver is not None:
                return from_resolver

        if value_store is not None:
            from_store = value_store.get("anthropic_api_key")
            if from_store is not None:
                return cast(str, from_store)

        from_env = os.environ.get("ANTHROPIC_API_KEY")
        if from_env is not None:
            return from_env

        raise AuthError(
            "No Anthropic API key resolved. Provide api_key, api_key_resolver, "
            "value_store.anthropic_api_key, or set the ANTHROPIC_API_KEY "
            "environment variable."
        )

    @staticmethod
    def __encode_tool(tool: Tool) -> dict[str, Any]:
        """Translate a normalised Tool into Anthropic's tools= entry shape."""
        return {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.input_schema,
        }

    @staticmethod
    def __encode_tool_choice(choice: ToolChoice) -> dict[str, Any]:
        """Translate a normalised ToolChoice into Anthropic's tool_choice= shape."""
        if choice.mode == "tool":
            return {"type": "tool", "name": choice.name}

        return {"type": "any" if choice.mode == "required" else choice.mode}

    @staticmethod
    def __to_response(resp: anthropic.types.Message) -> Response:
        """Translate an SDK Message into a normalised Response."""
        text = "".join(block.text for block in resp.content if block.type == "text")
        tool_calls = tuple(
            ToolCall(
                id=block.id, name=block.name, input=cast(dict[str, Any], block.input)
            )
            for block in resp.content
            if block.type == "tool_use"
        )
        return Response(
            text=text,
            model=resp.model,
            stop_reason=resp.stop_reason or "",
            usage=Usage(
                input_tokens=resp.usage.input_tokens,
                output_tokens=resp.usage.output_tokens,
            ),
            tool_calls=tool_calls,
            raw_content=resp.content,
        )
