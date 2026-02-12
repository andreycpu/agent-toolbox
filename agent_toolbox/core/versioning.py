"""Tool versioning and migration system."""

import re
import json
import hashlib
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class VersionCompatibility(Enum):
    """Version compatibility levels."""
    COMPATIBLE = "compatible"
    BACKWARD_COMPATIBLE = "backward_compatible"
    BREAKING_CHANGE = "breaking_change"
    DEPRECATED = "deprecated"


@dataclass
class Version:
    """Semantic version representation."""
    
    major: int
    minor: int
    patch: int
    pre_release: Optional[str] = None
    build: Optional[str] = None
    
    @classmethod
    def from_string(cls, version_str: str) -> 'Version':
        """Parse version from string."""
        # Match semantic version pattern
        pattern = r'^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9\-\.]+))?(?:\+([a-zA-Z0-9\-\.]+))?$'
        match = re.match(pattern, version_str)
        
        if not match:
            raise ValueError(f"Invalid version format: {version_str}")
            
        major, minor, patch = map(int, match.groups()[:3])
        pre_release = match.group(4)
        build = match.group(5)
        
        return cls(major, minor, patch, pre_release, build)
        
    def to_string(self) -> str:
        """Convert version to string."""
        version = f"{self.major}.{self.minor}.{self.patch}"
        
        if self.pre_release:
            version += f"-{self.pre_release}"
            
        if self.build:
            version += f"+{self.build}"
            
        return version
        
    def is_compatible_with(self, other: 'Version') -> VersionCompatibility:
        """Check compatibility with another version."""
        if self.major != other.major:
            return VersionCompatibility.BREAKING_CHANGE
            
        if self.minor > other.minor:
            return VersionCompatibility.BACKWARD_COMPATIBLE
        elif self.minor < other.minor:
            return VersionCompatibility.BREAKING_CHANGE
            
        if self.patch > other.patch:
            return VersionCompatibility.COMPATIBLE
        elif self.patch < other.patch:
            return VersionCompatibility.COMPATIBLE
            
        return VersionCompatibility.COMPATIBLE
        
    def __eq__(self, other) -> bool:
        if not isinstance(other, Version):
            return False
        return (self.major, self.minor, self.patch, self.pre_release, self.build) == \
               (other.major, other.minor, other.patch, other.pre_release, other.build)
               
    def __lt__(self, other) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
            
        # Compare major.minor.patch
        self_tuple = (self.major, self.minor, self.patch)
        other_tuple = (other.major, other.minor, other.patch)
        
        if self_tuple != other_tuple:
            return self_tuple < other_tuple
            
        # Handle pre-release versions
        if self.pre_release is None and other.pre_release is None:
            return False
        elif self.pre_release is None:
            return False  # Release > pre-release
        elif other.pre_release is None:
            return True  # Pre-release < release
        else:
            return self.pre_release < other.pre_release
            
    def __le__(self, other) -> bool:
        return self == other or self < other
        
    def __gt__(self, other) -> bool:
        return not self <= other
        
    def __ge__(self, other) -> bool:
        return not self < other
        
    def __str__(self) -> str:
        return self.to_string()
        
    def __repr__(self) -> str:
        return f"Version('{self.to_string()}')"


@dataclass
class ParameterMigration:
    """Parameter migration definition."""
    
    old_name: str
    new_name: Optional[str] = None
    transform: Optional[Callable[[Any], Any]] = None
    default_value: Any = None
    removed: bool = False
    
    
@dataclass
class VersionMigration:
    """Migration between two versions."""
    
    from_version: Version
    to_version: Version
    parameter_migrations: List[ParameterMigration] = field(default_factory=list)
    custom_migration: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None
    breaking_changes: List[str] = field(default_factory=list)
    deprecation_warnings: List[str] = field(default_factory=list)
    
    
@dataclass
class ToolVersion:
    """Tool version metadata."""
    
    tool_name: str
    version: Version
    schema_hash: Optional[str] = None
    parameter_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    dependencies: Dict[str, str] = field(default_factory=dict)
    changelog: List[str] = field(default_factory=list)
    deprecated: bool = False
    deprecation_date: Optional[str] = None
    removal_date: Optional[str] = None
    
    def calculate_schema_hash(self) -> str:
        """Calculate hash of parameter and output schemas."""
        schema_data = {
            'parameter_schema': self.parameter_schema,
            'output_schema': self.output_schema
        }
        schema_json = json.dumps(schema_data, sort_keys=True)
        return hashlib.sha256(schema_json.encode()).hexdigest()[:16]
        
    def __post_init__(self):
        if self.schema_hash is None and (self.parameter_schema or self.output_schema):
            self.schema_hash = self.calculate_schema_hash()


