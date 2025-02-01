from __future__ import annotations as _annotations

from dataclasses import dataclass
from dotenv import load_dotenv
import logfire
import asyncio
import httpx
import os

from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.models.openai import OpenAIModel
from openai import AsyncOpenAI
from supabase import Client
from typing import List

load_dotenv()

llm = os.getenv('LLM_MODEL', 'gpt-4o-mini')
model = OpenAIModel(llm)

logfire.configure(send_to_logfire='if-token-present')

@dataclass
class DeepSeekDeps:  # Changed from PydanticAIDeps
    supabase: Client
    openai_client: AsyncOpenAI
    
system_prompt = """
You are an expert at DeepSeek - an LLM agent framework. You have access to all the documentation including API references, 
examples, and guides. Your primary role is to assist users with DeepSeek-related queries using the provided documentation tools.

Always follow these rules:
1. Start with RAG search using retrieve_relevant_documentation
2. If needed, use list_documentation_pages to explore available content
3. Use get_page_content for specific page retrieval
4. Always cite sources with exact URLs
5. Be transparent about missing information
"""

agentic_rag = Agent(
    model=model,
    system_prompt=system_prompt,
    deps_type=DeepSeekDeps,  # Updated deps type
    retries=2
)

async def get_embedding(text: str, openai_client: AsyncOpenAI) -> List[float]:
    """Get embedding vector from OpenAI."""
    try:
        response = await openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error getting embedding: {e}")
        return [0] * 1536
    
@agentic_rag.tool
async def retrieve_relevant_documentation(ctx: RunContext[DeepSeekDeps], user_query: str) -> str:
    """
    Retrieve relevant DeepSeek documentation chunks using vector similarity search

    Args:
        ctx: Context with Supabase and OpenAI clients
        user_query: User's question/query

    Returns:
        str: Top 5 relevant documentation chunks with sources
    """
    try:
        query_embedding = await get_embedding(user_query, ctx.deps.openai_client)
        
        result = ctx.deps.supabase.rpc('match_deepseek_pages', {
            'query_embedding': query_embedding,
            'match_count': 5,
            'filter': {'source': 'deepseek_docs'}  # Updated source filter
        }).execute()
        
        if not result.data:
            return "No relevant documentation found."
        
        formatted_chunks = []
        for doc in result.data:
            chunk_text = f"""## {doc['title']}
            Source: {doc['url']}
            {doc['content'][:1000]}..."""
            formatted_chunks.append(chunk_text)
            
        return "\n\n---\n\n".join(formatted_chunks)
    
    except Exception as e:
        print(f"Documentation retrieval error: {e}")
        return f"Error: {str(e)}"
    
@agentic_rag.tool
async def list_documentation_pages(ctx: RunContext[DeepSeekDeps]) -> List[str]:
    """
    Get all available DeepSeek documentation URLs
    
    Returns:
        List[str]: Unique documentation page URLs
    """
    try:
        result = ctx.deps.supabase.from_('deepseek_pages') \
            .select('url') \
            .eq('metadata->>source', 'deepseek_docs') \
            .execute()
            
        return sorted(set(doc['url'] for doc in result.data)) if result.data else []
    
    except Exception as e:
        print(f"URL listing error: {e}")
        return []

@agentic_rag.tool
async def get_page_content(ctx: RunContext[DeepSeekDeps], url: str) -> str:
    """
    Retrieve full content of a DeepSeek documentation page
    
    Args:
        url: Valid DeepSeek documentation URL
        
    Returns:
        str: Complete page content with chunks ordered
    """
    try:
        result = ctx.deps.supabase.from_('deepseek_pages') \
            .select('title,content,chunk_number') \
            .eq('url', url) \
            .order('chunk_number') \
            .execute()
        
        if not result.data:
            return f'No content found for: {url}'
        
        content = [f"# {result.data[0]['title']}"]
        content.extend(chunk['content'] for chunk in result.data)
        return '\n\n'.join(content)
    
    except Exception as e:
        print(f"Content retrieval error: {e}")
        return f"Error: {str(e)}"