import pytest

from aviary_kernel.environment import Environment


@pytest.fixture
def env():
    return Environment()