class VersionRegistry:
    """Registry for tool versions and migrations."""
    
    def __init__(self):
        self.tool_versions: Dict[str, List[ToolVersion]] = {}
        self.migrations: Dict[str, List[VersionMigration]] = {}
        
    def register_version(self, tool_version: ToolVersion) -> None:
        """Register a new tool version."""
        tool_name = tool_version.tool_name
        
        if tool_name not in self.tool_versions:
            self.tool_versions[tool_name] = []
            
        # Check if version already exists
        existing_versions = [tv.version for tv in self.tool_versions[tool_name]]
        if tool_version.version in existing_versions:
            raise ValueError(f"Version {tool_version.version} already exists for tool {tool_name}")
            
        self.tool_versions[tool_name].append(tool_version)
        
        # Sort versions
        self.tool_versions[tool_name].sort(key=lambda tv: tv.version)
        
        logger.info(f"Registered version {tool_version.version} for tool {tool_name}")
        
    def register_migration(self, migration: VersionMigration) -> None:
        """Register a migration between versions."""
        tool_name = None
        
        # Find tool name from existing versions
        for name, versions in self.tool_versions.items():
            version_list = [tv.version for tv in versions]
            if migration.from_version in version_list or migration.to_version in version_list:
                tool_name = name
                break
                
        if not tool_name:
            raise ValueError("Cannot register migration: versions not found in registry")
            
        if tool_name not in self.migrations:
            self.migrations[tool_name] = []
            
        self.migrations[tool_name].append(migration)
        logger.info(f"Registered migration from {migration.from_version} to {migration.to_version} for tool {tool_name}")
        
    def get_latest_version(self, tool_name: str) -> Optional[ToolVersion]:
        """Get the latest version of a tool."""
        if tool_name not in self.tool_versions:
            return None
            
        versions = self.tool_versions[tool_name]
        if not versions:
            return None
            
        # Filter out deprecated versions unless all are deprecated
        non_deprecated = [tv for tv in versions if not tv.deprecated]
        if non_deprecated:
            return max(non_deprecated, key=lambda tv: tv.version)
        else:
            return max(versions, key=lambda tv: tv.version)
            
    def get_version(self, tool_name: str, version: Union[str, Version]) -> Optional[ToolVersion]:
        """Get a specific version of a tool."""
        if isinstance(version, str):
            version = Version.from_string(version)
            
        if tool_name not in self.tool_versions:
            return None
            
        for tool_version in self.tool_versions[tool_name]:
            if tool_version.version == version:
                return tool_version
                
        return None
        
    def get_compatible_version(self, tool_name: str, version: Union[str, Version]) -> Optional[ToolVersion]:
        """Get the best compatible version of a tool."""
        if isinstance(version, str):
            version = Version.from_string(version)
            
        if tool_name not in self.tool_versions:
            return None
            
        # Find exact match first
        exact_match = self.get_version(tool_name, version)
        if exact_match and not exact_match.deprecated:
            return exact_match
            
        # Find compatible versions
        compatible_versions = []
        
        for tool_version in self.tool_versions[tool_name]:
            if tool_version.deprecated:
                continue
                
            compatibility = tool_version.version.is_compatible_with(version)
            if compatibility in [VersionCompatibility.COMPATIBLE, VersionCompatibility.BACKWARD_COMPATIBLE]:
                compatible_versions.append(tool_version)
                
        if compatible_versions:
            # Return the highest compatible version
            return max(compatible_versions, key=lambda tv: tv.version)
            
        return None
        
    def find_migration_path(self, tool_name: str, from_version: Version, to_version: Version) -> List[VersionMigration]:
        """Find migration path between versions."""
        if tool_name not in self.migrations:
            return []
            
        migrations = self.migrations[tool_name]
        
        # Simple case: direct migration exists
        for migration in migrations:
            if migration.from_version == from_version and migration.to_version == to_version:
                return [migration]
                
        # Complex case: find path through multiple migrations
        # Using simple BFS for now
        from collections import deque
        
        queue = deque([(from_version, [])])
        visited = {from_version}
        
        while queue:
            current_version, path = queue.popleft()
            
            if current_version == to_version:
                return path
                
            # Find all migrations from current version
            for migration in migrations:
                if (migration.from_version == current_version and 
                    migration.to_version not in visited):
                    
                    new_path = path + [migration]
                    queue.append((migration.to_version, new_path))
                    visited.add(migration.to_version)
                    
        return []  # No migration path found
        
    def get_all_versions(self, tool_name: str) -> List[ToolVersion]:
        """Get all versions of a tool."""
        return self.tool_versions.get(tool_name, []).copy()
        
    def get_deprecated_versions(self, tool_name: str) -> List[ToolVersion]:
        """Get deprecated versions of a tool."""
        if tool_name not in self.tool_versions:
            return []
            
        return [tv for tv in self.tool_versions[tool_name] if tv.deprecated]


