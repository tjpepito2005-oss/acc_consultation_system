from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort

from database import get_db
from utils import login_required, roles_required

bp = Blueprint("expert", __name__, url_prefix="/expert")


@bp.route("/dashboard")
@login_required
@roles_required("medical_expert")
def dashboard():
    db = get_db()
    expert_id = session["user_id"]

    stats = db.execute(
        """SELECT
               SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) AS pending,
               SUM(CASE WHEN status = 'Approved' THEN 1 ELSE 0 END) AS approved,
               SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) AS completed,
               COUNT(*) AS total
           FROM consultations
           WHERE expert_id = ? OR (expert_id IS NULL AND status = 'Pending')""",
        (expert_id,),
    ).fetchone()

    # Unassigned pending requests (any expert may pick these up) + own assigned requests
    queue = db.execute(
        """SELECT c.*, u.full_name AS student_name
           FROM consultations c
           JOIN users u ON u.id = c.student_id
           WHERE (c.expert_id = ? AND c.status IN ('Pending', 'Approved'))
              OR (c.expert_id IS NULL AND c.status = 'Pending')
           ORDER BY c.created_at ASC""",
        (expert_id,),
    ).fetchall()

    return render_template("expert/dashboard.html", stats=stats, queue=queue)


@bp.route("/requests")
@login_required
@roles_required("medical_expert")
def requests_list():
    db = get_db()
    expert_id = session["user_id"]
    status_filter = request.args.get("status", "")

    query = """SELECT c.*, u.full_name AS student_name
               FROM consultations c
               JOIN users u ON u.id = c.student_id
               WHERE (c.expert_id = ? OR (c.expert_id IS NULL AND c.status = 'Pending'))"""
    params = [expert_id]
    if status_filter:
        query += " AND c.status = ?"
        params.append(status_filter)
    query += " ORDER BY c.created_at DESC"

    consultations = db.execute(query, params).fetchall()
    return render_template(
        "expert/requests.html", consultations=consultations, status_filter=status_filter
    )


def _get_expert_consultation_or_404(db, consultation_id, expert_id):
    consultation = db.execute(
        """SELECT c.*, u.full_name AS student_name, u.student_id_no
           FROM consultations c
           JOIN users u ON u.id = c.student_id
           WHERE c.id = ? AND (c.expert_id = ? OR c.expert_id IS NULL)""",
        (consultation_id, expert_id),
    ).fetchone()
    if consultation is None:
        abort(404)
    return consultation


@bp.route("/consultation/<int:consultation_id>")
@login_required
@roles_required("medical_expert")
def view_consultation(consultation_id):
    db = get_db()
    consultation = _get_expert_consultation_or_404(db, consultation_id, session["user_id"])
    logs = db.execute(
        """SELECT l.*, u.full_name AS performed_by_name
           FROM consultation_logs l
           LEFT JOIN users u ON u.id = l.performed_by
           WHERE l.consultation_id = ? ORDER BY l.timestamp ASC""",
        (consultation_id,),
    ).fetchall()
    return render_template("expert/consultation_detail.html", c=consultation, logs=logs)


@bp.route("/consultation/<int:consultation_id>/accept", methods=["POST"])
@login_required
@roles_required("medical_expert")
def accept(consultation_id):
    db = get_db()
    expert_id = session["user_id"]
    _get_expert_consultation_or_404(db, consultation_id, expert_id)

    db.execute(
        """UPDATE consultations
           SET status = 'Approved', expert_id = ?, updated_at = CURRENT_TIMESTAMP
           WHERE id = ?""",
        (expert_id, consultation_id),
    )
    db.execute(
        """INSERT INTO consultation_logs (consultation_id, action, performed_by, details)
           VALUES (?, 'Approved', ?, 'Consultation accepted by medical expert')""",
        (consultation_id, expert_id),
    )
    db.commit()
    flash("Consultation accepted.", "success")
    return redirect(url_for("expert.view_consultation", consultation_id=consultation_id))


@bp.route("/consultation/<int:consultation_id>/decline", methods=["POST"])
@login_required
@roles_required("medical_expert")
def decline(consultation_id):
    db = get_db()
    expert_id = session["user_id"]
    _get_expert_consultation_or_404(db, consultation_id, expert_id)
    reason = request.form.get("reason", "").strip()

    db.execute(
        "UPDATE consultations SET status = 'Declined', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (consultation_id,),
    )
    db.execute(
        """INSERT INTO consultation_logs (consultation_id, action, performed_by, details)
           VALUES (?, 'Declined', ?, ?)""",
        (consultation_id, expert_id, reason or "Declined by medical expert"),
    )
    db.commit()
    flash("Consultation declined.", "info")
    return redirect(url_for("expert.requests_list"))


@bp.route("/consultation/<int:consultation_id>/reschedule", methods=["POST"])
@login_required
@roles_required("medical_expert")
def reschedule(consultation_id):
    db = get_db()
    expert_id = session["user_id"]
    _get_expert_consultation_or_404(db, consultation_id, expert_id)
    new_date = request.form.get("new_date", "").strip()

    if not new_date:
        flash("Please provide a new preferred date/time.", "danger")
        return redirect(url_for("expert.view_consultation", consultation_id=consultation_id))

    db.execute(
        """UPDATE consultations
           SET preferred_date = ?, status = 'Pending', expert_id = ?, updated_at = CURRENT_TIMESTAMP
           WHERE id = ?""",
        (new_date, expert_id, consultation_id),
    )
    db.execute(
        """INSERT INTO consultation_logs (consultation_id, action, performed_by, details)
           VALUES (?, 'Rescheduled', ?, ?)""",
        (consultation_id, expert_id, f"Rescheduled to {new_date}"),
    )
    db.commit()
    flash("Consultation rescheduled. Awaiting confirmation.", "success")
    return redirect(url_for("expert.view_consultation", consultation_id=consultation_id))


@bp.route("/consultation/<int:consultation_id>/complete", methods=["POST"])
@login_required
@roles_required("medical_expert")
def complete(consultation_id):
    db = get_db()
    expert_id = session["user_id"]
    consultation = db.execute(
        "SELECT * FROM consultations WHERE id = ? AND expert_id = ?",
        (consultation_id, expert_id),
    ).fetchone()
    if consultation is None:
        abort(404)

    notes = request.form.get("notes", "").strip()

    db.execute(
        """UPDATE consultations
           SET status = 'Completed', notes = ?, updated_at = CURRENT_TIMESTAMP
           WHERE id = ?""",
        (notes, consultation_id),
    )
    db.execute(
        """INSERT INTO consultation_logs (consultation_id, action, performed_by, details)
           VALUES (?, 'Completed', ?, 'Consultation marked complete with notes added')""",
        (consultation_id, expert_id),
    )
    db.commit()
    flash("Consultation marked as completed and notes saved.", "success")
    return redirect(url_for("expert.view_consultation", consultation_id=consultation_id))


@bp.route("/history")
@login_required
@roles_required("medical_expert")
def history():
    db = get_db()
    consultations = db.execute(
        """SELECT c.*, u.full_name AS student_name
           FROM consultations c
           JOIN users u ON u.id = c.student_id
           WHERE c.expert_id = ? AND c.status IN ('Completed', 'Declined', 'Cancelled')
           ORDER BY c.updated_at DESC""",
        (session["user_id"],),
    ).fetchall()
    return render_template("expert/history.html", consultations=consultations)
