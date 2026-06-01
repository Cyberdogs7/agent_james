import asyncio
import aiohttp
import os
import time

async def main():
    with open('dummy.bin', 'wb') as f:
        f.write(b'0' * 1024 * 1024 * 10) # 10MB

    start = time.time()
    # What if we just load the whole file via to_thread?
    async def read_file():
        with open('dummy.bin', 'rb') as f:
            return f.read()

    data_bytes = await asyncio.to_thread(read_file)
    data = aiohttp.FormData()
    data.add_field('file', data_bytes, filename='dummy.bin')
    print("loaded in", time.time() - start)

asyncio.run(main())
