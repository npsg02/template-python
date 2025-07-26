import pika
import threading

credentials = pika.PlainCredentials('guest', 'guest')

parameters = pika.ConnectionParameters(
    host='ubuntu',
    port=5672,  # default RabbitMQ port
    virtual_host='/',  # default vhost, change if needed
    credentials=credentials
)

def queue_listener(queue_name, host="localhost"):
    def decorator(func):
        def start_consumer():
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            channel.queue_declare(queue=queue_name, durable=True)

            def callback(ch, method, properties, body):
                try:
                    func(body.decode())  # Gọi hàm xử lý
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                except Exception as e:
                    print(f"Error handling message: {e}")
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=queue_name, on_message_callback=callback)
            print(f"[+] Listening on queue '{queue_name}'")
            channel.start_consuming()

        # chạy consumer trên thread riêng (không chặn main thread)
        threading.Thread(target=start_consumer, daemon=True).start()
        return func
    return decorator

@queue_listener("hello-python")
def process_message(msg):
    print(f"[x] Received: {msg}")


@queue_listener("test")
def test_queue_listener(msg):
    # This function is just for testing the queue listener
    print(f"[test] Received message: {msg}")


# publish a message to the queue
def publish_message(queue_name, message):
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    # channel.queue_declare(queue=queue_name, durable=True)
    channel.basic_publish(
        exchange='',
        routing_key=queue_name,
        body=message,
        properties=pika.BasicProperties(
            delivery_mode=2,  # make message persistent
        )
    )
    print(f"[x] Sent: {message}")

publish_message("hello-python", "RabbitMQ is running!")