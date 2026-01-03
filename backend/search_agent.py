import asyncio
from .trello_agent import TrelloAgent
from .project_manager import ProjectManager

class SearchAgent:
    def __init__(self, trello_agent: TrelloAgent, project_manager: ProjectManager):
        self.trello_agent = trello_agent
        self.project_manager = project_manager

    async def search(self, query: str):
        """
        Searches for a query across all available tools and local files.
        """
        trello_results_task = asyncio.create_task(self.trello_agent.search_cards(query))
        local_files_results_task = asyncio.create_task(asyncio.to_thread(self.project_manager.search_files, query))

        await trello_results_task
        await local_files_results_task

        return {
            "trello": trello_results_task.result(),
            "local_files": local_files_results_task.result(),
        }
