from datetime import datetime
import hashlib
import os
import random
import sqlite3
import string
import threading
import time
from flask import Flask, flash, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
# Persistent secret key so player & admin sessions survive server reloads
app.secret_key = os.environ.get(
    "NOVABETX_SECRET_KEY", "nvx_ultra_pro_max_99x_vault_secret_key_2026"
)

# Resolve absolute paths so PythonAnywhere WSGI workers always find betting.db & uploads
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

USE_MYSQL = False
if USE_MYSQL:
  import mysql.connector

  DB_CONFIG = {
      "host": "yourusername.mysql.pythonanywhere-services.com",
      "user": "yourusername",
      "password": "your_mysql_password",
      "database": "yourusername$betting",
  }
else:
  DB_NAME = os.path.join(BASE_DIR, "betting.db")

UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Thread lock for multiplayer live game state machines & in-memory cache
STATE_LOCK = threading.RLock()
SITE_SETTINGS_CACHE = {"data": None, "timestamp": 0.0}

# ==========================================
# STEALTH ADMIN CREDENTIALS & SECRET ROUTES
# ==========================================
ADMIN_USERNAME = "superadmin"
ADMIN_PASSWORD_HASH = generate_password_hash(
    "NavabetxAdmin99!", method="pbkdf2:sha256"
)

# Change these two paths anytime; url_for('admin_login') and url_for('admin') update automatically
SECRET_ADMIN_LOGIN_PATH = "/nvx-vault-99x-auth"
SECRET_ADMIN_PANEL_PATH = "/nvx-godmode-77x-panel"

GAMES_CATALOG = [
    {
        "id": "jetx",
        "route": "jetx_game",
        "title": "JetX Rocket",
        "category": "Crash",
        "icon": "fa-rocket",
        "color": "amber",
        "min_bet": 10,
    },
    {
        "id": "plinko",
        "route": "plinko_game",
        "title": "Plinko Ball",
        "category": "Instant Win",
        "icon": "fa-circle-nodes",
        "color": "pink",
        "min_bet": 10,
    },
    {
        "id": "blackjack",
        "route": "blackjack_game",
        "title": "Blackjack 21",
        "category": "Cards & Tables",
        "icon": "fa-heart",
        "color": "emerald",
        "min_bet": 10,
    },
    {
        "id": "roulette",
        "route": "roulette_game",
        "title": "European Roulette",
        "category": "Cards & Tables",
        "icon": "fa-circle-notch",
        "color": "red",
        "min_bet": 10,
    },
    {
        "id": "baccarat",
        "route": "baccarat_game",
        "title": "Baccarat Pro",
        "category": "Cards & Tables",
        "icon": "fa-diamond",
        "color": "blue",
        "min_bet": 10,
    },
    {
        "id": "craps",
        "route": "craps_game",
        "title": "Craps Street",
        "category": "Dice & Numbers",
        "icon": "fa-dice",
        "color": "orange",
        "min_bet": 10,
    },
    {
        "id": "poker",
        "route": "poker_game",
        "title": "Video Poker",
        "category": "Cards & Tables",
        "icon": "fa-crown",
        "color": "indigo",
        "min_bet": 10,
    },
    {
        "id": "andar_bahar",
        "route": "andar_bahar_game",
        "title": "Andar Bahar",
        "category": "Cards & Tables",
        "icon": "fa-layer-group",
        "color": "teal",
        "min_bet": 10,
    },
    {
        "id": "teen_patti",
        "route": "teen_patti_game",
        "title": "Teen Patti Live",
        "category": "Cards & Tables",
        "icon": "fa-shield-halved",
        "color": "yellow",
        "min_bet": 10,
    },
    {
        "id": "limbo",
        "route": "limbo_game",
        "title": "Limbo Rocket",
        "category": "Crash",
        "icon": "fa-arrow-trend-up",
        "color": "cyan",
        "min_bet": 10,
    },
    {
        "id": "aviator",
        "route": "aviator_game",
        "title": "Aviator",
        "category": "Crash",
        "icon": "fa-plane-up",
        "color": "red",
        "min_bet": 10,
    },
    {
        "id": "dragon_tiger",
        "route": "dragon_tiger_game",
        "title": "Dragon Tiger",
        "category": "Cards & Tables",
        "icon": "fa-dragon",
        "color": "yellow",
        "min_bet": 10,
    },
    {
        "id": "heads_tails",
        "route": "heads_tails_game",
        "title": "Heads v Tails",
        "category": "Instant Win",
        "icon": "fa-coins",
        "color": "slate",
        "min_bet": 10,
    },
    {
        "id": "color_prediction",
        "route": "color_prediction_game",
        "title": "Color Predict",
        "category": "Dice & Numbers",
        "icon": "fa-palette",
        "color": "purple",
        "min_bet": 10,
    },
    {
        "id": "mines",
        "route": "mines_game",
        "title": "Cyber Mines",
        "category": "Instant Win",
        "icon": "fa-bomb",
        "color": "cyan",
        "min_bet": 10,
    },
    {
        "id": "dice",
        "route": "dice_game",
        "title": "Digital Dice",
        "category": "Dice & Numbers",
        "icon": "fa-dice-d20",
        "color": "pink",
        "min_bet": 10,
    },
    {
        "id": "spin",
        "route": "spin_game",
        "title": "Daily Spin",
        "category": "Bonus",
        "icon": "fa-dharmachakra",
        "color": "indigo",
        "min_bet": 0,
    },
    {
        "id": "seven_up_down",
        "route": "seven_up_down_game",
        "title": "7 Up 7 Down",
        "category": "Dice & Numbers",
        "icon": "fa-dice",
        "color": "yellow",
        "min_bet": 10,
    },
    {
        "id": "penalty",
        "route": "penalty_game",
        "title": "Penalty Shootout",
        "category": "Instant Win",
        "icon": "fa-futbol",
        "color": "emerald",
        "min_bet": 10,
    },
    {
        "id": "hilo",
        "route": "hilo_game",
        "title": "Hi-Lo Cards",
        "category": "Cards & Tables",
        "icon": "fa-arrow-up-wide-short",
        "color": "cyan",
        "min_bet": 10,
    },
    {
        "id": "slots",
        "route": "slots_game",
        "title": "Neon 777 Slots",
        "category": "Crash",
        "icon": "fa-gem",
        "color": "pink",
        "min_bet": 10,
    },
    {
        "id": "thimbles",
        "route": "thimbles_game",
        "title": "Thimbles",
        "category": "Instant Win",
        "icon": "fa-cubes",
        "color": "amber",
        "min_bet": 10,
    },
    {
        "id": "tower",
        "route": "tower_game",
        "title": "Tower Climb",
        "category": "Crash",
        "icon": "fa-cubes-stacked",
        "color": "purple",
        "min_bet": 10,
    },
    {
        "id": "keno",
        "route": "keno_game",
        "title": "Classic Keno",
        "category": "Dice & Numbers",
        "icon": "fa-ticket",
        "color": "blue",
        "min_bet": 10,
    },
    {
        "id": "wheel",
        "route": "wheel_game",
        "title": "Turbo Wheel",
        "category": "Crash",
        "icon": "fa-circle-radiation",
        "color": "red",
        "min_bet": 10,
    },
    {
        "id": "jhandi_munda",
        "route": "jhandi_munda_game",
        "title": "Jhandi Munda",
        "category": "Dice & Numbers",
        "icon": "fa-crown",
        "color": "teal",
        "min_bet": 10,
    },
    {
        "id": "coin_field",
        "route": "coin_field_game",
        "title": "Coin Field",
        "category": "Instant Win",
        "icon": "fa-border-all",
        "color": "brand",
        "min_bet": 10,
    },
    {
        "id": "scratch",
        "route": "scratch_game",
        "title": "Scratch & Win",
        "category": "Instant Win",
        "icon": "fa-ticket",
        "color": "purple",
        "min_bet": 10,
    },
    {
        "id": "casino_war",
        "route": "casino_war_game",
        "title": "Casino War",
        "category": "Cards & Tables",
        "icon": "fa-khanda",
        "color": "red",
        "min_bet": 10,
    },
    {
        "id": "horse_racing",
        "route": "horse_racing_game",
        "title": "Virtual Racing",
        "category": "Arcade",
        "icon": "fa-horse",
        "color": "amber",
        "min_bet": 10,
    },
    {
        "id": "russian_roulette",
        "route": "russian_roulette_game",
        "title": "Russian Roulette",
        "category": "Crash",
        "icon": "fa-gun",
        "color": "gray",
        "min_bet": 10,
    },
    {
        "id": "safes",
        "route": "safes_game",
        "title": "Magic Safes",
        "category": "Instant Win",
        "icon": "fa-vault",
        "color": "yellow",
        "min_bet": 10,
    },
    {
        "id": "rps",
        "route": "rps_game",
        "title": "Ro-Sham-Bo",
        "category": "Arcade",
        "icon": "fa-hand-scissors",
        "color": "cyan",
        "min_bet": 10,
    },
    {
        "id": "red_dog",
        "route": "red_dog_game",
        "title": "Red Dog",
        "category": "Cards & Tables",
        "icon": "fa-dog",
        "color": "orange",
        "min_bet": 10,
    },
    {
        "id": "pharaoh_slot",
        "route": "pharaoh_slot_game",
        "title": "Pharaoh's Tomb",
        "category": "Slots",
        "icon": "fa-gem",
        "color": "amber",
        "min_bet": 10,
    },
    {
        "id": "hilo_dice",
        "route": "hilo_dice_game",
        "title": "Hi-Lo Dice",
        "category": "Dice & Numbers",
        "icon": "fa-dice-two",
        "color": "pink",
        "min_bet": 10,
    },
    {
        "id": "coin_streak",
        "route": "coin_streak_game",
        "title": "Coin Streak",
        "category": "Instant Win",
        "icon": "fa-coins",
        "color": "brand",
        "min_bet": 10,
    },
]

# Universal God Mode dictionary for all 37 games
ADMIN_GAME_CONTROL = {g["id"]: None for g in GAMES_CATALOG}
ADMIN_GAME_CONTROL.update(
    {"aviator": None, "jetx": None, "dt": None, "ht": None, "cp": None}
)


def get_ctrl(game_id):
  """Returns normalized lowercase control string ('win', 'loss') or exact value."""
  val = ADMIN_GAME_CONTROL.get(game_id)
  if isinstance(val, str):
    return val.lower()
  return val


AVIATOR_STATE = {
    "state": "WAITING",
    "start_time": time.time(),
    "crash_point": 0.00,
    "match_number": 1,
    "history": [],
}
ACTIVE_BETS = {}


def update_aviator_state():
  global AVIATOR_STATE, ACTIVE_BETS, ADMIN_GAME_CONTROL
  with STATE_LOCK:
    now = time.time()
    elapsed = now - AVIATOR_STATE["start_time"]
    if AVIATOR_STATE["state"] == "WAITING" and elapsed > 5.0:
      AVIATOR_STATE["state"] = "FLYING"
      AVIATOR_STATE["start_time"] = now
      ctrl = get_ctrl("aviator")
      if ctrl == "win":
        crash = round(random.uniform(5.00, 15.00), 2)
      elif ctrl == "loss":
        crash = 1.00
      elif ctrl is not None:
        crash = float(ctrl)
      else:
        rand = random.random()
        if rand < 0.60:
          crash = round(random.uniform(1.00, 1.49), 2)
        elif rand < 0.85:
          crash = round(random.uniform(1.50, 1.99), 2)
        elif rand < 0.95:
          crash = round(random.uniform(2.00, 5.00), 2)
        else:
          crash = round(random.uniform(5.01, 35.00), 2)
      AVIATOR_STATE["crash_point"] = crash
    elif AVIATOR_STATE["state"] == "FLYING":
      if 1.00 + (elapsed**1.4) * 0.08 >= AVIATOR_STATE["crash_point"]:
        AVIATOR_STATE["state"] = "CRASHED"
        AVIATOR_STATE["start_time"] = now
        AVIATOR_STATE["history"].insert(
            0,
            {
                "id": f"{AVIATOR_STATE['match_number']:06d}",
                "mult": AVIATOR_STATE["crash_point"],
            },
        )
        if len(AVIATOR_STATE["history"]) > 15:
          AVIATOR_STATE["history"].pop()
        ACTIVE_BETS.clear()
    elif AVIATOR_STATE["state"] == "CRASHED" and elapsed > 3.0:
      AVIATOR_STATE["state"] = "WAITING"
      AVIATOR_STATE["start_time"] = now
      AVIATOR_STATE["match_number"] += 1


JETX_STATE = {
    "state": "WAITING",
    "start_time": time.time(),
    "crash_point": 1.50,
    "match_number": 1,
}
JETX_BETS = {}


def update_jetx_state():
  global JETX_STATE, JETX_BETS, ADMIN_GAME_CONTROL
  with STATE_LOCK:
    now = time.time()
    elapsed = now - JETX_STATE["start_time"]
    if JETX_STATE["state"] == "WAITING" and elapsed > 5.0:
      JETX_STATE["state"] = "FLYING"
      JETX_STATE["start_time"] = now
      ctrl = get_ctrl("jetx")
      if ctrl == "win":
        JETX_STATE["crash_point"] = round(random.uniform(5.00, 15.00), 2)
      elif ctrl == "loss":
        JETX_STATE["crash_point"] = 1.00
      elif ctrl is not None:
        JETX_STATE["crash_point"] = float(ctrl)
      else:
        r = random.random()
        JETX_STATE["crash_point"] = round(
            1.01
            + (
                random.uniform(0.1, 15.0)
                if r > 0.4
                else random.uniform(0.01, 1.3)
            ),
            2,
        )
    elif JETX_STATE["state"] == "FLYING":
      if 1.00 + (elapsed**1.35) * 0.09 >= JETX_STATE["crash_point"]:
        JETX_STATE["state"] = "CRASHED"
        JETX_STATE["start_time"] = now
        JETX_BETS.clear()
    elif JETX_STATE["state"] == "CRASHED" and elapsed > 3.0:
      JETX_STATE["state"] = "WAITING"
      JETX_STATE["start_time"] = now
      JETX_STATE["match_number"] += 1


DT_STATE = {
    "state": "WAITING",
    "start_time": time.time(),
    "result": None,
    "d_card": 0,
    "t_card": 0,
    "match_number": 1,
    "history": [],
}
DT_BETS = {}


def update_dt_state():
  global DT_STATE, DT_BETS, ADMIN_GAME_CONTROL
  with STATE_LOCK:
    now = time.time()
    elapsed = now - DT_STATE["start_time"]
    if DT_STATE["state"] == "WAITING" and elapsed > 15.0:
      DT_STATE["state"] = "REVEAL"
      DT_STATE["start_time"] = now
      forced = ADMIN_GAME_CONTROL.get("dt") or ADMIN_GAME_CONTROL.get(
          "dragon_tiger"
      )
      f_low = forced.lower() if isinstance(forced, str) else None
      if f_low in ["dragon", "win"]:
        d_card = random.randint(3, 14)
        t_card = random.randint(2, d_card - 1)
        res = "Dragon"
      elif f_low in ["tiger", "loss"]:
        t_card = random.randint(3, 14)
        d_card = random.randint(2, t_card - 1)
        res = "Tiger"
      elif f_low == "tie":
        d_card = random.randint(2, 14)
        t_card = d_card
        res = "Tie"
      else:
        rand = random.random()
        if rand < 0.45:
          d_card = random.randint(3, 14)
          t_card = random.randint(2, d_card - 1)
          res = "Dragon"
        elif rand < 0.90:
          t_card = random.randint(3, 14)
          d_card = random.randint(2, t_card - 1)
          res = "Tiger"
        else:
          d_card = random.randint(2, 14)
          t_card = d_card
          res = "Tie"
      DT_STATE["d_card"], DT_STATE["t_card"], DT_STATE["result"] = (
          d_card,
          t_card,
          res,
      )
      DT_STATE["history"].insert(
          0, {"id": f"{DT_STATE['match_number']:06d}", "val": res}
      )
      if len(DT_STATE["history"]) > 15:
        DT_STATE["history"].pop()
      if DT_BETS:
        pending_payouts = list(DT_BETS.items())
        DT_BETS.clear()
        with get_db() as conn:
          for uid, bet in pending_payouts:
            if bet["target"] == res:
              conn.execute(
                  "UPDATE users SET balance = balance + ? WHERE id = ?",
                  (bet["stake"] * (8.0 if res == "Tie" else 2.0), uid),
              )
          conn.commit()
    elif DT_STATE["state"] == "REVEAL" and elapsed > 6.0:
      DT_STATE["state"] = "WAITING"
      DT_STATE["start_time"] = now
      DT_STATE["match_number"] += 1


