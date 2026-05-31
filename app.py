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
DB_NAME = "betting.db"
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ADMIN_USERNAME = "superadmin"
ADMIN_PASSWORD_HASH = generate_password_hash("NavabetxAdmin99!")

# ==========================================
# 1. MULTIPLAYER GAME ENGINES
# ==========================================
AVIATOR_STATE = {"state": "WAITING", "start_time": time.time(), "crash_point": 0.00, "history": [1.45, 2.10, 1.01, 5.50]}
ACTIVE_BETS = {} 
def update_aviator_state():
    global AVIATOR_STATE, ACTIVE_BETS
    now = time.time(); elapsed = now - AVIATOR_STATE["start_time"]
    if AVIATOR_STATE["state"] == "WAITING" and elapsed > 5.0: 
        AVIATOR_STATE["state"] = "FLYING"; AVIATOR_STATE["start_time"] = now
        rand = random.random()
        if rand < 0.60: crash = round(random.uniform(1.00, 1.49), 2)
        elif rand < 0.85: crash = round(random.uniform(1.50, 1.99), 2)
        elif rand < 0.95: crash = round(random.uniform(2.00, 5.00), 2)
        else: crash = round(random.uniform(5.01, 35.00), 2)
        AVIATOR_STATE["crash_point"] = crash
    elif AVIATOR_STATE["state"] == "FLYING":
        if 1.00 + (elapsed ** 1.4) * 0.08 >= AVIATOR_STATE["crash_point"]:
            AVIATOR_STATE["state"] = "CRASHED"; AVIATOR_STATE["start_time"] = now
            AVIATOR_STATE["history"].insert(0, AVIATOR_STATE["crash_point"])
            if len(AVIATOR_STATE["history"]) > 15: AVIATOR_STATE["history"].pop()
            ACTIVE_BETS.clear()
    elif AVIATOR_STATE["state"] == "CRASHED" and elapsed > 3.0: 
        AVIATOR_STATE["state"] = "WAITING"; AVIATOR_STATE["start_time"] = now

DT_STATE = {"state": "WAITING", "start_time": time.time(), "result": None, "d_card": 0, "t_card": 0, "history": ["D", "T", "T", "Tie", "D"]}
DT_BETS = {} 
def update_dt_state():
    global DT_STATE, DT_BETS
    now = time.time(); elapsed = now - DT_STATE["start_time"]
    if DT_STATE["state"] == "WAITING" and elapsed > 15.0: 
        DT_STATE["state"] = "REVEAL"; DT_STATE["start_time"] = now
        rand = random.random()
        if rand < 0.45: d_card = random.randint(3, 14); t_card = random.randint(2, d_card - 1); res = "Dragon"
        elif rand < 0.90: t_card = random.randint(3, 14); d_card = random.randint(2, t_card - 1); res = "Tiger"
        else: d_card = random.randint(2, 14); t_card = d_card; res = "Tie"
        DT_STATE["d_card"] = d_card; DT_STATE["t_card"] = t_card; DT_STATE["result"] = res
        DT_STATE["history"].insert(0, res)
        if len(DT_STATE["history"]) > 15: DT_STATE["history"].pop()
        if DT_BETS:
            with get_db() as conn:
                for uid, bet in DT_BETS.items():
                    if bet['target'] == res: conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (bet['stake'] * (8.0 if res == "Tie" else 2.0), uid))
                conn.commit()
            DT_BETS.clear()
    elif DT_STATE["state"] == "REVEAL" and elapsed > 6.0: 
        DT_STATE["state"] = "WAITING"; DT_STATE["start_time"] = now

HT_STATE = {"state": "WAITING", "start_time": time.time(), "result": None, "history": ["H", "T", "H", "H"]}
HT_BETS = {} 
def update_ht_state():
    global HT_STATE, HT_BETS
    now = time.time(); elapsed = now - HT_STATE["start_time"]
    if HT_STATE["state"] == "WAITING" and elapsed > 12.0:
        HT_STATE["state"] = "FLIPPING"; HT_STATE["start_time"] = now
        res = "Heads" if random.random() < 0.5 else "Tails"
        HT_STATE["result"] = res; HT_STATE["history"].insert(0, "H" if res == "Heads" else "T")
        if len(HT_STATE["history"]) > 15: HT_STATE["history"].pop()
        if HT_BETS:
            with get_db() as conn:
                for uid, bet in HT_BETS.items():
                    if bet['target'] == res: conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (bet['stake'] * 1.95, uid))
                conn.commit()
            HT_BETS.clear()
    elif HT_STATE["state"] == "FLIPPING" and elapsed > 5.0:
        HT_STATE["state"] = "WAITING"; HT_STATE["start_time"] = now

