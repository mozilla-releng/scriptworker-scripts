import logging


def init():
    FORMAT = '%(asctime)s - %(filename)s - %(levelname)s - %(message)s'
    logging.basicConfig(format=FORMAT, level=logging.DEBUG)
    logging.getLogger('oauth2client').setLevel(logging.WARNING)
    logging.getLogger('androguard').setLevel(logging.WARNING)
