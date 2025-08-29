#!/usr/bin/env python3

import json
from typing import Dict, List, Any, Optional
from pathlib import Path
import os


class MBPPDataLoader:
    """Data loader for MBPP decompilation dataset."""
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.data = self.load_data()
    
    def load_data(self) -> List[Dict[str, Any]]:
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            return self.data
        except FileNotFoundError:
            raise FileNotFoundError(f"Dataset file not found: {self.file_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")

    def __len__(self) -> int:
        if not self.data:
            self.load_data()
        return len(self.data)
    
    def __iter__(self):
        if not self.data:
            self.load_data()
        return iter(self.data)
    
class JSONLDataLoader:
    def __init__(self, jsonl_file_path: str):
        self.jsonl_file_path = jsonl_file_path
        self.data = None
        
    def load_data(self) -> List[Dict[str, Any]]:
        print(f"Loading data from {self.jsonl_file_path}")
        
        if not os.path.exists(self.jsonl_file_path):
            print(f"Error: File {self.jsonl_file_path} does not exist")
            return []
            
        data = []
        with open(self.jsonl_file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line:
                    try:
                        sample = json.loads(line)
                        data.append(sample)
                    except json.JSONDecodeError as e:
                        print(f"Error parsing line {line_num}: {e}")
                        continue
                        
        self.data = data
        print(f"Loaded {len(data)} samples")
        return data    