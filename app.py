import os, io, csv, sqlite3, secrets
from datetime import date, datetime
from functools import wraps
from flask import Flask, request, redirect, url_for, session, flash, render_template_string, send_file, abort
from werkzeug.security import check_password_hash, generate_password_hash

# Self-contained templates and CSS: upload only this Python file.
CSS = '@import url(\'https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800;900&display=swap\');:root{--red:#f04452;--bg:#09090d;--panel:#15151d;--line:#30303a;--muted:#9696a4;--text:#fafaff}*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 85% -15%,#4b111c 0,transparent 36%),var(--bg);color:var(--text);font-family:Cairo,Arial,sans-serif;min-height:100vh}a{color:inherit;text-decoration:none}button,input{font:inherit}.top{height:70px;padding:0 max(5vw,18px);display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--line);background:#0a0a0de8}.brand,.logo{font-size:22px;font-weight:900;letter-spacing:1px}.brand b,.logo b,.hero i{color:var(--red)}.wrap{max-width:1180px;margin:auto;padding:32px 20px 60px}.hero{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-bottom:24px}.eyebrow{font-size:10px;letter-spacing:2px;color:var(--red);font-weight:800;margin:0 0 6px}.hero h1{font-size:clamp(26px,4vw,38px);margin:0}.muted{color:var(--muted);font-size:12px}.tag{border:1px solid #57222b;background:#2a1016;border-radius:30px;padding:8px 12px;color:#ffabb2;font-size:11px}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px}.stat,.panel{border:1px solid var(--line);border-radius:16px;background:linear-gradient(145deg,#191922,#101015);padding:20px;min-width:0}.stat small{display:block;color:var(--muted);font-size:11px}.stat strong{font-size:29px;display:block;margin-top:8px}.cols{display:grid;grid-template-columns:1fr 1fr;gap:15px;margin-bottom:15px}.panel h2{font-size:16px;margin:0 0 7px}.upload{display:flex;gap:9px;align-items:center;flex-wrap:wrap;margin-top:18px}.upload input{min-width:0;flex:1;color:var(--muted);font-size:12px}.primary{border:0;border-radius:10px;padding:10px 16px;color:#fff;font-weight:800;background:linear-gradient(110deg,#f04452,#a70e29);cursor:pointer}.outline,.btn,.mini{border:1px solid var(--line);border-radius:9px;padding:9px 12px;background:#22222c;color:#eee;cursor:pointer;font-size:11px;font-weight:700}.buttons{display:flex;gap:9px;flex-wrap:wrap;margin-top:17px}.btn{display:inline-block}.country{display:flex;justify-content:space-between;align-items:center;border:1px solid #292933;background:#1a1a23;padding:10px 12px;border-radius:10px;margin-top:7px}.country small{display:block;color:var(--muted);font-size:10px}.download{background:#32151b;color:#ffadb4;border-radius:7px;padding:6px 9px;font-size:11px}.table{padding-bottom:0}.scroll{overflow:auto;margin:14px -20px 0}table{width:100%;border-collapse:collapse;white-space:nowrap;font-size:11px}th,td{text-align:right;padding:12px 18px;border-top:1px solid var(--line)}th{color:var(--muted);background:#111117}.mini{padding:5px 8px}.foot{color:var(--muted);font-size:10px;line-height:1.9}.login{display:grid;place-items:center;padding:18px}.login-card{width:min(100%,420px);border:1px solid #35323d;border-radius:22px;background:linear-gradient(145deg,#1a1a23,#0e0e14);padding:32px;box-shadow:0 25px 90px #0008;position:relative}.login-card:before{content:"";position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,transparent,var(--red),transparent)}.login-card h1{font-size:23px;margin:8px 0}.login-card label{display:block;font-size:12px;margin:15px 0 6px}.login-card input{width:100%;padding:12px;background:#0a0a10;border:1px solid #363640;border-radius:9px;color:white}.login-card .primary{width:100%;margin-top:20px}.login-card small{display:block;color:var(--muted);font-size:10px;text-align:center;margin-top:18px}.notice{padding:10px 12px;border-radius:9px;margin:12px 0;background:#32151b;color:#ffb1b8;font-size:12px}.notice.success{background:#103127;color:#a2f4d0}.toastbox{position:fixed;bottom:15px;left:15px;max-width:90vw}@media(max-width:800px){.stats{grid-template-columns:repeat(2,1fr)}.cols{grid-template-columns:1fr}.hero{align-items:flex-start;flex-direction:column}}@media(max-width:480px){.wrap{padding:22px 12px 45px}.stat,.panel{padding:14px}.stat strong{font-size:24px}.buttons{flex-direction:column}.buttons>*{width:100%}.login-card{padding:25px 20px}}'
LOGIN_HTML = '<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MUSAB OTP | دخول الأدمن</title><style>STYLEMARKERZZ</style></head><body class="login"><main class="login-card"><div class="logo">MUSAB <b>OTP</b></div><p class="eyebrow">SECURE ADMIN ACCESS</p><h1>تسجيل دخول الأدمن</h1><p class="muted">لوحة خاصة بالإدارة — لا يوجد إنشاء حسابات عامة.</p>{% with messages=get_flashed_messages(with_categories=true) %}{% for cat,msg in messages %}<div class="notice {{cat}}">{{msg}}</div>{% endfor %}{% endwith %}<form method="post"><label>اسم المستخدم</label><input name="username" autocomplete="username" required placeholder="admin"><label>كلمة المرور</label><input type="password" name="password" autocomplete="current-password" required placeholder="••••••••"><button class="primary">دخول آمن <span>↗</span></button></form><small>استخدم بيانات الأدمن التي وضعتها في إعدادات الاستضافة.</small></main></body></html>'.replace("STYLEMARKERZZ", CSS)
DASHBOARD_HTML = '<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MUSAB OTP | لوحة الأدمن</title><style>STYLEMARKERZZ</style></head><body><header class="top"><a class="brand" href="/">MUSAB <b>OTP</b></a><form method="post" action="/logout"><button class="outline">تسجيل الخروج</button></form></header><main class="wrap"><section class="hero"><div><p class="eyebrow">ADMIN DASHBOARD</p><h1>لوحة التحكم <i>●</i></h1><p class="muted">إدارة الأرقام حسب الدولة واستيراد وتنزيل ملفات TXT.</p></div><span class="tag">● الوضع التجريبي</span></section><section class="stats"><div class="stat"><small>إجمالي الأرقام</small><strong>{{total}}</strong></div><div class="stat"><small>أرقام مؤهلة للمراجعة</small><strong>{{eligible}}</strong></div><div class="stat"><small>المكافآت المسجلة</small><strong>{{reward_days}}</strong></div><div class="stat"><small>التقدير التجريبي</small><strong>${{estimated}}</strong><small>ليس رصيداً فعلياً</small></div></section><div class="cols"><section class="panel"><h2>📥 استيراد الأرقام</h2><p class="muted">TXT: رقم بكل سطر. CSV: أعمدة phone وcountry اختيارية.</p><form class="upload" method="post" action="/upload" enctype="multipart/form-data"><input type="file" name="file" accept=".txt,.csv" required><button class="primary">رفع الملف</button></form><div class="buttons"><a class="btn" href="/download/all">تنزيل كل الأرقام TXT ↓</a><form method="post" action="/claim-daily"><button class="btn">تسجيل مكافأة اليوم $0.10</button></form></div></section><section class="panel"><h2>🌍 الدول</h2><p class="muted">كل دولة في قائمة مستقلة.</p>{% for c in countries %}<div class="country"><div><b>{{c.country}}</b><small>{{c.n}} رقم</small></div><a class="download" href="{{ url_for(\'download_country\',country=c.country) }}">TXT ↓</a></div>{% else %}<p class="muted">ارفع ملف أرقام للبدء.</p>{% endfor %}</section></div><section class="panel table"><h2>آخر الأرقام</h2><div class="scroll"><table><thead><tr><th>الرقم</th><th>الدولة</th><th>تاريخ الإضافة</th><th>الحالة</th><th>إجراء</th></tr></thead><tbody>{% for r in recent %}<tr><td dir="ltr">{{r.phone}}</td><td>{{r.country}}</td><td>{{r.created_at}}</td><td>{{\'مؤهل للمراجعة\' if r.eligible else \'غير مؤهل\'}}</td><td><form method="post" action="/numbers/{{r.id}}/toggle"><button class="mini">{{\'إلغاء التأهيل\' if r.eligible else \'تأهيل للمراجعة\'}}</button></form></td></tr>{% else %}<tr><td colspan="5">لا توجد أرقام حتى الآن.</td></tr>{% endfor %}</tbody></table></div></section><p class="foot">الأرباح $0.15 لكل رقم والمكافأة اليومية $0.10 تجريبية فقط. لا توجد مدفوعات فعلية أو ربط SMS في هذا الإصدار. استخدم أرقاماً لديك تصريح بإدارتها.</p></main>{% with messages=get_flashed_messages(with_categories=true) %}{% if messages %}<aside class="toastbox">{% for cat,msg in messages %}<div class="notice {{cat}}">{{msg}}</div>{% endfor %}</aside>{% endif %}{% endwith %}</body></html>'.replace("STYLEMARKERZZ", CSS)

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
    return render_template_string(DASHBOARD_HTML, total=total, eligible=eligible, countries=countries,
                                  recent=recent, reward_days=reward_days,
                                  estimated=f"{cents//100}.{cents%100:02d}")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username","mpsabsms")
        password = request.form.get("password","mosab123")
        valid_user = secrets.compare_digest(username, ADMIN_USERNAME)
        valid_pass = secrets.compare_digest(password, ADMIN_PASSWORD)
        if valid_user and valid_pass:
            session.clear()
            session["admin_ok"] = True
            return redirect(url_for("home"))
        flash("اسم المستخدم أو كلمة المرور غير صحيحة.", "error")
    return render_template_string(LOGIN_HTML)

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
