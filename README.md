# DeepSeek Agentic RAG

A hallucination-free AI system that automates extraction, validation, and natural language querying of DeepSeek's API documentation. By combining parallel web crawling (crawl4ai), vector storage (Supabase), and Pydantic AI's agentic capabilities, this system enables developers to interact with technical documentation conversationally while enforcing strict schema compliance to eliminate inaccuracies.

## Overview

This project demonstrates the power of Agentic RAG using Pydantic AI, creating a reliable documentation assistant that:
1. Automatically crawls and validates DeepSeek's API documentation using parallel processing
2. Enforces strict schema compliance during information extraction and storage
3. Provides a hallucination-free chat interface powered by GPT-4o-mini
4. Uses autonomous reasoning with built-in accuracy constraints for API endpoint descriptions

## What is Agentic RAG?

Agentic RAG extends traditional RAG systems by incorporating autonomous decision-making capabilities and schema validation:
- **Traditional RAG** simply retrieves relevant documents and generates responses, risking hallucinations
- **Agentic RAG** using Pydantic AI can:
  - Enforce strict schema compliance for API documentation
  - Validate information against known patterns and structures
  - Autonomously decide what information to retrieve
  - Chain multiple retrievals for complex technical queries
  - Reason about the relevance and accuracy of retrieved information
  - Dynamically adjust search strategies while maintaining accuracy
  - Maintain conversation context across multiple turns

## Architecture

The system consists of several key components:

### 1. Documentation Crawler (`crawl_deepseek_docs.py`)
- Crawls DeepSeek's documentation using `crawl4ai`
- Processes documentation into chunks
- Generates embeddings using OpenAI's embedding model
- Stores processed chunks in Supabase

### 2. Vector Database (`deepseek_pages.sql`)
- PostgreSQL with pgvector extension
- Stores documentation chunks with:
  - Text content
  - Embeddings
  - Metadata
  - URLs and titles
- Provides similarity search functionality

### 3. Agent Framework (`deepseek_agent.py`)
- Implements Agentic RAG logic using the Pydantic AI framework
- Defines agent tools and behaviors for:
  - Intelligent documentation retrieval
  - Context-aware page listing
  - Dynamic content fetching
  - Autonomous reasoning about user queries
- Uses OpenAI's models for embeddings and responses
- Maintains conversation state and context

### 4. Web Interface (`streamlit_deepseek.py`)
- Streamlit-based chat interface
- Real-time streaming responses
- Message history management
- Clean and intuitive UI

## Prerequisites

- Python 3.8+
- PostgreSQL with pgvector extension
- Supabase account
- OpenAI API key

## Environment Variables

Create a `.env` file with:

```
OPENAI_API_KEY=your_openai_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_KEY=your_supabase_service_key
LLM_MODEL=gpt-4o-mini  # or your preferred OpenAI model
```

## Installation

1. Clone the repository:
```bash
gh repo clone aravpatel19/deepseek-agentic-rag
cd deepseek-agentic-rag
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up the database:
- Create a Supabase project
- Run the SQL commands from `deepseek_pages.sql`

## Usage

1. Crawl and process documentation:
```bash
python crawl_deepseek_docs.py
```

2. Start the Streamlit interface:
```bash
streamlit run streamlit_deepseek.py
```

3. Access the web interface at `http://localhost:8501`

## How It Works

1. **Documentation Processing**:
   - The crawler fetches documentation from DeepSeek's sitemap
   - Content is split into manageable chunks
   - Each chunk gets a title, summary, and embedding vector
   - Chunks are stored in Supabase with metadata

2. **Agentic Query Processing**:
   - User questions are analyzed by the Pydantic AI agent
   - The agent autonomously decides on the retrieval strategy
   - Questions are converted to embeddings
   - Similar documentation chunks are retrieved
   - The agent reasons about the relevance of retrieved information
   - The LLM generates accurate answers based on the agent's analysis
   - Responses are streamed in real-time

3. **Vector Search**:
   - Uses cosine similarity to find relevant documentation
   - Supports filtering by metadata
   - Returns top matches for each query
   - Agent can dynamically adjust search parameters based on context

## Project Structure

