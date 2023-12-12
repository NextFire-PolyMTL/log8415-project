import asyncio
import logging

from common.config import LOG_LEVEL

from patterns.setup import patterns_setup

if __name__ == "__main__":
    logging.basicConfig(level=LOG_LEVEL)
    asyncio.run(patterns_setup())
