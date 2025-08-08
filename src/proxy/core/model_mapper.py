"""Model mapping functionality."""

from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..models import ModelMapping, Provider
from ..models.database import get_db_session


class ModelMapper:
    """Handles mapping between client model names and provider models."""
    
    def __init__(self):
        pass
    
    def get_provider_mapping(self, model_alias: str, tenant_id: Optional[str] = None) -> List[Tuple[Provider, str, Dict[str, Any]]]:
        """Get ordered list of provider mappings for a model alias.
        
        Args:
            model_alias: Client-facing model name
            tenant_id: Optional tenant ID for tenant-specific mappings
            
        Returns:
            List of tuples: (Provider, provider_model_name, config)
        """
        with get_db_session() as db:
            # Query mappings ordered by order_index
            mappings = db.query(ModelMapping, Provider).join(
                Provider, ModelMapping.provider_id == Provider.id
            ).filter(
                ModelMapping.alias_name == model_alias
            ).order_by(ModelMapping.order_index).all()
            
            if not mappings:
                return []
            
            result = []
            for mapping, provider in mappings:
                result.append((
                    provider,
                    mapping.provider_model_name,
                    mapping.config_json or {}
                ))
            
            return result
    
    def get_default_mapping(self, model_alias: str) -> Optional[Tuple[Provider, str, Dict[str, Any]]]:
        """Get the default (first) mapping for a model alias.
        
        Args:
            model_alias: Client-facing model name
            
        Returns:
            Tuple of (Provider, provider_model_name, config) or None
        """
        mappings = self.get_provider_mapping(model_alias)
        return mappings[0] if mappings else None
    
    def get_fallback_mappings(self, model_alias: str, exclude_provider_id: Optional[int] = None) -> List[Tuple[Provider, str, Dict[str, Any]]]:
        """Get fallback mappings for a model alias, excluding specified provider.
        
        Args:
            model_alias: Client-facing model name
            exclude_provider_id: Provider ID to exclude from results
            
        Returns:
            List of tuples: (Provider, provider_model_name, config)
        """
        mappings = self.get_provider_mapping(model_alias)
        
        if exclude_provider_id:
            mappings = [
                (provider, model_name, config)
                for provider, model_name, config in mappings
                if provider.id != exclude_provider_id
            ]
        
        return mappings
    
    def create_mapping(
        self,
        alias_name: str,
        provider_id: int,
        provider_model_name: str,
        order_index: int = 0,
        is_default: bool = False,
        config: Optional[Dict[str, Any]] = None
    ) -> ModelMapping:
        """Create a new model mapping.
        
        Args:
            alias_name: Client-facing model name
            provider_id: Provider ID
            provider_model_name: Provider's model name
            order_index: Order for fallback (lower = higher priority)
            is_default: Whether this is the default mapping
            config: Optional model-specific configuration
            
        Returns:
            Created ModelMapping instance
        """
        with get_db_session() as db:
            # If this is marked as default, unset other defaults for this alias
            if is_default:
                db.query(ModelMapping).filter(
                    and_(
                        ModelMapping.alias_name == alias_name,
                        ModelMapping.is_default == True
                    )
                ).update({ModelMapping.is_default: False})
            
            mapping = ModelMapping(
                alias_name=alias_name,
                provider_id=provider_id,
                provider_model_name=provider_model_name,
                order_index=order_index,
                is_default=is_default,
                config_json=config or {}
            )
            
            db.add(mapping)
            db.commit()
            db.refresh(mapping)
            
            return mapping
    
    def update_mapping(
        self,
        mapping_id: int,
        provider_model_name: Optional[str] = None,
        order_index: Optional[int] = None,
        is_default: Optional[bool] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Optional[ModelMapping]:
        """Update an existing model mapping.
        
        Args:
            mapping_id: Mapping ID to update
            provider_model_name: New provider model name
            order_index: New order index
            is_default: New default status
            config: New configuration
            
        Returns:
            Updated ModelMapping instance or None if not found
        """
        with get_db_session() as db:
            mapping = db.query(ModelMapping).filter(ModelMapping.id == mapping_id).first()
            if not mapping:
                return None
            
            # If setting as default, unset other defaults for this alias
            if is_default:
                db.query(ModelMapping).filter(
                    and_(
                        ModelMapping.alias_name == mapping.alias_name,
                        ModelMapping.is_default == True,
                        ModelMapping.id != mapping_id
                    )
                ).update({ModelMapping.is_default: False})
            
            # Update fields
            if provider_model_name is not None:
                mapping.provider_model_name = provider_model_name
            if order_index is not None:
                mapping.order_index = order_index
            if is_default is not None:
                mapping.is_default = is_default
            if config is not None:
                mapping.config_json = config
            
            db.commit()
            db.refresh(mapping)
            
            return mapping
    
    def delete_mapping(self, mapping_id: int) -> bool:
        """Delete a model mapping.
        
        Args:
            mapping_id: Mapping ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        with get_db_session() as db:
            mapping = db.query(ModelMapping).filter(ModelMapping.id == mapping_id).first()
            if not mapping:
                return False
            
            db.delete(mapping)
            db.commit()
            
            return True
    
    def list_mappings(self, alias_name: Optional[str] = None, provider_id: Optional[int] = None) -> List[ModelMapping]:
        """List model mappings with optional filters.
        
        Args:
            alias_name: Filter by alias name
            provider_id: Filter by provider ID
            
        Returns:
            List of ModelMapping instances
        """
        with get_db_session() as db:
            query = db.query(ModelMapping)
            
            if alias_name:
                query = query.filter(ModelMapping.alias_name == alias_name)
            if provider_id:
                query = query.filter(ModelMapping.provider_id == provider_id)
            
            return query.order_by(ModelMapping.alias_name, ModelMapping.order_index).all()
    
    def get_available_models(self) -> List[str]:
        """Get list of all available model aliases.
        
        Returns:
            List of unique model alias names
        """
        with get_db_session() as db:
            aliases = db.query(ModelMapping.alias_name).distinct().all()
            return [alias[0] for alias in aliases]
    
    def validate_mapping(self, alias_name: str, provider_id: int, provider_model_name: str) -> Dict[str, Any]:
        """Validate a model mapping configuration.
        
        Args:
            alias_name: Client-facing model name
            provider_id: Provider ID
            provider_model_name: Provider's model name
            
        Returns:
            Dictionary with validation results
        """
        with get_db_session() as db:
            # Check if provider exists
            provider = db.query(Provider).filter(Provider.id == provider_id).first()
            if not provider:
                return {
                    "valid": False,
                    "error": f"Provider with ID {provider_id} not found"
                }
            
            # Check if provider is active
            if provider.status != "active":
                return {
                    "valid": False,
                    "error": f"Provider '{provider.name}' is not active"
                }
            
            # Check for duplicate mappings (same alias, provider, model)
            existing = db.query(ModelMapping).filter(
                and_(
                    ModelMapping.alias_name == alias_name,
                    ModelMapping.provider_id == provider_id,
                    ModelMapping.provider_model_name == provider_model_name
                )
            ).first()
            
            if existing:
                return {
                    "valid": False,
                    "error": f"Mapping already exists for alias '{alias_name}' to provider '{provider.name}' model '{provider_model_name}'"
                }
            
            return {
                "valid": True,
                "provider": provider.name,
                "provider_type": provider.provider_type
            }


# Global model mapper instance
model_mapper = ModelMapper()