HT_STATE = {
    "state": "WAITING",
    "start_time": time.time(),
    "result": None,
    "match_number": 1,
    "history": [],
}
HT_BETS = {}


def update_ht_state():
  global HT_STATE, HT_BETS, ADMIN_GAME_CONTROL
  with STATE_LOCK:
    now = time.time()
    elapsed = now - HT_STATE["start_time"]
    if HT_STATE["state"] == "WAITING" and elapsed > 12.0:
      HT_STATE["state"] = "FLIPPING"
      HT_STATE["start_time"] = now
      forced = ADMIN_GAME_CONTROL.get("ht") or ADMIN_GAME_CONTROL.get(
          "heads_tails"
      )
      f_low = forced.lower() if isinstance(forced, str) else None
      if f_low in ["heads", "win"]:
        res = "Heads"
      elif f_low in ["tails", "loss"]:
        res = "Tails"
      else:
        res = "Heads" if random.random() < 0.5 else "Tails"
      HT_STATE["result"] = res
      HT_STATE["history"].insert(
          0,
          {
              "id": f"{HT_STATE['match_number']:06d}",
              "val": "H" if res == "Heads" else "T",
          },
      )
      if len(HT_STATE["history"]) > 15:
        HT_STATE["history"].pop()
      if HT_BETS:
        pending_payouts = list(HT_BETS.items())
        HT_BETS.clear()
        with get_db() as conn:
          for uid, bet in pending_payouts:
            if bet["target"] == res:
              conn.execute(
                  "UPDATE users SET balance = balance + ? WHERE id = ?",
                  (bet["stake"] * 1.95, uid),
              )
          conn.commit()
    elif HT_STATE["state"] == "FLIPPING" and elapsed > 5.0:
      HT_STATE["state"] = "WAITING"
      HT_STATE["start_time"] = now
      HT_STATE["match_number"] += 1


CP_STATE = {
    "state": "WAITING",
    "start_time": time.time(),
    "result_number": -1,
    "result_color": "",
    "match_number": 1,
    "history": [],
}
CP_BETS = {}


def update_cp_state():
  global CP_STATE, CP_BETS, ADMIN_GAME_CONTROL
  with STATE_LOCK:
    now = time.time()
    elapsed = now - CP_STATE["start_time"]
    if CP_STATE["state"] == "WAITING" and elapsed > 30.0:
      CP_STATE["state"] = "REVEAL"
      CP_STATE["start_time"] = now
      forced = (
          ADMIN_GAME_CONTROL.get("cp")
          if ADMIN_GAME_CONTROL.get("cp") is not None
          else ADMIN_GAME_CONTROL.get("color_prediction")
      )
      f_low = forced.lower() if isinstance(forced, str) else forced
      if f_low == "win":
        res_num = 1
      elif f_low == "loss":
        res_num = 0
      elif isinstance(forced, int) or (
          isinstance(forced, str) and forced.isdigit()
      ):
        res_num = int(forced)
      else:
        res_num = random.randint(0, 9)
      res_color = (
          "Green"
          if res_num in [1, 3, 7, 9]
          else ("Red" if res_num in [2, 4, 6, 8] else "Violet")
      )
      CP_STATE["result_number"], CP_STATE["result_color"] = res_num, res_color
      CP_STATE["history"].insert(
          0,
          {
              "id": f"{CP_STATE['match_number']:06d}",
              "val": res_num,
              "col": res_color,
          },
      )
      if len(CP_STATE["history"]) > 15:
        CP_STATE["history"].pop()
      if CP_BETS:
        pending_payouts = list(CP_BETS.items())
        CP_BETS.clear()
        with get_db() as conn:
          for uid, bet in pending_payouts:
            target, stake, win = str(bet["target"]), bet["stake"], 0
            if target == str(res_num):
              win = stake * 9.0
            elif target == "Green" and res_color == "Green":
              win = stake * 2.0
            elif target == "Red" and res_color == "Red":
              win = stake * 2.0
            elif target == "Violet" and res_color == "Violet":
              win = stake * 4.5
            if win > 0:
              conn.execute(
                  "UPDATE users SET balance = balance + ? WHERE id = ?",
                  (win, uid),
              )
          conn.commit()
    elif CP_STATE["state"] == "REVEAL" and elapsed > 5.0:
      CP_STATE["state"] = "WAITING"
      CP_STATE["start_time"] = now
      CP_STATE["match_number"] += 1


# ==========================================
# SERVER-SIDE ACTIVE SESSION TRACKERS
# (Prevents Fake Cashout Exploits)
# ==========================================
ACTIVE_MINES = {}
ACTIVE_BLACKJACK = {}
ACTIVE_TOWER = {}
ACTIVE_RR = {}
ACTIVE_STREAK = {}
ACTIVE_COIN_FIELD = {}


def draw_card(rank=None):
  return {
      "rank": rank
      or random.choice(
          ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
      ),
      "suit": random.choice(["♠", "♥", "♦", "♣"]),
  }


def calc_hand(hand):
  val, aces = 0, 0
  for c in hand:
    if c["rank"] in ["J", "Q", "K"]:
      val += 10
    elif c["rank"] == "A":
      val += 11
      aces += 1
    else:
      val += int(c["rank"])
  while val > 21 and aces > 0:
    val -= 10
    aces -= 1
  return val


# ==========================================
# HIGH-CONCURRENCY DATABASE ENGINE (WAL + POOLING)
# ==========================================
class ManagedDBConnection:
  """Context-manager wrapper that commits/rolls back cleanly and reuses request-scoped connections."""

  def __init__(self, raw_conn, close_on_exit=False):
    self._conn = raw_conn
    self._close_on_exit = close_on_exit

  def __getattr__(self, name):
    return getattr(self._conn, name)

  def __enter__(self):
    return self._conn

  def __exit__(self, exc_type, exc_val, exc_tb):
    try:
      if exc_type is not None:
        self._conn.rollback()
      else:
        self._conn.commit()
    except Exception:
      pass
    if self._close_on_exit:
      try:
        self._conn.close()
      except Exception:
        pass
    return False


def _create_raw_connection():
  if USE_MYSQL:
    conn = mysql.connector.connect(**DB_CONFIG)
    conn.row_factory = lambda cursor, row: dict(
        zip([col[0] for col in cursor.description], row)
    )
    return conn
  conn = sqlite3.connect(DB_NAME, timeout=30.0, check_same_thread=False)
  conn.row_factory = sqlite3.Row
  # High-Concurrency SQLite Tuning for Multiplayer Performance
  conn.execute("PRAGMA journal_mode=WAL")
  conn.execute("PRAGMA synchronous=NORMAL")
  conn.execute("PRAGMA busy_timeout=30000")
  conn.execute("PRAGMA cache_size=-64000")  # 64MB RAM cache
  conn.execute("PRAGMA temp_store=MEMORY")
  conn.execute("PRAGMA mmap_size=268435456")  # 256MB memory-mapped I/O
  return conn


def get_db():
  try:
    # Reuse connection within the same Flask HTTP request
    if "_db_conn" not in g or g._db_conn is None:
      g._db_conn = _create_raw_connection()
    return ManagedDBConnection(g._db_conn, close_on_exit=False)
  except RuntimeError:
    # Outside request context (e.g., startup init_db)
    return ManagedDBConnection(_create_raw_connection(), close_on_exit=True)


@app.teardown_appcontext
def close_db_connection(exception=None):
  conn = g.pop("_db_conn", None)
  if conn is not None:
    try:
      conn.close()
    except Exception:
      pass


def init_db():
  if USE_MYSQL:
    return
  with get_db() as conn:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, mobile TEXT, balance REAL DEFAULT 0.00, bonus_balance REAL DEFAULT 0.00, status TEXT DEFAULT 'Pending', referrer_id INTEGER, total_wagered REAL DEFAULT 0.00)"""
    )
    try:
      conn.execute(
          "ALTER TABLE users ADD COLUMN total_wagered REAL DEFAULT 0.00"
      )
    except Exception:
      pass
    conn.execute(
        """CREATE TABLE IF NOT EXISTS matches (id INTEGER PRIMARY KEY AUTOINCREMENT, sport TEXT, league TEXT, team1 TEXT, team2 TEXT, score TEXT, status TEXT, odds1 REAL, oddsX REAL, odds2 REAL, is_live INTEGER DEFAULT 0)"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS bets (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, match_id INTEGER, match_name TEXT, team TEXT, odds REAL, stake REAL, profit REAL, match_status TEXT DEFAULT 'Open', date TEXT)"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS withdrawals (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, account_number TEXT, account_name TEXT, ifsc TEXT, bank_name TEXT, amount REAL, status TEXT DEFAULT 'Pending', date TEXT)"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS deposits (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, method TEXT, amount REAL, utr TEXT, screenshot TEXT, status TEXT DEFAULT 'Pending', date TEXT)"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS daily_spins (user_id INTEGER PRIMARY KEY, last_spin_time REAL)"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS site_settings (id INTEGER PRIMARY KEY AUTOINCREMENT, upi_id TEXT, bank_account TEXT, ifsc_code TEXT)"""
    )
    if not conn.execute("SELECT * FROM site_settings").fetchone():
      conn.execute(
          "INSERT INTO site_settings (upi_id, bank_account, ifsc_code) VALUES"
          " ('your_upi@okbank', 'Account Number Here', 'IFSC Code Here')"
      )

    # Non-destructive performance indexes for instant lookups under high player load
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_status ON users(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_bets_user_id ON bets(user_id)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_bets_match_status ON bets(match_id,"
        " match_status)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_deposits_user_status ON"
        " deposits(user_id, status)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_withdrawals_user_status ON"
        " withdrawals(user_id, status)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_matches_live ON matches(is_live,"
        " status)"
    )
    conn.commit()


@app.before_request
def verify_active_player_session():
  """Prevents 'None has no attribute balance' 500 crashes across all routes if betting.db is reset."""
  if request.endpoint in (
      "static",
      "login",
      "register",
      "fast_track_deposit",
      "logout",
      "admin_login",
      "admin",
      "decoy_admin_trap",
  ):
    return
  if "user_id" in session and not session.get("is_admin"):
    with get_db() as conn:
      u = conn.execute(
          "SELECT id FROM users WHERE id = ?", (session["user_id"],)
      ).fetchone()
      if not u:
        session.clear()
        if request.method == "POST" or request.is_json:
          return jsonify(
              {"success": False, "error": "Session expired. Please log in."}
          )
        flash(
            "Session expired or database reset. Please log in again.", "error"
        )
        return redirect(url_for("login"))


@app.context_processor
def inject_global_settings():
  now = time.time()
  if (
      SITE_SETTINGS_CACHE["data"] is not None
      and (now - SITE_SETTINGS_CACHE["timestamp"]) < 30.0
  ):
    return dict(site_settings=SITE_SETTINGS_CACHE["data"])
  try:
    with get_db() as conn:
      row = conn.execute(
          "SELECT * FROM site_settings ORDER BY id DESC LIMIT 1"
      ).fetchone()
      if row:
        SITE_SETTINGS_CACHE["data"] = dict(row)
        SITE_SETTINGS_CACHE["timestamp"] = now
      return dict(site_settings=row)
  except Exception:
    return dict(
        site_settings={
            "upi_id": "Updating...",
            "bank_account": "Updating...",
            "ifsc_code": "Updating...",
        }
    )


def deduct_stake(conn, user_id, stake, user_balance, user_bonus):
  if user_bonus >= stake:
    conn.execute(
        "UPDATE users SET bonus_balance = bonus_balance - ?, total_wagered ="
        " total_wagered + ? WHERE id = ?",
        (stake, stake, user_id),
    )
  else:
    conn.execute(
        "UPDATE users SET bonus_balance = 0, balance = balance - ?,"
        " total_wagered = total_wagered + ? WHERE id = ?",
        (stake - user_bonus, stake, user_id),
    )


# ==========================================
# CUSTOM 404 ERROR HANDLER & DECOY TRAPS
# ==========================================
def render_404_response():
  try:
    return render_template("404.html"), 404
  except Exception:
    return (
        """<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>404 - Page Not Found</title><script src="https://cdn.tailwindcss.com"></script></head><body class="bg-[#06090e] text-white min-h-screen flex items-center justify-center p-6 text-center"><div class="max-w-md bg-[#0f141d] border border-gray-800 rounded-3xl p-8 shadow-2xl"><div class="text-6xl font-black text-[#1CDA3A] font-mono mb-2">404</div><h1 class="text-xl font-black uppercase tracking-wider mb-2">Page Not Found</h1><p class="text-xs text-gray-400 mb-6">The page you are looking for does not exist or has been moved.</p><a href="/" class="inline-block bg-[#1CDA3A] text-black font-black text-xs uppercase tracking-wider px-6 py-3 rounded-xl">Back to Home</a></div></body></html>""",
        404,
    )


@app.errorhandler(404)
def page_not_found(e):
  return render_404_response()


# Decoy routes: Anyone probing /admin, /admin_login, /admin_dashboard, or /wp-admin gets a 404
@app.route("/admin", methods=["GET", "POST"])
@app.route("/admin_login", methods=["GET", "POST"])
@app.route("/admin_dashboard", methods=["GET", "POST"])
@app.route("/wp-admin", methods=["GET", "POST"])
def decoy_admin_trap():
  return render_404_response()


# ==========================================
# AUTH & USER ACCOUNT ROUTES
# ==========================================
@app.route("/", methods=["GET", "POST"])
def login():
  if "user_id" in session:
    return redirect(url_for("admin" if session.get("is_admin") else "home"))
  if request.method == "POST":
    with get_db() as conn:
      user = conn.execute(
          "SELECT * FROM users WHERE username = ?", (request.form["username"],)
      ).fetchone()
      if user and check_password_hash(
          user["password"], request.form["password"]
      ):
        if user["status"] == "Pending":
          flash("Account pending admin approval.", "error")
          return redirect(url_for("login"))
        session["user_id"], session["username"], session["is_admin"] = (
            user["id"],
            user["username"],
            False,
        )
        return redirect(url_for("home"))
      flash("Invalid credentials.", "error")
  return render_template("login.html")


@app.route("/register", methods=["POST"])
def register():
  username, mobile = (
      request.form["username"].strip(),
      request.form["mobile"].strip(),
  )
  pwd, cpwd = request.form["password"], request.form["confirm_password"]
  ref = request.form.get("referral_code", "").strip()
  if pwd != cpwd:
    flash("Passwords don't match!", "error")
    return redirect(url_for("login"))
  with get_db() as conn:
    if conn.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone():
      flash("Username exists.", "error")
      return redirect(url_for("login"))
    referrer = (
        conn.execute(
            "SELECT id FROM users WHERE username = ?", (ref,)
        ).fetchone()
        if ref
        else None
    )
    cursor = conn.execute(
        'INSERT INTO users (username, password, mobile, status, referrer_id)'
        ' VALUES (?, ?, ?, "Pending", ?)',
        (
            username,
            generate_password_hash(pwd, method="pbkdf2:sha256"),
            mobile,
            referrer["id"] if referrer else None,
        ),
    )
    conn.commit()
    flash(str(cursor.lastrowid), "fast_track")
  return redirect(url_for("login"))


@app.route("/fast_track_deposit", methods=["POST"])
def fast_track_deposit():
  try:
    uid, amt = int(request.form["user_id"]), float(request.form["amount"])
    if amt <= 0:
      raise ValueError
  except Exception:
    flash("Invalid deposit amount.", "error")
    return redirect(url_for("login"))
  utr = request.form["utr"].strip()
  file = request.files.get("screenshot")
  fname = (
      secure_filename(f"{uid}_{int(time.time())}_{file.filename}")
      if file
      else ""
  )
  if fname:
    file.save(os.path.join(app.config["UPLOAD_FOLDER"], fname))
  with get_db() as conn:
    conn.execute(
        'INSERT INTO deposits (user_id, method, amount, utr, screenshot,'
        ' status, date) VALUES (?, "First Deposit", ?, ?, ?, "Pending", ?)',
        (uid, amt, utr, fname, datetime.now().strftime("%Y-%m-%d %H:%M")),
    )
    conn.commit()
    flash("Payment proof submitted! Admin will verify.", "success")
  return redirect(url_for("login"))


@app.route("/logout")
def logout():
  session.clear()
  return redirect(url_for("login"))


@app.route("/home")
def home():
  if "user_id" not in session or session.get("is_admin"):
    return redirect(url_for("login"))
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
    if not u:
      session.clear()
      flash("Session expired or database reset. Please log in again.", "error")
      return redirect(url_for("login"))
    l = conn.execute(
        "SELECT * FROM matches WHERE is_live = 1 AND (status IS NULL OR status"
        ' NOT LIKE "Winner:%") LIMIT 4'
    ).fetchall()
    p = conn.execute(
        "SELECT * FROM matches WHERE is_live = 0 AND (status IS NULL OR status"
        ' NOT LIKE "Winner:%") LIMIT 10'
    ).fetchall()
  return render_template("index.html", live_matches=l, popular_matches=p, user=u)


@app.route("/games")
def games():
  if "user_id" not in session or session.get("is_admin"):
    return redirect(url_for("login"))
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return render_template("games.html", user=u, games_catalog=GAMES_CATALOG)


@app.route("/profile")
def profile():
  if "user_id" not in session or session.get("is_admin"):
    return redirect(url_for("login"))
  with get_db() as conn:
    user = conn.execute(
        "SELECT * FROM users WHERE id = ?", (session["user_id"],)
    ).fetchone()
    tot_dep = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) as total FROM deposits WHERE user_id ="
        " ? AND status = 'Approved'",
        (session["user_id"],),
    ).fetchone()["total"]
    curr_w = (
        user["total_wagered"]
        if "total_wagered" in user.keys() and user["total_wagered"] is not None
        else 0.0
    )
    effective_vip = max(curr_w + tot_dep, user["balance"] + curr_w)
    if effective_vip > curr_w:
      conn.execute(
          "UPDATE users SET total_wagered = ? WHERE id = ?",
          (effective_vip, session["user_id"]),
      )
      conn.commit()
      user = conn.execute(
          "SELECT * FROM users WHERE id = ?", (session["user_id"],)
      ).fetchone()
    bc = conn.execute(
        "SELECT COUNT(*) as count FROM bets WHERE user_id = ?",
        (session["user_id"],),
    ).fetchone()
    dep = conn.execute(
        "SELECT * FROM deposits WHERE user_id = ? ORDER BY id DESC",
        (session["user_id"],),
    ).fetchall()
    wit = conn.execute(
        "SELECT * FROM withdrawals WHERE user_id = ? ORDER BY id DESC",
        (session["user_id"],),
    ).fetchall()
    has_dep = (
        conn.execute(
            "SELECT COUNT(*) as count FROM deposits WHERE user_id = ? AND"
            " status = 'Approved'",
            (session["user_id"],),
        ).fetchone()["count"]
        > 0
    )
  return render_template(
      "profile.html",
      user=user,
      bet_count=bc["count"],
      deposits=dep,
      withdrawals=wit,
      has_deposited=has_dep,
  )


