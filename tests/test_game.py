import random
import unittest

from game import MAX_MISSES, HangmanGame, Outcome, Status, WordBag
from words import MAX_WORD_LENGTH, WORDS


class HangmanGameTests(unittest.TestCase):
    def test_hit_reveals_every_position_of_a_repeated_letter(self):
        game = HangmanGame("JAVA")
        result = game.guess_letter("a")
        self.assertIs(result.outcome, Outcome.HIT)
        self.assertEqual(result.positions, (1, 3))
        self.assertEqual(game.masked, "_A_A")

    def test_guesses_are_case_insensitive(self):
        # The original game counted lowercase guesses against words like "HTML" as misses.
        game = HangmanGame("Html")
        for letter in "hTmL":
            self.assertIs(game.guess_letter(letter).outcome, Outcome.HIT)
        self.assertIs(game.status, Status.WON)
        self.assertEqual(game.misses, 0)

    def test_miss_costs_a_life(self):
        game = HangmanGame("CODE")
        result = game.guess_letter("z")
        self.assertIs(result.outcome, Outcome.MISS)
        self.assertTrue(result.costs_life)
        self.assertEqual(game.lives_left, MAX_MISSES - 1)

    def test_repeated_guess_is_free(self):
        game = HangmanGame("CODE")
        game.guess_letter("z")
        game.guess_letter("c")
        self.assertIs(game.guess_letter("Z").outcome, Outcome.REPEAT)
        self.assertIs(game.guess_letter("c").outcome, Outcome.REPEAT)
        self.assertEqual(game.misses, 1)

    def test_empty_and_non_letter_guesses_are_rejected_without_penalty(self):
        game = HangmanGame("CODE")
        for bad in ("", " ", "1", "?", "co", "é"):
            self.assertIs(game.guess_letter(bad).outcome, Outcome.INVALID, bad)
        self.assertEqual(game.misses, 0)
        self.assertEqual(game.masked, "____")

    def test_losing_after_max_misses(self):
        game = HangmanGame("CODE")
        for letter in "QWRTYU":
            game.guess_letter(letter)
        self.assertIs(game.status, Status.LOST)
        self.assertIs(game.guess_letter("C").outcome, Outcome.GAME_OVER)
        self.assertEqual(game.masked, "____")

    def test_no_guesses_after_winning(self):
        game = HangmanGame("BETA")
        for letter in "BETA":
            game.guess_letter(letter)
        self.assertIs(game.status, Status.WON)
        self.assertIs(game.guess_letter("Z").outcome, Outcome.GAME_OVER)
        self.assertIs(game.guess_word("BETA").outcome, Outcome.GAME_OVER)
        self.assertEqual(game.misses, 0)

    def test_solving_the_whole_word_reveals_the_rest(self):
        game = HangmanGame("PYTHON")
        game.guess_letter("o")
        result = game.guess_word(" python ")
        self.assertIs(result.outcome, Outcome.SOLVED)
        self.assertEqual(result.positions, (0, 1, 2, 3, 5))
        self.assertIs(game.status, Status.WON)
        self.assertEqual(game.masked, "PYTHON")

    def test_wrong_word_costs_a_life_once(self):
        game = HangmanGame("PYTHON")
        self.assertIs(game.guess_word("KOTLIN").outcome, Outcome.WRONG_WORD)
        self.assertIs(game.guess_word("kotlin").outcome, Outcome.REPEAT)
        self.assertEqual(game.misses, 1)

    def test_word_guess_of_wrong_length_or_symbols_is_rejected(self):
        game = HangmanGame("PYTHON")
        for bad in ("", "JAVA", "PYTH0N", "PYTHONS"):
            self.assertIs(game.guess_word(bad).outcome, Outcome.INVALID, bad)
        self.assertEqual(game.misses, 0)

    def test_single_letter_word_guess_is_a_letter_guess(self):
        game = HangmanGame("PYTHON")
        self.assertIs(game.guess_word("p").outcome, Outcome.HIT)

    def test_substring_is_not_a_hit(self):
        # The original game accepted any substring, e.g. "ec" for "Tech".
        game = HangmanGame("TECH")
        self.assertIs(game.guess_letter("ec").outcome, Outcome.INVALID)
        self.assertIs(game.guess_word("ec").outcome, Outcome.INVALID)

    def test_rejects_invalid_words(self):
        for bad in ("", "NODE JS", "C++", "D4TA"):
            with self.assertRaises(ValueError):
                HangmanGame(bad)


class WordBagTests(unittest.TestCase):
    def test_deals_every_word_once_per_cycle(self):
        words = {"A": ("ONE", "TWO", "THREE"), "B": ("FOUR", "FIVE")}
        bag = WordBag(words, random.Random(1))
        dealt = [bag.next()[0] for _ in range(len(bag))]
        self.assertCountEqual(dealt, ["ONE", "TWO", "THREE", "FOUR", "FIVE"])

    def test_never_repeats_a_word_back_to_back(self):
        bag = WordBag({"A": ("ONE", "TWO")}, random.Random(7))
        previous = bag.next()
        for _ in range(500):
            current = bag.next()
            self.assertNotEqual(current, previous)
            previous = current

    def test_keeps_category_and_drops_duplicates(self):
        bag = WordBag({"First": ("code",), "Second": ("CODE", "BYTE")}, random.Random(0))
        self.assertEqual(len(bag), 2)
        self.assertEqual(dict(bag.next() for _ in range(2)), {"CODE": "First", "BYTE": "Second"})


class WordListTests(unittest.TestCase):
    def test_every_word_is_playable_and_fits_the_tiles(self):
        for category, words in WORDS.items():
            for word in words:
                self.assertTrue(word.isascii() and word.isalpha(), (category, word))
                self.assertLessEqual(len(word), MAX_WORD_LENGTH, word)
                HangmanGame(word, category)

    def test_word_list_has_no_duplicates(self):
        all_words = [word for words in WORDS.values() for word in words]
        self.assertEqual(len(all_words), len(set(all_words)))


if __name__ == "__main__":
    unittest.main()
