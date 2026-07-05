import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../backend'))

from trello_agent import TrelloAgent

class TestAgentCaching(unittest.IsolatedAsyncioTestCase):

    async def test_trello_agent_caching(self):
        agent = TrelloAgent()
        agent.api_key = "fake"
        agent.token = "fake"

        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"id": "board1", "name": "B1"}]

        with patch('requests.request', return_value=mock_response) as mock_req:
            # First call
            res1 = await agent.list_boards()
            self.assertEqual(len(res1), 1)
            self.assertEqual(mock_req.call_count, 1)

            # Second call - Cache
            res2 = await agent.list_boards()
            self.assertEqual(len(res2), 1)
            self.assertEqual(mock_req.call_count, 1) # Count stays 1

            # Invalidate
            agent.invalidate_cache("list_boards")

            # Third call
            res3 = await agent.list_boards()
            self.assertEqual(len(res3), 1)
            self.assertEqual(mock_req.call_count, 2) # Count increases

if __name__ == '__main__':
    unittest.main()
