import sqlite3
import os
import time
import random
import hashlib
import string
from flask import Flask, request, session, redirect, url_for, flash, render_template, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.urandom(24) 

USE_MYSQL = False
if USE_MYSQL:
    import mysql.connector
    DB_CONFIG = {'host': 'yourusername.mysql.pythonanywhere-services.com', 'user': 'yourusername', 'password': 'your_mysql_password', 'database': 'yourusername$betting'}
else:
    DB_NAME = "betting.db"

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ADMIN_USERNAME = "superadmin"
ADMIN_PASSWORD_HASH = generate_password_hash("NavabetxAdmin99!", method='pbkdf2:sha256')

GAMES_CATALOG = [
    {"id": "jetx", "route": "jetx_game", "title": "JetX Rocket", "category": "Crash", "icon": "fa-rocket", "color": "amber", "min_bet": 10},
    {"id": "plinko", "route": "plinko_game", "title": "Plinko Ball", "category": "Instant Win", "icon": "fa-circle-nodes", "color": "pink", "min_bet": 10},
    {"id": "blackjack", "route": "blackjack_game", "title": "Blackjack 21", "category": "Cards & Tables", "icon": "fa-heart", "color": "emerald", "min_bet": 10},
    {"id": "roulette", "route": "roulette_game", "title": "European Roulette", "category": "Cards & Tables", "icon": "fa-circle-notch", "color": "red", "min_bet": 10},
    {"id": "baccarat", "route": "baccarat_game", "title": "Baccarat Pro", "category": "Cards & Tables", "icon": "fa-diamond", "color": "blue", "min_bet": 10},
    {"id": "craps", "route": "craps_game", "title": "Craps Street", "category": "Dice & Numbers", "icon": "fa-dice", "color": "orange", "min_bet": 10},
    {"id": "poker", "route": "poker_game", "title": "Video Poker", "category": "Cards & Tables", "icon": "fa-crown", "color": "indigo", "min_bet": 10},
    {"id": "andar_bahar", "route": "andar_bahar_game", "title": "Andar Bahar", "category": "Cards & Tables", "icon": "fa-layer-group", "color": "teal", "min_bet": 10},
    {"id": "teen_patti", "route": "teen_patti_game", "title": "Teen Patti Live", "category": "Cards & Tables", "icon": "fa-shield-halved", "color": "yellow", "min_bet": 10},
    {"id": "limbo", "route": "limbo_game", "title": "Limbo Rocket", "category": "Crash", "icon": "fa-arrow-trend-up", "color": "cyan", "min_bet": 10},
    {"id": "aviator", "route": "aviator_game", "title": "Aviator", "category": "Crash", "icon": "fa-plane-up", "color": "red", "min_bet": 10},
    {"id": "dragon_tiger", "route": "dragon_tiger_game", "title": "Dragon Tiger", "category": "Cards & Tables", "icon": "fa-dragon", "color": "yellow", "min_bet": 10},
    {"id": "heads_tails", "route": "heads_tails_game", "title": "Heads v Tails", "category": "Instant Win", "icon": "fa-coins", "color": "slate", "min_bet": 10},
    {"id": "color_prediction", "route": "color_prediction_game", "title": "Color Predict", "category": "Dice & Numbers", "icon": "fa-palette", "color": "purple", "min_bet": 10},
    {"id": "mines", "route": "mines_game", "title": "Cyber Mines", "category": "Instant Win", "icon": "fa-bomb", "color": "cyan", "min_bet": 10},
    {"id": "dice", "route": "dice_game", "title": "Digital Dice", "category": "Dice & Numbers", "icon": "fa-dice-d20", "color": "pink", "min_bet": 10},
    {"id": "spin", "route": "spin_game", "title": "Daily Spin", "category": "Bonus", "icon": "fa-dharmachakra", "color": "indigo", "min_bet": 0},
    {"id": "seven_up_down", "route": "seven_up_down_game", "title": "7 Up 7 Down", "category": "Dice & Numbers", "icon": "fa-dice", "color": "yellow", "min_bet": 10},
    {"id": "penalty", "route": "penalty_game", "title": "Penalty Shootout", "category": "Instant Win", "icon": "fa-futbol", "color": "emerald", "min_bet": 10},
    {"id": "hilo", "route": "hilo_game", "title": "Hi-Lo Cards", "category": "Cards & Tables", "icon": "fa-arrow-up-wide-short", "color": "cyan", "min_bet": 10},
    {"id": "slots", "route": "slots_game", "title": "Neon 777 Slots", "category": "Crash", "icon": "fa-gem", "color": "pink", "min_bet": 10},
    {"id": "thimbles", "route": "thimbles_game", "title": "Thimbles", "category": "Instant Win", "icon": "fa-cubes", "color": "amber", "min_bet": 10},
    {"id": "tower", "route": "tower_game", "title": "Tower Climb", "category": "Crash", "icon": "fa-cubes-stacked", "color": "purple", "min_bet": 10},
    {"id": "keno", "route": "keno_game", "title": "Classic Keno", "category": "Dice & Numbers", "icon": "fa-ticket", "color": "blue", "min_bet": 10},
    {"id": "wheel", "route": "wheel_game", "title": "Turbo Wheel", "category": "Crash", "icon": "fa-circle-radiation", "color": "red", "min_bet": 10},
    {"id": "jhandi_munda", "route": "jhandi_munda_game", "title": "Jhandi Munda", "category": "Dice & Numbers", "icon": "fa-crown", "color": "teal", "min_bet": 10},
    {"id": "coin_field", "route": "coin_field_game", "title": "Coin Field", "category": "Instant Win", "icon": "fa-border-all", "color": "brand", "min_bet": 10},
    {"id": "scratch", "route": "scratch_game", "title": "Scratch & Win", "category": "Instant Win", "icon": "fa-ticket", "color": "purple", "min_bet": 10},
    {"id": "casino_war", "route": "casino_war_game", "title": "Casino War", "category": "Cards & Tables", "icon": "fa-khanda", "color": "red", "min_bet": 10},
    {"id": "horse_racing", "route": "horse_racing_game", "title": "Virtual Racing", "category": "Arcade", "icon": "fa-horse", "color": "amber", "min_bet": 10},
    {"id": "russian_roulette", "route": "russian_roulette_game", "title": "Russian Roulette", "category": "Crash", "icon": "fa-gun", "color": "gray", "min_bet": 10},
    {"id": "safes", "route": "safes_game", "title": "Magic Safes", "category": "Instant Win", "icon": "fa-vault", "color": "yellow", "min_bet": 10},
    {"id": "rps", "route": "rps_game", "title": "Ro-Sham-Bo", "category": "Arcade", "icon": "fa-hand-scissors", "color": "cyan", "min_bet": 10},
    {"id": "red_dog", "route": "red_dog_game", "title": "Red Dog", "category": "Cards & Tables", "icon": "fa-dog", "color": "orange", "min_bet": 10},
    {"id": "pharaoh_slot", "route": "pharaoh_slot_game", "title": "Pharaoh's Tomb", "category": "Slots", "icon": "fa-gem", "color": "amber", "min_bet": 10},
    {"id": "hilo_dice", "route": "hilo_dice_game", "title": "Hi-Lo Dice", "category": "Dice & Numbers", "icon": "fa-dice-two", "color": "pink", "min_bet": 10},
    {"id": "coin_streak", "route": "coin_streak_game", "title": "Coin Streak", "category": "Instant Win", "icon": "fa-coins", "color": "brand", "min_bet": 10}
]

ADMIN_GAME_CONTROL = {"aviator": None, "jetx": None, "dt": None, "ht": None, "cp": None}

AVIATOR_STATE = {"state": "WAITING", "start_time": time.time(), "crash_point": 0.00, "match_number": 1, "history": []}
ACTIVE_BETS = {}
def update_aviator_state():
    global AVIATOR_STATE, ACTIVE_BETS, ADMIN_GAME_CONTROL
    now = time.time()
    elapsed = now - AVIATOR_STATE["start_time"]
    if AVIATOR_STATE["state"] == "WAITING" and elapsed > 5.0: 
        AVIATOR_STATE["state"] = "FLYING"
        AVIATOR_STATE["start_time"] = now
        if ADMIN_GAME_CONTROL["aviator"] is not None: 
            crash = ADMIN_GAME_CONTROL["aviator"]
        else:
            rand = random.random()
            if rand < 0.60: crash = round(random.uniform(1.00, 1.49), 2)
            elif rand < 0.85: crash = round(random.uniform(1.50, 1.99), 2)
            elif rand < 0.95: crash = round(random.uniform(2.00, 5.00), 2)
            else: crash = round(random.uniform(5.01, 35.00), 2)
        AVIATOR_STATE["crash_point"] = crash
    elif AVIATOR_STATE["state"] == "FLYING":
        if 1.00 + (elapsed ** 1.4) * 0.08 >= AVIATOR_STATE["crash_point"]:
            AVIATOR_STATE["state"] = "CRASHED"
            AVIATOR_STATE["start_time"] = now
            AVIATOR_STATE["history"].insert(0, {"id": f"{AVIATOR_STATE['match_number']:06d}", "mult": AVIATOR_STATE["crash_point"]})
            if len(AVIATOR_STATE["history"]) > 15: 
                AVIATOR_STATE["history"].pop()
            ACTIVE_BETS.clear()
    elif AVIATOR_STATE["state"] == "CRASHED" and elapsed > 3.0: 
        AVIATOR_STATE["state"] = "WAITING"
        AVIATOR_STATE["start_time"] = now
        AVIATOR_STATE["match_number"] += 1 

JETX_STATE = {"state": "WAITING", "start_time": time.time(), "crash_point": 1.50, "match_number": 1}
JETX_BETS = {}
def update_jetx_state():
    global JETX_STATE, JETX_BETS, ADMIN_GAME_CONTROL
    now = time.time()
    elapsed = now - JETX_STATE["start_time"]
    if JETX_STATE["state"] == "WAITING" and elapsed > 5.0:
        JETX_STATE["state"] = "FLYING"
        JETX_STATE["start_time"] = now
        
        # Admin Override Check
        if ADMIN_GAME_CONTROL.get("jetx") is not None:
            JETX_STATE["crash_point"] = ADMIN_GAME_CONTROL["jetx"]
        else:
            r = random.random()
            JETX_STATE["crash_point"] = round(1.01 + (random.uniform(0.1, 15.0) if r > 0.4 else random.uniform(0.01, 1.3)), 2)
            
    elif JETX_STATE["state"] == "FLYING":
        if 1.00 + (elapsed ** 1.35) * 0.09 >= JETX_STATE["crash_point"]:
            JETX_STATE["state"] = "CRASHED"
            JETX_STATE["start_time"] = now
            JETX_BETS.clear()
    elif JETX_STATE["state"] == "CRASHED" and elapsed > 3.0:
        JETX_STATE["state"] = "WAITING"
        JETX_STATE["start_time"] = now
        JETX_STATE["match_number"] += 1
DT_STATE = {"state": "WAITING", "start_time": time.time(), "result": None, "d_card": 0, "t_card": 0, "match_number": 1, "history": []}
DT_BETS = {} 
def update_dt_state():
    global DT_STATE, DT_BETS, ADMIN_GAME_CONTROL
    now = time.time()
    elapsed = now - DT_STATE["start_time"]
    if DT_STATE["state"] == "WAITING" and elapsed > 15.0: 
        DT_STATE["state"] = "REVEAL"
        DT_STATE["start_time"] = now
        forced = ADMIN_GAME_CONTROL["dt"]
        if forced == "Dragon": d_card = random.randint(3, 14); t_card = random.randint(2, d_card - 1); res = "Dragon"
        elif forced == "Tiger": t_card = random.randint(3, 14); d_card = random.randint(2, t_card - 1); res = "Tiger"
        elif forced == "Tie": d_card = random.randint(2, 14); t_card = d_card; res = "Tie"
        else:
            rand = random.random()
            if rand < 0.45: d_card = random.randint(3, 14); t_card = random.randint(2, d_card - 1); res = "Dragon"
            elif rand < 0.90: t_card = random.randint(3, 14); d_card = random.randint(2, t_card - 1); res = "Tiger"
            else: d_card = random.randint(2, 14); t_card = d_card; res = "Tie"
        DT_STATE["d_card"] = d_card
        DT_STATE["t_card"] = t_card
        DT_STATE["result"] = res
        DT_STATE["history"].insert(0, {"id": f"{DT_STATE['match_number']:06d}", "val": res})
        if len(DT_STATE["history"]) > 15: 
            DT_STATE["history"].pop()
        if DT_BETS:
            with get_db() as conn:
                for uid, bet in DT_BETS.items():
                    if bet['target'] == res: 
                        conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (bet['stake'] * (8.0 if res == "Tie" else 2.0), uid))
                conn.commit()
            DT_BETS.clear()
    elif DT_STATE["state"] == "REVEAL" and elapsed > 6.0: 
        DT_STATE["state"] = "WAITING"
        DT_STATE["start_time"] = now
        DT_STATE["match_number"] += 1

