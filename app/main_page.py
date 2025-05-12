import os

# Load environment variables
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=env_path, override=True)

import asyncio

from nicegui import ui, app
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request

from state import State
from utils.custom_css import slide_up_bounce, message_hover_animation, pulse_custom
from components.chat_message import Message
from components.chat_input import ChatInput

# -------------------------- Middleware and Static Files -------------------------- #
# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files for icons
app.add_static_files('/icon', 'icon')

# -------------------------- Main Page Definition -------------------------- #
@ui.page('/', favicon='🚀', title='FMCAIサポートデスク')
async def page(request: Request):
    """
    Defines the main page of the application, including the header, chat interface, and footer.
    """

    # -------------------------- Starting App Loading -------------------------- #
    # Display a loading spinner while the page initializes
    with ui.card().tight().classes('fixed-center') as startup_element:
        with ui.column().classes('fixed-center'):
            ui.spinner('comment', size='13em', color="deep-purple")

    # -------------------------- Initialize Page -------------------------- #
    # Set the page title and add custom CSS/animations
    ui.page_title(title="メルカリAIサポートデスク")
    ui.add_head_html(slide_up_bounce)
    ui.add_head_html(pulse_custom)

    # Add custom CSS for links and layout adjustments
    ui.add_css(r'a:link, a:visited {color: inherit !important; text-decoration: none; font-weight: 500}')
    ui.query('.q-page').classes('flex')
    ui.query('.nicegui-content').classes('w-full')

    # -------------------------- Dialog Section -------------------------- #
    # Add a reset dialog to allow users to restart the chat
    with ui.dialog().props('persistent') as reset_dialog, ui.card():
        ui.markdown('チャットを初めからやります？')
        with ui.row().classes('w-full'):
            ui.space()
            ui.button('適用', color='teal', on_click=lambda: ui.navigate.reload())
            ui.button('キャンセル', on_click=lambda: reset_dialog.close())

    # -------------------------- Audio Player Pop-Up -------------------------- #
    # Define a refreshable pop-up for playing audio responses
    @ui.refreshable
    async def player_pop_up(audio_path: str, dialog_open: bool = False):
        with ui.dialog().props('position="bottom"') as player_dialog, ui.card():
            with ui.column(align_items='center').classes('w-full'):
                ui.markdown(content="AIサポートデスク")
                from_text_audio = ui.audio(src=audio_path)
                from_text_audio.on('ended', lambda: player_dialog.close())

        if dialog_open:
            player_dialog.open()
            await asyncio.sleep(0.3)
            from_text_audio.play()

    await player_pop_up('', False)

    # -------------------------- Initialize Client-Specific State -------------------------- #
    # Create a State instance for managing OpenAI interactions and conversation history
    client_state = State(
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )

    # -------------------------- Header Section -------------------------- #
    # Add a header with the app title and a reset button
    with ui.header(bordered=True).classes('items-center text-black bg-white h-[5rem]'), ui.column(align_items='center').classes('w-full max-w-3xl mx-auto'):
        with ui.row(align_items='center').classes('w-full no-wrap items-center'):
            with ui.avatar(color="white", rounded=True):
                ui.image(source='/icon/bot_icon.png')
                ui.badge(color='green').props('floating rounded').classes('animate-bounce')
            ui.markdown(f'AIサポートデスク<br>**メルカリ商品検索**')
            ui.space()
            with ui.column(align_items='center'):
                ui.button(icon='restart_alt', on_click=lambda: reset_dialog.open()).props('flat size="lg" padding="xs md"')

    # Wait for the client to connect before clearing the loading spinner
    await ui.context.client.connected(timeout=120)
    startup_element.clear()

    # -------------------------- Message Body Section -------------------------- #
    # Add a chat interface for displaying messages
    message_container = ui.column().classes('w-full max-w-2xl mx-auto flex-grow items-stretch')
    with message_container:
        # Display the first bot message
        response_first_message = Message(avatar='/icon/bot_icon.png', name='AIサポートデスク', stamp=client_state.get_time_stamp(), sent=False, client_state=client_state).classes(message_hover_animation)
        response_first_text = ''
        async for i in client_state.stream_manual_message(message="こんにちは！何かお手伝いできますか？"):
            response_first_text += i
            with response_first_message.add_slot('default'):
                response_first_message.stored_text = response_first_text
                ui.markdown(response_first_text)

    # -------------------------- Footer Section -------------------------- #
    # Add a footer with the chat input field
    with ui.footer(bordered=True).classes('bg-white').style('animation: slideUpBounce 0.5s ease-in-out forwards;'), ui.column(align_items='center').classes('w-full max-w-3xl mx-auto'):
        ChatInput(message_container=message_container, client_state=client_state)


# -------------------------- Run the Application -------------------------- #
if __name__ in {"__main__", "__mp_main__"}:
    ui.run(reload=False, port=8801, language='ja')