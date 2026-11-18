"""
NorthStar Retail - AWS Tools & Agent Comprehensive Test Suite
Validates that sales tools, hybrid policy tools, and Bedrock agent
operate reliably with grounded citations and schema consistency.
"""

import unittest
from agent.tools.sales_tools import (
    get_top_products,
    get_revenue_by_region,
    get_recent_best_category,
)
from agent.tools.policy_tools import (
    search_policy_documents,
)
from agent.agent import BedrockRetailAgent, root_agent


class TestAWSPipelineAndAgent(unittest.TestCase):
    """Test suite validating production AWS tools and Bedrock agent loop."""

    def test_production_get_top_products(self):
        result = get_top_products(limit=5)
        self.assertIn("data", result)
        self.assertEqual(result["source"], "Amazon Athena Gold")
        self.assertLessEqual(len(result["data"]), 5)
        self.assertGreater(len(result["data"]), 0)
        top = result["data"][0]
        self.assertIn("product_id", top)
        self.assertIn("product_name", top)
        self.assertIn("total_revenue", top)
        self.assertGreater(top["total_revenue"], 0)

    def test_production_get_revenue_by_region(self):
        result = get_revenue_by_region()
        self.assertIn("data", result)
        self.assertEqual(result["source"], "Amazon Athena Gold")
        self.assertGreater(len(result["data"]), 0)
        item = result["data"][0]
        self.assertIn("region", item)
        self.assertIn("total_revenue", item)

    def test_production_get_recent_best_category(self):
        result = get_recent_best_category()
        self.assertIn("data", result)
        self.assertEqual(result["source"], "Amazon Athena Gold")
        self.assertEqual(len(result["data"]), 1)
        item = result["data"][0]
        self.assertIn("category", item)
        self.assertIn("total_revenue", item)
        self.assertEqual(item["category"], "Apparel")

    def test_production_policy_search_returns(self):
        result = search_policy_documents("return policy")
        self.assertIn("results", result)
        self.assertGreater(len(result["results"]), 0)
        first_doc = result["results"][0]
        self.assertIn("source_name", first_doc)
        self.assertIn("s3_uri", first_doc)
        self.assertTrue(first_doc["s3_uri"].startswith("s3://"))
        self.assertIn("content", first_doc)

    def test_production_policy_search_warranty(self):
        result = search_policy_documents("appliance warranty")
        self.assertIn("results", result)
        self.assertGreater(len(result["results"]), 0)
        found = any("warranty" in d["source_name"].lower() or "warranty" in d["content"].lower() for d in result["results"])
        self.assertTrue(found)

    def test_bedrock_agent_top_products_query(self):
        agent = BedrockRetailAgent()
        answer = agent.ask("What are the top 5 highest selling products by revenue?")
        self.assertIn("Source:\nAmazon Athena Gold", answer)
        self.assertIn("Running Shoes", answer)

    def test_bedrock_agent_policy_returns_query(self):
        agent = BedrockRetailAgent()
        answer = agent.ask("What is the return policy for purchases?")
        self.assertIn("Source:\nreturns.pdf", answer)
        self.assertIn("30 days", answer)

    def test_bedrock_agent_recent_category_query(self):
        agent = BedrockRetailAgent()
        answer = agent.ask("Which category generated the highest revenue in the 7 days prior to latest order?")
        self.assertIn("Source:\nAmazon Athena Gold", answer)
        self.assertIn("Apparel", answer)


if __name__ == "__main__":
    unittest.main()
