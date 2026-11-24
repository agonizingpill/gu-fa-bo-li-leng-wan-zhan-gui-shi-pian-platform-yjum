"""母板分组、合并冲突判定和拟合快照的纯函数工具。"""
from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any, Iterable

TRAIN = "train"
HOLDOUT = "holdout"
EXCLUDED = "excluded"
MISSING_PLATE = "missing_plate"
MIXED_SIDES = "mixed_sides"
SIDE_CONFLICT = "cross_side_merge"

SIDE_LABELS = {
    TRAIN: "训练",
    HOLDOUT: "留验",
    EXCLUDED: "退出后续拟合",
    "quarantined": "隔离",
}

REASON_LABELS = {
    MISSING_PLATE: "未登记母板号，旧试片先隔离",
    "plate_missing": "未登记母板号，旧试片先隔离",
    MIXED_SIDES: "同块母板的试片原分属训练和留验，整板退出后续拟合",
    SIDE_CONFLICT: "合并的两个母板号原分属训练与留验，整板退出后续拟合",
    "side_conflict": "两个母板号原分属训练与留验，整板退出后续拟合",
    "merged_across_sides": "两个母板号原分属训练与留验，整板退出后续拟合",
    "not_witnessed": "试片尚未经复核员见证",
    "missing_side": "母板尚未取得固定分组",
    "excluded": "该母板已被排除",
}


def clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def code_value(value: Any) -> str | None:
    if isinstance(value, dict):
        for key in ("code", "plate", "plate_code", "value", "id", "number"):
            parsed = clean(value.get(key))
            if parsed:
                return parsed
        return None
    return clean(value)


def model_data(data: Any) -> dict[str, Any]:
    if data is None:
        return {}
    if isinstance(data, dict):
        return dict(data)
    if hasattr(data, "model_dump"):
        try:
            return data.model_dump()
        except Exception:
            pass
    return {key: getattr(data, key) for key in dir(data) if not key.startswith("_")}


def first_value(data: Any, names: Iterable[str]) -> str | None:
    payload = model_data(data)
    for name in names:
        if name in payload:
            value = clean(payload[name])
            if value:
                return value
    extra = payload.get("model_extra")
    if isinstance(extra, dict):
        for name in names:
            value = clean(extra.get(name))
            if value:
                return value
    return None


def plate_from_witness(data: Any) -> str | None:
    return first_value(data, (
        "plate", "plate_code", "plate_no", "plate_number", "master_plate",
        "master_plate_code", "master_plate_number", "mother_plate",
        "mother_plate_code", "parent_plate", "parent_plate_code",
        "board", "board_code", "mother_board",
    ))


def pair_from_merge(data: Any) -> tuple[str, str] | None:
    payload = model_data(data)

    direct_pairs = [
        ("first", "second"), ("a", "b"), ("one", "two"), ("left", "right"),
        ("source", "target"), ("from", "to"), ("from_", "to"),
        ("code", "into"), ("plate", "into"), ("old_code", "into_code"),
        ("old_code", "new_code"), ("old_plate", "new_plate"),
        ("duplicate_code", "canonical_code"),
        ("duplicate", "canonical"), ("old", "new"),
        ("from_plate", "to_plate"), ("source_plate", "target_plate"),
        ("plate_a", "plate_b"), ("plate1", "plate2"),
        ("code_a", "code_b"), ("first_code", "second_code"),
        ("merge_from", "merge_into"),
        ("source_code", "target_code"), ("from_code", "to_code"),
        ("old_code", "new_code"), ("duplicate_code", "canonical_code"),
    ]
    for left_name, right_name in direct_pairs:
        left = code_value(payload.get(left_name))
        right = code_value(payload.get(right_name))
        if left and right:
            return left, right

    for list_name in ("codes", "plates", "plate_codes", "numbers", "plate_numbers", "ids"):
        values = payload.get(list_name)
        if isinstance(values, (list, tuple)) and len(values) >= 2:
            left, right = code_value(values[0]), code_value(values[1])
            if left and right:
                return left, right

    # 最后兜底：接受任意 *_a/*_b、*_1/*_2、first_*/second_* 形式。
    flat: dict[str, str] = {}

    def remember(key: Any, value: Any) -> None:
        if not isinstance(key, str):
            return
        parsed = code_value(value)
        if parsed:
            snake = re.sub(r'(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Za-z])(?=[0-9])', '_', key).lower()
            flat[snake] = parsed
            flat[key.lower()] = parsed

    for key, value in payload.items():
        remember(key, value)
    extra = payload.get("model_extra")
    if isinstance(extra, dict):
        for key, value in extra.items():
            remember(key, value)

    for key, value in list(flat.items()):
        if key.endswith("_a") and key[:-2] + "_b" in flat:
            return value, flat[key[:-2] + "_b"]
        if key.endswith("_1") and key[:-2] + "_2" in flat:
            return value, flat[key[:-2] + "_2"]

    first_key = next((key for key in flat if "first" in key or key in ("from", "source", "old", "duplicate")), None)
    second_key = next((key for key in flat if "second" in key or key in ("to", "target", "new", "canonical")), None)
    if first_key and second_key and first_key != second_key:
        return flat[first_key], flat[second_key]

    for prefix in ("plate", "plate_no", "code", "coupon", "master_plate", "mother_plate",
                   "parent_plate", "number", "id", "source", "target"):
        for left_tpl, right_tpl in (
            (prefix + "_a", prefix + "_b"),
            (prefix + "_1", prefix + "_2"),
            ("first_" + prefix, "second_" + prefix),
        ):
            if left_tpl in flat and right_tpl in flat:
                return flat[left_tpl], flat[right_tpl]
    return None


