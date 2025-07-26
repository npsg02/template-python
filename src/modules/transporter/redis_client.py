
import redis

# Connect to Redis
r = redis.Redis(host='ubuntu', port=6379, decode_responses=True)

# Set a value
r.set('foo', 'bar')

# Get a value
value = r.get('foo')
print(value)  # Output: bar


print("Redis client is running...", r.ping())


import asyncio
from redis.asyncio import Redis
from functools import wraps
from typing import Callable, Dict


class AsyncRedisPubSub:
    def __init__(self, host="ubuntu", port=6379, db=0):
        self.redis = Redis(host=host, port=port, db=db)
        self.channel_handlers: Dict[str, Callable[[str], None]] = {}
        self._subscriber_started = False
        self._lock = asyncio.Lock()

    def subscribe(self, channel: str):
        def decorator(func: Callable[[str], None]):
            self.channel_handlers[channel] = func
            asyncio.create_task(self._ensure_subscriber())
            return func
        return decorator

    async def publish(self, channel: str, message: str):
        await self.redis.publish(channel, message)

    async def _ensure_subscriber(self):
        async with self._lock:
            if self._subscriber_started:
                return
            self._subscriber_started = True
            await self._start_subscriber()

    async def _start_subscriber(self):
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(*self.channel_handlers.keys())
        print(f"Subscribed to: {', '.join(self.channel_handlers.keys())}")

        async def listen():
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                channel = message["channel"].decode()
                data = message["data"].decode()
                handler = self.channel_handlers.get(channel)
                if handler:
                    await self._maybe_async(handler, data)

        asyncio.create_task(listen())

    async def _maybe_async(self, func: Callable, *args, **kwargs):
        result = func(*args, **kwargs)
        if asyncio.iscoroutine(result):
            await result


pubsub = AsyncRedisPubSub()

@pubsub.subscribe("chat")
def handle_chat(msg):
    print(f"[chat redis] Received: {msg}")

@pubsub.subscribe("news")
def handle_news(msg):
    print(f"[news] Breaking: {msg}")
