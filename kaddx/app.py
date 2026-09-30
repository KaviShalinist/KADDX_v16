# =============================================================
# KADDX — CM Trophy Kabaddi Tournament App (v2)
# Features: Event page, Teams, Players, Fixtures, LIVE SCORE,
#           Standings, Results, Search/Filters, Full Admin Panel
# Roles: Admin (separate login), Team Manager, Player, Public Viewer
# Run:  py app.py   →   open http://127.0.0.1:5000
# =============================================================

from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps
import sqlite3
import os
from datetime import date

app = Flask(__name__)
app.secret_key = "kaddx-secret-change-in-production"

DB_PATH = "kaddx.db"
POSITIONS = ["raider", "defender", "all-rounder"]
STAGES = ["district", "zone", "state"]
T_STATUS = ["upcoming", "live", "completed"]

# -------------------------------------------------------------
# DATABASE
# -------------------------------------------------------------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        role TEXT NOT NULL CHECK (role IN ('admin','player','manager')))""")
    cur.execute("""CREATE TABLE IF NOT EXISTS tournament (
        id INTEGER PRIMARY KEY,
        name TEXT, start_date TEXT, end_date TEXT, venue TEXT,
        gender TEXT DEFAULT 'Men',
        level TEXT DEFAULT 'District',
        status TEXT DEFAULT 'upcoming')""")
    cur.execute("""CREATE TABLE IF NOT EXISTS teams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        district TEXT,
        manager_id INTEGER REFERENCES users(id))""")
    cur.execute("""CREATE TABLE IF NOT EXISTS players (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER REFERENCES users(id),
        team_id INTEGER REFERENCES teams(id),
        position TEXT,
        gender TEXT DEFAULT 'Men',
        age INTEGER,
        weight INTEGER,
        district TEXT,
        matches_played INTEGER DEFAULT 0,
        raid_points INTEGER DEFAULT 0,
        tackle_points INTEGER DEFAULT 0,
        super10 INTEGER DEFAULT 0,
        high5 INTEGER DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        team1_id INTEGER REFERENCES teams(id),
        team2_id INTEGER REFERENCES teams(id),
        date TEXT, time TEXT, venue TEXT,
        stage TEXT DEFAULT 'district',
        status TEXT DEFAULT 'upcoming',
        referee TEXT, scorer TEXT, live_note TEXT)""")
    # migration for databases created before the live_note column
    try:
        cur.execute("ALTER TABLE matches ADD COLUMN live_note TEXT")
    except sqlite3.OperationalError:
        pass  # column already exists
    # migration for databases created before the gender column
    try:
        cur.execute("ALTER TABLE players ADD COLUMN gender TEXT DEFAULT 'Men'")
    except sqlite3.OperationalError:
        pass  # column already exists
    # migrations for account profile fields
    for col, decl in [("age", "INTEGER"), ("weight", "INTEGER"), ("district", "TEXT")]:
        try:
            cur.execute(f"ALTER TABLE players ADD COLUMN {col} {decl}")
        except sqlite3.OperationalError:
            pass  # column already exists
    cur.execute("""CREATE TABLE IF NOT EXISTS scores (
        match_id INTEGER PRIMARY KEY REFERENCES matches(id),
        team1_points INTEGER, team2_points INTEGER)""")
    conn.commit()
    conn.close()

