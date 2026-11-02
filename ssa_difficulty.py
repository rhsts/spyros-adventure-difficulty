"""Difficulty picker for Skylanders: Spyro's Adventure (Wii, SSPP52 Rev 3) in Dolphin.

Needs the "Damage multiplier" Gecko code (make_gecko.py) enabled. The code keeps
its data right after the magic word 'SSA2': the multiplier (in 1/256 steps), the
HP ID and the player's flag word. This window finds that word in memory and
keeps the multiplier up to date while the game runs. It also reads
and writes the Skylander's HP directly for the HP bar, Refill and Regeneration.
  python ssa_difficulty.py
"""
import json, os, tkinter as tk
import numpy as np
from dolmem import Dolphin, view
from make_gecko import MAGIC, HP_ID, PLAYER_FLAG, ONE

MAX_ID = 0x12fc524a   # script int holding the Skylander's max HP
HUD_ID = 0x12fcc7dc   # HUD copy of HP; the game re-syncs it from the real HP when written
INT_VT = 0x80485f0c   # script int variable object; ID at +8, value at +0x20
REF_TAG = 0x806dfb38  # script reference object: [... ref ID, 3 funcs, REF_TAG, target]
ONE_SHOT = 1024 * ONE  # 1024x: any normal hit takes all HP, no 32-bit overflow
# Easy..Nightmare use the enemy damage scale of Imaginators' own difficulties
# (CGlobalTuningData._difficultyFixedEnemyDamageScale in permanent.pak:
# Beginner 0.4, Adventurer 1.0, Expert 1.8, Nightmare 3.5).
TAKEN = [  # name, multiplier in 1/256 steps, blurb, accent colour
    ("Invincible", 0, "No damage", "#3fb8c8"),
    ("Easy", round(0.4 * ONE), "0.4x damage", "#4caf7d"),
    ("Medium", ONE, "Normal game", "#4c8bf5"),
    ("Hard", round(1.8 * ONE), "1.8x damage", "#f0a030"),
    ("Nightmare", round(3.5 * ONE), "3.5x damage", "#e0504a"),
    ("One-shot", ONE_SHOT, "One hit kills", "#a05ae0"),
]
BG, CARD, TEXT, MUTED = "#16161c", "#22222b", "#ececf1", "#8a8a99"
SETTINGS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")


def find_data(d):
    """Address of the code's data block (just after 'SSAD'), or None."""
    # The code handler copies Gecko codes into low memory; scan the first 64 KB.
    v = view(np.frombuffer(d.read(0x80000000, 0x10000), dtype=np.uint8), "u32")
    hits = np.nonzero(v == MAGIC)[0]
    return 0x80000000 + 4 * int(hits[0]) + 4 if len(hits) else None


def find_vars(v, var_id):
    """Value addresses of every script int with this ID."""
    i = np.nonzero(v == var_id)[0]
    i = i[(i >= 2) & (v[i - 2] == INT_VT)]
    return [0x80000000 + 4 * int(x) + 0x18 for x in i]


def find_player_hp(v):
    """The player's HP object: the HP variable a script reference with the HP ID points to.

    Every enemy's HP has the same ID, but only the player's is referenced like this."""
    a = lambda p: (p - 0x80000000) // 4
    for x in np.nonzero(v == REF_TAG)[0]:
        target = int(v[x + 1])
        if (v[x - 4] == HP_ID and 0x80000000 <= target < 0x81800000
                and v[a(target)] == INT_VT and v[a(target) + 2] == HP_ID):
            return target
    return None


