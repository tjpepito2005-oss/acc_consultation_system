import sys
from flask import Flask, render_template

from config import Config
from database import register_db, init_db, db_exists
from seed import seed_users
from utils import home_for_role


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    register_db(app)

    from routes.auth import bp as auth_bp
    from routes.student import bp as student_bp
    from routes.expert import bp as expert_bp
    from routes.admin import bp as admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(expert_bp)
    app.register_blueprint(admin_bp)

    @app.context_processor
    def inject_helpers():
        return {"home_for_role": home_for_role}

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    return app


app = create_app()


if __name__ == "__main__":
    # Support: python app.py --reset-db   -> rebuilds schema and re-seeds sample users
    if "--reset-db" in sys.argv or not db_exists(app):
        print("Initializing database schema...")
        init_db(app)
        seed_users(app)

    app.run(debug=True, host="0.0.0.0", port=5000)
