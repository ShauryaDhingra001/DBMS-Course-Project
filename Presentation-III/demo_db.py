"""Creates demo.db (SQLite) with the same 10 tables + data. ONLY for trying the UI without MySQL."""
import os, sqlite3, config
import seed_data as s

DDL = """
CREATE TABLE `USER`(user_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE, phone TEXT NOT NULL,
  user_type TEXT NOT NULL CHECK(user_type IN ('Student','Faculty')), department TEXT NOT NULL);
CREATE TABLE LABORATORY(lab_id INTEGER PRIMARY KEY AUTOINCREMENT, lab_name TEXT NOT NULL, location TEXT NOT NULL,
  capacity INTEGER NOT NULL CHECK(capacity>0), lab_status TEXT NOT NULL DEFAULT 'Active');
CREATE TABLE EQUIPMENT_CATEGORY(category_id INTEGER PRIMARY KEY AUTOINCREMENT, category_name TEXT NOT NULL UNIQUE, description TEXT);
CREATE TABLE EQUIPMENT(equipment_id INTEGER PRIMARY KEY AUTOINCREMENT, equipment_name TEXT NOT NULL,
  category_id INTEGER NOT NULL REFERENCES EQUIPMENT_CATEGORY(category_id), lab_id INTEGER NOT NULL REFERENCES LABORATORY(lab_id),
  serial_number TEXT NOT NULL UNIQUE, purchase_date TEXT NOT NULL, equipment_status TEXT NOT NULL DEFAULT 'Available',
  `condition` TEXT NOT NULL DEFAULT 'Good', quantity INTEGER NOT NULL DEFAULT 1 CHECK(quantity>0));
CREATE TABLE BOOKING(booking_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES `USER`(user_id),
  equipment_id INTEGER NOT NULL REFERENCES EQUIPMENT(equipment_id), booking_date TEXT NOT NULL, start_time TEXT NOT NULL,
  end_time TEXT NOT NULL, purpose TEXT NOT NULL, booking_status TEXT NOT NULL DEFAULT 'Pending', CHECK(end_time>start_time));
CREATE TABLE TECHNICIAN(technician_id INTEGER PRIMARY KEY AUTOINCREMENT, technician_name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
  phone TEXT NOT NULL, specialization TEXT NOT NULL);
CREATE TABLE MAINTENANCE_TYPE(maintenance_type_id INTEGER PRIMARY KEY AUTOINCREMENT, type_name TEXT NOT NULL UNIQUE, description TEXT);
CREATE TABLE MAINTENANCE(maintenance_id INTEGER PRIMARY KEY AUTOINCREMENT, equipment_id INTEGER NOT NULL REFERENCES EQUIPMENT(equipment_id),
  technician_id INTEGER NOT NULL REFERENCES TECHNICIAN(technician_id),
  maintenance_type_id INTEGER NOT NULL REFERENCES MAINTENANCE_TYPE(maintenance_type_id), maintenance_date TEXT NOT NULL,
  description TEXT, cost REAL NOT NULL CHECK(cost>=0), maintenance_status TEXT NOT NULL, next_maintenance_date TEXT);
CREATE TABLE FEEDBACK(feedback_id INTEGER PRIMARY KEY AUTOINCREMENT, booking_id INTEGER NOT NULL REFERENCES BOOKING(booking_id),
  user_id INTEGER NOT NULL REFERENCES `USER`(user_id), rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5), comments TEXT, feedback_date TEXT NOT NULL);
CREATE TABLE PAYMENT(payment_id INTEGER PRIMARY KEY AUTOINCREMENT, booking_id INTEGER NOT NULL REFERENCES BOOKING(booking_id),
  amount REAL NOT NULL CHECK(amount>0), payment_date TEXT NOT NULL, payment_method TEXT NOT NULL, payment_status TEXT NOT NULL,
  transaction_reference TEXT NOT NULL UNIQUE);
"""

def build(path=None):
    path = path or config.SQLITE_PATH
    if os.path.exists(path): os.remove(path)
    c = sqlite3.connect(path); c.executescript(DDL)
    for i, (n, t, d) in enumerate(s.USERS, 1):
        a, b = n.lower().split(" ")[:2]
        c.execute("INSERT INTO `USER` VALUES(?,?,?,?,?,?)", (i, n, f"{a}.{b}@university.com", str(9876500000 + i), t, d))
    c.executemany("INSERT INTO LABORATORY(lab_name,location,capacity,lab_status) VALUES(?,?,?,?)", s.LABS)
    c.executemany("INSERT INTO EQUIPMENT_CATEGORY(category_name,description) VALUES(?,?)", s.CATEGORIES)
    c.executemany("INSERT INTO EQUIPMENT(equipment_name,category_id,lab_id,serial_number,purchase_date,equipment_status,`condition`,quantity) VALUES(?,?,?,?,?,?,?,?)", s.EQUIPMENT)
    c.executemany("INSERT INTO BOOKING(user_id,equipment_id,booking_date,start_time,end_time,purpose,booking_status) VALUES(?,?,?,?,?,?,?)", s.BOOKINGS)
    for i, (n, sp) in enumerate(s.TECHNICIANS, 1):
        a, b = n.lower().split(" ")[:2]
        c.execute("INSERT INTO TECHNICIAN VALUES(?,?,?,?,?)", (i, n, f"{a}.{b}@university.com", str(9867000000 + i), sp))
    c.executemany("INSERT INTO MAINTENANCE_TYPE(type_name,description) VALUES(?,?)", s.MAINT_TYPES)
    c.executemany("INSERT INTO MAINTENANCE(equipment_id,technician_id,maintenance_type_id,maintenance_date,description,cost,maintenance_status,next_maintenance_date) VALUES(?,?,?,?,?,?,?,?)", s.MAINTENANCE)
    for i, (r, cm, d) in enumerate(s.FEEDBACK, 1):
        c.execute("INSERT INTO FEEDBACK(booking_id,user_id,rating,comments,feedback_date) VALUES(?,?,?,?,?)", (i, i, r, cm, d))
    for i, (a, d, m, st, ref) in enumerate(s.PAYMENTS, 1):
        c.execute("INSERT INTO PAYMENT(booking_id,amount,payment_date,payment_method,payment_status,transaction_reference) VALUES(?,?,?,?,?,?)", (i, a, d, m, st, ref))
    c.commit(); c.close()

if __name__ == "__main__":
    build(); print("demo.db created")
