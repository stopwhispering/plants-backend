import pytest


@pytest.fixture(scope="session")
def number():
    print('hello')
    yield 1
    print('goodbye')