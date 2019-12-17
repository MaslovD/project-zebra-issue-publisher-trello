from config import ApplicationConfig
import traceback
import sys
from os import getenv
import pika
from trello import TrelloClient
from json import loads, dumps
from logger import get_logger

PROPERTIES_URL = getenv('PROPERTIES_URL')
logger = get_logger(__name__)
config = ApplicationConfig(PROPERTIES_URL)

# TRELLO_VERSION = r"Version: (\S+)\.?"
TRELLO_LIST_PUSH_NAME = "backlog"


def trello_list(api_key, token, url="https://trello.com/b/uEd50g7X/zebra-test"):
    board = trello_board(api_key, token, url)
    list_lists = board.open_lists()
    if TRELLO_LIST_PUSH_NAME in list(map(str.lower, [l.name for l in list_lists])):
        return list_lists[list(map(str.lower, [l.name for l in list_lists])).index(TRELLO_LIST_PUSH_NAME)]
    return board.add_list(TRELLO_LIST_PUSH_NAME, 0)


def trello_board(api_key, token, url="https://trello.com/b/uEd50g7X/zebra-test"):
    return list(filter(lambda b: b.url == url, TrelloClient(api_key=api_key, token=token).list_boards()))[0]


CONTACT_FORMAT = """

Contact info:
----------------------
*{}*
"""


def name(body):
    return body.get('name', 'Custom issue')


def desc(body):
    return body.get('arbitraryDescription', '') + contact(body)


def labels(body):
    list_labels = [(i.get('name', 'no name'), i.get('color', 'none')) for i in body.get('labels', {})]
    return [create_label_safe(*i) for i in list_labels]


def contact(body):
    contact_info_plain = body.get('contactInfo', '')
    if contact_info_plain != '':
        return CONTACT_FORMAT.format(contact_info_plain)
    return ""


def assign(*args):
    board = trello_board(config.trello_api_key, config.trello_token)
    return [board.all_members()[0]]


TRELLO_MAPPING = {'name': name,
                  'desc': desc,
                  'labels': labels,
                  'assign': assign
                  }


def on_message(channel, method_frame, header_frame, body):
    try:
        body = loads(body.decode('utf8'))
        trello_list(config.trello_api_key, config.trello_token).add_card(
            **{i[0]: i[1](body) for i in TRELLO_MAPPING.items()})
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
    board = trello_board(config.trello_api_key, config.trello_token)
    list_labels = {(i.name, i.color): i for i in board.get_labels()}
    if (name, color) in list_labels.keys():
        return list_labels[(name, color)]
    else:
        return board.add_label(name, color)


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
