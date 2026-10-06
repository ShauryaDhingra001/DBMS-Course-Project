# Laboratory Equipment Booking & Maintenance System - User Interface (Presentation III)

**Name:** Shaurya Dhingra  **Roll No.:** 25WU0102254
**Project:** Design and Implementation of a Database Management System for Laboratory Equipment Booking and Maintenance System
**Description:** Flask web UI connected to MySQL (`laboratory_management`) for viewing, inserting and deleting records in all 10 tables, with business-rule validation and SQL reports.

## Run it (Windows / Linux / Mac)
1. Install Python 3.9+ and make sure MySQL is running with the `laboratory_management` database you created in Presentation II.
2. `pip install -r requirements.txt`
3. Open `config.py` and set `DB_PASSWORD` (and `DB_USER` / `DB_HOST` if different) - or set environment variables.
4. `python app.py`
5. Open http://127.0.0.1:5000

## Files
| File | Purpose |
|---|---|
| `app.py` | Flask routes: dashboard, view, insert, delete, reports, business rules |
| `db.py` | Database layer (PyMySQL / mysql-connector for MySQL) |
| `schema_config.py` | Describes the 10 tables, columns, drop-downs and foreign keys |
| `templates/`, `static/` | HTML pages and CSS |
| `capture_screenshots.py` | Takes the before/after screenshots (Playwright) |
| `demo_db.py`, `seed_data.py` | SQLite copy of the data - only for trying the UI without MySQL (`DB_BACKEND=sqlite`) |

## Live demo script (10 minutes)
1. Dashboard - show the counts, then open **Bookings** (VIEW). Search `pending`.
2. In MySQL console: `SELECT COUNT(*) FROM BOOKING;` -> 30.
3. **Add booking** (user 5, Creality Ender 3D Printer, a future date, 10:00-12:00, Pending) -> banner shows 30 -> 31 and the SQL. In console: `SELECT * FROM BOOKING ORDER BY booking_id DESC LIMIT 1;`
4. Try the same equipment with a Confirmed overlapping slot -> time-clash error. Try the centrifuge -> "Under Maintenance" error.
5. **Delete** the new booking (confirm page) -> 31 -> 30. Console: `SELECT COUNT(*) FROM BOOKING;`
6. Try deleting booking 1 -> refused by the foreign key (payment / feedback depend on it).
7. Open **SQL Reports**.

Tip: to demo PAYMENT / FEEDBACK insert, first add a new booking (those tables need a booking_id that has none yet).
