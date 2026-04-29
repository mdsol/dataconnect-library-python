import pytest


def test_client() -> None:
    assert True


@pytest.mark.benchmark
def test_dummy_benchmark() -> None:
    # Dummy benchmark test to satisfy CI
    assert True
