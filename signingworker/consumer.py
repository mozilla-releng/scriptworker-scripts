import logging

from configman import Namespace, ConfigurationManager
from kombu import Connection

from signingworker.worker import SigningConsumer

log = logging.getLogger(__name__)


def main():
    config = ConfigurationManager(define_config()).get_config()
    if config.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.WARNING
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=log_level
    )
    logging.getLogger("taskcluster").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.ERROR)
    logging.getLogger("hawk").setLevel(logging.WARNING)
    logging.getLogger("sh").setLevel(logging.WARNING)

    queue_name = 'queue/{}/{}/pending'.format(config.pulse_user,
                                              config.worker_type)
    taskcluster_config = {
        "credentials": {
            "clientId": config.taskcluster_client_id,
            "accessToken": config.taskcluster_access_token
        }
    }
    with Connection(hostname=config.pulse_host, port=config.pulse_port,
                    userid=config.pulse_user, password=config.pulse_password,
                    virtual_host='/', ssl=True, heartbeat=5) as connection:
        worker = SigningConsumer(
            connection=connection, exchange=config.exchange,
            queue_name=queue_name, worker_type=config.worker_type,
            taskcluster_config=taskcluster_config,
            signing_server_config=config.signing_server_config,
            tools_checkout=config.tools_checkout,
            my_ip=config.my_ip,
            worker_id=config.worker_id
        )
        worker.run()


def define_config():
    ns = Namespace()
    ns.add_option(name="pulse_host")
    ns.add_option(name="pulse_password", secret=True)
    ns.add_option(name="pulse_port", from_string_converter=int)
    ns.add_option(name="pulse_user", secret=True)
    ns.add_option(name="worker_type")
    ns.add_option(name="exchange")
    ns.add_option(name="taskcluster_client_id")
    ns.add_option(name="taskcluster_access_token")
    ns.add_option(name="signing_server_config")
    ns.add_option(name="tools_checkout")
    ns.add_option(name="my_ip")
    ns.add_option(name="worker_id")
    ns.add_option(name="verbose", default=False)
    return ns

if __name__ == "__main__":
    main()