@app.route("/update_profile", methods=["POST"])
def update_profile():
  if "user_id" not in session:
    return redirect(url_for("login"))
  mobile = request.form.get("mobile", "").strip()
  old_password, new_password = request.form.get(
      "old_password", ""
  ), request.form.get("new_password", "")
  with get_db() as conn:
    user = conn.execute(
        "SELECT * FROM users WHERE id = ?", (session["user_id"],)
    ).fetchone()
    if new_password:
      if not check_password_hash(user["password"], old_password):
        flash("Security Alert: Incorrect current password!", "error")
        return redirect(url_for("profile"))
      conn.execute(
          "UPDATE users SET mobile = ?, password = ? WHERE id = ?",
          (
              mobile,
              generate_password_hash(new_password, method="pbkdf2:sha256"),
              session["user_id"],
          ),
      )
      flash("Vault secured! Password & Profile updated.", "success")
    else:
      conn.execute(
          "UPDATE users SET mobile = ? WHERE id = ?",
          (mobile, session["user_id"]),
      )
      flash("Profile details updated successfully!", "success")
    conn.commit()
  return redirect(url_for("profile"))


@app.route("/my_bets")
def my_bets():
  if "user_id" not in session or session.get("is_admin"):
    return redirect(url_for("login"))
  with get_db() as conn:
    user = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
    bets = conn.execute(
        "SELECT * FROM bets WHERE user_id = ? ORDER BY id DESC",
        (session["user_id"],),
    ).fetchall()
  return render_template("my_bets.html", bets=bets, user=user)


@app.route("/claim_referral", methods=["POST"])
def claim_referral():
  if "user_id" not in session:
    return redirect(url_for("login"))
  ref = request.form.get("referral_code", "").strip()
  with get_db() as conn:
    if not USE_MYSQL:
      conn.execute("BEGIN IMMEDIATE")
    user = conn.execute(
        "SELECT * FROM users WHERE id = ?", (session["user_id"],)
    ).fetchone()
    if user["referrer_id"]:
      flash("Bonus already claimed!", "error")
      return redirect(url_for("profile"))
    if user["username"].lower() == ref.lower():
      flash("Cannot use your own code!", "error")
      return redirect(url_for("profile"))
    referrer = conn.execute(
        "SELECT * FROM users WHERE username = ? COLLATE NOCASE", (ref,)
    ).fetchone()
    if not referrer:
      flash("Invalid referral code.", "error")
      return redirect(url_for("profile"))
    conn.execute(
        "UPDATE users SET bonus_balance = bonus_balance + 50 WHERE id = ?",
        (referrer["id"],),
    )
    conn.execute(
        "UPDATE users SET bonus_balance = bonus_balance + 50, referrer_id = ?"
        " WHERE id = ?",
        (referrer["id"], session["user_id"]),
    )
    conn.commit()
    flash("₹50 Referral Bonus Applied!", "success")
  return redirect(url_for("profile"))


@app.route("/deposit", methods=["POST"])
def deposit():
  if "user_id" not in session:
    return redirect(url_for("login"))
  try:
    amt = float(request.form["amount"])
    if amt < 10:
      raise ValueError
  except Exception:
    flash("Invalid minimum amount.", "error")
    return redirect(url_for("profile"))
  file = request.files.get("screenshot")
  fname = (
      secure_filename(f"{session['user_id']}_{int(time.time())}_{file.filename}")
      if file
      else ""
  )
  if fname:
    file.save(os.path.join(app.config["UPLOAD_FOLDER"], fname))
  with get_db() as conn:
    conn.execute(
        'INSERT INTO deposits (user_id, method, amount, utr, screenshot,'
        ' status, date) VALUES (?, ?, ?, ?, ?, "Pending", ?)',
        (
            session["user_id"],
            request.form["method"],
            amt,
            request.form["utr"],
            fname,
            datetime.now().strftime("%Y-%m-%d %H:%M"),
        ),
    )
    conn.commit()
    flash("Deposit submitted for admin approval.", "success")
  return redirect(url_for("profile"))


@app.route("/withdraw", methods=["POST"])
def withdraw():
  if "user_id" not in session:
    return redirect(url_for("login"))
  try:
    amt = float(request.form["amount"])
    if amt < 50:
      raise ValueError
  except Exception:
    flash("Minimum withdrawal is ₹50.", "error")
    return redirect(url_for("profile"))
  with get_db() as conn:
    if not USE_MYSQL:
      conn.execute("BEGIN IMMEDIATE")
    if (
        conn.execute(
            "SELECT COUNT(*) as count FROM deposits WHERE user_id = ? AND"
            " status = 'Approved'",
            (session["user_id"],),
        ).fetchone()["count"]
        == 0
    ):
      flash("Must deposit first to unlock withdrawals!", "error")
      return redirect(url_for("profile"))
    user = conn.execute(
        "SELECT balance FROM users WHERE id = ?", (session["user_id"],)
    ).fetchone()
    if user["balance"] < amt:
      flash("Insufficient REAL balance!", "error")
    else:
      conn.execute(
          "UPDATE users SET balance = balance - ? WHERE id = ?",
          (amt, session["user_id"]),
      )
      conn.execute(
          "INSERT INTO withdrawals (user_id, account_number, account_name,"
          ' ifsc, bank_name, amount, status, date) VALUES (?, ?, ?, ?, ?, ?,'
          ' "Pending", ?)',
          (
              session["user_id"],
              request.form["account_number"],
              request.form["account_name"],
              request.form["ifsc"],
              request.form["bank_name"],
              amt,
              datetime.now().strftime("%Y-%m-%d %H:%M"),
          ),
      )
      conn.commit()
      flash("Withdrawal request submitted successfully!", "success")
  return redirect(url_for("profile"))


@app.route("/place_bet", methods=["POST"])
def place_bet():
  if "user_id" not in session or session.get("is_admin"):
    return jsonify({"success": False, "error": "Unauthorized"})
  data = request.json
  try:
    mid, team, odds, stake = (
        int(data.get("match_id")),
        data.get("team").strip(),
        float(data.get("odds")),
        float(data.get("stake")),
    )
    if stake < 10:
      raise ValueError
  except Exception:
    return jsonify({"success": False, "error": "Invalid bet details."})
  with get_db() as conn:
    if not USE_MYSQL:
      conn.execute("BEGIN IMMEDIATE")
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
    if (u["balance"] + u["bonus_balance"]) < stake:
      return jsonify({"success": False, "error": "Insufficient balance!"})
    match = conn.execute(
        "SELECT team1, team2 FROM matches WHERE id = ?", (mid,)
    ).fetchone()
    deduct_stake(conn, session["user_id"], stake, u["balance"], u["bonus_balance"])
    conn.execute(
        "INSERT INTO bets (user_id, match_id, match_name, team, odds, stake,"
        ' profit, match_status, date) VALUES (?, ?, ?, ?, ?, ?, ?, "Open", ?)',
        (
            session["user_id"],
            mid,
            f"{match['team1']} vs {match['team2']}" if match else f"ID: {mid}",
            team,
            odds,
            stake,
            (odds * stake) - stake,
            datetime.now().strftime("%Y-%m-%d %H:%M"),
        ),
    )
    conn.commit()
    un = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return jsonify(
      {"success": True, "new_total": un["balance"] + un["bonus_balance"]}
  )


# ==========================================
# 5. ALL 37 GAME ROUTES (GOD MODE + SECURED)
# ==========================================


@app.route("/spin")
def spin_game():
  if "user_id" not in session:
    return redirect(url_for("login"))
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
    spin_data = conn.execute(
        "SELECT last_spin_time FROM daily_spins WHERE user_id = ?",
        (session["user_id"],),
    ).fetchone()
    can_spin, time_left = True, 0
    if spin_data:
      elapsed = time.time() - spin_data["last_spin_time"]
      if elapsed < 86400:
        can_spin, time_left = False, int(86400 - elapsed)
    return render_template(
        "spin.html", user=u, can_spin=can_spin, time_left=time_left
    )


@app.route("/spin/claim", methods=["POST"])
def spin_claim():
  if "user_id" not in session:
    return jsonify({"success": False})
  uid = session["user_id"]
  with get_db() as conn:
    if not USE_MYSQL:
      conn.execute("BEGIN IMMEDIATE")
    spin_data = conn.execute(
        "SELECT last_spin_time FROM daily_spins WHERE user_id = ?", (uid,)
    ).fetchone()
    if spin_data and (time.time() - spin_data["last_spin_time"]) < 86400:
      return jsonify({"success": False, "error": "Already spun!"})
    ctrl = get_ctrl("spin")
    if ctrl == "win":
      prize = 500
    elif ctrl == "loss":
      prize = 0
    else:
      rand = random.random()
      prize = (
          500
          if rand < 0.01
          else 50
          if rand < 0.10
          else 10
          if rand < 0.40
          else 5
          if rand < 0.85
          else 0
      )
    if prize > 0:
      conn.execute(
          "UPDATE users SET bonus_balance = bonus_balance + ? WHERE id = ?",
          (prize, uid),
      )
    if spin_data:
      conn.execute(
          "UPDATE daily_spins SET last_spin_time = ? WHERE user_id = ?",
          (time.time(), uid),
      )
    else:
      conn.execute(
          "INSERT INTO daily_spins (user_id, last_spin_time) VALUES (?, ?)",
          (uid, time.time()),
      )
    conn.commit()
    un = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?", (uid,)
    ).fetchone()
  return jsonify({
      "success": True,
      "prize": prize,
      "new_total": un["balance"] + un["bonus_balance"],
  })


@app.route("/aviator")
def aviator_game():
  if "user_id" not in session:
    return redirect(url_for("login"))
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return render_template("aviator.html", user=u)


@app.route("/aviator/sync")
def aviator_sync():
  update_aviator_state()
  return jsonify({
      "state": AVIATOR_STATE["state"],
      "elapsed": time.time() - AVIATOR_STATE["start_time"],
      "crash_point": (
          AVIATOR_STATE["crash_point"]
          if AVIATOR_STATE["state"] == "CRASHED"
          else None
      ),
      "history": AVIATOR_STATE["history"],
      "match_number": f"{AVIATOR_STATE['match_number']:06d}",
  })


@app.route("/aviator/bet", methods=["POST"])
def aviator_bet():
  if "user_id" not in session:
    return jsonify({"success": False})
  update_aviator_state()
  try:
    stake = float(request.json.get("stake", 0))
  except Exception:
    return jsonify({"success": False})
  if stake < 10:
    return jsonify({"success": False, "error": "Min bet 10"})
  with STATE_LOCK:
    if AVIATOR_STATE["state"] != "WAITING" or session["user_id"] in ACTIVE_BETS:
      return jsonify({"success": False, "error": "Closed"})
    with get_db() as conn:
      u = conn.execute(
          "SELECT balance, bonus_balance FROM users WHERE id = ?",
          (session["user_id"],),
      ).fetchone()
      if (u["balance"] + u["bonus_balance"]) < stake:
        return jsonify({"success": False, "error": "Insufficient balance"})
      deduct_stake(
          conn, session["user_id"], stake, u["balance"], u["bonus_balance"]
      )
      conn.commit()
      ACTIVE_BETS[session["user_id"]] = stake
      un = conn.execute(
          "SELECT balance, bonus_balance FROM users WHERE id = ?",
          (session["user_id"],),
      ).fetchone()
  return jsonify(
      {"success": True, "new_total": un["balance"] + un["bonus_balance"]}
  )


@app.route("/aviator/cashout", methods=["POST"])
def aviator_cashout():
  if "user_id" not in session:
    return jsonify({"success": False})
  update_aviator_state()
  with STATE_LOCK:
    if (
        AVIATOR_STATE["state"] != "FLYING"
        or session["user_id"] not in ACTIVE_BETS
    ):
      return jsonify({"success": False})
    m = 1.00 + ((time.time() - AVIATOR_STATE["start_time"]) ** 1.4) * 0.08
    if m >= AVIATOR_STATE["crash_point"]:
      return jsonify({"success": False})
    win = round(ACTIVE_BETS.pop(session["user_id"]) * m, 2)
  with get_db() as conn:
    conn.execute(
        "UPDATE users SET balance = balance + ? WHERE id = ?",
        (win, session["user_id"]),
    )
    conn.commit()
    un = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return jsonify({
      "success": True,
      "new_total": un["balance"] + un["bonus_balance"],
      "winnings": win,
      "multiplier": m,
  })


@app.route("/jetx")
def jetx_game():
  if "user_id" not in session:
    return redirect(url_for("login"))
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return render_template("jetx.html", user=u)


@app.route("/jetx/sync")
def jetx_sync():
  update_jetx_state()
  elapsed = time.time() - JETX_STATE["start_time"]
  current_mult = (
      round(1.00 + (elapsed**1.35) * 0.09, 2)
      if JETX_STATE["state"] == "FLYING"
      else 1.00
  )
  return jsonify({
      "state": JETX_STATE["state"],
      "multiplier": current_mult,
      "match_number": f"{JETX_STATE['match_number']:06d}",
      "crash_point": (
          JETX_STATE["crash_point"]
          if JETX_STATE["state"] == "CRASHED"
          else None
      ),
  })


@app.route("/jetx/bet", methods=["POST"])
def jetx_bet():
  if "user_id" not in session:
    return jsonify({"success": False})
  update_jetx_state()
  try:
    stake = float(request.json.get("stake", 0))
  except Exception:
    return jsonify({"success": False})
  if stake < 10:
    return jsonify({"success": False})
  with STATE_LOCK:
    if JETX_STATE["state"] != "WAITING":
      return jsonify({"success": False})
    with get_db() as conn:
      u = conn.execute(
          "SELECT balance, bonus_balance FROM users WHERE id = ?",
          (session["user_id"],),
      ).fetchone()
      if (u["balance"] + u["bonus_balance"]) < stake:
        return jsonify({"success": False})
      deduct_stake(
          conn, session["user_id"], stake, u["balance"], u["bonus_balance"]
      )
      conn.commit()
      JETX_BETS[session["user_id"]] = stake
      un = conn.execute(
          "SELECT balance, bonus_balance FROM users WHERE id = ?",
          (session["user_id"],),
      ).fetchone()
  return jsonify(
      {"success": True, "new_total": un["balance"] + un["bonus_balance"]}
  )


