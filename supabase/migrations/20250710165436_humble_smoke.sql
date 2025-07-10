/*
  # Add content hash for caching

  1. Schema Changes
    - Add `content_hash` column to `code_embeddings` table for caching
    - Add index on content_hash for fast lookups
  
  2. Performance
    - Enable faster duplicate detection
    - Support embedding caching
*/

-- Add content_hash column for caching
ALTER TABLE code_embeddings 
ADD COLUMN IF NOT EXISTS content_hash text;

-- Create index for fast hash lookups
CREATE INDEX IF NOT EXISTS idx_code_embeddings_content_hash 
ON code_embeddings(content_hash);

-- Create index for file_path lookups
CREATE INDEX IF NOT EXISTS idx_code_embeddings_file_path 
ON code_embeddings(file_path);

-- Create index for repository and branch
CREATE INDEX IF NOT EXISTS idx_code_embeddings_repo_branch 
ON code_embeddings(repository, branch);