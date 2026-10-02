from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash, generate_password_hash

from database import get_db
from utils import home_for_role

bp = Blueprint("auth", __name__)


@bp.route("/")
def index():
    if "user_id" in session:
        return redirect(home_for_role(session.get("role")))
    return redirect(url_for("auth.login"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(home_for_role(session.get("role")))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ? OR email = ?", (username, username)
        ).fetchone()

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid username or password.", "danger")
            return render_template("login.html")

        if not user["is_active"]:
            flash("This account has been deactivated. Contact the administrator.", "danger")
            return render_template("login.html")

        session.clear()
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["full_name"] = user["full_name"]
        session["role"] = user["role"]

        flash(f"Welcome back, {user['full_name']}!", "success")
        return redirect(home_for_role(user["role"]))

    return render_template("login.html")


@bp.route("/register", methods=["GET", "POST"])
def register():
    """Public self-registration is limited to the Student role.
    Medical Experts and Admins are provisioned by the Super Admin."""
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        student_id_no = request.form.get("student_id_no", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        errors = []
        if not full_name or not username or not email or not password:
            errors.append("All required fields must be filled in.")
        if password != confirm_password:
            errors.append("Passwords do not match.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters long.")

        db = get_db()
        if db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone():
            errors.append("That username is already taken.")
        if db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone():
            errors.append("That email is already registered.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("register.html", form=request.form)

        db.execute(
            """INSERT INTO users (username, email, password_hash, full_name, role, student_id_no)
               VALUES (?, ?, ?, ?, 'student', ?)""",
            (username, email, generate_password_hash(password), full_name, student_id_no),
        )
        db.commit()

        flash("Registration successful! You may now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html", form={})


@bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