@app.route("/jetx/cashout", methods=["POST"])
def jetx_cashout():
  if "user_id" not in session:
    return jsonify({"success": False})
  update_jetx_state()
  with STATE_LOCK:
    if session["user_id"] not in JETX_BETS or JETX_STATE["state"] != "FLYING":
      return jsonify({"success": False})
    elapsed = time.time() - JETX_STATE["start_time"]
    mult = round(1.00 + (elapsed**1.35) * 0.09, 2)
    if mult >= JETX_STATE["crash_point"]:
      return jsonify({"success": False})
    winnings = round(JETX_BETS.pop(session["user_id"]) * mult, 2)
  with get_db() as conn:
    conn.execute(
        "UPDATE users SET balance = balance + ? WHERE id = ?",
        (winnings, session["user_id"]),
    )
    conn.commit()
    un = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return jsonify({
      "success": True,
      "winnings": winnings,
      "new_total": un["balance"] + un["bonus_balance"],
      "multiplier": mult,
  })


@app.route("/plinko")
def plinko_game():
  if "user_id" not in session:
    return redirect(url_for("login"))
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return render_template("plinko.html", user=u)


@app.route("/plinko/drop", methods=["POST"])
def plinko_drop():
  if "user_id" not in session:
    return jsonify({"success": False})
  try:
    stake = float(request.json.get("stake", 0))
  except Exception:
    return jsonify({"success": False})
  if stake < 10:
    return jsonify({"success": False})
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
    if (u["balance"] + u["bonus_balance"]) < stake:
      return jsonify({"success": False})
    deduct_stake(conn, session["user_id"], stake, u["balance"], u["bonus_balance"])
    ctrl = get_ctrl("plinko")
    if ctrl == "win":
      path = [random.choice([0, 1])] * 12
    elif ctrl == "loss":
      path = [0] * 6 + [1] * 6
      random.shuffle(path)
    else:
      path = [random.choice([0, 1]) for _ in range(12)]
    slot = sum(path)
    mult = [16, 9, 2, 1.4, 1.1, 1, 0.5, 1, 1.1, 1.4, 2, 9, 16][slot]
    winnings = round(stake * mult, 2)
    if winnings > 0:
      conn.execute(
          "UPDATE users SET balance = balance + ? WHERE id = ?",
          (winnings, session["user_id"]),
      )
    conn.commit()
    un = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return jsonify({
      "success": True,
      "path": path,
      "slot": slot,
      "multiplier": mult,
      "winnings": winnings,
      "new_total": un["balance"] + un["bonus_balance"],
  })


@app.route("/blackjack")
def blackjack_game():
  if "user_id" not in session:
    return redirect(url_for("login"))
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return render_template("blackjack.html", user=u)


@app.route("/blackjack/deal", methods=["POST"])
def bj_deal():
  uid = session.get("user_id")
  if not uid:
    return jsonify({"success": False})
  try:
    stake = float(request.json.get("stake", 0))
  except Exception:
    return jsonify({"success": False})
  if stake < 10:
    return jsonify({"success": False})
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?", (uid,)
    ).fetchone()
    if (u["balance"] + u["bonus_balance"]) < stake:
      return jsonify({"success": False})
    deduct_stake(conn, uid, stake, u["balance"], u["bonus_balance"])
    conn.commit()
    ctrl = get_ctrl("blackjack")
    if ctrl == "win":
      p, d = [draw_card("10"), draw_card("A")], [draw_card("9"), draw_card("7")]
    elif ctrl == "loss":
      p, d = [draw_card("10"), draw_card("6")], [
          draw_card("10"),
          draw_card("A"),
      ]
    else:
      p, d = [draw_card(), draw_card()], [draw_card(), draw_card()]
    ACTIVE_BLACKJACK[uid] = {
        "stake": stake,
        "player": p,
        "dealer": d,
        "status": "PLAYING",
    }
    un = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?", (uid,)
    ).fetchone()
  return jsonify({
      "success": True,
      "player": p,
      "player_score": calc_hand(p),
      "dealer_up": d[0],
      "new_total": un["balance"] + un["bonus_balance"],
  })


@app.route("/blackjack/hit", methods=["POST"])
def bj_hit():
  uid = session.get("user_id")
  if uid not in ACTIVE_BLACKJACK:
    return jsonify({"success": False})
  g_state = ACTIVE_BLACKJACK[uid]
  ctrl = get_ctrl("blackjack")
  if ctrl == "loss":
    g_state["player"].append(draw_card("K"))
  elif ctrl == "win":
    need = max(2, min(10, 21 - calc_hand(g_state["player"])))
    g_state["player"].append(draw_card(str(need)))
  else:
    g_state["player"].append(draw_card())
  s = calc_hand(g_state["player"])
  if s > 21:
    del ACTIVE_BLACKJACK[uid]
  return jsonify({
      "success": True,
      "player": g_state["player"] if s <= 21 else [],
      "score": s,
      "bust": s > 21,
  })


@app.route("/blackjack/stand", methods=["POST"])
def bj_stand():
  uid = session.get("user_id")
  if uid not in ACTIVE_BLACKJACK:
    return jsonify({"success": False})
  g_state = ACTIVE_BLACKJACK.pop(uid)
  p_s, d_s = calc_hand(g_state["player"]), calc_hand(g_state["dealer"])
  ctrl = get_ctrl("blackjack")
  if ctrl == "win" and d_s >= p_s:
    g_state["dealer"] = [g_state["dealer"][0], draw_card("6"), draw_card("K")]
    d_s = calc_hand(g_state["dealer"])
  elif ctrl == "loss" and d_s < p_s:
    g_state["dealer"] = [
        g_state["dealer"][0],
        draw_card("A")
        if calc_hand([g_state["dealer"][0], draw_card("A")]) <= 21
        else draw_card("10"),
    ]
    d_s = max(p_s + 1, min(21, calc_hand(g_state["dealer"])))
  else:
    while d_s < 17:
      g_state["dealer"].append(draw_card())
      d_s = calc_hand(g_state["dealer"])
  win, push, mult = False, False, 2.0
  if p_s <= 21 and (d_s > 21 or p_s > d_s):
    win = True
  elif p_s == d_s:
    push = True
  w = (g_state["stake"] * mult) if win else (g_state["stake"] if push else 0)
  with get_db() as conn:
    if w > 0:
      conn.execute(
          "UPDATE users SET balance = balance + ? WHERE id = ?", (w, uid)
      )
    conn.commit()
    un = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?", (uid,)
    ).fetchone()
  return jsonify({
      "success": True,
      "dealer": g_state["dealer"],
      "dealer_score": d_s,
      "win": win,
      "push": push,
      "winnings": w,
      "new_total": un["balance"] + un["bonus_balance"],
  })


@app.route("/roulette")
def roulette_game():
  if "user_id" not in session:
    return redirect(url_for("login"))
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return render_template("roulette.html", user=u)


@app.route("/roulette/spin", methods=["POST"])
def roulette_spin():
  if "user_id" not in session:
    return jsonify({"success": False})
  try:
    stake = float(request.json.get("stake", 0))
  except Exception:
    return jsonify({"success": False})
  bet_type, target = request.json.get("type"), request.json.get("target")
  if stake < 10:
    return jsonify({"success": False})
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
    if (u["balance"] + u["bonus_balance"]) < stake:
      return jsonify({"success": False})
    deduct_stake(conn, session["user_id"], stake, u["balance"], u["bonus_balance"])
    reds = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
    blacks = [x for x in range(1, 37) if x not in reds]
    ctrl = get_ctrl("roulette")
    if ctrl == "win":
      if bet_type == "number":
        r_num = int(target)
      elif bet_type == "red":
        r_num = random.choice(reds)
      elif bet_type == "black":
        r_num = random.choice(blacks)
      elif bet_type == "even":
        r_num = random.choice([x for x in range(2, 37, 2)])
      else:
        r_num = random.choice([x for x in range(1, 36, 2)])
    elif ctrl == "loss":
      r_num = 0 if bet_type != "number" or int(target) != 0 else 1
    else:
      r_num = random.randint(0, 36)
    col = "red" if r_num in reds else ("black" if r_num != 0 else "green")
    win, p = False, 0
    if bet_type == "number" and int(target) == r_num:
      win, p = True, stake * 36
    elif bet_type == "red" and col == "red":
      win, p = True, stake * 2
    elif bet_type == "black" and col == "black":
      win, p = True, stake * 2
    elif bet_type == "even" and r_num != 0 and r_num % 2 == 0:
      win, p = True, stake * 2
    elif bet_type == "odd" and r_num % 2 != 0:
      win, p = True, stake * 2
    if win:
      conn.execute(
          "UPDATE users SET balance = balance + ? WHERE id = ?",
          (p, session["user_id"]),
      )
    conn.commit()
    un = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return jsonify({
      "success": True,
      "number": r_num,
      "color": col,
      "win": win,
      "winnings": p,
      "new_total": un["balance"] + un["bonus_balance"],
  })


@app.route("/baccarat")
def baccarat_game():
  if "user_id" not in session:
    return redirect(url_for("login"))
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return render_template("baccarat.html", user=u)


@app.route("/baccarat/deal", methods=["POST"])
def baccarat_deal():
  if "user_id" not in session:
    return jsonify({"success": False})
  try:
    stake = float(request.json.get("stake", 0))
  except Exception:
    return jsonify({"success": False})
  choice = request.json.get("choice")
  if stake < 10:
    return jsonify({"success": False})
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
    if (u["balance"] + u["bonus_balance"]) < stake:
      return jsonify({"success": False})
    deduct_stake(conn, session["user_id"], stake, u["balance"], u["bonus_balance"])
    ctrl = get_ctrl("baccarat")
    if ctrl == "win":
      if choice == "Player":
        p_val, b_val = 9, 5
      elif choice == "Banker":
        p_val, b_val = 4, 9
      else:
        p_val = b_val = 8
    elif ctrl == "loss":
      if choice == "Player":
        p_val, b_val = 3, 8
      else:
        p_val, b_val = 8, 2
    else:
      p_val = (random.randint(1, 9) + random.randint(1, 9)) % 10
      b_val = (random.randint(1, 9) + random.randint(1, 9)) % 10
    out = "Tie" if p_val == b_val else ("Player" if p_val > b_val else "Banker")
    win = out == choice
    p = (
        (stake * (8.0 if out == "Tie" else (1.95 if out == "Banker" else 2.0)))
        if win
        else 0
    )
    if win:
      conn.execute(
          "UPDATE users SET balance = balance + ? WHERE id = ?",
          (p, session["user_id"]),
      )
    conn.commit()
    un = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return jsonify({
      "success": True,
      "player_score": p_val,
      "banker_score": b_val,
      "winner": out,
      "win": win,
      "winnings": p,
      "new_total": un["balance"] + un["bonus_balance"],
  })


@app.route("/craps")
def craps_game():
  if "user_id" not in session:
    return redirect(url_for("login"))
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return render_template("craps.html", user=u)


@app.route("/craps/roll", methods=["POST"])
def craps_roll():
  if "user_id" not in session:
    return jsonify({"success": False})
  try:
    stake = float(request.json.get("stake", 0))
  except Exception:
    return jsonify({"success": False})
  choice = request.json.get("choice")
  if stake < 10:
    return jsonify({"success": False})
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
    if (u["balance"] + u["bonus_balance"]) < stake:
      return jsonify({"success": False})
    deduct_stake(conn, session["user_id"], stake, u["balance"], u["bonus_balance"])
    ctrl = get_ctrl("craps")
    if ctrl == "win":
      d1, d2 = (4, 3) if choice == "Pass" else (1, 1)
    elif ctrl == "loss":
      d1, d2 = (1, 2) if choice == "Pass" else (4, 3)
    else:
      d1, d2 = random.randint(1, 6), random.randint(1, 6)
    tot = d1 + d2
    win = (tot in [7, 11]) if choice == "Pass" else (tot in [2, 3, 12])
    p = (stake * 2.0) if win else 0
    if win:
      conn.execute(
          "UPDATE users SET balance = balance + ? WHERE id = ?",
          (p, session["user_id"]),
      )
    conn.commit()
    un = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return jsonify({
      "success": True,
      "dice1": d1,
      "dice2": d2,
      "total": tot,
      "win": win,
      "winnings": p,
      "new_total": un["balance"] + un["bonus_balance"],
  })


@app.route("/poker")
def poker_game():
  if "user_id" not in session:
    return redirect(url_for("login"))
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return render_template("poker.html", user=u)


@app.route("/poker/play", methods=["POST"])
def poker_play():
  if "user_id" not in session:
    return jsonify({"success": False})
  try:
    stake = float(request.json.get("stake", 0))
  except Exception:
    return jsonify({"success": False})
  if stake < 10:
    return jsonify({"success": False})
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
    if (u["balance"] + u["bonus_balance"]) < stake:
      return jsonify({"success": False})
    deduct_stake(conn, session["user_id"], stake, u["balance"], u["bonus_balance"])
    ctrl = get_ctrl("poker")
    if ctrl == "win":
      c = [
          draw_card("A"),
          draw_card("A"),
          draw_card("A"),
          draw_card("K"),
          draw_card("K"),
      ]
    elif ctrl == "loss":
      c = [
          draw_card("2"),
          draw_card("5"),
          draw_card("7"),
          draw_card("9"),
          draw_card("J"),
      ]
    else:
      c = [draw_card() for _ in range(5)]
    r = [card["rank"] for card in c]
    mult, h_n = 0, "High Card (No Win)"
    if any(r.count(x) == 4 for x in r):
      mult, h_n = 25, "Four of a Kind"
    elif any(r.count(x) == 3 for x in r) and any(r.count(x) == 2 for x in r):
      mult, h_n = 9, "Full House"
    elif any(r.count(x) == 3 for x in r):
      mult, h_n = 3, "Three of a Kind"
    elif [r.count(x) for x in r].count(2) == 4:
      mult, h_n = 2, "Two Pair"
    elif any(x in ["J", "Q", "K", "A"] and r.count(x) == 2 for x in r):
      mult, h_n = 1.5, "Jacks or Better"
    w = round(stake * mult, 2)
    if w > 0:
      conn.execute(
          "UPDATE users SET balance = balance + ? WHERE id = ?",
          (w, session["user_id"]),
      )
    conn.commit()
    un = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return jsonify({
      "success": True,
      "cards": c,
      "hand": h_n,
      "multiplier": mult,
      "winnings": w,
      "new_total": un["balance"] + un["bonus_balance"],
  })


@app.route("/andar_bahar")
def andar_bahar_game():
  if "user_id" not in session:
    return redirect(url_for("login"))
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return render_template("andar_bahar.html", user=u)


@app.route("/andar_bahar/deal", methods=["POST"])
def andar_bahar_deal():
  if "user_id" not in session:
    return jsonify({"success": False})
  try:
    stake = float(request.json.get("stake", 0))
  except Exception:
    return jsonify({"success": False})
  side = request.json.get("side")
  if stake < 10:
    return jsonify({"success": False})
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
    if (u["balance"] + u["bonus_balance"]) < stake:
      return jsonify({"success": False})
    deduct_stake(conn, session["user_id"], stake, u["balance"], u["bonus_balance"])
    j = draw_card()
    ctrl = get_ctrl("andar_bahar")
    if ctrl == "win":
      w_s = side
    elif ctrl == "loss":
      w_s = "Bahar" if side == "Andar" else "Andar"
    else:
      w_s = random.choice(["Andar", "Bahar"])
    win = side == w_s
    w = round(stake * 1.95, 2) if win else 0
    if win:
      conn.execute(
          "UPDATE users SET balance = balance + ? WHERE id = ?",
          (w, session["user_id"]),
      )
    conn.commit()
    un = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return jsonify({
      "success": True,
      "joker": j,
      "winner": w_s,
      "win": win,
      "winnings": w,
      "new_total": un["balance"] + un["bonus_balance"],
  })


@app.route("/teen_patti")
def teen_patti_game():
  if "user_id" not in session:
    return redirect(url_for("login"))
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return render_template("teen_patti.html", user=u)


