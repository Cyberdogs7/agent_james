import asyncio
import os
import json
from google import genai
from google.genai import types
from backend.browser_agent import ProgrammaticBrowserAgent

browser_navigate_tool = {
    "name": "browser_navigate",
    "description": "Programmatically navigates the browser to a specific URL.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "url": {"type": "STRING", "description": "The URL to navigate to."}
        },
        "required": ["url"]
    }
}

browser_execute_javascript_tool = {
    "name": "browser_execute_javascript",
    "description": "Executes arbitrary JavaScript in the programmatic browser and returns the result.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "script": {"type": "STRING", "description": "The JavaScript code to execute."}
        },
        "required": ["script"]
    }
}

browser_get_dom_tool = {
    "name": "browser_get_dom",
    "description": "Returns the HTML of the programmatic browser's current page, or a specific element if a selector is provided.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "selector": {"type": "STRING", "description": "Optional CSS selector to get the HTML of a specific element."}
        }
    }
}

tools = [browser_navigate_tool, browser_execute_javascript_tool, browser_get_dom_tool]

async def run_test():
    browser_agent = ProgrammaticBrowserAgent()
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    
    prompt = (
        "You are an AI agent with programmatic browser tools. "
        "Navigate to https://nlevelsoftware.github.io/minigames/butterfly_botanist.html. "
        "First, use browser_execute_javascript or browser_get_dom to understand the game state if needed. "
        "Then, write a javascript script to automatically click the butterflies and win the game. "
        "The game might require you to click them continuously or interact with specific elements. "
        "Return when you think you've won."
    )
    
    chat = client.aio.chats.create(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            tools=[{"function_declarations": tools}],
            temperature=0.2
        )
    )
    
    print(f"User: {prompt}")
    response = await chat.send_message(prompt)
    
    for _ in range(15): # Max 15 turns
        if not response.function_calls:
            print(f"Agent Final Reply: {response.text}")
            break
            
        function_responses = []
        for call in response.function_calls:
            call_id = getattr(call, 'id', None)
            print(f"Agent wants to call: {call.name} with args: {call.args}")
            
            if call.name == "browser_navigate":
                result = await browser_agent.browser_navigate(call.args["url"])
            elif call.name == "browser_execute_javascript":
                result = await browser_agent.browser_execute_javascript(call.args["script"])
            elif call.name == "browser_get_dom":
                selector = call.args.get("selector")
                result = await browser_agent.browser_get_dom(selector)
            else:
                result = "Unknown function"
                
            try:
                print(f"Tool Result ({call.name}): {str(result)[:200]}...")
            except UnicodeEncodeError:
                print(f"Tool Result ({call.name}): [Output contains special characters]")
            
            # Construct response
            fr = types.FunctionResponse(
                name=call.name,
                id=call_id,
                response={"result": result}
            )
            function_responses.append(types.Part(function_response=fr))
            
        # Send results back
        await asyncio.sleep(5) # Delay to respect free-tier RPM limits
        response = await chat.send_message(function_responses)
        if response.text:
             print(f"Agent Thought: {response.text}")
            
    print("Test finished!")
    await browser_agent.stop()

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(run_test())
