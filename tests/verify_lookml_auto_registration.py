
import unittest
import sys
import os
import json
from unittest.mock import MagicMock, patch

# Add apps/agent to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../apps/agent")))

try:
    from lookml_context import LookMLParser, LookMLContext
    from mcp_agent import MCPAgent
except ImportError:
    # Handle case where imports might fail in this environment if paths aren't perfect
    print("⚠️  Import failed, trying alternative path or mocking...")
    sys.path.append(os.path.abspath("apps/agent"))
    from lookml_context import LookMLParser, LookMLContext

class TestLookMLAutoRegistration(unittest.TestCase):
    
    def test_parser_view(self):
        lookml = """
        view: users {
            sql_table_name: `project.dataset.users`;;
            
            dimension: id {
                type: number
                sql: ${TABLE}.id ;;
            }
            
            measure: count {
                type: count
            }
        }
        """
        meta = LookMLParser.parse_view(lookml)
        self.assertIsNotNone(meta)
        self.assertEqual(meta.name, "users")
        self.assertEqual(len(meta.fields), 2)
        self.assertEqual(meta.fields[0].name, "id")
        self.assertEqual(meta.fields[1].name, "count")
        print("✅ View Parsing Passed")

    def test_parser_model(self):
        lookml = """
        connection: "my_db"
        include: "/views/*.view.lkml"
        
        explore: orders {}
        """
        meta = LookMLParser.parse_model(lookml, "my_model")
        self.assertIsNotNone(meta)
        self.assertEqual(meta.name, "my_model")
        self.assertEqual(meta.connection, "my_db")
        self.assertIn("orders", meta.explores)
        print("✅ Model Parsing Passed")

    def test_auto_registration_in_context(self):
        context = LookMLContext()
        lookml = """
        view: products {
            dimension: id { type: number }
        }
        """
        meta = LookMLParser.parse_view(lookml)
        context.register_view(meta.name, meta.fields, meta.sql_table_name)
        
        self.assertIn("products", context.views)
        self.assertEqual(context.views["products"].fields[0].name, "id")
        print("✅ Context Registration Passed")

if __name__ == '__main__':
    unittest.main()
