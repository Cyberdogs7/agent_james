import os
import json
import subprocess

class WritingAgent:
    def __init__(self, project_manager, git_agent):
        self.project_manager = project_manager
        self.git_agent = git_agent

    def _parse_args(self, args):
        if not args:
            return []
        try:
            # Handles OpenAI/Gemini tool calling where args is a JSON string of properties
            data = json.loads(args)
            if isinstance(data, dict):
                res = []
                for k, v in data.items():
                    if k == "args": # e.g. {"args": "--from-scratch"}
                        res.extend(str(v).split())
                    elif k.startswith("-"):
                        res.extend([k, str(v)])
                    else:
                        # Fallback for unexpected structured args, prepend with -- if it looks like a param
                        res.extend([f"--{k}", str(v)])
                return res
        except json.JSONDecodeError:
            pass

        # Handle plain string arguments
        return str(args).split()

    def _run_script(self, script_name, args=None):
        cwd = self.project_manager.get_current_project_path()

        # Determine the path to the autonovel directory relative to this file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        autonovel_dir = os.path.join(current_dir, "autonovel")
        script_path = os.path.join(autonovel_dir, script_name)

        # Check if script exists
        if not os.path.exists(script_path):
             return f"Error: Script {script_name} not found in {autonovel_dir}. Ensure 'autonovel' is downloaded."

        # The autonovel scripts expect to run via 'uv run python' or 'python'.
        # Since 'uv run python' manages virtual environments which may not be present,
        # we will attempt to execute them via the current standard 'python' executable.
        # Alternatively, if 'uv' is installed on this host, it could be used. For safety, we use the local python env.
        cmd = ["python", script_path]

        parsed_args = self._parse_args(args)
        if parsed_args:
            cmd.extend(parsed_args)

        env = os.environ.copy()

        # Ensure PYTHONPATH includes the autonovel directory so the scripts can import their modules
        current_pythonpath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{autonovel_dir}:{current_pythonpath}" if current_pythonpath else autonovel_dir

        # Explicitly forward keys that might be globally defined in jules root .env
        # (instead of relying on autonovel scripts to call load_dotenv() from their own directory)
        for key in ["ANTHROPIC_API_KEY", "FAL_KEY", "ELEVENLABS_API_KEY", "GEMINI_API_KEY"]:
            if key in os.environ:
                env[key] = os.environ[key]

        try:
            # Run the process
            result = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
            if result.returncode == 0:
                return f"Successfully executed {script_name}.\n{result.stdout}"
            else:
                return f"Error executing {script_name} (Code {result.returncode}):\n{result.stderr}\n{result.stdout}"
        except Exception as e:
            return f"Failed to execute {script_name}: {str(e)}"

    async def commit_novel_changes(self, args=None):
        """Initializes repo if needed, stages, and commits changes."""
        message = "Novel updates"
        if args:
            try:
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
        return self._run_script("seed.py", args)

    def gen_world(self, args=None):
        return self._run_script("gen_world.py", args)

    def gen_characters(self, args=None):
        return self._run_script("gen_characters.py", args)

    def gen_outline(self, args=None):
        return self._run_script("gen_outline.py", args)

    def gen_outline_part2(self, args=None):
        return self._run_script("gen_outline_part2.py", args)

    def gen_canon(self, args=None):
        return self._run_script("gen_canon.py", args)

    def voice_fingerprint(self, args=None):
        return self._run_script("voice_fingerprint.py", args)

    def draft_chapter(self, args=None):
        return self._run_script("draft_chapter.py", args)

    def run_drafts(self, args=None):
        return self._run_script("run_drafts.py", args)

    def evaluate(self, args=None):
        return self._run_script("evaluate.py", args)

    def adversarial_edit(self, args=None):
        return self._run_script("adversarial_edit.py", args)

    def compare_chapters(self, args=None):
        return self._run_script("compare_chapters.py", args)

    def reader_panel(self, args=None):
        return self._run_script("reader_panel.py", args)

    def review(self, args=None):
        return self._run_script("review.py", args)

    def gen_brief(self, args=None):
        return self._run_script("gen_brief.py", args)

    def gen_revision(self, args=None):
        return self._run_script("gen_revision.py", args)

    def apply_cuts(self, args=None):
        return self._run_script("apply_cuts.py", args)

    def gen_audiobook_script(self, args=None):
        return self._run_script("gen_audiobook_script.py", args)

    def gen_audiobook(self, args=None):
        return self._run_script("gen_audiobook.py", args)

    def run_pipeline(self, args=None):
        return self._run_script("run_pipeline.py", args)

    def build_arc_summary(self, args=None):
        return self._run_script("build_arc_summary.py", args)

    def build_outline(self, args=None):
        return self._run_script("build_outline.py", args)

    def build_tex(self, args=None):
        return self._run_script("typeset/build_tex.py", args)
