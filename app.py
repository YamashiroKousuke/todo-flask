from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

from flask import Flask, render_template, request, redirect, url_for, flash

# Reuse storage and logic from the CLI module
from todo import (
    add_task,
    list_tasks,
    edit_task,
    delete_tasks,
    mark_done,
    stats as stats_fn,
    load_data,
    Task,
)


app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-secret-key"  # replace in production


def parse_due(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    try:
        # Expect YYYY-MM-DD
        return date.fromisoformat(value).isoformat()
    except Exception:
        return None


def get_task_by_id(task_id: int) -> Optional[Task]:
    data = load_data()
    for raw in data["tasks"]:
        if int(raw["id"]) == int(task_id):
            return Task.from_dict(raw)
    return None


@app.context_processor
def inject_globals():
    # Expose stats to all templates (base.html expects it)
    return {"stats": stats_fn()}


@app.route("/")
def index():
    kind = request.args.get("filter", "pending")
    if kind not in ("pending", "all", "done"):
        kind = "pending"
    tasks = list_tasks(kind)
    s = stats_fn()
    return render_template(
        "index.html",
        kind=kind,
        tasks=tasks,
        stats=s,
        today=date.today().isoformat(),
    )


@app.post("/add")
def add():
    title = (request.form.get("title") or "").strip()
    due_raw = (request.form.get("due") or "").strip()
    due = parse_due(due_raw)
    if not title:
        flash("タイトルを入力してください", "warning")
        return redirect(url_for("index", filter=request.args.get("filter", "pending")))
    if due_raw and not due:
        flash("期日は YYYY-MM-DD 形式で入力してください", "warning")
        return redirect(url_for("index", filter=request.args.get("filter", "pending")))
    t = add_task(title, due)
    flash(f"追加しました: #{t.id} {t.title}", "success")
    return redirect(url_for("index", filter=request.args.get("filter", "pending")))


@app.post("/toggle/<int:task_id>")
def toggle(task_id: int):
    act = request.args.get("act", "toggle")
    if act == "done":
        mark_done([task_id])
    elif act == "undone":
        edit_task(task_id, None, None, False, True)
    else:
        # If unknown, try to infer
        task = get_task_by_id(task_id)
        if task and task.completed:
            edit_task(task_id, None, None, False, True)
        else:
            mark_done([task_id])
    return redirect(url_for("index", filter=request.args.get("filter", "pending")))


@app.post("/delete/<int:task_id>")
def delete(task_id: int):
    n = delete_tasks([task_id])
    if n:
        flash(f"削除しました: #{task_id}", "info")
    else:
        flash(f"見つかりませんでした: #{task_id}", "warning")
    return redirect(url_for("index", filter=request.args.get("filter", "pending")))


@app.route("/edit/<int:task_id>", methods=["GET", "POST"])
def edit(task_id: int):
    task = get_task_by_id(task_id)
    if not task:
        flash(f"見つかりませんでした: #{task_id}", "warning")
        return redirect(url_for("index"))

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        due_raw = (request.form.get("due") or "").strip()
        clear_due = request.form.get("clear_due") == "on"
        undone = request.form.get("undone") == "on"

        if not title:
            flash("タイトルを入力してください", "warning")
            return redirect(url_for("edit", task_id=task_id))

        due = parse_due(due_raw)
        if due_raw and not due and not clear_due:
            flash("期日は YYYY-MM-DD 形式で入力してください", "warning")
            return redirect(url_for("edit", task_id=task_id))

        updated = edit_task(task_id, title, due, clear_due, undone)
        if updated:
            flash(f"更新しました: #{updated.id}", "success")
        else:
            flash("更新に失敗しました", "danger")
        return redirect(url_for("index", filter=request.args.get("filter", "pending")))

    return render_template("edit.html", task=task)


if __name__ == "__main__":
    # Start dev server: python app.py
    app.run(debug=True)
