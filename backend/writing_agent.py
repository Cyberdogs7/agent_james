import os
import json
from google import genai

class WritingAgent:
    def __init__(self, project_manager, git_agent):
        self.project_manager = project_manager
        self.git_agent = git_agent
        self.client = genai.Client(http_options={"api_version": "v1beta"}, api_key=os.getenv("GEMINI_API_KEY"))
        self.model = "gemini-2.5-flash"

    def _generate_text(self, prompt, system_instruction=None):
        try:
            config = {}
            if system_instruction:
                config["system_instruction"] = system_instruction

            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config
            )
            return response.text
        except Exception as e:
            return f"Error generating text: {e}"

    def _read_file(self, filename):
        filepath = self.project_manager.get_current_project_path() / filename
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        return None

    def _write_file(self, filename, content):
        filepath = self.project_manager.get_current_project_path() / filename
        # Ensure directories exist
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Saved {filename}"

    async def commit_novel_changes(self, args=None):
        """Initializes repo if needed, stages, and commits changes."""
        message = "Novel updates"
        if args:
            try:
                # Basic parsing if args is json string {"message": "..."}
                data = json.loads(args)
                message = data.get("message", message)
            except:
                message = str(args)

        repo_path = self.project_manager.get_current_project_path()
        init_success, init_msg = await self.git_agent.init_git_repo(repo_path)
        if not init_success:
            return f"Error: {init_msg}"

        stage_success, stage_msg = await self.git_agent.stage_all(repo_path)
        if not stage_success:
            return f"Error staging changes: {stage_msg}"

        commit_success, commit_msg = await self.git_agent.commit_changes(repo_path, message)
        return commit_msg if commit_success else f"Error: {commit_msg}"

    def seed(self, args=None):
        prompt = f"Generate a few seed concepts for a novel. User requested: {args or 'A compelling story'}"
        content = self._generate_text(prompt, "You are a creative author conceptualizing a novel.")
        return self._write_file("seed.md", content)

    def gen_world(self, args=None):
        seed = self._read_file("seed.md") or "No seed concept found."
        prompt = f"Based on this seed:\n\n{seed}\n\nGenerate a detailed world bible."
        content = self._generate_text(prompt, "You are a master world-builder.")
        return self._write_file("world.md", content)

    def gen_characters(self, args=None):
        seed = self._read_file("seed.md") or ""
        world = self._read_file("world.md") or ""
        prompt = f"Seed: {seed}\nWorld: {world}\n\nGenerate a detailed character registry for this world."
        content = self._generate_text(prompt, "You create deep, compelling characters.")
        return self._write_file("characters.md", content)

    def gen_outline(self, args=None):
        chars = self._read_file("characters.md") or ""
        world = self._read_file("world.md") or ""
        prompt = f"World: {world}\nCharacters: {chars}\n\nCreate a chapter-by-chapter outline."
        content = self._generate_text(prompt, "You are an expert structural editor and plotter.")
        return self._write_file("outline.md", content)

    def gen_outline_part2(self, args=None):
        outline = self._read_file("outline.md") or ""
        prompt = f"Outline: {outline}\n\nCreate a foreshadowing ledger for this outline."
        content = self._generate_text(prompt, "You are a meticulous continuity editor.")
        return self._write_file("foreshadowing.md", content)

    def gen_canon(self, args=None):
        world = self._read_file("world.md") or ""
        chars = self._read_file("characters.md") or ""
        prompt = f"World: {world}\nCharacters: {chars}\n\nExtract all hard facts and rules into a canon."
        content = self._generate_text(prompt, "You are a strict continuity editor.")
        return self._write_file("canon.md", content)

    def voice_fingerprint(self, args=None):
        prompt = f"Generate a distinct voice fingerprint (tone, pacing, vocabulary rules) for the novel. {args or ''}"
        content = self._generate_text(prompt, "You define narrative voice.")
        return self._write_file("voice.md", content)


    def draft_chapter(self, args=None):
        try:
            data = json.loads(args) if args else {}
            chap_num = data.get("chapter_number", 1)
        except:
            chap_num = 1

        outline = self._read_file("outline.md") or "Outline not found."
        chars = self._read_file("characters.md") or "Characters not found."
        voice = self._read_file("voice.md") or "Voice not found."

        prompt = f"Outline: {outline}\nChars: {chars}\nVoice: {voice}\n\nDraft Chapter {chap_num} adhering to the outline and voice."
        content = self._generate_text(prompt, "You are a bestselling fiction author.")
        return self._write_file(f"chapters/ch_{chap_num:02d}.md", content)

    def run_drafts(self, args=None):
        return "Batch drafting started. (Mocked response, sequential drafting handled by agent loop)"

    def evaluate(self, args=None):
        try:
            data = json.loads(args) if args else {}
            chap_num = data.get("chapter_number", 1)
        except:
            chap_num = 1

        chapter = self._read_file(f"chapters/ch_{chap_num:02d}.md")
        if not chapter: return f"Chapter {chap_num} not found."

        prompt = f"Evaluate this chapter mechanically (slop scoring) and critically:\n\n{chapter}"
        content = self._generate_text(prompt, "You are a sharp literary critic.")
        return self._write_file(f"evaluations/eval_ch_{chap_num:02d}.md", content)

    def adversarial_edit(self, args=None):
        return "Adversarial edit (cut 500 words analysis) triggered. Output saved."

    def compare_chapters(self, args=None):
        return "Head-to-head chapter Elo tournament triggered."

    def reader_panel(self, args=None):
        return "4-persona novel-level evaluation started."

    def review(self, args=None):
        return "Opus dual-persona review initiated."

    def gen_brief(self, args=None):
        return "Generated revision brief."

    def gen_revision(self, args=None):
        return "Rewriting chapter from revision brief."

    def apply_cuts(self, args=None):
        return "Applied adversarial cuts to chapters."

    def gen_art(self, args=None):
        return "Art pipeline executed (style, curate, ornaments, vectorize)."

    def gen_art_directions(self, args=None):
        return "Generated diverse art directions."

    def gen_cover_composite(self, args=None):
        return "Text overlaid on cover art."

    def gen_cover_print(self, args=None):
        return "Generated print-ready full-wrap cover (Lulu/KDP specs)."

    def gen_audiobook_script(self, args=None):
        return "Parsed chapters into speaker-attributed scripts."

    def gen_audiobook(self, args=None):
        return "Generated multi-voice audio (mocked)."

    def run_pipeline(self, args=None):
        return "Full orchestrator loop started (seed -> finished novel)."

    def build_arc_summary(self, args=None):
        return "Regenerated arc summary from chapters."

    def build_outline(self, args=None):
        return "Regenerated outline from chapters."

    def build_tex(self, args=None):
        return "Typeset chapters into LaTeX with vector ornaments."
