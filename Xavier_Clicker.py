from __future__ import annotations
import json
import math
import random
import time
import tkinter as tk
from tkinter import messagebox
from typing import Dict, Any

SAVE_FILE = "xavier_clicker_save.json"
# Config File
CONFIG: Dict[str, Any] = {
    "friend_name": "Xavier",
    "emoji": "🐝",
    "click_name": "Pet",
    "point_name": "Xavs",
    "start_points": 0,
    "start_click_value": 1,
    "auto_save_seconds": 10,
    "flavor_lines": [
        "Xavier asked for snacks. You gave him 1 Xav.",
        "Xavier has opinions about your haircut.",
        "Xavier attempted to moonwalk and gained style points.",
        "Xavier sneezed. It was majestic.",
        "Xavier philosophized about sandwiches.",
    ],
    "upgrades": {
        "lazy_applause": {
            "name": "Lazy Applause",
            "emoji": "👏",
            "base_cost": 15,
            "base_cps": 0.2,
            "description": "Small encouragement — occasional clap.",
            "cost_mult": 1.15,
        },
        "meme_generator": {
            "name": "Meme Generator",
            "emoji": "📸",
            "base_cost": 100,
            "base_cps": 1.5,
            "description": "Spreads Xavier's legend.",
            "cost_mult": 1.18,
        },
        "energy_drink": {
            "name": "Energy Drink",
            "emoji": "⚡",
            "base_cost": 500,
            "base_cps": 8,
            "description": "Hyper Xavier automates tasks.",
            "cost_mult": 1.20,
        },
        "home_studio": {
            "name": "Home Studio",
            "emoji": "🎛️",
            "base_cost": 2500,
            "base_cps": 40,
            "description": "Xavier produces content non-stop.",
            "cost_mult": 1.22,
        },
    },
    "multipliers": {
        "coffee_rush": {
            "name": "Coffee Rush",
            "emoji": "☕",
            "cost": 250,
            "mult": 2.0,
            "duration_seconds": 20,
            "description": "Temporary double production.",
        }
    },
    "achievements": {
        "first_pet": {"title": "First Pet", "desc": "Pet Xavier once."},
        "century_clicks": {"title": "Century of Pets", "desc": "Pet Xavier 100 times."},
        "rich_xavier": {"title": "Rich Xavier", "desc": "Reach 10 000 Xavs."},
    },
    "rebirth_cost": 100_000,
    "rebirth_multiplier": 1.5,
    "max_rebirths": 3,
}

def format_num(v: float) -> str:
    try:
        n = float(v)
    except Exception:
        return str(v)
    if n == 0:
        return "0"
    if n < 1000:
        return f"{n:.2f}" if not float(n).is_integer() else str(int(n))
    suffixes = ["", "K", "M", "B", "T", "Q"]
    magnitude = min(int(math.floor(math.log10(abs(n)) / 3)), len(suffixes) - 1)
    val = n / (1000 ** magnitude)
    return f"{val:.2f}{suffixes[magnitude]}"

def default_state() -> Dict[str, Any]:
    return {
        "points": float(CONFIG["start_points"]),
        "click_value": float(CONFIG["start_click_value"]),
        "total_clicks": 0,
        "items": {k: 0 for k in CONFIG["upgrades"]},
        "active_multipliers": {},
        "achievements": [],
        "rebirths": 0,
        "hacks_unlocked": False,
        "fast_ticks": False,
        "created_at": time.time(),
    }

def load_state() -> Dict[str, Any]:
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            s = json.load(f)
            for k in CONFIG["upgrades"]:
                s.setdefault("items", {}).setdefault(k, 0)
            s.setdefault("rebirths", 0)
            s.setdefault("hacks_unlocked", False)
            s.setdefault("fast_ticks", False)
            return s
    except Exception:
        return default_state()

def save_state(state: Dict[str, Any]) -> None:
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print("Save failed:", e)

def cost_for(uid: str, owned: int) -> float:
    u = CONFIG["upgrades"][uid]
    return math.ceil(u["base_cost"] * (u.get("cost_mult", 1.15) ** owned))

