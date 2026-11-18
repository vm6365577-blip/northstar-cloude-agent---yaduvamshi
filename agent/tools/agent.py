"""
NorthStar Retail - Agent Tools Bridge
Re-exports the root Amazon Bedrock Agent.
"""

from agent.agent import root_agent, BedrockRetailAgent, main

__all__ = ["root_agent", "BedrockRetailAgent", "main"]

if __name__ == "__main__":
    main()
