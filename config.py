import os
import jprops
import requests
import io
import sys

ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
CONFIG_PATH = os.path.join(ROOT_DIR, '.cfg.properties')


class ApplicationConfig:
    def __init__(self, url):
        try:
            props = self._from_local_config()
            self._set_props(props)
            return
        except FileNotFoundError:
            pass

        try:
            props = self._from_properties_url(url)
            self._set_props(props)
        except requests.exceptions.RequestException:
            # FIXME: do it in the better way
            sys.exit(1)

    def _set_props(self, props):
        # self.eureka_url = props.get("eureka.client.serviceUrl.defaultZone")
        # self.eureka_instance_name = props.get("eureka.instance.name")
        # self.eureka_lease_renewal_interval_in_seconds = int(props.get("eureka.instance.leaseRenewalIntervalInSeconds", 5))
        # self.eureka_registry_fetch_interval_seconds = int(props.get("eureka.client.registryFetchIntervalSeconds", 5))
        self.trello_api_key = props.get('issue-publisher.trello.api_key')
        self.trello_token = props.get('issue-publisher.trello.token')
        self.rabbitmq_host = props.get('spring.rabbitmq.host')
        self.rabbitmq_port = props.get('spring.rabbitmq.port')
        self.rabbitmq_protocol = props.get('spring.rabbitmq.protocol')
        self.rabbitmq_virtual_host = props.get('spring.rabbitmq.virtual_host')
        self.rabbitmq_username = props.get('spring.rabbitmq.username')
        self.rabbitmq_password = props.get('spring.rabbitmq.password')
        self.rabbitmq_queue_name = props.get('issue-publisher.trello.rabbitmq.queue.name')
        self.rabbitmq_queue_key = props.get('issue-publisher.trello.rabbitmq.queue.key')
        self.rabbitmq_exchange_name = props.get('issue-publisher.rabbitmq.exchange.name')

    @staticmethod
    def _from_local_config() -> dict:
        with open(CONFIG_PATH, 'r') as file:
            return jprops.load_properties(file)

    @staticmethod
    def _from_properties_url(url) -> dict:
        session = requests.Session()
        session.trust_env = False
        response = session.get(url)
        props = jprops.load_properties(io.StringIO(response.text))
        session.close()
        return props
