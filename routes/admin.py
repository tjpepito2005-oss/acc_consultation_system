from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.security import generate_password_hash

from database import get_db
from utils import login_required, roles_required

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/dashboard")
@login_required
@roles_required("super_admin")
def dashboard():
    db = get_db()

    user_stats = db.execute(
        """SELECT
               SUM(CASE WHEN role = 'medical_expert' THEN 1 ELSE 0 END) AS experts,
               SUM(CASE WHEN role = 'student' THEN 1 ELSE 0 END) AS students,
               SUM(CASE WHEN role = 'super_admin' THEN 1 ELSE 0 END) AS admins,
               SUM(CASE WHEN is_active = 0 THEN 1 ELSE 0 END) AS deactivated,
               COUNT(*) AS total
           FROM users"""
    ).fetchone()

    consult_stats = db.execute(
        """SELECT
               SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) AS pending,
               SUM(CASE WHEN status = 'Approved' THEN 1 ELSE 0 END) AS approved,
               SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) AS completed,
               SUM(CASE WHEN status = 'Cancelled' THEN 1 ELSE 0 END) AS cancelled,
               SUM(CASE WHEN status = 'Declined' THEN 1 ELSE 0 END) AS declined,
               COUNT(*) AS total
           FROM consultations"""
    ).fetchone()

    recent_logs = db.execute(
        """SELECT l.*, c.subject, u.full_name AS performed_by_name
           FROM consultation_logs l
           JOIN consultations c ON c.id = l.consultation_id
           LEFT JOIN users u ON u.id = l.performed_by
           ORDER BY l.timestamp DESC LIMIT 10"""
    ).fetchall()

    return render_template(
        "admin/dashboard.html", user_stats=user_stats, consult_stats=consult_stats, recent_logs=recent_logs
    )


@bp.route("/users")
@login_required
@roles_required("super_admin")
def users():
    db = get_db()
    role_filter = request.args.get("role", "")
    query = "SELECT * FROM users"
    params = []
    if role_filter:
        query += " WHERE role = ?"
        params.append(role_filter)
    query += " ORDER BY created_at DESC"
    all_users = db.execute(query, params).fetchall()
    return render_template("admin/users.html", all_users=all_users, role_filter=role_filter)


@bp.route("/users/create", methods=["GET", "POST"])
@login_required
@roles_required("super_admin")
def create_user():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        role = request.form.get("role", "")
        specialty = request.form.get("specialty", "").strip() or None
        student_id_no = request.form.get("student_id_no", "").strip() or None
        password = request.form.get("password", "")

        errors = []
        if not full_name or not username or not email or not password:
            errors.append("All required fields must be filled in.")
        if role not in ("super_admin", "medical_expert", "student"):
            errors.append("Invalid role selected.")

        db = get_db()
        if db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone():
            errors.append("That username is already taken.")
        if db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone():
            errors.append("That email is already registered.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("admin/user_form.html", form=request.form, mode="create")

        db.execute(
            """INSERT INTO users (username, email, password_hash, full_name, role, specialty, student_id_no)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (username, email, generate_password_hash(password), full_name, role, specialty, student_id_no),
        )
        db.commit()
        flash(f"{full_name} was created successfully as {role.replace('_', ' ').title()}.", "success")
        return redirect(url_for("admin.users"))

    return render_template("admin/user_form.html", form={}, mode="create")


@bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@roles_required("super_admin")
def edit_user(user_id):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if user is None:
        abort(404)

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip()
        specialty = request.form.get("specialty", "").strip() or None
        student_id_no = request.form.get("student_id_no", "").strip() or None
        new_password = request.form.get("password", "").strip()

        if not full_name or not email:
            flash("Full name and email are required.", "danger")
            return render_template("admin/user_form.html", form=request.form, mode="edit", target=user)

        if new_password:
            db.execute(
                """UPDATE users SET full_name = ?, email = ?, specialty = ?, student_id_no = ?,
                   password_hash = ? WHERE id = ?""",
                (full_name, email, specialty, student_id_no, generate_password_hash(new_password), user_id),
            )
        else:
            db.execute(
                """UPDATE users SET full_name = ?, email = ?, specialty = ?, student_id_no = ?
                   WHERE id = ?""",
                (full_name, email, specialty, student_id_no, user_id),
            )
        db.commit()
        flash("User updated successfully.", "success")
        return redirect(url_for("admin.users"))

    return render_template("admin/user_form.html", form=dict(user), mode="edit", target=user)


@bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@login_required
@roles_required("super_admin")
def toggle_user(user_id):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if user is None:
        abort(404)
    if user_id == session["user_id"]:
        flash("You cannot deactivate your own account.", "warning")
        return redirect(url_for("admin.users"))

    new_status = 0 if user["is_active"] else 1
    db.execute("UPDATE users SET is_active = ? WHERE id = ?", (new_status, user_id))
    db.commit()
    flash(
        f"{user['full_name']} has been {'activated' if new_status else 'deactivated'}.", "info"
    )
    return redirect(url_for("admin.users"))


@bp.route("/consultations")
@login_required
@roles_required("super_admin")
def consultations():
    db = get_db()
    status_filter = request.args.get("status", "")
    query = """SELECT c.*, s.full_name AS student_name, e.full_name AS expert_name
               FROM consultations c
               JOIN users s ON s.id = c.student_id
               LEFT JOIN users e ON e.id = c.expert_id"""
    params = []
    if status_filter:
        query += " WHERE c.status = ?"
        params.append(status_filter)
    query += " ORDER BY c.created_at DESC"
    all_consultations = db.execute(query, params).fetchall()
    return render_template(
        "admin/consultations.html", consultations=all_consultations, status_filter=status_filter
    )


@bp.route("/consultation/<int:consultation_id>")
@login_required
@roles_required("super_admin")
def view_consultation(consultation_id):
    db = get_db()
    consultation = db.execute(
        """SELECT c.*, s.full_name AS student_name, e.full_name AS expert_name
           FROM consultations c
           JOIN users s ON s.id = c.student_id
           LEFT JOIN users e ON e.id = c.expert_id
           WHERE c.id = ?""",
        (consultation_id,),
    ).fetchone()
    if consultation is None:
        abort(404)
    logs = db.execute(
        """SELECT l.*, u.full_name AS performed_by_name
           FROM consultation_logs l
           LEFT JOIN users u ON u.id = l.performed_by
           WHERE l.consultation_id = ? ORDER BY l.timestamp ASC""",
        (consultation_id,),
    ).fetchall()
    return render_template("admin/consultation_detail.html", c=consultation, logs=logs)


@bp.route("/settings", methods=["GET", "POST"])
@login_required
@roles_required("super_admin")
def settings():
    db = get_db()
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip()
        new_password = request.form.get("password", "").strip()

        if new_password:
            db.execute(
                "UPDATE users SET full_name = ?, email = ?, password_hash = ? WHERE id = ?",
                (full_name, email, generate_password_hash(new_password), session["user_id"]),
            )
        else:
            db.execute(
                "UPDATE users SET full_name = ?, email = ? WHERE id = ?",
                (full_name, email, session["user_id"]),
            )
        db.commit()
        session["full_name"] = full_name
        flash("Settings updated.", "success")
        return redirect(url_for("admin.settings"))

    admin_user = db.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    return render_template("admin/settings.html", admin_user=admin_user)
