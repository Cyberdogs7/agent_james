import asyncio
import traceback
import os
import importlib.util
import sys

class ToolRegistry:
    def __init__(self):
        self._handlers = {}
        self._dynamic_declarations = []

    def register(self, name, handler):
        """Registers a tool handler."""
        self._handlers[name] = handler

    def get_dynamic_tool_declarations(self):
        """Returns the list of dynamically loaded tool declarations."""
        return self._dynamic_declarations

    def load_skills(self, skills_dir="projects/skills"):
        """Dynamically loads skills from the skills directory."""
        if not os.path.exists(skills_dir):
            os.makedirs(skills_dir, exist_ok=True)
            return

        self._dynamic_declarations = []
        for filename in os.listdir(skills_dir):
            if filename.endswith(".py"):
                module_name = filename[:-3]
                file_path = os.path.join(skills_dir, filename)
                try:
                    spec = importlib.util.spec_from_file_location(module_name, file_path)
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)

                    if hasattr(module, 'tool_declaration') and hasattr(module, 'execute'):
                        decl = module.tool_declaration
                        self.register(decl['name'], module.execute)
                        self._dynamic_declarations.append(decl)
                except Exception as e:
                    print(f"Error loading skill {filename}: {e}")
                    traceback.print_exc()

    def add_skill(self, name, description, code, skills_dir="projects/skills"):
        """Saves a new skill to the skills directory and reloads."""
        if not os.path.exists(skills_dir):
            os.makedirs(skills_dir, exist_ok=True)

        file_path = os.path.join(skills_dir, f"{name}.py")
        with open(file_path, "w") as f:
            f.write(code)

        self.load_skills(skills_dir)

    def get_handler(self, name):
        """Returns the handler for a tool."""
        return self._handlers.get(name)

    def is_confirmation_required(self, tool_name):
        """Checks if a tool requires user confirmation."""
        destructive_keywords = ['delete', 'remove', 'wipe', 'destroy', 'dismiss', 'stop_jules', 'merge_pull_request']
        return any(keyword in tool_name.lower() for keyword in destructive_keywords)

    async def dispatch(self, tool_name, args):
        """
        Dispatches the tool call to the registered handler.
        """
        if tool_name not in self._handlers:
            return f"Tool '{tool_name}' not found."

        handler = self._handlers[tool_name]

        try:
            if asyncio.iscoroutinefunction(handler):
                return await handler(**args)
            else:
                return handler(**args)
        except Exception as e:
            traceback.print_exc()
            error_msg = f"Error executing '{tool_name}': {str(e)}\n{traceback.format_exc()}"
            if any(tool_name == decl['name'] for decl in self._dynamic_declarations):
                error_msg += f"\nThis is a dynamically generated skill. Please use create_new_skill to update the code for '{tool_name}' to fix this error."
            return error_msg
