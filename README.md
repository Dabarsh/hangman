# hangman
cool hangman, built with Python and [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter).

## Run it

```
pip install -r requirements.txt
python main.py
```

## How to play

- Guess a letter by clicking a key or typing it on your keyboard.
- You have 6 lives. Every wrong letter adds a part to the hangman.
- The hint under the drawing tells you the word's category.
- Know the word? Type it in the box at the bottom and press **Enter** (a wrong word costs a life).
- Repeated guesses, empty guesses and words of the wrong length never cost a life.
- Your wins, losses and streak are shown at the top. Skipping a round you've started ends your streak.

| Key | Action |
| --- | --- |
| `A`-`Z` | Guess a letter |
| `Enter` | Solve (in the word box), or start a new game when a round is over |
| `Ctrl+N` | New game at any time |
| `Esc` | Leave the word box and go back to guessing letters |

Use the **Dark** switch in the top right to change the theme.

## Project layout

- `main.py`: the window and everything you see
- `game.py`: the game rules (no UI code)
- `words.py`: the word list, grouped by category. Add your own words here.
- `tests/`: tests for the game rules. Run them with `python -m unittest`.
