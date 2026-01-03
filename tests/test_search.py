import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import os
import asyncio

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

from backend.project_manager import ProjectManager
from backend.trello_agent import TrelloAgent
from backend.search_agent import SearchAgent
from backend.tools import tools_list

class TestSearch(unittest.IsolatedAsyncioTestCase):

    def test_project_manager_search_files(self):
        # Create a dummy project structure
        project_dir = 'test_project'
        os.makedirs(project_dir, exist_ok=True)
        with open(os.path.join(project_dir, 'file1.txt'), 'w') as f:
            f.write('hello world')
        with open(os.path.join(project_dir, 'file2.txt'), 'w') as f:
            f.write('another file')

        # Patch the ProjectManager to use the test project
        with patch('backend.project_manager.ProjectManager.get_current_project_path', return_value=project_dir):
            project_manager = ProjectManager('.')
            results = project_manager.search_files('hello')
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]['file'], 'file1.txt')

        # Clean up the dummy project
        import shutil
        shutil.rmtree(project_dir)

    @patch('backend.trello_agent.TrelloAgent._request', new_callable=AsyncMock)
    async def test_trello_agent_search_cards(self, mock_request):
        # Mock the Trello API response for search
        mock_request.return_value = {
            'cards': [
                {'id': '1', 'name': 'Test Card', 'idBoard': '1'},
            ]
        }

        # Mock the Trello API response for get_board
        with patch('backend.trello_agent.TrelloAgent.get_board', new_callable=AsyncMock) as mock_get_board:
            mock_get_board.return_value = {'id': '1', 'name': 'Test Board'}

            trello_agent = TrelloAgent()

            # Run the async search_cards method
            results = await trello_agent.search_cards('test')
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]['name'], 'Test Card')

    def test_search_agent_search(self):
        # Mock the TrelloAgent and ProjectManager
        trello_agent = TrelloAgent()
        project_manager = ProjectManager('.')

        trello_agent.search_cards = AsyncMock(return_value=[{'name': 'Test Card'}])
        project_manager.search_files = MagicMock(return_value=[{'file': 'test.txt'}])

        search_agent = SearchAgent(trello_agent, project_manager)

        # Run the async search method
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(search_agent.search('test'))

        self.assertIn('trello', results)
        self.assertIn('local_files', results)
        self.assertEqual(len(results['trello']), 1)
        self.assertEqual(len(results['local_files']), 1)

    def test_search_tool_in_tools_list(self):
        # Check if the search tool is in the tools list
        search_tool_exists = any(tool.get('name') == 'search' for tool in tools_list[0]['function_declarations'])
        self.assertTrue(search_tool_exists, "The 'search' tool should be in the tools list")

if __name__ == '__main__':
    unittest.main()
