import asyncio
from trello_agent import TrelloAgent
from project_manager import ProjectManager
from scraper_agent import ScraperAgent

class SearchAgent:
    def __init__(self, trello_agent: TrelloAgent, project_manager: ProjectManager, scraper_agent: ScraperAgent):
        self.trello_agent = trello_agent
        self.project_manager = project_manager
        self.scraper_agent = scraper_agent

    async def search(self, query: str):
        """
        Searches for a query across all available tools, local files, and the web.
        """
        trello_results_task = asyncio.create_task(self.trello_agent.search_cards(query))
        local_files_results_task = asyncio.create_task(asyncio.to_thread(self.project_manager.search_files, query))
        # Always perform a web search/scrape as requested for "universal search" capabilities
        web_results_task = asyncio.create_task(self.scraper_agent.search_and_scrape(query))

        # Wait for all tasks
        await asyncio.gather(trello_results_task, local_files_results_task, web_results_task)

        return {
            "trello": trello_results_task.result(),
            "local_files": local_files_results_task.result(),
            "web": web_results_task.result()
        }
