"""Convert legacy tags once at a boundary; scheduling uses stable IDs and a DAG."""

from __future__ import annotations

from src.orchestration.heuristics._structural import (
    TAG_PATTERN,
    complexity_score,
    tag_map,
    safe_structural_shuffle,
)


def normalize_tasks(tasks: list[dict]) -> list[dict]:
    tasks = [
        dict(task, id=task.get("id", f"task-{i + 1}")) for i, task in enumerate(tasks)
    ]
    if tasks and all("depends_on" not in task for task in tasks):
        tasks = safe_structural_shuffle(tasks, lambda _task: 0)
    result = []
    for index, original in enumerate(tasks):
        task = dict(original)
        tags = tag_map(task)
        task.setdefault(
            "complexity", {1: "low", 2: "medium", 3: "high"}[complexity_score(task)]
        )
        if "depends_on" not in task:
            # Legacy groups execute in first-appearance order. Within a group,
            # only an explicit contiguous shuffle run can be independent.
            task["depends_on"] = []
            group = tags.get("group", "default")
            for previous in result:
                prev_tags = tag_map(previous)
                same_run = (
                    tags.get("shuffle") in {"yes", "true", "1"}
                    and prev_tags.get("shuffle") in {"yes", "true", "1"}
                    and not (tags.get("seq") or prev_tags.get("seq"))
                    and prev_tags.get("group", "default") == group
                )
                if not same_run:
                    task["depends_on"].append(previous["id"])
        result.append(task)
    validate_dag(result)
    return result


def validate_dag(tasks: list[dict]) -> None:
    ids = [task["id"] for task in tasks]
    if len(set(ids)) != len(ids):
        raise ValueError("Task IDs must be unique")
    pending = {task["id"]: set(task.get("depends_on", [])) for task in tasks}
    if any(not dependencies.issubset(ids) for dependencies in pending.values()):
        raise ValueError("A task dependency does not exist")
    done: set[str] = set()
    while pending:
        ready = {key for key, deps in pending.items() if deps <= done}
        if not ready:
            raise ValueError("Task dependencies contain a cycle")
        done.update(ready)
        pending = {key: deps for key, deps in pending.items() if key not in ready}


def clean_description(value: str) -> str:
    return TAG_PATTERN.sub("", value).strip()
