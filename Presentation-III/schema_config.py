"""Describes the 10 tables once; the generic view / insert / delete pages are built from this."""

def C(name, label, type="text", ref=None, choices=None, required=True, default=None, **kw):
    return dict(name=name, label=label, type=type, ref=ref, choices=choices,
                required=required, default=default, **kw)

TABLES = {
 "USER": dict(title="Users", one="User", pk="user_id", icon="👤", order=1,
   search=["name", "email", "department"], label="{name}",
   cols=[C("name", "Full name"), C("email", "Email", "email"),
         C("phone", "Phone (10 digits)", "tel", pattern=r"\d{10}"),
         C("user_type", "User type", "enum", choices=["Student", "Faculty"]),
         C("department", "Department")]),
 "LABORATORY": dict(title="Laboratories", one="Laboratory", pk="lab_id", icon="🏛️", order=2,
   search=["lab_name", "location", "lab_status"], label="{lab_name}",
   cols=[C("lab_name", "Laboratory name"), C("location", "Location"),
         C("capacity", "Capacity", "int", min=1),
         C("lab_status", "Status", "enum", choices=["Active", "Under Maintenance", "Temporarily Closed", "Renovation"], default="Active")]),
 "EQUIPMENT_CATEGORY": dict(title="Equipment Categories", one="Category", pk="category_id", icon="🗂️", order=3,
   search=["category_name", "description"], label="{category_name}",
   cols=[C("category_name", "Category name"), C("description", "Description", "textarea")]),
 "EQUIPMENT": dict(title="Equipment", one="Equipment", pk="equipment_id", icon="🔬", order=4,
   search=["equipment_name", "serial_number", "equipment_status"], label="{equipment_name}",
   cols=[C("equipment_name", "Equipment name"),
         C("category_id", "Category", "ref", ref="EQUIPMENT_CATEGORY"),
         C("lab_id", "Laboratory", "ref", ref="LABORATORY"),
         C("serial_number", "Serial number"),
         C("purchase_date", "Purchase date", "date"),
         C("equipment_status", "Status", "enum", choices=["Available", "In Use", "Under Maintenance", "Damaged", "Active"], default="Available"),
         C("condition", "Condition", "enum", choices=["Excellent", "Good", "Fair", "Needs Repair", "Poor"], default="Good"),
         C("quantity", "Quantity", "int", min=1, default=1)]),
 "BOOKING": dict(title="Bookings", one="Booking", pk="booking_id", icon="📅", order=5,
   search=["purpose", "booking_status"], label="#{booking_id} {purpose}",
   cols=[C("user_id", "User", "ref", ref="USER"),
         C("equipment_id", "Equipment", "ref", ref="EQUIPMENT"),
         C("booking_date", "Booking date", "date"),
         C("start_time", "Start time", "time"), C("end_time", "End time", "time"),
         C("purpose", "Purpose"),
         C("booking_status", "Status", "enum", choices=["Pending", "Confirmed", "Completed", "Cancelled", "Rejected"], default="Pending")]),
 "TECHNICIAN": dict(title="Technicians", one="Technician", pk="technician_id", icon="🧰", order=6,
   search=["technician_name", "email", "specialization"], label="{technician_name}",
   cols=[C("technician_name", "Technician name"), C("email", "Email", "email"),
         C("phone", "Phone (10 digits)", "tel", pattern=r"\d{10}"),
         C("specialization", "Specialization")]),
 "MAINTENANCE_TYPE": dict(title="Maintenance Types", one="Maintenance type", pk="maintenance_type_id", icon="🏷️", order=7,
   search=["type_name", "description"], label="{type_name}",
   cols=[C("type_name", "Type name"), C("description", "Description", "textarea")]),
 "MAINTENANCE": dict(title="Maintenance", one="Maintenance record", pk="maintenance_id", icon="🛠️", order=8,
   search=["description", "maintenance_status"], label="#{maintenance_id}",
   cols=[C("equipment_id", "Equipment", "ref", ref="EQUIPMENT"),
         C("technician_id", "Technician", "ref", ref="TECHNICIAN"),
         C("maintenance_type_id", "Maintenance type", "ref", ref="MAINTENANCE_TYPE"),
         C("maintenance_date", "Maintenance date", "date"),
         C("description", "Description", "textarea"),
         C("cost", "Cost (Rs.)", "decimal", min=0),
         C("maintenance_status", "Status", "enum", choices=["Scheduled", "In Progress", "Completed", "Emergency"], default="Scheduled"),
         C("next_maintenance_date", "Next maintenance date", "date", required=False)]),
 "FEEDBACK": dict(title="Feedback", one="Feedback", pk="feedback_id", icon="⭐", order=9,
   search=["comments"], label="#{feedback_id}",
   cols=[C("booking_id", "Booking", "ref", ref="BOOKING"),
         C("user_id", "User", "ref", ref="USER"),
         C("rating", "Rating (1-5)", "enum", choices=["1", "2", "3", "4", "5"], default="5"),
         C("comments", "Comments", "textarea", required=False),
         C("feedback_date", "Feedback date", "date", default="today")]),
 "PAYMENT": dict(title="Payments", one="Payment", pk="payment_id", icon="💳", order=10,
   search=["payment_method", "payment_status", "transaction_reference"], label="#{payment_id}",
   cols=[C("booking_id", "Booking", "ref", ref="BOOKING"),
         C("amount", "Amount (Rs.)", "decimal", min=0),
         C("payment_date", "Payment date", "date", default="today"),
         C("payment_method", "Method", "enum", choices=["UPI", "Debit Card", "Credit Card", "Net Banking", "Cash"]),
         C("payment_status", "Status", "enum", choices=["Paid", "Pending", "Failed", "Refunded"], default="Pending"),
         C("transaction_reference", "Transaction reference")]),
}

# Equipment in these states cannot be booked (business rule)
UNBOOKABLE = ("Under Maintenance", "Damaged")

def referenced_by(table):
    """[(child_table, column)] that point at `table` through a foreign key."""
    out = []
    for t, cfg in TABLES.items():
        for c in cfg["cols"]:
            if c["ref"] == table:
                out.append((t, c["name"]))
    return out