def label_for_side(side: str | None) -> str:
    return SIDE_LABELS.get(side or "", "未分组")


def detail_for_reason(reason: str | None) -> str | None:
    if not reason:
        return None
    return REASON_LABELS.get(reason, reason)


def _canonical_code(code: str | None, plates_by_code: dict[str, dict[str, Any]],
                    seen: set[str] | None = None) -> str | None:
    code = clean(code)
    if not code:
        return None
    seen = set() if seen is None else seen
    if code in seen:
        return code
    seen.add(code)
    row = plates_by_code.get(code)
    if not row:
        return code
    nxt = clean(row.get("canonical_code") or row.get("merged_into"))
    if not nxt or nxt == code:
        return code
    return _canonical_code(nxt, plates_by_code, seen)


def build_plate_report(
    coupons: Iterable[dict[str, Any]],
    plates: Iterable[dict[str, Any]] | None = None,
    *,
    revision: int | None = None,
    at: datetime | str | None = None,
    include_unlocked: bool = False,
) -> dict[str, Any]:
    coupon_rows = [dict(row) for row in coupons]
    plate_rows = [dict(row) for row in (plates or [])]
    plates_by_code = {clean(row.get("code")): row for row in plate_rows if clean(row.get("code"))}

    groups: dict[str, dict[str, Any]] = {}
    assignments: list[dict[str, Any]] = []

    def group_for(key: str) -> dict[str, Any]:
        if key not in groups:
            groups[key] = {
                "plate": None if key == "__missing__" else key,
                "code": None if key == "__missing__" else key,
                "canonical": None if key == "__missing__" else key,
                "codes": set(),
                "aliases": set(),
                "coupons": [],
                "coupon_codes": [],
                "train": [],
                "holdout": [],
                "train_coupons": [],
                "holdout_coupons": [],
                "original_sides": set(),
                "reasons": set(),
            }
        return groups[key]

    for coupon in sorted(coupon_rows, key=lambda row: clean(row.get("code")) or ""):
        code = clean(coupon.get("code"))
        if not code:
            continue
        locked = bool(coupon.get("locked"))
        if not locked and not include_unlocked:
            continue

        entered_plate = clean(coupon.get("plate_original")) or clean(coupon.get("plate"))
        current_plate = clean(coupon.get("plate")) or entered_plate
        canonical = _canonical_code(current_plate, plates_by_code)
        key = canonical or "__missing__"
        group = group_for(key)

        for alias in (entered_plate, current_plate, canonical):
            if alias and key != "__missing__":
                group["codes"].add(alias)
                group["aliases"].add(alias)

        reason = clean(coupon.get("exclude_reason") or coupon.get("exclusion_reason"))
        blocked = bool(coupon.get("excluded") or coupon.get("quarantined"))
        if blocked:
            group["reasons"].add(reason or EXCLUDED)

        plate_row = plates_by_code.get(entered_plate or "") or plates_by_code.get(current_plate or "")
        canonical_row = plates_by_code.get(canonical or "")
        for row in (plate_row, canonical_row):
            if row:
                row_reason = clean(row.get("reason"))
                if row_reason and (row.get("state") == "excluded" or row.get("side") == EXCLUDED):
                    group["reasons"].add(row_reason)
                for alias_name in ("code", "canonical_code", "merged_into"):
                    alias = clean(row.get(alias_name))
                    if alias and key != "__missing__":
                        group["codes"].add(alias)
                        group["aliases"].add(alias)

        effective_side = clean(coupon.get("side"))
        original_side = clean(coupon.get("original_side") or coupon.get("assigned_side"))
        if original_side not in (TRAIN, HOLDOUT):
            original_side = effective_side if effective_side in (TRAIN, HOLDOUT) else None
        if plate_row and original_side is None:
            candidate = clean(plate_row.get("original_side"))
            if candidate in (TRAIN, HOLDOUT):
                original_side = candidate
        if canonical_row and original_side is None:
            candidate = clean(canonical_row.get("original_side"))
            if candidate in (TRAIN, HOLDOUT):
                original_side = candidate

        if not current_plate:
            group["reasons"].add(MISSING_PLATE)
        elif not locked:
            group["reasons"].add("not_witnessed")
        elif original_side is None:
            group["reasons"].add("missing_side")
        elif original_side in (TRAIN, HOLDOUT):
            group["original_sides"].add(original_side)
            group[original_side].append(code)
            group[f"{original_side}_coupons"].append(code)

        group["coupons"].append(code)
        group["coupon_codes"].append(code)

        assignment_side = original_side
        assignment_excluded = bool(blocked or group["reasons"])
        assignments.append({
            "coupon": code,
            "code": code,
            "plate": canonical,
            "plate_code": entered_plate,
            "canonical_plate": canonical,
            "side": EXCLUDED if assignment_excluded else assignment_side,
            "original_side": original_side,
            "split": EXCLUDED if assignment_excluded else assignment_side,
            "destination": EXCLUDED if assignment_excluded else assignment_side,
            "label": label_for_side(EXCLUDED if assignment_excluded else assignment_side),
            "excluded": assignment_excluded,
            "quarantined": assignment_excluded,
            "reason": sorted(group["reasons"])[0] if group["reasons"] else None,
            "reasons": sorted(group["reasons"]),
            "detail": detail_for_reason(sorted(group["reasons"])[0]) if group["reasons"] else None,
            "locked": locked,
        })

    plate_items: list[dict[str, Any]] = []
    for key, group in sorted(groups.items(), key=lambda item: (item[0] == "__missing__", item[0])):
        reasons = set(group["reasons"])
        original_sides = group["original_sides"]
        if len(original_sides) > 1:
            reasons.add(MIXED_SIDES)

        excluded = bool(reasons)
        if excluded:
            side = EXCLUDED
            reason_code = SIDE_CONFLICT if SIDE_CONFLICT in reasons else (
                MIXED_SIDES if MIXED_SIDES in reasons else sorted(reasons)[0]
            )
        else:
            side = next(iter(original_sides)) if len(original_sides) == 1 else EXCLUDED
            if side == EXCLUDED:
                reason_code = "missing_side"
                reasons.add(reason_code)
                excluded = True
            else:
                reason_code = None

        codes = sorted(group["codes"])
        item = {
            "plate": group["plate"],
            "code": group["code"] or "UNREGISTERED",
            "canonical": group["canonical"],
            "canonical_code": group["canonical"],
            "codes": codes,
            "aliases": sorted(group["aliases"]),
            "numbers": codes,
            "coupons": group["coupons"],
            "coupon_codes": group["coupon_codes"],
            "train": sorted(group["train"]),
            "holdout": sorted(group["holdout"]),
            "train_coupons": sorted(group["train_coupons"]),
            "holdout_coupons": sorted(group["holdout_coupons"]),
            "train_count": len(group["train"]),
            "holdout_count": len(group["holdout"]),
            "coupon_count": len(group["coupons"]),
            "original_sides": sorted(original_sides),
            "side": side,
            "split": side,
            "assignment": side,
            "destination": side,
            "destination_label": label_for_side(side),
            "side_label": label_for_side(side),
            "label": label_for_side(side),
            "state": EXCLUDED if excluded else "active",
            "status": EXCLUDED if excluded else "active",
            "active": not excluded,
            "excluded": excluded,
            "quarantined": excluded,
            "isolated": excluded,
            "blocked": excluded,
            "ineligible": excluded,
            "reason": reason_code,
            "reason_code": reason_code,
            "exclusion_reason": reason_code,
            "quarantine_reason": reason_code,
            "reasons": sorted(reasons),
            "detail": detail_for_reason(reason_code),
            "explanation": detail_for_reason(reason_code),
        }
        plate_items.append(item)

    active = [item for item in plate_items if not item["excluded"]]
    by_plate = {item["code"]: item for item in plate_items}
    report = {
        "plates": plate_items,
        "groups": plate_items,
        "allocations": plate_items,
        "plate_sides": plate_items,
        "plate_allocations": plate_items,
        "lineage": plate_items,
        "trace": plate_items,
        "by_plate": by_plate,
        "plate_map": by_plate,
        "assignments": assignments,
        "revision": revision,
        "snapshot_at": (at or datetime.now(timezone.utc)).isoformat() if not isinstance(at, str) else at,
        "counts": {
            "plates": len(plate_items),
            "active_plates": len(active),
            "train_plates": sum(item["side"] == TRAIN for item in active),
            "holdout_plates": sum(item["side"] == HOLDOUT for item in active),
            "excluded_plates": sum(item["excluded"] for item in plate_items),
        },
    }
    return report


def report_groups(data: Any) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        return []
    for key in ("plates", "groups", "allocation", "allocations", "plate_report"):
        value = data.get(key)
        if isinstance(value, dict):
            groups = value.get("plates") or value.get("groups")
            if isinstance(groups, list):
                return groups
        if isinstance(value, list):
            return value
    return []