def seed_data():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] > 0:
        conn.close()
        return
    cur.execute("INSERT INTO tournament VALUES (1,'CM Trophy Kabaddi 2026','2026-10-10','2026-10-20','District Sports Stadium, Chennai','Men','District','live')")
    for u in [
        ("Admin", "admin@kaddx.com", "admin123", "admin"),
        ("Ravi Manager", "ravi@kaddx.com", "ravi123", "manager"),
        ("Kumar Manager", "kumar@kaddx.com", "kumar123", "manager"),
        ("Arun Player", "arun@kaddx.com", "arun123", "player"),
        ("Bala Player", "bala@kaddx.com", "bala123", "player"),
        ("Deepan Player", "deepan@kaddx.com", "deepan123", "player"),
        ("Esakki Player", "esakki@kaddx.com", "esakki123", "player"),
        ("Farhan Player", "farhan@kaddx.com", "farhan123", "player"),
        ("Guna Player", "guna@kaddx.com", "guna123", "player"),
        ("Hari Player", "hari@kaddx.com", "hari123", "player"),
        ("Ilango Player", "ilango@kaddx.com", "ilango123", "player"),
        ("Jagan Player", "jagan@kaddx.com", "jagan123", "player"),
        ("Divya", "divya@kaddx.com", "divya123", "player"),
        ("Meena", "meena@kaddx.com", "meena123", "player"),
        ("Kavya", "kavya@kaddx.com", "kavya123", "player"),
        ("Priya", "priya@kaddx.com", "priya123", "player"),
        ("Anitha", "anitha@kaddx.com", "anitha123", "player"),
    ]:
        cur.execute("INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)", u)
    for t in [
        ("Chennai Cheetahs", "Chennai", 2), ("Madurai Bulls", "Madurai", 3),
        ("Trichy Tigers", "Trichy", None), ("Salem Sharks", "Salem", None),
        ("Erode Eagles", "Erode", None), ("Coimbatore Lions", "Coimbatore", None),
    ]:
        cur.execute("INSERT INTO teams (name, district, manager_id) VALUES (?,?,?)", t)
    for p in [  # uid, team, pos, MP, raid, tackle, S10, H5, gender, age, weight, district
        (4, 1, "raider", 8, 96, 14, 7, 1, "Men", 23, 74, "Chennai"), (5, 1, "defender", 8, 22, 58, 1, 5, "Men", 25, 80, "Chennai"),
        (6, 1, "all-rounder", 8, 61, 40, 4, 3, "Men", 22, 72, "Chennai"), (7, 2, "raider", 8, 88, 10, 6, 0, "Men", 24, 70, "Madurai"),
        (8, 2, "defender", 7, 15, 66, 0, 6, "Men", 26, 82, "Madurai"), (9, 3, "raider", 8, 74, 18, 5, 1, "Men", 21, 68, "Trichy"),
        (10, 3, "all-rounder", 8, 52, 45, 3, 3, "Men", 23, 75, "Trichy"), (11, 4, "raider", 6, 58, 12, 4, 1, "Men", 22, 71, "Salem"),
        (12, 5, "raider", 6, 47, 15, 3, 0, "Men", 24, 69, "Erode"),
        (13, 5, "raider", 7, 89, 12, 5, 1, "Women", 21, 58, "Erode"), (14, 4, "defender", 7, 14, 54, 0, 4, "Women", 22, 62, "Salem"),
        (15, 1, "all-rounder", 8, 71, 28, 4, 2, "Women", 20, 56, "Chennai"), (16, 2, "defender", 6, 10, 41, 0, 3, "Women", 23, 60, "Madurai"),
        (17, 3, "raider", 8, 77, 9, 5, 0, "Women", 22, 57, "Trichy"),
    ]:
        cur.execute("""INSERT INTO players (user_id, team_id, position, matches_played,
            raid_points, tackle_points, super10, high5, gender, age, weight, district)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", p)
    for m in [  # t1, t2, date, time, venue, stage, status, ref, scorer, s1, s2, live_note
        (1, 2, "2026-10-10", "5:00 PM", "District Stadium", "district", "finished", "Mr. Ramesh", "Mr. Suresh", 42, 38, None),
        (3, 4, "2026-10-10", "6:30 PM", "District Stadium", "district", "finished", "Mr. Anand", "Mr. Suresh", 35, 40, None),
        (5, 4, "2026-10-12", "2:00 PM", "XYZ Stadium, Erode", "district", "live", "Mr. Ramesh", "Mr. Vijay", 24, 21, "2nd Half | 08:32"),
        (1, 3, "2026-10-13", "5:00 PM", "District Stadium", "zone", "upcoming", "Mr. Anand", "Mr. Vijay", None, None, None),
        (2, 6, "2026-10-14", "6:30 PM", "District Stadium", "zone", "upcoming", "Mr. Bala", "Mr. Suresh", None, None, None),
        (4, 5, "2026-10-16", "5:00 PM", "Main Stadium", "state", "upcoming", "Mr. Ramesh", "Mr. Anand", None, None, None),
    ]:
        cur.execute("""INSERT INTO matches (team1_id, team2_id, date, time, venue, stage,
            status, referee, scorer, live_note) VALUES (?,?,?,?,?,?,?,?,?,?)""",
            m[:9] + (m[11],))
        if m[6] in ("finished", "live"):
            cur.execute("INSERT INTO scores (match_id, team1_points, team2_points) VALUES (?,?,?)",
                        (cur.lastrowid, m[9], m[10]))
    conn.commit()
    conn.close()

# -------------------------------------------------------------
# HELPERS
# -------------------------------------------------------------
def team_stats(team_id):
    conn = get_db()
    rows = conn.execute("""SELECT m.team1_id, m.team2_id, s.team1_points, s.team2_points
        FROM matches m JOIN scores s ON s.match_id = m.id
        WHERE m.status='finished' AND (m.team1_id=? OR m.team2_id=?)""",
        (team_id, team_id)).fetchall()
    squad = conn.execute("""SELECT COALESCE(SUM(matches_played),0) mp,
        COALESCE(SUM(raid_points),0) rp, COALESCE(SUM(tackle_points),0) tp,
        COALESCE(SUM(super10),0) s10, COALESCE(SUM(high5),0) h5
        FROM players WHERE team_id=?""", (team_id,)).fetchone()
    conn.close()
    played, won, lost, pf, pa = len(rows), 0, 0, 0, 0
    for r in rows:
        my = r["team1_points"] if r["team1_id"] == team_id else r["team2_points"]
        op = r["team2_points"] if r["team1_id"] == team_id else r["team1_points"]
        pf += my; pa += op
        if my > op: won += 1
        elif my < op: lost += 1
    return {"played": played, "won": won, "lost": lost, "pf": pf, "pa": pa,
            "diff": pf - pa, "pts": won * 5, "raid": squad["rp"], "tackle": squad["tp"],
            "super10": squad["s10"], "high5": squad["h5"]}

def current_user():
    return {"id": session.get("user_id"), "name": session.get("name"),
            "role": session.get("role")} if session.get("user_id") else None

def login_required(f):
    @wraps(f)
    def wrapper(*a, **kw):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*a, **kw)
    return wrapper

def role_required(*roles):
    def deco(f):
        @wraps(f)
        def wrapper(*a, **kw):
            if "user_id" not in session:
                return redirect(url_for("login"))
            if session.get("role") not in roles:
                return "<h2 style='padding:40px;text-align:center;'>403 — Access denied</h2>", 403
            return f(*a, **kw)
        return wrapper
    return deco

def matches_query(where="", args=(), limit=None):
    conn = get_db()
    lim = f" LIMIT {int(limit)}" if limit else ""
    rows = conn.execute("""SELECT m.*, t1.name team1, t2.name team2, t1.district d1,
        t2.district d2, s.team1_points, s.team2_points
        FROM matches m
        JOIN teams t1 ON m.team1_id = t1.id
        JOIN teams t2 ON m.team2_id = t2.id
        LEFT JOIN scores s ON s.match_id = m.id """ + where + """
        ORDER BY m.date, m.time""" + lim, args).fetchall()
    conn.close()
    return rows

def match_datetime_iso(m):
    """Convert a match row (date + '5:00 PM') to ISO string for JS countdown."""
    import re
    if not m or not m["date"]:
        return None
    hour, minute = 0, 0
    try:
        hit = re.match(r"(\d{1,2}):(\d{2})\s*(AM|PM)?", (m["time"] or "").upper())
        if hit:
            hour, minute = int(hit.group(1)), int(hit.group(2))
            mer = hit.group(3)
            if mer == "PM" and hour != 12:
                hour += 12
            if mer == "AM" and hour == 12:
                hour = 0
    except Exception:
        pass
    return f"{m['date']}T{hour:02d}:{minute:02d}:00"

def top_player(col, gender="Men"):
    """Return the top player for a stat column (raid_points / tackle_points / super10 / high5)."""
    conn = get_db()
    row = conn.execute(f"""SELECT u.name, t.name tname, p.{col} val, p.team_id FROM players p
        JOIN users u ON p.user_id=u.id
        LEFT JOIN teams t ON p.team_id=t.id
        WHERE p.gender = ?
        ORDER BY p.{col} DESC, p.id ASC LIMIT 1""", (gender,)).fetchone()
    conn.close()
    return row

# -------------------------------------------------------------
# PUBLIC PAGES
# -------------------------------------------------------------
@app.route("/")
@app.route("/cm-trophy")
def event_page():
    conn = get_db()
    t = conn.execute("SELECT * FROM tournament WHERE id=1").fetchone()
    counts = {
        "teams": conn.execute("SELECT COUNT(*) c FROM teams").fetchone()["c"],
        "players": conn.execute("SELECT COUNT(*) c FROM players").fetchone()["c"],
        "matches": conn.execute("SELECT COUNT(*) c FROM matches").fetchone()["c"],
    }
    conn.close()
    live = matches_query("WHERE m.status='live'")
    upcoming = matches_query("WHERE m.status='upcoming'", limit=1)
    next_match = upcoming[0] if upcoming else None
    today = date.today().isoformat()
    today_matches = matches_query("WHERE m.date=?", (today,))
    performers_gendered = {
        "Men": {
            "raider": top_player("raid_points", "Men"),
            "defender": top_player("tackle_points", "Men"),
            "super10": top_player("super10", "Men"),
            "high5": top_player("high5", "Men"),
        },
        "Women": {
            "raider": top_player("raid_points", "Women"),
            "defender": top_player("tackle_points", "Women"),
            "super10": top_player("super10", "Women"),
            "high5": top_player("high5", "Women"),
        },
    }
    return render_template("index.html", t=t, counts=counts, live=live,
                           next_match=next_match,
                           next_iso=match_datetime_iso(next_match),
                           today=today, today_matches=today_matches,
                           performers_gendered=performers_gendered)

@app.route("/standings")
def standings():
    conn = get_db()
    teams = conn.execute("SELECT id, name, district FROM teams").fetchall()
    conn.close()
    data = sorted([{"id": x["id"], "name": x["name"], "district": x["district"],
                    **team_stats(x["id"])} for x in teams],
                  key=lambda x: (-x["pts"], -x["diff"]))
    return render_template("standings.html", teams=data)

@app.route("/stats")
def stats_page():
    import json
    conn = get_db()
    players = conn.execute("""SELECT p.id, u.name, t.name tname, p.position,
        p.matches_played, p.raid_points, p.tackle_points, p.super10, p.high5,
        (p.raid_points + p.tackle_points) AS total_pts
        FROM players p JOIN users u ON p.user_id=u.id
        LEFT JOIN teams t ON p.team_id=t.id
        ORDER BY total_pts DESC""").fetchall()
    teams = conn.execute("SELECT id, name, district FROM teams").fetchall()
    conn.close()
    team_data = sorted([{"id": x["id"], "name": x["name"], "district": x["district"],
                        **team_stats(x["id"])} for x in teams],
                      key=lambda x: (-x["pts"], -x["diff"]))
    return render_template("stats.html", players=players, teams=team_data,
                           players_json=json.dumps([dict(p) for p in players]),
                           teams_json=json.dumps(team_data))

@app.route("/fixtures")
def fixtures():
    stage = request.args.get("stage", "")
    status = request.args.get("status", "")
    date = request.args.get("date", "")
    where, args = [], []
    if stage in STAGES:
        where.append("m.stage=?"); args.append(stage)
    if status in ("upcoming", "live", "finished"):
        where.append("m.status=?"); args.append(status)
    if date:
        where.append("m.date=?"); args.append(date)
    w = ("WHERE " + " AND ".join(where)) if where else ""
    return render_template("fixtures.html", matches=matches_query(w, args),
                           stage=stage, status=status, date=date,
                           stages=STAGES)

@app.route("/match/<int:mid>")
def match_detail(mid):
    conn = get_db()
    m = conn.execute("""SELECT m.*, t1.name team1, t2.name team2,
        s.team1_points, s.team2_points
        FROM matches m JOIN teams t1 ON m.team1_id=t1.id
        JOIN teams t2 ON m.team2_id=t2.id
        LEFT JOIN scores s ON s.match_id=m.id WHERE m.id=?""", (mid,)).fetchone()
    squad1 = squad2 = []
    if m:
        squad1 = conn.execute("""SELECT u.name, p.* FROM players p
            JOIN users u ON p.user_id=u.id WHERE p.team_id=? LIMIT 7""",
            (m["team1_id"],)).fetchall()
        squad2 = conn.execute("""SELECT u.name, p.* FROM players p
            JOIN users u ON p.user_id=u.id WHERE p.team_id=? LIMIT 7""",
            (m["team2_id"],)).fetchall()
    conn.close()
    if not m:
        return "<h2 style='padding:40px;text-align:center;'>Match not found</h2>", 404
    return render_template("match.html", m=m, squad1=squad1, squad2=squad2)

@app.route("/teams")
def teams():
    district = request.args.get("district", "")
    conn = get_db()
    rows = conn.execute("SELECT id, name, district FROM teams").fetchall()
    districts = [r["district"] for r in conn.execute(
        "SELECT DISTINCT district FROM teams WHERE district IS NOT NULL ORDER BY district")]
    live_teams = set()
    for m in conn.execute("SELECT team1_id, team2_id FROM matches WHERE status='live'"):
        live_teams.update([m["team1_id"], m["team2_id"]])
    data = []
    for x in rows:
        st = team_stats(x["id"])
        top_players = conn.execute("""SELECT u.name FROM players p
            JOIN users u ON p.user_id=u.id WHERE p.team_id=?
            ORDER BY (p.raid_points + p.tackle_points) DESC LIMIT 5""",
            (x["id"],)).fetchall()
        data.append({"id": x["id"], "name": x["name"], "district": x["district"],
                     "initials": [p["name"][0] for p in top_players],
                     "squad": conn.execute("SELECT COUNT(*) c FROM players WHERE team_id=?",
                                           (x["id"],)).fetchone()["c"],
                     "live": x["id"] in live_teams, **st})
    conn.close()
    data.sort(key=lambda x: (-x["pts"], -x["diff"]))
    for i, t in enumerate(data):
        t["rank"] = i + 1
    shown = [t for t in data if not district or t["district"] == district]
    return render_template("teams.html", teams=shown, districts=districts,
                           district=district)

@app.route("/team/<int:tid>")
def team_detail(tid):
    conn = get_db()
    team = conn.execute("""SELECT t.*, u.name manager FROM teams t
        LEFT JOIN users u ON t.manager_id=u.id WHERE t.id=?""", (tid,)).fetchone()
    players = conn.execute("""SELECT u.name, p.* FROM players p
        JOIN users u ON p.user_id=u.id WHERE p.team_id=?""", (tid,)).fetchall()
    conn.close()
    if not team:
        return "<h2 style='padding:40px;text-align:center;'>Team not found</h2>", 404
    return render_template("team.html", team=team, players=players,
                           stats=team_stats(tid))

@app.route("/players")
def players():
    q = request.args.get("q", "").strip()
    team_id = request.args.get("team", type=int)
    position = request.args.get("position", "")
    gender = request.args.get("gender", "Men")
    if gender not in ("Men", "Women"):
        gender = "Men"
    where, args = ["p.gender = ?"], [gender]
    if q:
        where.append("u.name LIKE ?"); args.append("%" + q + "%")
    if team_id:
        where.append("p.team_id=?"); args.append(team_id)
    if position in POSITIONS:
        where.append("p.position=?"); args.append(position)
    w = "WHERE " + " AND ".join(where)
    conn = get_db()
    rows = conn.execute("""SELECT u.name, p.*, t.name tname, t.district tdist
        FROM players p JOIN users u ON p.user_id=u.id
        LEFT JOIN teams t ON p.team_id=t.id """ + w + """
        ORDER BY (p.raid_points + p.tackle_points) DESC""", args).fetchall()
    team_rows = conn.execute("SELECT id, name FROM teams ORDER BY name").fetchall()
    conn.close()
    return render_template("players.html", players=rows, team_rows=team_rows,
                           q=q, team_id=team_id, position=position, gender=gender)

@app.route("/results")
def results():
    return render_template("results.html", matches=matches_query("WHERE m.status='finished'"))

# -------------------------------------------------------------
# AUTH — separate admin login page
# -------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        conn = get_db()
        u = conn.execute("SELECT * FROM users WHERE email=?",
                         (request.form["email"],)).fetchone()
        conn.close()
        if u and u["password"] == request.form["password"]:
            if u["role"] == "admin":
                error = "Admin? Please use the Admin Login page."
            else:
                session["user_id"], session["name"], session["role"] = u["id"], u["name"], u["role"]
                return redirect(url_for("dashboard"))
        else:
            error = "Invalid email or password"
    return render_template("login.html", error=error)

@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        f = request.form
        name = f.get("name", "").strip()
        email = f.get("email", "").strip().lower()
        pw = f.get("password", "")
        pw2 = f.get("confirm_password", "")
        role = f.get("role", "player")
        if not (name and email and pw):
            error = "All fields are required."
        elif "@" not in email or "." not in email:
            error = "Enter a valid email address."
        elif len(pw) < 4:
            error = "Password must be at least 4 characters."
        elif pw != pw2:
            error = "Passwords do not match."
        elif role not in ("player", "manager"):
            error = "Pick Player or Team Manager."
        else:
            conn = get_db()
            if conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone():
                error = "That email is already registered. Try logging in."
            else:
                conn.execute("INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)",
                             (name, email, pw, role))
                conn.commit()
                conn.close()
                flash("Account created! Now login with your email and password. ✅")
                return redirect(url_for("login"))
            conn.close()
    return render_template("register.html", error=error)

@app.route("/account", methods=["GET", "POST"])
@login_required
def account():
    uid = session["user_id"]
    role = session["role"]
    if role == "admin":
        return redirect(url_for("admin_home"))
    conn = get_db()
    if request.method == "POST":
        f = request.form
        name = f.get("name", "").strip()
        email = f.get("email", "").strip().lower()
        pw = f.get("new_password", "")
        pw2 = f.get("confirm_password", "")
        if not (name and email):
            flash("Name and email are required.")
        elif "@" not in email:
            flash("Enter a valid email.")
        elif pw and pw != pw2:
            flash("New passwords do not match.")
        else:
            dup = conn.execute("SELECT id FROM users WHERE email=? AND id != ?",
                               (email, uid)).fetchone()
            if dup:
                flash("That email is already used by another account.")
            else:
                if pw:
                    conn.execute("UPDATE users SET name=?, email=?, password=? WHERE id=?",
                                 (name, email, pw, uid))
                else:
                    conn.execute("UPDATE users SET name=?, email=? WHERE id=?",
                                 (name, email, uid))
                session["name"] = name
                if role == "player":
                    team_id = f.get("team_id", type=int)
                    pos = f.get("position")
                    age = f.get("age", type=int)
                    weight = f.get("weight", type=int)
                    district = f.get("district", "").strip() or None
                    if team_id and pos in POSITIONS:
                        if conn.execute("SELECT id FROM players WHERE user_id=?", (uid,)).fetchone():
                            conn.execute("""UPDATE players SET team_id=?, position=?, age=?,
                                weight=?, district=? WHERE user_id=?""",
                                (team_id, pos, age, weight, district, uid))
                        else:
                            conn.execute("""INSERT INTO players (user_id, team_id, position,
                                age, weight, district) VALUES (?,?,?,?,?,?)""",
                                (uid, team_id, pos, age, weight, district))
                else:  # manager
                    district = f.get("district", "").strip() or None
                    team = conn.execute("SELECT * FROM teams WHERE manager_id=?", (uid,)).fetchone()
                    if team:
                        conn.execute("UPDATE teams SET district=? WHERE id=?",
                                     (district, team["id"]))
                        selected = request.form.getlist("player_ids")
                        conn.execute("UPDATE players SET team_id=NULL WHERE team_id=?",
                                     (team["id"],))
                        for pid in selected:
                            conn.execute("UPDATE players SET team_id=? WHERE id=?",
                                         (team["id"], int(pid)))
                conn.commit()
                flash("Account updated successfully. ✅")
    # build view data
    me = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    teams = conn.execute("SELECT id, name FROM teams ORDER BY name").fetchall()
    districts = [r["district"] for r in conn.execute(
        "SELECT DISTINCT district FROM teams WHERE district IS NOT NULL ORDER BY district")]
    my_player, my_team, all_players = None, None, []
    if role == "player":
        my_player = conn.execute("SELECT * FROM players WHERE user_id=?", (uid,)).fetchone()
    else:
        my_team = conn.execute("SELECT * FROM teams WHERE manager_id=?", (uid,)).fetchone()
        all_players = conn.execute("""SELECT p.id, u.name, p.position, p.team_id
            FROM players p JOIN users u ON p.user_id=u.id ORDER BY u.name""").fetchall()
    conn.close()
    return render_template("account.html", me=me, teams=teams, districts=districts,
                           my_player=my_player, my_team=my_team,
                           all_players=all_players, positions=POSITIONS)

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        conn = get_db()
        u = conn.execute("SELECT * FROM users WHERE email=?",
                         (request.form["email"],)).fetchone()
        conn.close()
        if u and u["password"] == request.form["password"] and u["role"] == "admin":
            session["user_id"], session["name"], session["role"] = u["id"], u["name"], u["role"]
            return redirect(url_for("admin_home"))
        error = "Invalid admin credentials"
    return render_template("admin_login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("event_page"))

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return redirect(url_for("admin_home" if session["role"] == "admin"
                            else "manager_home" if session["role"] == "manager"
                            else "player_home"))

@app.route("/compare", methods=["GET", "POST"])
@login_required
def compare():
    conn = get_db()
    all_teams = conn.execute("SELECT id, name, district FROM teams ORDER BY name").fetchall()
    all_players = conn.execute("""SELECT p.id, u.name name, t.name tname, p.position
        FROM players p JOIN users u ON p.user_id=u.id
        LEFT JOIN teams t ON p.team_id=t.id ORDER BY u.name""").fetchall()
    conn.close()

    ctype = request.values.get("type", "teams")
    if ctype not in ("teams", "players"):
        ctype = "teams"

    def player_stats(pid):
        conn = get_db()
        row = conn.execute("""SELECT u.name name, t.name tname, p.position,
            p.matches_played mp, p.raid_points, p.tackle_points, p.super10, p.high5,
            (p.raid_points + p.tackle_points) total
            FROM players p JOIN users u ON p.user_id=u.id
            LEFT JOIN teams t ON p.team_id=t.id WHERE p.id=?""", (pid,)).fetchone()
        conn.close()
        if not row:
            return None
        d = dict(row)
        d["ppm"] = round(d["total"] / d["mp"], 1) if d["mp"] else 0
        return d

    a = b = None
    t1 = t2 = p1 = p2 = None
    if ctype == "players":
        p1 = request.values.get("p1", type=int)
        p2 = request.values.get("p2", type=int)
        if p1 and p2 and p1 != p2:
            a, b = player_stats(p1), player_stats(p2)
        elif p1 and p2:
            flash("Please pick two different players to compare.")
    else:
        t1 = request.values.get("t1", type=int)
        t2 = request.values.get("t2", type=int)
        if t1 and t2 and t1 != t2:
            conn = get_db()
            n1 = conn.execute("SELECT name, district FROM teams WHERE id=?", (t1,)).fetchone()
            n2 = conn.execute("SELECT name, district FROM teams WHERE id=?", (t2,)).fetchone()
            conn.close()
            if n1 and n2:
                a = {"name": n1["name"], "district": n1["district"], **team_stats(t1)}
                b = {"name": n2["name"], "district": n2["district"], **team_stats(t2)}
        elif t1 and t2:
            flash("Please pick two different teams to compare.")
    return render_template("compare.html", ctype=ctype, all_teams=all_teams,
                           all_players=all_players, a=a, b=b,
                           t1=t1, t2=t2, p1=p1, p2=p2)

# -------------------------------------------------------------
# ADMIN PANEL
# -------------------------------------------------------------
@app.route("/admin")
@role_required("admin")
def admin_home():
    conn = get_db()
    t = conn.execute("SELECT * FROM tournament WHERE id=1").fetchone()
    teams = conn.execute("""SELECT t.*, u.name manager FROM teams t
        LEFT JOIN users u ON t.manager_id=u.id ORDER BY t.id""").fetchall()
    players = conn.execute("""SELECT p.*, u.name pname, t.name tname FROM players p
        JOIN users u ON p.user_id=u.id LEFT JOIN teams t ON p.team_id=t.id
        ORDER BY p.id""").fetchall()
    free_players = conn.execute("""SELECT id, name FROM users WHERE role='player'
        AND id NOT IN (SELECT user_id FROM players)""").fetchall()
    team_rows = conn.execute("SELECT id, name FROM teams ORDER BY name").fetchall()
    conn.close()
    return render_template("admin.html", t=t, teams=teams, players=players,
                           matches=matches_query(), free_players=free_players,
                           team_rows=team_rows, positions=POSITIONS,
                           stages=STAGES, t_status=T_STATUS)

@app.route("/admin/tournament/edit", methods=["POST"])
@role_required("admin")
def admin_edit_tournament():
    f = request.form
    conn = get_db()
    conn.execute("""UPDATE tournament SET name=?, start_date=?, end_date=?, venue=?,
        gender=?, level=?, status=? WHERE id=1""",
        (f["name"], f["start_date"], f["end_date"], f["venue"],
         f.get("gender", "Men"), f.get("level", "District"), f.get("status", "upcoming")))
    conn.commit(); conn.close()
    flash("Tournament details updated.")
    return redirect(url_for("admin_home"))

@app.route("/admin/user/add", methods=["POST"])
@role_required("admin")
def admin_add_user():
    f = request.form
    if not (f["name"].strip() and f["email"].strip() and f["password"]):
        flash("All fields are required.")
        return redirect(url_for("admin_home"))
    conn = get_db()
    try:
        conn.execute("INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)",
                     (f["name"].strip(), f["email"].strip().lower(), f["password"], f["role"]))
        conn.commit()
        flash(f"User '{f['name']}' created as {f['role']}.")
    except sqlite3.IntegrityError:
        flash("That email is already registered.")
    conn.close()
    return redirect(url_for("admin_home"))

@app.route("/admin/team/add", methods=["POST"])
@role_required("admin")
def admin_add_team():
    f = request.form
    if not f["name"].strip():
        flash("Team name is required.")
        return redirect(url_for("admin_home"))
    conn = get_db()
    try:
        conn.execute("INSERT INTO teams (name, district, manager_id) VALUES (?,?,?)",
                     (f["name"].strip(), f.get("district", "").strip(),
                      f.get("manager_id") or None))
        conn.commit()
        flash(f"Team '{f['name']}' created.")
    except sqlite3.IntegrityError:
        flash("That team name already exists.")
    conn.close()
    return redirect(url_for("admin_home"))

@app.route("/admin/player/add", methods=["POST"])
@role_required("admin")
def admin_add_player():
    uid = request.form.get("user_id", type=int)
    tid = request.form.get("team_id", type=int)
    pos = request.form.get("position")
    gen = request.form.get("gender", "Men")
    if not (uid and tid and pos in POSITIONS and gen in ("Men", "Women")):
        flash("Pick a user, team, position and category.")
        return redirect(url_for("admin_home"))
    conn = get_db()
    conn.execute("INSERT INTO players (user_id, team_id, position, gender) VALUES (?,?,?,?)",
                 (uid, tid, pos, gen))
    conn.commit(); conn.close()
    flash("Player profile created.")
    return redirect(url_for("admin_home"))

@app.route("/admin/player/update", methods=["POST"])
@role_required("admin")
def admin_update_player():
    f = request.form
    pid = f.get("player_id", type=int)
    tid = f.get("team_id", type=int)
    pos = f.get("position")
    gen = f.get("gender", "Men")
    if not (pid and tid and pos in POSITIONS and gen in ("Men", "Women")):
        flash("Invalid player update.")
        return redirect(url_for("admin_home"))
    conn = get_db()
    conn.execute("""UPDATE players SET team_id=?, position=?, gender=?, matches_played=?,
        raid_points=?, tackle_points=?, super10=?, high5=? WHERE id=?""",
        (tid, pos, gen, f.get("matches_played", 0, type=int),
         f.get("raid_points", 0, type=int), f.get("tackle_points", 0, type=int),
         f.get("super10", 0, type=int), f.get("high5", 0, type=int), pid))
    conn.commit(); conn.close()
    flash("Player details updated.")
    return redirect(url_for("admin_home"))

@app.route("/admin/match/add", methods=["POST"])
@role_required("admin")
def admin_add_match():
    f = request.form
    t1 = f.get("team1_id", type=int)
    t2 = f.get("team2_id", type=int)
    if not (t1 and t2 and t1 != t2 and f["date"].strip() and f["venue"].strip()):
        flash("Pick two different teams, date and venue.")
        return redirect(url_for("admin_home"))
    conn = get_db()
    conn.execute("""INSERT INTO matches (team1_id, team2_id, date, time, venue,
        stage, status, referee, scorer) VALUES (?,?,?,?,?,?,'upcoming',?,?)""",
        (t1, t2, f["date"].strip(), f.get("time", "").strip(),
         f["venue"].strip(), f.get("stage", "district"),
         f.get("referee", "").strip(), f.get("scorer", "").strip()))
    conn.commit(); conn.close()
    flash("Fixture created.")
    return redirect(url_for("admin_home"))

@app.route("/admin/match/control", methods=["POST"])
@role_required("admin")
def admin_match_control():
    f = request.form
    mid = f.get("match_id", type=int)
    action = f.get("action")
    conn = get_db()
    if action == "start":
        conn.execute("UPDATE matches SET status='live' WHERE id=?", (mid,))
        flash(f"Match #{mid} is now LIVE.")
    elif action == "end":
        conn.execute("UPDATE matches SET status='finished' WHERE id=?", (mid,))
        flash(f"Match #{mid} finished — result published.")
    conn.commit(); conn.close()
    return redirect(url_for("admin_home"))

@app.route("/admin/score/submit", methods=["POST"])
@role_required("admin")
def admin_submit_score():
    f = request.form
    mid = f.get("match_id", type=int)
    p1 = f.get("team1_points", type=int)
    p2 = f.get("team2_points", type=int)
    if not (mid and p1 is not None and p2 is not None):
        flash("Enter both scores.")
        return redirect(url_for("admin_home"))
    conn = get_db()
    conn.execute("""INSERT OR REPLACE INTO scores (match_id, team1_points, team2_points)
        VALUES (?,?,?)""", (mid, p1, p2))
    note = request.form.get("live_note", "").strip() or None
    conn.execute("UPDATE matches SET live_note=? WHERE id=?", (note, mid))
    conn.commit(); conn.close()
    flash("Score updated — website shows the latest score.")
    return redirect(url_for("admin_home"))

# -------------------------------------------------------------
# PLAYER PANEL
# -------------------------------------------------------------
@app.route("/player")
@role_required("player")
def player_home():
    conn = get_db()
    me = conn.execute("""SELECT p.*, u.name, t.name team_name, t.id team_id
        FROM players p JOIN users u ON p.user_id=u.id
        LEFT JOIN teams t ON p.team_id=t.id WHERE p.user_id=?""",
        (session["user_id"],)).fetchone()
    team_rows = conn.execute("SELECT id, name FROM teams ORDER BY name").fetchall()
    conn.close()
    return render_template("player_dash.html", me=me, team_rows=team_rows,
                           positions=POSITIONS,
                           stats=(team_stats(me["team_id"]) if me and me["team_id"] else None))

@app.route("/player/profile/create", methods=["POST"])
@role_required("player")
def player_create_profile():
    tid = request.form.get("team_id", type=int)
    pos = request.form.get("position")
    gen = request.form.get("gender", "Men")
    if not (tid and pos in POSITIONS and gen in ("Men", "Women")):
        flash("Pick your team, position and category.")
        return redirect(url_for("player_home"))
    conn = get_db()
    if conn.execute("SELECT id FROM players WHERE user_id=?",
                    (session["user_id"],)).fetchone():
        flash("Your profile already exists.")
    else:
        conn.execute("INSERT INTO players (user_id, team_id, position, gender) VALUES (?,?,?,?)",
                     (session["user_id"], tid, pos, gen))
        conn.commit()
        flash("Your player profile is created! 🏆")
    conn.close()
    return redirect(url_for("player_home"))

@app.route("/player/profile/edit", methods=["POST"])
@role_required("player")
def player_edit_profile():
    pos = request.form.get("position")
    if pos not in POSITIONS:
        flash("Invalid position.")
        return redirect(url_for("player_home"))
    conn = get_db()
    conn.execute("UPDATE players SET position=? WHERE user_id=?",
                 (pos, session["user_id"]))
    conn.commit(); conn.close()
    flash("Profile updated.")
    return redirect(url_for("player_home"))

# -------------------------------------------------------------
# MANAGER PANEL
# -------------------------------------------------------------
@app.route("/manager")
@role_required("manager")
def manager_home():
    conn = get_db()
    my_team = conn.execute("SELECT * FROM teams WHERE manager_id=?",
                           (session["user_id"],)).fetchone()
    players = []
    if my_team:
        players = conn.execute("""SELECT u.name, p.* FROM players p
            JOIN users u ON p.user_id=u.id WHERE p.team_id=?
            ORDER BY (p.raid_points + p.tackle_points) DESC""",
            (my_team["id"],)).fetchall()
    conn.close()
    return render_template("manager_dash.html", my_team=my_team, players=players,
                           stats=(team_stats(my_team["id"]) if my_team else None))

@app.route("/manager/team/create", methods=["POST"])
@role_required("manager")
def manager_create_team():
    f = request.form
    if not f["name"].strip():
        flash("Team name is required.")
        return redirect(url_for("manager_home"))
    conn = get_db()
    if conn.execute("SELECT id FROM teams WHERE manager_id=?",
                    (session["user_id"],)).fetchone():
        flash("You already have a team.")
    else:
        try:
            conn.execute("INSERT INTO teams (name, district, manager_id) VALUES (?,?,?)",
                         (f["name"].strip(), f.get("district", "").strip(),
                          session["user_id"]))
            conn.commit()
            flash(f"Team '{f['name']}' created — ask the admin to add players.")
        except sqlite3.IntegrityError:
            flash("That team name already exists.")
    conn.close()
    return redirect(url_for("manager_home"))

# -------------------------------------------------------------
# START
# -------------------------------------------------------------
# Initialize the database on startup (works with BOTH local run
# and Render/gunicorn — gunicorn skips the __main__ block)
init_db()
_conn = get_db()
if _conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"] == 0:
    seed_data()
_conn.close()

if __name__ == "__main__":
    print("=" * 50)
    print("  KADDX v16.0 — CM Trophy Kabaddi")
    print("  Open: http://localhost:5000")
    print("=" * 50)
    app.run(debug=True)
