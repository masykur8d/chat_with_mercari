import re
import os
from typing import Optional

from nicegui import ui, run
from openai import AsyncOpenAI

from state import State
from utils.custom_css import message_hover_animation
from components.chat_message import Message


def is_japanese(text: str) -> bool:
    """
    Check if the given text contains Japanese characters.
    """
    japanese_pattern = re.compile(r'[\u3040-\u30FF\u4E00-\u9FAF]')
    return bool(japanese_pattern.search(text))


class ChatInput(ui.row):
    """
    A UI component for handling user input in the chat interface.
    Includes input validation, message sending, and response streaming.
    """

    def __init__(
            self, 
            *, 
            wrap=True, 
            align_items='center',
            message_text: Optional[str] = None,
            message_container: ui.column,
            client_state: State,
        ):
        """
        Initialize the ChatInput component.

        Args:
            wrap (bool): Whether the row should wrap its content.
            align_items (str): Alignment of items in the row.
            message_text (Optional[str]): Initial message text.
            message_container (ui.column): Container for displaying chat messages.
            client_state (State): The application's state for managing OpenAI interactions.
        """
        super().__init__(wrap=wrap, align_items=align_items)

        # Store references to the message container and client state
        self.message_text = message_text
        self.message_container = message_container
        self.client_state = client_state

        # Create the input field and buttons for sending messages and recording
        with self.classes('w-full no-wrap items-center'):
            with ui.input(placeholder="質問を入力してください！").props('autogrow filled clearable').classes("w-full") as input_question:
                with input_question.add_slot('append'):
                    self.send_button = ui.button(
                        text='送信', 
                        color='teal', 
                        on_click=self.send_message,
                    ).classes('ml-3')
            self.input_question = input_question

    # -------------------------- Function to update UI -------------------------- #
    async def send_message(self) -> None:
        """
        Handle the process of sending a message:
        - Validate the input.
        - Display the user's message in the chat.
        - Stream the AI's response and display it.
        """
        # Get the user's input
        question = getattr(self.input_question, 'value', '')
        if question is None:
            return
        elif len(question) == 0:
            ui.notify('質問を入力してから送信ボタンを押してください！', type='warning', close_button=True, position='top')
            return
        elif len(question) <= 2:
            ui.notify('質問を細かく書いてください！', type='warning', close_button=True, position='top')
            return

        # Disable the send button while processing
        self.send_button.props(add='disable loading')

        # Check if the input is in Japanese
        is_japanese_text = await run.cpu_bound(is_japanese, question)
        if not is_japanese_text:
            self.send_button.props(remove='disable loading')
            ui.notify('日本語で書いてください！', type='warning', close_button=True, position='top')
            return

        # Clear the input field and display the user's message
        self.input_question.value = ''
        with self.message_container:
            Message(
                text=question, 
                avatar='/icon/user_icon.png', 
                name='あなた', 
                sent=True, 
                stamp=self.client_state.get_time_stamp(), 
                client_state=self.client_state
            ).props('bg-color="amber-7"').classes(message_hover_animation)

            # Create a placeholder for the AI's response
            response_message = Message(
                avatar='/icon/bot_icon.png', 
                name='AIサポートデスク', 
                sent=False, 
                stamp=self.client_state.get_time_stamp(), 
                client_state=self.client_state
            ).classes(message_hover_animation)
            with response_message:
                with ui.column(align_items='center').classes('w-full'):
                    ui.spinner(type='dots', size='3rem')
            ui.run_javascript('window.scrollTo(0, document.body.scrollHeight)')

        try:
            # Stream the response from State.stream_response
            response = ''
            async for chunk in self.client_state.stream_response(question):
                response += chunk
                with response_message.add_slot('default'):
                    response_message.stored_text = response
                    ui.markdown(response)
                ui.run_javascript('window.scrollTo(0, document.body.scrollHeight)')

        except Exception as e:
            # Handle errors and notify the user
            error_message = f"エラーが発生しました: {str(e)}"
            print(f"Error: {error_message}")
            with response_message.add_slot('default'):
                response_message.stored_text = error_message
                ui.markdown(error_message)
            ui.run_javascript('window.scrollTo(0, document.body.scrollHeight)')

        # Re-enable the send button after processing
        self.send_button.props(remove='disable loading')