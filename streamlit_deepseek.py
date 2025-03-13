from __future__ import annotations
from typing import Literal, TypedDict
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

import streamlit as st
import json
import logfire
from supabase import Client
from openai import AsyncOpenAI

# Import all the message part classes
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    UserPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    RetryPromptPart,
    ModelMessagesTypeAdapter
)
from deepseek_agent import agentic_rag, DeepSeekDeps  # Changed import

# Get the directory containing the script
script_dir = Path(__file__).resolve().parent

# Load .env file from the same directory as the script
env_path = script_dir / '.env'
load_dotenv(dotenv_path=env_path)

# Debug: Print where we're loading from
print(f"Loading .env file from: {env_path}")
print(f"SUPABASE_URL: {'[SET]' if os.getenv('SUPABASE_URL') else '[NOT SET]'}")
print(f"SUPABASE_SERVICE_KEY: {'[SET]' if os.getenv('SUPABASE_SERVICE_KEY') else '[NOT SET]'}")
print(f"OPENAI_API_KEY: {'[SET]' if os.getenv('OPENAI_API_KEY') else '[NOT SET]'}")

# Initialize Supabase client with environment variables
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")

if not supabase_url or not supabase_key or not openai_api_key:
    raise ValueError(
        "Missing required credentials. Please ensure SUPABASE_URL, "
        "SUPABASE_SERVICE_KEY, and OPENAI_API_KEY are set in your .env file"
    )

# Initialize the clients
supabase = Client(supabase_url, supabase_key)
openai_client = AsyncOpenAI(api_key=openai_api_key)

# Configure logfire to suppress warnings (optional)
logfire.configure(send_to_logfire='never')

class ChatMessage(TypedDict):
    """Format of messages sent to the browser/API."""
    role: Literal['user', 'model']
    timestamp: str
    content: str

def display_message_part(part):
    """Display a single part of a message in the Streamlit UI."""
    if part.part_kind == 'system-prompt':
        with st.chat_message("system"):
            st.markdown(f"**System**: {part.content}")
    elif part.part_kind == 'user-prompt':
        with st.chat_message("user"):
            st.markdown(part.content)
    elif part.part_kind == 'text':
        with st.chat_message("assistant"):
            st.markdown(part.content)          

async def run_agent_with_streaming(user_input: str):
    """Run the agent with streaming text for DeepSeek queries."""
    deps = DeepSeekDeps(  # Changed class
        supabase=supabase,
        openai_client=openai_client
    )

    async with agentic_rag.run_stream(
        user_input,
        deps=deps,
        message_history=st.session_state.messages[:-1],
    ) as result:
        partial_text = ""
        message_placeholder = st.empty()

        async for chunk in result.stream_text(delta=True):
            partial_text += chunk
            message_placeholder.markdown(partial_text)

        filtered_messages = [msg for msg in result.new_messages() 
                            if not (hasattr(msg, 'parts') and 
                                    any(part.part_kind == 'user-prompt' for part in msg.parts))]
        st.session_state.messages.extend(filtered_messages)

        st.session_state.messages.append(
            ModelResponse(parts=[TextPart(content=partial_text)])
        )

async def main():
    st.title("DeepSeek Agentic RAG")  # Updated title
    st.write("Ask any question about DeepSeek's documentation including API references, guides, and best practices. Made by Arav Patel")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        if isinstance(msg, ModelRequest) or isinstance(msg, ModelResponse):
            for part in msg.parts:
                display_message_part(part)

    user_input = st.chat_input("What questions do you have about DeepSeek's documentation?")  # Updated prompt

    if user_input:
        st.session_state.messages.append(
            ModelRequest(parts=[UserPromptPart(content=user_input)])
        )
        
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            await run_agent_with_streaming(user_input)

if __name__ == "__main__":
    asyncio.run(main())