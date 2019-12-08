from config import ApplicationConfig
from os import getenv
from py_eureka_client import eureka_client
import pika
from trello import TrelloClient
from json import loads

PROPERTIES_URL = getenv('PROPERTIES_URL')

config = ApplicationConfig(PROPERTIES_URL)


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
                         assign=[trello_board.all_members()[0]])
    channel.basic_ack(delivery_tag=method_frame.delivery_tag)


virtual_host = config.rabbitmq_virtual_host.replace('/', '')
virtual_host = virtual_host if virtual_host else '/'
connection = pika.BlockingConnection(
    pika.ConnectionParameters(
        host=config.rabbitmq_host,
        port=config.rabbitmq_port,
        credentials=pika.PlainCredentials(
            config.rabbitmq_username,
            config.rabbitmq_password
        ),
        virtual_host=virtual_host
    )
)
channel = connection.channel()
channel.exchange_declare(exchange_type='topic', exchange=config.rabbitmq_exchange_name)
channel.queue_declare(queue=config.rabbitmq_queue_name)
channel.queue_bind(queue=config.rabbitmq_queue_name, exchange=config.rabbitmq_exchange_name,
                   routing_key=config.rabbitmq_queue_key)
channel.basic_consume(config.rabbitmq_queue_name, on_message)

trello_client = TrelloClient(
    api_key=config.trello_api_key,
    token=config.trello_token
)

trello_board = trello_client.list_boards()[0]
trello_list = trello_board.get_list('5dbf362946cb870de24aff11')

try:
    channel.start_consuming()
except KeyboardInterrupt:
    channel.stop_consuming()
connection.close()