
import unittest
from duckduckgo_search import DDGS
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestSearchBackends(unittest.TestCase):
    def test_backend_api(self):
        """Test default API backend"""
        try:
            print("\nTesting 'api' backend...")
            with DDGS() as ddgs:
                results = list(ddgs.text("python programming", backend="api", max_results=3))
            print(f"✅ API Backend success: {len(results)} results")
            for r in results:
                print(f"  - {r.get('title')}")
        except Exception as e:
            print(f"❌ API Backend failed: {e}")

    def test_backend_html(self):
        """Test HTML backend"""
        try:
            print("\nTesting 'html' backend...")
            with DDGS() as ddgs:
                results = list(ddgs.text("python programming", backend="html", max_results=3))
            print(f"✅ HTML Backend success: {len(results)} results")
            for r in results:
                print(f"  - {r.get('title')}")
        except Exception as e:
            print(f"❌ HTML Backend failed: {e}")

    def test_backend_lite(self):
        """Test Lite backend"""
        try:
            print("\nTesting 'lite' backend...")
            with DDGS() as ddgs:
                results = list(ddgs.text("python programming", backend="lite", max_results=3))
            print(f"✅ Lite Backend success: {len(results)} results")
            for r in results:
                print(f"  - {r.get('title')}")
        except Exception as e:
            print(f"❌ Lite Backend failed: {e}")

if __name__ == "__main__":
    unittest.main()
