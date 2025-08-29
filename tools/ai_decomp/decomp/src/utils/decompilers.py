#!/usr/bin/env python3

import os
import time
import requests
import json
from abc import ABC, abstractmethod


from src.rag.prompt_templates import get_template


class DecompilerBase(ABC):
    def __init__(self, args):
        self.args = args
        self.setup()
    
    @abstractmethod
    def setup(self):
        pass
    
    @abstractmethod
    def decompile(self, input_prompt, context=None):
        pass
    
    def cleanup(self):
        pass


class GeneralLLMDecompiler(DecompilerBase):
    def setup(self):
        self.api_key = os.getenv('DEEPSEEK_API_KEY')
        if not self.api_key:
            raise ValueError("API key for general LLM is required")
        
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "Connection": "close"
        }
    
    def decompile(self, input_prompt, context=None):
        data = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": input_prompt}],
            "max_tokens": self.args.max_new_tokens,
            "temperature": self.args.temperature,
            "stream": False
        }

        for attempt in range(self.args.api_max_retries):
            try:
                with requests.Session() as session:
                    response = session.post(
                        self.args.api_url, 
                        headers=self.headers, 
                        json=data, 
                        timeout=self.args.api_timeout
                    )
                    response.raise_for_status()
                    result = response.json()

                if 'choices' in result and result['choices']:
                    generated_text = result['choices'][0]['message']['content'].strip()
                    if "```cpp" in generated_text:
                        return generated_text.split("```cpp")[1].split("```")[0].strip()
                    elif "```c" in generated_text:
                        return generated_text.split("```c")[1].split("```")[0].strip()
                    return generated_text
                else:
                    return ""
                    
            except requests.exceptions.RequestException as e:
                if attempt < self.args.api_max_retries - 1:
                    time.sleep(self.args.api_retry_delay * (2 ** attempt))
                else:
                    print(f"API request failed after {self.args.api_max_retries} attempts: {e}")
                    return ""
            except Exception as e:
                print(f"Unexpected error: {e}")
                return ""
            

class RAGDecompiler(DecompilerBase):
    def setup(self):
        """Initialize RAG resources for retrieval-augmented generation."""
        from src.rag.retriever import SimilarityRetriever
        from src.dataset.data_loader import MBPPDataLoader
        
        self.retriever = SimilarityRetriever(embeddings_path=self.args.embeddings_path, chunks_file=self.args.chunks_path)
        
        self.chunks = []
        if os.path.exists(self.args.chunks_path):
            with open(self.args.chunks_path, 'r') as f:
                for line in f:
                    self.chunks.append(json.loads(line.strip()))
        else:
            print(f"Warning: Chunks file not found: {self.args.chunks_path}")
            self.chunks = []
        
        self.dataset_loader = MBPPDataLoader(self.args.kb_path)
        
        self.general_llm_decompiler = GeneralLLMDecompiler(self.args)
        
        self.prompt_template = get_template(self.args.rag_prompt_template)
        
    
    def _format_example(self, chunk, metadata, example_num):
        """Format a single example according to the template."""
        template = self.prompt_template
        
        assembly_text = template["assembly_section"].format(
            optimization=metadata.get('optimization', 'unknown'),
            assembly_content=chunk['content']
        )
        
        sample_index = metadata.get('index', chunk.get('index', 0))
        source_code = self.dataset_loader.data[sample_index]['func']
        
        if source_code:
            source_text = template["source_section"].format(
                language=metadata.get('language', 'C/C++'),
                source_content=source_code
            )
        else:
            source_text = template["source_not_available"].format(
                language=metadata.get('language', 'C/C++')
            )
        
        example_text = (
            template["example_start"].format(example_num=example_num) +
            assembly_text +
            source_text
        )
        
        return example_text
    
    def decompile(self, input_prompt, context=None):
        """Decompile using RAG with similarity-based retrieval."""
        if not self.chunks:
            return ""
        
        assembly_code = input_prompt
        if "# This is the assembly code:\n" in assembly_code:
            assembly_code = assembly_code.split("# This is the assembly code:\n")[1]
        if "\n# What is the source code?\n" in assembly_code:
            assembly_code = assembly_code.split("\n# What is the source code?\n")[0]

        opt_level = None
        if context and 'opt' in context:
            opt_level = context['opt']
        
        similar_indices = self.retriever.search(assembly_code.strip(), k=self.args.top_k, opt_level=opt_level)[0]
        
        rag_prompt = self.prompt_template["header"]
        
        metadata = {'optimization': 'unknown'}
        
        for i, idx in enumerate(similar_indices):
            if idx < len(self.chunks):
                chunk = self.chunks[idx]
                metadata = chunk.get('metadata', {})
                example_text = self._format_example(chunk, metadata, i + 1)
                rag_prompt += example_text
        
        rag_prompt += self.prompt_template["query_section"].format(
            optimization=metadata.get('optimization', 'unknown'),
            target_assembly=assembly_code.strip()
        )
        return self.general_llm_decompiler.decompile(rag_prompt)
    
    def cleanup(self):
        """Clean up RAG resources."""
        if hasattr(self, 'general_llm_decompiler'):
            self.general_llm_decompiler.cleanup()


class DecompilerFactory:
    @staticmethod
    def create_decompiler(method_name, args):
        if method_name == "general_llm":
            return GeneralLLMDecompiler(args)
        elif method_name == "RAG":
            return RAGDecompiler(args)
        else:
            raise ValueError(f"Unknown decompiler method: {method_name}") 