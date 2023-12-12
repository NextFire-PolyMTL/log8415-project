import asyncio
import logging

from common.config import LOG_LEVEL

from standalone.setup import standalone_setup

if __name__ == "__main__":
    logging.basicConfig(level=LOG_LEVEL)
    asyncio.run(standalone_setup())
