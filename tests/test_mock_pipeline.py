"""
NorthStar Retail - Mock Pipeline Unit Tests
Ensures all mock tools and isolated pipelines run end-to-end without active AWS credentials.
"""

import unittest
from mock.mock_sales_tools import (
    get_mock_top_products,
    get_mock_revenue_by_region,
    get_mock_recent_best_category,
)
from mock.mock_policy_tools import (
    search_mock_policy_documents,
)


class TestMockPipelineAndTools(unittest.TestCase):
    """Test suite ensuring all mock tools and isolated pipelines run end-to-end without active AWS credentials."""

    def test_mock_get_top_products(self):
        result = get_mock_top_products(limit=5)
        self.assertIn("data", result)
        self.assertIn("source", result)
        self.assertLessEqual(len(result["data"]), 5)
        if result["data"]:
            first = result["data"][0]
            self.assertIn("product_id", first)
            self.assertIn("product_name", first)
            self.assertIn("total_revenue", first)
            self.assertGreaterEqual(first["total_revenue"], 0)

    def test_mock_get_revenue_by_region(self):
        result = get_mock_revenue_by_region()
        self.assertIn("data", result)
        self.assertIn("source", result)
        self.assertGreater(len(result["data"]), 0)
        first = result["data"][0]
        self.assertIn("region", first)
        self.assertIn("total_revenue", first)

    def test_mock_get_recent_best_category(self):
        result = get_mock_recent_best_category()
        self.assertIn("data", result)
        self.assertIn("source", result)
        self.assertEqual(len(result["data"]), 1)
        first = result["data"][0]
        self.assertIn("category", first)
        self.assertIn("total_revenue", first)

    def test_mock_search_policy_documents_returns(self):
        result = search_mock_policy_documents("return")
        self.assertIn("results", result)
        self.assertGreater(len(result["results"]), 0)
        found = any("return" in doc["source_name"].lower() or "return" in doc["content"].lower() for doc in result["results"])
        self.assertTrue(found)

    def test_mock_search_policy_documents_warranty(self):
        result = search_mock_policy_documents("warranty")
        self.assertIn("results", result)
        self.assertGreater(len(result["results"]), 0)
        found = any("warranty" in doc["source_name"].lower() or "warranty" in doc["content"].lower() for doc in result["results"])
        self.assertTrue(found)


if __name__ == "__main__":
    unittest.main()
