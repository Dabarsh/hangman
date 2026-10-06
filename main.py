"""Hangman, built with CustomTkinter.

Run it with ``python main.py``. Guess letters by clicking the keys or typing on
your keyboard, or type the whole word into the box at the bottom to solve it.
"""

from __future__ import annotations

import tkinter as tk
from typing import Dict, List, Sequence, Tuple

import customtkinter as ctk

from game import MAX_MISSES, GuessResult, HangmanGame, Outcome, Status, WordBag, is_letters
from words import WORDS

Color = Tuple[str, str]  # (light mode, dark mode)

SURFACE: Color = ("#EEF0F4", "#14161A")
CARD: Color = ("#FFFFFF", "#1F2228")
TILE: Color = ("#EEF0F4", "#2A2E36")
INK: Color = ("#1F2328", "#E8EAED")
MUTED: Color = ("#5F6672", "#9AA0A8")
FAINT: Color = ("#C4C9D1", "#454B55")
KEY: Color = ("#E2E5EA", "#2C3038")
KEY_HOVER: Color = ("#D0D5DC", "#3A3F49")
ACCENT: Color = ("#2563EB", "#2563EB")
ACCENT_HOVER: Color = ("#1D4ED8", "#1D4ED8")
GOOD: Color = ("#15803D", "#15803D")       # fills behind white text
GOOD_INK: Color = ("#15803D", "#4CC38A")   # text and lines on the card
BAD: Color = ("#B91C1C", "#E05252")
MISS_KEY: Color = ("#F6D9D9", "#3D2629")
MISS_TEXT: Color = ("#9F1C1C", "#F19C9C")
WOOD: Color = ("#4B5563", "#8B929C")
ROPE: Color = ("#9A6B3A", "#C49A62")
WHITE: Color = ("#FFFFFF", "#FFFFFF")

KEY_ROWS = ("QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM")
TILE_ROW_WIDTH = 480  # tiles shrink for long words so the row fits the minimum window width
TILE_GAP = 6
CONTROL_MASK = 0x0004


def shortcut_mask(windowing_system: str) -> int:
    """Modifier bits that mean a key press is a shortcut, not a guess: Control plus Alt
    (Command on macOS). Alt is 0x0008 on X11 and macOS, but 0x20000 on Windows,
    where 0x0008 is NumLock."""
    return CONTROL_MASK | (0x20000 if windowing_system == "win32" else 0x0008)

# Key styles: (background, text colour, state). Compared by identity to skip redraws.
KEY_IDLE = (KEY, INK, "normal")
KEY_HIT = (GOOD, WHITE, "disabled")
KEY_MISS = (MISS_KEY, MISS_TEXT, "disabled")
KEY_LOCKED = (KEY, FAINT, "disabled")


