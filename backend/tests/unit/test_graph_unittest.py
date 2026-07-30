"""Built-in Unittest Runner for LangGraph Workflow Execution."""

import asyncio
import unittest
from langchain_core.messages import HumanMessage
from backend.graph.workflow import graph
from backend.graph.state import AgentState


class TestLangGraphWorkflow(unittest.TestCase):
    """
    Standard unittest test case for LangGraph state machine.
    """

    def test_langgraph_workflow_execution(self):
        """
        Executes async graph state transition test using standard asyncio loop.
        """
        async def run_test():
            initial_state: AgentState = {
                "messages": [HumanMessage(content="Hello AI Harness")],
                "user_id": "test_user_001",
                "session_id": "session_abc123",
                "current_step": "init",
                "metadata": {}
            }
            config = {"configurable": {"thread_id": "thread_test_unittest_1"}}
            result = await graph.ainvoke(initial_state, config=config)
            return result

        result = asyncio.run(run_test())
        self.assertIsNotNone(result)
        self.assertEqual(len(result["messages"]), 2)
        self.assertIn("Processed request - Hello AI Harness", result["messages"][-1].content)
        self.assertEqual(result["current_step"], "completed")


if __name__ == "__main__":
    unittest.main()
