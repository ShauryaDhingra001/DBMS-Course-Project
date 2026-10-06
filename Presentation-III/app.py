"""Laboratory Equipment Booking & Maintenance System - web UI (Flask + MySQL).
Supports: View, Insert and Delete for all 10 tables, a dashboard and SQL reports."""
import collections
import datetime as dt
import re

from flask import Flask, abort, flash, g, redirect, render_template, request, url_for

import config
import db
from schema_config import TABLES, UNBOOKABLE, referenced_by

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
PAGE_SIZE = 12
ACTIVITY = collections.deque(maxlen=10)          # live change log shown on the dashboard


# ---------------------------------------------------------------- helpers
def get_conn():
    if "conn" not in g:
        g.conn = db.connect()
    return g.conn


@app.teardown_appcontext
def close_conn(_):
    conn = g.pop("conn", None)
    if conn is not None:
        conn.close()


def q(sql, params=()):
    return db.query(get_conn(), sql, params)


def cfg_or_404(table):
    table = table.upper()
    if table not in TABLES:
        abort(404)
    return table, TABLES[table]


def count(table):
    return q(f"SELECT COUNT(*) AS n FROM `{table}`")[0]["n"]


def show_sql(sql, params):
    """SQL text with the values filled in - only for display."""
    vals = iter(params)
    def sub(_):
        v = next(vals)
        return "NULL" if v is None else (str(v) if isinstance(v, (int, float)) else "'" + str(v).replace("'", "''") + "'")
    return re.sub(r"%s", sub, sql)


def ref_options(table):
    """[(id, label)] for a foreign-key drop-down."""
    cfg = TABLES[table]
    rows = q(f"SELECT * FROM `{table}` ORDER BY `{cfg['pk']}`")
    out = []
    for r in rows:
        r = {k: db.fmt(v) for k, v in r.items()}
        out.append((r[cfg["pk"]], f"{r[cfg['pk']]} - {cfg['label'].format(**r)}"))
    return out


def ref_labels(table):
    return dict(ref_options(table))


def today():
    return dt.date.today().isoformat()


def log_activity(op, table, sql, note):
    ACTIVITY.appendleft(dict(time=dt.datetime.now().strftime("%H:%M:%S"), op=op, table=table, sql=sql, note=note))


@app.template_filter("badge")
def badge_class(v):
    v = (v or "").lower()
    if v in ("available", "active", "completed", "paid", "confirmed", "student", "excellent", "good"):
        return "ok"
    if v in ("pending", "in progress", "scheduled", "in use", "fair", "refunded", "faculty"):
        return "warn"
    if v in ("damaged", "failed", "rejected", "cancelled", "emergency", "needs repair", "poor",
             "under maintenance", "temporarily closed", "renovation"):
        return "bad"
    return "info"


@app.context_processor
def inject_nav():
    return dict(nav_tables=sorted(TABLES.items(), key=lambda kv: kv[1]["order"]),
                db_name=config.DB_NAME, fmt=db.fmt)


# ---------------------------------------------------------------- pages
@app.route("/")
def dashboard():
    kpi = dict(
        equipment=q("SELECT COALESCE(SUM(quantity),0) AS n FROM EQUIPMENT")[0]["n"],
        available=q("SELECT COUNT(*) AS n FROM EQUIPMENT WHERE equipment_status IN ('Available','Active')")[0]["n"],
        pending=q("SELECT COUNT(*) AS n FROM BOOKING WHERE booking_status='Pending'")[0]["n"],
        overdue=q("SELECT COUNT(*) AS n FROM MAINTENANCE WHERE next_maintenance_date < %s", (today(),))[0]["n"],
        revenue=q("SELECT COALESCE(SUM(amount),0) AS n FROM PAYMENT WHERE payment_status='Paid'")[0]["n"],
    )
    counts = [(t, c, count(t)) for t, c in sorted(TABLES.items(), key=lambda kv: kv[1]["order"])]
    return render_template("dashboard.html", kpi=kpi, counts=counts, activity=list(ACTIVITY))


