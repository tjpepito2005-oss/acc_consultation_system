# ACC Consultation System

A full-stack web-based consultation system connecting **Students** with **Medical
Experts**, with **Super Admin** oversight. Built with Flask, Jinja2, and SQLite,
using session-based authentication and role-based access control (RBAC).

---

## 1. Folder Structure

```
acc_consultation_system/
│
├── app.py                  # App factory, blueprint registration, entry point
├── config.py                # Config (secret key, DB path)
├── database.py               # SQLite connection helpers + init_db()
├── schema.sql                 # Full database schema (users, consultations, logs)
├── seed.py                   # Creates the 4 default sample accounts
├── utils.py                  # login_required / roles_required decorators
├── requirements.txt
├── README.md
│
├── instance/
│   └── acc_consultation.db     # SQLite database file (created on first run)
│
├── routes/                   # Flask Blueprints — one per role/area
│   ├── auth.py                # /login, /register, /logout
│   ├── student.py              # /student/*  (booking, history)
│   ├── expert.py               # /expert/*  (accept/decline/reschedule/notes)
│   └── admin.py                # /admin/*   (user mgmt, system-wide logs)
│
├── templates/                # Jinja2 templates
│   ├── base.html               # Shared sidebar/topbar layout (Chroma theme)
│   ├── login.html
│   ├── register.html
│   ├── errors/ (403.html, 404.html)
│   ├── student/ (dashboard, book, my_consultations, consultation_detail)
│   ├── expert/  (dashboard, requests, consultation_detail, history)
│   └── admin/   (dashboard, users, user_form, consultations, consultation_detail, settings)
│
└── static/
    ├── css/style.css           # Chroma-inspired teal/cyan theme
    └── js/main.js               # (reserved for any future client-side JS)
```

### How the pieces fit together
- **`app.py`** creates the Flask app, wires up the four blueprints, and (on
  first run) builds the schema and seeds sample accounts.
- **`database.py`** opens one SQLite connection per request (via Flask's `g`
  object) and closes it automatically at teardown.
- **`utils.py`** provides `@login_required` and `@roles_required(*roles)`
  decorators used on every protected route — this is the RBAC enforcement
  layer.
- Each **role** has its own Blueprint and its own template folder, so
  permissions map directly onto which routes/templates a role can reach.

---

## 2. Local Setup & Run Instructions

### Prerequisites
- Python 3.9+ installed
- `pip` available on your PATH

### Step 1 — Get the code
Unzip the project and open a terminal inside the `acc_consultation_system/`
folder.

### Step 2 — Create and activate a virtual environment

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows (PowerShell):**
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

### Step 3 — Install dependencies
```bash
pip install -r requirements.txt
```

### Step 4 — Initialize the database
The app auto-creates and seeds `instance/acc_consultation.db` the **first
time you run it**, if the file doesn't already exist yet. A ready-to-use,
already-seeded database file is also included in this delivery under
`instance/acc_consultation.db`, so you can skip straight to Step 5.

If you ever want to wipe all data and start fresh with just the 4 sample
accounts:
```bash
python app.py --reset-db
```
This drops and recreates every table from `schema.sql`, then re-seeds the
sample users. **This deletes all consultations/users you've added.**

### Step 5 — Run the Flask server
```bash
python app.py
```
The app starts in debug mode at:
```
http://127.0.0.1:5000
```

### Step 6 — Log in
Open the URL above in your browser and log in with any of the sample
credentials in the section below. Registration for **new students** is also
open at `/register` — Medical Experts and Admin accounts must be created by
a Super Admin from the **Manage Users** panel.

---

## 3. Default / Sample Login Credentials

| Role            | Username   | Password     | Notes                                   |
|-----------------|------------|--------------|------------------------------------------|
| Super Admin     | `admin`    | `Admin@123`  | Full system access                      |
| Medical Expert  | `drsantos` | `Expert@123` | Specialty: General Medicine             |
| Medical Expert  | `drreyes`  | `Expert@123` | Specialty: Mental Health / Counseling   |
| Student         | `jstudent` | `Student@123`| Sample student account                  |

> ⚠️ These are demo credentials for local testing only. Change the
> passwords (via each role's settings / user-edit form) before deploying
> anywhere beyond your own machine, and set a real `SECRET_KEY` environment
> variable in production.

---

## 4. Feature Summary

- **Authentication:** Session-based login/logout, self-registration for
  students only, password hashing via Werkzeug.
- **RBAC:** `roles_required()` decorator guards every route; each role only
  sees its own sidebar links and dashboard.
- **Consultation lifecycle:** `Pending → Approved → Completed`, with
  `Cancelled` (student-initiated) and `Declined` (expert-initiated) side
  branches. Every state change is written to `consultation_logs` for a full
  audit trail.
- **Student:** book a consultation (optionally picking a preferred expert),
  track status, view expert notes once completed, cancel while pending/approved.
- **Medical Expert:** action queue of unassigned + own consultations,
  accept/decline/reschedule, add notes and mark complete, view own history.
- **Super Admin:** create/edit/deactivate any user, view system-wide
  consultation logs with filters, view full activity log per consultation,
  manage their own account settings.
- **UI:** Responsive sidebar layout in a teal/cyan "Chroma" palette, status
  badges, filter bars, and flash messages for feedback on every action.

## 5. Notes on Extending This Project

- Swap SQLite for Postgres/MySQL by changing `database.py`'s connection
  logic — the SQL in `schema.sql` and the routes use plain parameterized
  queries, so the migration surface is small.
- To add email notifications on status changes, hook into the same points
  where `consultation_logs` rows are inserted (`routes/student.py` and
  `routes/expert.py`).
- To require Super Admin approval before a Medical Expert account is
  active, set `is_active = 0` by default for that role at creation time.
