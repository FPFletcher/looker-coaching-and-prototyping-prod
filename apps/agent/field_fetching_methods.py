    def _fetch_and_register_explore_fields(self, model: str, explore: str, url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """
        Fetch actual dimensions/measures from API and register in context.
        This ensures we only use real fields, never invented ones.
        """
        try:
            logger.info(f"🔍 [FETCH_FIELDS] Fetching fields for {model}.{explore} from API...")
            sdk = self._init_sdk(url, client_id, client_secret)
            
            # Get explore metadata from API
            explore_metadata = sdk.lookml_model_explore(model, explore)
            
            from lookml_context import Field
            
            # Extract dimensions
            dimensions = []
            for field in explore_metadata.fields.dimensions or []:
                dimensions.append(Field(
                    name=field.name,
                    type="dimension",
                    field_type=field.type or "string",
                    label=field.label_short or field.label or field.name,
                    sql=None
                ))
            
            # Extract measures
            measures = []
            for field in explore_metadata.fields.measures or []:
                measures.append(Field(
                    name=field.name,
                    type="measure",
                    field_type=field.type or "count",
                    label=field.label_short or field.label or field.name,
                    sql=None
                ))
            
            # Register in context with API source
            all_fields = dimensions + measures
            self.lookml_context.register_explore_fields(
                model=model,
                explore=explore,
                fields=all_fields,
                source="api"  # Mark as API-fetched (authoritative)
            )
            
            logger.info(f"✅ Registered {len(dimensions)} dimensions and {len(measures)} measures from API")
            
            return {
                "success": True,
                "dimensions": len(dimensions),
                "measures": len(measures),
                "total_fields": len(all_fields),
                "field_names": [f.name for f in all_fields]
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch fields: {e}")
            return {"success": False, "error": str(e)}
    
    def _execute_get_explore_fields(self, args: Dict[str, Any], url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """
        Tool to explicitly fetch dimensions and measures for an explore.
        ALWAYS call this before creating dashboards to ensure real fields are used.
        """
        model = args.get("model")
        explore = args.get("explore")
        
        result = self._fetch_and_register_explore_fields(model, explore, url, client_id, client_secret)
        
        if result.get("success"):
            return {
                "success": True,
                "model": model,
                "explore": explore,
                "dimensions": result["dimensions"],
                "measures": result["measures"],
                "total_fields": result["total_fields"],
                "available_fields": result["field_names"],
                "message": f"✅ Fetched {result['total_fields']} real fields from API. Use ONLY these fields when creating dashboards."
            }
        else:
            return result