@app.route("/teen_patti/play", methods=["POST"])
def teen_patti_play():
  if "user_id" not in session:
    return jsonify({"success": False})
  try:
    stake = float(request.json.get("stake", 0))
  except Exception:
    return jsonify({"success": False})
  if stake < 10:
    return jsonify({"success": False})
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
    if (u["balance"] + u["bonus_balance"]) < stake:
      return jsonify({"success": False})
    deduct_stake(conn, session["user_id"], stake, u["balance"], u["bonus_balance"])
    p_c, d_c = [draw_card() for _ in range(3)], [draw_card() for _ in range(3)]
    ctrl = get_ctrl("teen_patti")
    win = (
        True
        if ctrl == "win"
        else (False if ctrl == "loss" else (random.random() < 0.48))
    )
    w = round(stake * 1.95, 2) if win else 0
    if win:
      conn.execute(
          "UPDATE users SET balance = balance + ? WHERE id = ?",
          (w, session["user_id"]),
      )
    conn.commit()
    un = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return jsonify({
      "success": True,
      "player": p_c,
      "dealer": d_c,
      "win": win,
      "winnings": w,
      "new_total": un["balance"] + un["bonus_balance"],
  })


@app.route("/limbo")
def limbo_game():
  if "user_id" not in session:
    return redirect(url_for("login"))
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return render_template("limbo.html", user=u)


@app.route("/limbo/play", methods=["POST"])
def limbo_play():
  if "user_id" not in session:
    return jsonify({"success": False})
  try:
    stake, target = float(request.json.get("stake", 0)), float(
        request.json.get("target", 2.0)
    )
  except Exception:
    return jsonify({"success": False})
  if stake < 10 or target < 1.01 or target > 1000:
    return jsonify({"success": False})
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
    if (u["balance"] + u["bonus_balance"]) < stake:
      return jsonify({"success": False})
    deduct_stake(conn, session["user_id"], stake, u["balance"], u["bonus_balance"])
    ctrl = get_ctrl("limbo")
    if ctrl == "win":
      roll = round(target + random.uniform(0.2, 3.0), 2)
    elif ctrl == "loss":
      roll = round(max(1.00, target - random.uniform(0.05, 0.5)), 2)
    else:
      roll = round(
          random.uniform(
              1.00, target * 1.5 if random.random() > 0.52 else target * 0.9
          ),
          2,
      )
    win = roll >= target
    w = round(stake * target, 2) if win else 0
    if win:
      conn.execute(
          "UPDATE users SET balance = balance + ? WHERE id = ?",
          (w, session["user_id"]),
      )
    conn.commit()
    un = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return jsonify({
      "success": True,
      "roll": roll,
      "target": target,
      "win": win,
      "winnings": w,
      "new_total": un["balance"] + un["bonus_balance"],
  })


@app.route("/dragon_tiger")
def dragon_tiger_game():
  if "user_id" not in session:
    return redirect(url_for("login"))
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return render_template("dragon_tiger.html", user=u)


@app.route("/dragon_tiger/sync")
def dragon_tiger_sync():
  update_dt_state()
  return jsonify({
      "state": DT_STATE["state"],
      "elapsed": time.time() - DT_STATE["start_time"],
      "d_card": DT_STATE["d_card"] if DT_STATE["state"] == "REVEAL" else 0,
      "t_card": DT_STATE["t_card"] if DT_STATE["state"] == "REVEAL" else 0,
      "result": DT_STATE["result"] if DT_STATE["state"] == "REVEAL" else None,
      "history": DT_STATE["history"],
      "match_number": f"{DT_STATE['match_number']:06d}",
  })


@app.route("/dragon_tiger/bet", methods=["POST"])
def dragon_tiger_bet():
  if "user_id" not in session:
    return jsonify({"success": False})
  update_dt_state()
  try:
    stake = float(request.json.get("stake", 0))
  except Exception:
    return jsonify({"success": False})
  target = request.json.get("target")
  with STATE_LOCK:
    if (
        stake < 10
        or target not in ["Dragon", "Tiger", "Tie"]
        or DT_STATE["state"] != "WAITING"
        or session["user_id"] in DT_BETS
    ):
      return jsonify({"success": False})
    with get_db() as conn:
      u = conn.execute(
          "SELECT balance, bonus_balance FROM users WHERE id = ?",
          (session["user_id"],),
      ).fetchone()
      if (u["balance"] + u["bonus_balance"]) < stake:
        return jsonify({"success": False})
      deduct_stake(
          conn, session["user_id"], stake, u["balance"], u["bonus_balance"]
      )
      conn.commit()
      un = conn.execute(
          "SELECT balance, bonus_balance FROM users WHERE id = ?",
          (session["user_id"],),
      ).fetchone()
      DT_BETS[session["user_id"]] = {"target": target, "stake": stake}
  return jsonify(
      {"success": True, "new_total": un["balance"] + un["bonus_balance"]}
  )


@app.route("/heads_tails")
def heads_tails_game():
  if "user_id" not in session:
    return redirect(url_for("login"))
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return render_template("heads_tails.html", user=u)


@app.route("/heads_tails/sync")
def heads_tails_sync():
  update_ht_state()
  return jsonify({
      "state": HT_STATE["state"],
      "elapsed": time.time() - HT_STATE["start_time"],
      "result": HT_STATE["result"] if HT_STATE["state"] == "FLIPPING" else None,
      "history": HT_STATE["history"],
      "match_number": f"{HT_STATE['match_number']:06d}",
  })


@app.route("/heads_tails/bet", methods=["POST"])
def heads_tails_bet():
  if "user_id" not in session:
    return jsonify({"success": False})
  update_ht_state()
  try:
    stake = float(request.json.get("stake", 0))
  except Exception:
    return jsonify({"success": False})
  target = request.json.get("target")
  with STATE_LOCK:
    if (
        stake < 10
        or target not in ["Heads", "Tails"]
        or HT_STATE["state"] != "WAITING"
        or session["user_id"] in HT_BETS
    ):
      return jsonify({"success": False})
    with get_db() as conn:
      u = conn.execute(
          "SELECT balance, bonus_balance FROM users WHERE id = ?",
          (session["user_id"],),
      ).fetchone()
      if (u["balance"] + u["bonus_balance"]) < stake:
        return jsonify({"success": False})
      deduct_stake(
          conn, session["user_id"], stake, u["balance"], u["bonus_balance"]
      )
      conn.commit()
      un = conn.execute(
          "SELECT balance, bonus_balance FROM users WHERE id = ?",
          (session["user_id"],),
      ).fetchone()
      HT_BETS[session["user_id"]] = {"target": target, "stake": stake}
  return jsonify(
      {"success": True, "new_total": un["balance"] + un["bonus_balance"]}
  )


@app.route("/color_prediction")
def color_prediction_game():
  if "user_id" not in session:
    return redirect(url_for("login"))
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return render_template("color_prediction.html", user=u)


@app.route("/color_prediction/sync")
def color_prediction_sync():
  update_cp_state()
  return jsonify({
      "state": CP_STATE["state"],
      "elapsed": time.time() - CP_STATE["start_time"],
      "result_number": (
          CP_STATE["result_number"] if CP_STATE["state"] == "REVEAL" else -1
      ),
      "result_color": (
          CP_STATE["result_color"] if CP_STATE["state"] == "REVEAL" else ""
      ),
      "history": CP_STATE["history"],
      "match_number": f"{CP_STATE['match_number']:06d}",
  })


@app.route("/color_prediction/bet", methods=["POST"])
def color_prediction_bet():
  if "user_id" not in session:
    return jsonify({"success": False})
  update_cp_state()
  try:
    stake = float(request.json.get("stake", 0))
  except Exception:
    return jsonify({"success": False})
  target = request.json.get("target")
  with STATE_LOCK:
    if (
        stake < 10
        or CP_STATE["state"] != "WAITING"
        or session["user_id"] in CP_BETS
    ):
      return jsonify({"success": False})
    with get_db() as conn:
      u = conn.execute(
          "SELECT balance, bonus_balance FROM users WHERE id = ?",
          (session["user_id"],),
      ).fetchone()
      if (u["balance"] + u["bonus_balance"]) < stake:
        return jsonify({"success": False})
      deduct_stake(
          conn, session["user_id"], stake, u["balance"], u["bonus_balance"]
      )
      conn.commit()
      un = conn.execute(
          "SELECT balance, bonus_balance FROM users WHERE id = ?",
          (session["user_id"],),
      ).fetchone()
      CP_BETS[session["user_id"]] = {"target": target, "stake": stake}
  return jsonify(
      {"success": True, "new_total": un["balance"] + un["bonus_balance"]}
  )


@app.route("/mines")
def mines_game():
  if "user_id" not in session:
    return redirect(url_for("login"))
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return render_template("mines.html", user=u)


@app.route("/mines/start", methods=["POST"])
def mines_start():
  if "user_id" not in session:
    return jsonify({"success": False})
  uid = session["user_id"]
  try:
    stake, mines_count = float(request.json.get("stake", 0)), int(
        request.json.get("mines", 3)
    )
  except Exception:
    return jsonify({"success": False})
  if stake < 10 or mines_count not in [3, 5, 10] or uid in ACTIVE_MINES:
    return jsonify({"success": False})
  client_seed = request.json.get("client_seed", "novabetx_player")
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?", (uid,)
    ).fetchone()
    if (u["balance"] + u["bonus_balance"]) < stake:
      return jsonify({"success": False})
    deduct_stake(conn, uid, stake, u["balance"], u["bonus_balance"])
    conn.commit()
    un = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?", (uid,)
    ).fetchone()
    server_seed = "".join(
        random.choices(string.ascii_letters + string.digits, k=16)
    )
    server_hash = hashlib.sha256(server_seed.encode()).hexdigest()
    # Thread-safe isolated RNG instance so concurrent players never collide
    local_rng = random.Random(f"{server_seed}-{client_seed}")
    grid = [0] * 25
    for i in local_rng.sample(range(25), mines_count):
      grid[i] = 1
    ACTIVE_MINES[uid] = {
        "grid": grid,
        "stake": stake,
        "mines": mines_count,
        "cleared": 0,
        "server_seed": server_seed,
        "clicked": [],
    }
  return jsonify({
      "success": True,
      "new_total": un["balance"] + un["bonus_balance"],
      "server_hash": server_hash,
  })


@app.route("/mines/click", methods=["POST"])
def mines_click():
  if "user_id" not in session:
    return jsonify({"success": False})
  uid = session["user_id"]
  try:
    idx = int(request.json.get("index"))
  except Exception:
    return jsonify({"success": False})
  if idx < 0 or idx > 24 or uid not in ACTIVE_MINES:
    return jsonify({"success": False})
  game = ACTIVE_MINES[uid]
  if idx in game["clicked"]:
    return jsonify({"success": False})
  game["clicked"].append(idx)
  ctrl = get_ctrl("mines")
  if ctrl == "win":
    game["grid"][idx] = 0
  elif ctrl == "loss":
    game["grid"][idx] = 1
  if game["grid"][idx] == 1:
    server_seed = game["server_seed"]
    del ACTIVE_MINES[uid]
    return jsonify({
        "success": True,
        "bomb": True,
        "grid": game["grid"],
        "server_seed": server_seed,
    })
  game["cleared"] += 1
  return jsonify({
      "success": True,
      "bomb": False,
      "multiplier": round(
          1.0 + (game["cleared"] * 0.15 * (game["mines"] / 3)), 2
      ),
  })


@app.route("/mines/cashout", methods=["POST"])
def mines_cashout():
  if "user_id" not in session:
    return jsonify({"success": False})
  uid = session["user_id"]
  if uid not in ACTIVE_MINES or ACTIVE_MINES[uid]["cleared"] == 0:
    return jsonify({"success": False})
  game = ACTIVE_MINES.pop(uid)
  mult = round(1.0 + (game["cleared"] * 0.15 * (game["mines"] / 3)), 2)
  win = round(game["stake"] * mult, 2)
  server_seed = game["server_seed"]
  with get_db() as conn:
    conn.execute(
        "UPDATE users SET balance = balance + ? WHERE id = ?", (win, uid)
    )
    conn.commit()
    un = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?", (uid,)
    ).fetchone()
  return jsonify({
      "success": True,
      "new_total": un["balance"] + un["bonus_balance"],
      "winnings": win,
      "server_seed": server_seed,
  })


@app.route("/dice")
def dice_game():
  if "user_id" not in session:
    return redirect(url_for("login"))
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return render_template("dice.html", user=u)


@app.route("/dice/roll", methods=["POST"])
def dice_roll():
  if "user_id" not in session:
    return jsonify({"success": False})
  uid = session["user_id"]
  try:
    stake, target = float(request.json.get("stake", 0)), float(
        request.json.get("target", 50)
    )
  except Exception:
    return jsonify({"success": False})
  condition = request.json.get("condition")
  if condition not in ["over", "under"] or stake < 10 or target < 2 or target > 98:
    return jsonify({"success": False})
  client_seed = request.json.get("client_seed", "novabetx_player")
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?", (uid,)
    ).fetchone()
    if (u["balance"] + u["bonus_balance"]) < stake:
      return jsonify({"success": False})
    deduct_stake(conn, uid, stake, u["balance"], u["bonus_balance"])
    server_seed = "".join(
        random.choices(string.ascii_letters + string.digits, k=16)
    )
    combo = f"{server_seed}-{client_seed}"
    hash_result = hashlib.sha256(combo.encode()).hexdigest()
    ctrl = get_ctrl("dice")
    if ctrl == "win":
      roll = round(
          min(99.99, target + 5.0)
          if condition == "over"
          else max(0.01, target - 5.0),
          2,
      )
    elif ctrl == "loss":
      roll = round(
          max(0.01, target - 5.0)
          if condition == "over"
          else min(99.99, target + 5.0),
          2,
      )
    else:
      roll = (int(hash_result[:8], 16) % 10001) / 100.0
    win = (condition == "over" and roll > target) or (
        condition == "under" and roll < target
    )
    chance = (100.0 - target) if condition == "over" else target
    mult = round(99.0 / chance, 2) if chance > 0 else 1.01
    winnings = round(stake * mult, 2) if win else 0
    if win:
      conn.execute(
          "UPDATE users SET balance = balance + ? WHERE id = ?", (winnings, uid)
      )
    conn.commit()
    un = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?", (uid,)
    ).fetchone()
  return jsonify({
      "success": True,
      "roll": roll,
      "win": win,
      "multiplier": mult,
      "winnings": winnings,
      "new_total": un["balance"] + un["bonus_balance"],
      "server_seed": server_seed,
      "hash": hash_result,
  })


@app.route("/seven_up_down")
def seven_up_down_game():
  if "user_id" not in session:
    return redirect(url_for("login"))
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return render_template("seven_up_down.html", user=u)


@app.route("/seven_up_down/roll", methods=["POST"])
def seven_up_down_roll():
  if "user_id" not in session:
    return jsonify({"success": False})
  try:
    stake = float(request.json.get("stake", 0))
  except Exception:
    return jsonify({"success": False})
  target = request.json.get("choice")
  if stake < 10:
    return jsonify({"success": False})
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
    if (u["balance"] + u["bonus_balance"]) < stake:
      return jsonify({"success": False})
    deduct_stake(conn, session["user_id"], stake, u["balance"], u["bonus_balance"])
    ctrl = get_ctrl("seven_up_down")
    if ctrl == "win":
      d1, d2 = (
          (2, 2) if target == "7Down" else ((5, 5) if target == "7Up" else (3, 4))
      )
    elif ctrl == "loss":
      d1, d2 = (5, 5) if target == "7Down" else (2, 2)
    else:
      d1, d2 = random.randint(1, 6), random.randint(1, 6)
    total = d1 + d2
    result = "7Down" if total < 7 else ("7Up" if total > 7 else "7")
    win = target == result
    mult = 5.0 if result == "7" else 2.0
    winnings = round(stake * mult, 2) if win else 0
    if win:
      conn.execute(
          "UPDATE users SET balance = balance + ? WHERE id = ?",
          (winnings, session["user_id"]),
      )
    conn.commit()
    un = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return jsonify({
      "success": True,
      "d1": d1,
      "d2": d2,
      "total": total,
      "result": result,
      "win": win,
      "winnings": winnings,
      "new_total": un["balance"] + un["bonus_balance"],
  })


@app.route("/penalty")
def penalty_game():
  if "user_id" not in session:
    return redirect(url_for("login"))
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return render_template("penalty.html", user=u)


