-- ACC Consultation System Database Schema
-- SQLite

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS consultation_logs;
DROP TABLE IF EXISTS consultations;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT UNIQUE NOT NULL,
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name     TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('super_admin', 'medical_expert', 'student')),
    specialty     TEXT,                       -- used for medical experts
    student_id_no TEXT,                       -- used for students
    is_active     INTEGER NOT NULL DEFAULT 1,
    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE consultations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id      INTEGER NOT NULL,
    expert_id       INTEGER,                  -- NULL until assigned/accepted
    subject         TEXT NOT NULL,
    description     TEXT,
    preferred_date  TEXT NOT NULL,            -- ISO date/time string chosen by student
    status          TEXT NOT NULL DEFAULT 'Pending'
                        CHECK (status IN ('Pending', 'Approved', 'Completed', 'Cancelled', 'Declined')),
    notes           TEXT,                     -- expert's consultation notes/record
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES users (id),
    FOREIGN KEY (expert_id)  REFERENCES users (id)
);

CREATE TABLE consultation_logs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    consultation_id  INTEGER NOT NULL,
    action           TEXT NOT NULL,           -- e.g. 'Created', 'Approved', 'Declined', 'Rescheduled', 'Completed'
    performed_by      INTEGER,                -- user id who performed the action
    details          TEXT,
    timestamp        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (consultation_id) REFERENCES consultations (id),
    FOREIGN KEY (performed_by) REFERENCES users (id)
);

CREATE INDEX idx_consultations_student ON consultations (student_id);
CREATE INDEX idx_consultations_expert ON consultations (expert_id);
CREATE INDEX idx_consultations_status ON consultations (status);
CREATE INDEX idx_logs_consultation ON consultation_logs (consultation_id);
