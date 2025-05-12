from io import BytesIO
from typing import Literal, Union, List, Optional

from nicegui import ui

from state import State

class Message(ui.chat_message):
    def __init__(self,
                 text: Union[str, List[str]] = ...,  # ✅ Default matches ui.chat_message
                 sent: bool = False,
                 avatar: Optional[str] = None,
                 name: Optional[str] = None,
                 stamp: Optional[str] = None,
                 message_type: Literal['text', 'audio'] = "text",
                 sender_type: Literal['chat_bot_message', 'human_message'] = "human_message",
                 message_text_to_speech: Optional[BytesIO] = None,
                 message_audio_path: Optional[str] = None,
                 message_audio_to_text: Optional[str] = None,
                 client_state: State = None,
                 *args, **kwargs):  
        """Custom chat message that supports text, audio, and additional metadata."""

        self.stored_text = text if isinstance(text, str) else " ".join(text) if isinstance(text, list) else ""

        super().__init__(text=text, avatar=avatar, name=name, stamp=stamp, sent=sent, *args, **kwargs)  

        self.message_type = message_type
        self.sender_type = sender_type
        self.message_text_to_speech = message_text_to_speech
        self.message_audio_path = message_audio_path
        self.message_audio_to_text = message_audio_to_text
        self.client_state = client_state

        with self.add_slot('name'):
            with ui.row(align_items='center').classes('w-full').style('gap: 0rem'):
                if sent:
                    ui.space()
                ui.markdown(content=name)