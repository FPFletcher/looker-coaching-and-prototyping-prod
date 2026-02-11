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