@app.route("/penalty/shoot", methods=["POST"])
def penalty_shoot():
  if "user_id" not in session:
    return jsonify({"success": False})
  try:
    stake, target_zone = float(request.json.get("stake", 0)), int(
        request.json.get("zone", 1)
    )
  except Exception:
    return jsonify({"success": False})
  if stake < 10:
    return jsonify({"success": False})
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
    if (u["balance"] + u["bonus_balance"]) < stake:
      return jsonify({"success": False})
    deduct_stake(conn, session["user_id"], stake, u["balance"], u["bonus_balance"])
    ctrl = get_ctrl("penalty")
    if ctrl == "win":
      keeper_save_zone = (target_zone % 5) + 1
    elif ctrl == "loss":
      keeper_save_zone = target_zone
    else:
      keeper_save_zone = random.randint(1, 5)
    goal = target_zone != keeper_save_zone
    winnings = round(stake * 1.95, 2) if goal else 0
    if goal:
      conn.execute(
          "UPDATE users SET balance = balance + ? WHERE id = ?",
          (winnings, session["user_id"]),
      )
    conn.commit()
    un = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return jsonify({
      "success": True,
      "goal": goal,
      "keeper_zone": keeper_save_zone,
      "winnings": winnings,
      "new_total": un["balance"] + un["bonus_balance"],
  })


@app.route("/hilo")
def hilo_game():
  if "user_id" not in session:
    return redirect(url_for("login"))
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return render_template("hilo.html", user=u)


@app.route("/hilo/play", methods=["POST"])
def hilo_play():
  if "user_id" not in session:
    return jsonify({"success": False})
  try:
    stake, guess, current_val = (
        float(request.json.get("stake", 0)),
        request.json.get("guess"),
        int(request.json.get("current_card", 7)),
    )
  except Exception:
    return jsonify({"success": False})
  if stake < 10:
    return jsonify({"success": False})
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
    if (u["balance"] + u["bonus_balance"]) < stake:
      return jsonify({"success": False})
    deduct_stake(conn, session["user_id"], stake, u["balance"], u["bonus_balance"])
    ctrl = get_ctrl("hilo")
    if ctrl == "win":
      next_val = (
          current_val
          if guess == "same"
          else (
              min(13, current_val + 2)
              if guess == "higher"
              else max(1, current_val - 2)
          )
      )
    elif ctrl == "loss":
      next_val = (
          max(1, current_val - 2)
          if guess == "higher"
          else min(13, current_val + 2)
      )
    else:
      next_val = random.randint(1, 13)
    win, mult = False, 1.95
    if guess == "higher" and next_val > current_val:
      win = True
    elif guess == "lower" and next_val < current_val:
      win = True
    elif guess == "same" and next_val == current_val:
      win, mult = True, 11.0
    winnings = round(stake * mult, 2) if win else 0
    if win:
      conn.execute(
          "UPDATE users SET balance = balance + ? WHERE id = ?",
          (winnings, session["user_id"]),
      )
    conn.commit()
    un = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return jsonify({
      "success": True,
      "next_card": next_val,
      "win": win,
      "winnings": winnings,
      "new_total": un["balance"] + un["bonus_balance"],
  })


@app.route("/slots")
def slots_game():
  if "user_id" not in session:
    return redirect(url_for("login"))
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return render_template("slots.html", user=u)


@app.route("/slots/spin", methods=["POST"])
def slots_spin():
  if "user_id" not in session:
    return jsonify({"success": False})
  try:
    stake = float(request.json.get("stake", 0))
  except Exception:
    return jsonify({"success": False})
  if stake < 10:
    return jsonify({"success": False})
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
    if (u["balance"] + u["bonus_balance"]) < stake:
      return jsonify({"success": False})
    deduct_stake(conn, session["user_id"], stake, u["balance"], u["bonus_balance"])
    syms, weights = ["🍒", "🍋", "🍇", "🔔", "BAR", "777"], [
        35,
        25,
        18,
        12,
        7,
        3,
    ]
    ctrl = get_ctrl("slots")
    if ctrl == "win":
      r1 = r2 = r3 = "777"
    elif ctrl == "loss":
      r1, r2, r3 = "🍒", "🍋", "🍇"
    else:
      r1, r2, r3 = (
          random.choices(syms, weights=weights)[0],
          random.choices(syms, weights=weights)[0],
          random.choices(syms, weights=weights)[0],
      )
    mult = (
        {"🍒": 5, "🍋": 8, "🍇": 12, "🔔": 20, "BAR": 35, "777": 100}[r1]
        if r1 == r2 == r3
        else (1.5 if (r1 == r2 or r2 == r3 or r1 == r3) else 0)
    )
    winnings = round(stake * mult, 2)
    if winnings > 0:
      conn.execute(
          "UPDATE users SET balance = balance + ? WHERE id = ?",
          (winnings, session["user_id"]),
      )
    conn.commit()
    un = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return jsonify({
      "success": True,
      "reels": [r1, r2, r3],
      "multiplier": mult,
      "winnings": winnings,
      "new_total": un["balance"] + un["bonus_balance"],
  })


@app.route("/thimbles")
def thimbles_game():
  if "user_id" not in session:
    return redirect(url_for("login"))
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return render_template("thimbles.html", user=u)


@app.route("/thimbles/play", methods=["POST"])
def thimbles_play():
  if "user_id" not in session:
    return jsonify({"success": False})
  try:
    stake, guess_cup = float(request.json.get("stake", 0)), int(
        request.json.get("cup", 0)
    )
  except Exception:
    return jsonify({"success": False})
  if stake < 10:
    return jsonify({"success": False})
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
    if (u["balance"] + u["bonus_balance"]) < stake:
      return jsonify({"success": False})
    deduct_stake(conn, session["user_id"], stake, u["balance"], u["bonus_balance"])
    ctrl = get_ctrl("thimbles")
    ball_cup = (
        guess_cup
        if ctrl == "win"
        else (((guess_cup + 1) % 3) if ctrl == "loss" else random.randint(0, 2))
    )
    win = guess_cup == ball_cup
    winnings = round(stake * 2.85, 2) if win else 0
    if win:
      conn.execute(
          "UPDATE users SET balance = balance + ? WHERE id = ?",
          (winnings, session["user_id"]),
      )
    conn.commit()
    un = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return jsonify({
      "success": True,
      "ball_cup": ball_cup,
      "win": win,
      "winnings": winnings,
      "new_total": un["balance"] + un["bonus_balance"],
  })


# ----------------------------------------------------
# SECURED TOWER CLIMB (Server-Verified Session State)
# ----------------------------------------------------
@app.route("/tower")
def tower_game():
  if "user_id" not in session:
    return redirect(url_for("login"))
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return render_template("tower.html", user=u)


@app.route("/tower/step", methods=["POST"])
def tower_step():
  if "user_id" not in session:
    return jsonify({"success": False})
  uid = session["user_id"]
  try:
    stake, tier, pick_tile = (
        float(request.json.get("stake", 0)),
        int(request.json.get("tier", 1)),
        int(request.json.get("tile", 0)),
    )
  except Exception:
    return jsonify({"success": False})
  if tier < 1 or tier > 8 or pick_tile not in [0, 1]:
    return jsonify({"success": False})

  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?", (uid,)
    ).fetchone()
    if tier == 1:
      if stake < 10 or (u["balance"] + u["bonus_balance"]) < stake:
        return jsonify({"success": False, "error": "Insufficient balance"})
      deduct_stake(conn, uid, stake, u["balance"], u["bonus_balance"])
      conn.commit()
      ACTIVE_TOWER[uid] = {"stake": stake, "tier": 0, "winnings": 0.0}
    else:
      if uid not in ACTIVE_TOWER or tier != ACTIVE_TOWER[uid]["tier"] + 1:
        return jsonify({"success": False, "error": "Invalid tower session"})
      stake = ACTIVE_TOWER[uid]["stake"]

    ctrl = get_ctrl("tower")
    broken_tile = (
        (1 - pick_tile)
        if ctrl == "win"
        else (pick_tile if ctrl == "loss" else random.choice([0, 1]))
    )
    safe = pick_tile != broken_tile
    step_mult = (
        [1.3, 1.7, 2.3, 3.1, 4.2, 5.8, 8.0, 12.0][tier - 1] if safe else 0
    )
    winnings = round(stake * step_mult, 2) if safe else 0

    if safe:
      ACTIVE_TOWER[uid]["tier"] = tier
      ACTIVE_TOWER[uid]["winnings"] = winnings
    else:
      ACTIVE_TOWER.pop(uid, None)

    un = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?", (uid,)
    ).fetchone()
  return jsonify({
      "success": True,
      "safe": safe,
      "broken_tile": broken_tile,
      "tier": tier,
      "multiplier": step_mult,
      "winnings": winnings,
      "new_total": un["balance"] + un["bonus_balance"],
  })


@app.route("/tower/cashout", methods=["POST"])
def tower_cashout():
  if "user_id" not in session:
    return jsonify({"success": False})
  uid = session["user_id"]
  # Also support Coin Field cashout calls that hit /tower/cashout
  if uid not in ACTIVE_TOWER and uid in ACTIVE_COIN_FIELD:
    cf_game = ACTIVE_COIN_FIELD.pop(uid, None)
    with get_db() as conn:
      un = conn.execute(
          "SELECT balance, bonus_balance FROM users WHERE id = ?", (uid,)
      ).fetchone()
    return jsonify({
        "success": True,
        "winnings": cf_game["winnings"] if cf_game else 0,
        "new_total": un["balance"] + un["bonus_balance"],
    })
  if uid not in ACTIVE_TOWER or ACTIVE_TOWER[uid]["winnings"] <= 0:
    return jsonify({"success": False, "error": "No active tower winnings"})
  game = ACTIVE_TOWER.pop(uid)
  winnings = game["winnings"]
  with get_db() as conn:
    conn.execute(
        "UPDATE users SET balance = balance + ? WHERE id = ?", (winnings, uid)
    )
    conn.commit()
    un = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?", (uid,)
    ).fetchone()
  return jsonify({
      "success": True,
      "winnings": winnings,
      "new_total": un["balance"] + un["bonus_balance"],
  })


@app.route("/keno")
def keno_game():
  if "user_id" not in session:
    return redirect(url_for("login"))
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return render_template("keno.html", user=u)


@app.route("/keno/draw", methods=["POST"])
def keno_draw():
  if "user_id" not in session:
    return jsonify({"success": False})
  try:
    stake, chosen_numbers = (
        float(request.json.get("stake", 0)),
        [int(n) for n in request.json.get("numbers", [])][:5],
    )
  except Exception:
    return jsonify({"success": False})
  if stake < 10 or len(chosen_numbers) != 5:
    return jsonify({"success": False})
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
    if (u["balance"] + u["bonus_balance"]) < stake:
      return jsonify({"success": False})
    deduct_stake(conn, session["user_id"], stake, u["balance"], u["bonus_balance"])
    others = [n for n in range(1, 31) if n not in chosen_numbers]
    ctrl = get_ctrl("keno")
    if ctrl == "win":
      drawn_balls = chosen_numbers + random.sample(others, 3)
    elif ctrl == "loss":
      drawn_balls = random.sample(others, 8)
    else:
      drawn_balls = random.sample(range(1, 31), 8)
    matches = len(set(chosen_numbers).intersection(drawn_balls))
    mult = {0: 0, 1: 0, 2: 1.5, 3: 4.0, 4: 15.0, 5: 50.0}.get(matches, 0)
    winnings = round(stake * mult, 2)
    if winnings > 0:
      conn.execute(
          "UPDATE users SET balance = balance + ? WHERE id = ?",
          (winnings, session["user_id"]),
      )
    conn.commit()
    un = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return jsonify({
      "success": True,
      "drawn": drawn_balls,
      "matches": matches,
      "multiplier": mult,
      "winnings": winnings,
      "new_total": un["balance"] + un["bonus_balance"],
  })


@app.route("/wheel")
def wheel_game():
  if "user_id" not in session:
    return redirect(url_for("login"))
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return render_template("wheel.html", user=u)


@app.route("/wheel/spin", methods=["POST"])
def wheel_spin():
  if "user_id" not in session:
    return jsonify({"success": False})
  try:
    stake = float(request.json.get("stake", 0))
  except Exception:
    return jsonify({"success": False})
  if stake < 10:
    return jsonify({"success": False})
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
    if (u["balance"] + u["bonus_balance"]) < stake:
      return jsonify({"success": False})
    deduct_stake(conn, session["user_id"], stake, u["balance"], u["bonus_balance"])
    segments = [1.2, 1.5, 1.2, 2.0, 0.0, 1.5, 3.0, 1.2, 5.0, 0.0, 1.5, 10.0]
    ctrl = get_ctrl("wheel")
    picked_idx = (
        11 if ctrl == "win" else (4 if ctrl == "loss" else random.randint(0, 11))
    )
    mult = segments[picked_idx]
    winnings = round(stake * mult, 2)
    if winnings > 0:
      conn.execute(
          "UPDATE users SET balance = balance + ? WHERE id = ?",
          (winnings, session["user_id"]),
      )
    conn.commit()
    un = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return jsonify({
      "success": True,
      "segment_index": picked_idx,
      "multiplier": mult,
      "winnings": winnings,
      "new_total": un["balance"] + un["bonus_balance"],
  })


@app.route("/jhandi_munda")
def jhandi_munda_game():
  if "user_id" not in session:
    return redirect(url_for("login"))
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return render_template("jhandi_munda.html", user=u)


@app.route("/jhandi_munda/roll", methods=["POST"])
def jhandi_munda_roll():
  if "user_id" not in session:
    return jsonify({"success": False})
  try:
    stake = float(request.json.get("stake", 0))
  except Exception:
    return jsonify({"success": False})
  choice = request.json.get("symbol")
  if stake < 10:
    return jsonify({"success": False})
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
    if (u["balance"] + u["bonus_balance"]) < stake:
      return jsonify({"success": False})
    deduct_stake(conn, session["user_id"], stake, u["balance"], u["bonus_balance"])
    syms = ["Heart", "Spade", "Club", "Diamond", "Flag", "Crown"]
    ctrl = get_ctrl("jhandi_munda")
    if ctrl == "win":
      rolls = [choice] * 5 + [random.choice(syms)]
    elif ctrl == "loss":
      rolls = [random.choice([s for s in syms if s != choice]) for _ in range(6)]
    else:
      rolls = [random.choice(syms) for _ in range(6)]
    matches = rolls.count(choice)
    mult = 1.0 if matches == 1 else (matches + 1 if matches > 1 else 0)
    winnings = round(stake * mult, 2)
    if winnings > 0:
      conn.execute(
          "UPDATE users SET balance = balance + ? WHERE id = ?",
          (winnings, session["user_id"]),
      )
    conn.commit()
    un = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return jsonify({
      "success": True,
      "rolls": rolls,
      "matches": matches,
      "multiplier": mult,
      "winnings": winnings,
      "new_total": un["balance"] + un["bonus_balance"],
  })


# ----------------------------------------------------
# SECURED COIN FIELD (Server-Verified Session + Cashout)
# ----------------------------------------------------
@app.route("/coin_field")
def coin_field_game():
  if "user_id" not in session:
    return redirect(url_for("login"))
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return render_template("coin_field.html", user=u)


@app.route("/coin_field/step", methods=["POST"])
def coin_field_step():
  if "user_id" not in session:
    return jsonify({"success": False})
  uid = session["user_id"]
  try:
    stake, lane, step_num = (
        float(request.json.get("stake", 0)),
        int(request.json.get("lane", 0)),
        int(request.json.get("step", 1)),
    )
  except Exception:
    return jsonify({"success": False})
  if step_num < 1 or step_num > 10 or lane not in [0, 1, 2]:
    return jsonify({"success": False})

  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?", (uid,)
    ).fetchone()
    if step_num == 1:
      if stake < 10 or (u["balance"] + u["bonus_balance"]) < stake:
        return jsonify({"success": False})
      deduct_stake(conn, uid, stake, u["balance"], u["bonus_balance"])
      conn.commit()
      ACTIVE_COIN_FIELD[uid] = {"stake": stake, "step": 0, "winnings": 0.0}
    else:
      if (
          uid not in ACTIVE_COIN_FIELD
          or step_num != ACTIVE_COIN_FIELD[uid]["step"] + 1
      ):
        return jsonify({"success": False, "error": "Invalid session"})
      stake = ACTIVE_COIN_FIELD[uid]["stake"]

    ctrl = get_ctrl("coin_field")
    mine_lane = (
        ((lane + 1) % 3)
        if ctrl == "win"
        else (lane if ctrl == "loss" else random.choice([0, 1, 2]))
    )
    safe = lane != mine_lane
    mult = round(1.0 + (step_num * 0.45), 2) if safe else 0
    winnings = round(stake * mult, 2) if safe else 0

    if safe:
      # Incremental credit per safe step so both instant & cashout templates work seamlessly
      prev_win = ACTIVE_COIN_FIELD[uid]["winnings"]
      delta = round(winnings - prev_win, 2)
      if delta > 0:
        conn.execute(
            "UPDATE users SET balance = balance + ? WHERE id = ?", (delta, uid)
        )
        conn.commit()
      ACTIVE_COIN_FIELD[uid]["step"] = step_num
      ACTIVE_COIN_FIELD[uid]["winnings"] = winnings
    else:
      prev_win = ACTIVE_COIN_FIELD.pop(uid, {}).get("winnings", 0.0)
      if prev_win > 0:
        conn.execute(
            "UPDATE users SET balance = MAX(0, balance - ?) WHERE id = ?",
            (prev_win, uid),
        )
        conn.commit()

    un = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?", (uid,)
    ).fetchone()
  return jsonify({
      "success": True,
      "safe": safe,
      "mine_lane": mine_lane,
      "multiplier": mult,
      "winnings": winnings,
      "new_total": un["balance"] + un["bonus_balance"],
  })


