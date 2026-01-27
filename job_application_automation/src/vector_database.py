"""
Vector database management using FAISS for efficient similarity search.
"""
import os
import pickle
import numpy as np
import faiss
import logging
import json
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional, Union, Callable
from datetime import datetime
from functools import lru_cache, wraps
import time
from sentence_transformers import SentenceTransformer
from src.database_errors import handle_db_errors, with_retry
from job_application_automation.config.config import get_config

# Set up logging
logger = logging.getLogger(__name__)

# Default paths from centralized config
CONFIG = get_config()
DEFAULT_INDEX_DIR = Path(CONFIG.data_dir) / "vector_indices"
DEFAULT_EMBEDDINGS_CACHE = Path(CONFIG.data_dir) / "embeddings_cache"

# Function to time vector operations for performance monitoring
def time_vector_operation(operation_name: str):
    """
    Decorator to time vector operations for performance monitoring.
    
    Args:
        operation_name: Name of the operation being timed
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            elapsed_time = time.time() - start_time
            logger.debug(f"Vector operation '{operation_name}' took {elapsed_time:.3f} seconds")
            return result
        return wrapper
    return decorator

class VectorDatabaseService:
    """FAISS vector database service for efficient similarity search."""
    
    def __init__(self, 
                 index_dir: Union[str, Path] = DEFAULT_INDEX_DIR,
                 embeddings_cache_dir: Union[str, Path] = DEFAULT_EMBEDDINGS_CACHE,
                 model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize FAISS vector database service.
        
        Args:
            index_dir: Directory to store FAISS indexes
            embeddings_cache_dir: Directory to cache embeddings
            model_name: Sentence transformer model name
        """
        self.index_dir = Path(index_dir)
        self.embeddings_cache_dir = Path(embeddings_cache_dir)
        self.model_name = model_name
        self._model = None
        
        # Ensure directories exist
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.embeddings_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Index metadata store
        self.metadata_path = self.index_dir / 'index_metadata.json'
        self.metadata = self._load_metadata()
        
        logger.info(f"Initialized vector database with model {model_name}")

    @property
    def model(self) -> SentenceTransformer:
        """Get or load the embedding model."""
        if self._model is None:
            logger.info(f"Loading embedding model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
        return self._model
        
    def _load_metadata(self) -> Dict[str, Any]:
        """Load index metadata from disk."""
        if not self.metadata_path.exists():
            return {}
        try:
            with open(self.metadata_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading index metadata: {e}")
            return {}
            
    def _save_metadata(self) -> None:
        """Save index metadata to disk."""
        try:
            with open(self.metadata_path, 'w') as f:
                json.dump(self.metadata, f, default=str)
        except Exception as e:
            logger.error(f"Error saving index metadata: {e}")
    
    @with_retry()
    @handle_db_errors
    def create_index(self, index_name: str, dimension: int = 384, 
                    index_type: str = "Flat") -> bool:
        """
        Create a new FAISS index.
        
        Args:
            index_name: Unique name for the index
            dimension: Vector dimension (depends on the embedding model)
            index_type: FAISS index type (Flat, IVF, HNSW, etc.)
            
        Returns:
            True if index created successfully
        """
        try:
            index_path = self.index_dir / f"{index_name}.index"
            
            # Check if index already exists
            if index_path.exists():
                logger.warning(f"Index {index_name} already exists")
                return False
                
            # Create appropriate FAISS index based on type
            if index_type == "Flat":
                index = faiss.IndexFlatL2(dimension)
            elif index_type == "HNSW":
                index = faiss.IndexHNSWFlat(dimension, 32)  # 32 neighbors
            elif index_type == "IVF":
                quantizer = faiss.IndexFlatL2(dimension)
                index = faiss.IndexIVFFlat(quantizer, dimension, 100)  # 100 centroids
                index.train(np.random.rand(1000, dimension).astype(np.float32))
            else:
                logger.error(f"Unsupported index type: {index_type}")
                return False
                
            # Save empty index
            faiss.write_index(index, str(index_path))
            
            # Save metadata
            self.metadata[index_name] = {
                "created_at": datetime.utcnow(),
                "dimension": dimension,
                "index_type": index_type,
                "item_count": 0
            }
            self._save_metadata()
            
            logger.info(f"Created {index_type} index '{index_name}' with dimension {dimension}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating index {index_name}: {e}")
            return False
    
    @with_retry()
    @handle_db_errors
    def delete_index(self, index_name: str) -> bool:
        """Delete an existing FAISS index."""
        try:
            index_path = self.index_dir / f"{index_name}.index"
            ids_path = self.index_dir / f"{index_name}_ids.pkl"
            
            # Check if index exists
            if not index_path.exists():
                logger.warning(f"Index {index_name} does not exist")
                return False
                
            # Delete index files
            index_path.unlink()
            if ids_path.exists():
                ids_path.unlink()
                
            # Remove from metadata
            if index_name in self.metadata:
                del self.metadata[index_name]
                self._save_metadata()
                
            logger.info(f"Deleted index '{index_name}'")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting index {index_name}: {e}")
            return False
    
    @lru_cache(maxsize=5)  # Cache up to 5 recently loaded indexes
    def _load_index(self, index_name: str) -> Tuple[Any, List[Any]]:
        """
        Load FAISS index and associated IDs from disk.
        
        Returns:
            Tuple of (faiss_index, id_list)
        """
        index_path = self.index_dir / f"{index_name}.index"
        ids_path = self.index_dir / f"{index_name}_ids.pkl"
        
        if not index_path.exists():
            raise FileNotFoundError(f"Index {index_name} not found")
            
        index = faiss.read_index(str(index_path))
        
        if ids_path.exists():
            with open(ids_path, 'rb') as f:
                ids = pickle.load(f)
        else:
            ids = []
            
        return index, ids
    
    @with_retry()
    @handle_db_errors
    def add_items(self, index_name: str, items: List[Dict[str, Any]], 
                text_field: str, id_field: str = "id") -> bool:
        """
        Add items to a FAISS index.
        
        Args:
            index_name: Name of the index
            items: List of dictionaries containing items to add
            text_field: Field name in items to embed
            id_field: Field name in items to use as ID
            
        Returns:
            True if items added successfully
        """
        try:
            # Load index and IDs
            index, ids = self._load_index(index_name)
            
            # Extract texts and IDs
            texts = [item[text_field] for item in items]
            item_ids = [item[id_field] for item in items]
            
            # Create embeddings
            embeddings = self.model.encode(texts, convert_to_tensor=False)
            embeddings = embeddings.astype(np.float32)  # Convert to float32 for FAISS
            
            # Add vectors to index
            index.add(embeddings)
            ids.extend(item_ids)
            
            # Save updated index and IDs
            faiss.write_index(index, str(self.index_dir / f"{index_name}.index"))
            with open(self.index_dir / f"{index_name}_ids.pkl", 'wb') as f:
                pickle.dump(ids, f)
                
            # Update metadata
            if index_name in self.metadata:
                self.metadata[index_name]["item_count"] = len(ids)
                self.metadata[index_name]["updated_at"] = datetime.utcnow()
                self._save_metadata()
                
            logger.info(f"Added {len(items)} items to index '{index_name}'")
            return True
            
        except Exception as e:
            logger.error(f"Error adding items to index {index_name}: {e}")
            return False
    
    @with_retry()
    @handle_db_errors
    def search(self, index_name: str, query: str, k: int = 10) -> List[Tuple[Any, float]]:
        """
        Search for similar items in a FAISS index.
        
        Args:
            index_name: Name of the index
            query: Text query to search for
            k: Number of results to return
            
        Returns:
            List of (id, distance) tuples sorted by similarity
        """
        try:
            # Load index and IDs
            index, ids = self._load_index(index_name)
            
            # Create query embedding
            query_vector = self.model.encode([query], convert_to_tensor=False)
            query_vector = query_vector.astype(np.float32)
            
            # Search
            distances, indices = index.search(query_vector, k)
            
            # Map results to IDs and distances
            results = []
            for i, idx in enumerate(indices[0]):
                if 0 <= idx < len(ids):
                    results.append((ids[idx], float(distances[0][i])))
                    
            logger.debug(f"Search query '{query}' returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Error searching index {index_name}: {e}")
            return []
    
    @with_retry()
    def get_index_stats(self, index_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics about one or all FAISS indexes.
        
        Args:
            index_name: Optional specific index name
            
        Returns:
            Dictionary containing index statistics
        """
        try:
            if index_name:
                if index_name in self.metadata:
                    return {index_name: self.metadata[index_name]}
                else:
                    return {}
            else:
                return self.metadata
                
        except Exception as e:
            logger.error(f"Error getting index stats: {e}")
            return {}
            
    def embed_text(self, text: str) -> np.ndarray:
        """
        Generate embeddings for a single text string.
        
        Args:
            text: Text to embed
            
        Returns:
            Numpy array of embeddings
        """
        try:
            embedding = self.model.encode(text, convert_to_tensor=False)
            return embedding.astype(np.float32)
        except Exception as e:
            logger.error(f"Error embedding text: {e}")
            return np.array([])
            
    def embed_batch(self, texts: List[str], 
                  batch_size: int = 32, 
                  show_progress: bool = True) -> np.ndarray:
        """
        Generate embeddings for a batch of texts.
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing
            show_progress: Whether to show progress bar
            
        Returns:
            Numpy array of embeddings
        """
        try:
            embeddings = self.model.encode(
                texts, 
                batch_size=batch_size,
                show_progress_bar=show_progress,
                convert_to_tensor=False
            )
            return embeddings.astype(np.float32)
        except Exception as e:
            logger.error(f"Error batch embedding texts: {e}")
            return np.array([])

# Initialize global vector database service
vector_db = VectorDatabaseService()