from openai import AsyncOpenAI
import asyncio
from typing import List, Dict, Union
import os

# Initialize the AsyncOpenAI client
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

from utils.prompt import EXTRACT_KEYWORDS_PROMPT

async def extract_keywords_and_sort_order(conversation: List[Dict[str, str]], max_keywords: int = 4) -> Dict[str, Union[List[str], str]]:
    """
    Asynchronously analyze a conversation and extract up to `max_keywords` for searching items,
    along with the sort order.

    Args:
        conversation (List[Dict[str, str]]): The conversation history, where each message is a dictionary
                                             with "role" (e.g., "user", "assistant") and "content".
        max_keywords (int): The maximum number of keywords to extract.

    Returns:
        Dict[str, Union[List[str], str]]: A dictionary containing extracted keywords and the sort order.
    """
    try:
        # Add a system message to guide the assistant
        system_message = {
            "role": "system",
            "content": EXTRACT_KEYWORDS_PROMPT
        }

        # Combine the system message with the conversation
        messages = [system_message] + conversation

        # Call OpenAI's ChatCompletion API asynchronously
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=100,
            temperature=0.5,
        )

        # Extract the response content
        response_content = response.choices[0].message.content.strip()

        # Split the response into keywords and sort order
        lines = response_content.split("\n")
        keywords = lines[0].split()  # Space-separated keywords
        sort_order = lines[1] if len(lines) > 1 and lines[1].strip() else "score:desc"  # Default to "score:desc" if not provided

        # Limit the number of keywords to the specified max_keywords
        print(f"Extracted Keywords: {keywords}, Sort Order: {sort_order}")
        return {"keywords": keywords[:max_keywords], "sort_order": sort_order}

    except Exception as e:
        print(f"Error extracting keywords and sort order: {e}")
        return {"keywords": [], "sort_order": "score:desc"}

# async def main():
#     # Example conversation
#     conversation = [
#         {"role": "user", "content": "こんにちは！スノーボードのおすすめ商品を教えてください！"},
#         {"role": "assistant", "content": "どのようなスノーボードをお探しですか？"},
#         {"role": "user", "content": "初心者向けで、価格が手頃なものがいいです。"}
#     ]

#     # Call the extract_keywords function
#     keywords = await extract_keywords_and_sort_order(conversation)
#     print(f"Extracted Keywords: {keywords}")

#     # Call the extract_keywords_and_sort_order function
#     result = await extract_keywords_and_sort_order(conversation)
#     print(f"Extracted Keywords and Sort Order: {result}")

# asyncio.run(main())