def cps_for(uid: str, owned: int) -> float:
    return CONFIG["upgrades"][uid]["base_cps"] * owned

def total_cps(state: Dict[str, Any]) -> float:
    base = sum(cps_for(uid, cnt) for uid, cnt in state["items"].items())
    multi = 1.0
    now = time.time()
    expired = []
    for mid, expiry in list(state["active_multipliers"].items()):
        if expiry <= now:
            expired.append(mid)
        else:
            multi *= CONFIG["multipliers"].get(mid, {}).get("mult", 1.0)
    for e in expired:
        state["active_multipliers"].pop(e, None)
    multi *= CONFIG["rebirth_multiplier"] ** state.get("rebirths", 0)
    if state.get("fast_ticks"):
        multi *= 10.0
    return base * multi

def unlock_achievement(aid: str, state: Dict[str, Any], ui_callback) -> None:
    if aid in state["achievements"]:
        return
    state["achievements"].append(aid)
    info = CONFIG["achievements"].get(aid, {"title": aid, "desc": ""})
    ui_callback(f"🏆 {info['title']}: {info['desc']}")

def check_achievements(state: Dict[str, Any], ui_callback) -> None:
    if "first_pet" not in state["achievements"] and state["total_clicks"] >= 1:
        unlock_achievement("first_pet", state, ui_callback)
    if "century_clicks" not in state["achievements"] and state["total_clicks"] >= 100:
        unlock_achievement("century_clicks", state, ui_callback)
    if "rich_xavier" not in state["achievements"] and state["points"] >= 10_000:
        unlock_achievement("rich_xavier", state, ui_callback)

def maybe_random_event(state: Dict[str, Any], ui_callback) -> None:
    if random.random() < 0.06:
        line = random.choice(CONFIG["flavor_lines"])
        bonus = random.choice([0, 1, 2, 5])
        if bonus:
            state["points"] += bonus
            ui_callback(f"{line} (+{bonus} {CONFIG['point_name']})")
        else:
            ui_callback(line)

class XavierClickerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{CONFIG['friend_name']} Clicker — The Unofficial Saga")
        self.state = load_state()
        self.last_tick = time.time()
        self.ending_shown = False
        top = tk.Frame(root, pady=6)
        top.pack(fill=tk.X)
        self.points_var = tk.StringVar()
        self.cps_var = tk.StringVar()
        lbl_points = tk.Label(top, textvariable=self.points_var, font=("Helvetica", 24, "bold"))
        lbl_points.pack(anchor="w", padx=8)
        lbl_cps = tk.Label(top, textvariable=self.cps_var, font=("Helvetica", 10))
        lbl_cps.pack(anchor="w", padx=8)
        center = tk.Frame(root, pady=6)
        center.pack()
        self.click_btn = tk.Button(
            center,
            text=f"{CONFIG['emoji']} {CONFIG['click_name']} {CONFIG['friend_name']}",
            font=("Helvetica", 16),
            width=28,
            height=2,
            command=self.on_click,
        )
        self.click_btn.pack()
        self.flavor_var = tk.StringVar()
        tk.Label(root, textvariable=self.flavor_var, fg="darkgreen", pady=4).pack()
        main = tk.Frame(root)
        main.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)
        upgrades_container = tk.LabelFrame(main, text="Upgrades", padx=4, pady=4)
        upgrades_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        canvas = tk.Canvas(upgrades_container)
        vscroll = tk.Scrollbar(upgrades_container, orient="vertical", command=canvas.yview)
        self.upgrades_frame = tk.Frame(canvas)
        self.upgrades_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.upgrades_frame, anchor="nw")
        canvas.configure(yscrollcommand=vscroll.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vscroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.info_frame = tk.LabelFrame(main, text="Info & Actions", padx=6, pady=6)
        self.info_frame.pack(side=tk.LEFT, fill=tk.Y)
        self.upgrade_widgets = {}
        for uid, data in CONFIG["upgrades"].items():
            row = tk.Frame(self.upgrades_frame, pady=2)
            row.pack(fill=tk.X, padx=4)
            name = f"{data['emoji']} {data['name']}"
            tk.Label(row, text=name, width=20, anchor="w").pack(side=tk.LEFT)
            cost_lbl = tk.Label(row, text="", width=10)
            cost_lbl.pack(side=tk.LEFT)
            tk.Button(row, text="Buy", command=lambda u=uid: self.buy_upgrade(u)).pack(side=tk.LEFT, padx=6)
            owned_lbl = tk.Label(row, text="0", width=6)
            owned_lbl.pack(side=tk.LEFT)
            self.upgrade_widgets[uid] = {"cost": cost_lbl, "owned": owned_lbl}
        tk.Label(self.info_frame, text="Specials:").pack(anchor="w")
        for mid, m in CONFIG["multipliers"].items():
            tk.Button(
                self.info_frame,
                text=f"{m['emoji']} {m['name']} ({format_num(m['cost'])})",
                command=lambda m_id=mid: self.buy_multiplier(m_id),
            ).pack(fill=tk.X, pady=2)
        self.rebirth_preview_var = tk.StringVar()
        tk.Label(self.info_frame, textvariable=self.rebirth_preview_var, wraplength=220, justify="left").pack(pady=6)
        ctl = tk.Frame(self.info_frame)
        ctl.pack(pady=6)
        tk.Button(ctl, text="Save Now", command=lambda: save_state(self.state)).pack(side=tk.LEFT, padx=4)
        tk.Button(ctl, text="Reset", command=self.reset_save).pack(side=tk.LEFT, padx=4)
        self.rebirth_btn = tk.Button(self.info_frame, text="🔁 Rebirth", fg="purple", command=self.rebirth)
        self.rebirth_btn.pack(fill=tk.X, pady=4)
        self.ach_var = tk.StringVar()
        tk.Label(self.info_frame, textvariable=self.ach_var, wraplength=220, justify="left").pack(pady=4)
        self.fly_label = tk.Label(root, text="", fg="blue")
        self.fly_label.pack()
        self.cmd_frame = tk.Frame(root)
        self.cmd_entry = tk.Entry(self.cmd_frame, width=40)
        self.cmd_entry.pack(side=tk.LEFT, padx=4, pady=4)
        tk.Button(self.cmd_frame, text="Run", command=self.run_command).pack(side=tk.LEFT, padx=4)
        self.cmd_frame.pack_forget()
        self.hacks_frame = tk.LabelFrame(root, text="Hacks (unlocked)", padx=6, pady=6)
        self.hacks_frame.pack_forget()
        tk.Button(self.hacks_frame, text="Give 100k Xavs", command=lambda: self.add_points(100_000)).pack(fill=tk.X, pady=2)
        tk.Button(self.hacks_frame, text="Max All Upgrades", command=self.max_upgrades).pack(fill=tk.X, pady=2)
        self.fast_tick_btn = tk.Button(self.hacks_frame, text="Toggle Fast Ticks", command=self.toggle_fast_ticks)
        self.fast_tick_btn.pack(fill=tk.X, pady=2)
        root.bind_all("<Control-Shift-O>", lambda e: self.toggle_command_bar())
        self.update_rebirth_preview()
        self.update_points_labels()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self._tick_loop()
        self._autosave_loop()

    def update_points_labels(self) -> None:
        self.points_var.set(f"{format_num(self.state['points'])} {CONFIG['point_name']}")
        self.cps_var.set(f"CPS: {format_num(total_cps(self.state))}")
        for uid, widgets in self.upgrade_widgets.items():
            owned = self.state["items"].get(uid, 0)
            widgets["owned"].config(text=str(owned))
            widgets["cost"].config(text=format_num(cost_for(uid, owned)))
        achs = ", ".join(self.state.get("achievements", []) or ["—"])
        reb = self.state.get("rebirths", 0)
        self.ach_var.set(f"Rebirths: {reb}\nAchievements: {achs}")
        if self.state["points"] >= CONFIG["rebirth_cost"]:
            self.rebirth_btn.config(state="normal")
        else:
            self.rebirth_btn.config(state="disabled")
        if self.state.get("hacks_unlocked", False):
            self.hacks_frame.pack(fill=tk.X, padx=8, pady=6)
            self.fast_tick_btn.config(relief="sunken" if self.state.get("fast_ticks", False) else "raised")
        else:
            self.hacks_frame.pack_forget()
        if self.state.get("rebirths", 0) >= CONFIG["max_rebirths"] and not self.ending_shown:
            self.show_ending()

    def show_temporary(self, text: str, duration_ms: int = 2200) -> None:
        self.fly_label.config(text=text)
        self.root.after(duration_ms, lambda: self.fly_label.config(text=""))

    def on_click(self) -> None:
        mult = CONFIG["rebirth_multiplier"] ** self.state.get("rebirths", 0)
        now = time.time()
        for mid, expiry in list(self.state["active_multipliers"].items()):
            if expiry > now:
                mult *= CONFIG["multipliers"].get(mid, {}).get("mult", 1.0)
        if self.state.get("fast_ticks"):
            mult *= 10.0
        added = self.state.get("click_value", 1.0) * mult
        self.state["points"] += added
        self.state["total_clicks"] = self.state.get("total_clicks", 0) + 1
        self.update_points_labels()
        self.show_temporary(f"+{format_num(added)} {CONFIG['point_name']}")
        check_achievements(self.state, self.show_temporary)
        self.update_rebirth_preview()

    def buy_upgrade(self, uid: str) -> None:
        owned = self.state["items"].get(uid, 0)
        cost = cost_for(uid, owned)
        if self.state["points"] >= cost:
            self.state["points"] -= cost
            self.state["items"][uid] = owned + 1
            self.show_temporary(f"Bought {CONFIG['upgrades'][uid]['name']} — Xavier approves.")
        else:
            self.show_temporary("Not enough Xavs. Try giving snacks.")
        self.update_points_labels()
        self.update_rebirth_preview()

    def buy_multiplier(self, mid: str) -> None:
        m = CONFIG["multipliers"][mid]
        if self.state["points"] >= m["cost"]:
            self.state["points"] -= m["cost"]
            self.state["active_multipliers"][mid] = time.time() + m["duration_seconds"]
            self.show_temporary(f"{m['name']} active for {m['duration_seconds']}s!")
        else:
            self.show_temporary("Can't afford that right now.")
        self.update_points_labels()

    def update_rebirth_preview(self) -> None:
        current_cps = total_cps(self.state)
        future_rebirths = self.state.get("rebirths", 0) + 1
        multiplier_future = CONFIG["rebirth_multiplier"] ** future_rebirths
        base = sum(cps_for(u, c) for u, c in self.state["items"].items())
        future_cps = base * multiplier_future
        self.rebirth_preview_var.set(
            f"Rebirth cost: {format_num(CONFIG['rebirth_cost'])} {CONFIG['point_name']}\n"
            f"Current CPS: {format_num(current_cps)} → After rebirth CPS: {format_num(future_cps)}\n"
            f"Rebirths owned: {self.state.get('rebirths', 0)} / {CONFIG['max_rebirths']}"
        )

    def rebirth(self) -> None:
        if self.state["points"] < CONFIG["rebirth_cost"]:
            self.show_temporary("Not enough Xavs to trigger cosmic rebirth.")
            return
        self.state["rebirths"] = self.state.get("rebirths", 0) + 1
        reb = self.state["rebirths"]
        if reb >= CONFIG["max_rebirths"]:
            messagebox.showinfo("🏁 The Finale", "Xavier completes his final rebirth and becomes legend.\nEnjoy the ending!")
            self.state = default_state()
            self.state["rebirths"] = reb
        else:
            messagebox.showinfo(
                "Rebirth!",
                f"Xavier reincarnates. Permanent {CONFIG['rebirth_multiplier']}× production awarded.\n"
                f"You have {reb} rebirth(s).",
            )
            new_state = default_state()
            new_state["rebirths"] = reb
            new_state["hacks_unlocked"] = self.state.get("hacks_unlocked", False)
            new_state["fast_ticks"] = self.state.get("fast_ticks", False)
            self.state = new_state
        save_state(self.state)
        self.update_points_labels()
        self.update_rebirth_preview()

    def show_ending(self) -> None:
        self.ending_shown = True
        overlay = tk.Toplevel(self.root)
        overlay.title("🏁 Xavier Ascends")
        overlay.geometry("600x380")
        overlay.transient(self.root)
        overlay.grab_set()
        msg = tk.Label(
            overlay,
            text=(
                "✨ THE END ✨\n\n"
                "After mastering the arts of snacks and memes, Xavier ascends to a "
                "mythical plane of eternal chill. Thanks for playing.\n\n"
                "You may close this window; Xavier is busy ascending."
            ),
            font=("Helvetica", 14),
            justify="center",
            wraplength=520,
            padx=20,
            pady=20,
        )
        msg.pack(expand=True)
        tk.Button(overlay, text="Close", command=overlay.destroy).pack(pady=8)
        self.click_btn.config(state="disabled")
        self.rebirth_btn.config(state="disabled")

    def toggle_command_bar(self) -> None:
        if self.cmd_frame.winfo_ismapped():
            self.cmd_frame.pack_forget()
        else:
            self.cmd_frame.pack(fill=tk.X, padx=8)
            self.cmd_entry.focus_set()

    def run_command(self) -> None:
        cmd = self.cmd_entry.get().strip()
        self.cmd_entry.delete(0, tk.END)
        if not cmd:
            return
        if cmd == "OpenSesame":
            if not self.state.get("hacks_unlocked", False):
                self.state["hacks_unlocked"] = True
                self.show_temporary("Secret accepted. Hacks unlocked.")
            else:
                self.show_temporary("Hacks already unlocked. Use them wisely.")
            self.update_points_labels()
        else:
            self.show_temporary("Unknown command. Try again.")

    def add_points(self, amount: float) -> None:
        self.state["points"] = self.state.get("points", 0) + amount
        self.show_temporary(f"+{format_num(amount)} {CONFIG['point_name']}")
        self.update_points_labels()
        self.update_rebirth_preview()

    def max_upgrades(self) -> None:
        for uid in CONFIG["upgrades"]:
            self.state["items"][uid] = 999
        self.show_temporary("All upgrades maxed (999). Enjoy.")
        self.update_points_labels()
        self.update_rebirth_preview()

    def toggle_fast_ticks(self) -> None:
        current = self.state.get("fast_ticks", False)
        self.state["fast_ticks"] = not current
        self.show_temporary("Fast ticks " + ("enabled" if not current else "disabled"))
        self.update_points_labels()

    def _tick_loop(self) -> None:
        now = time.time()
        interval = 0.25 if self.state.get("fast_ticks") else 1.0
        if now - self.last_tick >= interval:
            gained = total_cps(self.state) * (interval if not self.state.get("fast_ticks") else 1.0)
            self.state["points"] += gained
            self.last_tick = now
            maybe_random_event(self.state, self.show_temporary)
            check_achievements(self.state, self.show_temporary)
            self.update_points_labels()
            self.update_rebirth_preview()
        self.root.after(200 if self.state.get("fast_ticks") else 500, self._tick_loop)

    def _autosave_loop(self) -> None:
        save_state(self.state)
        self.root.after(int(CONFIG["auto_save_seconds"] * 1000), self._autosave_loop)

    def reset_save(self) -> None:
        if messagebox.askyesno("Reset", "Delete save and restart?"):
            self.state = default_state()
            save_state(self.state)
            self.update_points_labels()
            self.show_temporary("Save reset. Xavier forgets everything.")

    def on_close(self) -> None:
        save_state(self.state)
        self.root.destroy()

def main() -> None:
    root = tk.Tk()
    root.geometry("760x560")
    app = XavierClickerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
