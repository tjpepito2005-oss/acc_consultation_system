"""
Seeds the database with default sample accounts for testing:

  Super Admin    -> username: admin      password: Admin@123
  Medical Expert -> username: drsantos   password: Expert@123
  Medical Expert -> username: drreyes    password: Expert@123
  Student        -> username: jstudent   password: Student@123

Run this after init_db (see README) or via `python app.py --reset-db`.
"""
from werkzeug.security import generate_password_hash
from database import get_db


def seed_users(app):
    with app.app_context():
        db = get_db()
        cur = db.cursor()

        cur.execute("SELECT COUNT(*) AS c FROM users")
        if cur.fetchone()["c"] > 0:
            return  # already seeded

        users = [
            (
                "admin", "admin@acc.edu.ph", generate_password_hash("Admin@123"),
                "System Administrator", "super_admin", None, None,
            ),
            (
                "drsantos", "drsantos@acc.edu.ph", generate_password_hash("Expert@123"),
                "Dr. Maria Santos", "medical_expert", "General Medicine", None,
            ),
            (
                "drreyes", "drreyes@acc.edu.ph", generate_password_hash("Expert@123"),
                "Dr. Paolo Reyes", "medical_expert", "Mental Health / Counseling", None,
            ),
            (
                "jstudent", "jstudent@student.acc.edu.ph", generate_password_hash("Student@123"),
                "Juan Dela Cruz", "student", None, "2023-00123",
            ),
        ]

        cur.executemany(
            """INSERT INTO users
               (username, email, password_hash, full_name, role, specialty, student_id_no)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            users,
        )
        db.commit()
        print("Seeded default users: admin / drsantos / drreyes / jstudent")
