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
        
    def filter_dataframe(self, df: pd.DataFrame, conditions: Dict[str, Any]) -> pd.DataFrame:
        """Filter DataFrame based on conditions."""
        result = df.copy()
        
        for column, condition in conditions.items():
            if column not in df.columns:
                continue
                
            if isinstance(condition, dict):
                # Handle complex conditions like {'gt': 5, 'lt': 10}
                for op, value in condition.items():
                    if op == 'gt':
                        result = result[result[column] > value]
                    elif op == 'lt':
                        result = result[result[column] < value]
                    elif op == 'gte':
                        result = result[result[column] >= value]
                    elif op == 'lte':
                        result = result[result[column] <= value]
                    elif op == 'eq':
                        result = result[result[column] == value]
                    elif op == 'ne':
                        result = result[result[column] != value]
                    elif op == 'isin':
                        result = result[result[column].isin(value)]
                    elif op == 'contains':
                        result = result[result[column].str.contains(str(value), na=False)]
            else:
                # Simple equality condition
                result = result[result[column] == condition]
                
        return result
        
    def aggregate_data(self, df: pd.DataFrame, group_by: List[str], agg_funcs: Dict[str, str]) -> pd.DataFrame:
        """Aggregate DataFrame by grouping columns."""
        return df.groupby(group_by).agg(agg_funcs).reset_index()
        
    def transform_column(self, df: pd.DataFrame, column: str, func: Callable) -> pd.DataFrame:
        """Apply transformation function to a column."""
        result = df.copy()
        result[column] = result[column].apply(func)
        return result
        
    def normalize_column(self, df: pd.DataFrame, column: str, method: str = 'minmax') -> pd.DataFrame:
        """Normalize numeric column values."""
        result = df.copy()
        
        if method == 'minmax':
            min_val = result[column].min()
            max_val = result[column].max()
            result[column] = (result[column] - min_val) / (max_val - min_val)
        elif method == 'zscore':
            mean_val = result[column].mean()
            std_val = result[column].std()
            result[column] = (result[column] - mean_val) / std_val
            
        return result