@app.route("/coin_field/cashout", methods=["POST"])
def coin_field_cashout():
  if "user_id" not in session:
    return jsonify({"success": False})
  uid = session["user_id"]
  game = ACTIVE_COIN_FIELD.pop(uid, None)
  with get_db() as conn:
    un = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?", (uid,)
    ).fetchone()
  return jsonify({
      "success": True,
      "winnings": game["winnings"] if game else 0,
      "new_total": un["balance"] + un["bonus_balance"],
  })


@app.route("/scratch")
def scratch_game():
  if "user_id" not in session:
    return redirect(url_for("login"))
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return render_template("scratch.html", user=u)


@app.route("/scratch/play", methods=["POST"])
def scratch_play():
  if "user_id" not in session:
    return jsonify({"success": False})
  try:
    stake = float(request.json.get("stake", 0))
  except Exception:
    return jsonify({"success": False})
  if stake < 10:
    return jsonify({"success": False})
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
    if (u["balance"] + u["bonus_balance"]) < stake:
      return jsonify({"success": False})
    deduct_stake(conn, session["user_id"], stake, u["balance"], u["bonus_balance"])
    ctrl = get_ctrl("scratch")
    if ctrl == "win":
      grid = ["7️⃣", "7️⃣", "7️⃣", "🍒", "🍋", "💎", "💰", "🍒", "🍋"]
    elif ctrl == "loss":
      grid = ["🍒", "🍒", "🍋", "🍋", "💎", "💎", "💰", "💰", "7️⃣"]
    else:
      grid = [
          random.choices(
              ["🍒", "🍋", "💎", "💰", "7️⃣"], weights=[40, 30, 15, 10, 5]
          )[0]
          for _ in range(9)
      ]
    counts = {s: grid.count(s) for s in set(grid)}
    win_symbol = next((s for s, count in counts.items() if count >= 3), None)
    mult = (
        {"🍒": 1.5, "🍋": 2.5, "💎": 5.0, "💰": 10.0, "7️⃣": 50.0}.get(
            win_symbol, 0
        )
        if win_symbol
        else 0
    )
    winnings = round(stake * mult, 2)
    if winnings > 0:
      conn.execute(
          "UPDATE users SET balance = balance + ? WHERE id = ?",
          (winnings, session["user_id"]),
      )
    conn.commit()
    un = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return jsonify({
      "success": True,
      "grid": grid,
      "win": winnings > 0,
      "winnings": winnings,
      "multiplier": mult,
      "new_total": un["balance"] + un["bonus_balance"],
  })


@app.route("/casino_war")
def casino_war_game():
  if "user_id" not in session:
    return redirect(url_for("login"))
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return render_template("casino_war.html", user=u)


@app.route("/casino_war/play", methods=["POST"])
def casino_war_play():
  if "user_id" not in session:
    return jsonify({"success": False})
  try:
    stake = float(request.json.get("stake", 0))
  except Exception:
    return jsonify({"success": False})
  if stake < 10:
    return jsonify({"success": False})
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
    if (u["balance"] + u["bonus_balance"]) < stake:
      return jsonify({"success": False})
    deduct_stake(conn, session["user_id"], stake, u["balance"], u["bonus_balance"])
    ctrl = get_ctrl("casino_war")
    if ctrl == "win":
      player, dealer = draw_card("A"), draw_card("3")
    elif ctrl == "loss":
      player, dealer = draw_card("3"), draw_card("A")
    else:
      player, dealer = draw_card(), draw_card()
    rank_vals = {
        "2": 2,
        "3": 3,
        "4": 4,
        "5": 5,
        "6": 6,
        "7": 7,
        "8": 8,
        "9": 9,
        "10": 10,
        "J": 11,
        "Q": 12,
        "K": 13,
        "A": 14,
    }
    p_val, d_val = rank_vals[player["rank"]], rank_vals[dealer["rank"]]
    mult = 2.0 if p_val > d_val else (10.0 if p_val == d_val else 0)
    winnings = round(stake * mult, 2)
    if winnings > 0:
      conn.execute(
          "UPDATE users SET balance = balance + ? WHERE id = ?",
          (winnings, session["user_id"]),
      )
    conn.commit()
    un = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return jsonify({
      "success": True,
      "player": player,
      "dealer": dealer,
      "win": p_val >= d_val,
      "winnings": winnings,
      "new_total": un["balance"] + un["bonus_balance"],
  })


@app.route("/horse_racing")
def horse_racing_game():
  if "user_id" not in session:
    return redirect(url_for("login"))
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return render_template("horse_racing.html", user=u)


@app.route("/horse_racing/race", methods=["POST"])
def horse_racing_race():
  if "user_id" not in session:
    return jsonify({"success": False})
  try:
    stake, horse = float(request.json.get("stake", 0)), int(
        request.json.get("horse", 1)
    )
  except Exception:
    return jsonify({"success": False})
  if stake < 10:
    return jsonify({"success": False})
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
    if (u["balance"] + u["bonus_balance"]) < stake:
      return jsonify({"success": False})
    deduct_stake(conn, session["user_id"], stake, u["balance"], u["bonus_balance"])
    ctrl = get_ctrl("horse_racing")
    winner = (
        horse
        if ctrl == "win"
        else (((horse % 4) + 1) if ctrl == "loss" else random.randint(1, 4))
    )
    win = horse == winner
    winnings = round(stake * 3.8, 2) if win else 0
    if win:
      conn.execute(
          "UPDATE users SET balance = balance + ? WHERE id = ?",
          (winnings, session["user_id"]),
      )
    conn.commit()
    un = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return jsonify({
      "success": True,
      "winner": winner,
      "win": win,
      "winnings": winnings,
      "new_total": un["balance"] + un["bonus_balance"],
  })


# ----------------------------------------------------
# SECURED RUSSIAN ROULETTE (Server-Verified Session)
# ----------------------------------------------------
@app.route("/russian_roulette")
def russian_roulette_game():
  if "user_id" not in session:
    return redirect(url_for("login"))
  with get_db() as conn:
    user_data = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return render_template("russian_roulette.html", user=user_data)


@app.route("/russian_roulette/play", methods=["POST"])
def russian_roulette_play():
  if "user_id" not in session:
    return jsonify({"success": False})
  uid = session["user_id"]
  try:
    stake, step = float(request.json.get("stake", 0)), int(
        request.json.get("step", 1)
    )
  except Exception:
    return jsonify({"success": False})
  if step < 1 or step > 5:
    return jsonify({"success": False})

  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?", (uid,)
    ).fetchone()
    if step == 1:
      if stake < 10 or (u["balance"] + u["bonus_balance"]) < stake:
        return jsonify({"success": False, "error": "Insufficient funds"})
      deduct_stake(conn, uid, stake, u["balance"], u["bonus_balance"])
      conn.commit()
      ACTIVE_RR[uid] = {"stake": stake, "step": 0, "winnings": 0.0}
    else:
      if uid not in ACTIVE_RR or step != ACTIVE_RR[uid]["step"] + 1:
        return jsonify({"success": False, "error": "Invalid session"})
      stake = ACTIVE_RR[uid]["stake"]

    ctrl = get_ctrl("russian_roulette")
    survived = (
        True
        if ctrl == "win"
        else (False if ctrl == "loss" else (random.randint(1, 7 - step) != 1))
    )
    mults = [1.0, 1.2, 1.5, 2.0, 3.0, 5.0]
    mult = mults[step] if survived else 0
    winnings = round(stake * mult, 2) if survived else 0

    if survived:
      ACTIVE_RR[uid]["step"] = step
      ACTIVE_RR[uid]["winnings"] = winnings
    else:
      ACTIVE_RR.pop(uid, None)

    un = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?", (uid,)
    ).fetchone()
  return jsonify({
      "success": True,
      "survived": survived,
      "winnings": winnings,
      "multiplier": mult,
      "new_total": un["balance"] + un["bonus_balance"],
  })


@app.route("/russian_roulette/cashout", methods=["POST"])
def russian_roulette_cashout():
  if "user_id" not in session:
    return jsonify({"success": False})
  uid = session["user_id"]
  if uid not in ACTIVE_RR or ACTIVE_RR[uid]["winnings"] <= 0:
    return jsonify({"success": False, "error": "No active winnings"})
  game = ACTIVE_RR.pop(uid)
  winnings = game["winnings"]
  with get_db() as conn:
    conn.execute(
        "UPDATE users SET balance = balance + ? WHERE id = ?", (winnings, uid)
    )
    conn.commit()
    un = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?", (uid,)
    ).fetchone()
  return jsonify({
      "success": True,
      "winnings": winnings,
      "new_total": un["balance"] + un["bonus_balance"],
  })


@app.route("/safes")
def safes_game():
  if "user_id" not in session:
    return redirect(url_for("login"))
  with get_db() as conn:
    user_data = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return render_template("safes.html", user=user_data)


@app.route("/safes/open", methods=["POST"])
def safes_open():
  if "user_id" not in session:
    return jsonify({"success": False})
  try:
    stake, safe_choice = float(request.json.get("stake", 0)), int(
        request.json.get("safe", 0)
    )
  except Exception:
    return jsonify({"success": False})
  if stake < 10:
    return jsonify({"success": False})
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
    if (u["balance"] + u["bonus_balance"]) < stake:
      return jsonify({"success": False, "error": "Insufficient"})
    deduct_stake(conn, session["user_id"], stake, u["balance"], u["bonus_balance"])
    ctrl = get_ctrl("safes")
    empty_safe = (
        ((safe_choice + 1) % 3)
        if ctrl == "win"
        else (safe_choice if ctrl == "loss" else random.randint(0, 2))
    )
    win = safe_choice != empty_safe
    winnings = round(stake * 1.45, 2) if win else 0
    if win:
      conn.execute(
          "UPDATE users SET balance = balance + ? WHERE id = ?",
          (winnings, session["user_id"]),
      )
    conn.commit()
    un = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return jsonify({
      "success": True,
      "win": win,
      "empty_safe": empty_safe,
      "winnings": winnings,
      "new_total": un["balance"] + un["bonus_balance"],
  })


@app.route("/rps")
def rps_game():
  if "user_id" not in session:
    return redirect(url_for("login"))
  with get_db() as conn:
    user_data = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return render_template("rps.html", user=user_data)


@app.route("/rps/play", methods=["POST"])
def rps_play():
  if "user_id" not in session:
    return jsonify({"success": False})
  try:
    stake = float(request.json.get("stake", 0))
  except Exception:
    return jsonify({"success": False})
  choice = request.json.get("choice")
  if stake < 10:
    return jsonify({"success": False})
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
    if (u["balance"] + u["bonus_balance"]) < stake:
      return jsonify({"success": False})
    deduct_stake(conn, session["user_id"], stake, u["balance"], u["bonus_balance"])
    ctrl = get_ctrl("rps")
    if ctrl == "win":
      dealer = {"rock": "scissors", "paper": "rock", "scissors": "paper"}.get(
          choice, "rock"
      )
    elif ctrl == "loss":
      dealer = {"rock": "paper", "paper": "scissors", "scissors": "rock"}.get(
          choice, "paper"
      )
    else:
      dealer = random.choice(["rock", "paper", "scissors"])
    win = (
        (choice == "rock" and dealer == "scissors")
        or (choice == "paper" and dealer == "rock")
        or (choice == "scissors" and dealer == "paper")
    )
    push = choice == dealer
    winnings = round(stake * 1.95, 2) if win else (stake if push else 0)
    if winnings > 0:
      conn.execute(
          "UPDATE users SET balance = balance + ? WHERE id = ?",
          (winnings, session["user_id"]),
      )
    conn.commit()
    un = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return jsonify({
      "success": True,
      "dealer": dealer,
      "win": win,
      "push": push,
      "winnings": winnings,
      "new_total": un["balance"] + un["bonus_balance"],
  })


@app.route("/red_dog")
def red_dog_game():
  if "user_id" not in session:
    return redirect(url_for("login"))
  with get_db() as conn:
    user_data = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return render_template("red_dog.html", user=user_data)


@app.route("/red_dog/play", methods=["POST"])
def red_dog_play():
  if "user_id" not in session:
    return jsonify({"success": False})
  try:
    stake = float(request.json.get("stake", 0))
  except Exception:
    return jsonify({"success": False})
  if stake < 10:
    return jsonify({"success": False})
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
    if (u["balance"] + u["bonus_balance"]) < stake:
      return jsonify({"success": False})
    deduct_stake(conn, session["user_id"], stake, u["balance"], u["bonus_balance"])
    ctrl = get_ctrl("red_dog")
    if ctrl == "win":
      c1, c2, c3 = draw_card("2"), draw_card("A"), draw_card("8")
    elif ctrl == "loss":
      c1, c2, c3 = draw_card("6"), draw_card("7"), draw_card("K")
    else:
      c1, c2, c3 = draw_card(), draw_card(), draw_card()
    rank_vals = {
        "2": 2,
        "3": 3,
        "4": 4,
        "5": 5,
        "6": 6,
        "7": 7,
        "8": 8,
        "9": 9,
        "10": 10,
        "J": 11,
        "Q": 12,
        "K": 13,
        "A": 14,
    }
    v1, v2, v3 = rank_vals[c1["rank"]], rank_vals[c2["rank"]], rank_vals[c3["rank"]]
    win = min(v1, v2) < v3 < max(v1, v2)
    winnings = round(stake * 2.0, 2) if win else 0
    if win:
      conn.execute(
          "UPDATE users SET balance = balance + ? WHERE id = ?",
          (winnings, session["user_id"]),
      )
    conn.commit()
    un = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return jsonify({
      "success": True,
      "c1": c1,
      "c2": c2,
      "c3": c3,
      "win": win,
      "winnings": winnings,
      "new_total": un["balance"] + un["bonus_balance"],
  })


@app.route("/pharaoh_slot")
def pharaoh_slot_game():
  if "user_id" not in session:
    return redirect(url_for("login"))
  with get_db() as conn:
    user_data = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return render_template("pharaoh_slot.html", user=user_data)


@app.route("/pharaoh_slot/spin", methods=["POST"])
def pharaoh_slot_spin():
  if "user_id" not in session:
    return jsonify({"success": False})
  try:
    stake = float(request.json.get("stake", 0))
  except Exception:
    return jsonify({"success": False})
  if stake < 10:
    return jsonify({"success": False})
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
    if (u["balance"] + u["bonus_balance"]) < stake:
      return jsonify({"success": False})
    deduct_stake(conn, session["user_id"], stake, u["balance"], u["bonus_balance"])
    syms = ["🏺", "🦂", "🐪", "👁️", "☥", "𓋹"]
    ctrl = get_ctrl("pharaoh_slot")
    if ctrl == "win":
      reels = ["𓋹"] * 5
    elif ctrl == "loss":
      reels = syms[:5]
    else:
      reels = [random.choice(syms) for _ in range(5)]
    matches = max([reels.count(s) for s in set(reels)])
    mult = (
        50.0
        if matches == 5
        else (10.0 if matches == 4 else (2.0 if matches == 3 else 0.0))
    )
    winnings = round(stake * mult, 2)
    if winnings > 0:
      conn.execute(
          "UPDATE users SET balance = balance + ? WHERE id = ?",
          (winnings, session["user_id"]),
      )
    conn.commit()
    un = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return jsonify({
      "success": True,
      "reels": reels,
      "multiplier": mult,
      "winnings": winnings,
      "new_total": un["balance"] + un["bonus_balance"],
  })


@app.route("/hilo_dice")
def hilo_dice_game():
  if "user_id" not in session:
    return redirect(url_for("login"))
  with get_db() as conn:
    user_data = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return render_template("hilo_dice.html", user=user_data)


