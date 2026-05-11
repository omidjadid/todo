#!/usr/bin/env python3
from pathlib import Path
import os
import sqlite3

import jdatetime
from flask import Flask, jsonify, render_template, request, redirect, url_for


app = Flask(__name__)

DB_PATH = Path.home() / ".daily_todo.sqlite3"

def wants_json_response() -> bool:
    return "application/json" in (request.headers.get("accept") or "").lower()

def task_to_dict(row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "jalali_date": row["jalali_date"],
        "progress": row["progress"],
        "note": row["note"] or "",
    }


def normalize_digits(text: str) -> str:
    text = str(text)

    persian = "۰۱۲۳۴۵۶۷۸۹"
    arabic = "٠١٢٣٤٥٦٧٨٩"
    english = "0123456789"

    for p, e in zip(persian, english):
        text = text.replace(p, e)

    for a, e in zip(arabic, english):
        text = text.replace(a, e)

    return text


def today_jalali() -> str:
    today = jdatetime.date.today()
    return f"{today.year:04d}-{today.month:02d}-{today.day:02d}"


def validate_jalali_date(date_text: str) -> str:
    date_text = normalize_digits(str(date_text).strip())

    if not date_text or date_text in ["today", "امروز"]:
        return today_jalali()

    try:
        y, m, d = map(int, date_text.split("-"))
        jdatetime.date(y, m, d)
        return f"{y:04d}-{m:02d}-{d:02d}"
    except Exception:
        return today_jalali()


def clean_progress(progress) -> int:
    try:
        progress = int(normalize_digits(progress))
    except Exception:
        progress = 0

    return max(0, min(100, progress))


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            jalali_date TEXT NOT NULL,
            progress INTEGER NOT NULL DEFAULT 0,
            note TEXT,
            created_at TEXT NOT NULL
        )
        """
    )

    return conn


@app.route("/")
def index():
    selected_date = request.args.get("date", "today")
    selected_date = validate_jalali_date(selected_date)

    conn = connect()

    tasks = conn.execute(
        """
        SELECT id, title, jalali_date, progress, COALESCE(note, '') AS note
        FROM tasks
        WHERE jalali_date = ?
        ORDER BY id DESC
        """,
        (selected_date,),
    ).fetchall()

    stats = conn.execute(
        """
        SELECT
            COUNT(*) AS total_count,
            SUM(CASE WHEN progress = 100 THEN 1 ELSE 0 END) AS done_count,
            AVG(progress) AS avg_progress
        FROM tasks
        WHERE jalali_date = ?
        """,
        (selected_date,),
    ).fetchone()

    conn.close()

    total_count = stats["total_count"] or 0
    done_count = stats["done_count"] or 0
    avg_progress = stats["avg_progress"] or 0

    return render_template(
        "index.html",
        tasks=tasks,
        selected_date=selected_date,
        today=today_jalali(),
        total_count=total_count,
        done_count=done_count,
        avg_progress=avg_progress,
    )


@app.route("/add", methods=["POST"])
def add_task():
    title = request.form.get("title", "").strip()
    date = validate_jalali_date(request.form.get("date", "today"))
    progress = clean_progress(request.form.get("progress", 0))
    note = request.form.get("note", "").strip()

    created_task = None
    if title:
        conn = connect()
        cur = conn.execute(
            """
            INSERT INTO tasks (title, jalali_date, progress, note, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (title, date, progress, note, str(jdatetime.datetime.now())),
        )
        task_id = cur.lastrowid
        created_task = conn.execute(
            """
            SELECT id, title, jalali_date, progress, COALESCE(note, '') AS note
            FROM tasks
            WHERE id = ?
            """,
            (task_id,),
        ).fetchone()
        conn.commit()
        conn.close()

    if wants_json_response():
        if not created_task:
            return jsonify({"ok": False}), 400
        return jsonify({"ok": True, "task": task_to_dict(created_task), "selected_date": date})

    return redirect(url_for("index", date=date))


@app.route("/update/<int:task_id>", methods=["POST"])
def update_task(task_id):
    progress = clean_progress(request.form.get("progress", 0))
    date = validate_jalali_date(request.form.get("date", "today"))

    conn = connect()
    conn.execute(
        """
        UPDATE tasks
        SET progress = ?
        WHERE id = ?
        """,
        (progress, task_id),
    )
    conn.commit()
    conn.close()

    if wants_json_response():
        return jsonify({"ok": True, "task_id": task_id, "progress": progress})

    return redirect(url_for("index", date=date))


@app.route("/edit/<int:task_id>", methods=["POST"])
def edit_task(task_id):
    title = request.form.get("title", "").strip()
    note = request.form.get("note", "").strip()
    date = validate_jalali_date(request.form.get("date", "today"))

    updated_task = None
    if title:
        conn = connect()
        conn.execute(
            """
            UPDATE tasks
            SET title = ?, note = ?
            WHERE id = ?
            """,
            (title, note, task_id),
        )
        updated_task = conn.execute(
            """
            SELECT id, title, jalali_date, progress, COALESCE(note, '') AS note
            FROM tasks
            WHERE id = ?
            """,
            (task_id,),
        ).fetchone()
        conn.commit()
        conn.close()

    if wants_json_response():
        if not updated_task:
            return jsonify({"ok": False}), 400
        return jsonify({"ok": True, "task": task_to_dict(updated_task), "selected_date": date})

    return redirect(url_for("index", date=date))


@app.route("/done/<int:task_id>", methods=["POST"])
def done_task(task_id):
    date = validate_jalali_date(request.form.get("date", "today"))

    conn = connect()
    conn.execute(
        """
        UPDATE tasks
        SET progress = 100
        WHERE id = ?
        """,
        (task_id,),
    )
    conn.commit()
    conn.close()

    if wants_json_response():
        return jsonify({"ok": True, "task_id": task_id, "progress": 100})

    return redirect(url_for("index", date=date))


@app.route("/delete/<int:task_id>", methods=["POST"])
def delete_task(task_id):
    date = validate_jalali_date(request.form.get("date", "today"))

    conn = connect()
    conn.execute(
        """
        DELETE FROM tasks
        WHERE id = ?
        """,
        (task_id,),
    )
    conn.commit()
    conn.close()

    if wants_json_response():
        return jsonify({"ok": True, "task_id": task_id})

    return redirect(url_for("index", date=date))


if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5000"))
    app.run(debug=True, host=host, port=port)