HT_STATE = {"state": "WAITING", "start_time": time.time(), "result": None, "match_number": 1, "history": []}
HT_BETS = {} 
def update_ht_state():
    global HT_STATE, HT_BETS, ADMIN_GAME_CONTROL
    now = time.time()
    elapsed = now - HT_STATE["start_time"]
    if HT_STATE["state"] == "WAITING" and elapsed > 12.0:
        HT_STATE["state"] = "FLIPPING"
        HT_STATE["start_time"] = now
        res = ADMIN_GAME_CONTROL["ht"] if ADMIN_GAME_CONTROL["ht"] is not None else ("Heads" if random.random() < 0.5 else "Tails")
        HT_STATE["result"] = res
        HT_STATE["history"].insert(0, {"id": f"{HT_STATE['match_number']:06d}", "val": "H" if res == "Heads" else "T"})
        if len(HT_STATE["history"]) > 15: 
            HT_STATE["history"].pop()
        if HT_BETS:
            with get_db() as conn:
                for uid, bet in HT_BETS.items():
                    if bet['target'] == res: 
                        conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (bet['stake'] * 1.95, uid))
                conn.commit()
            HT_BETS.clear()
    elif HT_STATE["state"] == "FLIPPING" and elapsed > 5.0:
        HT_STATE["state"] = "WAITING"
        HT_STATE["start_time"] = now
        HT_STATE["match_number"] += 1

CP_STATE = {"state": "WAITING", "start_time": time.time(), "result_number": -1, "result_color": "", "match_number": 1, "history": []}
CP_BETS = {} 
def update_cp_state():
    global CP_STATE, CP_BETS, ADMIN_GAME_CONTROL
    now = time.time()
    elapsed = now - CP_STATE["start_time"]
    if CP_STATE["state"] == "WAITING" and elapsed > 30.0:
        CP_STATE["state"] = "REVEAL"
        CP_STATE["start_time"] = now
        res_num = ADMIN_GAME_CONTROL["cp"] if ADMIN_GAME_CONTROL["cp"] is not None else random.randint(0, 9)
        if res_num in [1, 3, 7, 9]: res_color = "Green"
        elif res_num in [2, 4, 6, 8]: res_color = "Red"
        else: res_color = "Violet"
        CP_STATE["result_number"] = res_num
        CP_STATE["result_color"] = res_color
        CP_STATE["history"].insert(0, {"id": f"{CP_STATE['match_number']:06d}", "val": res_num, "col": res_color})
        if len(CP_STATE["history"]) > 15: 
            CP_STATE["history"].pop()
        if CP_BETS:
            with get_db() as conn:
                for uid, bet in CP_BETS.items():
                    target = str(bet['target'])
                    stake = bet['stake']
                    win = 0
                    if target == str(res_num): win = stake * 9.0
                    elif target == "Green" and res_color == "Green": win = stake * 2.0
                    elif target == "Red" and res_color == "Red": win = stake * 2.0
                    elif target == "Violet" and res_color == "Violet": win = stake * 4.5
                    if win > 0: 
                        conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (win, uid))
                conn.commit()
            CP_BETS.clear()
    elif CP_STATE["state"] == "REVEAL" and elapsed > 5.0:
        CP_STATE["state"] = "WAITING"
        CP_STATE["start_time"] = now
        CP_STATE["match_number"] += 1

ACTIVE_MINES = {} 
ACTIVE_BLACKJACK = {}

def draw_card():
    return {'rank': random.choice(['2','3','4','5','6','7','8','9','10','J','Q','K','A']), 'suit': random.choice(['♠', '♥', '♦', '♣'])}

def calc_hand(hand):
    val = 0
    aces = 0
    for c in hand:
        if c['rank'] in ['J', 'Q', 'K']: val += 10
        elif c['rank'] == 'A': val += 11; aces += 1
        else: val += int(c['rank'])
    while val > 21 and aces > 0: 
        val -= 10
        aces -= 1
    return val