@app.route("/hilo_dice/play", methods=["POST"])
def hilo_dice_play():
  if "user_id" not in session:
    return jsonify({"success": False})
  try:
    stake, current = float(request.json.get("stake", 0)), int(
        request.json.get("current", 7)
    )
  except Exception:
    return jsonify({"success": False})
  guess = request.json.get("guess")
  if stake < 10:
    return jsonify({"success": False})
  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
    if (u["balance"] + u["bonus_balance"]) < stake:
      return jsonify({"success": False})
    deduct_stake(conn, session["user_id"], stake, u["balance"], u["bonus_balance"])
    ctrl = get_ctrl("hilo_dice")
    if ctrl == "win":
      nxt = (
          current
          if guess == "same"
          else (
              min(12, current + 2) if guess == "hi" else max(2, current - 2)
          )
      )
    elif ctrl == "loss":
      nxt = max(2, current - 2) if guess == "hi" else min(12, current + 2)
    else:
      nxt = random.randint(1, 6) + random.randint(1, 6)
    win = (
        (guess == "hi" and nxt > current)
        or (guess == "lo" and nxt < current)
        or (guess == "same" and nxt == current)
    )
    mult = 5.0 if guess == "same" else 1.95
    winnings = round(stake * mult, 2) if win else 0
    if win:
      conn.execute(
          "UPDATE users SET balance = balance + ? WHERE id = ?",
          (winnings, session["user_id"]),
      )
    conn.commit()
    un = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return jsonify({
      "success": True,
      "next": nxt,
      "win": win,
      "winnings": winnings,
      "new_total": un["balance"] + un["bonus_balance"],
  })


# ----------------------------------------------------
# SECURED COIN STREAK (Server-Verified Session)
# ----------------------------------------------------
@app.route("/coin_streak")
def coin_streak_game():
  if "user_id" not in session:
    return redirect(url_for("login"))
  with get_db() as conn:
    user_data = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
  return render_template("coin_streak.html", user=user_data)


@app.route("/coin_streak/play", methods=["POST"])
def coin_streak_play():
  if "user_id" not in session:
    return jsonify({"success": False})
  uid = session["user_id"]
  try:
    stake, step = float(request.json.get("stake", 0)), int(
        request.json.get("step", 1)
    )
  except Exception:
    return jsonify({"success": False})
  if step < 1 or step > 15:
    return jsonify({"success": False})

  with get_db() as conn:
    u = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?", (uid,)
    ).fetchone()
    if step == 1:
      if stake < 10 or (u["balance"] + u["bonus_balance"]) < stake:
        return jsonify({"success": False})
      deduct_stake(conn, uid, stake, u["balance"], u["bonus_balance"])
      conn.commit()
      ACTIVE_STREAK[uid] = {"stake": stake, "step": 0, "winnings": 0.0}
    else:
      if uid not in ACTIVE_STREAK or step != ACTIVE_STREAK[uid]["step"] + 1:
        return jsonify({"success": False, "error": "Invalid streak session"})
      stake = ACTIVE_STREAK[uid]["stake"]

    ctrl = get_ctrl("coin_streak")
    win = (
        True
        if ctrl == "win"
        else (False if ctrl == "loss" else random.choice([True, False]))
    )
    mult = round(1.95**step, 2) if win else 0
    winnings = round(stake * mult, 2) if win else 0

    if win:
      ACTIVE_STREAK[uid]["step"] = step
      ACTIVE_STREAK[uid]["winnings"] = winnings
    else:
      ACTIVE_STREAK.pop(uid, None)

    un = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?", (uid,)
    ).fetchone()
  return jsonify({
      "success": True,
      "win": win,
      "multiplier": mult,
      "winnings": winnings,
      "new_total": un["balance"] + un["bonus_balance"],
  })


@app.route("/coin_streak/cashout", methods=["POST"])
def coin_streak_cashout():
  if "user_id" not in session:
    return jsonify({"success": False})
  uid = session["user_id"]
  if uid not in ACTIVE_STREAK or ACTIVE_STREAK[uid]["winnings"] <= 0:
    return jsonify({"success": False, "error": "No active streak winnings"})
  game = ACTIVE_STREAK.pop(uid)
  winnings = game["winnings"]
  with get_db() as conn:
    conn.execute(
        "UPDATE users SET balance = balance + ? WHERE id = ?", (winnings, uid)
    )
    conn.commit()
    un = conn.execute(
        "SELECT balance, bonus_balance FROM users WHERE id = ?", (uid,)
    ).fetchone()
  return jsonify({
      "success": True,
      "winnings": winnings,
      "new_total": un["balance"] + un["bonus_balance"],
  })


# ==========================================
# 6. STEALTH ADMIN PORTAL & UNIVERSAL GOD MODE
# ==========================================
@app.route(SECRET_ADMIN_LOGIN_PATH, methods=["GET", "POST"])
def admin_login():
  if session.get("is_admin"):
    return redirect(url_for("admin"))
  if request.method == "POST":
    if request.form["username"] == ADMIN_USERNAME and check_password_hash(
        ADMIN_PASSWORD_HASH, request.form["password"]
    ):
      session["user_id"], session["is_admin"] = "admin_system", True
      return redirect(url_for("admin"))
    flash("Invalid Admin Credentials.", "error")
  return render_template("admin_login.html")


@app.route(SECRET_ADMIN_PANEL_PATH, methods=["GET", "POST"])
def admin():
  global ADMIN_GAME_CONTROL
  if not session.get("is_admin"):
    return redirect(url_for("admin_login"))
  with get_db() as conn:
    if request.method == "POST":
      act = request.form.get("action")

      if act == "update_payment":
        upi, acct, ifsc = (
            request.form.get("upi_id", "").strip(),
            request.form.get("bank_account", "").strip(),
            request.form.get("ifsc_code", "").strip(),
        )
        conn.execute(
            "UPDATE site_settings SET upi_id=?, bank_account=?, ifsc_code=?",
            (upi, acct, ifsc),
        )
        conn.commit()
        SITE_SETTINGS_CACHE["timestamp"] = 0.0  # Invalidate RAM cache immediately
        flash("Global Payment Details Updated successfully!", "success")
        return redirect(url_for("admin"))

      elif act == "control_game":
        game = request.form.get("game")
        mode = request.form.get("mode", "auto")
        mode_low = mode.lower()

        if game == "ALL":
          target_val = None if mode_low == "auto" else mode.upper()
          for k in ADMIN_GAME_CONTROL:
            ADMIN_GAME_CONTROL[k] = target_val
          flash(
              f"Global Master Override: ALL 37 GAMES set to {mode.upper()}!",
              "success",
          )
          return redirect(url_for("admin"))

        if game in ["aviator", "jetx"]:
          if mode_low == "auto":
            ADMIN_GAME_CONTROL[game] = None
          elif mode_low in ["win", "loss"]:
            ADMIN_GAME_CONTROL[game] = mode.upper()
          else:
            try:
              ADMIN_GAME_CONTROL[game] = float(request.form.get("value"))
            except Exception:
              flash(f"Invalid {game.upper()} multiplier.", "error")
        elif game in ["dt", "dragon_tiger"]:
          val = (
              None
              if mode_low == "auto"
              else (mode.upper() if mode_low in ["win", "loss"] else mode)
          )
          ADMIN_GAME_CONTROL["dt"] = ADMIN_GAME_CONTROL["dragon_tiger"] = val
        elif game in ["ht", "heads_tails"]:
          val = (
              None
              if mode_low == "auto"
              else (mode.upper() if mode_low in ["win", "loss"] else mode)
          )
          ADMIN_GAME_CONTROL["ht"] = ADMIN_GAME_CONTROL["heads_tails"] = val
        elif game in ["cp", "color_prediction"]:
          if mode_low == "auto":
            ADMIN_GAME_CONTROL["cp"] = ADMIN_GAME_CONTROL[
                "color_prediction"
            ] = None
          elif mode_low in ["win", "loss"]:
            ADMIN_GAME_CONTROL["cp"] = ADMIN_GAME_CONTROL[
                "color_prediction"
            ] = mode.upper()
          else:
            try:
              v = int(request.form.get("value"))
              ADMIN_GAME_CONTROL["cp"] = ADMIN_GAME_CONTROL[
                  "color_prediction"
              ] = v
            except Exception:
              flash("Invalid Color Prediction number.", "error")
        elif game in ADMIN_GAME_CONTROL:
          ADMIN_GAME_CONTROL[game] = (
              None if mode_low == "auto" else mode.upper()
          )

        flash(
            f"God Mode updated for {game.upper()} -> {mode.upper()}", "success"
        )
        return redirect(url_for("admin"))

      elif act == "add_match":
        conn.execute(
            "INSERT INTO matches (sport, league, team1, team2, score, status,"
            " odds1, oddsX, odds2, is_live) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                request.form["sport"],
                request.form["league"],
                request.form["team1"],
                request.form["team2"],
                request.form.get("score", ""),
                request.form.get("status", ""),
                request.form["odds1"],
                request.form.get("oddsX", 0.0),
                request.form["odds2"],
                1 if request.form.get("is_live") else 0,
            ),
        )
        conn.commit()
        flash("Match added successfully!", "success")
      elif act == "toggle_live":
        mid = request.form["match_id"]
        m = conn.execute(
            "SELECT is_live FROM matches WHERE id = ?", (mid,)
        ).fetchone()
        if m:
          new_state = 0 if m["is_live"] else 1
          conn.execute(
              "UPDATE matches SET is_live = ? WHERE id = ?", (new_state, mid)
          )
          conn.commit()
          flash(
              "Match status updated to"
              f" {'Live' if new_state else 'Upcoming'}!",
              "success",
          )
      elif act == "delete_match":
        conn.execute(
            'UPDATE bets SET match_status = "Void" WHERE match_id = ? AND'
            ' match_status = "Open"',
            (request.form["match_id"],),
        )
        conn.execute(
            "DELETE FROM matches WHERE id = ?", (request.form["match_id"],)
        )
        conn.commit()
        flash("Match deleted permanently.", "success")
      elif act == "resolve_match":
        mid, wt = request.form["match_id"], request.form["winning_team"].strip()
        bets = conn.execute(
            'SELECT * FROM bets WHERE match_id = ? AND match_status = "Open"',
            (mid,),
        ).fetchall()
        for b in bets:
          if b["team"].strip() == wt:
            conn.execute(
                "UPDATE users SET balance = balance + ? WHERE id = ?",
                (b["stake"] + b["profit"], b["user_id"]),
            )
            conn.execute(
                'UPDATE bets SET match_status = "Win" WHERE id = ?', (b["id"],)
            )
          else:
            conn.execute(
                'UPDATE bets SET match_status = "Loss" WHERE id = ?', (b["id"],)
            )
        conn.execute(
            "UPDATE matches SET status = ? WHERE id = ?", (f"Winner: {wt}", mid)
        )
        conn.commit()
        flash("Match resolved. Winners paid!", "success")
      elif act == "approve_user":
        uid = request.form["user_id"]
        u = conn.execute(
            "SELECT referrer_id FROM users WHERE id = ?", (uid,)
        ).fetchone()
        if u and u["referrer_id"]:
          conn.execute(
              "UPDATE users SET bonus_balance = bonus_balance + 50 WHERE id IN"
              " (?, ?)",
              (u["referrer_id"], uid),
          )
        conn.execute('UPDATE users SET status = "Approved" WHERE id = ?', (uid,))
        conn.commit()
        flash("Player Approved!", "success")
      elif act == "reject_user":
        conn.execute("DELETE FROM users WHERE id = ?", (request.form["user_id"],))
        conn.execute(
            "DELETE FROM deposits WHERE user_id = ?", (request.form["user_id"],)
        )
        conn.commit()
        flash("Player application declined.", "error")
      elif act == "delete_user_permanently":
        target_uid = request.form["user_id"]
        for tbl in ["users", "bets", "deposits", "withdrawals", "daily_spins"]:
          col = "id" if tbl == "users" else "user_id"
          conn.execute(f"DELETE FROM {tbl} WHERE {col} = ?", (target_uid,))
        conn.commit()
        flash("Player account and all records permanently deleted.", "success")
      elif act == "create_user":
        try:
          conn.execute(
              'INSERT INTO users (username, password, status) VALUES (?, ?,'
              ' "Approved")',
              (
                  request.form["new_username"],
                  generate_password_hash(
                      request.form["new_password"], method="pbkdf2:sha256"
                  ),
              ),
          )
          conn.commit()
          flash("User created!", "success")
        except sqlite3.IntegrityError:
          flash("Username exists.", "error")
      elif act == "adjust_balance":
        target_uid = request.form["user_id"]
        try:
          amount = float(request.form["amount"])
        except Exception:
          flash("Invalid amount.", "error")
          return redirect(url_for("admin"))
        mode = request.form["mode"]
        if amount <= 0:
          flash("Amount must be greater than zero.", "error")
        elif mode == "remove":
          current_bal = conn.execute(
              "SELECT balance FROM users WHERE id = ?", (target_uid,)
          ).fetchone()["balance"]
          amount = min(amount, current_bal)
          conn.execute(
              "UPDATE users SET balance = balance - ? WHERE id = ?",
              (amount, target_uid),
          )
          flash(f"Subtracted ₹{amount} from account!", "success")
        else:
          conn.execute(
              "UPDATE users SET balance = balance + ?, total_wagered ="
              " total_wagered + ? WHERE id = ?",
              (amount, amount, target_uid),
          )
          flash(f"Added ₹{amount} to account!", "success")
        conn.commit()
      elif act == "approve_deposit":
        d = conn.execute(
            "SELECT * FROM deposits WHERE id = ?", (request.form["deposit_id"],)
        ).fetchone()
        if d and d["status"] == "Pending":
          conn.execute(
              "UPDATE users SET balance = balance + ?, total_wagered ="
              " total_wagered + ? WHERE id = ?",
              (d["amount"], d["amount"], d["user_id"]),
          )
          conn.execute(
              'UPDATE deposits SET status = "Approved" WHERE id = ?', (d["id"],)
          )
          conn.commit()
          flash("Deposit Approved!", "success")
      elif act == "reject_deposit":
        conn.execute(
            'UPDATE deposits SET status = "Rejected" WHERE id = ?',
            (request.form["deposit_id"],),
        )
        conn.commit()
        flash("Deposit rejected.", "error")
      elif act == "approve_withdraw":
        conn.execute(
            'UPDATE withdrawals SET status = "Approved" WHERE id = ?',
            (request.form["withdraw_id"],),
        )
        conn.commit()
        flash("Withdrawal Approved!", "success")
      elif act == "reject_withdraw":
        w = conn.execute(
            "SELECT * FROM withdrawals WHERE id = ?",
            (request.form["withdraw_id"],),
        ).fetchone()
        if w and w["status"] == "Pending":
          conn.execute(
              "UPDATE users SET balance = balance + ? WHERE id = ?",
              (w["amount"], w["user_id"]),
          )
          conn.execute(
              'UPDATE withdrawals SET status = "Rejected" WHERE id = ?',
              (w["id"],),
          )
          conn.commit()
          flash("Withdrawal refunded.", "error")
      return redirect(url_for("admin"))

    m = conn.execute("SELECT * FROM matches ORDER BY id DESC").fetchall()
    u = conn.execute(
        "SELECT id, username, mobile, balance, bonus_balance, total_wagered"
        ' FROM users WHERE status = "Approved" ORDER BY id DESC'
    ).fetchall()
    pu = conn.execute(
        'SELECT id, username, mobile FROM users WHERE status = "Pending" ORDER'
        " BY id DESC"
    ).fetchall()
    w = conn.execute(
        """SELECT w.*, u.username FROM withdrawals w JOIN users u ON w.user_id = u.id ORDER BY w.id DESC"""
    ).fetchall()
    d = conn.execute(
        """SELECT d.*, u.username FROM deposits d JOIN users u ON d.user_id = u.id ORDER BY d.id DESC"""
    ).fetchall()

  return render_template(
      "admin.html",
      matches=m,
      users=u,
      pending_users=pu,
      withdrawals=w,
      deposits=d,
      games_catalog=GAMES_CATALOG,
      game_control=ADMIN_GAME_CONTROL,
      aviator_state=AVIATOR_STATE,
      jetx_state=JETX_STATE,
      dt_state=DT_STATE,
      ht_state=HT_STATE,
      cp_state=CP_STATE,
  )


init_db()
if __name__ == "__main__":
  with app.app_context():
    init_db()
  print(f"🔒 Stealth Admin Login: http://localhost:5050{SECRET_ADMIN_LOGIN_PATH}")
  app.run(host="0.0.0.0", debug=False, port=5050, threaded=True)