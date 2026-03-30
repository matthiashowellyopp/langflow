from urllib import parse

from lfx.base.memory.model import LCChatMemoryComponent
from lfx.field_typing.constants import Memory
from lfx.inputs.inputs import IntInput, MessageTextInput, SecretStrInput, StrInput


class ValkeyIndexChatMemory(LCChatMemoryComponent):
    display_name = "Valkey Chat Memory"
    description = "Retrieves and stores chat messages from Valkey."
    name = "ValkeyChatMemory"
    icon = "Valkey"

    inputs = [
        StrInput(
            name="host", display_name="hostname", required=True, value="localhost", info="IP address or hostname."
        ),
        IntInput(name="port", display_name="port", required=True, value=6379, info="Valkey Port Number."),
        StrInput(name="database", display_name="database", required=True, value="0", info="Valkey database."),
        MessageTextInput(
            name="username", display_name="Username", value="", info="The Valkey user name.", advanced=True
        ),
        SecretStrInput(
            name="password", display_name="Valkey Password", info="The password for username.", advanced=True,
            load_from_db=False,
        ),
        StrInput(name="key_prefix", display_name="Key prefix", info="Key prefix.", advanced=True),
        MessageTextInput(
            name="session_id", display_name="Session ID", info="Session ID for the message.", advanced=True
        ),
    ]

    def build_message_history(self) -> Memory:
        from langchain_community.chat_message_histories.redis import RedisChatMessageHistory

        kwargs = {}
        if self.key_prefix:
            kwargs["key_prefix"] = self.key_prefix

        # Build URL, only include auth if credentials are actually provided
        password = getattr(self, 'password', None)
        username = getattr(self, 'username', None)
        has_password = password is not None and str(password).strip() not in ("", "None")
        has_username = username is not None and str(username).strip() not in ("", "None")

        if has_password:
            encoded_pw = parse.quote_plus(str(password))
            if has_username:
                auth = f"{username}:{encoded_pw}@"
            else:
                auth = f":{encoded_pw}@"
        else:
            auth = ""

        url = f"redis://{auth}{self.host}:{self.port}/{self.database}"
        return RedisChatMessageHistory(session_id=self.session_id, url=url, **kwargs)
