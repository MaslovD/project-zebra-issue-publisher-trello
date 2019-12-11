from config import ApplicationConfig
from os import getenv
from py_eureka_client import eureka_client
import pika
from trello import TrelloClient
from json import loads
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


def on_message(channel, method_frame, header_frame, body):
    body = loads(body.decode('utf8'))
    trello_list.add_card(name=body.get('name'),
                         desc=body.get('arbitraryDescription'),
                         # assign=[trello_board.all_members()[0]]
                         )
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
    channel.basic_consume(config.rabbitmq_queue_name, on_message)
    channel.start_consuming()


if __name__ == '__main__':
    run()
