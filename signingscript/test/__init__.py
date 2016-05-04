import os


def read_file(path):
    with open(path) as f:
        return f.read()


PUB_KEY = read_file(os.path.join(os.path.dirname(__file__), "id_rsa.pub"))
