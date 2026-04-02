"""
This file contains fixtures that will be used in multiple test modules.

See:
https://docs.pytest.org/en/latest/how-to/fixtures.html?highlight=conftest
https://stackoverflow.com/questions/34466027/in-pytest-what-is-the-use-of-conftest-py-files
"""
from typing import List

import pytest
import yaml

from python_template.reverse import get_reversers


def get_words() -> List[str]:
    with open("./tests/mocks/words.yml", "r") as f:
        return yaml.safe_load(f)


@pytest.fixture(params=get_words(), scope="module")
def word(request):
    return request.param


@pytest.fixture(params=get_reversers(), scope="module")
def reverser(request):
    return request.param
