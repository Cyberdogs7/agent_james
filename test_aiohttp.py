import asyncio
import aiohttp
import aiofiles
import os
import time

async def main():
    async with aiofiles.open('dummy.bin', 'wb') as f:
        await f.write(b'0' * 1024 * 1024 * 10) # 10MB

    start = time.time()
    # What if we just load the whole file via to_thread?
    async def read_file():
        with open('dummy.bin', 'rb') as f:
            return f.read()

    data_bytes = await asyncio.to_thread(read_file)
    data = aiohttp.FormData()
    data.add_field('file', data_bytes, filename='dummy.bin')
    print("loaded in", time.time() - start)

    os.remove('dummy.bin')

asyncio.run(main())