class HangmanDrawing(ctk.CTkFrame):
    """The gallows and figure, drawn as vector shapes on a Tk canvas.

    Every shape is created once. Resizing only moves the existing shapes, and a
    guess only flips one shape's visibility, so it stays crisp at any window size
    and in both light and dark mode without loading or rescaling images.
    """

    VIEW_W, VIEW_H = 200, 222

    # (shape, coordinates in the 200x222 view box, line width, colour)
    GALLOWS = (
        ("line", (24, 208, 136, 208), 7, WOOD),   # ground
        ("line", (56, 208, 56, 14), 7, WOOD),     # pole
        ("line", (52, 14, 152, 14), 7, WOOD),     # beam
        ("line", (56, 50, 92, 14), 5, WOOD),      # brace
        ("line", (146, 14, 146, 44), 3, ROPE),    # rope
    )
    BODY = (
        ("oval", (128, 44, 164, 80), 4),          # head
        ("line", (146, 80, 146, 140), 4),         # torso
        ("line", (146, 96, 118, 124), 4),         # left arm
        ("line", (146, 96, 174, 124), 4),         # right arm
        ("line", (146, 140, 124, 182), 4),        # left leg
        ("line", (146, 140, 168, 182), 4),        # right leg
    )
    EYES = (  # two crosses, shown when the round is lost
        (137, 56, 143, 62), (143, 56, 137, 62),
        (149, 56, 155, 62), (155, 56, 149, 62),
    )

    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", corner_radius=0, **kwargs)
        self._canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0, width=220, height=200)
        self._canvas.pack(fill="both", expand=True)

        # (item id, view-box coordinates, view-box line width)
        self._items: List[Tuple[int, Sequence[float], float]] = []
        self._color_option: Dict[int, str] = {}  # ovals are coloured by outline, lines by fill
        self._gallows = [(self._make(shape, xy, w), color) for shape, xy, w, color in self.GALLOWS]
        self._body = [self._make(shape, xy, w, hidden=True) for shape, xy, w in self.BODY]
        self._eyes = [self._make("line", xy, 3, hidden=True) for xy in self.EYES]

        self._shown = 0
        self._eyes_shown = False
        self._figure_color: Color = INK
        self._size = (0, 0)
        self._layout_pending = False

        self._canvas.bind("<Configure>", self._on_configure)
        self._apply_colors()

    def show(self, misses: int, status: Status) -> None:
        """Show one body part per miss; colour the figure when the round ends."""
        shown = min(misses, len(self._body))
        if shown != self._shown:
            low, high = sorted((shown, self._shown))
            state = "normal" if shown > self._shown else "hidden"
            for item in self._body[low:high]:
                self._canvas.itemconfigure(item, state=state)
            self._shown = shown

        lost = status is Status.LOST
        if lost != self._eyes_shown:
            for item in self._eyes:
                self._canvas.itemconfigure(item, state="normal" if lost else "hidden")
            self._eyes_shown = lost

        color = BAD if lost else GOOD_INK if status is Status.WON else INK
        if color is not self._figure_color:
            self._figure_color = color
            self._apply_figure_color()

    def _make(self, shape: str, coords: Sequence[float], width: float, hidden: bool = False) -> int:
        state = "hidden" if hidden else "normal"
        if shape == "oval":
            item = self._canvas.create_oval(*coords, width=width, state=state)
            self._color_option[item] = "outline"
        else:
            item = self._canvas.create_line(*coords, width=width, state=state, capstyle=tk.ROUND)
            self._color_option[item] = "fill"
        self._items.append((item, coords, width))
        return item

    def _on_configure(self, event: tk.Event) -> None:
        self._size = (event.width, event.height)
        if not self._layout_pending:  # coalesce bursts of resize events into one layout
            self._layout_pending = True
            self.after_idle(self._layout)

    def _layout(self) -> None:
        self._layout_pending = False
        width, height = self._size
        if width < 2 or height < 2:
            return
        scale = max(min(width / self.VIEW_W, height / self.VIEW_H), 0.05)
        dx = (width - self.VIEW_W * scale) / 2
        dy = (height - self.VIEW_H * scale) / 2
        canvas = self._canvas
        for item, coords, line_width in self._items:
            canvas.coords(item, *[c * scale + (dx if i % 2 == 0 else dy) for i, c in enumerate(coords)])
            canvas.itemconfigure(item, width=max(1.0, line_width * scale))

    def _paint(self, item: int, color: Color) -> None:
        self._canvas.itemconfigure(item, **{self._color_option[item]: self._apply_appearance_mode(color)})

    def _apply_figure_color(self) -> None:
        for item in self._body + self._eyes:
            self._paint(item, self._figure_color)

    def _apply_colors(self) -> None:
        self._canvas.configure(bg=self._apply_appearance_mode(CARD))
        for item, color in self._gallows:
            self._paint(item, color)
        self._apply_figure_color()

    def _set_appearance_mode(self, mode_string: str) -> None:
        super()._set_appearance_mode(mode_string)
        self._apply_colors()


