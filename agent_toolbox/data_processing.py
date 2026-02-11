"""Data processing utilities for agent tasks."""

import pandas as pd
import numpy as np
import json
import csv
from typing import Dict, List, Optional, Union, Any, Callable
from pathlib import Path
import re


class DataProcessor:
    """Comprehensive data processing utilities for agents."""
    
    def __init__(self):
        """Initialize DataProcessor."""
        pass
        
    def load_csv(self, file_path: Union[str, Path], **kwargs) -> pd.DataFrame:
        """Load CSV file into DataFrame."""
        return pd.read_csv(file_path, **kwargs)
        
    def save_csv(self, data: pd.DataFrame, file_path: Union[str, Path], **kwargs) -> None:
        """Save DataFrame to CSV file."""
        data.to_csv(file_path, index=False, **kwargs)
        
    def load_json_lines(self, file_path: Union[str, Path]) -> List[Dict[str, Any]]:
        """Load JSONL file."""
        data = []
        with open(file_path, 'r') as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line.strip()))
        return data
        
    def save_json_lines(self, data: List[Dict[str, Any]], file_path: Union[str, Path]) -> None:
        """Save data to JSONL file."""
        with open(file_path, 'w') as f:
            for item in data:
                f.write(json.dumps(item) + '\n')
                
    def clean_text(self, text: str, 
                   remove_extra_whitespace: bool = True,
                   remove_special_chars: bool = False,
                   lowercase: bool = False) -> str:
        """Clean and normalize text data."""
        if not isinstance(text, str):
            return str(text)
            
        # Remove extra whitespace
        if remove_extra_whitespace:
            text = re.sub(r'\s+', ' ', text.strip())
            
        # Remove special characters
        if remove_special_chars:
            text = re.sub(r'[^\w\s]', '', text)
            
        # Convert to lowercase
        if lowercase:
            text = text.lower()
            
        return text