def get_db():
    if USE_MYSQL:
        conn = mysql.connector.connect(**DB_CONFIG)
        conn.row_factory = lambda cursor, row: dict(zip([col[0] for col in cursor.description], row))
        return conn
    else:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    if USE_MYSQL: return 
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, mobile TEXT, balance REAL DEFAULT 0.00, bonus_balance REAL DEFAULT 0.00, status TEXT DEFAULT 'Pending', referrer_id INTEGER, total_wagered REAL DEFAULT 0.00)''') 
        try: conn.execute('ALTER TABLE users ADD COLUMN total_wagered REAL DEFAULT 0.00')
        except: pass
        conn.execute('''CREATE TABLE IF NOT EXISTS matches (id INTEGER PRIMARY KEY AUTOINCREMENT, sport TEXT, league TEXT, team1 TEXT, team2 TEXT, score TEXT, status TEXT, odds1 REAL, oddsX REAL, odds2 REAL, is_live INTEGER DEFAULT 0)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS bets (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, match_id INTEGER, match_name TEXT, team TEXT, odds REAL, stake REAL, profit REAL, match_status TEXT DEFAULT 'Open', date TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS withdrawals (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, account_number TEXT, account_name TEXT, ifsc TEXT, bank_name TEXT, amount REAL, status TEXT DEFAULT 'Pending', date TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS deposits (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, method TEXT, amount REAL, utr TEXT, screenshot TEXT, status TEXT DEFAULT 'Pending', date TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS daily_spins (user_id INTEGER PRIMARY KEY, last_spin_time REAL)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS site_settings (id INTEGER PRIMARY KEY AUTOINCREMENT, upi_id TEXT, bank_account TEXT, ifsc_code TEXT)''')
        if not conn.execute('SELECT * FROM site_settings').fetchone(): 
            conn.execute("INSERT INTO site_settings (upi_id, bank_account, ifsc_code) VALUES ('your_upi@okbank', 'Account Number Here', 'IFSC Code Here')")
        conn.commit()

@app.context_processor
def inject_global_settings():
    try:
        with get_db() as conn: 
            return dict(site_settings=conn.execute('SELECT * FROM site_settings ORDER BY id DESC LIMIT 1').fetchone())
    except: 
        return dict(site_settings={'upi_id': 'Updating...', 'bank_account': 'Updating...', 'ifsc_code': 'Updating...'})

def deduct_stake(conn, user_id, stake, user_balance, user_bonus):
    if user_bonus >= stake: 
        conn.execute('UPDATE users SET bonus_balance = bonus_balance - ?, total_wagered = total_wagered + ? WHERE id = ?', (stake, stake, user_id))
    else: 
        conn.execute('UPDATE users SET bonus_balance = 0, balance = balance - ?, total_wagered = total_wagered + ? WHERE id = ?', (stake - user_bonus, stake, user_id))

@app.route('/', methods=['GET', 'POST'])
def login():
    if 'user_id' in session: 
        return redirect(url_for('admin' if session.get('is_admin') else 'home'))
    if request.method == 'POST':
        with get_db() as conn:
            user = conn.execute('SELECT * FROM users WHERE username = ?', (request.form['username'],)).fetchone()
            if user and check_password_hash(user['password'], request.form['password']):
                if user['status'] == 'Pending': 
                    flash('Account pending admin approval.', 'error')
                    return redirect(url_for('login'))
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['is_admin'] = False
                return redirect(url_for('home'))
            else: 
                flash('Invalid credentials.', 'error')
    return render_template('login.html')

@app.route('/register', methods=['POST'])
def register():
    username = request.form['username'].strip()
    mobile = request.form['mobile'].strip()
    pwd = request.form['password']
    cpwd = request.form['confirm_password']
    ref = request.form.get('referral_code', '').strip()
    if pwd != cpwd: 
        flash("Passwords don't match!", "error")
        return redirect(url_for('login'))
    with get_db() as conn:
        if conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone(): 
            flash("Username exists.", "error")
            return redirect(url_for('login'))
        referrer = conn.execute('SELECT id FROM users WHERE username = ?', (ref,)).fetchone() if ref else None
        cursor = conn.execute('INSERT INTO users (username, password, mobile, status, referrer_id) VALUES (?, ?, ?, "Pending", ?)', (username, generate_password_hash(pwd, method='pbkdf2:sha256'), mobile, referrer['id'] if referrer else None))
        conn.commit()
        flash(str(cursor.lastrowid), 'fast_track')
    return redirect(url_for('login'))

@app.route('/fast_track_deposit', methods=['POST'])
def fast_track_deposit():
    try: 
        uid = int(request.form['user_id'])
        amt = float(request.form['amount'])
    except: 
        flash('Invalid deposit amount.', 'error')
        return redirect(url_for('login'))
    if amt <= 0: 
        flash('Invalid deposit amount.', 'error')
        return redirect(url_for('login'))
    utr = request.form['utr'].strip()
    file = request.files.get('screenshot')
    fname = secure_filename(f"{uid}_{int(time.time())}_{file.filename}") if file else ""
    if fname: 
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
    with get_db() as conn:
        conn.execute('INSERT INTO deposits (user_id, method, amount, utr, screenshot, status, date) VALUES (?, "First Deposit", ?, ?, ?, "Pending", ?)', (uid, amt, utr, fname, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        flash('Payment proof submitted! Admin will verify.', 'success')
    return redirect(url_for('login'))

@app.route('/logout')
def logout(): 
    session.clear()
    return redirect(url_for('login'))

@app.route('/home')
def home():
    if 'user_id' not in session or session.get('is_admin'): 
        return redirect(url_for('login'))
    with get_db() as conn:
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        l = conn.execute('SELECT * FROM matches WHERE is_live = 1 AND (status IS NULL OR status NOT LIKE "Winner:%") LIMIT 4').fetchall()
        p = conn.execute('SELECT * FROM matches WHERE is_live = 0 AND (status IS NULL OR status NOT LIKE "Winner:%") LIMIT 10').fetchall()
    return render_template('index.html', live_matches=l, popular_matches=p, user=u)

@app.route('/games')
def games():
    if 'user_id' not in session or session.get('is_admin'): 
        return redirect(url_for('login'))
    with get_db() as conn: 
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return render_template('games.html', user=u, games_catalog=GAMES_CATALOG)

@app.route('/profile')
def profile():
    if 'user_id' not in session or session.get('is_admin'): 
        return redirect(url_for('login'))
    with get_db() as conn:
        user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        tot_dep = conn.execute("SELECT COALESCE(SUM(amount), 0) as total FROM deposits WHERE user_id = ? AND status = 'Approved'", (session['user_id'],)).fetchone()['total']
        curr_w = user['total_wagered'] if 'total_wagered' in user.keys() and user['total_wagered'] is not None else 0.0
        effective_vip = max(curr_w + tot_dep, user['balance'] + curr_w)
        if effective_vip > curr_w:
            conn.execute('UPDATE users SET total_wagered = ? WHERE id = ?', (effective_vip, session['user_id']))
            conn.commit()
            user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        bc = conn.execute('SELECT COUNT(*) as count FROM bets WHERE user_id = ?', (session['user_id'],)).fetchone()
        dep = conn.execute('SELECT * FROM deposits WHERE user_id = ? ORDER BY id DESC', (session['user_id'],)).fetchall()
        wit = conn.execute('SELECT * FROM withdrawals WHERE user_id = ? ORDER BY id DESC', (session['user_id'],)).fetchall()
        has_dep = conn.execute("SELECT COUNT(*) as count FROM deposits WHERE user_id = ? AND status = 'Approved'", (session['user_id'],)).fetchone()['count'] > 0
    return render_template('profile.html', user=user, bet_count=bc['count'], deposits=dep, withdrawals=wit, has_deposited=has_dep)
    
@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session: 
        return redirect(url_for('login'))
    mobile = request.form.get('mobile', '').strip()
    old_password = request.form.get('old_password', '')
    new_password = request.form.get('new_password', '')
    with get_db() as conn:
        user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if new_password:
            if not check_password_hash(user['password'], old_password): 
                flash('Security Alert: Incorrect current password!', 'error')
                return redirect(url_for('profile'))
            conn.execute('UPDATE users SET mobile = ?, password = ? WHERE id = ?', (mobile, generate_password_hash(new_password, method='pbkdf2:sha256'), session['user_id']))
            flash('Vault secured! Password & Profile updated.', 'success')
        else:
            conn.execute('UPDATE users SET mobile = ? WHERE id = ?', (mobile, session['user_id']))
            flash('Profile details updated successfully!', 'success')
        conn.commit()
    return redirect(url_for('profile'))

@app.route('/my_bets')
def my_bets():
    if 'user_id' not in session or session.get('is_admin'): 
        return redirect(url_for('login'))
    with get_db() as conn:
        user = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        bets = conn.execute('SELECT * FROM bets WHERE user_id = ? ORDER BY id DESC', (session['user_id'],)).fetchall()
    return render_template('my_bets.html', bets=bets, user=user)

@app.route('/claim_referral', methods=['POST'])
def claim_referral():
    if 'user_id' not in session: 
        return redirect(url_for('login'))
    ref = request.form.get('referral_code', '').strip()
    with get_db() as conn:
        if not USE_MYSQL:
            conn.execute('BEGIN IMMEDIATE')
        user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if user['referrer_id']: 
            flash('Bonus already claimed!', 'error')
            return redirect(url_for('profile'))
        if user['username'].lower() == ref.lower(): 
            flash('Cannot use your own code!', 'error')
            return redirect(url_for('profile'))
        referrer = conn.execute('SELECT * FROM users WHERE username = ? COLLATE NOCASE', (ref,)).fetchone()
        if not referrer: 
            flash('Invalid referral code.', 'error')
            return redirect(url_for('profile'))
        conn.execute('UPDATE users SET bonus_balance = bonus_balance + 50 WHERE id = ?', (referrer['id'],))
        conn.execute('UPDATE users SET bonus_balance = bonus_balance + 50, referrer_id = ? WHERE id = ?', (referrer['id'], session['user_id']))
        conn.commit()
        flash('₹50 Referral Bonus Applied!', 'success')
    return redirect(url_for('profile'))

@app.route('/deposit', methods=['POST'])
def deposit():
    if 'user_id' not in session: 
        return redirect(url_for('login'))
    try:
        amt = float(request.form['amount'])
        if amt < 10: raise ValueError
    except: 
        flash('Invalid minimum amount.', 'error')
        return redirect(url_for('profile'))
    file = request.files.get('screenshot')
    fname = secure_filename(f"{session['user_id']}_{int(time.time())}_{file.filename}") if file else ""
    if fname: 
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
    with get_db() as conn:
        conn.execute('INSERT INTO deposits (user_id, method, amount, utr, screenshot, status, date) VALUES (?, ?, ?, ?, ?, "Pending", ?)', 
                     (session['user_id'], request.form['method'], amt, request.form['utr'], fname, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        flash('Deposit submitted for admin approval.', 'success')
    return redirect(url_for('profile'))

@app.route('/withdraw', methods=['POST'])
def withdraw():
    if 'user_id' not in session: 
        return redirect(url_for('login'))
    try:
        amt = float(request.form['amount'])
        if amt < 50: raise ValueError
    except: 
        flash('Minimum withdrawal is ₹50.', 'error')
        return redirect(url_for('profile'))
    with get_db() as conn:
        if not USE_MYSQL:
            conn.execute('BEGIN IMMEDIATE')
        if conn.execute("SELECT COUNT(*) as count FROM deposits WHERE user_id = ? AND status = 'Approved'", (session['user_id'],)).fetchone()['count'] == 0:
            flash('Must deposit first to unlock withdrawals!', 'error')
            return redirect(url_for('profile'))
        user = conn.execute('SELECT balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if user['balance'] < amt: 
            flash('Insufficient REAL balance!', 'error')
        else:
            conn.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (amt, session['user_id']))
            conn.execute('INSERT INTO withdrawals (user_id, account_number, account_name, ifsc, bank_name, amount, status, date) VALUES (?, ?, ?, ?, ?, ?, "Pending", ?)', 
                         (session['user_id'], request.form['account_number'], request.form['account_name'], request.form['ifsc'], request.form['bank_name'], amt, datetime.now().strftime("%Y-%m-%d %H:%M")))
            conn.commit()
            flash('Withdrawal request submitted successfully!', 'success')
    return redirect(url_for('profile'))

@app.route('/place_bet', methods=['POST'])
def place_bet():
    if 'user_id' not in session or session.get('is_admin'): 
        return jsonify({'success': False, 'error': 'Unauthorized'})
    data = request.json
    try:
        mid = int(data.get('match_id'))
        team = data.get('team').strip()
        odds = float(data.get('odds'))
        stake = float(data.get('stake'))
        if stake < 10: raise ValueError
    except: 
        return jsonify({'success': False, 'error': 'Invalid bet details.'})
    with get_db() as conn:
        if not USE_MYSQL:
            conn.execute('BEGIN IMMEDIATE')
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if (u['balance'] + u['bonus_balance']) < stake: 
            return jsonify({'success': False, 'error': 'Insufficient balance!'})
        match = conn.execute('SELECT team1, team2 FROM matches WHERE id = ?', (mid,)).fetchone()
        deduct_stake(conn, session['user_id'], stake, u['balance'], u['bonus_balance'])
        conn.execute('INSERT INTO bets (user_id, match_id, match_name, team, odds, stake, profit, match_status, date) VALUES (?, ?, ?, ?, ?, ?, ?, "Open", ?)',
                     (session['user_id'], mid, f"{match['team1']} vs {match['team2']}" if match else f"ID: {mid}", team, odds, stake, (odds*stake)-stake, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return jsonify({'success': True, 'new_total': un['balance'] + un['bonus_balance']})

# ==========================================
# 5. ALL 37 GAME ROUTES
# ==========================================

@app.route('/spin')
def spin_game():
    if 'user_id' not in session: return redirect(url_for('login'))
    with get_db() as conn: 
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        spin_data = conn.execute('SELECT last_spin_time FROM daily_spins WHERE user_id = ?', (session['user_id'],)).fetchone()
        can_spin = True
        time_left = 0
        if spin_data:
            elapsed = time.time() - spin_data['last_spin_time']
            if elapsed < 86400: 
                can_spin = False
                time_left = int(86400 - elapsed)
        return render_template('spin.html', user=u, can_spin=can_spin, time_left=time_left)

@app.route('/spin/claim', methods=['POST'])
def spin_claim():
    if 'user_id' not in session: return jsonify({'success': False})
    uid = session['user_id']
    with get_db() as conn:
        spin_data = conn.execute('SELECT last_spin_time FROM daily_spins WHERE user_id = ?', (uid,)).fetchone()
        if spin_data and (time.time() - spin_data['last_spin_time']) < 86400: return jsonify({'success': False, 'error': 'Already spun!'})
        rand = random.random()
        prize = 500 if rand < 0.01 else 50 if rand < 0.10 else 10 if rand < 0.40 else 5 if rand < 0.85 else 0
        if prize > 0: conn.execute('UPDATE users SET bonus_balance = bonus_balance + ? WHERE id = ?', (prize, uid))
        if spin_data: conn.execute('UPDATE daily_spins SET last_spin_time = ? WHERE user_id = ?', (time.time(), uid))
        else: conn.execute('INSERT INTO daily_spins (user_id, last_spin_time) VALUES (?, ?)', (uid, time.time()))
        conn.commit()
        un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (uid,)).fetchone()
    return jsonify({'success': True, 'prize': prize, 'new_total': un['balance'] + un['bonus_balance']})

@app.route('/aviator')
def aviator_game():
    if 'user_id' not in session: return redirect(url_for('login'))
    with get_db() as conn: 
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return render_template('aviator.html', user=u)

@app.route('/aviator/sync')
def aviator_sync(): 
    update_aviator_state() 
    return jsonify({"state": AVIATOR_STATE["state"], "elapsed": time.time() - AVIATOR_STATE["start_time"], "crash_point": AVIATOR_STATE["crash_point"] if AVIATOR_STATE["state"] == "CRASHED" else None, "history": AVIATOR_STATE["history"], "match_number": f"{AVIATOR_STATE['match_number']:06d}"})

@app.route('/aviator/bet', methods=['POST'])
def aviator_bet():
    if 'user_id' not in session: return jsonify({'success': False})
    update_aviator_state()
    try: stake = float(request.json.get('stake', 0))
    except: return jsonify({'success': False})
    if stake < 10: return jsonify({'success': False, 'error': 'Min bet 10'})
    if AVIATOR_STATE["state"] != "WAITING" or session['user_id'] in ACTIVE_BETS: return jsonify({'success': False, 'error': 'Closed'})
    with get_db() as conn:
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if (u['balance'] + u['bonus_balance']) < stake: return jsonify({'success': False})
        deduct_stake(conn, session['user_id'], stake, u['balance'], u['bonus_balance'])
        conn.commit()
        ACTIVE_BETS[session['user_id']] = stake
        un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return jsonify({'success': True, 'new_total': un['balance'] + un['bonus_balance']})

@app.route('/aviator/cashout', methods=['POST'])
def aviator_cashout():
    if 'user_id' not in session: return jsonify({'success': False})
    update_aviator_state()
    if AVIATOR_STATE["state"] != "FLYING" or session['user_id'] not in ACTIVE_BETS: return jsonify({'success': False})
    m = 1.00 + ((time.time() - AVIATOR_STATE["start_time"]) ** 1.4) * 0.08
    if m >= AVIATOR_STATE["crash_point"]: return jsonify({'success': False})
    win = round(ACTIVE_BETS.pop(session['user_id']) * m, 2) 
    with get_db() as conn:
        conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (win, session['user_id']))
        conn.commit()
        un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return jsonify({'success': True, 'new_total': un['balance'] + un['bonus_balance'], 'winnings': win, 'multiplier': m})

@app.route('/jetx')
def jetx_game():
    if 'user_id' not in session: return redirect(url_for('login'))
    with get_db() as conn: 
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return render_template('jetx.html', user=u)

@app.route('/jetx/sync')
def jetx_sync():
    update_jetx_state()
    elapsed = time.time() - JETX_STATE["start_time"]
    current_mult = round(1.00 + (elapsed ** 1.35) * 0.09, 2) if JETX_STATE["state"] == "FLYING" else 1.00
    return jsonify({"state": JETX_STATE["state"], "multiplier": current_mult, "match_number": f"{JETX_STATE['match_number']:06d}", "crash_point": JETX_STATE["crash_point"] if JETX_STATE["state"] == "CRASHED" else None})

@app.route('/jetx/bet', methods=['POST'])
def jetx_bet():
    if 'user_id' not in session: return jsonify({'success': False})
    update_jetx_state()
    if JETX_STATE["state"] != "WAITING": return jsonify({'success': False})
    try: stake = float(request.json.get('stake', 0))
    except: return jsonify({'success': False})
    if stake < 10: return jsonify({'success': False})
    with get_db() as conn:
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if (u['balance'] + u['bonus_balance']) < stake: return jsonify({'success': False})
        deduct_stake(conn, session['user_id'], stake, u['balance'], u['bonus_balance'])
        conn.commit()
        JETX_BETS[session['user_id']] = stake
        un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return jsonify({'success': True, 'new_total': un['balance'] + un['bonus_balance']})

@app.route('/jetx/cashout', methods=['POST'])
def jetx_cashout():
    if 'user_id' not in session or session['user_id'] not in JETX_BETS: return jsonify({'success': False})
    update_jetx_state()
    if JETX_STATE["state"] != "FLYING": return jsonify({'success': False})
    elapsed = time.time() - JETX_STATE["start_time"]
    mult = round(1.00 + (elapsed ** 1.35) * 0.09, 2)
    if mult >= JETX_STATE["crash_point"]: return jsonify({'success': False})
    winnings = round(JETX_BETS.pop(session['user_id']) * mult, 2)
    with get_db() as conn:
        conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (winnings, session['user_id']))
        conn.commit()
        un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return jsonify({'success': True, 'winnings': winnings, 'new_total': un['balance'] + un['bonus_balance'], 'multiplier': mult})

@app.route('/plinko')
def plinko_game():
    if 'user_id' not in session: return redirect(url_for('login'))
    with get_db() as conn: 
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return render_template('plinko.html', user=u)

@app.route('/plinko/drop', methods=['POST'])
def plinko_drop():
    if 'user_id' not in session: return jsonify({'success': False})
    try: stake = float(request.json.get('stake', 0))
    except: return jsonify({'success': False})
    if stake < 10: return jsonify({'success': False})
    with get_db() as conn:
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if (u['balance'] + u['bonus_balance']) < stake: return jsonify({'success': False})
        deduct_stake(conn, session['user_id'], stake, u['balance'], u['bonus_balance'])
        path = [random.choice([0, 1]) for _ in range(12)]
        slot = sum(path)
        mult = [16, 9, 2, 1.4, 1.1, 1, 0.5, 1, 1.1, 1.4, 2, 9, 16][slot]
        winnings = round(stake * mult, 2)
        if winnings > 0: conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (winnings, session['user_id']))
        conn.commit()
        un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return jsonify({'success': True, 'path': path, 'slot': slot, 'multiplier': mult, 'winnings': winnings, 'new_total': un['balance'] + un['bonus_balance']})

@app.route('/blackjack')
def blackjack_game():
    if 'user_id' not in session: return redirect(url_for('login'))
    with get_db() as conn: 
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return render_template('blackjack.html', user=u)

@app.route('/blackjack/deal', methods=['POST'])
def bj_deal():
    uid = session.get('user_id')
    if not uid: return jsonify({'success': False})
    try: stake = float(request.json.get('stake', 0))
    except: return jsonify({'success': False})
    if stake < 10: return jsonify({'success': False})
    with get_db() as conn:
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (uid,)).fetchone()
        if (u['balance'] + u['bonus_balance']) < stake: return jsonify({'success': False})
        deduct_stake(conn, uid, stake, u['balance'], u['bonus_balance'])
        conn.commit()
        p, d = [draw_card(), draw_card()], [draw_card(), draw_card()]
        ACTIVE_BLACKJACK[uid] = {'stake': stake, 'player': p, 'dealer': d, 'status': 'PLAYING'}
        un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (uid,)).fetchone()
    return jsonify({'success': True, 'player': p, 'player_score': calc_hand(p), 'dealer_up': d[0], 'new_total': un['balance'] + un['bonus_balance']})

@app.route('/blackjack/hit', methods=['POST'])
def bj_hit():
    uid = session.get('user_id')
    if uid not in ACTIVE_BLACKJACK: return jsonify({'success': False})
    g = ACTIVE_BLACKJACK[uid]
    g['player'].append(draw_card())
    s = calc_hand(g['player'])
    if s > 21: del ACTIVE_BLACKJACK[uid]
    return jsonify({'success': True, 'player': g['player'] if s <= 21 else [], 'score': s, 'bust': s > 21})

@app.route('/blackjack/stand', methods=['POST'])
def bj_stand():
    uid = session.get('user_id')
    if uid not in ACTIVE_BLACKJACK: return jsonify({'success': False})
    g = ACTIVE_BLACKJACK.pop(uid)
    p_s, d_s = calc_hand(g['player']), calc_hand(g['dealer'])
    while d_s < 17:
        g['dealer'].append(draw_card())
        d_s = calc_hand(g['dealer'])
    win, push, mult = False, False, 2.0
    if p_s <= 21 and (d_s > 21 or p_s > d_s): win = True
    elif p_s == d_s: push = True
    w = (g['stake'] * mult) if win else (g['stake'] if push else 0)
    with get_db() as conn:
        if w > 0: conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (w, uid))
        conn.commit()
        un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (uid,)).fetchone()
    return jsonify({'success': True, 'dealer': g['dealer'], 'dealer_score': d_s, 'win': win, 'push': push, 'winnings': w, 'new_total': un['balance'] + un['bonus_balance']})

@app.route('/roulette')
def roulette_game():
    if 'user_id' not in session: return redirect(url_for('login'))
    with get_db() as conn: 
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return render_template('roulette.html', user=u)

@app.route('/roulette/spin', methods=['POST'])
def roulette_spin():
    if 'user_id' not in session: return jsonify({'success': False})
    try: stake = float(request.json.get('stake', 0))
    except: return jsonify({'success': False})
    bet_type = request.json.get('type')
    target = request.json.get('target')
    if stake < 10: return jsonify({'success': False})
    with get_db() as conn:
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if (u['balance'] + u['bonus_balance']) < stake: return jsonify({'success': False})
        deduct_stake(conn, session['user_id'], stake, u['balance'], u['bonus_balance'])
        r_num = random.randint(0, 36)
        col = "red" if r_num in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36] else ("black" if r_num != 0 else "green")
        win, p = False, 0
        if bet_type == "number" and int(target) == r_num: win, p = True, stake * 36
        elif bet_type == "red" and col == "red": win, p = True, stake * 2
        elif bet_type == "black" and col == "black": win, p = True, stake * 2
        elif bet_type == "even" and r_num != 0 and r_num % 2 == 0: win, p = True, stake * 2
        elif bet_type == "odd" and r_num % 2 != 0: win, p = True, stake * 2
        if win: conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (p, session['user_id']))
        conn.commit()
        un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return jsonify({'success': True, 'number': r_num, 'color': col, 'win': win, 'winnings': p, 'new_total': un['balance'] + un['bonus_balance']})

@app.route('/baccarat')
def baccarat_game():
    if 'user_id' not in session: return redirect(url_for('login'))
    with get_db() as conn: 
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return render_template('baccarat.html', user=u)

@app.route('/baccarat/deal', methods=['POST'])
def baccarat_deal():
    if 'user_id' not in session: return jsonify({'success': False})
    try: stake = float(request.json.get('stake', 0))
    except: return jsonify({'success': False})
    choice = request.json.get('choice')
    if stake < 10: return jsonify({'success': False})
    with get_db() as conn:
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if (u['balance'] + u['bonus_balance']) < stake: return jsonify({'success': False})
        deduct_stake(conn, session['user_id'], stake, u['balance'], u['bonus_balance'])
        p_val = (random.randint(1, 9) + random.randint(1, 9)) % 10
        b_val = (random.randint(1, 9) + random.randint(1, 9)) % 10
        out = 'Tie' if p_val == b_val else ('Player' if p_val > b_val else 'Banker')
        win = (out == choice)
        p = (stake * (8.0 if out == 'Tie' else (1.95 if out == 'Banker' else 2.0))) if win else 0
        if win: conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (p, session['user_id']))
        conn.commit()
        un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return jsonify({'success': True, 'player_score': p_val, 'banker_score': b_val, 'winner': out, 'win': win, 'winnings': p, 'new_total': un['balance'] + un['bonus_balance']})

@app.route('/craps')
def craps_game():
    if 'user_id' not in session: return redirect(url_for('login'))
    with get_db() as conn: 
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return render_template('craps.html', user=u)

@app.route('/craps/roll', methods=['POST'])
def craps_roll():
    if 'user_id' not in session: return jsonify({'success': False})
    try: stake = float(request.json.get('stake', 0))
    except: return jsonify({'success': False})
    choice = request.json.get('choice')
    if stake < 10: return jsonify({'success': False})
    with get_db() as conn:
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if (u['balance'] + u['bonus_balance']) < stake: return jsonify({'success': False})
        deduct_stake(conn, session['user_id'], stake, u['balance'], u['bonus_balance'])
        d1, d2 = random.randint(1, 6), random.randint(1, 6)
        tot = d1 + d2
        win = (tot in [7, 11]) if choice == 'Pass' else (tot in [2, 3, 12])
        p = (stake * 2.0) if win else 0
        if win: conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (p, session['user_id']))
        conn.commit()
        un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return jsonify({'success': True, 'dice1': d1, 'dice2': d2, 'total': tot, 'win': win, 'winnings': p, 'new_total': un['balance'] + un['bonus_balance']})

@app.route('/poker')
def poker_game():
    if 'user_id' not in session: return redirect(url_for('login'))
    with get_db() as conn: 
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return render_template('poker.html', user=u)

@app.route('/poker/play', methods=['POST'])
def poker_play():
    if 'user_id' not in session: return jsonify({'success': False})
    try: stake = float(request.json.get('stake', 0))
    except: return jsonify({'success': False})
    if stake < 10: return jsonify({'success': False})
    with get_db() as conn:
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if (u['balance'] + u['bonus_balance']) < stake: return jsonify({'success': False})
        deduct_stake(conn, session['user_id'], stake, u['balance'], u['bonus_balance'])
        c = [draw_card() for _ in range(5)]
        r = [card['rank'] for card in c]
        mult = 0
        h_n = "High Card (No Win)"
        if any(r.count(x) == 4 for x in r): mult, h_n = 25, "Four of a Kind"
        elif any(r.count(x) == 3 for x in r) and any(r.count(x) == 2 for x in r): mult, h_n = 9, "Full House"
        elif any(r.count(x) == 3 for x in r): mult, h_n = 3, "Three of a Kind"
        elif [r.count(x) for x in r].count(2) == 4: mult, h_n = 2, "Two Pair"
        elif any(x in ['J', 'Q', 'K', 'A'] and r.count(x) == 2 for x in r): mult, h_n = 1.5, "Jacks or Better"
        w = round(stake * mult, 2)
        if w > 0: conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (w, session['user_id']))
        conn.commit()
        un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return jsonify({'success': True, 'cards': c, 'hand': h_n, 'multiplier': mult, 'winnings': w, 'new_total': un['balance'] + un['bonus_balance']})

@app.route('/andar_bahar')
def andar_bahar_game():
    if 'user_id' not in session: return redirect(url_for('login'))
    with get_db() as conn: 
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return render_template('andar_bahar.html', user=u)

@app.route('/andar_bahar/deal', methods=['POST'])
def andar_bahar_deal():
    if 'user_id' not in session: return jsonify({'success': False})
    try: stake = float(request.json.get('stake', 0))
    except: return jsonify({'success': False})
    side = request.json.get('side')
    if stake < 10: return jsonify({'success': False})
    with get_db() as conn:
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if (u['balance'] + u['bonus_balance']) < stake: return jsonify({'success': False})
        deduct_stake(conn, session['user_id'], stake, u['balance'], u['bonus_balance'])
        j = draw_card()
        w_s = random.choice(['Andar', 'Bahar'])
        win = (side == w_s)
        w = round(stake * 1.95, 2) if win else 0
        if win: conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (w, session['user_id']))
        conn.commit()
        un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return jsonify({'success': True, 'joker': j, 'winner': w_s, 'win': win, 'winnings': w, 'new_total': un['balance'] + un['bonus_balance']})

@app.route('/teen_patti')
def teen_patti_game():
    if 'user_id' not in session: return redirect(url_for('login'))
    with get_db() as conn: 
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return render_template('teen_patti.html', user=u)

@app.route('/teen_patti/play', methods=['POST'])
def teen_patti_play():
    if 'user_id' not in session: return jsonify({'success': False})
    try: stake = float(request.json.get('stake', 0))
    except: return jsonify({'success': False})
    if stake < 10: return jsonify({'success': False})
    with get_db() as conn:
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if (u['balance'] + u['bonus_balance']) < stake: return jsonify({'success': False})
        deduct_stake(conn, session['user_id'], stake, u['balance'], u['bonus_balance'])
        p_c = [draw_card() for _ in range(3)]
        d_c = [draw_card() for _ in range(3)]
        win = random.random() < 0.48
        w = round(stake * 1.95, 2) if win else 0
        if win: conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (w, session['user_id']))
        conn.commit()
        un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return jsonify({'success': True, 'player': p_c, 'dealer': d_c, 'win': win, 'winnings': w, 'new_total': un['balance'] + un['bonus_balance']})

@app.route('/limbo')
def limbo_game():
    if 'user_id' not in session: return redirect(url_for('login'))
    with get_db() as conn: 
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return render_template('limbo.html', user=u)

@app.route('/limbo/play', methods=['POST'])
def limbo_play():
    if 'user_id' not in session: return jsonify({'success': False})
    try: 
        stake = float(request.json.get('stake', 0))
        target = float(request.json.get('target', 2.0))
    except: return jsonify({'success': False})
    if stake < 10: return jsonify({'success': False})
    if target < 1.01 or target > 1000: return jsonify({'success': False})
    with get_db() as conn:
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if (u['balance'] + u['bonus_balance']) < stake: return jsonify({'success': False})
        deduct_stake(conn, session['user_id'], stake, u['balance'], u['bonus_balance'])
        roll = round(random.uniform(1.00, target * 1.5 if random.random() > 0.52 else target * 0.9), 2)
        win = (roll >= target)
        w = round(stake * target, 2) if win else 0
        if win: conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (w, session['user_id']))
        conn.commit()
        un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return jsonify({'success': True, 'roll': roll, 'target': target, 'win': win, 'winnings': w, 'new_total': un['balance'] + un['bonus_balance']})

@app.route('/dragon_tiger')
def dragon_tiger_game():
    if 'user_id' not in session: return redirect(url_for('login'))
    with get_db() as conn: 
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return render_template('dragon_tiger.html', user=u)

@app.route('/dragon_tiger/sync')
def dragon_tiger_sync(): 
    update_dt_state()
    return jsonify({"state": DT_STATE["state"], "elapsed": time.time() - DT_STATE["start_time"], "d_card": DT_STATE["d_card"] if DT_STATE["state"] == "REVEAL" else 0, "t_card": DT_STATE["t_card"] if DT_STATE["state"] == "REVEAL" else 0, "result": DT_STATE["result"] if DT_STATE["state"] == "REVEAL" else None, "history": DT_STATE["history"], "match_number": f"{DT_STATE['match_number']:06d}"})

@app.route('/dragon_tiger/bet', methods=['POST'])
def dragon_tiger_bet():
    if 'user_id' not in session: return jsonify({'success': False})
    update_dt_state()
    try: stake = float(request.json.get('stake', 0))
    except: return jsonify({'success': False})
    target = request.json.get('target')
    if stake < 10: return jsonify({'success': False})
    if target not in ["Dragon", "Tiger", "Tie"]: return jsonify({'success': False})
    if DT_STATE["state"] != "WAITING" or session['user_id'] in DT_BETS: return jsonify({'success': False})
    with get_db() as conn:
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if (u['balance'] + u['bonus_balance']) < stake: return jsonify({'success': False})
        deduct_stake(conn, session['user_id'], stake, u['balance'], u['bonus_balance'])
        conn.commit()
        un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        DT_BETS[session['user_id']] = {'target': target, 'stake': stake}
    return jsonify({'success': True, 'new_total': un['balance'] + un['bonus_balance']})

@app.route('/heads_tails')
def heads_tails_game():
    if 'user_id' not in session: return redirect(url_for('login'))
    with get_db() as conn: 
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return render_template('heads_tails.html', user=u)

@app.route('/heads_tails/sync')
def heads_tails_sync(): 
    update_ht_state() 
    return jsonify({"state": HT_STATE["state"], "elapsed": time.time() - HT_STATE["start_time"], "result": HT_STATE["result"] if HT_STATE["state"] == "FLIPPING" else None, "history": HT_STATE["history"], "match_number": f"{HT_STATE['match_number']:06d}"})

@app.route('/heads_tails/bet', methods=['POST'])
def heads_tails_bet():
    if 'user_id' not in session: return jsonify({'success': False})
    update_ht_state()
    try: stake = float(request.json.get('stake', 0))
    except: return jsonify({'success': False})
    target = request.json.get('target')
    if stake < 10: return jsonify({'success': False})
    if target not in ["Heads", "Tails"]: return jsonify({'success': False})
    if HT_STATE["state"] != "WAITING" or session['user_id'] in HT_BETS: return jsonify({'success': False})
    with get_db() as conn:
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if (u['balance'] + u['bonus_balance']) < stake: return jsonify({'success': False})
        deduct_stake(conn, session['user_id'], stake, u['balance'], u['bonus_balance'])
        conn.commit()
        un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        HT_BETS[session['user_id']] = {'target': target, 'stake': stake}
    return jsonify({'success': True, 'new_total': un['balance'] + un['bonus_balance']})

@app.route('/color_prediction')
def color_prediction_game():
    if 'user_id' not in session: return redirect(url_for('login'))
    with get_db() as conn: 
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return render_template('color_prediction.html', user=u)

@app.route('/color_prediction/sync')
def color_prediction_sync(): 
    update_cp_state() 
    return jsonify({"state": CP_STATE["state"], "elapsed": time.time() - CP_STATE["start_time"], "result_number": CP_STATE["result_number"] if CP_STATE["state"] == "REVEAL" else -1, "result_color": CP_STATE["result_color"] if CP_STATE["state"] == "REVEAL" else "", "history": CP_STATE["history"], "match_number": f"{CP_STATE['match_number']:06d}"})

@app.route('/color_prediction/bet', methods=['POST'])
def color_prediction_bet():
    if 'user_id' not in session: return jsonify({'success': False})
    update_cp_state()
    try: stake = float(request.json.get('stake', 0))
    except: return jsonify({'success': False})
    target = request.json.get('target')
    if stake < 10: return jsonify({'success': False})
    if CP_STATE["state"] != "WAITING" or session['user_id'] in CP_BETS: return jsonify({'success': False})
    with get_db() as conn:
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if (u['balance'] + u['bonus_balance']) < stake: return jsonify({'success': False})
        deduct_stake(conn, session['user_id'], stake, u['balance'], u['bonus_balance'])
        conn.commit()
        un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        CP_BETS[session['user_id']] = {'target': target, 'stake': stake}
    return jsonify({'success': True, 'new_total': un['balance'] + un['bonus_balance']})

@app.route('/mines')
def mines_game():
    if 'user_id' not in session: return redirect(url_for('login'))
    with get_db() as conn: 
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return render_template('mines.html', user=u)

@app.route('/mines/start', methods=['POST'])
def mines_start():
    if 'user_id' not in session: return jsonify({'success': False})
    uid = session['user_id']
    try:
        stake = float(request.json.get('stake', 0))
        mines_count = int(request.json.get('mines', 3))
    except: return jsonify({'success': False})
    if stake < 10: return jsonify({'success': False})
    if mines_count not in [3, 5, 10]: return jsonify({'success': False})
    client_seed = request.json.get('client_seed', 'novabetx_player')
    if uid in ACTIVE_MINES: return jsonify({'success': False})
    with get_db() as conn:
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (uid,)).fetchone()
        if (u['balance'] + u['bonus_balance']) < stake: return jsonify({'success': False})
        deduct_stake(conn, uid, stake, u['balance'], u['bonus_balance'])
        conn.commit()
        un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (uid,)).fetchone()
        server_seed = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        server_hash = hashlib.sha256(server_seed.encode()).hexdigest()
        random.seed(f"{server_seed}-{client_seed}")
        grid = [0]*25
        for i in random.sample(range(25), mines_count): grid[i] = 1 
        random.seed() 
        ACTIVE_MINES[uid] = {'grid': grid, 'stake': stake, 'mines': mines_count, 'cleared': 0, 'server_seed': server_seed, 'clicked': []}
    return jsonify({'success': True, 'new_total': un['balance'] + un['bonus_balance'], 'server_hash': server_hash})

@app.route('/mines/click', methods=['POST'])
def mines_click():
    if 'user_id' not in session: return jsonify({'success': False})
    uid = session['user_id']
    try: idx = int(request.json.get('index'))
    except: return jsonify({'success': False})
    if idx < 0 or idx > 24: return jsonify({'success': False})
    if uid not in ACTIVE_MINES: return jsonify({'success': False})
    game = ACTIVE_MINES[uid]
    if idx in game['clicked']: return jsonify({'success': False})
    game['clicked'].append(idx)
    if game['grid'][idx] == 1: 
        server_seed = game['server_seed']
        del ACTIVE_MINES[uid]
        return jsonify({'success': True, 'bomb': True, 'grid': game['grid'], 'server_seed': server_seed})
    else: 
        game['cleared'] += 1
        return jsonify({'success': True, 'bomb': False, 'multiplier': round(1.0 + (game['cleared'] * 0.15 * (game['mines']/3)), 2)})

@app.route('/mines/cashout', methods=['POST'])
def mines_cashout():
    if 'user_id' not in session: return jsonify({'success': False})
    uid = session['user_id']
    if uid not in ACTIVE_MINES or ACTIVE_MINES[uid]['cleared'] == 0: return jsonify({'success': False})
    game = ACTIVE_MINES.pop(uid) 
    mult = round(1.0 + (game['cleared'] * 0.15 * (game['mines']/3)), 2)
    win = round(game['stake'] * mult, 2)
    server_seed = game['server_seed']
    with get_db() as conn: 
        conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (win, uid))
        conn.commit()
        un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (uid,)).fetchone()
    return jsonify({'success': True, 'new_total': un['balance'] + un['bonus_balance'], 'winnings': win, 'server_seed': server_seed})

@app.route('/dice')
def dice_game():
    if 'user_id' not in session: return redirect(url_for('login'))
    with get_db() as conn: 
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return render_template('dice.html', user=u)

@app.route('/dice/roll', methods=['POST'])
def dice_roll():
    if 'user_id' not in session: return jsonify({'success': False})
    uid = session['user_id']
    try: 
        stake = float(request.json.get('stake', 0))
        target = float(request.json.get('target', 50))
    except: return jsonify({'success': False})
    condition = request.json.get('condition') 
    if condition not in ['over', 'under']: return jsonify({'success': False})
    if stake < 10: return jsonify({'success': False})
    if target < 2 or target > 98: return jsonify({'success': False})
    client_seed = request.json.get('client_seed', 'novabetx_player')
    with get_db() as conn:
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (uid,)).fetchone()
        if (u['balance'] + u['bonus_balance']) < stake: return jsonify({'success': False})
        deduct_stake(conn, uid, stake, u['balance'], u['bonus_balance'])
        server_seed = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        combo = f"{server_seed}-{client_seed}"
        hash_result = hashlib.sha256(combo.encode()).hexdigest()
        roll = (int(hash_result[:8], 16) % 10001) / 100.0
        win = False
        if condition == "over" and roll > target: win = True
        elif condition == "under" and roll < target: win = True
        chance = (100.0 - target) if condition == "over" else target
        mult = round(99.0 / chance, 2) if chance > 0 else 1.01
        winnings = round(stake * mult, 2) if win else 0
        if win: conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (winnings, uid))
        conn.commit()
        un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (uid,)).fetchone()
    return jsonify({'success': True, 'roll': roll, 'win': win, 'multiplier': mult, 'winnings': winnings, 'new_total': un['balance'] + un['bonus_balance'], 'server_seed': server_seed, 'hash': hash_result})

@app.route('/seven_up_down')
def seven_up_down_game():
    if 'user_id' not in session: return redirect(url_for('login'))
    with get_db() as conn: 
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return render_template('seven_up_down.html', user=u)

@app.route('/seven_up_down/roll', methods=['POST'])
def seven_up_down_roll():
    if 'user_id' not in session: return jsonify({'success': False})
    try: stake = float(request.json.get('stake', 0))
    except: return jsonify({'success': False})
    target = request.json.get('choice')
    if stake < 10: return jsonify({'success': False})
    with get_db() as conn:
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if (u['balance'] + u['bonus_balance']) < stake: return jsonify({'success': False})
        deduct_stake(conn, session['user_id'], stake, u['balance'], u['bonus_balance'])
        d1 = random.randint(1, 6)
        d2 = random.randint(1, 6)
        total = d1 + d2
        result = '7Down' if total < 7 else ('7Up' if total > 7 else '7')
        win = (target == result)
        mult = 5.0 if result == '7' else 2.0
        winnings = round(stake * mult, 2) if win else 0
        if win: conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (winnings, session['user_id']))
        conn.commit()
        un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return jsonify({'success': True, 'd1': d1, 'd2': d2, 'total': total, 'result': result, 'win': win, 'winnings': winnings, 'new_total': un['balance'] + un['bonus_balance']})

@app.route('/penalty')
def penalty_game():
    if 'user_id' not in session: return redirect(url_for('login'))
    with get_db() as conn: 
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return render_template('penalty.html', user=u)

@app.route('/penalty/shoot', methods=['POST'])
def penalty_shoot():
    if 'user_id' not in session: return jsonify({'success': False})
    try:
        stake = float(request.json.get('stake', 0))
        target_zone = int(request.json.get('zone', 1))
    except: return jsonify({'success': False})
    if stake < 10: return jsonify({'success': False})
    with get_db() as conn:
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if (u['balance'] + u['bonus_balance']) < stake: return jsonify({'success': False})
        deduct_stake(conn, session['user_id'], stake, u['balance'], u['bonus_balance'])
        keeper_save_zone = random.randint(1, 5)
        goal = (target_zone != keeper_save_zone)
        winnings = round(stake * 1.95, 2) if goal else 0
        if goal: conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (winnings, session['user_id']))
        conn.commit()
        un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return jsonify({'success': True, 'goal': goal, 'keeper_zone': keeper_save_zone, 'winnings': winnings, 'new_total': un['balance'] + un['bonus_balance']})

@app.route('/hilo')
def hilo_game():
    if 'user_id' not in session: return redirect(url_for('login'))
    with get_db() as conn: 
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return render_template('hilo.html', user=u)

@app.route('/hilo/play', methods=['POST'])
def hilo_play():
    if 'user_id' not in session: return jsonify({'success': False})
    try:
        stake = float(request.json.get('stake', 0))
        guess = request.json.get('guess')
        current_val = int(request.json.get('current_card', 7))
    except: return jsonify({'success': False})
    if stake < 10: return jsonify({'success': False})
    with get_db() as conn:
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if (u['balance'] + u['bonus_balance']) < stake: return jsonify({'success': False})
        deduct_stake(conn, session['user_id'], stake, u['balance'], u['bonus_balance'])
        next_val = random.randint(1, 13)
        win = False
        mult = 1.95
        if guess == 'higher' and next_val > current_val: win = True
        elif guess == 'lower' and next_val < current_val: win = True
        elif guess == 'same' and next_val == current_val: 
            win = True
            mult = 11.0
        winnings = round(stake * mult, 2) if win else 0
        if win: conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (winnings, session['user_id']))
        conn.commit()
        un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return jsonify({'success': True, 'next_card': next_val, 'win': win, 'winnings': winnings, 'new_total': un['balance'] + un['bonus_balance']})

@app.route('/slots')
def slots_game():
    if 'user_id' not in session: return redirect(url_for('login'))
    with get_db() as conn: 
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return render_template('slots.html', user=u)

@app.route('/slots/spin', methods=['POST'])
def slots_spin():
    if 'user_id' not in session: return jsonify({'success': False})
    try: stake = float(request.json.get('stake', 0))
    except: return jsonify({'success': False})
    if stake < 10: return jsonify({'success': False})
    with get_db() as conn:
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if (u['balance'] + u['bonus_balance']) < stake: return jsonify({'success': False})
        deduct_stake(conn, session['user_id'], stake, u['balance'], u['bonus_balance'])
        syms = ['🍒', '🍋', '🍇', '🔔', 'BAR', '777']
        weights = [35, 25, 18, 12, 7, 3]
        r1 = random.choices(syms, weights=weights)[0]
        r2 = random.choices(syms, weights=weights)[0]
        r3 = random.choices(syms, weights=weights)[0]
        mult = 0
        if r1 == r2 == r3: mult = {'🍒': 5, '🍋': 8, '🍇': 12, '🔔': 20, 'BAR': 35, '777': 100}[r1]
        elif r1 == r2 or r2 == r3 or r1 == r3: mult = 1.5
        winnings = round(stake * mult, 2)
        if winnings > 0: conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (winnings, session['user_id']))
        conn.commit()
        un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return jsonify({'success': True, 'reels': [r1, r2, r3], 'multiplier': mult, 'winnings': winnings, 'new_total': un['balance'] + un['bonus_balance']})

@app.route('/thimbles')
def thimbles_game():
    if 'user_id' not in session: return redirect(url_for('login'))
    with get_db() as conn: 
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return render_template('thimbles.html', user=u)

@app.route('/thimbles/play', methods=['POST'])
def thimbles_play():
    if 'user_id' not in session: return jsonify({'success': False})
    try:
        stake = float(request.json.get('stake', 0))
        guess_cup = int(request.json.get('cup', 0))
    except: return jsonify({'success': False})
    if stake < 10: return jsonify({'success': False})
    with get_db() as conn:
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if (u['balance'] + u['bonus_balance']) < stake: return jsonify({'success': False})
        deduct_stake(conn, session['user_id'], stake, u['balance'], u['bonus_balance'])
        ball_cup = random.randint(0, 2)
        win = (guess_cup == ball_cup)
        winnings = round(stake * 2.85, 2) if win else 0
        if win: conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (winnings, session['user_id']))
        conn.commit()
        un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return jsonify({'success': True, 'ball_cup': ball_cup, 'win': win, 'winnings': winnings, 'new_total': un['balance'] + un['bonus_balance']})

@app.route('/tower')
def tower_game():
    if 'user_id' not in session: return redirect(url_for('login'))
    with get_db() as conn: 
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return render_template('tower.html', user=u)

@app.route('/tower/step', methods=['POST'])
def tower_step():
    if 'user_id' not in session: return jsonify({'success': False})
    try:
        stake = float(request.json.get('stake', 0))
        tier = int(request.json.get('tier', 1))
        pick_tile = int(request.json.get('tile', 0))
    except: return jsonify({'success': False})
    if stake < 10: return jsonify({'success': False})
    with get_db() as conn:
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if (u['balance'] + u['bonus_balance']) < stake: return jsonify({'success': False})
        if tier == 1: 
            deduct_stake(conn, session['user_id'], stake, u['balance'], u['bonus_balance'])
            conn.commit()
        broken_tile = random.choice([0, 1])
        safe = (pick_tile != broken_tile)
        step_mult = [1.3, 1.7, 2.3, 3.1, 4.2, 5.8, 8.0, 12.0][tier - 1] if safe else 0
        winnings = round(stake * step_mult, 2) if safe else 0
        un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return jsonify({'success': True, 'safe': safe, 'broken_tile': broken_tile, 'tier': tier, 'multiplier': step_mult, 'winnings': winnings, 'new_total': un['balance'] + un['bonus_balance']})

@app.route('/tower/cashout', methods=['POST'])
def tower_cashout():
    if 'user_id' not in session: return jsonify({'success': False})
    try: winnings = float(request.json.get('winnings', 0))
    except: return jsonify({'success': False})
    if winnings > 0:
        with get_db() as conn:
            conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (winnings, session['user_id']))
            conn.commit()
            un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        return jsonify({'success': True, 'new_total': un['balance'] + un['bonus_balance']})
    return jsonify({'success': False})

@app.route('/keno')
def keno_game():
    if 'user_id' not in session: return redirect(url_for('login'))
    with get_db() as conn: 
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return render_template('keno.html', user=u)

@app.route('/keno/draw', methods=['POST'])
def keno_draw():
    if 'user_id' not in session: return jsonify({'success': False})
    try:
        stake = float(request.json.get('stake', 0))
        chosen_numbers = [int(n) for n in request.json.get('numbers', [])][:5]
    except: return jsonify({'success': False})
    if stake < 10 or len(chosen_numbers) != 5: return jsonify({'success': False})
    with get_db() as conn:
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if (u['balance'] + u['bonus_balance']) < stake: return jsonify({'success': False})
        deduct_stake(conn, session['user_id'], stake, u['balance'], u['bonus_balance'])
        drawn_balls = random.sample(range(1, 31), 8)
        matches = len(set(chosen_numbers).intersection(drawn_balls))
        mult = {0: 0, 1: 0, 2: 1.5, 3: 4.0, 4: 15.0, 5: 50.0}.get(matches, 0)
        winnings = round(stake * mult, 2)
        if winnings > 0: conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (winnings, session['user_id']))
        conn.commit()
        un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return jsonify({'success': True, 'drawn': drawn_balls, 'matches': matches, 'multiplier': mult, 'winnings': winnings, 'new_total': un['balance'] + un['bonus_balance']})

@app.route('/wheel')
def wheel_game():
    if 'user_id' not in session: return redirect(url_for('login'))
    with get_db() as conn: 
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return render_template('wheel.html', user=u)

@app.route('/wheel/spin', methods=['POST'])
def wheel_spin():
    if 'user_id' not in session: return jsonify({'success': False})
    try: stake = float(request.json.get('stake', 0))
    except: return jsonify({'success': False})
    if stake < 10: return jsonify({'success': False})
    with get_db() as conn:
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if (u['balance'] + u['bonus_balance']) < stake: return jsonify({'success': False})
        deduct_stake(conn, session['user_id'], stake, u['balance'], u['bonus_balance'])
        segments = [1.2, 1.5, 1.2, 2.0, 0.0, 1.5, 3.0, 1.2, 5.0, 0.0, 1.5, 10.0]
        picked_idx = random.randint(0, 11)
        mult = segments[picked_idx]
        winnings = round(stake * mult, 2)
        if winnings > 0: conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (winnings, session['user_id']))
        conn.commit()
        un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return jsonify({'success': True, 'segment_index': picked_idx, 'multiplier': mult, 'winnings': winnings, 'new_total': un['balance'] + un['bonus_balance']})

@app.route('/jhandi_munda')
def jhandi_munda_game():
    if 'user_id' not in session: return redirect(url_for('login'))
    with get_db() as conn: 
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return render_template('jhandi_munda.html', user=u)

@app.route('/jhandi_munda/roll', methods=['POST'])
def jhandi_munda_roll():
    if 'user_id' not in session: return jsonify({'success': False})
    try: stake = float(request.json.get('stake', 0))
    except: return jsonify({'success': False})
    choice = request.json.get('symbol')
    if stake < 10: return jsonify({'success': False})
    with get_db() as conn:
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if (u['balance'] + u['bonus_balance']) < stake: return jsonify({'success': False})
        deduct_stake(conn, session['user_id'], stake, u['balance'], u['bonus_balance'])
        rolls = [random.choice(['Heart', 'Spade', 'Club', 'Diamond', 'Flag', 'Crown']) for _ in range(6)]
        matches = rolls.count(choice)
        mult = 0
        if matches == 1: mult = 1.0 
        elif matches > 1: mult = matches + 1 
        winnings = round(stake * mult, 2)
        if winnings > 0: conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (winnings, session['user_id']))
        conn.commit()
        un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return jsonify({'success': True, 'rolls': rolls, 'matches': matches, 'multiplier': mult, 'winnings': winnings, 'new_total': un['balance'] + un['bonus_balance']})

@app.route('/coin_field')
def coin_field_game():
    if 'user_id' not in session: return redirect(url_for('login'))
    with get_db() as conn: 
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return render_template('coin_field.html', user=u)

@app.route('/coin_field/step', methods=['POST'])
def coin_field_step():
    if 'user_id' not in session: return jsonify({'success': False})
    try:
        stake = float(request.json.get('stake', 0))
        lane = int(request.json.get('lane', 0))
        step_num = int(request.json.get('step', 1))
    except: return jsonify({'success': False})
    if stake < 10: return jsonify({'success': False})
    with get_db() as conn:
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if (u['balance'] + u['bonus_balance']) < stake: return jsonify({'success': False})
        if step_num == 1: 
            deduct_stake(conn, session['user_id'], stake, u['balance'], u['bonus_balance'])
            conn.commit()
        mine_lane = random.choice([0, 1, 2])
        safe = (lane != mine_lane)
        mult = round(1.0 + (step_num * 0.45), 2) if safe else 0
        winnings = round(stake * mult, 2) if safe else 0
        un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return jsonify({'success': True, 'safe': safe, 'mine_lane': mine_lane, 'multiplier': mult, 'winnings': winnings, 'new_total': un['balance'] + un['bonus_balance']})

@app.route('/scratch')
def scratch_game():
    if 'user_id' not in session: return redirect(url_for('login'))
    with get_db() as conn: 
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return render_template('scratch.html', user=u)

@app.route('/scratch/play', methods=['POST'])
def scratch_play():
    if 'user_id' not in session: return jsonify({'success': False})
    try: stake = float(request.json.get('stake', 0))
    except: return jsonify({'success': False})
    if stake < 10: return jsonify({'success': False})
    with get_db() as conn:
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if (u['balance'] + u['bonus_balance']) < stake: return jsonify({'success': False})
        deduct_stake(conn, session['user_id'], stake, u['balance'], u['bonus_balance'])
        grid = [random.choices(['🍒', '🍋', '💎', '💰', '7️⃣'], weights=[40, 30, 15, 10, 5])[0] for _ in range(9)]
        counts = {s: grid.count(s) for s in set(grid)}
        win_symbol = next((s for s, count in counts.items() if count >= 3), None)
        mult = {'🍒': 1.5, '🍋': 2.5, '💎': 5.0, '💰': 10.0, '7️⃣': 50.0}.get(win_symbol, 0) if win_symbol else 0
        winnings = round(stake * mult, 2)
        if winnings > 0: conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (winnings, session['user_id']))
        conn.commit()
        un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return jsonify({'success': True, 'grid': grid, 'win': winnings > 0, 'winnings': winnings, 'multiplier': mult, 'new_total': un['balance'] + un['bonus_balance']})

@app.route('/casino_war')
def casino_war_game():
    if 'user_id' not in session: return redirect(url_for('login'))
    with get_db() as conn: 
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return render_template('casino_war.html', user=u)

@app.route('/casino_war/play', methods=['POST'])
def casino_war_play():
    if 'user_id' not in session: return jsonify({'success': False})
    try: stake = float(request.json.get('stake', 0))
    except: return jsonify({'success': False})
    if stake < 10: return jsonify({'success': False})
    with get_db() as conn:
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if (u['balance'] + u['bonus_balance']) < stake: return jsonify({'success': False})
        deduct_stake(conn, session['user_id'], stake, u['balance'], u['bonus_balance'])
        player = draw_card()
        dealer = draw_card()
        rank_vals = {'2':2,'3':3,'4':4,'5':5,'6':6,'7':7,'8':8,'9':9,'10':10,'J':11,'Q':12,'K':13,'A':14}
        p_val = rank_vals[player['rank']]
        d_val = rank_vals[dealer['rank']]
        mult = 2.0 if p_val > d_val else (10.0 if p_val == d_val else 0)
        winnings = round(stake * mult, 2)
        if winnings > 0: conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (winnings, session['user_id']))
        conn.commit()
        un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return jsonify({'success': True, 'player': player, 'dealer': dealer, 'win': p_val >= d_val, 'winnings': winnings, 'new_total': un['balance'] + un['bonus_balance']})

@app.route('/horse_racing')
def horse_racing_game():
    if 'user_id' not in session: return redirect(url_for('login'))
    with get_db() as conn: 
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return render_template('horse_racing.html', user=u)

@app.route('/horse_racing/race', methods=['POST'])
def horse_racing_race():
    if 'user_id' not in session: return jsonify({'success': False})
    try:
        stake = float(request.json.get('stake', 0))
        horse = int(request.json.get('horse', 1)) 
    except: return jsonify({'success': False})
    if stake < 10: return jsonify({'success': False})
    with get_db() as conn:
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if (u['balance'] + u['bonus_balance']) < stake: return jsonify({'success': False})
        deduct_stake(conn, session['user_id'], stake, u['balance'], u['bonus_balance'])
        winner = random.randint(1, 4)
        win = (horse == winner)
        winnings = round(stake * 3.8, 2) if win else 0
        if win: conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (winnings, session['user_id']))
        conn.commit()
        un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return jsonify({'success': True, 'winner': winner, 'win': win, 'winnings': winnings, 'new_total': un['balance'] + un['bonus_balance']})


# ==========================================
# 🎮 THE MISSING 7 GAME ROUTES
# ==========================================

@app.route('/russian_roulette')
def russian_roulette_game():
    if 'user_id' not in session: return redirect(url_for('login'))
    with get_db() as conn: 
        user_data = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return render_template('russian_roulette.html', user=user_data)

@app.route('/russian_roulette/play', methods=['POST'])
def russian_roulette_play():
    if 'user_id' not in session: return jsonify({'success': False})
    try:
        stake = float(request.json.get('stake', 0))
        step = int(request.json.get('step', 1))
    except: return jsonify({'success': False})
    if stake < 10: return jsonify({'success': False, 'error': 'Min bet 10'})
    with get_db() as conn:
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if step == 1:
            if (u['balance'] + u['bonus_balance']) < stake: return jsonify({'success': False, 'error': 'Insufficient funds'})
            deduct_stake(conn, session['user_id'], stake, u['balance'], u['bonus_balance'])
            conn.commit()
        survived = random.randint(1, 7 - step) != 1
        mults = [1.0, 1.2, 1.5, 2.0, 3.0, 5.0]
        mult = mults[step] if survived else 0
        winnings = round(stake * mult, 2) if survived else 0
        un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return jsonify({'success': True, 'survived': survived, 'winnings': winnings, 'multiplier': mult, 'new_total': un['balance'] + un['bonus_balance']})

@app.route('/russian_roulette/cashout', methods=['POST'])
def russian_roulette_cashout():
    if 'user_id' not in session: return jsonify({'success': False})
    try: winnings = float(request.json.get('winnings', 0))
    except: return jsonify({'success': False})
    if winnings > 0:
        with get_db() as conn:
            conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (winnings, session['user_id']))
            conn.commit()
            un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        return jsonify({'success': True, 'new_total': un['balance'] + un['bonus_balance']})
    return jsonify({'success': False})

@app.route('/safes')
def safes_game():
    if 'user_id' not in session: return redirect(url_for('login'))
    with get_db() as conn: 
        user_data = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return render_template('safes.html', user=user_data)

@app.route('/safes/open', methods=['POST'])
def safes_open():
    if 'user_id' not in session: return jsonify({'success': False})
    try:
        stake = float(request.json.get('stake', 0))
        safe_choice = int(request.json.get('safe', 0))
    except: return jsonify({'success': False})
    if stake < 10: return jsonify({'success': False})
    with get_db() as conn:
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if (u['balance'] + u['bonus_balance']) < stake: return jsonify({'success': False, 'error': 'Insufficient'})
        deduct_stake(conn, session['user_id'], stake, u['balance'], u['bonus_balance'])
        empty_safe = random.randint(0, 2)
        win = safe_choice != empty_safe
        winnings = round(stake * 1.45, 2) if win else 0
        if win: 
            conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (winnings, session['user_id']))
        conn.commit()
        un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return jsonify({'success': True, 'win': win, 'empty_safe': empty_safe, 'winnings': winnings, 'new_total': un['balance'] + un['bonus_balance']})

@app.route('/rps')
def rps_game():
    if 'user_id' not in session: return redirect(url_for('login'))
    with get_db() as conn: 
        user_data = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return render_template('rps.html', user=user_data)

@app.route('/rps/play', methods=['POST'])
def rps_play():
    if 'user_id' not in session: return jsonify({'success': False})
    try: stake = float(request.json.get('stake', 0))
    except: return jsonify({'success': False})
    choice = request.json.get('choice')
    if stake < 10: return jsonify({'success': False})
    with get_db() as conn:
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if (u['balance'] + u['bonus_balance']) < stake: return jsonify({'success': False})
        deduct_stake(conn, session['user_id'], stake, u['balance'], u['bonus_balance'])
        dealer = random.choice(['rock', 'paper', 'scissors'])
        win = False
        push = False
        if choice == dealer: 
            push = True
        elif (choice == 'rock' and dealer == 'scissors') or (choice == 'paper' and dealer == 'rock') or (choice == 'scissors' and dealer == 'paper'): 
            win = True
        winnings = round(stake * 1.95, 2) if win else (stake if push else 0)
        if winnings > 0: 
            conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (winnings, session['user_id']))
        conn.commit()
        un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return jsonify({'success': True, 'dealer': dealer, 'win': win, 'push': push, 'winnings': winnings, 'new_total': un['balance'] + un['bonus_balance']})

@app.route('/red_dog')
def red_dog_game():
    if 'user_id' not in session: return redirect(url_for('login'))
    with get_db() as conn: 
        user_data = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return render_template('red_dog.html', user=user_data)

@app.route('/red_dog/play', methods=['POST'])
def red_dog_play():
    if 'user_id' not in session: return jsonify({'success': False})
    try: stake = float(request.json.get('stake', 0))
    except: return jsonify({'success': False})
    if stake < 10: return jsonify({'success': False})
    with get_db() as conn:
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if (u['balance'] + u['bonus_balance']) < stake: return jsonify({'success': False})
        deduct_stake(conn, session['user_id'], stake, u['balance'], u['bonus_balance'])
        c1, c2, c3 = draw_card(), draw_card(), draw_card()
        rank_vals = {'2':2,'3':3,'4':4,'5':5,'6':6,'7':7,'8':8,'9':9,'10':10,'J':11,'Q':12,'K':13,'A':14}
        v1 = rank_vals[c1['rank']]
        v2 = rank_vals[c2['rank']]
        v3 = rank_vals[c3['rank']]
        low = min(v1, v2)
        high = max(v1, v2)
        win = (low < v3 < high)
        winnings = round(stake * 2.0, 2) if win else 0
        if win: 
            conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (winnings, session['user_id']))
        conn.commit()
        un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return jsonify({'success': True, 'c1': c1, 'c2': c2, 'c3': c3, 'win': win, 'winnings': winnings, 'new_total': un['balance'] + un['bonus_balance']})

@app.route('/pharaoh_slot')
def pharaoh_slot_game():
    if 'user_id' not in session: return redirect(url_for('login'))
    with get_db() as conn: 
        user_data = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return render_template('pharaoh_slot.html', user=user_data)

@app.route('/pharaoh_slot/spin', methods=['POST'])
def pharaoh_slot_spin():
    if 'user_id' not in session: return jsonify({'success': False})
    try: stake = float(request.json.get('stake', 0))
    except: return jsonify({'success': False})
    if stake < 10: return jsonify({'success': False})
    with get_db() as conn:
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if (u['balance'] + u['bonus_balance']) < stake: return jsonify({'success': False})
        deduct_stake(conn, session['user_id'], stake, u['balance'], u['bonus_balance'])
        syms = ['🏺', '🦂', '🐪', '👁️', '☥', '𓋹']
        reels = [random.choice(syms) for _ in range(5)]
        matches = max([reels.count(s) for s in set(reels)])
        mult = 0.0
        if matches == 5: mult = 50.0
        elif matches == 4: mult = 10.0
        elif matches == 3: mult = 2.0
        winnings = round(stake * mult, 2)
        if winnings > 0: 
            conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (winnings, session['user_id']))
        conn.commit()
        un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return jsonify({'success': True, 'reels': reels, 'multiplier': mult, 'winnings': winnings, 'new_total': un['balance'] + un['bonus_balance']})

@app.route('/hilo_dice')
def hilo_dice_game():
    if 'user_id' not in session: return redirect(url_for('login'))
    with get_db() as conn: 
        user_data = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return render_template('hilo_dice.html', user=user_data)

@app.route('/hilo_dice/play', methods=['POST'])
def hilo_dice_play():
    if 'user_id' not in session: return jsonify({'success': False})
    try:
        stake = float(request.json.get('stake', 0))
        current = int(request.json.get('current', 7))
    except: return jsonify({'success': False})
    guess = request.json.get('guess')
    if stake < 10: return jsonify({'success': False})
    with get_db() as conn:
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if (u['balance'] + u['bonus_balance']) < stake: return jsonify({'success': False})
        deduct_stake(conn, session['user_id'], stake, u['balance'], u['bonus_balance'])
        nxt = random.randint(1, 6) + random.randint(1, 6)
        win = False
        if guess == 'hi' and nxt > current: win = True
        elif guess == 'lo' and nxt < current: win = True
        elif guess == 'same' and nxt == current: win = True
        mult = 5.0 if guess == 'same' else 1.95
        winnings = round(stake * mult, 2) if win else 0
        if win: 
            conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (winnings, session['user_id']))
        conn.commit()
        un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return jsonify({'success': True, 'next': nxt, 'win': win, 'winnings': winnings, 'new_total': un['balance'] + un['bonus_balance']})

@app.route('/coin_streak')
def coin_streak_game():
    if 'user_id' not in session: return redirect(url_for('login'))
    with get_db() as conn: 
        user_data = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return render_template('coin_streak.html', user=user_data)

@app.route('/coin_streak/play', methods=['POST'])
def coin_streak_play():
    if 'user_id' not in session: return jsonify({'success': False})
    try:
        stake = float(request.json.get('stake', 0))
        step = int(request.json.get('step', 1))
    except: return jsonify({'success': False})
    if stake < 10: return jsonify({'success': False})
    with get_db() as conn:
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if step == 1:
            if (u['balance'] + u['bonus_balance']) < stake: return jsonify({'success': False})
            deduct_stake(conn, session['user_id'], stake, u['balance'], u['bonus_balance'])
            conn.commit()
        win = random.choice([True, False])
        mult = round(1.95 ** step, 2) if win else 0
        winnings = round(stake * mult, 2) if win else 0
        un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return jsonify({'success': True, 'win': win, 'multiplier': mult, 'winnings': winnings, 'new_total': un['balance'] + un['bonus_balance']})

@app.route('/coin_streak/cashout', methods=['POST'])
def coin_streak_cashout():
    if 'user_id' not in session: return jsonify({'success': False})
    try: winnings = float(request.json.get('winnings', 0))
    except: return jsonify({'success': False})
    if winnings > 0:
        with get_db() as conn:
            conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (winnings, session['user_id']))
            conn.commit()
            un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        return jsonify({'success': True, 'new_total': un['balance'] + un['bonus_balance']})
    return jsonify({'success': False})


# ==========================================
# 6. ADMIN DASHBOARD & PAYMENT SETTINGS
# ==========================================
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if session.get('is_admin'): return redirect(url_for('admin'))
    if request.method == 'POST':
        if request.form['username'] == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, request.form['password']):
            session['user_id'] = 'admin_system'
            session['is_admin'] = True
            return redirect(url_for('admin'))
        else: 
            flash('Invalid Admin Credentials.', 'error')
    return render_template('admin_login.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    global ADMIN_GAME_CONTROL
    if not session.get('is_admin'): return redirect(url_for('admin_login'))
    with get_db() as conn:
        if request.method == 'POST':
            act = request.form.get('action')
            
            if act == 'update_payment':
                upi = request.form.get('upi_id', '').strip()
                acct = request.form.get('bank_account', '').strip()
                ifsc = request.form.get('ifsc_code', '').strip()
                conn.execute('UPDATE site_settings SET upi_id=?, bank_account=?, ifsc_code=?', (upi, acct, ifsc))
                conn.commit()
                flash("Global Payment Details Updated successfully!", "success")
                return redirect(url_for('admin'))

            elif act == 'control_game':
                game = request.form.get('game')
                mode = request.form.get('mode')
                
                if game == 'aviator':
                    if mode == 'auto': ADMIN_GAME_CONTROL["aviator"] = None
                    else:
                        try: ADMIN_GAME_CONTROL["aviator"] = float(request.form.get('value'))
                        except: flash("Invalid Aviator value.", "error")
                elif game == 'jetx':
                    if mode == 'auto': ADMIN_GAME_CONTROL["jetx"] = None
                    else:
                        try: ADMIN_GAME_CONTROL["jetx"] = float(request.form.get('value'))
                        except: flash("Invalid JetX value.", "error")
                elif game == 'dt':
                    if mode == 'auto': ADMIN_GAME_CONTROL["dt"] = None
                    elif mode in ["Dragon", "Tiger", "Tie"]: ADMIN_GAME_CONTROL["dt"] = mode
                elif game == 'ht':
                    if mode == 'auto': ADMIN_GAME_CONTROL["ht"] = None
                    elif mode in ["Heads", "Tails"]: ADMIN_GAME_CONTROL["ht"] = mode
                elif game == 'cp':
                    if mode == 'auto': ADMIN_GAME_CONTROL["cp"] = None
                    else:
                        try: ADMIN_GAME_CONTROL["cp"] = int(request.form.get('value'))
                        except: flash("Invalid Color Prediction value.", "error")
                
                flash(f"Game control updated for {game.upper()} to {mode.upper()}", "success")
                return redirect(url_for('admin'))
            
            elif act == 'add_match':
                conn.execute('INSERT INTO matches (sport, league, team1, team2, score, status, odds1, oddsX, odds2, is_live) VALUES (?,?,?,?,?,?,?,?,?,?)', (request.form['sport'], request.form['league'], request.form['team1'], request.form['team2'], "", "", request.form['odds1'], request.form.get('oddsX', 0.0), request.form['odds2'], 1 if request.form.get('is_live') else 0)); conn.commit(); flash("Match added successfully!", "success")
            elif act == 'toggle_live':
                mid = request.form['match_id']
                m = conn.execute('SELECT is_live FROM matches WHERE id = ?', (mid,)).fetchone()
                if m:
                    new_state = 0 if m['is_live'] else 1
                    conn.execute('UPDATE matches SET is_live = ? WHERE id = ?', (new_state, mid))
                    conn.commit()
                    flash(f"Match status updated to {'Live' if new_state else 'Upcoming'}!", "success")
            elif act == 'delete_match': 
                conn.execute('UPDATE bets SET match_status = "Void" WHERE match_id = ? AND match_status = "Open"', (request.form['match_id'],))
                conn.execute('DELETE FROM matches WHERE id = ?', (request.form['match_id'],))
                conn.commit()
                flash("Match deleted permanently.", "success")
            elif act == 'resolve_match':
                mid, wt = request.form['match_id'], request.form['winning_team'].strip()
                bets = conn.execute('SELECT * FROM bets WHERE match_id = ? AND match_status = "Open"', (mid,)).fetchall()
                for b in bets:
                    if b['team'].strip() == wt: 
                        conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (b['stake']+b['profit'], b['user_id']))
                        conn.execute('UPDATE bets SET match_status = "Win" WHERE id = ?', (b['id'],))
                    else: 
                        conn.execute('UPDATE bets SET match_status = "Loss" WHERE id = ?', (b['id'],))
                conn.execute('UPDATE matches SET status = ? WHERE id = ?', (f"Winner: {wt}", mid))
                conn.commit()
                flash(f"Match resolved. Winners paid!", "success")
            elif act == 'approve_user':
                uid = request.form['user_id']
                u = conn.execute('SELECT referrer_id FROM users WHERE id = ?', (uid,)).fetchone()
                if u and u['referrer_id']: 
                    conn.execute('UPDATE users SET bonus_balance = bonus_balance + 50 WHERE id IN (?, ?)', (u['referrer_id'], uid))
                conn.execute('UPDATE users SET status = "Approved" WHERE id = ?', (uid,))
                conn.commit()
                flash("Player Approved!", "success")
            elif act == 'reject_user': 
                conn.execute('DELETE FROM users WHERE id = ?', (request.form['user_id'],))
                conn.execute('DELETE FROM deposits WHERE user_id = ?', (request.form['user_id'],))
                conn.commit()
                flash("Player application declined.", "error")
            elif act == 'delete_user_permanently':
                target_uid = request.form['user_id']
                conn.execute('DELETE FROM users WHERE id = ?', (target_uid,))
                conn.execute('DELETE FROM bets WHERE user_id = ?', (target_uid,))
                conn.execute('DELETE FROM deposits WHERE user_id = ?', (target_uid,))
                conn.execute('DELETE FROM withdrawals WHERE user_id = ?', (target_uid,))
                conn.execute('DELETE FROM daily_spins WHERE user_id = ?', (target_uid,))
                conn.commit()
                flash("Player account and all associated records permanently deleted.", "success")
            elif act == 'create_user': 
                try: 
                    conn.execute('INSERT INTO users (username, password, status) VALUES (?, ?, "Approved")', (request.form['new_username'], generate_password_hash(request.form['new_password'], method='pbkdf2:sha256')))
                    conn.commit()
                    flash("User created!", "success")
                except sqlite3.IntegrityError: 
                    flash("Username exists.", "error")
            elif act == 'adjust_balance': 
                target_uid = request.form['user_id']
                try: 
                    amount = float(request.form['amount'])
                except: 
                    flash("Invalid amount.", "error")
                    return redirect(url_for('admin'))
                
                mode = request.form['mode'] 
                if amount <= 0:
                    flash("Amount must be greater than zero.", "error")
                elif mode == 'remove':
                    current_bal = conn.execute('SELECT balance FROM users WHERE id = ?', (target_uid,)).fetchone()['balance']
                    amount = min(amount, current_bal)
                    conn.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (amount, target_uid))
                    flash(f"Successfully subtracted ₹{amount} from account!", "success")
                else:
                    conn.execute('UPDATE users SET balance = balance + ?, total_wagered = total_wagered + ? WHERE id = ?', (amount, amount, target_uid))
                    flash(f"Successfully added ₹{amount} to account!", "success")
                conn.commit()
            elif act == 'approve_deposit':
                d = conn.execute('SELECT * FROM deposits WHERE id = ?', (request.form['deposit_id'],)).fetchone()
                if d and d['status'] == 'Pending': 
                    conn.execute('UPDATE users SET balance = balance + ?, total_wagered = total_wagered + ? WHERE id = ?', (d['amount'], d['amount'], d['user_id']))
                    conn.execute('UPDATE deposits SET status = "Approved" WHERE id = ?', (d['id'],))
                    conn.commit()
                    flash("Deposit Approved!", "success")
            elif act == 'reject_deposit': 
                conn.execute('UPDATE deposits SET status = "Rejected" WHERE id = ?', (request.form['deposit_id'],))
                conn.commit()
                flash("Deposit rejected.", "error")
            elif act == 'approve_withdraw': 
                conn.execute('UPDATE withdrawals SET status = "Approved" WHERE id = ?', (request.form['withdraw_id'],))
                conn.commit()
                flash("Withdrawal Approved!", "success")
            elif act == 'reject_withdraw':
                w = conn.execute('SELECT * FROM withdrawals WHERE id = ?', (request.form['withdraw_id'],)).fetchone()
                if w and w['status'] == 'Pending': 
                    conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (w['amount'], w['user_id']))
                    conn.execute('UPDATE withdrawals SET status = "Rejected" WHERE id = ?', (w['id'],))
                    conn.commit()
                    flash("Withdrawal refunded.", "error")
            return redirect(url_for('admin'))
        
        m = conn.execute('SELECT * FROM matches ORDER BY id DESC').fetchall()
        u = conn.execute('SELECT id, username, mobile, balance, bonus_balance, total_wagered FROM users WHERE status = "Approved" ORDER BY id DESC').fetchall()
        pu = conn.execute('SELECT id, username, mobile FROM users WHERE status = "Pending" ORDER BY id DESC').fetchall()
        w = conn.execute('''SELECT w.*, u.username FROM withdrawals w JOIN users u ON w.user_id = u.id ORDER BY w.id DESC''').fetchall()
        d = conn.execute('''SELECT d.*, u.username FROM deposits d JOIN users u ON d.user_id = u.id ORDER BY d.id DESC''').fetchall()
        
    return render_template('admin.html', matches=m, users=u, pending_users=pu, withdrawals=w, deposits=d, 
                           game_control=ADMIN_GAME_CONTROL, 
                           aviator_state=AVIATOR_STATE,
                           jetx_state=JETX_STATE,
                           dt_state=DT_STATE,
                           ht_state=HT_STATE,
                           cp_state=CP_STATE)

if __name__ == '__main__':
    with app.app_context(): init_db()
    app.run( host="0.0.0.0",debug=False, port=5050)