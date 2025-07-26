import asyncio
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from functools import wraps
from typing import Callable, Dict


class AsyncKafkaPubSub:
    def __init__(self, bootstrap_servers="ubuntu:9092", group_id="default-py-group"):
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.handlers: Dict[str, Callable[[str], None]] = {}
        self._consumer_started = False
        self._lock = asyncio.Lock()
        self._producer = None

    def subscribe(self, topic: str):
        print(f"Subscribing to topic: {topic}")
        def decorator(func: Callable[[str], None]):
            self.handlers[topic] = func
            asyncio.create_task(self._ensure_consumer())
            return func
        return decorator

    async def publish(self, topic: str, message: str):
        if not self._producer:
            self._producer = AIOKafkaProducer(bootstrap_servers=self.bootstrap_servers)
            await self._producer.start()
        await self._producer.send_and_wait(topic, message.encode())

    async def _ensure_consumer(self):
        async with self._lock:
            if self._consumer_started:
                return
            self._consumer_started = True
            await self._start_consumer()

    async def _start_consumer(self):
        consumer = AIOKafkaConsumer(
            *self.handlers.keys(),
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            auto_offset_reset='latest',
        )
        await consumer.start()
        print(f"Subscribed to: {', '.join(self.handlers.keys())}")

        async def listen():
            try:
                async for msg in consumer:
                    print(f"Received message on topic '{msg.topic}': {msg.value.decode()}")
                    topic = msg.topic
                    data = msg.value.decode()
                    handler = self.handlers.get(topic)
                    if handler:
                        await self._maybe_async(handler, data)
            finally:
                await consumer.stop()

        asyncio.create_task(listen())

    async def _maybe_async(self, func: Callable, *args, **kwargs):
        result = func(*args, **kwargs)
        if asyncio.iscoroutine(result):
            await result


kafka_pubsub = AsyncKafkaPubSub()


@kafka_pubsub.subscribe("chat")
def handle_chat(msg):
    print(f"[chat kafka] {msg}")