class WordTiles(ctk.CTkFrame):
    """A row of letter tiles. Tiles are pooled and reused between rounds, and each
    tile remembers its current look so unchanged tiles are never redrawn."""

    def __init__(self, master, font: ctk.CTkFont, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._font = font
        self._tiles: List[ctk.CTkLabel] = []
        self._looks: List[Tuple[str, Color, Color]] = []
        self._widths: List[int] = []
        self._word = ""

    def reset(self, word: str) -> None:
        self._word = word
        width = min(46, TILE_ROW_WIDTH // len(word) - TILE_GAP)
        while len(self._tiles) < len(word):
            tile = ctk.CTkLabel(self, text="", width=width, height=56, corner_radius=10,
                                fg_color=TILE, text_color=INK, font=self._font)
            self._tiles.append(tile)
            self._looks.append(("", TILE, INK))
            self._widths.append(width)
        for index, tile in enumerate(self._tiles):
            if index < len(word):
                self._set(index, "", TILE, INK)
                if self._widths[index] != width:
                    self._widths[index] = width
                    tile.configure(width=width)
                tile.grid(row=0, column=index, padx=TILE_GAP // 2)
            else:
                tile.grid_remove()

    def reveal(self, positions: Sequence[int]) -> None:
        for index in positions:
            self._set(index, self._word[index], TILE, INK)

    def finish(self, won: bool) -> None:
        for index, letter in enumerate(self._word):
            if won:
                self._set(index, letter, GOOD, WHITE)
            elif not self._looks[index][0]:
                self._set(index, letter, TILE, BAD)  # show what the player missed

    def _set(self, index: int, text: str, fg: Color, text_color: Color) -> None:
        look = (text, fg, text_color)
        if self._looks[index] != look:
            self._looks[index] = look
            self._tiles[index].configure(text=text, fg_color=fg, text_color=text_color)


class HangmanApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__(fg_color=SURFACE)
        self.title("Hangman")
        self.geometry("700x820")
        self.minsize(560, 700)

        self._fonts = {
            "title": ctk.CTkFont(size=26, weight="bold"),
            "stats": ctk.CTkFont(size=13),
            "hint": ctk.CTkFont(size=12, weight="bold"),
            "tile": ctk.CTkFont(size=26, weight="bold"),
            "status": ctk.CTkFont(size=15),
            "key": ctk.CTkFont(size=16, weight="bold"),
            "heart": ctk.CTkFont(size=18),
            "button": ctk.CTkFont(size=14, weight="bold"),
        }
        self._bag = WordBag(WORDS)
        self.game = HangmanGame("A")  # placeholder until new_game() deals a real word
        self.wins = self.losses = self.streak = self.best_streak = 0
        self._shortcut_mask = shortcut_mask(self.tk.call("tk", "windowingsystem"))

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_header()
        self._build_board()
        self._build_keyboard()
        self._build_footer()
        self._bind_keys()
        self.new_game()

    # ----------------------------------------------------------------- layout

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(18, 10))
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(header, text="HANGMAN", font=self._fonts["title"], text_color=INK).grid(
            row=0, column=0, sticky="w")
        self._stats = ctk.CTkLabel(header, text="", font=self._fonts["stats"], text_color=MUTED)
        self._stats.grid(row=0, column=1, sticky="e", padx=16)

        self._dark_mode = ctk.CTkSwitch(header, text="Dark", font=self._fonts["stats"],
                                        text_color=MUTED, progress_color=ACCENT,
                                        command=self._toggle_theme)
        self._dark_mode.grid(row=0, column=2, sticky="e")
        if ctk.get_appearance_mode() == "Dark":
            self._dark_mode.select()

    def _build_board(self) -> None:
        card = ctk.CTkFrame(self, fg_color=CARD, corner_radius=18)
        card.grid(row=1, column=0, sticky="nsew", padx=24, pady=6)
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(0, weight=1)

        self._drawing = HangmanDrawing(card)
        self._drawing.grid(row=0, column=0, sticky="nsew", padx=20, pady=(18, 6))

        info = ctk.CTkFrame(card, fg_color="transparent")
        info.grid(row=1, column=0, pady=(4, 10))
        self._hint = ctk.CTkLabel(info, text="", font=self._fonts["hint"], text_color=MUTED,
                                  fg_color=TILE, corner_radius=12, height=26)
        self._hint.pack(side="left", padx=(0, 16), ipadx=10)
        self._hearts: List[ctk.CTkLabel] = []
        self._hearts_alive: List[bool] = []
        for _ in range(MAX_MISSES):
            heart = ctk.CTkLabel(info, text="\u2665", font=self._fonts["heart"], text_color=BAD,
                                 width=20)
            heart.pack(side="left", padx=1)
            self._hearts.append(heart)
            self._hearts_alive.append(True)

        self._tiles = WordTiles(card, self._fonts["tile"])
        self._tiles.grid(row=2, column=0, pady=(2, 8))

        self._status = ctk.CTkLabel(card, text="", font=self._fonts["status"], text_color=MUTED,
                                    height=28, wraplength=460)
        self._status.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 16))
        self._status_look: Tuple[str, Color] = ("", MUTED)

    def _build_keyboard(self) -> None:
        keyboard = ctk.CTkFrame(self, fg_color="transparent")
        keyboard.grid(row=2, column=0, pady=(12, 4))
        self._keys: Dict[str, ctk.CTkButton] = {}
        self._key_styles: Dict[str, tuple] = {}
        for row_letters in KEY_ROWS:
            row = ctk.CTkFrame(keyboard, fg_color="transparent")
            row.pack(pady=3)
            for letter in row_letters:
                key = ctk.CTkButton(row, text=letter, width=44, height=48, corner_radius=9,
                                    font=self._fonts["key"], fg_color=KEY, hover_color=KEY_HOVER,
                                    text_color=INK, text_color_disabled=INK,
                                    command=lambda ch=letter: self.guess_letter(ch))
                key.pack(side="left", padx=3)
                self._keys[letter] = key
                self._key_styles[letter] = KEY_IDLE

    def _build_footer(self) -> None:
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=24, pady=(10, 20))
        footer.grid_columnconfigure(0, weight=1)

        self._solve_entry = ctk.CTkEntry(footer, height=40, corner_radius=10, font=self._fonts["status"],
                                         placeholder_text="Know the word? Type it and press Enter",
                                         text_color=INK, fg_color=CARD, border_color=FAINT)
        self._solve_entry.grid(row=0, column=0, sticky="ew")
        self._solve_entry.bind("<Return>", self._on_solve)
        self._solve_entry.bind("<KP_Enter>", self._on_solve)

        ctk.CTkButton(footer, text="Solve", width=84, height=40, corner_radius=10,
                      font=self._fonts["button"], fg_color=KEY, hover_color=KEY_HOVER,
                      text_color=INK, command=self._on_solve).grid(row=0, column=1, padx=(8, 0))
        ctk.CTkButton(footer, text="New game", width=112, height=40, corner_radius=10,
                      font=self._fonts["button"], fg_color=ACCENT, hover_color=ACCENT_HOVER,
                      text_color=WHITE, command=self.new_game).grid(row=0, column=2, padx=(8, 0))

    def _bind_keys(self) -> None:
        self.bind("<KeyPress>", self._on_key)
        self.bind("<Return>", self._on_return)
        self.bind("<KP_Enter>", self._on_return)
        self.bind("<Escape>", lambda _event: self.focus_set())
        self.bind("<Control-n>", lambda _event: self.new_game())
        self.bind("<Control-N>", lambda _event: self.new_game())
        self.bind("<Button-1>", self._on_click)

    # ------------------------------------------------------------------- game

    def new_game(self) -> None:
        if self.game.status is Status.PLAYING and (self.game.guessed or self.game.wrong_words):
            self.streak = 0  # skipping a round you have started ends the streak
        word, category = self._bag.next()
        self.game = HangmanGame(word, category)

        self._tiles.reset(word)
        for letter in self._keys:
            self._style_key(letter, KEY_IDLE)
        self._render_lives()
        self._drawing.show(0, Status.PLAYING)
        self._hint.configure(text=f"HINT  \u00b7  {category.upper()}")
        self._render_stats()
        self._set_status("Guess a letter: click a key or type it on your keyboard.", MUTED)
        self._clear_entry()
        self.focus_set()

    def guess_letter(self, letter: str) -> GuessResult:
        result = self.game.guess_letter(letter)
        self._apply(result)
        return result

    def guess_word(self, word: str) -> GuessResult:
        result = self.game.guess_word(word)
        self._apply(result)
        return result

    def _apply(self, result: GuessResult) -> None:
        game, outcome, guess = self.game, result.outcome, result.guess

        if outcome is Outcome.GAME_OVER:
            self._set_status("This round is over. Press Enter for a new game.", MUTED)
            return
        if outcome is Outcome.REPEAT:
            self._set_status(f"You already tried {guess}.", MUTED)
            return
        if outcome is Outcome.INVALID:
            if is_letters(guess) and len(guess) != len(game.word):
                self._set_status(f"The word has {len(game.word)} letters.", MUTED)
            else:
                self._set_status("Use the letters A to Z only.", MUTED)
            return

        if outcome is Outcome.HIT:
            self._style_key(guess, KEY_HIT)
        elif outcome is Outcome.MISS:
            self._style_key(guess, KEY_MISS)
        if result.positions:
            self._tiles.reveal(result.positions)
        if result.costs_life:
            self._render_lives()
            self._drawing.show(game.misses, game.status)

        if game.status is not Status.PLAYING:
            self._finish()
        elif outcome is Outcome.HIT:
            count = len(result.positions)
            self._set_status(f"Nice! {guess} appears {count} times." if count > 1
                             else f"Nice! There is one {guess}.", GOOD_INK)
        else:
            lives = game.lives_left
            left = "Last life!" if lives == 1 else f"{lives} lives left."
            what = f"No {guess} in this word." if outcome is Outcome.MISS else f"{guess} is not the word."
            self._set_status(f"{what} {left}", BAD)

    def _finish(self) -> None:
        game = self.game
        won = game.status is Status.WON
        if won:
            self.wins += 1
            self.streak += 1
            self.best_streak = max(self.best_streak, self.streak)
            flawless = " Flawless!" if game.misses == 0 else ""
            self._set_status(f"You got it! The word was {game.word}.{flawless} Press Enter to play again.", GOOD_INK)
        else:
            self.losses += 1
            self.streak = 0
            self._set_status(f"Out of lives. The word was {game.word}. Press Enter to try another.", BAD)

        self._tiles.finish(won)
        self._drawing.show(game.misses, game.status)
        for letter, style in self._key_styles.items():
            if style is KEY_IDLE:
                self._style_key(letter, KEY_LOCKED)
        self._render_stats()
        self.focus_set()  # so Enter starts the next round even after solving in the entry box

    # ------------------------------------------------------------- rendering

    def _style_key(self, letter: str, style: tuple) -> None:
        if self._key_styles[letter] is style:
            return
        self._key_styles[letter] = style
        fg, text_color, state = style
        self._keys[letter].configure(fg_color=fg, text_color=text_color,
                                     text_color_disabled=text_color, state=state)

    def _render_lives(self) -> None:
        lives = self.game.lives_left
        for index, heart in enumerate(self._hearts):
            alive = index < lives
            if self._hearts_alive[index] != alive:
                self._hearts_alive[index] = alive
                heart.configure(text_color=BAD if alive else FAINT)

    def _render_stats(self) -> None:
        self._stats.configure(text=f"Wins {self.wins}    Losses {self.losses}    "
                                   f"Streak {self.streak}    Best {self.best_streak}")

    def _clear_entry(self) -> None:
        # Only delete real text: deleting while the placeholder is showing erases the placeholder.
        if self._solve_entry.get():
            self._solve_entry.delete(0, "end")

    def _set_status(self, text: str, color: Color) -> None:
        if self._status_look != (text, color):
            self._status_look = (text, color)
            self._status.configure(text=text, text_color=color)

    # ---------------------------------------------------------------- events

    def _on_key(self, event: tk.Event) -> None:
        if isinstance(event.widget, tk.Entry) or event.state & self._shortcut_mask:
            return
        char = event.char
        if len(char) == 1 and char.isascii() and char.isalpha():
            self.guess_letter(char)

    def _on_return(self, event: tk.Event) -> None:
        if not isinstance(event.widget, tk.Entry) and self.game.status is not Status.PLAYING:
            self.new_game()

    def _on_solve(self, _event: tk.Event = None) -> str:
        text = self._solve_entry.get().strip()
        if text:
            if self.guess_word(text).outcome is not Outcome.INVALID:
                self._clear_entry()  # keep invalid text so it can be fixed
        elif self.game.status is Status.PLAYING:
            self._set_status("Type a word in the box first.", MUTED)
        else:
            self.new_game()
        return "break"

    def _on_click(self, event: tk.Event) -> None:
        # Clicking anywhere outside the entry box returns typing to letter guesses.
        if not isinstance(event.widget, tk.Entry):
            self.focus_set()

    def _toggle_theme(self) -> None:
        ctk.set_appearance_mode("dark" if self._dark_mode.get() else "light")


def main() -> None:
    HangmanApp().mainloop()


if __name__ == "__main__":
    main()
