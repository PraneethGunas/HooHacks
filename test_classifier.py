import asyncio
import sys

sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv('.env')

from backend.agents.classifier import run_classifier

async def main():
    result = await run_classifier("Raise the federal minimum wage to $15/hr")
    print(result.model_dump_json(indent=2))

asyncio.run(main())
