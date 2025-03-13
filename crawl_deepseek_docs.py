import os
import sys
import json
import asyncio
import requests
import argparse
from xml.etree import ElementTree
from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse
from pathlib import Path
from dotenv import load_dotenv

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from openai import AsyncOpenAI
from supabase import create_client, Client

# Get the directory containing the script
script_dir = Path(__file__).resolve().parent

# Load .env file from the same directory as the script
env_path = script_dir / '.env'
load_dotenv(dotenv_path=env_path)

# Debug: Print where we're loading from
print(f"Loading .env file from: {env_path}")
print(f"SUPABASE_URL: {'[SET]' if os.getenv('SUPABASE_URL') else '[NOT SET]'}")
print(f"SUPABASE_SERVICE_KEY: {'[SET]' if os.getenv('SUPABASE_SERVICE_KEY') else '[NOT SET]'}")

# Initialize Supabase client with environment variables
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

if not supabase_url or not supabase_key:
    raise ValueError(
        "Missing Supabase credentials. Please ensure SUPABASE_URL and "
        "SUPABASE_SERVICE_KEY are set in your .env file"
    )

# Initialize OpenAI and Supabase clients
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
supabase: Client = create_client(
    supabase_url,
    supabase_key
)

# Debug: Check database connection and table existence
try:
    print("\nChecking database connection and tables...")
    # Try to directly query the deepseek_pages table
    test_query = supabase.table("deepseek_pages").select("id").limit(1).execute()
    print("Successfully connected to deepseek_pages table")
    
    print("\nTesting table permissions...")
    # Try a simple count query
    count_query = supabase.table("deepseek_pages").select("*", count="exact").execute()
    print(f"Current number of records in table: {count_query.count}")

except Exception as e:
    print(f"\nDatabase connection error: {str(e)}")
    sys.exit(1)

@dataclass
class ProcessedChunk:
    url: str
    chunk_number: int
    title: str
    summary: str
    content: str
    metadata: Dict[str, Any]
    embedding: List[float]

def chunk_text(text: str, chunk_size: int = 5000) -> List[str]:
    """Split text into chunks, respecting code blocks and paragraphs."""
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        # Calculate end position
        end = start + chunk_size

        # If we're at the end of the text, just take what's left
        if end >= text_length:
            chunks.append(text[start:].strip())
            break

        # Try to find a code block boundary first (```)
        chunk = text[start:end]
        code_block = chunk.rfind('```')
        if code_block != -1 and code_block > chunk_size * 0.3:
            end = start + code_block

        # If no code block, try to break at a paragraph
        elif '\n\n' in chunk:
            # Find the last paragraph break
            last_break = chunk.rfind('\n\n')
            if last_break > chunk_size * 0.3:  # Only break if we're past 30% of chunk_size
                end = start + last_break

        # If no paragraph break, try to break at a sentence
        elif '. ' in chunk:
            # Find the last sentence break
            last_period = chunk.rfind('. ')
            if last_period > chunk_size * 0.3:  # Only break if we're past 30% of chunk_size
                end = start + last_period + 1

        # Extract chunk and clean it up
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Move start position for next chunk
        start = max(start + 1, end)

    return chunks

async def get_title_and_summary(chunk: str, url: str) -> Dict[str, str]:
    """Extract title and summary using GPT-4."""
    system_prompt = """You are an AI that extracts titles and summaries from documentation chunks.
    Return a JSON object with 'title' and 'summary' keys.
    For the title: If this seems like the start of a document, extract its title. If it's a middle chunk, derive a descriptive title.
    For the summary: Create a concise summary of the main points in this chunk.
    Keep both title and summary concise but informative."""
    
    try:
        response = await openai_client.chat.completions.create(
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"URL: {url}\n\nContent:\n{chunk[:1000]}..."}  # Send first 1000 chars for context
            ],
            response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)
    
    except Exception as e:
        print(f"Error getting title and summary: {e}")
        return {"title": "Error processing title", "summary": "Error processing summary"}

async def get_embedding(text: str) -> List[float]:
    """Get embedding vector from OpenAI."""
    try:
        response = await openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    
    except Exception as e:
        print(f"Error getting embedding: {e}")
        return [0] * 1536  # Return zero vector on error

async def process_chunk(chunk: str, chunk_number: int, url: str) -> ProcessedChunk:
    """Process a single chunk of text."""
    # Get title and summary
    extracted = await get_title_and_summary(chunk, url)
    
    # Get embedding
    embedding = await get_embedding(chunk)
    
    # Create metadata
    metadata = {
        "source": "deepseek_docs",  # Changed from pydantic_ai_docs
        "chunk_size": len(chunk),
        "crawled_at": datetime.now(timezone.utc).isoformat(),
        "url_path": urlparse(url).path
    }
    
    return ProcessedChunk(
        url=url,
        chunk_number=chunk_number,
        title=extracted['title'],
        summary=extracted['summary'],
        content=chunk,  # Store the original chunk content
        metadata=metadata,
        embedding=embedding
    )

