import { NextApiRequest, NextApiResponse } from 'next';
import { createClient } from '@supabase/supabase-js';
import { Configuration, OpenAIApi } from 'openai';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_KEY!
);

const openai = new OpenAIApi(
  new Configuration({
    apiKey: process.env.OPENAI_API_KEY,
  })
);

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ message: 'Method not allowed' });
  }

  try {
    const { message } = req.body;

    // Get embedding for the query
    const embeddingResponse = await openai.createEmbedding({
      model: "text-embedding-3-small",
      input: message,
    });
    const queryEmbedding = embeddingResponse.data.data[0].embedding;

    // Search for relevant docs
    const { data: docs } = await supabase.rpc('match_deepseek_pages', {
      query_embedding: queryEmbedding,
      match_count: 5,
    });

    // Format context from relevant docs
    const context = docs.map((doc: any) => `
      ${doc.title}
      Source: ${doc.url}
      ${doc.content}
    `).join('\n\n');

    // Get chat completion
    const completion = await openai.createChatCompletion({
      model: process.env.LLM_MODEL || "gpt-4",
      messages: [
        { role: "system", content: "You are an expert at DeepSeek..." },
        { role: "user", content: `Context: ${context}\n\nQuestion: ${message}` }
      ],
    });

    res.status(200).json({ response: completion.data.choices[0].message?.content });
  } catch (error) {
    console.error('Error:', error);
    res.status(500).json({ message: 'Internal server error' });
  }
} 