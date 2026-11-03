import asyncio
import os
import sys
import json

# Ensure the backend module can be found
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.agent_james import AgentJames
from backend.llm_client import get_llm_client
from backend.tools import tools_list
from backend.project_manager import ProjectManager

def convert_gemini_to_openai(gemini_tools, _alias=True):
    # Backward compat alias — use backend.local_web_agent.convert_tools_to_openai
    from backend.local_web_agent import convert_tools_to_openai
    flat = []
    for group in gemini_tools:
        decls = group.get("function_declarations", []) if isinstance(group, dict) else group
        if not isinstance(decls, list):
            decls = [decls]
        flat.extend(decls)
    return convert_tools_to_openai(flat)

async def run_harness():
    print("Initializing Agent James Test Harness (OpenAI/OpenRouter/Local Mode)...")
    print("This may take a moment as agents start up...")
    
    project_root = os.path.dirname(os.path.abspath(__file__))
    pm = ProjectManager(project_root)
    james = AgentJames(project_manager=pm)
    
    await asyncio.sleep(2)
    
    # Raw httpx LLM (OpenRouter → LM Studio → Ollama /v1); no SDK.
    llm = get_llm_client(prefer_openrouter=True)

    print(f"\nUsing LLM API (raw httpx):")
    print(f"Provider: {llm.provider}")
    print(f"Model: {llm.model}")
    print(f"To change this, set OPENROUTER_API_KEY and OPENROUTER_MODEL, or LM_STUDIO_BASE_URL and LM_STUDIO_MODEL in your .env file.")

    openai_tools = convert_gemini_to_openai(tools_list)
    
    messages = [
        {"role": "system", "content": "You are Agent James, an advanced AI agent with numerous tools. You are currently running in a generic CLI test harness. Use your tools to fulfill the user's requests."}
    ]
    
    print("\n================================================")
    print("   Agent James Generic Test Harness Initialized")
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
                response = await llm.chat_completion(
                    messages=messages,
                    tools=openai_tools,
                    temperature=0.2
                )

                message = response.choices[0].message
                messages.append(message.to_dict() if hasattr(message, "to_dict") else message)
                
                if message.tool_calls:
                    for call in message.tool_calls:
                        print(f"\n[Tool Call] {call.function.name}")
                        print(f"[Tool Args] {call.function.arguments}")
                        
                        try:
                            args = json.loads(call.function.arguments)
                            result = await james.tool_registry.dispatch(call.function.name, args)
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
                    print(f"\nAgent James: {message.content}")
                    break
                    
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\nError in chat loop: {e}")
            break
            
    print("\nShutting down harness...")
    james.stop()

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(run_harness())
