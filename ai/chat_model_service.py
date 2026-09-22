# PATH: GovScheme/ai/chat_model_service.py
"""
ChatModelService abstraction (spec section 42).

The core system MUST work without any external LLM API. By default
(no LLM_API_KEY in .env) the chatbot uses ai/chatbot.py's local,
database-grounded structured responses only. If an LLM key IS configured,
it can optionally be used for surface-level rewording of an already-
computed, fact-checked response (never to invent eligibility rules or
scheme facts - those always come from the database + eligibility engine).
"""
from config import Config


class ChatModelService:
    def is_available(self) -> bool:
        raise NotImplementedError

    def polish_response(self, grounded_text: str, user_message: str, language: str) -> str:
        """Takes an already-correct, database-grounded response and may
        rephrase it for tone/fluency. Must not add new facts."""
        raise NotImplementedError


class LocalOnlyChatModelService(ChatModelService):
    """Default service: returns the grounded text unchanged. Always available,
    zero cost, zero external dependency."""

    def is_available(self) -> bool:
        return True

    def polish_response(self, grounded_text: str, user_message: str, language: str) -> str:
        return grounded_text


def get_chat_model_service() -> ChatModelService:
    if not Config.LLM_API_KEY or not Config.LLM_PROVIDER:
        return LocalOnlyChatModelService()
    # Example wiring point for an external LLM used ONLY for rephrasing:
    # if Config.LLM_PROVIDER == "anthropic":
    #     from ai.providers.anthropic_chat import AnthropicPolishService
    #     return AnthropicPolishService(api_key=Config.LLM_API_KEY)
    return LocalOnlyChatModelService()
