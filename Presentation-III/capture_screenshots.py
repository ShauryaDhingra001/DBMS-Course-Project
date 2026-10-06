"""Takes before/after screenshots of every UI screen with Playwright.
Usage:  start the app (python app.py) then  python capture_screenshots.py [http://127.0.0.1:5000]
Needs:  pip install playwright && playwright install chromium"""
import os, sys
from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000"
OUT = "screenshots"
os.makedirs(OUT, exist_ok=True)

# one test record per table (order matters: BOOKING first, PAYMENT/FEEDBACK reuse the new booking)
CASES = [
 ("USER", dict(name="Test Student", email="test.student@university.com", phone="9000000001", user_type="Student", department="Robotics")),
 ("LABORATORY", dict(lab_name="Quantum Computing Lab", location="Block H - Ground Floor", capacity="25", lab_status="Active")),
 ("EQUIPMENT_CATEGORY", dict(category_name="Spectrum Analyzer", description="Instrument that displays signal strength across frequencies")),
 ("EQUIPMENT", dict(equipment_name="R&S Spectrum Analyzer", category_id="2", lab_id="8", serial_number="SA-2026-031", purchase_date="2026-09-15", equipment_status="Available", condition="Excellent", quantity="2")),
 ("BOOKING", dict(user_id="5", equipment_id="6", booking_date="2026-10-12", start_time="10:00", end_time="12:00", purpose="Prototype enclosure printing", booking_status="Pending")),
 ("TECHNICIAN", dict(technician_name="Aman Verma", email="aman.verma@university.com", phone="9867000031", specialization="Spectrum Analysis")),
 ("MAINTENANCE_TYPE", dict(type_name="Leak Testing", description="Testing of vacuum and pressure lines for leaks")),
 ("MAINTENANCE", dict(equipment_id="6", technician_id="11", maintenance_type_id="1", maintenance_date="2026-10-05", description="Nozzle cleaning and belt tension check", cost="650", maintenance_status="Scheduled", next_maintenance_date="2027-04-05")),
 ("PAYMENT", dict(booking_id="BOOKING_NEW", amount="1100", payment_method="UPI", payment_status="Paid", transaction_reference="TXN-UPI-10031")),
 ("FEEDBACK", dict(booking_id="BOOKING_NEW", user_id="5", rating="5", comments="Smooth session and helpful lab staff")),
]

def fill(page, values):
    for k, v in values.items():
        loc = page.locator(f"[name={k}]")
        if loc.evaluate("e => e.tagName") == "SELECT":
            loc.select_option(value=v) if v.isdigit() or k.endswith("_id") else loc.select_option(label=v)
        else:
            loc.fill(v)

def shot(page, name, full=True):
    page.screenshot(path=f"{OUT}/{name}.png", full_page=full)
    print("saved", name)

with sync_playwright() as p:
    br = p.chromium.launch()
    page = br.new_page(viewport={"width": 1440, "height": 900})
    page.goto(BASE); shot(page, "00_dashboard")
    new_booking = None
    order = {t: i for i, (t, _) in enumerate(CASES, 1)}
    pending_delete = []
    for table, vals in CASES:
        n = f"{order[table]:02d}_{table.lower()}"
        page.goto(f"{BASE}/t/{table}"); shot(page, f"{n}_1_view_before")
        page.goto(f"{BASE}/t/{table}/new")
        if new_booking and vals.get("booking_id") == "BOOKING_NEW":
            vals = dict(vals, booking_id=new_booking)
        fill(page, vals); shot(page, f"{n}_2_insert_form")
        page.click("button[type=submit]"); page.wait_for_load_state()
        shot(page, f"{n}_3_insert_after")
        new_id = page.locator("tr.hl td.idc").first.inner_text()
        if table == "BOOKING":
            new_booking = new_id
            # business-rule screenshots
            page.goto(f"{BASE}/t/BOOKING/new")
            fill(page, dict(user_id="2", equipment_id="7", booking_date="2026-10-02", start_time="10:00", end_time="12:00", purpose="Clash test", booking_status="Confirmed"))
            page.click("button[type=submit]"); shot(page, f"{n}_x_rule_time_clash")
            page.goto(f"{BASE}/t/BOOKING/new")
            fill(page, dict(user_id="2", equipment_id="3", booking_date="2026-10-20", start_time="10:00", end_time="12:00", purpose="Maintenance test", booking_status="Pending"))
            page.click("button[type=submit]"); shot(page, f"{n}_x_rule_equipment_under_maintenance")
            continue                      # booking is deleted last (payment / feedback depend on it)
        # delete the record that was just inserted
        page.goto(f"{BASE}/t/{table}/{new_id}/delete"); shot(page, f"{n}_4_delete_confirm")
        page.click("button.danger"); page.wait_for_load_state(); shot(page, f"{n}_5_delete_after")
    # booking: first try (blocked by payment), then delete children, then the booking
    n = f"{order['BOOKING']:02d}_booking"
    # re-create payment + feedback so we can show the foreign-key block
    for t, v in (("PAYMENT", dict(booking_id=new_booking, amount="1100", payment_method="UPI", payment_status="Paid", transaction_reference="TXN-UPI-10032")),):
        page.goto(f"{BASE}/t/{t}/new"); fill(page, v); page.click("button[type=submit]")
    page.goto(f"{BASE}/t/BOOKING/{new_booking}/delete"); shot(page, f"{n}_x_delete_blocked_confirm")
    page.click("button.danger"); page.wait_for_load_state(); shot(page, f"{n}_x_delete_blocked_result")
    pid = page.evaluate("fetch('/t/PAYMENT').then(r=>r.text()).then(t=>t.match(/PAYMENT\\/(\\d+)\\/delete/)[1])")
    page.goto(f"{BASE}/t/PAYMENT/{pid}/delete"); page.click("button.danger")
    page.goto(f"{BASE}/t/BOOKING/{new_booking}/delete"); shot(page, f"{n}_4_delete_confirm")
    page.click("button.danger"); page.wait_for_load_state(); shot(page, f"{n}_5_delete_after")
    page.goto(f"{BASE}/t/BOOKING?q=pending"); shot(page, "11_search_booking_pending")
    page.goto(f"{BASE}/reports"); shot(page, "12_reports")
    page.goto(BASE); shot(page, "13_dashboard_change_log")
    br.close()
