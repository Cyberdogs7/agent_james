import asyncio
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field

from backend.scraper_agent import ScraperAgent
from backend.browser_agent import ProgrammaticBrowserAgent
from backend.local_web_agent import LocalWebAgent
from backend.tool_registry import ToolRegistry
from backend.llm_client import get_llm_client, MODEL_CONFIGS


@dataclass
class ResearchPlan:
    topic: str
    questions: List[str]
    sources: List[str] = field(default_factory=list)
    findings: Dict[str, Any] = field(default_factory=dict)
    gaps: List[str] = field(default_factory=list)
    iteration: int = 0
    max_iterations: int = 5


@dataclass
class ResearchResult:
    topic: str
    executive_summary: str
    detailed_findings: Dict[str, Any]
    sources: List[Dict[str, Any]]
    gaps: List[str]
    confidence: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class ResearchAgent:
    def __init__(self, tool_registry: ToolRegistry = None, browser_agent: ProgrammaticBrowserAgent = None):
        self.scraper = ScraperAgent()
        self.browser_agent = browser_agent or ProgrammaticBrowserAgent()
        self.local_web_agent = LocalWebAgent(self.browser_agent, tool_registry) if tool_registry else None
        self.llm_client = get_llm_client(prefer_openrouter=True)
        self.include_raw = os.environ.get("INCLUDE_RAW_LOGS", "False") == "True"

    def _log(self, *args, **kwargs):
        if self.include_raw:
            print(*args, **kwargs)

    async def research(self, topic: str, depth: str = "standard", update_callback=None) -> ResearchResult:
        """
        Main entry point for deep research.
        depth: "quick" (2 iterations), "standard" (5 iterations), "deep" (10 iterations)
        """
        max_iterations = {"quick": 2, "standard": 5, "deep": 10}.get(depth, 5)

        plan = ResearchPlan(topic=topic, max_iterations=max_iterations)

        # Phase 1: Initial Planning
        await self._create_initial_plan(plan, update_callback)

        # Phase 2: Iterative Research Loop
        for iteration in range(max_iterations):
            plan.iteration = iteration + 1
            self._log(f"\n=== Research Iteration {plan.iteration}/{max_iterations} ===")

            if update_callback:
                await update_callback(f"Research Iteration {plan.iteration}/{max_iterations}: Gathering data...")

            # Gather data for current questions
            await self._execute_research_plan(plan, update_callback)

            # Analyze findings and identify gaps
            await self._analyze_and_identify_gaps(plan, update_callback)

            # If no gaps or max iterations reached, break
            if not plan.gaps or plan.iteration >= max_iterations:
                break

            # Refine plan for next iteration
            await self._refine_plan(plan, update_callback)

        # Phase 3: Consolidate Report
        if update_callback:
            await update_callback("Consolidating final report...")

        result = await self._consolidate_report(plan)
        return result

    async def _create_initial_plan(self, plan: ResearchPlan, update_callback):
        """Create initial research plan with key questions to answer."""
        if update_callback:
            await update_callback("Creating research plan...")

        plan_prompt = f"""
        You are a senior research analyst. Create a comprehensive research plan for the topic: "{plan.topic}"
        
        Output a JSON object with:
        - "questions": Array of 5-8 specific, answerable research questions that cover different angles of the topic
        - "initial_sources": Array of suggested source types or specific sites to search (e.g., "academic papers", "industry blogs", "official documentation", "news sites")
        - "success_criteria": What would constitute a complete answer
        
        Focus on actionable, specific questions that can be answered through web research.
        """

        try:
            plan_data = await self.llm_client.structured_completion(
                messages=[{"role": "user", "content": plan_prompt}],
                temperature=MODEL_CONFIGS["research_planner"]["temperature"]
            )
            plan.questions = plan_data.get("questions", [])
            plan.sources = plan_data.get("initial_sources", [])
            self._log(f"[ResearchAgent] Initial plan created with {len(plan.questions)} questions")
        except Exception as e:
            self._log(f"[ResearchAgent] Failed to parse plan: {e}")
            # Fallback plan
            plan.questions = [
                f"What is {plan.topic}?",
                f"What are the key components of {plan.topic}?",
                f"What are the current trends in {plan.topic}?",
                f"What are the challenges/limitations of {plan.topic}?",
                f"What are the best practices for {plan.topic}?"
            ]

    async def _execute_research_plan(self, plan: ResearchPlan, update_callback):
        """Execute searches for each unanswered question."""
        unanswered = [q for q in plan.questions if q not in plan.findings]

        for question in unanswered:
            if update_callback:
                await update_callback(f"Researching: {question[:80]}...")

            # Search and scrape
            search_results = await self.scraper.search_and_scrape(question)

            # Also try browser agent for complex queries
            browser_findings = await self._deep_browse(question)

            # Synthesize findings for this question
            findings = await self._synthesize_findings(question, search_results, browser_findings)
            plan.findings[question] = findings

            # Track sources
            for result in search_results:
                if result.get("url") and result["url"] not in plan.sources:
                    plan.sources.append(result["url"])

    async def _deep_browse(self, question: str) -> str:
        """Use the local web agent for deeper browsing on complex questions."""
        if not self.local_web_agent:
            return ""

        try:
            result = await self.local_web_agent.deep_research(question)
            return result
        except Exception as e:
            self._log(f"[ResearchAgent] Deep browse failed: {e}")
            return ""

    async def _synthesize_findings(self, question: str, search_results: List[Dict], browser_findings: str) -> Dict:
        """Synthesize findings from multiple sources for a single question."""
        # Prepare context from search results
        context = ""
        for i, result in enumerate(search_results[:5]):
            context += f"\n--- Source {i+1}: {result.get('url', 'unknown')} ---\n"
            context += f"Title: {result.get('title', '')}\n"
            context += f"Description: {result.get('description', '')}\n"
            if result.get('json_ld'):
                context += f"Structured Data: {json.dumps(result['json_ld'][:2])}\n"

        if browser_findings:
            context += f"\n--- Deep Browse Findings ---\n{browser_findings[:3000]}"

        synthesis_prompt = f"""
        Question: {question}
        
        Research Context:
        {context}
        
        Provide a comprehensive answer to the question based on the available sources.
        Output JSON with:
        - "answer": The synthesized answer (2-3 paragraphs)
        - "key_points": Array of 3-5 bullet points
        - "citations": Array of source URLs used
        - "confidence": 0.0-1.0 confidence score
        - "missing_info": What information is still needed (if any)
        """

        try:
            result = await self.llm_client.structured_completion(
                messages=[{"role": "user", "content": synthesis_prompt}],
                temperature=MODEL_CONFIGS["research_synthesizer"]["temperature"]
            )
            return result
        except Exception as e:
            self._log(f"[ResearchAgent] Synthesis failed: {e}")
            return {
                "answer": "Failed to synthesize findings",
                "key_points": [],
                "citations": [],
                "confidence": 0.0,
                "missing_info": "Synthesis error"
            }

    async def _analyze_and_identify_gaps(self, plan: ResearchPlan, update_callback):
        """Analyze all findings and identify knowledge gaps."""
        if update_callback:
            await update_callback("Analyzing findings and identifying gaps...")

        findings_summary = ""
        for q, f in plan.findings.items():
            findings_summary += f"\nQ: {q}\nA: {f.get('answer', '')[:500]}\nConfidence: {f.get('confidence', 0)}\nMissing: {f.get('missing_info', 'None')}\n"

        analysis_prompt = f"""
        Research Topic: {plan.topic}
        Current Iteration: {plan.iteration}
        
        Current Findings:
        {findings_summary}
        
        Identify gaps in the research. What questions remain unanswered? What areas need deeper investigation?
        Output JSON with:
        - "gaps": Array of specific research gaps (questions that need answers)
        - "suggested_searches": Array of specific search queries to fill gaps
        - "is_complete": Boolean - is the research sufficiently complete?
        """

        try:
            analysis = await self.llm_client.structured_completion(
                messages=[{"role": "user", "content": analysis_prompt}],
                temperature=MODEL_CONFIGS["research_gap_analyzer"]["temperature"]
            )
            plan.gaps = analysis.get("gaps", [])
            # Add suggested searches as new questions
            for search in analysis.get("suggested_searches", []):
                if search not in plan.questions:
                    plan.questions.append(search)

            self._log(f"[ResearchAgent] Identified {len(plan.gaps)} gaps")
        except Exception as e:
            self._log(f"[ResearchAgent] Gap analysis failed: {e}")
            plan.gaps = []

    async def _refine_plan(self, plan: ResearchPlan, update_callback):
        """Refine the research plan based on gaps."""
        if update_callback:
            await update_callback(f"Refining plan for iteration {plan.iteration + 1}...")

        # Prioritize gaps and add as new questions
        for gap in plan.gaps[:3]:  # Limit to top 3 gaps per iteration
            if gap not in plan.questions:
                plan.questions.append(gap)

        plan.gaps = []  # Clear gaps for next iteration

    async def _consolidate_report(self, plan: ResearchPlan) -> ResearchResult:
        """Consolidate all findings into a final report."""

        all_findings = ""
        all_sources = []

        for question, finding in plan.findings.items():
            all_findings += f"\n## {question}\n{finding.get('answer', '')}\n"
            all_sources.extend(finding.get('citations', []))

        # Deduplicate sources
        unique_sources = list(dict.fromkeys(all_sources))

        report_prompt = f"""
        Create a comprehensive research report for: "{plan.topic}"
        
        Research conducted over {plan.iteration} iterations.
        
        All Findings:
        {all_findings}
        
        Sources: {unique_sources}
        
        Output JSON with:
        - "executive_summary": 2-3 paragraph high-level summary
        - "detailed_findings": Object mapping each question to its full answer
        - "sources": Array of {{"url": "", "title": "", "type": ""}} objects
        - "gaps": Remaining unanswered questions
        - "confidence": Overall confidence 0.0-1.0
        """

        try:
            report_data = await self.llm_client.structured_completion(
                messages=[{"role": "user", "content": report_prompt}],
                temperature=MODEL_CONFIGS["research_report_writer"]["temperature"]
            )
        except Exception as e:
            self._log(f"[ResearchAgent] Report consolidation failed: {e}")
            report_data = {
                "executive_summary": f"Research completed on {plan.topic} over {plan.iteration} iterations.",
                "detailed_findings": plan.findings,
                "sources": [{"url": s, "title": "", "type": "web"} for s in unique_sources],
                "gaps": plan.gaps,
                "confidence": 0.7
            }

        return ResearchResult(
            topic=plan.topic,
            executive_summary=report_data.get("executive_summary", ""),
            detailed_findings=report_data.get("detailed_findings", plan.findings),
            sources=report_data.get("sources", []),
            gaps=report_data.get("gaps", plan.gaps),
            confidence=report_data.get("confidence", 0.7)
        )

    async def run_research_task(self, prompt: str, update_callback=None) -> str:
        """Entry point compatible with tool registry."""
        # Extract topic and depth from prompt
        depth = "standard"
        if "deep" in prompt.lower():
            depth = "deep"
        elif "quick" in prompt.lower():
            depth = "quick"

        # Extract topic (remove depth keywords)
        topic = prompt.replace("deep research on", "").replace("deep research", "").replace("research", "").strip()
        if not topic:
            topic = prompt

        result = await self.research(topic, depth, update_callback)

        # Format output
        output = f"# Deep Research Report: {result.topic}\n\n"
        output += f"**Confidence:** {result.confidence:.0%}\n"
        output += f"**Provider:** {self.llm_client.provider}\n\n"
        output += f"## Executive Summary\n{result.executive_summary}\n\n"
        output += "## Detailed Findings\n"

        for question, finding in result.detailed_findings.items():
            output += f"\n### {question}\n"
            if isinstance(finding, dict):
                output += f"{finding.get('answer', '')}\n"
                if finding.get('key_points'):
                    output += "\n**Key Points:**\n"
                    for point in finding['key_points']:
                        output += f"- {point}\n"
            else:
                output += f"{finding}\n"

        if result.sources:
            output += "\n## Sources\n"
            for src in result.sources:
                if isinstance(src, dict):
                    output += f"- [{src.get('title', src.get('url', ''))}]({src.get('url', '')})\n"
                else:
                    output += f"- {src}\n"

        if result.gaps:
            output += "\n## Remaining Gaps\n"
            for gap in result.gaps:
                output += f"- {gap}\n"

        return output


# Tool declaration for registry
research_agent_tool = {
    "name": "run_research_agent",
    "description": "Launches a deep research agent that iteratively searches the web, analyzes findings, identifies gaps, and produces a comprehensive report. Use for complex topics requiring multi-source investigation.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "prompt": {
                "type": "STRING",
                "description": "The research topic or question. Add 'deep' for thorough research (10 iterations), 'quick' for fast research (2 iterations)."
            }
        },
        "required": ["prompt"]
    },
    "behavior": "NON_BLOCKING"
}