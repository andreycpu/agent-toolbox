"""Advanced file processing and analysis tools."""

import os
import json
import csv
import yaml
import mimetypes
import hashlib
import zipfile
import tarfile
from typing import Dict, List, Optional, Any, Union, BinaryIO
from dataclasses import dataclass, field
from pathlib import Path
import logging

from ..core.tool_base import BaseTool, ToolResult, ToolStatus, ToolValidationError
from ..core.tool_registry import tool_decorator

logger = logging.getLogger(__name__)


@dataclass
class FileStats:
    """File statistics and metadata."""
    
    path: str
    size: int
    created: float
    modified: float
    accessed: float
    mime_type: str
    extension: str
    is_directory: bool
    permissions: str
    checksum: Optional[str] = None


@tool_decorator(name="file_processor", category="files", tags=["processing", "analysis", "metadata"])
class FileProcessor(BaseTool):
    """Advanced file processing with format detection and analysis."""
    
    def validate_input(self, **kwargs) -> Dict[str, Any]:
        """Validate file processing parameters."""
        file_path = kwargs.get('file_path')
        if not file_path:
            raise ToolValidationError("file_path is required", self.tool_id)
            
        if not os.path.exists(file_path):
            raise ToolValidationError(f"File not found: {file_path}", self.tool_id)
            
        return {
            'file_path': file_path,
            'operation': kwargs.get('operation', 'analyze'),
            'include_content': kwargs.get('include_content', False),
            'calculate_checksum': kwargs.get('calculate_checksum', True),
            'max_content_size': kwargs.get('max_content_size', 1024 * 1024)  # 1MB
        }
        
    def execute(self, **kwargs) -> ToolResult:
        """Execute file processing operation."""
        file_path = kwargs['file_path']
        operation = kwargs['operation']
        include_content = kwargs['include_content']
        calculate_checksum = kwargs['calculate_checksum']
        max_content_size = kwargs['max_content_size']
        
        try:
            path = Path(file_path)
            
            if operation == 'analyze':
                result = self._analyze_file(path, include_content, calculate_checksum, max_content_size)
            elif operation == 'extract_metadata':
                result = self._extract_metadata(path)
            elif operation == 'convert':
                target_format = kwargs.get('target_format')
                if not target_format:
                    raise ToolValidationError("target_format required for convert operation", self.tool_id)
                result = self._convert_file(path, target_format)
            elif operation == 'validate':
                result = self._validate_file(path)
            else:
                raise ToolValidationError(f"Unknown operation: {operation}", self.tool_id)
                
            return ToolResult(
                tool_id=self.tool_id,
                status=ToolStatus.SUCCESS,
                data=result
            )
            
        except Exception as e:
            return ToolResult(
                tool_id=self.tool_id,
                status=ToolStatus.FAILED,
                error=str(e)
            )
            
    def _analyze_file(self, path: Path, include_content: bool, calculate_checksum: bool, max_content_size: int) -> Dict[str, Any]:
        """Analyze file comprehensively."""
        # Get basic stats
        stat = path.stat()
        mime_type, _ = mimetypes.guess_type(str(path))
        
        file_stats = FileStats(
            path=str(path),
            size=stat.st_size,
            created=stat.st_ctime,
            modified=stat.st_mtime,
            accessed=stat.st_atime,
            mime_type=mime_type or 'unknown',
            extension=path.suffix.lower(),
            is_directory=path.is_dir(),
            permissions=oct(stat.st_mode)[-3:]
        )
        
        # Calculate checksum
        if calculate_checksum and path.is_file() and stat.st_size <= max_content_size:
            file_stats.checksum = self._calculate_checksum(path)
            
        analysis = {
            'file_stats': {
                'path': file_stats.path,
                'size': file_stats.size,
                'size_human': self._format_bytes(file_stats.size),
                'created': file_stats.created,
                'modified': file_stats.modified,
                'accessed': file_stats.accessed,
                'mime_type': file_stats.mime_type,
                'extension': file_stats.extension,
                'is_directory': file_stats.is_directory,
                'permissions': file_stats.permissions,
                'checksum': file_stats.checksum
            }
        }
        
        # Format-specific analysis
        if path.is_file():
            if file_stats.extension in ['.json']:
                analysis['json_analysis'] = self._analyze_json(path)
            elif file_stats.extension in ['.csv']:
                analysis['csv_analysis'] = self._analyze_csv(path)
            elif file_stats.extension in ['.yaml', '.yml']:
                analysis['yaml_analysis'] = self._analyze_yaml(path)
            elif file_stats.extension in ['.txt', '.log']:
                analysis['text_analysis'] = self._analyze_text(path, max_content_size)
            elif file_stats.extension in ['.zip', '.tar', '.gz', '.bz2']:
                analysis['archive_analysis'] = self._analyze_archive(path)
                
        # Include content if requested and file is small enough
        if include_content and path.is_file() and stat.st_size <= max_content_size:
            try:
                if file_stats.mime_type and file_stats.mime_type.startswith('text/'):
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        analysis['content'] = f.read()
                else:
                    with open(path, 'rb') as f:
                        content = f.read()
                        analysis['content'] = {
                            'type': 'binary',
                            'size': len(content),
                            'preview': content[:100].hex()
                        }
            except Exception as e:
                analysis['content_error'] = str(e)
                
        return analysis
        
    def _calculate_checksum(self, path: Path, algorithm: str = 'sha256') -> str:
        """Calculate file checksum."""
        hash_obj = hashlib.new(algorithm)
        
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_obj.update(chunk)
                
        return hash_obj.hexdigest()
        
    def _format_bytes(self, bytes_size: int) -> str:
        """Format bytes in human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f} PB"
        
    def _analyze_json(self, path: Path) -> Dict[str, Any]:
        """Analyze JSON file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            def analyze_structure(obj, depth=0):
                if depth > 10:  # Prevent infinite recursion
                    return {'type': 'deep_nesting', 'depth': depth}
                    
                if isinstance(obj, dict):
                    return {
                        'type': 'object',
                        'keys': len(obj),
                        'key_types': {k: analyze_structure(v, depth + 1) for k, v in list(obj.items())[:5]}
                    }
                elif isinstance(obj, list):
                    return {
                        'type': 'array',
                        'length': len(obj),
                        'item_types': [analyze_structure(item, depth + 1) for item in obj[:3]]
                    }
                else:
                    return {'type': type(obj).__name__, 'value': str(obj)[:50]}
                    
            return {
                'valid': True,
                'structure': analyze_structure(data),
                'size_analysis': {
                    'total_keys': self._count_keys(data),
                    'max_depth': self._max_depth(data)
                }
            }
            
        except json.JSONDecodeError as e:
            return {
                'valid': False,
                'error': str(e),
                'line': e.lineno if hasattr(e, 'lineno') else None
            }
        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }
            
    def _analyze_csv(self, path: Path) -> Dict[str, Any]:
        """Analyze CSV file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                # Detect delimiter
                sample = f.read(1024)
                f.seek(0)
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter
                
                reader = csv.reader(f, delimiter=delimiter)
                rows = list(reader)
                
            if not rows:
                return {'valid': False, 'error': 'Empty file'}
                
            headers = rows[0] if rows else []
            data_rows = rows[1:] if len(rows) > 1 else []
            
            # Analyze columns
            column_analysis = {}
            if data_rows:
                for i, header in enumerate(headers):
                    column_values = [row[i] if i < len(row) else '' for row in data_rows]
                    
                    # Try to detect data types
                    numeric_count = 0
                    empty_count = 0
                    
                    for value in column_values:
                        if not value.strip():
                            empty_count += 1
                        else:
                            try:
                                float(value)
                                numeric_count += 1
                            except ValueError:
                                pass
                                
                    column_analysis[header] = {
                        'total_values': len(column_values),
                        'empty_values': empty_count,
                        'numeric_values': numeric_count,
                        'likely_numeric': numeric_count > len(column_values) * 0.8,
                        'sample_values': column_values[:3]
                    }
                    
            return {
                'valid': True,
                'delimiter': delimiter,
                'total_rows': len(rows),
                'headers': headers,
                'column_count': len(headers),
                'data_rows': len(data_rows),
                'column_analysis': column_analysis
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }
            
    def _analyze_yaml(self, path: Path) -> Dict[str, Any]:
        """Analyze YAML file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                
            return {
                'valid': True,
                'structure': self._analyze_yaml_structure(data),
                'size_analysis': {
                    'total_keys': self._count_keys(data) if isinstance(data, dict) else 0,
                    'max_depth': self._max_depth(data)
                }
            }
            
        except yaml.YAMLError as e:
            return {
                'valid': False,
                'error': str(e)
            }
        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }
            
    def _analyze_text(self, path: Path, max_size: int) -> Dict[str, Any]:
        """Analyze text file."""
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(max_size)
                
            lines = content.split('\n')
            words = content.split()
            
            # Character frequency
            char_freq = {}
            for char in content:
                char_freq[char] = char_freq.get(char, 0) + 1
                
            return {
                'total_characters': len(content),
                'total_lines': len(lines),
                'total_words': len(words),
                'average_line_length': sum(len(line) for line in lines) / len(lines) if lines else 0,
                'average_word_length': sum(len(word) for word in words) / len(words) if words else 0,
                'blank_lines': sum(1 for line in lines if not line.strip()),
                'character_frequency': dict(sorted(char_freq.items(), key=lambda x: x[1], reverse=True)[:10]),
                'encoding': 'utf-8'
            }
            
        except Exception as e:
            return {
                'error': str(e)
            }
            
    def _analyze_archive(self, path: Path) -> Dict[str, Any]:
        """Analyze archive file."""
        try:
            if path.suffix.lower() == '.zip':
                return self._analyze_zip(path)
            elif path.suffix.lower() in ['.tar', '.gz', '.bz2']:
                return self._analyze_tar(path)
            else:
                return {'error': 'Unsupported archive format'}
                
        except Exception as e:
            return {
                'error': str(e)
            }
            
    def _analyze_zip(self, path: Path) -> Dict[str, Any]:
        """Analyze ZIP file."""
        with zipfile.ZipFile(path, 'r') as zip_file:
            info_list = zip_file.infolist()
            
            files = []
            total_uncompressed = 0
            total_compressed = 0
            
            for info in info_list:
                files.append({
                    'filename': info.filename,
                    'compressed_size': info.compress_size,
                    'uncompressed_size': info.file_size,
                    'compression_ratio': 1 - (info.compress_size / info.file_size) if info.file_size > 0 else 0,
                    'is_directory': info.is_dir(),
                    'date_time': info.date_time
                })
                
                total_compressed += info.compress_size
                total_uncompressed += info.file_size
                
            return {
                'archive_type': 'zip',
                'total_files': len(info_list),
                'total_compressed_size': total_compressed,
                'total_uncompressed_size': total_uncompressed,
                'overall_compression_ratio': 1 - (total_compressed / total_uncompressed) if total_uncompressed > 0 else 0,
                'files': files[:20]  # Limit to first 20 files
            }
            
    def _analyze_tar(self, path: Path) -> Dict[str, Any]:
        """Analyze TAR file."""
        mode = 'r:gz' if path.suffix in ['.gz'] else 'r:bz2' if path.suffix == '.bz2' else 'r'
        
        with tarfile.open(path, mode) as tar_file:
            members = tar_file.getmembers()
            
            files = []
            total_size = 0
            
            for member in members:
                files.append({
                    'name': member.name,
                    'size': member.size,
                    'is_directory': member.isdir(),
                    'is_file': member.isfile(),
                    'mode': oct(member.mode),
                    'uid': member.uid,
                    'gid': member.gid,
                    'mtime': member.mtime
                })
                
                total_size += member.size
                
            return {
                'archive_type': 'tar',
                'compression': path.suffix[1:] if path.suffix in ['.gz', '.bz2'] else 'none',
                'total_members': len(members),
                'total_size': total_size,
                'files': files[:20]  # Limit to first 20 files
            }
            
    def _count_keys(self, obj, count=0):
        """Recursively count keys in nested structure."""
        if isinstance(obj, dict):
            count += len(obj)
            for value in obj.values():
                count = self._count_keys(value, count)
        elif isinstance(obj, list):
            for item in obj:
                count = self._count_keys(item, count)
        return count
        
    def _max_depth(self, obj, depth=0):
        """Calculate maximum depth of nested structure."""
        if isinstance(obj, dict):
            if not obj:
                return depth
            return max(self._max_depth(value, depth + 1) for value in obj.values())
        elif isinstance(obj, list):
            if not obj:
                return depth
            return max(self._max_depth(item, depth + 1) for item in obj)
        else:
            return depth
            
    def _analyze_yaml_structure(self, obj):
        """Analyze YAML structure."""
        if isinstance(obj, dict):
            return {
                'type': 'mapping',
                'keys': list(obj.keys())[:10],
                'total_keys': len(obj)
            }
        elif isinstance(obj, list):
            return {
                'type': 'sequence',
                'length': len(obj),
                'item_types': [type(item).__name__ for item in obj[:5]]
            }
        else:
            return {
                'type': type(obj).__name__,
                'value': str(obj)[:100]
            }
            
    def _extract_metadata(self, path: Path) -> Dict[str, Any]:
        """Extract metadata from file."""
        metadata = {
            'basic': {
                'name': path.name,
                'stem': path.stem,
                'suffix': path.suffix,
                'parent': str(path.parent),
                'absolute_path': str(path.absolute())
            }
        }
        
        # Try to extract extended metadata based on file type
        if path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.tiff']:
            metadata['image'] = self._extract_image_metadata(path)
        elif path.suffix.lower() in ['.mp3', '.wav', '.flac', '.m4a']:
            metadata['audio'] = self._extract_audio_metadata(path)
        elif path.suffix.lower() in ['.mp4', '.avi', '.mov', '.mkv']:
            metadata['video'] = self._extract_video_metadata(path)
        elif path.suffix.lower() in ['.pdf']:
            metadata['document'] = self._extract_document_metadata(path)
            
        return metadata
        
    def _extract_image_metadata(self, path: Path) -> Dict[str, Any]:
        """Extract image metadata (placeholder - would use PIL/Pillow)."""
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS
            
            with Image.open(path) as img:
                metadata = {
                    'format': img.format,
                    'mode': img.mode,
                    'size': img.size,
                    'width': img.width,
                    'height': img.height
                }
                
                # Extract EXIF data
                exif_data = {}
                if hasattr(img, '_getexif'):
                    exif = img._getexif()
                    if exif:
                        for tag_id, value in exif.items():
                            tag = TAGS.get(tag_id, tag_id)
                            exif_data[tag] = str(value)
                            
                metadata['exif'] = exif_data
                return metadata
                
        except ImportError:
            return {'error': 'PIL/Pillow not available for image analysis'}
        except Exception as e:
            return {'error': str(e)}
            
    def _extract_audio_metadata(self, path: Path) -> Dict[str, Any]:
        """Extract audio metadata (placeholder - would use mutagen)."""
        return {'message': 'Audio metadata extraction not implemented'}
        
    def _extract_video_metadata(self, path: Path) -> Dict[str, Any]:
        """Extract video metadata (placeholder - would use ffmpeg)."""
        return {'message': 'Video metadata extraction not implemented'}
        
    def _extract_document_metadata(self, path: Path) -> Dict[str, Any]:
        """Extract document metadata (placeholder - would use PyPDF2)."""
        return {'message': 'Document metadata extraction not implemented'}
        
    def _convert_file(self, path: Path, target_format: str) -> Dict[str, Any]:
        """Convert file to different format."""
        # This is a placeholder for file conversion functionality
        return {
            'message': f'File conversion from {path.suffix} to {target_format} not implemented',
            'source_file': str(path),
            'target_format': target_format
        }
        
    def _validate_file(self, path: Path) -> Dict[str, Any]:
        """Validate file integrity and format."""
        validation = {
            'exists': path.exists(),
            'is_file': path.is_file(),
            'readable': os.access(path, os.R_OK),
            'size_valid': True
        }
        
        if path.is_file():
            # Format-specific validation
            if path.suffix.lower() == '.json':
                try:
                    with open(path, 'r') as f:
                        json.load(f)
                    validation['json_valid'] = True
                except:
                    validation['json_valid'] = False
                    
            elif path.suffix.lower() in ['.yaml', '.yml']:
                try:
                    with open(path, 'r') as f:
                        yaml.safe_load(f)
                    validation['yaml_valid'] = True
                except:
                    validation['yaml_valid'] = False
                    
            # Check for empty files
            validation['size_valid'] = path.stat().st_size > 0
            
        validation['overall_valid'] = all([
            validation['exists'],
            validation['is_file'],
            validation['readable'],
            validation['size_valid']
        ])
        
        return validation


