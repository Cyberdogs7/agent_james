import asyncio, os
from backend.jules_agent import JulesAgent

async def count_pages():
    agent = JulesAgent()
    count = 0
    total = 0
    pt = None
    
    while True:
        params = {'pageSize': 100}
        if pt:
            params['pageToken'] = pt
            
        resp = await agent._request('GET', agent.base_url + '/sessions', tool_name='ls', params=params)
        if not resp:
            break
            
        sessions = resp.get('sessions', [])
        total += len(sessions)
        count += 1
        
        pt = resp.get('nextPageToken')
        if not pt:
            break
            
        print(f'Pages: {count}, Total: {total}')
        
        # Limit to 50 pages for safety
        if count >= 50:
            print("Hit 50 pages limit")
            break

asyncio.run(count_pages())
