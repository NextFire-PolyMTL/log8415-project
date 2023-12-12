import asyncio
import logging

from common.config import LOG_LEVEL

from cluster import cluster_setup

if __name__ == "__main__":
    logging.basicConfig(level=LOG_LEVEL)
    asyncio.run(cluster_setup())
