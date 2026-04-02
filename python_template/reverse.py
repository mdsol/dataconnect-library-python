"""
Reverse the letters in a string
"""

from typing import Callable, List


def for_loop_reverse(word: str) -> str:
    n_letters = len(word)
    ans = ""
    for index in range(n_letters):
        reverse_index = n_letters - (index + 1)
        ans += word[reverse_index]
    return ans


def slice_reverse(word: str) -> str:
    ans = word[::-1]
    return ans


def reverse_word(word: str, reverser: Callable[[str], str] = for_loop_reverse) -> str:
    return reverser(word)


def get_reversers() -> List[Callable[[str], str]]:
    return [slice_reverse, for_loop_reverse]
