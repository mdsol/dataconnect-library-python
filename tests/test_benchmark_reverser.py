import os

import pytest

from python_template.reverse import reverse_word

SKIP_BENCHMARK = len(os.environ.get("SKIP_BENCHMARK", "")) > 0
SKIP_REASON = "Environment doesn't want to run the benchmark"


@pytest.mark.benchmark
def test_benchmark(benchmark, reverser, word):
    benchmark(reverse_word, word, reverser)
