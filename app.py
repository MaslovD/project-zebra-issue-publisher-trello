from config import ApplicationConfig
import traceback
import sys
from os import getenv
from py_eureka_client import eureka_client
import pika
from trello import TrelloClient
from json import loads, dumps
from logger import get_logger

PROPERTIES_URL = getenv('PROPERTIES_URL')
logger = get_logger(__name__)
config = ApplicationConfig(PROPERTIES_URL)
trello_client = TrelloClient(
    api_key=config.trello_api_key,
    token=config.trello_token
)

trello_board = trello_client.list_boards()[0]
trello_list = trello_board.get_list('5dbf362946cb870de24aff11')

# try:
#     eureka_client.init_registry_client(
#         eureka_server=config.eureka_url,
#         app_name=config.eureka_instance_name,
#         renewal_interval_in_secs=config.eureka_lease_renewal_interval_in_seconds
#     )
# except Exception:
#     print('Failed to init eureka')

CONTACT_FORMAT = """

Контактная информация:
----------------------
*{}*
"""


def name(body):
    return body.get('name')


def desc(body):
    return body.get('arbitraryDescription') + contact(body)


def labels(body):
    list_labels = [(i.get('name'), i.get('color')) for i in body.get('labels', {})]
    return [create_label_safe(*i) for i in list_labels]


def contact(body):
    contact_info_plain = body.get('contactInfo', '')
    if contact_info_plain != '':
        return CONTACT_FORMAT.format(contact_info_plain)
    return ""


TRELLO_MAPPING = {'name': name,
                  'desc': desc,
                  'labels': labels}


def on_message(channel, method_frame, header_frame, body):
    body = loads(body.decode('utf8'))
    try:
        trello_list.add_card(**{i[0]: i[1](body) for i in TRELLO_MAPPING.items()})
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


def create_label_safe(name, color):
    list_labels = {(i.name, i.color): i for i in trello_board.get_labels()}
    if (name, color) in list_labels.keys():
        return list_labels[(name, color)]
    else:
        return trello_board.add_label(name, color)


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
