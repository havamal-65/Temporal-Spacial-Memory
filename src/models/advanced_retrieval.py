"""
Advanced Retrieval Methods for Temporal-Spatial Memory System

This module implements advanced retrieval methods for Phase 8 of the
Temporal-Spatial Memory System, including:

1. ColBERT-style token-level embeddings
2. Reranking with Cohere
3. Maximal Marginal Relevance (MMR)
4. Hybrid retrieval fusion techniques
"""

import numpy as np
import logging
import time
from typing import List, Dict, Any, Tuple, Optional, Union, Callable
import heapq
from sklearn.metrics.pairwise import cosine_similarity
import requests
import os
from functools import partial

# Import local modules
from src.models.narrative_atlas import Node
from src.utils.embedding_service import EmbeddingService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('AdvancedRetrieval')


class ColBERTRetriever:
    """
    Implements ColBERT-style token-level retrieval.
    
    ColBERT creates embeddings for each token rather than a single embedding
    for the entire document. This allows for more fine-grained matching between
    query tokens and document tokens, capturing localized semantic information.
    """
    
    def __init__(self, embedding_service: EmbeddingService, tokenizer=None):
        """
        Initialize the ColBERT retriever.
        
        Args:
            embedding_service: Service for generating embeddings
            tokenizer: Optional custom tokenizer for tokenizing text
        """
        self.embedding_service = embedding_service
        self.tokenizer = tokenizer
        
        # If no tokenizer provided, import and use simple tokenizer
        if self.tokenizer is None:
            from transformers import AutoTokenizer
            try:
                # Try to load the same tokenizer as the embedding model
                self.tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
                logger.info("Initialized default tokenizer for ColBERT")
            except Exception as e:
                logger.warning(f"Failed to load default tokenizer: {e}")
                # Fall back to simple space-based tokenization if transformer tokenizer fails
                self.tokenizer = lambda text: text.split()
        
    def _tokenize_and_embed(self, text: str) -> Tuple[List[str], np.ndarray]:
        """
        Tokenize text and generate embeddings for each token.
        
        Args:
            text: Text to tokenize and embed
            
        Returns:
            Tuple of (tokens, embeddings)
        """
        # Tokenize the text
        if hasattr(self.tokenizer, "tokenize"):
            tokens = self.tokenizer.tokenize(text)
        else:
            tokens = self.tokenizer(text)
        
        # Only keep alphanumeric tokens of reasonable length
        filtered_tokens = [token for token in tokens if token.isalnum() and len(token) > 1]
        
        # Generate embeddings for each token
        token_embeddings = []
        for token in filtered_tokens:
            try:
                embedding = self.embedding_service.embed_query(token)
                token_embeddings.append(embedding)
            except Exception as e:
                logger.warning(f"Failed to embed token {token}: {e}")
        
        return filtered_tokens, np.array(token_embeddings)
    
    def encode_query(self, query: str) -> Tuple[List[str], np.ndarray]:
        """
        Encode a query into token-level embeddings.
        
        Args:
            query: Query text to encode
            
        Returns:
            Tuple of (query_tokens, query_token_embeddings)
        """
        logger.info(f"Encoding query with ColBERT: {query[:50]}...")
        return self._tokenize_and_embed(query)
    
    def encode_document(self, document: str) -> Tuple[List[str], np.ndarray]:
        """
        Encode a document into token-level embeddings.
        
        Args:
            document: Document text to encode
            
        Returns:
            Tuple of (doc_tokens, doc_token_embeddings)
        """
        return self._tokenize_and_embed(document)
    
    def retrieve(self, 
               query: str, 
               nodes: List[Node], 
               k: int = 10) -> List[Tuple[Node, float]]:
        """
        Retrieve nodes using ColBERT-style token-level scoring.
        
        Args:
            query: Query text
            nodes: List of nodes to search through
            k: Number of results to return
            
        Returns:
            List of (node, score) tuples
        """
        start_time = time.time()
        
        # Process query
        query_tokens, query_embeddings = self.encode_query(query)
        
        if len(query_tokens) == 0:
            logger.warning("No valid tokens extracted from query")
            return []
        
        results = []
        for node in nodes:
            # Extract document text from node
            doc_text = ""
            if isinstance(node.content, dict) and "text" in node.content:
                doc_text = node.content["text"]
            else:
                doc_text = str(node.content)
            
            # Process document
            doc_tokens, doc_embeddings = self.encode_document(doc_text)
            
            if len(doc_tokens) == 0:
                continue
            
            # Calculate similarity matrix between query and document tokens
            # Shape: (query_tokens, doc_tokens)
            similarity_matrix = cosine_similarity(query_embeddings, doc_embeddings)
            
            # ColBERT scoring: for each query token, find the maximum similarity with any document token
            # Then sum these maximum similarities
            max_similarities = np.max(similarity_matrix, axis=1)
            score = np.sum(max_similarities)
            
            # Normalize by number of query tokens for fair comparison across queries
            normalized_score = score / len(query_tokens)
            
            results.append((node, float(normalized_score)))
        
        # Sort by score in descending order
        results.sort(key=lambda x: x[1], reverse=True)
        
        logger.info(f"ColBERT retrieval completed in {time.time() - start_time:.2f}s for {len(nodes)} nodes")
        
        return results[:k]


