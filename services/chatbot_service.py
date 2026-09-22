# PATH: GovScheme/services/chatbot_service.py
# Compatibility facade: the single chatbot implementation lives in ai.chatbot.
from ai.chatbot import handle_message
__all__=["handle_message"]
