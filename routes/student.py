from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort

from database import get_db
from utils import login_required, roles_required

bp = Blueprint("student", __name__, url_prefix="/student")


@bp.route("/dashboard")
@login_required
@roles_required("student")
def dashboard():
    db = get_db()
    student_id = session["user_id"]

    stats = db.execute(
        """SELECT
               SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) AS pending,
               SUM(CASE WHEN status = 'Approved' THEN 1 ELSE 0 END) AS approved,
               SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) AS completed,
               COUNT(*) AS total
           FROM consultations WHERE student_id = ?""",
        (student_id,),
    ).fetchone()

    recent = db.execute(
        """SELECT c.*, u.full_name AS expert_name
           FROM consultations c
           LEFT JOIN users u ON u.id = c.expert_id
           WHERE c.student_id = ?
           ORDER BY c.created_at DESC LIMIT 5""",
        (student_id,),
    ).fetchall()

    return render_template("student/dashboard.html", stats=stats, recent=recent)


@bp.route("/book", methods=["GET", "POST"])
@login_required
@roles_required("student")
def book():
    db = get_db()
    experts = db.execute(
        "SELECT id, full_name, specialty FROM users WHERE role = 'medical_expert' AND is_active = 1"
    ).fetchall()

    if request.method == "POST":
        subject = request.form.get("subject", "").strip()
        description = request.form.get("description", "").strip()
        preferred_date = request.form.get("preferred_date", "").strip()
        expert_id = request.form.get("expert_id") or None

        if not subject or not preferred_date:
            flash("Subject and preferred date are required.", "danger")
            return render_template("student/book.html", experts=experts, form=request.form)

        cur = db.execute(
            """INSERT INTO consultations (student_id, expert_id, subject, description, preferred_date, status)
               VALUES (?, ?, ?, ?, ?, 'Pending')""",
            (session["user_id"], expert_id, subject, description, preferred_date),
        )
        consultation_id = cur.lastrowid
        db.execute(
            """INSERT INTO consultation_logs (consultation_id, action, performed_by, details)
               VALUES (?, 'Created', ?, 'Consultation request submitted by student')""",
            (consultation_id, session["user_id"]),
        )
        db.commit()

        flash("Consultation request submitted successfully!", "success")
        return redirect(url_for("student.my_consultations"))

    return render_template("student/book.html", experts=experts, form={})


@bp.route("/my-consultations")
@login_required
@roles_required("student")
def my_consultations():
    db = get_db()
    status_filter = request.args.get("status", "")

    query = """SELECT c.*, u.full_name AS expert_name
               FROM consultations c
               LEFT JOIN users u ON u.id = c.expert_id
               WHERE c.student_id = ?"""
    params = [session["user_id"]]
    if status_filter:
        query += " AND c.status = ?"
        params.append(status_filter)
    query += " ORDER BY c.created_at DESC"

    consultations = db.execute(query, params).fetchall()
    return render_template(
        "student/my_consultations.html", consultations=consultations, status_filter=status_filter
    )


@bp.route("/consultation/<int:consultation_id>")
@login_required
@roles_required("student")
def view_consultation(consultation_id):
    db = get_db()
    consultation = db.execute(
        """SELECT c.*, u.full_name AS expert_name, u.specialty AS expert_specialty
           FROM consultations c
           LEFT JOIN users u ON u.id = c.expert_id
           WHERE c.id = ? AND c.student_id = ?""",
        (consultation_id, session["user_id"]),
    ).fetchone()

    if consultation is None:
        abort(404)

    return render_template("student/consultation_detail.html", c=consultation)


@bp.route("/consultation/<int:consultation_id>/cancel", methods=["POST"])
@login_required
@roles_required("student")
def cancel_consultation(consultation_id):
    db = get_db()
    consultation = db.execute(
        "SELECT * FROM consultations WHERE id = ? AND student_id = ?",
        (consultation_id, session["user_id"]),
    ).fetchone()

    if consultation is None:
        abort(404)
    if consultation["status"] not in ("Pending", "Approved"):
        flash("This consultation can no longer be cancelled.", "warning")
        return redirect(url_for("student.view_consultation", consultation_id=consultation_id))

    db.execute(
        "UPDATE consultations SET status = 'Cancelled', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (consultation_id,),
    )
    db.execute(
        """INSERT INTO consultation_logs (consultation_id, action, performed_by, details)
           VALUES (?, 'Cancelled', ?, 'Cancelled by student')""",
        (consultation_id, session["user_id"]),
    )
    db.commit()
    flash("Consultation request cancelled.", "info")
    return redirect(url_for("student.my_consultations"))