class CohereReranker:
    """
    Reranker using Cohere's reranking API.
    
    This class takes an initial set of retrieval results and reranks them
    using Cohere's reranking model for improved relevance.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "rerank-english-v2.0"):
        """
        Initialize the Cohere reranker.
        
        Args:
            api_key: Cohere API key (defaults to COHERE_API_KEY environment variable)
            model: Reranking model to use
        """
        self.api_key = api_key or os.environ.get("COHERE_API_KEY")
        if not self.api_key:
            logger.warning("No Cohere API key provided. Reranking will fail.")
        
        self.model = model
        self.api_url = "https://api.cohere.ai/v1/rerank"
        
    def rerank(self, 
             query: str, 
             results: List[Tuple[Node, float]], 
             top_n: int = None) -> List[Tuple[Node, float]]:
        """
        Rerank results using Cohere's reranking model.
        
        Args:
            query: Original query text
            results: List of (node, score) tuples from initial retrieval
            top_n: Number of results to return after reranking (defaults to all)
            
        Returns:
            Reranked list of (node, score) tuples
        """
        if not self.api_key:
            logger.error("Cannot rerank: No Cohere API key provided")
            return results
        
        if not results:
            return []
        
        top_n = top_n or len(results)
        
        # Extract documents from nodes
        documents = []
        for node, _ in results:
            if isinstance(node.content, dict) and "text" in node.content:
                documents.append(node.content["text"])
            else:
                documents.append(str(node.content))
        
        # Prepare request payload
        payload = {
            "model": self.model,
            "query": query,
            "documents": documents,
            "top_n": min(top_n, len(documents))
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            # Make request to Cohere API
            response = requests.post(self.api_url, headers=headers, json=payload)
            response.raise_for_status()
            
            # Process response
            rerank_data = response.json()
            
            # Create reranked results
            reranked_results = []
            for idx, result in enumerate(rerank_data.get("results", [])):
                original_idx = result.get("index")
                relevance_score = result.get("relevance_score")
                
                if original_idx < len(results):
                    node = results[original_idx][0]
                    reranked_results.append((node, relevance_score))
            
            logger.info(f"Reranked {len(reranked_results)} results using Cohere")
            return reranked_results
            
        except Exception as e:
            logger.error(f"Error during Cohere reranking: {e}")
            return results  # Fall back to original results on error


class MaximalMarginalRelevance:
    """
    Implements Maximal Marginal Relevance (MMR) for diverse retrieval.
    
    MMR selects documents that maximize relevance to the query while minimizing
    redundancy with previously selected documents, ensuring result diversity.
    """
    
    def __init__(self, lambda_param: float = 0.5):
        """
        Initialize the MMR retriever.
        
        Args:
            lambda_param: Diversity-relevance trade-off parameter (0-1)
                Higher values favor relevance, lower values favor diversity
        """
        self.lambda_param = lambda_param
    
    def _calculate_similarity(self, embed1: np.ndarray, embed2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embed1: First embedding vector
            embed2: Second embedding vector
            
        Returns:
            Cosine similarity value
        """
        # Reshape to 2D if needed (cosine_similarity expects 2D arrays)
        if embed1.ndim == 1:
            embed1 = embed1.reshape(1, -1)
        if embed2.ndim == 1:
            embed2 = embed2.reshape(1, -1)
        
        return float(cosine_similarity(embed1, embed2)[0][0])
    
    def _extract_embedding(self, node: Node) -> np.ndarray:
        """
        Extract embedding from node.
        
        Args:
            node: Node to extract embedding from
            
        Returns:
            Embedding vector
        """
        if node.embedding is not None:
            return node.embedding
        
        raise ValueError("Node does not have an embedding")
    
    def rerank(self, 
             query_embedding: np.ndarray, 
             results: List[Tuple[Node, float]], 
             k: int = 10) -> List[Tuple[Node, float]]:
        """
        Rerank results using MMR to promote diversity.
        
        Args:
            query_embedding: Embedding of the query
            results: List of (node, score) tuples from initial retrieval
            k: Number of results to return
            
        Returns:
            Reranked list of (node, score) tuples with improved diversity
        """
        if not results:
            return []
        
        k = min(k, len(results))
        
        # Initialize selected and remaining items
        selected_indices = []
        remaining_indices = list(range(len(results)))
        
        # Calculate relevance scores to query for all documents
        relevance_scores = {}
        for i, (node, score) in enumerate(results):
            try:
                doc_embedding = self._extract_embedding(node)
                relevance_scores[i] = self._calculate_similarity(query_embedding, doc_embedding)
            except Exception as e:
                logger.warning(f"Error calculating relevance for node {i}: {e}")
                relevance_scores[i] = 0.0
        
        # Iteratively select documents
        for _ in range(k):
            if not remaining_indices:
                break
            
            # For the first document, just pick the most relevant one
            if not selected_indices:
                best_idx = max(remaining_indices, key=lambda i: relevance_scores[i])
            else:
                # Calculate MMR score for each remaining document
                best_score = -float('inf')
                best_idx = None
                
                for i in remaining_indices:
                    # Get relevance to query (first term in MMR)
                    query_relevance = relevance_scores[i]
                    
                    # Calculate maximum similarity to already selected documents (second term in MMR)
                    max_similarity = -float('inf')
                    try:
                        doc_i_embedding = self._extract_embedding(results[i][0])
                        
                        for j in selected_indices:
                            doc_j_embedding = self._extract_embedding(results[j][0])
                            similarity = self._calculate_similarity(doc_i_embedding, doc_j_embedding)
                            max_similarity = max(max_similarity, similarity)
                        
                        # If no previous documents, set similarity to 0
                        if max_similarity == -float('inf'):
                            max_similarity = 0
                            
                        # Calculate MMR score
                        mmr_score = self.lambda_param * query_relevance - (1 - self.lambda_param) * max_similarity
                        
                        if mmr_score > best_score:
                            best_score = mmr_score
                            best_idx = i
                    except Exception as e:
                        logger.warning(f"Error in MMR calculation for node {i}: {e}")
                        continue
            
            # If we found a valid index, add it to selected and remove from remaining
            if best_idx is not None:
                selected_indices.append(best_idx)
                remaining_indices.remove(best_idx)
            else:
                break
        
        # Create new results list based on selected indices
        mmr_results = [(results[i][0], relevance_scores[i]) for i in selected_indices]
        
        return mmr_results


