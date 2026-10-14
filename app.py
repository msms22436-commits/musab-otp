import os, io, csv, sqlite3, secrets
from datetime import date, datetime
from functools import wraps
from flask import Flask, request, redirect, url_for, session, flash, render_template, send_file, abort
from werkzeug.security import check_password_hash, generate_password_hash

# Required on hosting: set ADMIN_PASSWORD and APP_SECRET_KEY as environment variables.
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
APP_SECRET_KEY = os.environ.get("APP_SECRET_KEY")
if not ADMIN_PASSWORD:
    raise RuntimeError("Set ADMIN_PASSWORD in your hosting environment. Do not use a blank/default password.")
if not APP_SECRET_KEY:
    raise RuntimeError("Set APP_SECRET_KEY in your hosting environment to a long random secret.")

app = Flask(__name__)
app.secret_key = APP_SECRET_KEY
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "0") == "1",
    MAX_CONTENT_LENGTH=5 * 1024 * 1024
)
DB_PATH = os.environ.get("DATABASE_PATH", "musab_otp.sqlite3")

def connect():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

with connect() as c:
    c.execute("""CREATE TABLE IF NOT EXISTS numbers(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT NOT NULL UNIQUE,
        country TEXT NOT NULL,
        created_at TEXT NOT NULL,
        eligible INTEGER NOT NULL DEFAULT 0
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS rewards(
        reward_date TEXT PRIMARY KEY,
        amount_cents INTEGER NOT NULL DEFAULT 10
    )""")

def admin_only(fn):
    @wraps(fn)
    def inner(*args, **kwargs):
        if not session.get("admin_ok"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return inner

def country_for(phone):
    prefixes = [
        ("+249","السودان"),("+966","السعودية"),("+971","الإمارات"),
        ("+970","فلسطين"),("+972","إسرائيل"),("+20","مصر"),
        ("+47","النرويج"),("+44","المملكة المتحدة"),("+91","الهند"),
        ("+92","باكستان"),("+90","تركيا"),("+1","أمريكا/كندا")
    ]
    for prefix, country in sorted(prefixes, key=lambda x: len(x[0]), reverse=True):
        if phone.startswith(prefix):
            return country
    return "غير محددة"

@app.route("/")
def home():
    if not session.get("admin_ok"):
        return redirect(url_for("login"))
    with connect() as c:
        total = c.execute("SELECT COUNT(*) FROM numbers").fetchone()[0]
        eligible = c.execute("SELECT COUNT(*) FROM numbers WHERE eligible=1").fetchone()[0]
        countries = c.execute("SELECT country,COUNT(*) n FROM numbers GROUP BY country ORDER BY country").fetchall()
        recent = c.execute("SELECT * FROM numbers ORDER BY id DESC LIMIT 30").fetchall()
        reward_days = c.execute("SELECT COUNT(*) FROM rewards").fetchone()[0]
    cents = eligible * 15 + reward_days * 10
    return render_template("dashboard.html", total=total, eligible=eligible, countries=countries,
                           recent=recent, reward_days=reward_days,
                           estimated=f"{cents//100}.{cents%100:02d}")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username","")
        password = request.form.get("password","")
        valid_user = secrets.compare_digest(username, ADMIN_USERNAME)
        valid_pass = check_password_hash(generate_password_hash(ADMIN_PASSWORD), password)
        if valid_user and valid_pass:
            session.clear()
            session["admin_ok"] = True
            return redirect(url_for("home"))
        flash("اسم المستخدم أو كلمة المرور غير صحيحة.", "error")
    return render_template("login.html")

@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.post("/upload")
@admin_only
def upload():
    f = request.files.get("file")
    if not f or not f.filename or not f.filename.lower().endswith((".txt",".csv")):
        flash("ارفع ملف TXT أو CSV فقط.", "error")
        return redirect(url_for("home"))
    try:
        text = f.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        flash("الملف لازم يكون UTF-8.", "error")
        return redirect(url_for("home"))
    parsed = []
    if f.filename.lower().endswith(".csv"):
        for row in csv.DictReader(io.StringIO(text)):
            phone = (row.get("phone") or row.get("number") or row.get("رقم") or "").strip().replace(" ","")
            country = (row.get("country") or row.get("الدولة") or "").strip() or country_for(phone)
            if phone: parsed.append((phone,country))
    else:
        for line in text.splitlines():
            phone = line.split(",")[0].strip().replace(" ","")
            if phone and not phone.startswith("#"): parsed.append((phone,country_for(phone)))
    added = 0
    with connect() as c:
        for phone,country in parsed:
            if phone.startswith("+") and phone[1:].isdigit() and 8 <= len(phone) <= 16:
                try:
                    c.execute("INSERT INTO numbers(phone,country,created_at,eligible) VALUES(?,?,?,0)",
                              (phone,country,datetime.utcnow().isoformat(timespec="seconds")+"Z"))
                    added += 1
                except sqlite3.IntegrityError:
                    pass
    flash(f"تم استيراد {added} رقم جديد. الأرقام لا تُحتسب أرباحاً تلقائياً.", "success")
    return redirect(url_for("home"))

@app.post("/numbers/<int:nid>/toggle")
@admin_only
def toggle(nid):
    with connect() as c:
        c.execute("UPDATE numbers SET eligible=1-eligible WHERE id=?", (nid,))
    return redirect(url_for("home"))

@app.get("/download/all")
@admin_only
def download_all():
    with connect() as c:
        rows = c.execute("SELECT phone FROM numbers ORDER BY country,phone").fetchall()
    data = "\n".join(r["phone"] for r in rows) + ("\n" if rows else "")
    return send_file(io.BytesIO(data.encode()), mimetype="text/plain",
                     as_attachment=True, download_name="MUSAB_OTP_All_Numbers.txt")

@app.get("/download/<path:country>")
@admin_only
def download_country(country):
    with connect() as c:
        rows = c.execute("SELECT phone FROM numbers WHERE country=? ORDER BY phone", (country,)).fetchall()
    if not rows: abort(404)
    data = "\n".join(r["phone"] for r in rows) + "\n"
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in country)
    return send_file(io.BytesIO(data.encode()), mimetype="text/plain",
                     as_attachment=True, download_name=f"{safe}.txt")

@app.post("/claim-daily")
@admin_only
def claim_daily():
    today = date.today().isoformat()
    with connect() as c:
        try:
            c.execute("INSERT INTO rewards(reward_date,amount_cents) VALUES(?,10)", (today,))
            flash("تم تسجيل مكافأة تجريبية لهذا اليوم: $0.10.", "success")
        except sqlite3.IntegrityError:
            flash("مكافأة اليوم مسجلة مسبقاً.", "error")
    return redirect(url_for("home"))

@app.get("/health")
def health():
    return {"status":"ok"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT","5000")), debug=False)
