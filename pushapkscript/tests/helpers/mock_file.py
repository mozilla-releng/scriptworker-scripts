class MockFile:
    def __init__(self, name):
        self.name = name

    def __enter__(self):
        return self

    def __exit__(self, _, __, ___):
        pass

    def __eq__(self, other):
        return isinstance(other, MockFile) and self.name == other.name


def mock_open(filename, _=None):
    return MockFile(filename)
