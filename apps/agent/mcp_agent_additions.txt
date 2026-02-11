    # ===== LOOKML CONTEXT TRACKING HELPERS =====
    
    def _register_lookml_in_context(self, path: str, source: str, project_id: str):
        """Parse and register LookML file in context"""
        try:
            from lookml_context import LookMLParser
            
            if path.endswith(".view.lkml"):
                # Parse view
                view_metadata = LookMLParser.parse_view(source)
                if view_metadata:
                    self.lookml_context.register_view(
                        view_name=view_metadata.name,
                        fields=view_metadata.fields,
                        sql_table_name=view_metadata.sql_table_name
                    )
                    logger.info(f"✅ Registered view '{view_metadata.name}' with {len(view_metadata.fields)} fields in context")
            
            elif path.endswith(".model.lkml"):
                # Extract model name from path
                model_name = path.replace(".model.lkml", "").split("/")[-1]
                
                # Parse model
                model_metadata = LookMLParser.parse_model(source, model_name)
                if model_metadata:
                    self.lookml_context.register_model(
                        model_name=model_metadata.name,
                        connection=model_metadata.connection,
                        explores=model_metadata.explores,
                        includes=model_metadata.includes
                    )
                    logger.info(f"✅ Registered model '{model_metadata.name}' with {len(model_metadata.explores)} explores in context")
                    
                    # Register each explore
                    for explore_name in model_metadata.explores:
                        # Assume base view has same name as explore (common pattern)
                        self.lookml_context.register_explore(
                            model=model_metadata.name,
                            explore=explore_name,
                            base_view=explore_name
                        )
                        logger.info(f"✅ Registered explore '{model_metadata.name}.{explore_name}' in context")
        
        except Exception as e:
            logger.warning(f"Failed to register LookML in context: {e}")
            # Don't fail the whole operation if context registration fails
    
    def _execute_create_query_from_context(self, args: Dict[str, Any], url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """
        Create and run a query using LookML context instead of API validation.
        Perfect for bare repos where explores aren't visible via API.
        """
        try:
            logger.info(f"🔧 [CREATE_QUERY_FROM_CONTEXT] Creating query from context")
            
            model = args.get("model")
            explore = args.get("explore")
            dimensions = args.get("dimensions", [])
            measures = args.get("measures", [])
            limit = args.get("limit", 500)
            
            # Check if we have this explore in context
            explore_key = f"{model}.{explore}"
            if not self.lookml_context.has_explore(model, explore):
                # Provide helpful error with context summary
                summary = self.lookml_context.get_summary()
                return {
                    "success": False,
                    "error": f"Explore {explore_key} not found in context. Available explores: {summary['explores']}. Did you create it in this session?"
                }
            
            # Get available fields
            available_fields = self.lookml_context.get_available_fields(model, explore)
            all_field_names = [f.name for f in available_fields]
            
            # Validate requested fields exist
            for dim in dimensions:
                if dim not in all_field_names:
                    return {
                        "success": False,
                        "error": f"Dimension '{dim}' not found in {explore_key}. Available fields: {all_field_names[:10]}"
                    }
            for meas in measures:
                if meas not in all_field_names:
                    return {
                        "success": False,
                        "error": f"Measure '{meas}' not found in {explore_key}. Available fields: {all_field_names[:10]}"
                    }
            
            # Generate query
            query_body = {
                "model": model,
                "view": explore,
                "fields": dimensions + measures,
                "limit": limit
            }
            
            # Run the query
            sdk = self._init_sdk(url, client_id, client_secret)
            result = sdk.create_query(body=query_body)
            
            logger.info(f"✅ Query created from context: {result.id}")
            
            return {
                "success": True,
                "query_id": result.id,
                "client_id": result.client_id,
                "fields_used": {
                    "dimensions": dimensions,
                    "measures": measures
                },
                "context_summary": self.lookml_context.get_summary()
            }
            
        except Exception as e:
            logger.error(f"Create query from context failed: {e}")
            return {"success": False, "error": str(e)}
