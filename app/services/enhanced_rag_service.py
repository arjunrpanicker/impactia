import os
import zipfile
import tempfile
import asyncio
from typing import Dict, Any, List, Tuple, Optional
from fastapi import UploadFile
from ..models.analysis import IndexingResult, CodeChange
from ..interfaces.vector_store import VectorStore, EmbeddingService
from ..services.supabase_vector_store import SupabaseVectorStore
from ..services.enhanced_embedding_service import AzureEmbeddingService

class EnhancedRAGService:
    """Enhanced RAG service with better architecture and performance"""
    
    def __init__(self, vector_store: VectorStore = None, embedding_service: EmbeddingService = None):
        self.vector_store = vector_store or SupabaseVectorStore()
        self.embedding_service = embedding_service or AzureEmbeddingService()
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment or defaults"""
        return {
            "batch_size": int(os.getenv("RAG_BATCH_SIZE", "20")),
            "max_file_size": int(os.getenv("RAG_MAX_FILE_SIZE", "102400")),  # 100KB
            "similarity_threshold": float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.7")),
            "skip_tests": os.getenv("RAG_SKIP_TESTS", "true").lower() == "true",
            "max_content_length": int(os.getenv("RAG_MAX_CONTENT_LENGTH", "24000")),
            "supported_extensions": os.getenv("RAG_SUPPORTED_EXTENSIONS", 
                ".py,.js,.ts,.cs,.java,.cpp,.go,.html,.css,.scss,.yaml,.yml,.json").split(",")
        }
    
    async def index_repository(self, file: UploadFile) -> IndexingResult:
        """Index repository with enhanced error handling and performance"""
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Extract repository
                code_files = await self._extract_and_filter_files(file, temp_dir)
                
                if not code_files:
                    return IndexingResult(indexed_files=0, total_methods=0, embedding_count=0)
                
                # Process files in parallel batches
                return await self._process_files_in_batches(code_files)
                
        except Exception as e:
            raise Exception(f"Failed to index repository: {str(e)}")
    
    async def _extract_and_filter_files(self, file: UploadFile, temp_dir: str) -> List[Tuple[str, str]]:
        """Extract and filter code files from uploaded repository"""
        zip_path = os.path.join(temp_dir, "repo.zip")
        
        # Save uploaded file
        with open(zip_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Extract zip file
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Filter and collect code files
        code_files = []
        for root, _, files in os.walk(temp_dir):
            for filename in files:
                if self._should_process_file(filename, root):
                    file_path = os.path.join(root, filename)
                    relative_path = os.path.relpath(file_path, temp_dir)
                    
                    # Validate file
                    if await self._validate_file(file_path):
                        code_files.append((file_path, relative_path))
        
        return code_files
    
    def _should_process_file(self, filename: str, root: str) -> bool:
        """Enhanced file filtering logic"""
        # Check extension
        if not any(filename.lower().endswith(ext) for ext in self.config["supported_extensions"]):
            return False
        
        # Skip hidden files
        if filename.startswith('.'):
            return False
        
        # Skip test files if configured
        if self.config["skip_tests"]:
            test_patterns = ['test.', '.test.', '.spec.', '.tests.', 'mock.', '.mock.']
            if any(pattern in filename.lower() for pattern in test_patterns):
                return False
        
        # Skip binary and generated directories
        skip_patterns = {
            'node_modules/', '/dist/', '/build/', '/bin/', '/obj/',
            '/vendor/', '/.git/', '/.vs/', '/.idea/', '/wwwroot/'
        }
        
        normalized_path = root.replace('\\', '/').lower()
        return not any(pattern in normalized_path + '/' for pattern in skip_patterns)
    
    async def _validate_file(self, file_path: str) -> bool:
        """Validate file before processing"""
        try:
            # Check file size
            if os.path.getsize(file_path) > self.config["max_file_size"]:
                return False
            
            # Try to read first few lines to ensure it's text
            with open(file_path, 'r', encoding='utf-8') as f:
                f.read(1024)  # Read first 1KB
            
            return True
        except (IOError, UnicodeDecodeError, OSError):
            return False
    
    async def _process_files_in_batches(self, code_files: List[Tuple[str, str]]) -> IndexingResult:
        """Process files in parallel batches for better performance"""
        total_files = len(code_files)
        indexed_files = 0
        total_methods = 0
        embedding_count = 0
        
        print(f"Processing {total_files} files in batches of {self.config['batch_size']}...")
        
        for i in range(0, len(code_files), self.config["batch_size"]):
            batch = code_files[i:i + self.config["batch_size"]]
            
            # Process batch in parallel
            batch_results = await asyncio.gather(
                *[self._process_single_file(file_path, relative_path) 
                  for file_path, relative_path in batch],
                return_exceptions=True
            )
            
            # Aggregate results
            for result in batch_results:
                if isinstance(result, Exception):
                    print(f"Error in batch processing: {result}")
                    continue
                
                if result:
                    indexed_files += 1
                    total_methods += result[0]
                    embedding_count += result[1]
            
            print(f"Processed {min(i + self.config['batch_size'], total_files)}/{total_files} files...")
        
        return IndexingResult(
            indexed_files=indexed_files,
            total_methods=total_methods,
            embedding_count=embedding_count
        )
    
    async def _process_single_file(self, file_path: str, relative_path: str) -> Optional[Tuple[int, int]]:
        """Process a single file with enhanced error handling"""
        try:
            # Read file content with multiple encoding attempts
            content = await self._read_file_safely(file_path)
            if not content:
                return None
            
            # Extract methods
            methods = self._extract_methods(content)
            
            # Truncate content if too long
            if len(content) > self.config["max_content_length"]:
                content = content[:self.config["max_content_length"]] + "\n... (truncated)"
            
            # Generate embeddings
            embeddings = await self.embedding_service.get_embeddings(content)
            
            # Store in vector database
            await self.vector_store.store_embeddings(
                embeddings=embeddings,
                metadata={
                    "type": "file",
                    "path": relative_path,
                    "size": len(content),
                    "methods": [
                        {
                            "name": method["name"],
                            "content": method["content"],
                            "start_line": method.get("start_line", 0)
                        }
                        for method in methods
                    ],
                    "file_type": os.path.splitext(relative_path)[1].lower()
                },
                content=content,
                file_path=relative_path,
                code_type="file"
            )
            
            return len(methods), 1
            
        except Exception as e:
            print(f"Error processing file {relative_path}: {str(e)}")
            return None
    
    async def _read_file_safely(self, file_path: str) -> Optional[str]:
        """Safely read file with multiple encoding attempts"""
        encodings = ['utf-8', 'utf-16', 'latin1', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                    
                    # Check for binary content
                    if '\x00' in content or sum(not c.isprintable() and c not in '\n\r\t' 
                                              for c in content) > len(content) * 0.1:
                        return None
                    
                    return content
            except (UnicodeDecodeError, IOError):
                continue
        
        return None
    
    def _extract_methods(self, content: str) -> List[Dict[str, str]]:
        """Extract methods from code content - reuse existing implementation"""
        # This would use the existing method extraction logic
        # from the original RAGService
        import re
        
        methods = []
        lines = content.split('\n')
        
        patterns = [
            (r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)\s*:', 1),
            (r'(async\s+)?function\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)', 2),
            (r'(public|private|protected|internal)?\s+[a-zA-Z_<>[\]]+\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)', 2),
        ]
        
        for i, line in enumerate(lines, 1):
            for pattern, group_idx in patterns:
                matches = re.finditer(pattern, line)
                for match in matches:
                    method_name = match.group(group_idx)
                    
                    # Extract method content (simplified)
                    start_line = max(0, i - 5)
                    end_line = min(len(lines), i + 50)
                    method_content = '\n'.join(lines[start_line:end_line])
                    
                    methods.append({
                        "name": method_name,
                        "content": method_content,
                        "start_line": i
                    })
        
        return methods
    
    async def get_related_code(self, changes: List[CodeChange]) -> Dict[str, Any]:
        """Enhanced related code retrieval with better performance"""
        try:
            # Prepare search query
            combined_text = self._prepare_search_query(changes)
            
            # Generate embedding for search
            query_embedding = await self.embedding_service.get_embeddings(combined_text)
            
            # Search for similar code
            similar_results = await self.vector_store.search_similar(
                query_embedding, 
                limit=15, 
                threshold=self.config["similarity_threshold"]
            )
            
            # Search for direct references
            changed_files = [change.file_path for change in changes]
            reference_results = await self._search_references_enhanced(changed_files)
            
            return self._format_related_code_results(similar_results, reference_results, changed_files)
            
        except Exception as e:
            raise Exception(f"Failed to get related code: {str(e)}")
    
    def _prepare_search_query(self, changes: List[CodeChange]) -> str:
        """Prepare optimized search query from changes"""
        query_parts = []
        
        for change in changes:
            if change.diff:
                # Extract meaningful parts from diff
                query_parts.append(f"File: {change.file_path}")
                # Add method names and key changes from diff
                lines = change.diff.split('\n')
                for line in lines:
                    if line.startswith('+') and ('def ' in line or 'function ' in line):
                        query_parts.append(line[1:].strip())
            elif change.content:
                # Use truncated content for search
                truncated = change.content[:1000] if len(change.content) > 1000 else change.content
                query_parts.append(f"File: {change.file_path}\n{truncated}")
        
        return '\n'.join(query_parts)
    
    async def _search_references_enhanced(self, file_paths: List[str]) -> Dict[str, Any]:
        """Enhanced reference search with better performance"""
        # This would implement more sophisticated reference detection
        # using the vector store's search capabilities
        return await self.vector_store.search_by_content(' '.join(file_paths), file_paths)
    
    def _format_related_code_results(self, similar_results: List[Dict], 
                                   reference_results: Dict[str, Any], 
                                   changed_files: List[str]) -> Dict[str, Any]:
        """Format the results into the expected structure"""
        return {
            "changed_files": changed_files,
            "similar_code": {
                "files": [
                    {
                        "path": item.get("metadata", {}).get("path", ""),
                        "content": item.get("content", ""),
                        "similarity": item.get("similarity", 0.0),
                        "methods": item.get("metadata", {}).get("methods", [])
                    }
                    for item in similar_results
                ],
                "methods": []  # Could be enhanced to extract method-level similarities
            },
            "direct_dependencies": reference_results,
            "dependency_chains": [],
            "dependency_visualization": []
        }