async def insert_chunk(chunk: ProcessedChunk, update_existing: bool = False):
    """Insert or update a processed chunk in Supabase."""
    try:
        # First, check if the chunk already exists
        print(f"\nChecking chunk existence for:")
        print(f"URL: {chunk.url}")
        print(f"Chunk number: {chunk.chunk_number}")
        
        existing = supabase.table("deepseek_pages")\
            .select("*")\
            .eq("url", chunk.url)\
            .eq("chunk_number", chunk.chunk_number)\
            .execute()
        
        print(f"Database response:")
        print(f"Data: {existing.data}")
        print(f"Count: {len(existing.data)}")
        
        data = {
            "url": chunk.url,
            "chunk_number": chunk.chunk_number,
            "title": chunk.title,
            "summary": chunk.summary,
            "content": chunk.content,
            "metadata": chunk.metadata,
            "embedding": chunk.embedding
        }
        
        if existing.data:
            if update_existing:
                print(f"Updating existing chunk...")
                result = supabase.table("deepseek_pages")\
                    .update(data)\
                    .eq("url", chunk.url)\
                    .eq("chunk_number", chunk.chunk_number)\
                    .execute()
                print(f"Update complete")
            else:
                print(f"Skipping existing chunk")
                return None
        else:
            print(f"Inserting new chunk...")
            result = supabase.table("deepseek_pages")\
                .insert(data)\
                .execute()
            print(f"Insert complete")
            
        return result
    
    except Exception as e:
        print(f"\nError in database operation:")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print(f"For chunk: URL={chunk.url}, Number={chunk.chunk_number}")
        return None

async def process_and_store_document(url: str, markdown: str, update_existing: bool = False):
    """Process a document and store its chunks in parallel."""
    # Split into chunks
    chunks = chunk_text(markdown)
    
    # Process chunks in parallel
    tasks = [
        process_chunk(chunk, i, url) 
        for i, chunk in enumerate(chunks)
    ]
    processed_chunks = await asyncio.gather(*tasks)
    
    # Store chunks in parallel
    insert_tasks = [
        insert_chunk(chunk, update_existing) 
        for chunk in processed_chunks
    ]
    await asyncio.gather(*insert_tasks)

async def crawl_parallel(urls: List[str], max_concurrent: int = 5, update_existing: bool = False):
    """Crawl multiple URLs in parallel with a concurrency limit."""
    browser_config = BrowserConfig(
        headless=True,
        verbose=False,
        extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"],
    )
    crawl_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)

    # Create the crawler instance
    crawler = AsyncWebCrawler(config=browser_config)
    await crawler.start()

    try:
        # Create a semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_url(url: str):
            async with semaphore:
                result = await crawler.arun(
                    url=url,
                    config=crawl_config,
                    session_id="session1"
                )
                if result.success:
                    print(f"Successfully crawled: {url}")
                    await process_and_store_document(url, result.markdown_v2.raw_markdown, update_existing)
                else:
                    print(f"Failed: {url} - Error: {result.error_message}")
        
        # Process all URLs in parallel with limited concurrency
        await asyncio.gather(*[process_url(url) for url in urls])
    finally:
        await crawler.close()

def get_deepseek_docs_urls() -> List[str]:  # Renamed from get_pydantic_ai_docs_urls
    """Get URLs from DeepSeek docs sitemap."""
    sitemap_url = "https://api-docs.deepseek.com/sitemap.xml"
    try:
        response = requests.get(sitemap_url)
        response.raise_for_status()
        
        # Parse the XML
        root = ElementTree.fromstring(response.content)
        
        # Extract all URLs from the sitemap
        # Namespace remains the same despite additional xmlns declarations
        namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        urls = [loc.text for loc in root.findall('.//ns:loc', namespace)]
        
        return urls
    except Exception as e:
        print(f"Error fetching sitemap: {e}")
        return []

async def main():
    parser = argparse.ArgumentParser(description='Crawl DeepSeek documentation')
    parser.add_argument('--update-existing', action='store_true',
                       help='Update existing documents instead of skipping')
    parser.add_argument('--max-concurrent', type=int, default=5,
                       help='Maximum number of concurrent crawls')
    args = parser.parse_args()

    # Get URLs from DeepSeek docs
    urls = get_deepseek_docs_urls()
    if not urls:
        print("No URLs found to crawl")
        return
    
    print(f"Found {len(urls)} URLs to crawl")
    await crawl_parallel(urls, max_concurrent=args.max_concurrent, update_existing=args.update_existing)

if __name__ == "__main__":
    asyncio.run(main())