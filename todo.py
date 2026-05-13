#!/usr/bin/env python3
import argparse
import sqlite3
from pathlib import Path
import jdatetime

DB_PATH = Path(__file__).parent / ".daily_todo.sqlite3"


def normalize_digits(text: str) -> str:
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
    date_text = normalize_digits(date_text.strip())

    if date_text in ["today", "امروز"]:
        return today_jalali()

    try:
        y, m, d = map(int, date_text.split("-"))
        jdatetime.date(y, m, d)
        return f"{y:04d}-{m:02d}-{d:02d}"
    except Exception:
        raise ValueError("فرمت تاریخ باید مثل 1403-02-22 باشد.")


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            jalali_date TEXT NOT NULL,
            progress INTEGER NOT NULL DEFAULT 0,
            note TEXT,
            created_at TEXT NOT NULL
        )
    """)
    return conn


def add_task(args):
    date = validate_jalali_date(args.date)
    progress = max(0, min(100, args.progress))

    conn = connect()
    conn.execute(
        """
        INSERT INTO tasks (title, jalali_date, progress, note, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            args.title,
            date,
            progress,
            args.note,
            str(jdatetime.datetime.now()),
        ),
    )
    conn.commit()
    conn.close()

    print(f"ثبت شد: {args.title} | تاریخ: {date} | پیشرفت: {progress}%")


def list_tasks(args):
    conn = connect()

    if args.date:
        date = validate_jalali_date(args.date)
        rows = conn.execute(
            """
            SELECT id, title, jalali_date, progress, COALESCE(note, '')
            FROM tasks
            WHERE jalali_date = ?
            ORDER BY id
            """,
            (date,),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT id, title, jalali_date, progress, COALESCE(note, '')
            FROM tasks
            ORDER BY jalali_date DESC, id DESC
            """
        ).fetchall()

    conn.close()

    if not rows:
        print("کاری پیدا نشد.")
        return

    print("-" * 80)
    # print(f"{'ردیف':<5} {'تاریخ':<12} {'درصد':<8} {'عنوان'}")
    print(f"{'Row':<5} {'Date':<12} {'Percent':<18} {'Title'}")
    print("-" * 80)

    for task_id, title, date, progress, note in rows:
        bar_count = progress // 10
        bar = "█" * bar_count + "░" * (10 - bar_count)
        # print(f"{task_id:<5} {date:<12} {progress:>3}% {bar}  {title}")
        status = "✅ تمام شده" if progress == 100 else "در حال انجام"
        print(f"{task_id:<5} {date:<12} {progress:>3}% {bar}  {status}  {title}")
        
        if note:
            print(f"      یادداشت: {note}")

    print("-" * 80)


def update_progress(args):
    progress = max(0, min(100, args.progress))

    conn = connect()
    cur = conn.execute(
        "UPDATE tasks SET progress = ? WHERE id = ?",
        (progress, args.id),
    )
    conn.commit()
    conn.close()

    if cur.rowcount == 0:
        print("کاری با این ID پیدا نشد.")
    else:
        print(f"درصد پیشرفت کار {args.id} شد: {progress}%")


def done_task(args):
    conn = connect()
    cur = conn.execute(
        "UPDATE tasks SET progress = 100 WHERE id = ?",
        (args.id,),
    )
    conn.commit()
    conn.close()

    if cur.rowcount == 0:
        print("کاری با این ID پیدا نشد.")
    else:
        print(f"کار {args.id} کامل شد: 100%")


def delete_task(args):
    conn = connect()
    cur = conn.execute("DELETE FROM tasks WHERE id = ?", (args.id,))
    conn.commit()
    conn.close()

    if cur.rowcount == 0:
        print("کاری با این ID پیدا نشد.")
    else:
        print(f"کار {args.id} حذف شد.")


def report(args):
    date = validate_jalali_date(args.date)
    conn = connect()

    rows = conn.execute(
        """
        SELECT progress
        FROM tasks
        WHERE jalali_date = ?
        """,
        (date,),
    ).fetchall()

    conn.close()

    if not rows:
        print(f"برای تاریخ {date} کاری ثبت نشده است.")
        return

    progresses = [r[0] for r in rows]
    avg_progress = sum(progresses) / len(progresses)
    done_count = sum(1 for p in progresses if p == 100)

    print(f"گزارش روز {date}")
    print("-" * 40)
    print(f"تعداد کارها: {len(progresses)}")
    print(f"تعداد کامل‌شده: {done_count}")
    print(f"میانگین پیشرفت: {avg_progress:.1f}%")

    bar_count = int(avg_progress) // 10
    bar = "█" * bar_count + "░" * (10 - bar_count)
    print(f"وضعیت کلی: {bar} {avg_progress:.1f}%")


def main():
    parser = argparse.ArgumentParser(
        description="Todo list ساده با پشتیبانی تاریخ شمسی و درصد پیشرفت"
    )

    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="افزودن کار جدید")
    p_add.add_argument("title", help="عنوان کار")
    p_add.add_argument("--date", default="today", help="تاریخ شمسی مثل 1403-02-22 یا today")
    p_add.add_argument("--progress", type=int, default=0, help="درصد پیشرفت بین 0 تا 100")
    p_add.add_argument("--note", default="", help="یادداشت اختیاری")
    p_add.set_defaults(func=add_task)

    p_list = sub.add_parser("list", help="نمایش کارها")
    p_list.add_argument("--date", help="فیلتر بر اساس تاریخ شمسی، مثل 1403-02-22 یا today")
    p_list.set_defaults(func=list_tasks)

    p_set = sub.add_parser("set", help="تغییر درصد پیشرفت")
    p_set.add_argument("id", type=int, help="شناسه کار")
    p_set.add_argument("--progress", type=int, required=True, help="درصد جدید بین 0 تا 100")
    p_set.set_defaults(func=update_progress)

    p_done = sub.add_parser("done", help="کامل کردن کار")
    p_done.add_argument("id", type=int, help="شناسه کار")
    p_done.set_defaults(func=done_task)

    p_del = sub.add_parser("delete", help="حذف کار")
    p_del.add_argument("id", type=int, help="شناسه کار")
    p_del.set_defaults(func=delete_task)

    p_report = sub.add_parser("report", help="گزارش پیشرفت یک روز")
    p_report.add_argument("--date", default="today", help="تاریخ شمسی یا today")
    p_report.set_defaults(func=report)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
    
# uv run python todo.py add "خواندن LangChain" --date 1403-02-22 --progress 20
# uv run python todo.py add "تمرین Python" --date today --progress 0
# uv run python todo.py list
# uv run python todo.py list --date today
# uv run python todo.py set 1 --progress 60
# uv run python todo.py done 1
#uv run python todo.py report --date today
