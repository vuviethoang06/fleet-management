"""Fleet Management - quản lý xe, bảo dưỡng, lịch trình, tài xế."""
import json, logging, os, sys, time
from contextlib import contextmanager
import psycopg2, psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool
from flask import Flask, g, redirect, render_template, request, url_for, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

class JsonFormatter(logging.Formatter):
    def format(self, r):
        return json.dumps({"ts": self.formatTime(r), "level": r.levelname, "msg": r.getMessage()}, ensure_ascii=False)

h = logging.StreamHandler(sys.stdout); h.setFormatter(JsonFormatter())
log = logging.getLogger("fleet"); log.setLevel(logging.INFO); log.addHandler(h)

app = Flask(__name__)
REQS = Counter("fleet_http_requests_total", "HTTP requests", ["method", "endpoint", "status"])
LAT = Histogram("fleet_http_request_seconds", "Latency", ["endpoint"])
pool = None

def get_pool():
    global pool
    if pool is None:
        pool = ThreadedConnectionPool(1, 8, host=os.environ["DB_HOST"], dbname=os.environ["DB_NAME"],
                                      user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"], connect_timeout=5)
    return pool

@contextmanager
def db():
    p = get_pool(); conn = p.getconn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        p.putconn(conn)

@app.before_request
def _start(): g.t = time.time()

@app.after_request
def _end(resp):
    ep = request.endpoint or "unknown"
    if ep != "metrics":
        REQS.labels(request.method, ep, resp.status_code).inc()
        LAT.labels(ep).observe(time.time() - g.t)
    return resp

@app.errorhandler(Exception)
def _err(e):
    log.error("unhandled error on %s: %s", request.path, e)
    return "Lỗi hệ thống", 500

@app.get("/health")
def health():
    with db() as c: c.execute("SELECT 1")
    return {"status": "ok"}

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

@app.get("/")
def index():
    with db() as c:
        c.execute("SELECT (SELECT count(*) FROM vehicles) v,(SELECT count(*) FROM drivers) d,"
                  "(SELECT count(*) FROM trips WHERE status='planned') t,"
                  "(SELECT count(*) FROM maintenance WHERE due_date<=CURRENT_DATE+30 AND done=false) m")
        s = c.fetchone()
    return render_template("index.html", s=s)

# ---- Vehicles ----
@app.route("/vehicles", methods=["GET", "POST"])
def vehicles():
    with db() as c:
        if request.method == "POST":
            f = request.form
            c.execute("INSERT INTO vehicles(plate,model,year,status) VALUES(%s,%s,%s,%s)",
                      (f["plate"], f["model"], f["year"], f["status"]))
            log.info("vehicle created plate=%s", f["plate"])
            return redirect(url_for("vehicles"))
        c.execute("SELECT * FROM vehicles ORDER BY id"); rows = c.fetchall()
    return render_template("vehicles.html", rows=rows)

@app.post("/vehicles/<int:i>/delete")
def vehicle_delete(i):
    with db() as c: c.execute("DELETE FROM vehicles WHERE id=%s", (i,))
    log.info("vehicle deleted id=%s", i)
    return redirect(url_for("vehicles"))

# ---- Drivers ----
@app.route("/drivers", methods=["GET", "POST"])
def drivers():
    with db() as c:
        if request.method == "POST":
            f = request.form
            c.execute("INSERT INTO drivers(name,license_no,phone) VALUES(%s,%s,%s)", (f["name"], f["license_no"], f["phone"]))
            log.info("driver created name=%s", f["name"])
            return redirect(url_for("drivers"))
        c.execute("SELECT * FROM drivers ORDER BY id"); rows = c.fetchall()
    return render_template("drivers.html", rows=rows)

@app.post("/drivers/<int:i>/delete")
def driver_delete(i):
    with db() as c: c.execute("DELETE FROM drivers WHERE id=%s", (i,))
    return redirect(url_for("drivers"))

# ---- Maintenance ----
@app.route("/maintenance", methods=["GET", "POST"])
def maintenance():
    with db() as c:
        if request.method == "POST":
            f = request.form
            c.execute("INSERT INTO maintenance(vehicle_id,description,due_date) VALUES(%s,%s,%s)",
                      (f["vehicle_id"], f["description"], f["due_date"]))
            log.info("maintenance scheduled vehicle=%s", f["vehicle_id"])
            return redirect(url_for("maintenance"))
        c.execute("SELECT m.*,v.plate FROM maintenance m JOIN vehicles v ON v.id=m.vehicle_id ORDER BY due_date"); rows = c.fetchall()
        c.execute("SELECT id,plate FROM vehicles ORDER BY plate"); vs = c.fetchall()
    return render_template("maintenance.html", rows=rows, vehicles=vs)

@app.post("/maintenance/<int:i>/done")
def maintenance_done(i):
    with db() as c: c.execute("UPDATE maintenance SET done=true WHERE id=%s", (i,))
    return redirect(url_for("maintenance"))

# ---- Trips ----
@app.route("/trips", methods=["GET", "POST"])
def trips():
    with db() as c:
        if request.method == "POST":
            f = request.form
            c.execute("INSERT INTO trips(vehicle_id,driver_id,origin,destination,depart_at) VALUES(%s,%s,%s,%s,%s)",
                      (f["vehicle_id"], f["driver_id"], f["origin"], f["destination"], f["depart_at"]))
            log.info("trip planned %s -> %s", f["origin"], f["destination"])
            return redirect(url_for("trips"))
        c.execute("SELECT t.*,v.plate,d.name driver FROM trips t JOIN vehicles v ON v.id=t.vehicle_id "
                  "JOIN drivers d ON d.id=t.driver_id ORDER BY depart_at DESC"); rows = c.fetchall()
        c.execute("SELECT id,plate FROM vehicles ORDER BY plate"); vs = c.fetchall()
        c.execute("SELECT id,name FROM drivers ORDER BY name"); ds = c.fetchall()
    return render_template("trips.html", rows=rows, vehicles=vs, drivers=ds)

@app.post("/trips/<int:i>/status")
def trip_status(i):
    with db() as c: c.execute("UPDATE trips SET status=%s WHERE id=%s", (request.form["status"], i))
    return redirect(url_for("trips"))
