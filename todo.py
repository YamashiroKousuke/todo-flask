#!/usr/bin/env python3
"""
Simple ToDo CLI (no external deps)

Usage examples:
  - Add a task:
      python todo.py add "Buy milk" --due 2025-09-01

  - List tasks (pending by default):
      python todo.py list
      python todo.py list --all
      python todo.py list --done

  - Mark as done / delete / edit:
      python todo.py done 3 4
      python todo.py delete 2
      python todo.py edit 5 --title "Buy oat milk" --due 2025-09-03
      python todo.py edit 5 --clear-due
      python todo.py edit 5 --undone

  - Clear tasks and see stats:
      python todo.py clear --done
      python todo.py clear --all
      python todo.py stats

Data is stored in a `todos.json` file next to this script.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict
from datetime import datetime, date
from pathlib import Path
from typing import List, Optional, Dict, Any


DATA_FILE = Path(__file__).with_name("todos.json")


def now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def parse_date(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    try:
        # Accept YYYY-MM-DD
        d = date.fromisoformat(s)
        return d.isoformat()
    except Exception:
        raise argparse.ArgumentTypeError(
            f"Invalid date '{s}'. Use YYYY-MM-DD (e.g., 2025-09-01)."
        )


@dataclass
class Task:
    id: int
    title: str
    completed: bool = False
    created_at: str = now_iso()
    due: Optional[str] = None  # YYYY-MM-DD
    completed_at: Optional[str] = None

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Task":
        return Task(
            id=int(d["id"]),
            title=str(d["title"]),
            completed=bool(d.get("completed", False)),
            created_at=str(d.get("created_at") or now_iso()),
            due=d.get("due"),
            completed_at=d.get("completed_at"),
        )


def load_data() -> Dict[str, Any]:
    if not DATA_FILE.exists():
        return {"next_id": 1, "tasks": []}
    try:
        with DATA_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("Corrupt data file root")
        data.setdefault("next_id", 1)
        data.setdefault("tasks", [])
        # sanitize tasks
        data["tasks"] = [asdict(Task.from_dict(t)) for t in data["tasks"]]
        return data
    except json.JSONDecodeError:
        raise SystemExit(f"Failed to parse {DATA_FILE.name}. Fix or delete it.")


def save_data(data: Dict[str, Any]) -> None:
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_task(title: str, due: Optional[str]) -> Task:
    data = load_data()
    tid = int(data["next_id"])
    task = Task(id=tid, title=title, due=due)
    data["tasks"].append(asdict(task))
    data["next_id"] = tid + 1
    save_data(data)
    return task


def list_tasks(kind: str) -> List[Task]:
    data = load_data()
    tasks = [Task.from_dict(t) for t in data["tasks"]]
    if kind == "pending":
        tasks = [t for t in tasks if not t.completed]
    elif kind == "done":
        tasks = [t for t in tasks if t.completed]
    # else 'all' -> no filter
    # Sort pending by due date (None last), then created_at; done by completed_at desc
    if kind in ("pending", "all"):
        tasks.sort(key=lambda t: (
            (t.due is None, t.due or "9999-12-31"),
            t.created_at,
        ))
    elif kind == "done":
        tasks.sort(key=lambda t: t.completed_at or "", reverse=True)
    return tasks


def mark_done(ids: List[int]) -> List[Task]:
    data = load_data()
    idset = set(ids)
    updated: List[Task] = []
    for i, raw in enumerate(data["tasks"]):
        if raw["id"] in idset and not raw.get("completed", False):
            raw["completed"] = True
            raw["completed_at"] = now_iso()
            updated.append(Task.from_dict(raw))
    save_data(data)
    return updated


def delete_tasks(ids: List[int]) -> int:
    data = load_data()
    idset = set(ids)
    before = len(data["tasks"])
    data["tasks"] = [t for t in data["tasks"] if t["id"] not in idset]
    after = len(data["tasks"])
    save_data(data)
    return before - after


def edit_task(id_: int, title: Optional[str], due: Optional[str], clear_due: bool, undone: bool) -> Optional[Task]:
    data = load_data()
    for raw in data["tasks"]:
        if int(raw["id"]) == id_:
            if title is not None:
                raw["title"] = title
            if clear_due:
                raw["due"] = None
            elif due is not None:
                raw["due"] = due
            if undone and raw.get("completed"):
                raw["completed"] = False
                raw["completed_at"] = None
            save_data(data)
            return Task.from_dict(raw)
    return None


def clear_tasks(mode: str) -> int:
    data = load_data()
    before = len(data["tasks"])
    if mode == "done":
        data["tasks"] = [t for t in data["tasks"] if not t.get("completed", False)]
    elif mode == "all":
        data["tasks"] = []
        data["next_id"] = 1
    else:
        raise ValueError("Unknown clear mode")
    after = len(data["tasks"])
    save_data(data)
    return before - after


def stats() -> Dict[str, int]:
    data = load_data()
    total = len(data["tasks"])
    done = sum(1 for t in data["tasks"] if t.get("completed", False))
    pending = total - done
    overdue = 0
    today = date.today().isoformat()
    for t in data["tasks"]:
        if not t.get("completed", False) and t.get("due") and t["due"] < today:
            overdue += 1
    return {"total": total, "pending": pending, "done": done, "overdue": overdue}


def format_tasks(tasks: List[Task]) -> str:
    if not tasks:
        return "(no tasks)"

    # Determine column widths
    headers = ["ID", "Title", "Due", "Status", "Created"]
    rows = []
    for t in tasks:
        status = "done" if t.completed else "pending"
        rows.append([
            str(t.id),
            t.title,
            t.due or "-",
            status,
            t.created_at.replace("T", " ").rstrip("Z"),
        ])

    widths = [len(h) for h in headers]
    for r in rows:
        for i, cell in enumerate(r):
            widths[i] = max(widths[i], len(cell))

    def fmt_row(vals):
        return "  ".join(val.ljust(widths[i]) for i, val in enumerate(vals))

    lines = [fmt_row(headers), fmt_row(["-" * w for w in widths])]
    lines += [fmt_row(r) for r in rows]
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Simple ToDo CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    pa = sub.add_parser("add", help="Add a new task")
    pa.add_argument("title", help="Task title")
    pa.add_argument("--due", type=parse_date, help="Due date YYYY-MM-DD")

    pl = sub.add_parser("list", help="List tasks")
    g = pl.add_mutually_exclusive_group()
    g.add_argument("--all", action="store_true", help="Show all tasks")
    g.add_argument("--done", action="store_true", help="Show completed tasks")
    g.add_argument("--pending", action="store_true", help="Show pending tasks (default)")

    pd = sub.add_parser("done", help="Mark task(s) as done")
    pd.add_argument("ids", nargs="+", type=int, help="Task id(s)")

    pdel = sub.add_parser("delete", help="Delete task(s)")
    pdel.add_argument("ids", nargs="+", type=int, help="Task id(s)")

    pe = sub.add_parser("edit", help="Edit a task")
    pe.add_argument("id", type=int, help="Task id")
    pe.add_argument("--title", help="New title")
    due_group = pe.add_mutually_exclusive_group()
    due_group.add_argument("--due", type=parse_date, help="New due date YYYY-MM-DD")
    due_group.add_argument("--clear-due", action="store_true", help="Clear due date")
    pe.add_argument("--undone", action="store_true", help="Mark task back to pending")

    pc = sub.add_parser("clear", help="Clear tasks")
    cg = pc.add_mutually_exclusive_group(required=True)
    cg.add_argument("--done", action="store_true", help="Remove completed tasks")
    cg.add_argument("--all", action="store_true", help="Remove all tasks and reset IDs")

    ps = sub.add_parser("stats", help="Show simple stats")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.cmd == "add":
        t = add_task(args.title, args.due)
        print(f"Added #{t.id}: {t.title}")
        return 0

    if args.cmd == "list":
        kind = "pending"
        if args.all:
            kind = "all"
        elif args.done:
            kind = "done"
        elif args.pending:
            kind = "pending"
        tasks = list_tasks(kind)
        print(format_tasks(tasks))
        return 0

    if args.cmd == "done":
        updated = mark_done(args.ids)
        if not updated:
            print("No tasks updated. Check IDs or status.")
        else:
            print("Marked done:", ", ".join(f"#{t.id}" for t in updated))
        return 0

    if args.cmd == "delete":
        n = delete_tasks(args.ids)
        print(f"Deleted {n} task(s)")
        return 0

    if args.cmd == "edit":
        t = edit_task(args.id, args.title, args.due, args.clear_due, args.undone)
        if t is None:
            print(f"Task #{args.id} not found")
            return 1
        print(f"Updated #{t.id}")
        return 0

    if args.cmd == "clear":
        mode = "done" if args.done else "all"
        n = clear_tasks(mode)
        print(f"Removed {n} task(s)")
        return 0

    if args.cmd == "stats":
        s = stats()
        print(
            f"Total: {s['total']} | Pending: {s['pending']} | Done: {s['done']} | Overdue: {s['overdue']}"
        )
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