def regen_step(hp, max_hp):
    """HP after one second of regeneration: 1% of max, at least 1."""
    return min(max_hp, hp + max(1, max_hp // 100))


def load_settings():
    try:
        with open(SETTINGS) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


class App:
    def __init__(self, root):
        self.root, self.d, self.data = root, None, None
        self.player, self.max_addrs, self.hud_addrs, self.scan_in = None, [], [], 0
        self.prev_hp, self.hits, self.lost = None, 0, 0
        s = load_settings()
        # Older versions saved quarters under "taken"/"quarters" (one-shot even as
        # 1,000,000); convert them to 1/256 steps and cap.
        old = s.get("taken", s.get("quarters", 4)) * (ONE // 4)
        self.taken = min(s.get("taken256", old), ONE_SHOT)
        self.regen = tk.BooleanVar(value=s.get("regen", False))
        self.on_top = tk.BooleanVar(value=s.get("on_top", False))

        root.title("SSA Difficulty")
        root.configure(bg=BG, padx=20, pady=18)
        root.resizable(False, False)
        tk.Label(root, text="Spyro's Adventure", bg=BG, fg=TEXT,
                 font=("Segoe UI Semibold", 16)).pack(anchor="w")

        self.taken_cards, self.taken_scale = self.section("Damage your Skylander takes", TAKEN, "taken")

        # HP bar + actions
        self.hp_text = tk.Label(root, text="HP  -", bg=BG, fg=TEXT, font=("Segoe UI Semibold", 10))
        self.hp_text.pack(anchor="w", pady=(14, 0))
        self.bar = tk.Canvas(root, width=410, height=12, bg=CARD, highlightthickness=0)
        self.bar.pack(anchor="w", pady=(4, 8))
        self.fill = self.bar.create_rectangle(0, 0, 0, 12, fill="#4caf7d", width=0)

        row = tk.Frame(root, bg=BG)
        row.pack(fill="x")
        tk.Button(row, text="Refill HP", command=self.refill, bg=CARD, fg=TEXT, bd=0, padx=12, pady=4,
                  activebackground="#30303b", activeforeground=TEXT, font=("Segoe UI", 9),
                  cursor="hand2").pack(side="left")
        for text, var in (("Regeneration", self.regen), ("Always on top", self.on_top)):
            tk.Checkbutton(row, text=text, variable=var, command=self.save, bg=BG, fg=TEXT,
                           selectcolor=CARD, activebackground=BG, activeforeground=TEXT,
                           font=("Segoe UI", 9)).pack(side="left", padx=(12, 0))

        self.stats = tk.Label(root, bg=BG, fg=MUTED, font=("Segoe UI", 9), anchor="w")
        self.stats.pack(fill="x", pady=(10, 0))
        self.status = tk.Label(root, bg=BG, fg=MUTED, font=("Segoe UI", 9), anchor="w")
        self.status.pack(fill="x")

        self.choose("taken", self.taken)
        self.tick()
        self.regen_tick()

    def section(self, heading, presets, which):
        tk.Label(self.root, text=heading, bg=BG, fg=MUTED,
                 font=("Segoe UI", 10)).pack(anchor="w", pady=(12, 6))
        grid = tk.Frame(self.root, bg=BG)
        grid.pack(anchor="w")
        cols = 3 if len(presets) > 4 else 4
        width = 128 if cols == 3 else 94
        cards = {}
        for i, (name, q, blurb, accent) in enumerate(presets):
            card = tk.Frame(grid, bg=CARD, padx=10, pady=8, cursor="hand2", width=width, height=60,
                            highlightthickness=2, highlightbackground=CARD)
            card.grid(row=i // cols, column=i % cols, padx=3, pady=3)
            card.pack_propagate(False)
            title = tk.Label(card, text=name, bg=CARD, fg=accent, font=("Segoe UI Semibold", 11))
            sub = tk.Label(card, text=blurb, bg=CARD, fg=MUTED, font=("Segoe UI", 9))
            title.pack(anchor="w")
            sub.pack(anchor="w")
            for w in (card, title, sub):
                w.bind("<Button-1>", lambda e, q=q: self.choose(which, q))
            cards[q] = (card, accent)
        scale = tk.Scale(self.root, from_=0, to=8, resolution=0.05, orient="horizontal",
                         length=410, bg=BG, fg=TEXT, troughcolor=CARD, highlightthickness=0,
                         activebackground=TEXT, bd=0, font=("Segoe UI", 8), showvalue=True,
                         command=lambda x: self.choose(which, round(float(x) * ONE), from_scale=True))
        scale.pack(anchor="w")
        return cards, scale

    # --- settings -------------------------------------------------------------
    def choose(self, which, mult, from_scale=False):
        setattr(self, which, mult)
        cards, scale = self.taken_cards, self.taken_scale
        for q, (card, accent) in cards.items():
            card.config(highlightbackground=accent if q == mult else CARD)
        if not from_scale and mult != ONE_SHOT:
            scale.set(round(mult / ONE, 2))
        self.apply()
        self.save()

    def save(self):
        self.root.attributes("-topmost", self.on_top.get())
        try:
            with open(SETTINGS, "w") as f:
                json.dump({"taken256": self.taken, "regen": self.regen.get(),
                           "on_top": self.on_top.get()}, f)
        except OSError:
            pass  # settings are a convenience; the game keeps working without them

    @staticmethod
    def label(q):
        return "one-shot" if q == ONE_SHOT else f"{q / ONE:.2g}x"

    # --- game memory ----------------------------------------------------------
    def write(self, addr, value):
        self.d.write(addr, int(value).to_bytes(4, "big"))

    def read(self, a):
        return int.from_bytes(self.d.read(a, 4), "big")

    def apply(self):
        if self.data is not None:
            self.write(self.data, self.taken)

    def hp(self):
        """(hp, max) of the player, or None outside a level."""
        if not self.player or not self.max_addrs:
            return None
        return self.read(self.player + 0x20), self.read(self.max_addrs[0])

    def set_hp(self, value):
        # The game shows the new HP after the next pause. Also writing the HUD copy
        # makes it show at once, but that crashed the game, so it is left alone.
        self.write(self.player + 0x20, value)
        self.prev_hp = value

    def refill(self):
        if self.hp():
            self.set_hp(self.hp()[1])

    def regen_tick(self):
        if self.regen.get() and self.data is not None and self.hp():
            hp, mx = self.hp()
            if 0 < hp < mx:   # never revive a defeated Skylander
                self.set_hp(regen_step(hp, mx))
        self.root.after(1000, self.regen_tick)

    def tick(self):
        try:
            if self.data is None:
                self.d = Dolphin()
                self.data = find_data(self.d)
            if self.data is None:
                self.status.config(text="●  Gecko code not found - enable \"Damage multiplier\"", fg="#e0504a")
            elif self.d.read(self.data - 4, 4) != MAGIC.to_bytes(4, "big"):
                self.data = None  # game restarted; find the code again
            elif self.read(self.data + 4) != HP_ID or self.read(self.data + 8) != PLAYER_FLAG:
                # An older version of the code with another data layout; writing would break it.
                self.status.config(text="●  Old Gecko code loaded - restart the game", fg="#f0a030")
                self.data = None
            else:
                self.update_hp()
                self.apply()      # also re-applies after the game rebooted the code at 1x
                self.status.config(text=f"●  Active - {self.label(self.taken)} damage taken",
                                   fg="#4caf7d")
        except (SystemExit, OSError) as e:
            self.data = None
            self.status.config(text=f"●  {e or 'Waiting for Dolphin'}", fg=MUTED)
        self.root.after(250, self.tick)

    def update_hp(self):
        # Levels and figure swaps move the variables; rescan every 2 s.
        self.scan_in -= 1
        if self.scan_in <= 0:
            self.scan_in = 8
            v = view(self.d.mem1(), "u32")
            self.player = find_player_hp(v)
            self.max_addrs, self.hud_addrs = find_vars(v, MAX_ID), find_vars(v, HUD_ID)
        cur = self.hp()
        if not cur or not 0 < cur[1] <= 10000 or cur[0] > cur[1]:
            self.hp_text.config(text="HP  -   (not in a level)")
            self.bar.coords(self.fill, 0, 0, 0, 12)
            self.prev_hp = None
            return
        hp, mx = cur
        if self.prev_hp is not None and hp < self.prev_hp:
            self.hits += 1
            self.lost += self.prev_hp - hp
        self.prev_hp = hp
        frac = hp / mx
        colour = "#4caf7d" if frac > 0.5 else "#f0a030" if frac > 0.25 else "#e0504a"
        self.hp_text.config(text=f"HP  {hp} / {mx}")
        self.bar.coords(self.fill, 0, 0, 410 * frac, 12)
        self.bar.itemconfig(self.fill, fill=colour)
        self.stats.config(text=f"This session: {self.hits} hits taken, {self.lost} HP lost")


if __name__ == "__main__":
    import sys
    if sys.argv[1:] == ["test"]:
        assert regen_step(100, 400) == 104
        assert regen_step(399, 400) == 400
        assert regen_step(10, 50) == 11       # at least 1 HP
        print("ok")
    else:
        App(tk.Tk()).root.mainloop()
