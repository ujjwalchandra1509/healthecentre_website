import os
import sqlite3
from datetime import datetime
from pathlib import Path

DB = Path(__file__).with_name("medical_centre_agent.db")


def connect():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    return db


def setup():
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS doctors (
            id INTEGER PRIMARY KEY, name TEXT NOT NULL,
            specialization TEXT NOT NULL, working_days TEXT NOT NULL,
            working_hours TEXT NOT NULL, daily_capacity INTEGER NOT NULL,
            active INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY, doctor_id INTEGER NOT NULL,
            patient_name TEXT NOT NULL, patient_email TEXT NOT NULL,
            appointment_date TEXT NOT NULL, appointment_time TEXT NOT NULL,
            reason TEXT NOT NULL, status TEXT DEFAULT 'booked',
            created_at TEXT NOT NULL, UNIQUE(doctor_id, appointment_date, appointment_time)
        );
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY, title TEXT NOT NULL, event_date TEXT NOT NULL,
            location TEXT NOT NULL, description TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS centre_hours (
            id INTEGER PRIMARY KEY, day_group TEXT NOT NULL, timings TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS centre_contacts (
            id INTEGER PRIMARY KEY, contact_person TEXT NOT NULL, phone TEXT NOT NULL
        );
        """)


def records(query, values=()):
    with connect() as db:
        return [dict(row) for row in db.execute(query, values).fetchall()]


def doctors(date=None):
    date = date or datetime.now().date().isoformat()
    rows = records("""
        SELECT d.*, d.daily_capacity - COUNT(a.id) remaining_slots
        FROM doctors d LEFT JOIN appointments a
        ON a.doctor_id=d.id AND a.appointment_date=? AND a.status='booked'
        WHERE d.active=1 GROUP BY d.id ORDER BY d.name
    """, (date,))
    day = datetime.strptime(date, "%Y-%m-%d").strftime("%A")
    for row in rows:
        row["date"] = date
        row["available_on_date"] = day in row["working_days"]
    return rows


def centre_info():
    return {
        "hours": records("SELECT * FROM centre_hours ORDER BY id"),
        "contacts": records("SELECT * FROM centre_contacts ORDER BY id"),
    }


def save_appointment(data):
    with connect() as db:
        doctor = db.execute(
            "SELECT * FROM doctors WHERE name LIKE ? AND active=1",
            ("%" + data.get("doctor_name", "") + "%",),
        ).fetchone()
        if not doctor:
            return {"error": "Doctor not found."}
        count = db.execute(
            "SELECT COUNT(*) FROM appointments WHERE doctor_id=? AND appointment_date=? AND status='booked'",
            (doctor["id"], data.get("appointment_date")),
        ).fetchone()[0]
        if count >= doctor["daily_capacity"]:
            return {"error": "This doctor is fully booked on that date."}
        try:
            cursor = db.execute("""
                INSERT INTO appointments
                (doctor_id, patient_name, patient_email, appointment_date,
                 appointment_time, reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                doctor["id"], data.get("patient_name", ""), data.get("patient_email", ""),
                data.get("appointment_date", ""), data.get("appointment_time", ""),
                data.get("reason", ""), datetime.now().isoformat(timespec="seconds"),
            ))
        except sqlite3.IntegrityError:
            return {"error": "That time is already booked."}
    return {"message": f"Appointment booked with {doctor['name']}. ID: {cursor.lastrowid}"}


def edit_doctor(data):
    if data.get("admin_pin") != os.getenv("MEDICAL_ADMIN_PIN"):
        return {"error": "Invalid admin PIN."}
    fields = ("working_days", "working_hours", "daily_capacity")
    changes = {field: data[field] for field in fields if data.get(field) is not None}
    if not changes:
        return {"error": "No schedule changes supplied."}
    with connect() as db:
        doctor = db.execute(
            "SELECT id, name FROM doctors WHERE name LIKE ? AND active=1",
            ("%" + data.get("doctor_name", "") + "%",),
        ).fetchone()
        if not doctor:
            return {"error": "Doctor not found."}
        sql = ", ".join(f"{field}=?" for field in changes)
        db.execute(f"UPDATE doctors SET {sql} WHERE id=?", (*changes.values(), doctor["id"]))
    return {"message": f"Updated schedule for {doctor['name']}."}


def action(data):
    name = data.get("action")
    if name == "list_doctors":
        return {"doctors": doctors(data.get("appointment_date"))}
    if name == "centre_information":
        return centre_info()
    if name == "list_events":
        return {"events": records("SELECT * FROM events ORDER BY event_date")}
    if name == "book_appointment":
        return save_appointment(data)
    if name == "edit_doctor":
        return edit_doctor(data)
    if name == "cancel_appointment":
        with connect() as db:
            changed = db.execute(
                "UPDATE appointments SET status='cancelled' WHERE id=? AND status='booked'",
                (int(data["appointment_id"]),),
            ).rowcount
        return {"message": "Appointment cancelled." if changed else "Appointment not found."}
    return {"error": "Unknown action."}
