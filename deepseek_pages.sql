-- Enable the pgvector extension to work with embeddings
create extension if not exists vector;

-- Create the deepseek_pages table
create table if not exists deepseek_pages (
    id bigint primary key generated always as identity,
    url text not null,
    chunk_number integer not null,
    title text,
    summary text,
    content text not null,
    metadata jsonb,
    embedding vector(1536),
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    unique(url, chunk_number)
);

-- Create a function to match similar documents
create or replace function match_deepseek_pages (
    query_embedding vector(1536),
    match_threshold float,
    match_count int
)
returns table (
    id bigint,
    url text,
    chunk_number integer,
    title text,
    summary text,
    content text,
    metadata jsonb,
    similarity float
)
language plpgsql
as $$
begin
    return query
    select
        deepseek_pages.id,
        deepseek_pages.url,
        deepseek_pages.chunk_number,
        deepseek_pages.title,
        deepseek_pages.summary,
        deepseek_pages.content,
        deepseek_pages.metadata,
        1 - (deepseek_pages.embedding <=> query_embedding) as similarity
    from deepseek_pages
    where 1 - (deepseek_pages.embedding <=> query_embedding) > match_threshold
    order by deepseek_pages.embedding <=> query_embedding
    limit match_count;
end;
$$;

-- Create an index for better vector similarity search performance
create index on deepseek_pages using ivfflat (embedding vector_cosine_ops);

-- Create an index on metadata for faster filtering
create index idx_deepseek_pages_metadata on deepseek_pages using gin (metadata);

-- Everything above will work for any PostgreSQL database. The below commands are for Supabase security

-- Enable RLS on the table
alter table deepseek_pages enable row level security;

-- Create a policy that allows anyone to read
create policy "Allow public read access"
  on deepseek_pages
  for select
  to public
  using (true);

-- Create a policy that allows authenticated users to insert
create policy "Allow authenticated insert"
  on deepseek_pages
  for insert
  to authenticated
  with check (true);

-- Create a policy that allows authenticated users to update
create policy "Allow authenticated update"
  on deepseek_pages
  for update
  to authenticated
  using (true)
  with check (true);