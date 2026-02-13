def _execute_register_lookml_manually(self, args: Dict[str, Any], url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """
        Manually register LookML artifacts in context.
        Safe fallback when API calls fail or when working with existing LookML.
        """
        try:
            logger.info(f"🔧 [REGISTER_LOOKML_MANUALLY] Manually registering LookML in context")

            from lookml_context import Field

            artifact_type = args.get("type")  # "view", "model", or "explore"

            if artifact_type == "view":
                view_name = args.get("view_name")
                fields_data = args.get("fields", [])
                sql_table_name = args.get("sql_table_name")

                # Convert field dicts to Field objects
                fields = []
                for f in fields_data:
                    fields.append(Field(
                        name=f.get("name"),
                        type=f.get("type", "dimension"),
                        field_type=f.get("field_type", "string"),
                        label=f.get("label", f.get("name").replace("_", " ").title()),
                        sql=f.get("sql")
                    ))

                self.lookml_context.register_view(
                    view_name=view_name,
                    fields=fields,
                    sql_table_name=sql_table_name
                )

                logger.info(f"✅ Manually registered view '{view_name}' with {len(fields)} fields")

                return {
                    "success": True,
                    "message": f"Registered view '{view_name}' with {len(fields)} fields",
                    "context_summary": self.lookml_context.get_summary()
                }

            elif artifact_type == "model":
                model_name = args.get("model_name")
                connection = args.get("connection", "unknown")
                explores = args.get("explores", [])
                includes = args.get("includes", [])

                self.lookml_context.register_model(
                    model_name=model_name,
                    connection=connection,
                    explores=explores,
                    includes=includes
                )

                logger.info(f"✅ Manually registered model '{model_name}' with {len(explores)} explores")

                return {
                    "success": True,
                    "message": f"Registered model '{model_name}' with {len(explores)} explores",
                    "context_summary": self.lookml_context.get_summary()
                }

            elif artifact_type == "explore":
                model = args.get("model")
                explore = args.get("explore")
                base_view = args.get("base_view")
                joins = args.get("joins", [])

                self.lookml_context.register_explore(
                    model=model,
                    explore=explore,
                    base_view=base_view,
                    joins=joins
                )

                logger.info(f"✅ Manually registered explore '{model}.{explore}'")

                return {
                    "success": True,
                    "message": f"Registered explore '{model}.{explore}'",
                    "context_summary": self.lookml_context.get_summary()
                }

            else:
                return {
                    "success": False,
                    "error": f"Invalid type '{artifact_type}'. Must be 'view', 'model', or 'explore'"
                }

        except Exception as e:
            logger.error(f"Manual LookML registration failed: {e}")
            return {"success": False, "error": str(e)}