class RAGFusionRetriever:
    """
    Implements RAG-Fusion technique for improved retrieval.
    
    RAG-Fusion combines results from multiple retrievers using reciprocal rank fusion,
    which gives higher weights to documents that appear near the top of multiple retrievers.
    """
    
    def __init__(self, retrievers: List[Callable], k: float = 60.0):
        """
        Initialize the RAG-Fusion retriever.
        
        Args:
            retrievers: List of retriever functions, each taking a query and returning a list of (node, score) tuples
            k: Fusion parameter that controls the impact of lower-ranked results
        """
        self.retrievers = retrievers
        self.k = k
    
    def retrieve(self, query: str, k: int = 10) -> List[Tuple[Node, float]]:
        """
        Retrieve documents using RAG-Fusion across multiple retrievers.
        
        Args:
            query: Query text
            k: Number of results to return
            
        Returns:
            List of (node, score) tuples
        """
        start_time = time.time()
        
        # Get results from each retriever
        all_results = []
        for i, retriever in enumerate(self.retrievers):
            try:
                results = retriever(query)
                all_results.append(results)
                logger.info(f"Retriever {i} returned {len(results)} results")
            except Exception as e:
                logger.error(f"Error in retriever {i}: {e}")
                all_results.append([])
        
        # Calculate reciprocal rank fusion scores
        fusion_scores = {}
        for retriever_idx, results in enumerate(all_results):
            for rank, (node, _) in enumerate(results):
                node_id = node.id
                if node_id not in fusion_scores:
                    fusion_scores[node_id] = 0.0
                
                # Reciprocal rank formula: 1 / (rank + k)
                fusion_scores[node_id] += 1.0 / (rank + self.k)
        
        # Create final results list
        final_results = []
        nodes_map = {}
        
        # Build map of nodes by ID for quick lookup
        for results in all_results:
            for node, _ in results:
                nodes_map[node.id] = node
        
        # Sort by fusion score
        for node_id, score in sorted(fusion_scores.items(), key=lambda x: x[1], reverse=True):
            if node_id in nodes_map:
                final_results.append((nodes_map[node_id], score))
            
            if len(final_results) >= k:
                break
        
        logger.info(f"RAG-Fusion completed in {time.time() - start_time:.2f}s, returning {len(final_results)} results")
        
        return final_results


# Helper function to create a weighted fusion of results
def weighted_fusion(result_lists: List[List[Tuple[Node, float]]], 
                   weights: List[float], 
                   k: int = 10) -> List[Tuple[Node, float]]:
    """
    Combine multiple result lists with weighted fusion.
    
    Args:
        result_lists: List of result lists, each containing (node, score) tuples
        weights: Weight to apply to each result list
        k: Number of results to return
        
    Returns:
        Fused list of (node, score) tuples
    """
    if len(result_lists) != len(weights):
        raise ValueError("Number of result lists must match number of weights")
    
    # Collect all nodes and their weighted scores
    node_scores = {}
    for results, weight in zip(result_lists, weights):
        for node, score in results:
            if node.id not in node_scores:
                node_scores[node.id] = 0.0
            node_scores[node.id] += score * weight
    
    # Create result list with fused scores
    fused_results = []
    nodes_map = {}
    
    # Build map of nodes by ID for quick lookup
    for results in result_lists:
        for node, _ in results:
            nodes_map[node.id] = node
    
    # Sort by fused score
    for node_id, score in sorted(node_scores.items(), key=lambda x: x[1], reverse=True):
        if node_id in nodes_map:
            fused_results.append((nodes_map[node_id], score))
        
        if len(fused_results) >= k:
            break
    
    return fused_results 