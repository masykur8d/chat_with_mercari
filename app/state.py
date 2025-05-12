import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

from openai import AsyncOpenAI
import json

from components.search_mercari import search_mercari
from components.create_keywords import extract_keywords_and_sort_order
from utils.prompt import OPENAI_CHAT_PROMPT, STREAM_RESPONSE_PROMPT

from nicegui import run

# Create a ZoneInfo object for Japan Standard Time
japan_tz = ZoneInfo("Asia/Tokyo")

class State:
    """
    Manages the application's state, including OpenAI interactions, conversation history,
    and tool-based function calls.
    """

    def __init__(self, openai_api_key: str) -> None:
        # Initialize OpenAI API key and chat prompt
        self.openai_api_key = openai_api_key
        self.openai_chat_prompt = OPENAI_CHAT_PROMPT

        # Initialize the AsyncOpenAI client for API interactions
        # As I am only have access to the OpenAI API, I will use the AsyncOpenAI client
        self.client = AsyncOpenAI(api_key=self.openai_api_key)

        # Initialize conversation history with a system message (chat prompt)
        self.conversation_history = [
            {"role": "system", "content": self.openai_chat_prompt}
        ]

    async def stream_response(self, user_input: str):
        """
        Handles user input, processes it with OpenAI, and streams the response.
        Ensures that `extract_keywords_and_sort_order` is executed first, followed by `search_mercari`.
        The AI generates the final response in Markdown format.
        """
        # Add user input to the conversation history
        self.conversation_history.append({"role": "user", "content": user_input})

        # Add the stream response prompt as a system message
        self.conversation_history.append({"role": "system", "content": STREAM_RESPONSE_PROMPT})

        # Define tools for OpenAI to use during the conversation
        tools = [
            {
                "type": "function",
                "name": "extract_keywords_and_sort_order",
                "description": (
                    "This function extracts keywords and determines the sort order from the conversation history. "
                    "It must be executed first. The output of this function (keywords and sort order) will be used "
                    "as input for the `search_mercari` function."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "conversation": {
                            "type": "array",
                            "items": {"type": "object"},
                            "description": "The conversation history."
                        }
                    },
                    "required": ["conversation"],
                    "additionalProperties": False
                }
            },
            {
                "type": "function",
                "name": "search_mercari",
                "description": (
                    "This function searches for items on Mercari using the keywords and sort order extracted by "
                    "`extract_keywords_and_sort_order`. It must be executed after `extract_keywords_and_sort_order` "
                    "has returned its output."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "keywords": {
                            "type": "string",
                            "description": "Space-separated keywords for the search."
                        },
                        "sort_order": {
                            "type": "string",
                            "description": (
                                "The sorting option to use. Options are:\n"
                                "- 'score:desc' (recommended items)\n"
                                "- 'created_time:desc' (latest items)\n"
                                "- 'price:asc' (lowest price)\n"
                                "- 'price:desc' (highest price)\n"
                                "- 'num_likes:desc' (most liked)"
                            )
                        }
                    },
                    "required": ["keywords", "sort_order"],
                    "additionalProperties": False
                }
            }
        ]

        # Process tool calls recursively until the final result is obtained
        items = await self.process_tool_calls_recursively(tools)

        # If items are retrieved, pass them to the AI for final response generation
        if items:
            # Ensure items is serialized to a JSON string
            try:
                serialized_items = json.dumps(items)
            except TypeError as e:
                raise ValueError(f"Failed to serialize items: {e}")

            # Add the retrieved items to the conversation history
            self.conversation_history.append({
                "role": "assistant",
                "content": f"Search Results: {serialized_items}"
            })

            # Call OpenAI API again to let it generate the final response
            response = await self.client.responses.create(
                model="gpt-4o",
                input=self.conversation_history,
                tools=[],  # No tools needed for this step
                parallel_tool_calls=False,
                stream=True  # Enable streaming for the response
            )

            # Stream the AI's response incrementally
            streamed = False
            async for chunk in response:
                if chunk.type == "response.output_text.delta":
                    streamed = True  # Mark that we have received a chunk
                    yield chunk.delta  # Yield the text content incrementally
                    print(f"Chunk received: {chunk.delta}")  # Debugging log

            # If no chunks were streamed, yield the default response
            if not streamed:
                yield "申し訳ありませんが、その質問にはお答えできません。"

    async def call_function(self, name: str, args: dict):
        """
        Executes the specified function with the given arguments.
        Supports 'extract_keywords_and_sort_order' and 'search_mercari'.
        """
        if name == "extract_keywords_and_sort_order":
            # Call the extract_keywords_and_sort_order function
            return await extract_keywords_and_sort_order(args["conversation"])

        if name == "search_mercari":
            # Call the search_mercari function in a separate thread (I/O-bound)
            keywords = args["keywords"]
            sort_order = args["sort_order"]
            return await asyncio.to_thread(search_mercari, keywords, sort_order)

        return None
    
    async def process_tool_calls(self, response):
        """
        Processes tool-based function calls from the OpenAI API response.
        Executes the functions and appends their results to the conversation history.
        """
        for tool_call in response.output:
            if tool_call.type != "function_call":
                continue  # Skip non-function-call responses

            # Extract the function name and arguments
            name = tool_call.name
            args = json.loads(tool_call.arguments)

            # Execute the function call and get the result
            result = await self.call_function(name, args)

            # Append the tool call output to the conversation history
            self.conversation_history.append({
                "role": "assistant",
                "content": f"Function '{name}' executed. Output: {json.dumps(result)}"
            })

            # Return the function name and result for further processing
            yield name, result

    async def process_tool_calls_recursively(self, tools):
        """
        Processes tool-based function calls recursively until no further calls are required.
        Updates the conversation history automatically after each tool call.
        """
        # Call OpenAI API with the current conversation history and tools
        response = await self.client.responses.create(
            model="gpt-4o",
            input=self.conversation_history,
            tools=tools,
            parallel_tool_calls=False  # Ensure tools are called sequentially
        )

        # Process each tool call in the response
        for tool_call in response.output:
            if tool_call.type != "function_call":
                continue  # Skip non-function-call responses

            # Extract the function name and arguments
            name = tool_call.name
            args = json.loads(tool_call.arguments)

            # Execute the function call and get the result
            result = await self.call_function(name, args)

            # Append the tool call output to the conversation history
            self.conversation_history.append({
                "role": "assistant",
                "content": f"Function '{name}' executed. Output: {json.dumps(result)}"
            })

            # If the result is the final recommendation, return it
            if name == "search_mercari" and result:
                return result

        # If no final result is found, call the function recursively
        return await self.process_tool_calls_recursively(tools)
    
    def get_time_stamp(self) -> str:
        # Get the current time in Japan
        now_in_japan = datetime.now(japan_tz)
        time_str = now_in_japan.strftime("%H:%M")
        
        return time_str
    
    async def stream_manual_message(self, message : str):
        for i in message:
            yield i
            await asyncio.sleep(0.06)