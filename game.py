"""Hangman game rules, kept free of any UI code so they are fast and easy to test."""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Mapping, Optional, Sequence, Set, Tuple

MAX_MISSES = 6  # head, body, two arms, two legs


class Status(Enum):
    PLAYING = "playing"
    WON = "won"
    LOST = "lost"


class Outcome(Enum):
    HIT = "hit"                # the letter is in the word
    MISS = "miss"              # the letter is not in the word (costs a life)
    SOLVED = "solved"          # the whole-word guess was right
    WRONG_WORD = "wrong_word"  # the whole-word guess was wrong (costs a life)
    REPEAT = "repeat"          # already tried, no penalty
    INVALID = "invalid"        # not letters, or the wrong length, no penalty
    GAME_OVER = "game_over"    # the round has already finished


@dataclass(frozen=True)
class GuessResult:
    outcome: Outcome
    guess: str = ""
    positions: Tuple[int, ...] = ()  # indexes revealed by this guess

    @property
    def costs_life(self) -> bool:
        return self.outcome in (Outcome.MISS, Outcome.WRONG_WORD)


def is_letters(text: str) -> bool:
    """True for a non-empty string made only of the letters A-Z (any case)."""
    return text.isascii() and text.isalpha()


class HangmanGame:
    """One round of hangman.

    Letter positions are indexed once up front, so every guess is a constant-time
    set/dict lookup no matter how long the word is or how many times a letter repeats.
    """

    __slots__ = ("word", "category", "max_misses", "misses", "status",
                 "guessed", "wrong_words", "_positions", "_hidden")

    def __init__(self, word: str, category: str = "", max_misses: int = MAX_MISSES) -> None:
        word = word.strip().upper()
        if not is_letters(word):
            raise ValueError(f"word must contain only letters A-Z, got {word!r}")
        if max_misses < 1:
            raise ValueError("max_misses must be at least 1")

        self.word = word
        self.category = category
        self.max_misses = max_misses
        self.misses = 0
        self.status = Status.PLAYING
        self.guessed: Set[str] = set()      # every letter the player has tried
        self.wrong_words: Set[str] = set()  # whole-word guesses that were wrong

        positions: Dict[str, List[int]] = {}
        for index, letter in enumerate(word):
            positions.setdefault(letter, []).append(index)
        self._positions: Dict[str, Tuple[int, ...]] = {k: tuple(v) for k, v in positions.items()}
        self._hidden: Set[str] = set(self._positions)  # letters not found yet

    @property
    def lives_left(self) -> int:
        return self.max_misses - self.misses

    @property
    def masked(self) -> str:
        """The word with unfound letters replaced by underscores, e.g. ``"PY__ON"``."""
        hidden = self._hidden
        return "".join("_" if letter in hidden else letter for letter in self.word)

    def is_revealed(self, index: int) -> bool:
        return self.word[index] not in self._hidden

    def guess_letter(self, letter: str) -> GuessResult:
        if self.status is not Status.PLAYING:
            return GuessResult(Outcome.GAME_OVER, letter)

        letter = letter.strip().upper()
        if len(letter) != 1 or not is_letters(letter):
            return GuessResult(Outcome.INVALID, letter)
        if letter in self.guessed:
            return GuessResult(Outcome.REPEAT, letter)

        self.guessed.add(letter)
        positions = self._positions.get(letter)
        if positions is None:
            self._miss()
            return GuessResult(Outcome.MISS, letter)

        self._hidden.discard(letter)
        if not self._hidden:
            self.status = Status.WON
        return GuessResult(Outcome.HIT, letter, positions)

    def guess_word(self, word: str) -> GuessResult:
        if self.status is not Status.PLAYING:
            return GuessResult(Outcome.GAME_OVER, word)

        word = word.strip().upper()
        if len(word) == 1:
            return self.guess_letter(word)
        if not is_letters(word) or len(word) != len(self.word):
            return GuessResult(Outcome.INVALID, word)

        if word == self.word:
            revealed = tuple(sorted(i for letter in self._hidden for i in self._positions[letter]))
            self._hidden.clear()
            self.status = Status.WON
            return GuessResult(Outcome.SOLVED, word, revealed)

        if word in self.wrong_words:
            return GuessResult(Outcome.REPEAT, word)
        self.wrong_words.add(word)
        self._miss()
        return GuessResult(Outcome.WRONG_WORD, word)

    def _miss(self) -> None:
        self.misses += 1
        if self.misses >= self.max_misses:
            self.status = Status.LOST


class WordBag:
    """Deals words in random order without repeats until every word has been used.

    This is a "shuffle bag": each pick is O(1), and a word is never dealt twice
    in a row, even when the bag is refilled.
    """

    def __init__(self, words: Mapping[str, Sequence[str]], rng: Optional[random.Random] = None) -> None:
        entries: Dict[str, str] = {}
        for category, category_words in words.items():
            for word in category_words:
                entries.setdefault(word.strip().upper(), category)
        if not entries:
            raise ValueError("WordBag needs at least one word")

        self._entries: List[Tuple[str, str]] = list(entries.items())
        self._rng = rng or random.Random()
        self._bag: List[Tuple[str, str]] = []
        self._last: Optional[Tuple[str, str]] = None

    def __len__(self) -> int:
        return len(self._entries)

    def next(self) -> Tuple[str, str]:
        """Return the next ``(word, category)`` pair."""
        if not self._bag:
            self._bag = self._entries[:]
            self._rng.shuffle(self._bag)
            # Words are popped from the end, so keep the previous word away from it.
            if len(self._bag) > 1 and self._bag[-1] == self._last:
                self._bag[0], self._bag[-1] = self._bag[-1], self._bag[0]
        self._last = self._bag.pop()
        return self._last