CP_STATE = {"state": "WAITING", "start_time": time.time(), "result_number": -1, "result_color": "", "history": []}
CP_BETS = {} 
def update_cp_state():
    global CP_STATE, CP_BETS
    now = time.time(); elapsed = now - CP_STATE["start_time"]
    if CP_STATE["state"] == "WAITING" and elapsed > 30.0:
        CP_STATE["state"] = "REVEAL"; CP_STATE["start_time"] = now
        res_num = random.randint(0, 9)
        if res_num in [1, 3, 7, 9]: res_color = "Green"
        elif res_num in [2, 4, 6, 8]: res_color = "Red"
        else: res_color = "Violet"
        CP_STATE["result_number"] = res_num; CP_STATE["result_color"] = res_color
        CP_STATE["history"].insert(0, {"num": res_num, "col": res_color})
        if len(CP_STATE["history"]) > 15: CP_STATE["history"].pop()
        if CP_BETS:
            with get_db() as conn:
                for uid, bet in CP_BETS.items():
                    target = str(bet['target']); stake = bet['stake']; win = 0
                    if target == str(res_num): win = stake * 9.0
                    elif target == "Green" and res_color == "Green": win = stake * 2.0
                    elif target == "Red" and res_color == "Red": win = stake * 2.0
                    elif target == "Violet" and res_color == "Violet": win = stake * 4.5
                    if win > 0: conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (win, uid))
                conn.commit()
            CP_BETS.clear()
    elif CP_STATE["state"] == "REVEAL" and elapsed > 5.0:
        CP_STATE["state"] = "WAITING"; CP_STATE["start_time"] = now

# ==========================================
# 2. SINGLE PLAYER MEMORY
# ==========================================
ACTIVE_MINES = {} 

