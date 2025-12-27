"""
Kafka/RabbitMQ Event Streaming Infrastructure
Production-grade message broker integration
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Callable, Dict, Optional

# Kafka support
try:
    from kafka import KafkaConsumer, KafkaProducer
    from kafka.errors import KafkaError

    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False

# RabbitMQ support
try:
    import pika

    RABBITMQ_AVAILABLE = True
except ImportError:
    RABBITMQ_AVAILABLE = False


class EventBroker:
    """
    Abstract base class for event brokers
    Supports both Kafka and RabbitMQ
    """

    def __init__(self, broker_type: str = "kafka", **config):
        self.broker_type = broker_type
        self.config = config
        self.producer = None
        self.consumer = None

    async def publish(self, topic: str, event: Dict[str, Any]):
        """Publish event to topic/queue"""
        raise NotImplementedError

    async def subscribe(self, topic: str, callback: Callable):
        """Subscribe to topic/queue"""
        raise NotImplementedError

    async def close(self):
        """Close connections"""
        raise NotImplementedError


class KafkaEventBroker(EventBroker):
    """Kafka-based event broker"""

    def __init__(self, bootstrap_servers: str = "localhost:9092", **config):
        super().__init__(broker_type="kafka", **config)

        if not KAFKA_AVAILABLE:
            raise ImportError("kafka-python not installed")

        self.bootstrap_servers = bootstrap_servers
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
            **config,
        )

    async def publish(
        self, topic: str, event: Dict[str, Any], key: Optional[str] = None
    ):
        """Publish event to Kafka topic"""
        try:
            # Add metadata
            event["_timestamp"] = datetime.utcnow().isoformat()
            event["_broker"] = "kafka"

            future = self.producer.send(topic, value=event, key=key)
            record_metadata = future.get(timeout=10)

            print(
                f"✅ Published to Kafka: {topic} (partition {record_metadata.partition}, offset {record_metadata.offset})"
            )
            return True

        except KafkaError as e:
            print(f"❌ Kafka publish error: {e}")
            return False

    async def subscribe(
        self, topic: str, callback: Callable, group_id: str = "toasty-analytics"
    ):
        """Subscribe to Kafka topic"""
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id=group_id,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="earliest",
            enable_auto_commit=True,
        )

        print(f"📡 Subscribed to Kafka topic: {topic}")

        # Consume messages
        for message in consumer:
            try:
                await callback(message.value)
            except Exception as e:
                print(f"⚠️  Error processing message: {e}")

    async def close(self):
        """Close Kafka connections"""
        if self.producer:
            self.producer.close()
        print("✅ Kafka connections closed")


class RabbitMQEventBroker(EventBroker):
    """RabbitMQ-based event broker"""

    def __init__(self, host: str = "localhost", port: int = 5672, **credentials):
        super().__init__(broker_type="rabbitmq")

        if not RABBITMQ_AVAILABLE:
            raise ImportError("pika not installed")

        self.host = host
        self.port = port
        self.credentials = pika.PlainCredentials(
            credentials.get("username", "guest"), credentials.get("password", "guest")
        )
        self.connection = None
        self.channel = None

    def connect(self):
        """Establish RabbitMQ connection"""
        if not self.connection or self.connection.is_closed:
            self.connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=self.host, port=self.port, credentials=self.credentials
                )
            )
            self.channel = self.connection.channel()

    async def publish(self, queue: str, event: Dict[str, Any], exchange: str = ""):
        """Publish event to RabbitMQ queue"""
        try:
            self.connect()

            # Declare queue
            self.channel.queue_declare(queue=queue, durable=True)

            # Add metadata
            event["_timestamp"] = datetime.utcnow().isoformat()
            event["_broker"] = "rabbitmq"

            self.channel.basic_publish(
                exchange=exchange,
                routing_key=queue,
                body=json.dumps(event),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    content_type="application/json",
                ),
            )

            print(f"✅ Published to RabbitMQ: {queue}")
            return True

        except Exception as e:
            print(f"❌ RabbitMQ publish error: {e}")
            return False

    async def subscribe(self, queue: str, callback: Callable):
        """Subscribe to RabbitMQ queue"""
        self.connect()

        # Declare queue
        self.channel.queue_declare(queue=queue, durable=True)

        def on_message(ch, method, properties, body):
            try:
                event = json.loads(body)
                asyncio.create_task(callback(event))
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                print(f"⚠️  Error processing message: {e}")
                ch.basic_nack(delivery_tag=method.delivery_tag)

        self.channel.basic_consume(queue=queue, on_message_callback=on_message)

        print(f"📡 Subscribed to RabbitMQ queue: {queue}")
        self.channel.start_consuming()

    async def close(self):
        """Close RabbitMQ connections"""
        if self.connection and not self.connection.is_closed:
            self.connection.close()
        print("✅ RabbitMQ connections closed")


class EventStreaming:
    """
    High-level event streaming interface
    Automatically selects available broker (Kafka > RabbitMQ > fallback)
    """

    def __init__(self, broker_type: Optional[str] = None, **config):
        # Auto-detect available broker
        if broker_type is None:
            if KAFKA_AVAILABLE:
                broker_type = "kafka"
            elif RABBITMQ_AVAILABLE:
                broker_type = "rabbitmq"
            else:
                broker_type = "memory"  # Fallback to in-memory queue

        self.broker_type = broker_type
        self.broker = self._create_broker(broker_type, **config)

    def _create_broker(self, broker_type: str, **config) -> EventBroker:
        """Create appropriate broker instance"""
        if broker_type == "kafka" and KAFKA_AVAILABLE:
            return KafkaEventBroker(**config)
        elif broker_type == "rabbitmq" and RABBITMQ_AVAILABLE:
            return RabbitMQEventBroker(**config)
        else:
            # Fallback to in-memory asyncio queue (same as current implementation)
            print("⚠️  Using in-memory event queue (no Kafka/RabbitMQ available)")
            return None

    async def publish_grading_event(
        self, user_id: str, code: str, score: float, dimension: str
    ):
        """Publish a grading event"""
        event = {
            "type": "grading_completed",
            "user_id": user_id,
            "code_preview": code[:100],  # First 100 chars
            "score": score,
            "dimension": dimension,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if self.broker:
            await self.broker.publish("grading-events", event, key=user_id)
        else:
            # Fallback - just log it
            print(f"📊 Grading event: {user_id} scored {score} on {dimension}")

    async def publish_learning_event(self, user_id: str, strategy: Dict[str, Any]):
        """Publish a learning event"""
        event = {
            "type": "learning_update",
            "user_id": user_id,
            "strategy": strategy,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if self.broker:
            await self.broker.publish("learning-events", event, key=user_id)
        else:
            print(f"🧠 Learning event: {user_id} updated strategy")

    async def subscribe_to_grading_events(self, callback: Callable):
        """Subscribe to grading events"""
        if self.broker:
            await self.broker.subscribe("grading-events", callback)

    async def close(self):
        """Close event streaming connections"""
        if self.broker:
            await self.broker.close()


# Singleton instance
_event_streaming = None


def get_event_streaming(**config) -> EventStreaming:
    """Get global event streaming instance"""
    global _event_streaming
    if _event_streaming is None:
        _event_streaming = EventStreaming(**config)
    return _event_streaming
