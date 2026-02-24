import sys
import os
import unittest
import shutil

# Add the apps/agent directory to the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../apps/agent')))

from lookml_context import LookMLContext

class TestContextIsolation(unittest.TestCase):
    def setUp(self):
        # clean up any existing context files
        self.session_1 = "session_test_1"
        self.session_2 = "session_test_2"
        self._clean_session(self.session_1)
        self._clean_session(self.session_2)

    def tearDown(self):
        self._clean_session(self.session_1)
        self._clean_session(self.session_2)

    def _clean_session(self, session_id):
        filename = f".lookml_context_{session_id}.json"
        if os.path.exists(filename):
            os.remove(filename)

    def test_isolation_and_persistence(self):
        # 1. Initialize Context 1
        ctx1 = LookMLContext(session_id=self.session_1)
        ctx1.register_explore(
            model="model_1",
            explore="explore_1",
            base_view="view_1",
            joins=[]
        )
        print(f"[Session 1] Registered explore_1 in model_1")

        # 2. Initialize Context 2 (Should be empty)
        ctx2 = LookMLContext(session_id=self.session_2)
        explores_2 = ctx2.explores
        print(f"[Session 2] Explores: {explores_2}")
        
        self.assertNotIn("model_1.explore_1", explores_2, "Session 2 should not have model_1.explore_1")

        # 3. Modify Session 2
        ctx2.register_explore(
            model="model_2",
            explore="explore_2",
            base_view="view_2",
            joins=[]
        )
        print(f"[Session 2] Registered explore_2 in model_2")

        # 4. Reload Session 1 (Should still have explore_1, but NOT explore_2)
        ctx1_b = LookMLContext(session_id=self.session_1)
        ctx1_b.load_from_file()
        explores_1_b = ctx1_b.explores
        print(f"[Session 1 Reloaded] Explores: {explores_1_b}")

        self.assertIn("model_1.explore_1", explores_1_b, "Session 1 should persist model_1.explore_1")
        self.assertNotIn("model_2.explore_2", explores_1_b, "Session 1 should NOT have model_2.explore_2")

        # 5. Reload Session 2 (Should have explore_2)
        ctx2_b = LookMLContext(session_id=self.session_2)
        ctx2_b.load_from_file()
        explores_2_b = ctx2_b.explores
        print(f"[Session 2 Reloaded] Explores: {explores_2_b}")
        
        self.assertIn("model_2.explore_2", explores_2_b, "Session 2 should persist model_2.explore_2")
        self.assertNotIn("model_1.explore_1", explores_2_b, "Session 2 should NOT have model_1.explore_1")

if __name__ == '__main__':
    unittest.main()
