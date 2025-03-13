from flask import Flask, request, jsonify
from flask_cors import CORS
from dataclasses import dataclass
from dotenv import load_dotenv
import os
import asyncio
from openai import AsyncOpenAI
from supabase import Client, create_client

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
load_dotenv()

# Initialize clients
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

@dataclass
class DeepSeekDeps:
    supabase: Client
    openai_client: AsyncOpenAI

# Import your existing agent
from deepseek_agent import agentic_rag

async def get_agent_response(message: str):
    deps = DeepSeekDeps(
        supabase=supabase,
        openai_client=openai_client
    )
    
    async with agentic_rag.run_stream(
        message,
        deps=deps,
        message_history=[],  # You might want to implement session-based history
    ) as result:
        response_text = ""
        async for chunk in result.stream_text(delta=True):
            response_text += chunk
            
        return response_text

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        message = request.json.get('message')
        if not message:
            return jsonify({'error': 'No message provided'}), 400
            
        # Run the async function in the sync Flask context
        response = asyncio.run(get_agent_response(message))
        return jsonify({'response': response})
        
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000) 