class ParameterMigrator:
    """Migrates parameters between tool versions."""
    
    def __init__(self, version_registry: VersionRegistry):
        self.version_registry = version_registry
        
    def migrate_parameters(self, 
                          tool_name: str,
                          parameters: Dict[str, Any],
                          from_version: Union[str, Version],
                          to_version: Union[str, Version]) -> Tuple[Dict[str, Any], List[str]]:
        """Migrate parameters between versions."""
        
        if isinstance(from_version, str):
            from_version = Version.from_string(from_version)
        if isinstance(to_version, str):
            to_version = Version.from_string(to_version)
            
        # Find migration path
        migration_path = self.version_registry.find_migration_path(tool_name, from_version, to_version)
        
        if not migration_path:
            raise ValueError(f"No migration path found from {from_version} to {to_version} for tool {tool_name}")
            
        migrated_params = parameters.copy()
        warnings = []
        
        # Apply migrations in sequence
        for migration in migration_path:
            migrated_params, migration_warnings = self._apply_migration(migration, migrated_params)
            warnings.extend(migration_warnings)
            
        return migrated_params, warnings
        
    def _apply_migration(self, 
                        migration: VersionMigration, 
                        parameters: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        """Apply a single migration to parameters."""
        
        result = parameters.copy()
        warnings = []
        
        # Apply custom migration first if available
        if migration.custom_migration:
            try:
                result = migration.custom_migration(result)
            except Exception as e:
                logger.error(f"Custom migration failed: {str(e)}")
                warnings.append(f"Custom migration failed: {str(e)}")
                
        # Apply parameter migrations
        for param_migration in migration.parameter_migrations:
            if param_migration.removed:
                # Remove parameter
                if param_migration.old_name in result:
                    del result[param_migration.old_name]
                    warnings.append(f"Parameter '{param_migration.old_name}' was removed")
                    
            elif param_migration.new_name:
                # Rename parameter
                if param_migration.old_name in result:
                    value = result[param_migration.old_name]
                    
                    # Apply transformation if available
                    if param_migration.transform:
                        try:
                            value = param_migration.transform(value)
                        except Exception as e:
                            logger.error(f"Parameter transformation failed: {str(e)}")
                            warnings.append(f"Transformation failed for '{param_migration.old_name}': {str(e)}")
                            
                    result[param_migration.new_name] = value
                    del result[param_migration.old_name]
                    warnings.append(f"Parameter '{param_migration.old_name}' renamed to '{param_migration.new_name}'")
                    
            else:
                # Transform parameter in place
                if param_migration.old_name in result and param_migration.transform:
                    try:
                        result[param_migration.old_name] = param_migration.transform(result[param_migration.old_name])
                    except Exception as e:
                        logger.error(f"Parameter transformation failed: {str(e)}")
                        warnings.append(f"Transformation failed for '{param_migration.old_name}': {str(e)}")
                        
        # Add deprecation warnings
        warnings.extend([f"Deprecation: {warning}" for warning in migration.deprecation_warnings])
        
        # Add breaking change warnings
        warnings.extend([f"Breaking change: {change}" for change in migration.breaking_changes])
        
        return result, warnings
        
    def validate_parameters(self, 
                           tool_name: str,
                           parameters: Dict[str, Any],
                           version: Union[str, Version]) -> List[str]:
        """Validate parameters against version schema."""
        
        if isinstance(version, str):
            version = Version.from_string(version)
            
        tool_version = self.version_registry.get_version(tool_name, version)
        if not tool_version:
            return [f"Version {version} not found for tool {tool_name}"]
            
        if not tool_version.parameter_schema:
            return []  # No schema to validate against
            
        errors = []
        schema = tool_version.parameter_schema
        
        # Simple validation (in real implementation, use jsonschema or similar)
        required_params = schema.get('required', [])
        for param in required_params:
            if param not in parameters:
                errors.append(f"Required parameter '{param}' is missing")
                
        # Check for unknown parameters
        allowed_params = set(schema.get('properties', {}).keys())
        for param in parameters:
            if param not in allowed_params:
                errors.append(f"Unknown parameter '{param}'")
                
        return errors


class VersionedTool:
    """Wrapper for tools with version management."""
    
    def __init__(self, 
                 tool_name: str,
                 version_registry: VersionRegistry,
                 parameter_migrator: ParameterMigrator):
        self.tool_name = tool_name
        self.version_registry = version_registry
        self.parameter_migrator = parameter_migrator
        
    def execute(self, 
               parameters: Dict[str, Any],
               version: Optional[Union[str, Version]] = None,
               auto_migrate: bool = True) -> Any:
        """Execute tool with version management."""
        
        # Use latest version if not specified
        if version is None:
            tool_version = self.version_registry.get_latest_version(self.tool_name)
            if not tool_version:
                raise ValueError(f"No versions available for tool {self.tool_name}")
            version = tool_version.version
        elif isinstance(version, str):
            version = Version.from_string(version)
            
        # Get tool version
        tool_version = self.version_registry.get_version(self.tool_name, version)
        if not tool_version:
            if auto_migrate:
                # Try to find compatible version
                tool_version = self.version_registry.get_compatible_version(self.tool_name, version)
                if tool_version:
                    logger.info(f"Using compatible version {tool_version.version} instead of {version}")
                    
        if not tool_version:
            raise ValueError(f"Version {version} not available for tool {self.tool_name}")
            
        # Validate parameters
        validation_errors = self.parameter_migrator.validate_parameters(
            self.tool_name, parameters, tool_version.version
        )
        
        if validation_errors:
            raise ValueError(f"Parameter validation failed: {', '.join(validation_errors)}")
            
        # Check for deprecation warnings
        if tool_version.deprecated:
            logger.warning(f"Tool {self.tool_name} version {tool_version.version} is deprecated")
            if tool_version.removal_date:
                logger.warning(f"This version will be removed on {tool_version.removal_date}")
                
        # Execute tool (placeholder - would call actual tool implementation)
        logger.info(f"Executing {self.tool_name} v{tool_version.version} with parameters: {parameters}")
        
        # Return placeholder result
        return {
            'tool_name': self.tool_name,
            'version': str(tool_version.version),
            'parameters': parameters,
            'result': 'success'
        }
        
    def get_version_info(self, version: Optional[Union[str, Version]] = None) -> Optional[ToolVersion]:
        """Get version information."""
        if version is None:
            return self.version_registry.get_latest_version(self.tool_name)
        elif isinstance(version, str):
            version = Version.from_string(version)
            
        return self.version_registry.get_version(self.tool_name, version)
        
    def list_versions(self) -> List[ToolVersion]:
        """List all available versions."""
        return self.version_registry.get_all_versions(self.tool_name)


# Global version registry
_global_version_registry = None
_global_parameter_migrator = None


def get_global_version_registry() -> VersionRegistry:
    """Get the global version registry."""
    global _global_version_registry
    if _global_version_registry is None:
        _global_version_registry = VersionRegistry()
    return _global_version_registry


def get_global_parameter_migrator() -> ParameterMigrator:
    """Get the global parameter migrator."""
    global _global_parameter_migrator
    if _global_parameter_migrator is None:
        registry = get_global_version_registry()
        _global_parameter_migrator = ParameterMigrator(registry)
    return _global_parameter_migrator


def versioned(tool_name: str, 
             version: str,
             parameter_schema: Optional[Dict[str, Any]] = None,
             output_schema: Optional[Dict[str, Any]] = None,
             dependencies: Optional[Dict[str, str]] = None,
             changelog: Optional[List[str]] = None):
    """Decorator to register a versioned tool."""
    
    def decorator(tool_func: Callable) -> Callable:
        registry = get_global_version_registry()
        
        tool_version = ToolVersion(
            tool_name=tool_name,
            version=Version.from_string(version),
            parameter_schema=parameter_schema,
            output_schema=output_schema,
            dependencies=dependencies or {},
            changelog=changelog or []
        )
        
        registry.register_version(tool_version)
        
        return tool_func
        
    return decorator