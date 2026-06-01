import asyncio
import os
import sys
import json
from openai import AsyncOpenAI

# Ensure the backend module can be found
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.ada import AudioLoop
from backend.tools import tools_list
from backend.project_manager import ProjectManager

def convert_gemini_to_openai(gemini_tools):
    openai_tools = []
    
    def lower_types(schema):
        if not isinstance(schema, dict):
            return schema
        new_schema = {}
        for k, v in schema.items():
            if k == "type" and isinstance(v, str):
                new_schema[k] = v.lower()
            elif isinstance(v, dict):
                new_schema[k] = lower_types(v)
            elif isinstance(v, list):
                new_schema[k] = [lower_types(i) for i in v]
            else:
                new_schema[k] = v
        return new_schema

    for group in gemini_tools:
        decls = group.get("function_declarations", []) if isinstance(group, dict) else group
        if not isinstance(decls, list): decls = [decls]
        for decl in decls:
            decl.pop("behavior", None)
            params = decl.get("parameters", {})
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": decl["name"],
                    "description": decl.get("description", ""),
                    "parameters": lower_types(params)
                }
            })
    return openai_tools

async def run_harness():
    print("Initializing A.D.A Test Harness (OpenAI/OpenRouter/Local Mode)...")
    print("This may take a moment as agents start up...")
    
    project_root = os.path.dirname(os.path.abspath(__file__))
    pm = ProjectManager(project_root)
    ada = AudioLoop(project_manager=pm)
    
    await asyncio.sleep(2)
    
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key:
        base_url = "https://openrouter.ai/api/v1"
        api_key = openrouter_key
        model = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")
    else:
        base_url = os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
        if base_url and not base_url.endswith("/v1"):
            base_url = base_url.rstrip("/") + "/v1"
        api_key = "lm-studio"
        model = os.getenv("LM_STUDIO_MODEL", "local-model")
    
    print(f"\nUsing LLM API:")
    print(f"Base URL: {base_url}")
    print(f"Model: {model}")
    print(f"To change this, set OPENROUTER_API_KEY and OPENROUTER_MODEL, or LM_STUDIO_BASE_URL and LM_STUDIO_MODEL in your .env file.")
    
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    openai_tools = convert_gemini_to_openai(tools_list)
    
    messages = [
        {"role": "system", "content": "You are A.D.A, an advanced AI agent with numerous tools. You are currently running in a generic CLI test harness. Use your tools to fulfill the user's requests."}
    ]
    
    print("\n================================================")
    print("   A.D.A Generic Test Harness Initialized")
    print("================================================")
    print("Type your commands. Type 'quit', 'exit', or 'q' to stop.")
    
    while True:
        try:
            user_input = await asyncio.to_thread(input, "\nUser: ")
            
            if user_input.strip().lower() in ['quit', 'exit', 'q']:
                break
                
            if not user_input.strip():
                continue
                
            messages.append({"role": "user", "content": user_input})
            
            while True:
                response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=openai_tools,
                    temperature=0.2
                )
                
                message = response.choices[0].message
                messages.append(message)
                
                if message.tool_calls:
                    for call in message.tool_calls:
                        print(f"\n[Tool Call] {call.function.name}")
                        print(f"[Tool Args] {call.function.arguments}")
                        
                        try:
                            args = json.loads(call.function.arguments)
                            result = await ada.tool_registry.dispatch(call.function.name, args)
                        except Exception as e:
                            result = f"Error executing tool: {e}"
                            
                        try:
                            result_str = str(result)
                            print(f"[Tool Result] {result_str[:500]}{'...' if len(result_str) > 500 else ''}")
                        except UnicodeEncodeError:
                            print(f"[Tool Result] [Output contains special characters, cannot print to Windows CLI]")
                            
                        messages.append({
                            "role": "tool",
                            "tool_call_id": call.id,
                            "name": call.function.name,
                            "content": str(result)
                        })
                        
                    await asyncio.sleep(2) 
                else:
                    print(f"\nA.D.A: {message.content}")
                    break
                    
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\nError in chat loop: {e}")
            break
            
    print("\nShutting down harness...")
    ada.stop()

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(run_harness())
