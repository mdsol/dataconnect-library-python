import pytest

from python_template.reverse import get_reversers, reverse_word


@pytest.fixture(scope="module")
def reversed_word(word, reverser):
    return reverse_word(word, reverser)


def test_reversed_string_same_length(word, reversed_word):
    assert len(word) == len(reversed_word)


def test_last_letter_of_reversed_word_is_first_letter_of_word(word, reversed_word):
    assert word[0] == reversed_word[-1]


def test_reverse_empty_string():
    word = ""
    reversed_word = reverse_word(word)
    assert word == reversed_word


def test_reversers_all_agree(word, reversed_word):
    first_reverser = get_reversers()[0]
    assert reversed_word == first_reverser(word)


def test_reversers_palindrome(word, reverser, reversed_word):
    palindrome = word + reversed_word
    assert palindrome == reverser(palindrome)


def test_reverse_asdfjkl_correctly():
    word = "asdfjkl"
    reversed_word = reverse_word(word)
    assert reversed_word == "lkjfdsa"
