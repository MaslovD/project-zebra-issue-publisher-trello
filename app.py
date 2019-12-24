import sys
import traceback
from json import loads, dumps
from json.decoder import JSONDecodeError
from os import getenv

import pika

from config import ApplicationConfig
from logger import get_logger
from providers import trello_app

PROPERTIES_URL = getenv('PROPERTIES_URL')
logger = get_logger(__name__)
config = ApplicationConfig(PROPERTIES_URL)


def on_message(channel, method_frame, header_frame, body):
    try:
        body = loads(body.decode('utf8'))
        if body.get("type") in ("trello", None):
            trello_app.push_card(config.trello_api_key,
                                 config.trello_token,
                                 body)
        else:
            raise NotImplementedError
    except JSONDecodeError as e:
        channel.basic_publish(exchange=config.rabbitmq_exchange_name,
                              routing_key=config.rabbitmq_dead_letter_queue_key,
                              body=dumps({
                                  "body": str(body),
                                  "exception": ''.join(traceback.format_exception(*sys.exc_info()))
                              }))
        logger.exception(e, exc_info=True)
    except Exception as e:
        channel.basic_publish(exchange=config.rabbitmq_exchange_name,
                              routing_key=config.rabbitmq_dead_letter_queue_key,
                              body=dumps({
                                  "body": body,
                                  "exception": ''.join(traceback.format_exception(*sys.exc_info()))
                              }))
        logger.exception(e, exc_info=True)
    finally:
        channel.basic_ack(delivery_tag=method_frame.delivery_tag)

def run():
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=config.rabbitmq_host,
            port=config.rabbitmq_port,
            credentials=pika.PlainCredentials(
                config.rabbitmq_username,
                config.rabbitmq_password
            ),
            virtual_host=config.rabbitmq_virtual_host
        )
    )
    logger.info("RabbitMQ connection created with params: host=%s port=%s virtual_host=%s ssl=%s",
                connection._impl.params.host,
                connection._impl.params.port,
                connection._impl.params.virtual_host,
                bool(connection._impl.params.ssl_options))
    channel = connection.channel()
    logger.info("Exchange %s created", config.rabbitmq_exchange_name)
    channel.exchange_declare(exchange_type='topic', exchange=config.rabbitmq_exchange_name)
    logger.info("Queue %s created", config.rabbitmq_queue_name)
    channel.queue_declare(queue=config.rabbitmq_queue_name)
    channel.queue_bind(queue=config.rabbitmq_queue_name, exchange=config.rabbitmq_exchange_name,
                       routing_key=config.rabbitmq_queue_key)
    logger.info("Queue %s created", config.rabbitmq_dead_letter_queue_name)
    channel.queue_declare(queue=config.rabbitmq_dead_letter_queue_name)
    channel.queue_bind(queue=config.rabbitmq_dead_letter_queue_name, exchange=config.rabbitmq_exchange_name,
                       routing_key=config.rabbitmq_dead_letter_queue_key)
    channel.basic_consume(config.rabbitmq_queue_name, on_message)
    channel.start_consuming()


if __name__ == '__main__':
    run()
