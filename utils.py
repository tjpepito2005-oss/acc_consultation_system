from functools import wraps
from flask import session, redirect, url_for, flash, abort


ROLE_HOME_ENDPOINT = {
    "super_admin": "admin.dashboard",
    "medical_expert": "expert.dashboard",
    "student": "student.dashboard",
}


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapped


def roles_required(*roles):
    """Restrict a view to one or more roles. Use after @login_required."""
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                flash("Please log in to continue.", "warning")
                return redirect(url_for("auth.login"))
            if session.get("role") not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


def home_for_role(role):
    return url_for(ROLE_HOME_ENDPOINT.get(role, "auth.login"))
