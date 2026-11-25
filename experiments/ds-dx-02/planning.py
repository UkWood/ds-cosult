"""Server-side validation and non-executable semantic recommendations."""
import re

from protocol import Stop

NAME = re.compile(r"[a-z][a-z0-9-]{0,47}\Z")
ADVISORY_FIELDS = {"topics", "priorities", "relationships", "applicability", "uncertainties",
                   "illustrations", "follow_up"}


def advisory_status(obj, finish):
    """Advisory is free-form engineering context; no executable fields are accepted."""
    if finish == "length":
        return "truncated", []
    if finish != "stop" or not isinstance(obj, dict):
        return "unavailable", []
    value = obj.get("advisory")
    if value is None and not ({"tasks", "gaps"} & obj.keys()):
        return "absent", []
    if ({"tasks", "gaps"} & obj.keys() or not isinstance(value, dict)
            or not value or not value.keys() <= ADVISORY_FIELDS
            or any(not isinstance(items, list) or not 1 <= len(items) <= 12
                   or any(not isinstance(item, str) or not 1 <= len(item.strip()) <= 240 for item in items)
                   for items in value.values())):
        return "unsupported_shape", []
    # Only these labels leave the private response as candidates for local grouping.
    return "accepted", [item.casefold().strip() for item in value.get("topics", [])]


def validate(plan, scope, images, limit):
    try:
        tasks, gaps = plan["tasks"], plan["gaps"]
        if set(plan) != {"tasks", "gaps"}:
            raise ValueError
        if not isinstance(tasks, list) or not isinstance(gaps, list) or len(tasks) > limit:
            raise ValueError
        pending = {}
        covered = set()
        visual = set()
        for task in tasks:
            id_ = task["id"]
            if set(task) != {"id", "topic", "kind", "scope", "images", "deps", "instruction", "limit"}:
                raise ValueError
            if (not NAME.fullmatch(id_) or not NAME.fullmatch(task["topic"]) or id_ in pending
                    or task["kind"] not in {"extract", "vision", "fusion"}
                    or type(task["limit"]) is not int or not 512 <= task["limit"] <= 8192
                    or not isinstance(task["instruction"], str) or not 1 <= len(task["instruction"]) <= 4000
                    or not isinstance(task["deps"], list) or not isinstance(task["images"], list)
                    or len(task["images"]) > 3 or not task["scope"]):
                raise ValueError
            for source, locations in task["scope"].items():
                if not isinstance(locations, list) or not locations or not set(locations) <= scope[source]:
                    raise ValueError
                if any(type(n) is not int for n in locations):
                    raise ValueError
                covered.update((source, n) for n in locations)
            if len(set(task["deps"])) != len(task["deps"]) or len(set(task["images"])) != len(task["images"]):
                raise ValueError
            for name in task["images"]:
                source, number = images[name]
                if number not in task["scope"].get(source, []) or task["kind"] != "vision":
                    raise ValueError
                visual.add(name)
            if task["kind"] == "vision" and not task["images"]:
                raise ValueError
            pending[id_] = task
        for gap in gaps:
            source, locations, reason = gap["source"], gap["locations"], gap["reason"]
            if (set(gap) != {"source", "locations", "reason"} or not isinstance(reason, str)
                    or not 1 <= len(reason.strip()) <= 4000 or not isinstance(locations, list) or not locations
                    or any(type(n) is not int for n in locations) or not set(locations) <= scope[source]):
                raise ValueError
        if covered != {(source, n) for source, numbers in scope.items() for n in numbers} or visual != set(images):
            raise ValueError
        ordered = []
        done = set()
        while pending:
            ready = [task for task in pending.values() if set(task["deps"]) <= done]
            if not ready:
                raise ValueError
            for task in ready:
                ordered.append(task)
                done.add(task["id"])
                del pending[task["id"]]
        return ordered
    except (ValueError, KeyError, AttributeError, TypeError):
        raise Stop("Invalid task graph: locator, budget, dependency or coverage violation") from None
