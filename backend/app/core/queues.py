import asyncio

# Queues globales en mémoire pour remplacer Kafka dans le mode Sans Docker
prices_queue = asyncio.Queue()
news_queue = asyncio.Queue()
