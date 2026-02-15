"""
LookML Context Tracking System

Tracks LookML artifacts created during the session to enable
query generation without API validation (perfect for bare repos).
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
import re


@dataclass
class Field:
    """Represents a LookML field (dimension or measure)"""
    name: str
    type: str  # dimension, measure, dimension_group
    field_type: str  # string, number, date, yesno, count, sum, etc.
    label: str
    sql: Optional[str] = None


@dataclass
class ViewMetadata:
    """Metadata for a LookML view"""
    name: str
    fields: List[Field]
    sql_table_name: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ModelMetadata:
    """Metadata for a LookML model"""
    name: str
    connection: str
    explores: List[str]
    includes: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ExploreMetadata:
    """Metadata for a LookML explore"""
    model_name: str
    explore_name: str
    base_view: str
    joins: List[Dict] = field(default_factory=list)
    fields: List[Field] = field(default_factory=list)
    field_source: str = "parsed"  # "parsed" from LookML or "api" from Looker API


class LookMLContext:
    """
    Tracks LookML artifacts created during the session.
    Provides query generation without API validation.
    """
    
    def __init__(self):
        self.views: Dict[str, ViewMetadata] = {}
        self.models: Dict[str, ModelMetadata] = {}
        self.explores: Dict[str, ExploreMetadata] = {}  # Key: "model.explore"
    
    def register_view(self, view_name: str, fields: List[Field], sql_table_name: Optional[str] = None):
        """Register a created view with its fields"""
        self.views[view_name] = ViewMetadata(
            name=view_name,
            fields=fields,
            sql_table_name=sql_table_name
        )
    
    def register_model(self, model_name: str, connection: str, explores: List[str], includes: List[str] = None):
        """Register a created model with its explores"""
        self.models[model_name] = ModelMetadata(
            name=model_name,
            connection=connection,
            explores=explores,
            includes=includes or []
        )
    
    def register_explore(self, model: str, explore: str, base_view: str, joins: List[Dict] = None):
        """Register an explore (model + explore + base view)"""
        explore_key = f"{model}.{explore}"
        
        # Get fields from base view
        fields = []
        if base_view in self.views:
            fields = self.views[base_view].fields.copy()
        
        # TODO: Add fields from joined views
        
        self.explores[explore_key] = ExploreMetadata(
            model_name=model,
            explore_name=explore,
            base_view=base_view,
            joins=joins or [],
            fields=fields
        )

    def has_explore(self, model: str, explore: str) -> bool:
        """Check if an explore exists in the context"""
        return f"{model}.{explore}" in self.explores
    
    def get_available_fields(self, model: str, explore: str) -> List[Field]:
        """Get fields for an explore without API call"""
        explore_key = f"{model}.{explore}"
        if explore_key in self.explores:
            return self.explores[explore_key].fields
        return []
    
    def has_explore(self, model: str, explore: str) -> bool:
        """Check if an explore exists in context"""
        explore_key = f"{model}.{explore}"
        return explore_key in self.explores
    
    def register_explore_fields(self, model: str, explore: str, fields: List[Field], source: str = "api"):
        """Register fields for an explore with source tracking (api or parsed)"""
        explore_key = f"{model}.{explore}"
        
        if explore_key in self.explores:
            # Update existing explore with API fields
            self.explores[explore_key].fields = fields
            self.explores[explore_key].field_source = source
        else:
            # Create new explore entry
            self.explores[explore_key] = ExploreMetadata(
                model_name=model,
                explore_name=explore,
                base_view=explore,  # Assume base view has same name
                fields=fields,
                field_source=source
            )
    
    def get_api_verified_fields(self, model: str, explore: str) -> List[Field]:
        """Get only fields that were fetched from API (authoritative)"""
        explore_key = f"{model}.{explore}"
        explore_meta = self.explores.get(explore_key)
        
        if not explore_meta or explore_meta.field_source != "api":
            return []
        
        return explore_meta.fields
    
    def has_api_verified_fields(self, model: str, explore: str) -> bool:
        """Check if explore has API-verified fields"""
        explore_key = f"{model}.{explore}"
        explore_meta = self.explores.get(explore_key)
        return explore_meta is not None and explore_meta.field_source == "api"
    
    def get_summary(self) -> Dict:
        """Get summary of tracked LookML artifacts"""
        api_verified_explores = [k for k, v in self.explores.items() if v.field_source == "api"]
        return {
            "views": list(self.views.keys()),
            "models": list(self.models.keys()),
            "explores": list(self.explores.keys()),
            "api_verified_explores": api_verified_explores,
            "total_fields": sum(len(v.fields) for v in self.views.values())
        }


class LookMLParser:
    """Parser for LookML files to extract metadata"""
    
    @staticmethod
    def parse_view(lookml_content: str) -> Optional[ViewMetadata]:
        """Parse view LookML and extract fields"""
        # Extract view name
        view_match = re.search(r'view:\s+(\w+)', lookml_content)
        if not view_match:
            return None
        
        view_name = view_match.group(1)
        
        # Extract sql_table_name
        table_match = re.search(r'sql_table_name:\s+["`]?([^"`\s]+)["`]?', lookml_content)
        sql_table_name = table_match.group(1) if table_match else None
        
        fields = []
        
        # Extract dimensions
        for match in re.finditer(r'dimension:\s+(\w+)\s*\{([^}]+)\}', lookml_content, re.DOTALL):
            dim_name = match.group(1)
            dim_body = match.group(2)
            
            # Extract type
            type_match = re.search(r'type:\s+(\w+)', dim_body)
            field_type = type_match.group(1) if type_match else 'string'
            
            # Extract label
            label_match = re.search(r'label:\s+"([^"]+)"', dim_body)
            label = label_match.group(1) if label_match else dim_name.replace('_', ' ').title()
            
            # Extract SQL
            sql_match = re.search(r'sql:\s+([^;]+);', dim_body)
            sql = sql_match.group(1).strip() if sql_match else None
            
            fields.append(Field(
                name=dim_name,
                type='dimension',
                field_type=field_type,
                label=label,
                sql=sql
            ))
        
        # Extract measures
        for match in re.finditer(r'measure:\s+(\w+)\s*\{([^}]+)\}', lookml_content, re.DOTALL):
            meas_name = match.group(1)
            meas_body = match.group(2)
            
            type_match = re.search(r'type:\s+(\w+)', meas_body)
            field_type = type_match.group(1) if type_match else 'count'
            
            label_match = re.search(r'label:\s+"([^"]+)"', meas_body)
            label = label_match.group(1) if label_match else meas_name.replace('_', ' ').title()
            
            sql_match = re.search(r'sql:\s+([^;]+);', meas_body)
            sql = sql_match.group(1).strip() if sql_match else None
            
            fields.append(Field(
                name=meas_name,
                type='measure',
                field_type=field_type,
                label=label,
                sql=sql
            ))
        
        return ViewMetadata(
            name=view_name,
            fields=fields,
            sql_table_name=sql_table_name
        )
    
    @staticmethod
    def parse_model(lookml_content: str, model_name: str) -> Optional[ModelMetadata]:
        """Parse model LookML and extract explores"""
        # Extract connection
        conn_match = re.search(r'connection:\s+"?([^"\s]+)"?', lookml_content)
        connection = conn_match.group(1) if conn_match else 'unknown'
        
        # Extract includes
        includes = []
        for match in re.finditer(r'include:\s+"([^"]+)"', lookml_content):
            includes.append(match.group(1))
        
        # Extract explores (names only for now, but we could parse blocks)
        explores = []
        for match in re.finditer(r'explore:\s+(\w+)', lookml_content):
            explore_name = match.group(1)
            explores.append(explore_name)
        
        return ModelMetadata(
            name=model_name,
            connection=connection,
            explores=explores,
            includes=includes
        )

    @staticmethod
    def parse_explore(lookml_content: str) -> Optional[ExploreMetadata]:
        """Parse explore LookML block and extract metadata"""
        # Note: This expects an "explore: name { ... }" block or file content
        
        explore_match = re.search(r'explore:\s+(\w+)', lookml_content)
        if not explore_match:
            return None
        explore_name = explore_match.group(1)
        
        # Extract base view (from 'from' parameter or default to explore name)
        from_match = re.search(r'from:\s+(\w+)', lookml_content)
        base_view = from_match.group(1) if from_match else explore_name

        # Extract joins
        joins = []
        # Regex to match join block with balanced braces for ${...}
        # matches: join: name { content }
        # content can contain anything except } OR ${...} which contains anything except }
        for match in re.finditer(r'join:\s+(\w+)\s*\{((?:[^{}]|\$\{[^}]+\})+)\}', lookml_content, re.DOTALL):
            join_name = match.group(1)
            join_body = match.group(2)
            
            # Simple extraction of sql_on or type if needed
            # Use DOTALL for sql_on to capture multi-line SQL
            # Non-greedy match until ;;
            sql_on_match = re.search(r'sql_on:\s+(.*?);;', join_body, re.DOTALL)
            relationship_match = re.search(r'relationship:\s+(\w+)', join_body)
            
            sql_on = sql_on_match.group(1).strip() if sql_on_match else None
            
            joins.append({
                "name": join_name,
                "sql_on": sql_on,
                "relationship": relationship_match.group(1) if relationship_match else "many_to_one"
            })
            
        return ExploreMetadata(
            model_name="unknown", # Context must supply this
            explore_name=explore_name,
            base_view=base_view,
            joins=joins
        )
