#!/usr/bin/env python3

import faiss
import numpy as np
import torch
from typing import List, Tuple
from transformers import AutoTokenizer, AutoModel


class SimilarityRetriever:
    def __init__(self, embeddings_path: str, model_name: str = 'lt-asset/nova-1.3b', chunks_file: str = None):
        self.model_name = model_name
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
            self.model.config.pad_token_id = self.model.config.eos_token_id
        
        data = np.load(embeddings_path)
        vectors = data['embeddings'].astype(np.float32)
        self.chunk_ids = data.get('chunk_ids', None)
        
        faiss.normalize_L2(vectors)
        self.index = faiss.IndexFlatIP(vectors.shape[1])
        self.index.add(vectors)
        self.chunks_data = None
        self.opt_level_indices = {}
        if chunks_file:
            self.chunks_data = self._load_chunks(chunks_file)
            self._build_opt_level_indices()
        


    def _load_chunks(self, chunks_file: str) -> dict:
        import json
        chunks = {}
        
        with open(chunks_file, 'r', encoding='utf-8') as f:
            for line in f:
                chunk = json.loads(line)
                chunks[chunk['chunk_id']] = chunk
        
        return chunks

    def _build_opt_level_indices(self):
        if not self.chunks_data:
            return
        
        for i, chunk_id in enumerate(self.chunk_ids):
            if chunk_id in self.chunks_data:
                opt_level = self.chunks_data[chunk_id].get('metadata', {}).get('optimization', '')
                if opt_level:
                    if opt_level not in self.opt_level_indices:
                        self.opt_level_indices[opt_level] = []
                    self.opt_level_indices[opt_level].append(i)

    def encode_query(self, query: str) -> np.ndarray:
        inputs = self.tokenizer(query, return_tensors='pt', truncation=True, 
                               padding=True, max_length=1024)
        
        with torch.no_grad():
            outputs = self.model(**inputs)
        
        embeddings = outputs.last_hidden_state.mean(dim=1)
        return embeddings.detach().numpy()

    def search(self, query: str, k: int = 5, opt_level: str = None) -> Tuple[List[int], List[float]]:
        query_vector = self.encode_query(query).astype(np.float32)
        faiss.normalize_L2(query_vector)
        
        if opt_level is not None:
            if opt_level not in self.opt_level_indices:
                print(f"Warning: No embeddings found for optimization level {opt_level}")
                return [], []
            
            valid_indices = self.opt_level_indices[opt_level]
            
            search_k = min(len(valid_indices), k * 10)
            distances, indices = self.index.search(query_vector, search_k)
            
            filtered_results = []
            for idx, dist in zip(indices[0], distances[0]):
                if idx in valid_indices:
                    filtered_results.append((idx, dist))
                if len(filtered_results) >= k:
                    break
            
            if not filtered_results:
                print(f"Warning: No results found for optimization level {opt_level}")
                return [], []
            
            result_indices, result_distances = zip(*filtered_results)
            return list(result_indices), list(result_distances)
        else:
            distances, indices = self.index.search(query_vector, k)
            return indices[0].tolist(), distances[0].tolist()