# ==========================================
# 3. DATABASE SETUP
# ==========================================
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, mobile TEXT, balance REAL DEFAULT 0.00, bonus_balance REAL DEFAULT 0.00, status TEXT DEFAULT 'Pending', referrer_id INTEGER)''') 
        conn.execute('''CREATE TABLE IF NOT EXISTS matches (id INTEGER PRIMARY KEY AUTOINCREMENT, sport TEXT, league TEXT, team1 TEXT, team2 TEXT, score TEXT, status TEXT, odds1 REAL, oddsX REAL, odds2 REAL, is_live INTEGER DEFAULT 0)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS bets (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, match_id INTEGER, match_name TEXT, team TEXT, odds REAL, stake REAL, profit REAL, match_status TEXT DEFAULT 'Open', date TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS withdrawals (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, account_number TEXT, account_name TEXT, ifsc TEXT, bank_name TEXT, amount REAL, status TEXT DEFAULT 'Pending', date TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS deposits (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, method TEXT, amount REAL, utr TEXT, screenshot TEXT, status TEXT DEFAULT 'Pending', date TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS daily_spins (user_id INTEGER PRIMARY KEY, last_spin_time REAL)''')
        conn.commit()

def deduct_stake(conn, user_id, stake, user_balance, user_bonus):
    if user_bonus >= stake: conn.execute('UPDATE users SET bonus_balance = bonus_balance - ? WHERE id = ?', (stake, user_id))
    else: conn.execute('UPDATE users SET bonus_balance = 0, balance = balance - ? WHERE id = ?', (stake - user_bonus, user_id))

# ==========================================
# 4. AUTHENTICATION & CORE
# ==========================================
@app.route('/', methods=['GET', 'POST'])
def login():
    if 'user_id' in session: return redirect(url_for('admin' if session.get('is_admin') else 'home'))
    if request.method == 'POST':
        with get_db() as conn:
            user = conn.execute('SELECT * FROM users WHERE username = ?', (request.form['username'],)).fetchone()
            if user and check_password_hash(user['password'], request.form['password']):
                if user['status'] == 'Pending': flash('Account pending admin approval.', 'error'); return redirect(url_for('login'))
                session['user_id'] = user['id']; session['username'] = user['username']; session['is_admin'] = False; return redirect(url_for('home'))
            else: flash('Invalid credentials.', 'error')
    return render_template('login.html')

@app.route('/register', methods=['POST'])
def register():
    username, mobile, pwd, cpwd, ref = request.form['username'].strip(), request.form['mobile'].strip(), request.form['password'], request.form['confirm_password'], request.form.get('referral_code', '').strip()
    if pwd != cpwd: flash("Passwords don't match!", "error"); return redirect(url_for('login'))
    with get_db() as conn:
        if conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone(): flash("Username exists.", "error"); return redirect(url_for('login'))
        referrer = conn.execute('SELECT id FROM users WHERE username = ?', (ref,)).fetchone() if ref else None
        cursor = conn.execute('INSERT INTO users (username, password, mobile, status, referrer_id) VALUES (?, ?, ?, "Pending", ?)', (username, generate_password_hash(pwd), mobile, referrer['id'] if referrer else None)); conn.commit()
        flash(str(cursor.lastrowid), 'fast_track')
    return redirect(url_for('login'))

@app.route('/fast_track_deposit', methods=['POST'])
def fast_track_deposit():
    uid, amt, utr = request.form['user_id'], float(request.form['amount']), request.form['utr'].strip()
    file = request.files.get('screenshot')
    fname = secure_filename(f"{uid}_{int(time.time())}_{file.filename}") if file else ""
    if fname: file.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
    with get_db() as conn:
        conn.execute('INSERT INTO deposits (user_id, method, amount, utr, screenshot, status, date) VALUES (?, "First Deposit", ?, ?, ?, "Pending", ?)', (uid, amt, utr, fname, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit(); flash('Payment proof submitted! Admin will verify.', 'success')
    return redirect(url_for('login'))

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login'))

@app.route('/home')
def home():
    if 'user_id' not in session or session.get('is_admin'): return redirect(url_for('login'))
    with get_db() as conn:
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        l = conn.execute('SELECT * FROM matches WHERE is_live = 1 AND (status IS NULL OR status NOT LIKE "Winner:%") LIMIT 4').fetchall()
        p = conn.execute('SELECT * FROM matches WHERE is_live = 0 AND (status IS NULL OR status NOT LIKE "Winner:%") LIMIT 10').fetchall()
    return render_template('index.html', live_matches=l, popular_matches=p, user=u)

@app.route('/games')
def games():
    if 'user_id' not in session or session.get('is_admin'): return redirect(url_for('login'))
    with get_db() as conn: u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return render_template('games.html', user=u)

@app.route('/profile')
def profile():
    if 'user_id' not in session or session.get('is_admin'): return redirect(url_for('login'))
    with get_db() as conn:
        user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        bc = conn.execute('SELECT COUNT(*) as count FROM bets WHERE user_id = ?', (session['user_id'],)).fetchone()
        dep = conn.execute('SELECT * FROM deposits WHERE user_id = ? ORDER BY id DESC', (session['user_id'],)).fetchall()
        wit = conn.execute('SELECT * FROM withdrawals WHERE user_id = ? ORDER BY id DESC', (session['user_id'],)).fetchall()
        has_dep = conn.execute("SELECT COUNT(*) as count FROM deposits WHERE user_id = ? AND status = 'Approved'", (session['user_id'],)).fetchone()['count'] > 0
    return render_template('profile.html', user=user, bet_count=bc['count'], deposits=dep, withdrawals=wit, has_deposited=has_dep)

@app.route('/my_bets')
def my_bets():
    if 'user_id' not in session or session.get('is_admin'): return redirect(url_for('login'))
    with get_db() as conn:
        user = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        bets = conn.execute('SELECT * FROM bets WHERE user_id = ? ORDER BY id DESC', (session['user_id'],)).fetchall()
    return render_template('my_bets.html', bets=bets, user=user)

@app.route('/claim_referral', methods=['POST'])
def claim_referral():
    if 'user_id' not in session: return redirect(url_for('login'))
    ref = request.form.get('referral_code', '').strip()
    with get_db() as conn:
        user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if user['referrer_id']: flash('Bonus already claimed!', 'error'); return redirect(url_for('profile'))
        if user['username'].lower() == ref.lower(): flash('Cannot use your own code!', 'error'); return redirect(url_for('profile'))
        referrer = conn.execute('SELECT * FROM users WHERE username = ? COLLATE NOCASE', (ref,)).fetchone()
        if not referrer: flash('Invalid referral code.', 'error'); return redirect(url_for('profile'))
        conn.execute('UPDATE users SET bonus_balance = bonus_balance + 50 WHERE id = ?', (referrer['id'],))
        conn.execute('UPDATE users SET bonus_balance = bonus_balance + 50, referrer_id = ? WHERE id = ?', (referrer['id'], session['user_id']))
        conn.commit(); flash('₹50 Referral Bonus Applied!', 'success')
    return redirect(url_for('profile'))

@app.route('/deposit', methods=['POST'])
def deposit():
    if 'user_id' not in session: return redirect(url_for('login'))
    file = request.files.get('screenshot')
    fname = secure_filename(f"{session['user_id']}_{int(time.time())}_{file.filename}") if file else ""
    if fname: file.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
    with get_db() as conn:
        conn.execute('INSERT INTO deposits (user_id, method, amount, utr, screenshot, status, date) VALUES (?, ?, ?, ?, ?, "Pending", ?)', 
                     (session['user_id'], request.form['method'], float(request.form['amount']), request.form['utr'], fname, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit(); flash('Deposit submitted for admin approval.', 'success')
    return redirect(url_for('profile'))

@app.route('/withdraw', methods=['POST'])
def withdraw():
    if 'user_id' not in session: return redirect(url_for('login'))
    amt = float(request.form['amount'])
    with get_db() as conn:
        if conn.execute("SELECT COUNT(*) as count FROM deposits WHERE user_id = ? AND status = 'Approved'", (session['user_id'],)).fetchone()['count'] == 0:
            flash('Must deposit first to unlock withdrawals!', 'error'); return redirect(url_for('profile'))
        user = conn.execute('SELECT balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if amt <= 0 or user['balance'] < amt: flash('Insufficient REAL balance!', 'error')
        else:
            conn.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (amt, session['user_id']))
            conn.execute('INSERT INTO withdrawals (user_id, account_number, account_name, ifsc, bank_name, amount, status, date) VALUES (?, ?, ?, ?, ?, ?, "Pending", ?)', 
                         (session['user_id'], request.form['account_number'], request.form['account_name'], request.form['ifsc'], request.form['bank_name'], amt, datetime.now().strftime("%Y-%m-%d %H:%M")))
            conn.commit(); flash('Withdrawal request submitted successfully!', 'success')
    return redirect(url_for('profile'))

@app.route('/place_bet', methods=['POST'])
def place_bet():
    if 'user_id' not in session or session.get('is_admin'): return jsonify({'success': False, 'error': 'Unauthorized'})
    data = request.json
    mid, team = data.get('match_id'), data.get('team').strip()
    odds, stake = float(data.get('odds')), float(data.get('stake'))
    with get_db() as conn:
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if stake <= 0 or (u['balance'] + u['bonus_balance']) < stake: 
            return jsonify({'success': False, 'error': 'Insufficient balance!'})
        match = conn.execute('SELECT team1, team2 FROM matches WHERE id = ?', (mid,)).fetchone()
        deduct_stake(conn, session['user_id'], stake, u['balance'], u['bonus_balance'])
        conn.execute('INSERT INTO bets (user_id, match_id, match_name, team, odds, stake, profit, match_status, date) VALUES (?, ?, ?, ?, ?, ?, ?, "Open", ?)',
                     (session['user_id'], mid, f"{match['team1']} vs {match['team2']}" if match else f"ID: {mid}", team, odds, stake, (odds*stake)-stake, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return jsonify({'success': True, 'new_total': un['balance'] + un['bonus_balance']})

# ==========================================
# 5. LIVE GAME API ROUTES
# ==========================================

@app.route('/spin')
def spin_game():
    if 'user_id' not in session or session.get('is_admin'): return redirect(url_for('login'))
    with get_db() as conn: 
        user = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        spin_data = conn.execute('SELECT last_spin_time FROM daily_spins WHERE user_id = ?', (session['user_id'],)).fetchone()
        can_spin = True; time_left_seconds = 0
        if spin_data:
            elapsed = time.time() - spin_data['last_spin_time']
            if elapsed < 86400: can_spin = False; time_left_seconds = int(86400 - elapsed)
    return render_template('spin.html', user=user, can_spin=can_spin, time_left=time_left_seconds)

@app.route('/spin/claim', methods=['POST'])
def spin_claim():
    if 'user_id' not in session: return jsonify({'success': False})
    uid = session['user_id']
    with get_db() as conn:
        spin_data = conn.execute('SELECT last_spin_time FROM daily_spins WHERE user_id = ?', (uid,)).fetchone()
        if spin_data and (time.time() - spin_data['last_spin_time']) < 86400: return jsonify({'success': False, 'error': 'You already spun today!'})
        rand = random.random()
        if rand < 0.01: prize = 500  
        elif rand < 0.10: prize = 50 
        elif rand < 0.40: prize = 10 
        elif rand < 0.85: prize = 5  
        else: prize = 0              
        if prize > 0: conn.execute('UPDATE users SET bonus_balance = bonus_balance + ? WHERE id = ?', (prize, uid))
        if spin_data: conn.execute('UPDATE daily_spins SET last_spin_time = ? WHERE user_id = ?', (time.time(), uid))
        else: conn.execute('INSERT INTO daily_spins (user_id, last_spin_time) VALUES (?, ?)', (uid, time.time()))
        conn.commit(); un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (uid,)).fetchone()
        return jsonify({'success': True, 'prize': prize, 'new_total': un['balance'] + un['bonus_balance']})

@app.route('/aviator')
def aviator_game():
    if 'user_id' not in session or session.get('is_admin'): return redirect(url_for('login'))
    with get_db() as conn: return render_template('aviator.html', user=conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone())

@app.route('/aviator/sync')
def aviator_sync(): 
    update_aviator_state() 
    return jsonify({"state": AVIATOR_STATE["state"], "elapsed": time.time() - AVIATOR_STATE["start_time"], "crash_point": AVIATOR_STATE["crash_point"] if AVIATOR_STATE["state"] == "CRASHED" else None, "history": AVIATOR_STATE["history"]})

@app.route('/aviator/bet', methods=['POST'])
def aviator_bet():
    if 'user_id' not in session: return jsonify({'success': False})
    update_aviator_state()
    if AVIATOR_STATE["state"] != "WAITING" or session['user_id'] in ACTIVE_BETS: return jsonify({'success': False, 'error': 'Betting closed'})
    s = float(request.json.get('stake', 0))
    with get_db() as conn:
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if s <= 0 or (u['balance'] + u['bonus_balance']) < s: return jsonify({'success': False, 'error': 'Insufficient funds'})
        deduct_stake(conn, session['user_id'], s, u['balance'], u['bonus_balance']); conn.commit(); un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone(); ACTIVE_BETS[session['user_id']] = s
    return jsonify({'success': True, 'new_total': un['balance'] + un['bonus_balance']})

@app.route('/aviator/cashout', methods=['POST'])
def aviator_cashout():
    if 'user_id' not in session: return jsonify({'success': False})
    update_aviator_state()
    if AVIATOR_STATE["state"] != "FLYING" or session['user_id'] not in ACTIVE_BETS: return jsonify({'success': False})
    m = 1.00 + ((time.time() - AVIATOR_STATE["start_time"]) ** 1.4) * 0.08
    if m >= AVIATOR_STATE["crash_point"]: return jsonify({'success': False})
    win = round(ACTIVE_BETS[session['user_id']] * m, 2)
    with get_db() as conn:
        conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (win, session['user_id'])); conn.commit(); un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    del ACTIVE_BETS[session['user_id']]; return jsonify({'success': True, 'new_total': un['balance'] + un['bonus_balance'], 'winnings': win, 'multiplier': m})

@app.route('/dragon_tiger')
def dragon_tiger_game():
    if 'user_id' not in session or session.get('is_admin'): return redirect(url_for('login'))
    with get_db() as conn: return render_template('dragon_tiger.html', user=conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone())

@app.route('/dragon_tiger/sync')
def dragon_tiger_sync(): 
    update_dt_state()
    return jsonify({"state": DT_STATE["state"], "elapsed": time.time() - DT_STATE["start_time"], "d_card": DT_STATE["d_card"] if DT_STATE["state"] == "REVEAL" else 0, "t_card": DT_STATE["t_card"] if DT_STATE["state"] == "REVEAL" else 0, "result": DT_STATE["result"] if DT_STATE["state"] == "REVEAL" else None, "history": DT_STATE["history"]})

@app.route('/dragon_tiger/bet', methods=['POST'])
def dragon_tiger_bet():
    if 'user_id' not in session: return jsonify({'success': False})
    update_dt_state()
    if DT_STATE["state"] != "WAITING" or session['user_id'] in DT_BETS: return jsonify({'success': False, 'error': 'Betting closed!'})
    stake, target = float(request.json.get('stake', 0)), request.json.get('target')
    with get_db() as conn:
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if stake <= 0 or (u['balance'] + u['bonus_balance']) < stake: return jsonify({'success': False, 'error': 'Insufficient funds'})
        deduct_stake(conn, session['user_id'], stake, u['balance'], u['bonus_balance']); conn.commit(); un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone(); DT_BETS[session['user_id']] = {'target': target, 'stake': stake}
    return jsonify({'success': True, 'new_total': un['balance'] + un['bonus_balance']})

@app.route('/heads_tails')
def heads_tails_game():
    if 'user_id' not in session or session.get('is_admin'): return redirect(url_for('login'))
    with get_db() as conn: return render_template('heads_tails.html', user=conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone())

@app.route('/heads_tails/sync')
def heads_tails_sync(): 
    update_ht_state() 
    return jsonify({"state": HT_STATE["state"], "elapsed": time.time() - HT_STATE["start_time"], "result": HT_STATE["result"] if HT_STATE["state"] == "FLIPPING" else None, "history": HT_STATE["history"]})

@app.route('/heads_tails/bet', methods=['POST'])
def heads_tails_bet():
    if 'user_id' not in session: return jsonify({'success': False})
    update_ht_state()
    if HT_STATE["state"] != "WAITING" or session['user_id'] in HT_BETS: return jsonify({'success': False, 'error': 'Already bet!'})
    stake, target = float(request.json.get('stake', 0)), request.json.get('target')
    with get_db() as conn:
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if stake <= 0 or (u['balance'] + u['bonus_balance']) < stake: return jsonify({'success': False, 'error': 'Insufficient funds'})
        deduct_stake(conn, session['user_id'], stake, u['balance'], u['bonus_balance']); conn.commit(); un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone(); HT_BETS[session['user_id']] = {'target': target, 'stake': stake}
    return jsonify({'success': True, 'new_total': un['balance'] + un['bonus_balance']})

@app.route('/color_prediction')
def color_prediction_game():
    if 'user_id' not in session or session.get('is_admin'): return redirect(url_for('login'))
    with get_db() as conn: return render_template('color_prediction.html', user=conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone())

@app.route('/color_prediction/sync')
def color_prediction_sync(): 
    update_cp_state() 
    return jsonify({"state": CP_STATE["state"], "elapsed": time.time() - CP_STATE["start_time"], "result_number": CP_STATE["result_number"] if CP_STATE["state"] == "REVEAL" else -1, "result_color": CP_STATE["result_color"] if CP_STATE["state"] == "REVEAL" else "", "history": CP_STATE["history"]})

@app.route('/color_prediction/bet', methods=['POST'])
def color_prediction_bet():
    if 'user_id' not in session: return jsonify({'success': False})
    update_cp_state()
    if CP_STATE["state"] != "WAITING" or session['user_id'] in CP_BETS: return jsonify({'success': False, 'error': 'Already bet!'})
    stake, target = float(request.json.get('stake', 0)), request.json.get('target')
    with get_db() as conn:
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if stake <= 0 or (u['balance'] + u['bonus_balance']) < stake: return jsonify({'success': False, 'error': 'Insufficient funds'})
        deduct_stake(conn, session['user_id'], stake, u['balance'], u['bonus_balance']); conn.commit(); un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone(); CP_BETS[session['user_id']] = {'target': target, 'stake': stake}
    return jsonify({'success': True, 'new_total': un['balance'] + un['bonus_balance']})


# --- PROVABLY FAIR CYBER MINES ---
@app.route('/mines')
def mines_game():
    if 'user_id' not in session or session.get('is_admin'): return redirect(url_for('login'))
    with get_db() as conn: return render_template('mines.html', user=conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone())

@app.route('/mines/start', methods=['POST'])
def mines_start():
    if 'user_id' not in session: return jsonify({'success': False})
    uid = session['user_id']
    stake = float(request.json.get('stake', 0))
    mines_count = int(request.json.get('mines', 3))
    client_seed = request.json.get('client_seed', 'novabetx_player')
    
    if uid in ACTIVE_MINES: return jsonify({'success': False, 'error': 'Game active'})
    with get_db() as conn:
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (uid,)).fetchone()
        if stake <= 0 or (u['balance'] + u['bonus_balance']) < stake: return jsonify({'success': False, 'error': 'Insufficient balance'})
        deduct_stake(conn, uid, stake, u['balance'], u['bonus_balance']); conn.commit(); un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (uid,)).fetchone()
        
        server_seed = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        server_hash = hashlib.sha256(server_seed.encode()).hexdigest()
        
        random.seed(f"{server_seed}-{client_seed}")
        grid = [0]*25; 
        for i in random.sample(range(25), mines_count): grid[i] = 1 
        random.seed() 
        
        ACTIVE_MINES[uid] = {'grid': grid, 'stake': stake, 'mines': mines_count, 'cleared': 0, 'server_seed': server_seed}
        
    return jsonify({'success': True, 'new_total': un['balance'] + un['bonus_balance'], 'server_hash': server_hash})

@app.route('/mines/click', methods=['POST'])
def mines_click():
    if 'user_id' not in session: return jsonify({'success': False})
    uid = session['user_id']
    idx = int(request.json.get('index'))
    if uid not in ACTIVE_MINES: return jsonify({'success': False, 'error': 'No active game'})
    game = ACTIVE_MINES[uid]
    
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
    if uid not in ACTIVE_MINES or ACTIVE_MINES[uid]['cleared'] == 0: return jsonify({'success': False, 'error': 'Play first!'})
    game = ACTIVE_MINES[uid]; mult = round(1.0 + (game['cleared'] * 0.15 * (game['mines']/3)), 2); win = round(game['stake'] * mult, 2)
    server_seed = game['server_seed']
    with get_db() as conn: 
        conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (win, uid)); conn.commit()
        un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (uid,)).fetchone()
    del ACTIVE_MINES[uid]
    return jsonify({'success': True, 'new_total': un['balance'] + un['bonus_balance'], 'winnings': win, 'server_seed': server_seed})


# --- PROVABLY FAIR DIGITAL DICE ---
@app.route('/dice')
def dice_game():
    if 'user_id' not in session or session.get('is_admin'): return redirect(url_for('login'))
    with get_db() as conn: return render_template('dice.html', user=conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone())

@app.route('/dice/roll', methods=['POST'])
def dice_roll():
    if 'user_id' not in session: return jsonify({'success': False})
    uid = session['user_id']
    stake = float(request.json.get('stake', 0))
    target = float(request.json.get('target', 50))
    condition = request.json.get('condition') 
    client_seed = request.json.get('client_seed', 'novabetx_player')
    
    with get_db() as conn:
        u = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (uid,)).fetchone()
        if stake <= 0 or (u['balance'] + u['bonus_balance']) < stake: return jsonify({'success': False, 'error': 'Insufficient balance'})
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
        conn.commit(); un = conn.execute('SELECT balance, bonus_balance FROM users WHERE id = ?', (uid,)).fetchone()
        
    return jsonify({
        'success': True, 'roll': roll, 'win': win, 'multiplier': mult, 'winnings': winnings, 
        'new_total': un['balance'] + un['bonus_balance'],
        'server_seed': server_seed, 'hash': hash_result
    })

# ==========================================
# 6. ADMIN DASHBOARD
# ==========================================
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if session.get('is_admin'): return redirect(url_for('admin'))
    if request.method == 'POST':
        if request.form['username'] == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, request.form['password']):
            session['user_id'] = 'admin_system'; session['is_admin'] = True; return redirect(url_for('admin'))
        else: flash('Invalid Admin Credentials.', 'error')
    return render_template('admin_login.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('is_admin'): return redirect(url_for('admin_login'))
    with get_db() as conn:
        if request.method == 'POST':
            act = request.form.get('action')
            if act == 'add_match':
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
                conn.execute('UPDATE bets SET match_status = "Void" WHERE match_id = ? AND match_status = "Open"', (request.form['match_id'],)); conn.execute('DELETE FROM matches WHERE id = ?', (request.form['match_id'],)); conn.commit(); flash("Match deleted permanently.", "success")
            elif act == 'resolve_match':
                mid, wt = request.form['match_id'], request.form['winning_team'].strip()
                bets = conn.execute('SELECT * FROM bets WHERE match_id = ? AND match_status = "Open"', (mid,)).fetchall()
                for b in bets:
                    if b['team'].strip() == wt: conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (b['stake']+b['profit'], b['user_id'])); conn.execute('UPDATE bets SET match_status = "Win" WHERE id = ?', (b['id'],))
                    else: conn.execute('UPDATE bets SET match_status = "Loss" WHERE id = ?', (b['id'],))
                conn.execute('UPDATE matches SET status = ? WHERE id = ?', (f"Winner: {wt}", mid)); conn.commit(); flash(f"Match resolved. Winners paid!", "success")
            elif act == 'approve_user':
                uid = request.form['user_id']; u = conn.execute('SELECT referrer_id FROM users WHERE id = ?', (uid,)).fetchone()
                if u and u['referrer_id']: conn.execute('UPDATE users SET bonus_balance = bonus_balance + 50 WHERE id IN (?, ?)', (u['referrer_id'], uid))
                conn.execute('UPDATE users SET status = "Approved" WHERE id = ?', (uid,)); conn.commit(); flash("Player Approved!", "success")
            elif act == 'reject_user': 
                conn.execute('DELETE FROM users WHERE id = ?', (request.form['user_id'],)); conn.execute('DELETE FROM deposits WHERE user_id = ?', (request.form['user_id'],)); conn.commit(); flash("Player application declined.", "error")
            elif act == 'create_user': 
                try: conn.execute('INSERT INTO users (username, password, status) VALUES (?, ?, "Approved")', (request.form['new_username'], generate_password_hash(request.form['new_password']))); conn.commit(); flash("User created!", "success")
                except sqlite3.IntegrityError: flash("Username exists.", "error")
            
            # --- IMPROVED ACTION: ADJUST BALANCE (SUPPORT ADDS AND SUBTRACTS) ---
            elif act == 'adjust_balance': 
                target_uid = request.form['user_id']
                amount = float(request.form['amount'])
                mode = request.form['mode'] # 'add' or 'remove'
                
                if mode == 'remove':
                    # Prevent going under negative balance
                    current_bal = conn.execute('SELECT balance FROM users WHERE id = ?', (target_uid,)).fetchone()['balance']
                    amount = min(amount, current_bal)
                    conn.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (amount, target_uid))
                    flash(f"Successfully subtracted ₹{amount} from account!", "success")
                else:
                    conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (amount, target_uid))
                    flash(f"Successfully added ₹{amount} to account!", "success")
                conn.commit()
                
            elif act == 'approve_deposit':
                d = conn.execute('SELECT * FROM deposits WHERE id = ?', (request.form['deposit_id'],)).fetchone()
                if d and d['status'] == 'Pending': conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (d['amount'], d['user_id'])); conn.execute('UPDATE deposits SET status = "Approved" WHERE id = ?', (d['id'],)); conn.commit(); flash("Deposit Approved!", "success")
            elif act == 'reject_deposit': 
                conn.execute('UPDATE deposits SET status = "Rejected" WHERE id = ?', (request.form['deposit_id'],)); conn.commit(); flash("Deposit rejected.", "error")
            elif act == 'approve_withdraw': 
                conn.execute('UPDATE withdrawals SET status = "Approved" WHERE id = ?', (request.form['withdraw_id'],)); conn.commit(); flash("Withdrawal Approved!", "success")
            elif act == 'reject_withdraw':
                w = conn.execute('SELECT * FROM withdrawals WHERE id = ?', (request.form['withdraw_id'],)).fetchone()
                if w and w['status'] == 'Pending': conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (w['amount'], w['user_id'])); conn.execute('UPDATE withdrawals SET status = "Rejected" WHERE id = ?', (w['id'],)); conn.commit(); flash("Withdrawal refunded.", "error")
            return redirect(url_for('admin'))
        
        m = conn.execute('SELECT * FROM matches ORDER BY id DESC').fetchall()
        u = conn.execute('SELECT id, username, balance, bonus_balance FROM users WHERE status = "Approved" ORDER BY id DESC').fetchall()
        pu = conn.execute('SELECT id, username, mobile FROM users WHERE status = "Pending" ORDER BY id DESC').fetchall()
        w = conn.execute('''SELECT w.*, u.username FROM withdrawals w JOIN users u ON w.user_id = u.id ORDER BY w.id DESC''').fetchall()
        d = conn.execute('''SELECT d.*, u.username FROM deposits d JOIN users u ON d.user_id = u.id ORDER BY d.id DESC''').fetchall()
        
    return render_template('admin.html', matches=m, users=u, pending_users=pu, withdrawals=w, deposits=d)

if __name__ == '__main__':
    with app.app_context(): init_db()
    app.run(debug=True, port=5000)