@app.route("/t/<table>")
def view_table(table):
    table, cfg = cfg_or_404(table)
    qtext = request.args.get("q", "").strip()
    page = max(int(request.args.get("page", 1) or 1), 1)
    where, params = "", []
    if qtext:
        parts = [f"`{c}` LIKE %s" for c in cfg["search"]]
        if qtext.isdigit():
            parts.append(f"`{cfg['pk']}` = %s")
        where = " WHERE " + " OR ".join(parts)
        params = [f"%{qtext}%"] * len(cfg["search"]) + ([int(qtext)] if qtext.isdigit() else [])
    total = q(f"SELECT COUNT(*) AS n FROM `{table}`{where}", params)[0]["n"]
    sql = f"SELECT * FROM `{table}`{where} ORDER BY `{cfg['pk']}` DESC LIMIT {PAGE_SIZE} OFFSET {(page - 1) * PAGE_SIZE}"
    rows = [{k: db.fmt(v) for k, v in r.items()} for r in q(sql, params)]
    labels = {c["name"]: ref_labels(c["ref"]) for c in cfg["cols"] if c["type"] == "ref"}
    pages = max((total + PAGE_SIZE - 1) // PAGE_SIZE, 1)
    return render_template("list.html", table=table, cfg=cfg, rows=rows, labels=labels, q=qtext,
                           page=page, pages=pages, total=total, all_total=count(table),
                           hl=request.args.get("hl", ""), shown_sql=show_sql(sql, params))


def parse_form(cfg, form):
    """Validate the submitted form; return (values, errors)."""
    vals, errors = {}, []
    for c in cfg["cols"]:
        raw = (form.get(c["name"]) or "").strip()
        if not raw:
            if c["required"]:
                errors.append(f"{c['label']} is required.")
            vals[c["name"]] = None
            continue
        try:
            if c["type"] == "int":
                v = int(raw)
                if c.get("min") is not None and v < c["min"]:
                    errors.append(f"{c['label']} must be at least {c['min']}.")
            elif c["type"] == "decimal":
                v = round(float(raw), 2)
                if c.get("min") is not None and v < c["min"]:
                    errors.append(f"{c['label']} cannot be negative.")
            elif c["type"] == "date":
                v = dt.date.fromisoformat(raw).isoformat()
            elif c["type"] == "time":
                v = raw if raw.count(":") == 2 else raw + ":00"
                dt.time.fromisoformat(v)
            elif c["type"] == "ref":
                v = int(raw)
            elif c["type"] == "enum":
                if raw not in c["choices"]:
                    errors.append(f"Invalid value for {c['label']}.")
                v = int(raw) if c["name"] == "rating" else raw
            elif c["type"] == "email":
                if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", raw):
                    errors.append("Enter a valid email address.")
                v = raw
            elif c["type"] == "tel":
                if not re.fullmatch(r"\d{10}", raw):
                    errors.append("Phone number must be exactly 10 digits.")
                v = raw
            else:
                v = raw
        except ValueError:
            errors.append(f"Invalid value for {c['label']}.")
            v = None
        vals[c["name"]] = v
    return vals, errors


def business_rules(table, v):
    """Rules from the project (no double booking, active equipment only, valid dates)."""
    errs = []
    if table == "BOOKING" and not errs:
        if v["start_time"] and v["end_time"] and v["end_time"] <= v["start_time"]:
            errs.append("End time must be later than start time.")
        eq = q("SELECT equipment_name, equipment_status FROM EQUIPMENT WHERE equipment_id=%s", (v["equipment_id"],)) if v["equipment_id"] else []
        if eq and v["booking_status"] not in ("Cancelled", "Rejected") and eq[0]["equipment_status"] in UNBOOKABLE:
            errs.append(f"'{eq[0]['equipment_name']}' is {eq[0]['equipment_status']} and cannot be booked.")
        if not errs and v["booking_status"] in ("Confirmed", "Completed"):
            clash = q("SELECT booking_id FROM BOOKING WHERE equipment_id=%s AND booking_date=%s AND booking_status IN ('Confirmed','Completed') "
                      "AND start_time < %s AND end_time > %s",
                      (v["equipment_id"], v["booking_date"], v["end_time"], v["start_time"]))
            if clash:
                errs.append(f"Time clash: booking #{clash[0]['booking_id']} already holds this equipment in that slot.")
    if table == "MAINTENANCE" and v["next_maintenance_date"] and v["maintenance_date"] and v["next_maintenance_date"] <= v["maintenance_date"]:
        errs.append("Next maintenance date must be later than the maintenance date.")
    if table == "PAYMENT" and v["amount"] is not None and v["amount"] <= 0:
        errs.append("Amount must be greater than zero.")
    return errs


@app.route("/t/<table>/new", methods=["GET", "POST"])
def insert_record(table):
    table, cfg = cfg_or_404(table)
    options = {c["name"]: ref_options(c["ref"]) for c in cfg["cols"] if c["type"] == "ref"}
    form = {c["name"]: (today() if c["default"] == "today" else (c["default"] or "")) for c in cfg["cols"]}
    errors = []
    if request.method == "POST":
        form = {c["name"]: (request.form.get(c["name"]) or "").strip() for c in cfg["cols"]}
        vals, errors = parse_form(cfg, request.form)
        if not errors:
            errors = business_rules(table, vals)
        if not errors:
            names = [c["name"] for c in cfg["cols"] if vals[c["name"]] is not None]
            params = [vals[n] for n in names]
            sql = f"INSERT INTO `{table}` ({', '.join('`'+n+'`' for n in names)}) VALUES ({', '.join(['%s']*len(names))})"
            before = count(table)
            try:
                new_id, _ = db.execute(get_conn(), sql, params)
            except db.IntegrityErrors as e:
                errors = [f"Database rejected the record (integrity rule): {e.args[-1] if e.args else e}"]
            except db.DBError as e:
                errors = [f"Database error: {e.args[-1] if e.args else e}"]
            else:
                shown = show_sql(sql, params)
                after = count(table)
                note = f"{table}: {before} → {after} rows"
                flash(f"{cfg['one']} #{new_id} inserted successfully. {note}.", "success")
                flash(shown, "sql")
                log_activity("INSERT", table, shown, note)
                return redirect(url_for("view_table", table=table, hl=new_id))
    return render_template("form.html", table=table, cfg=cfg, options=options, form=form, errors=errors)


@app.route("/t/<table>/<int:rid>/delete", methods=["GET", "POST"])
def delete_record(table, rid):
    table, cfg = cfg_or_404(table)
    rows = q(f"SELECT * FROM `{table}` WHERE `{cfg['pk']}`=%s", (rid,))
    if not rows:
        flash(f"{cfg['one']} #{rid} does not exist.", "error")
        return redirect(url_for("view_table", table=table))
    row = {k: db.fmt(v) for k, v in rows[0].items()}
    children = []
    for child, col in referenced_by(table):
        n = q(f"SELECT COUNT(*) AS n FROM `{child}` WHERE `{col}`=%s", (rid,))[0]["n"]
        if n:
            children.append((child, col, n))
    if request.method == "POST":
        sql = f"DELETE FROM `{table}` WHERE `{cfg['pk']}`=%s"
        before = count(table)
        try:
            _, n = db.execute(get_conn(), sql, (rid,))
        except db.IntegrityErrors:
            flash(f"Cannot delete {cfg['one']} #{rid}: other records still depend on it "
                  f"({', '.join(f'{c} ({k})' for c, _, k in children) or 'foreign key rule'}). "
                  f"Delete those first.", "error")
            return redirect(url_for("view_table", table=table))
        except db.DBError as e:
            flash(f"Database error: {e.args[-1] if e.args else e}", "error")
            return redirect(url_for("view_table", table=table))
        shown = show_sql(sql, (rid,))
        note = f"{table}: {before} → {count(table)} rows"
        flash(f"{cfg['one']} #{rid} deleted. {note}.", "success")
        flash(shown, "sql")
        log_activity("DELETE", table, shown, note)
        return redirect(url_for("view_table", table=table))
    labels = {c["name"]: ref_labels(c["ref"]) for c in cfg["cols"] if c["type"] == "ref"}
    return render_template("confirm.html", table=table, cfg=cfg, row=row, rid=rid, children=children, labels=labels)


@app.route("/reports")
def reports():
    t = today()
    R = [
     ("Booking details (4-table JOIN)", "Who booked what, where and when.",
      "SELECT b.booking_id, u.name AS booked_by, e.equipment_name, l.lab_name, b.booking_date, b.start_time, b.end_time, b.booking_status\n"
      "FROM BOOKING b JOIN `USER` u ON u.user_id=b.user_id\n"
      "JOIN EQUIPMENT e ON e.equipment_id=b.equipment_id\n"
      "JOIN LABORATORY l ON l.lab_id=e.lab_id\nORDER BY b.booking_date DESC LIMIT 8", ()),
     ("Equipment utilisation", "Number of live bookings per equipment (cancelled / rejected excluded).",
      "SELECT e.equipment_name, COUNT(b.booking_id) AS bookings\nFROM EQUIPMENT e JOIN BOOKING b ON b.equipment_id=e.equipment_id\n"
      "WHERE b.booking_status NOT IN ('Cancelled','Rejected')\nGROUP BY e.equipment_name\nORDER BY bookings DESC, e.equipment_name LIMIT 8", ()),
     ("Maintenance overdue", "Next-maintenance date already passed (calibration / servicing due).",
      "SELECT m.maintenance_id, e.equipment_name, mt.type_name, m.next_maintenance_date, m.maintenance_status\n"
      "FROM MAINTENANCE m JOIN EQUIPMENT e ON e.equipment_id=m.equipment_id\n"
      "JOIN MAINTENANCE_TYPE mt ON mt.maintenance_type_id=m.maintenance_type_id\n"
      "WHERE m.next_maintenance_date < %s ORDER BY m.next_maintenance_date", (t,)),
     ("Equipment needing attention", "Equipment that is under maintenance or damaged.",
      "SELECT e.equipment_name, l.lab_name, e.equipment_status, e.`condition`\nFROM EQUIPMENT e JOIN LABORATORY l ON l.lab_id=e.lab_id\n"
      "WHERE e.equipment_status IN ('Under Maintenance','Damaged')", ()),
     ("Payment summary", "Count and total amount by payment status.",
      "SELECT payment_status, COUNT(*) AS payments, SUM(amount) AS total_amount\nFROM PAYMENT GROUP BY payment_status ORDER BY total_amount DESC", ()),
     ("Average rating per equipment", "User feedback joined through bookings.",
      "SELECT e.equipment_name, ROUND(AVG(f.rating),2) AS avg_rating, COUNT(*) AS reviews\nFROM FEEDBACK f JOIN BOOKING b ON b.booking_id=f.booking_id\n"
      "JOIN EQUIPMENT e ON e.equipment_id=b.equipment_id\nGROUP BY e.equipment_name ORDER BY avg_rating DESC, e.equipment_name LIMIT 8", ()),
    ]
    R = [R[0], R[1], R[3], R[2], R[4], R[5]]          # layout order: wide, 2 small, wide, 2 small
    out = []
    for title, desc, sql, params in R:
        rows = [{k: db.fmt(v) for k, v in r.items()} for r in q(sql, params)]
        out.append(dict(wide=title.startswith(('Booking details', 'Maintenance overdue')), title=title, desc=desc, sql=show_sql(sql, params), rows=rows, cols=list(rows[0].keys()) if rows else []))
    return render_template("reports.html", reports=out)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