```
.
├── README.md
├── crawl_deepseek_docs.py    # Documentation crawler
├── deepseek_agent.py         # RAG agent implementation
├── deepseek_pages.sql        # Database schema
├── streamlit_deepseek.py     # Web interface
└── .env                      # Environment variables
```

## Dependencies

Key libraries and frameworks used:
- `pydantic-ai`: Core framework for implementing the agentic RAG system
- `crawl4ai`: Parallel web crawling with semantic filtering capabilities
- `openai`: API access for embeddings (text-embedding-3-small) and LLM (GPT-4o-mini)
- `supabase`: Vector database with pgvector for similarity search
- `streamlit`: Web interface with real-time streaming
- `logfire`: Optional logging configuration
- `asyncio`: Asynchronous operations for improved performance
- `httpx`: Modern HTTP client for async operations

## Technical Details

### Embedding System
- Uses OpenAI's `text-embedding-3-small` model
- 1536-dimensional embedding vectors
- Fallback to zero vector on embedding errors
- Cosine similarity for vector search

### Chunking Strategy
- Intelligent text chunking with respect to:
  - Code block boundaries (```)
  - Paragraph breaks (\n\n)
  - Sentence boundaries (. )
- Default chunk size: 5000 characters
- Minimum chunk threshold for quality control
- Preserves code block integrity

### Database Schema
- PostgreSQL with pgvector extension
- Optimized indexes for vector similarity search
- JSON metadata for flexible filtering
- Unique constraints on URL and chunk number
- Row-level security enabled for Supabase integration

### Error Handling
- Graceful degradation for embedding failures
- Comprehensive exception handling in crawler
- Retry mechanism for agent operations (2 retries)
- Detailed error logging and user feedback

## Security Considerations

1. Environment Variables
   - All sensitive credentials stored in `.env`
   - API keys never exposed in the frontend
   - Supabase RLS (Row Level Security) enabled

2. Database Access
   - Read-only public access to documentation
   - Protected write operations
   - Metadata filtering for security boundaries

## Performance Optimization

1. Parallel Processing
   - Concurrent document crawling
   - Parallel chunk processing
   - Asynchronous database operations

2. Database Optimization
   - IVFFlat index for vector search
   - GIN index for metadata queries
   - Optimized chunk size for retrieval

## Deployment

### Supabase Setup
1. Create a new Supabase project
2. Enable the pgvector extension
3. Run the schema from `deepseek_pages.sql`
4. Set up row-level security policies

### Application Deployment
1. Set up environment variables
2. Install dependencies
3. Initialize the database
4. Run the crawler
5. Start the Streamlit server

## Monitoring and Maintenance

1. Logging
   - Crawler progress and errors
   - Embedding generation status
   - Database operation results
   - Agent interaction logs

2. Regular Tasks
   - Update documentation chunks
   - Monitor embedding quality
   - Check for API rate limits
   - Verify database indexes

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

### Third-Party Licenses
- Pydantic AI: Apache 2.0
- Streamlit: Apache 2.0
- OpenAI API: Proprietary
- Supabase: Apache 2.0
- crawl4ai: MIT

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

### Development Guidelines
- Follow PEP 8 style guide
- Add docstrings for new functions
- Include type hints
- Write unit tests for new features
- Update documentation as needed

## Support

For support, please:
1. Check the existing documentation
2. Search for similar issues
3. Create a new issue with:
   - Clear description
   - Steps to reproduce
   - Expected vs actual behavior

## Acknowledgments

- Built with [Pydantic AI](https://github.com/pydantic/pydantic-ai)
- Uses [Streamlit](https://streamlit.io/) for the web interface
- Powered by [OpenAI](https://openai.com/) models
- Database hosted on [Supabase](https://supabase.com/)
- Crawling powered by [crawl4ai](https://github.com/your-username/crawl4ai)

## Citation

If you use this project in your research or work, please cite:

```bibtex
@software{deepseek_agentic_rag,
  title = {DeepSeek Agentic RAG},
  author = {Arav Patel},
  year = {2024},
  description = {A hallucination-free AI system for DeepSeek API documentation},
  url = {https://github.com/aravpatel19/deepseek-agentic-rag}
}
```