@tool_decorator(name="document_parser", category="files", tags=["parsing", "documents", "text_extraction"])
class DocumentParser(BaseTool):
    """Parse various document formats and extract text content."""
    
    def validate_input(self, **kwargs) -> Dict[str, Any]:
        """Validate document parsing parameters."""
        file_path = kwargs.get('file_path')
        if not file_path:
            raise ToolValidationError("file_path is required", self.tool_id)
            
        if not os.path.exists(file_path):
            raise ToolValidationError(f"File not found: {file_path}", self.tool_id)
            
        return {
            'file_path': file_path,
            'extract_images': kwargs.get('extract_images', False),
            'preserve_formatting': kwargs.get('preserve_formatting', False),
            'include_metadata': kwargs.get('include_metadata', True)
        }
        
    def execute(self, **kwargs) -> ToolResult:
        """Parse document and extract content."""
        file_path = kwargs['file_path']
        extract_images = kwargs['extract_images']
        preserve_formatting = kwargs['preserve_formatting']
        include_metadata = kwargs['include_metadata']
        
        try:
            path = Path(file_path)
            extension = path.suffix.lower()
            
            if extension == '.pdf':
                result = self._parse_pdf(path, extract_images, preserve_formatting, include_metadata)
            elif extension in ['.docx', '.doc']:
                result = self._parse_word(path, extract_images, preserve_formatting, include_metadata)
            elif extension in ['.txt']:
                result = self._parse_text(path, include_metadata)
            elif extension in ['.csv']:
                result = self._parse_csv(path, include_metadata)
            elif extension in ['.json']:
                result = self._parse_json(path, include_metadata)
            elif extension in ['.xml']:
                result = self._parse_xml(path, include_metadata)
            else:
                # Try generic text parsing
                result = self._parse_generic(path, include_metadata)
                
            return ToolResult(
                tool_id=self.tool_id,
                status=ToolStatus.SUCCESS,
                data=result
            )
            
        except Exception as e:
            return ToolResult(
                tool_id=self.tool_id,
                status=ToolStatus.FAILED,
                error=str(e)
            )
            
    def _parse_pdf(self, path: Path, extract_images: bool, preserve_formatting: bool, include_metadata: bool) -> Dict[str, Any]:
        """Parse PDF document (placeholder - would use PyPDF2/pdfplumber)."""
        return {
            'format': 'pdf',
            'text': 'PDF parsing not implemented - would extract text from PDF',
            'pages': 0,
            'metadata': {} if include_metadata else None,
            'images': [] if extract_images else None
        }
        
    def _parse_word(self, path: Path, extract_images: bool, preserve_formatting: bool, include_metadata: bool) -> Dict[str, Any]:
        """Parse Word document (placeholder - would use python-docx)."""
        return {
            'format': 'word',
            'text': 'Word document parsing not implemented - would extract text from DOCX/DOC',
            'paragraphs': 0,
            'metadata': {} if include_metadata else None,
            'images': [] if extract_images else None
        }
        
    def _parse_text(self, path: Path, include_metadata: bool) -> Dict[str, Any]:
        """Parse plain text file."""
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        lines = content.split('\n')
        words = content.split()
        
        result = {
            'format': 'text',
            'text': content,
            'lines': len(lines),
            'words': len(words),
            'characters': len(content)
        }
        
        if include_metadata:
            result['metadata'] = {
                'encoding': 'utf-8',
                'line_endings': 'mixed' if '\r\n' in content and '\n' in content else 'unix' if '\n' in content else 'windows',
                'blank_lines': sum(1 for line in lines if not line.strip())
            }
            
        return result
        
    def _parse_csv(self, path: Path, include_metadata: bool) -> Dict[str, Any]:
        """Parse CSV file."""
        with open(path, 'r', encoding='utf-8') as f:
            # Detect delimiter
            sample = f.read(1024)
            f.seek(0)
            sniffer = csv.Sniffer()
            delimiter = sniffer.sniff(sample).delimiter
            
            reader = csv.DictReader(f, delimiter=delimiter)
            rows = list(reader)
            
        result = {
            'format': 'csv',
            'rows': len(rows),
            'columns': list(reader.fieldnames) if reader.fieldnames else [],
            'data': rows[:100],  # Limit to first 100 rows
            'delimiter': delimiter
        }
        
        if include_metadata:
            result['metadata'] = {
                'has_headers': bool(reader.fieldnames),
                'total_rows': len(rows),
                'columns_count': len(reader.fieldnames) if reader.fieldnames else 0
            }
            
        return result
        
    def _parse_json(self, path: Path, include_metadata: bool) -> Dict[str, Any]:
        """Parse JSON file."""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        result = {
            'format': 'json',
            'data': data,
            'type': type(data).__name__
        }
        
        if include_metadata:
            result['metadata'] = {
                'keys_count': len(data) if isinstance(data, dict) else None,
                'items_count': len(data) if isinstance(data, list) else None,
                'max_depth': self._calculate_json_depth(data)
            }
            
        return result
        
    def _parse_xml(self, path: Path, include_metadata: bool) -> Dict[str, Any]:
        """Parse XML file (placeholder - would use xml.etree or lxml)."""
        return {
            'format': 'xml',
            'text': 'XML parsing not implemented - would parse XML structure',
            'metadata': {} if include_metadata else None
        }
        
    def _parse_generic(self, path: Path, include_metadata: bool) -> Dict[str, Any]:
        """Generic file parsing - attempt to read as text."""
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(1024)  # Read first 1KB
                
            return {
                'format': 'generic',
                'text_preview': content,
                'note': 'File parsed as generic text - full parsing not supported for this format'
            }
            
        except Exception as e:
            return {
                'format': 'binary',
                'error': str(e),
                'note': 'File appears to be binary and cannot be parsed as text'
            }
            
    def _calculate_json_depth(self, obj, depth=0):
        """Calculate maximum depth of JSON structure."""
        if isinstance(obj, dict):
            return max([self._calculate_json_depth(v, depth + 1) for v in obj.values()], default=depth)
        elif isinstance(obj, list):
            return max([self._calculate_json_depth(item, depth + 1) for item in obj], default=depth)
        else:
            return depth