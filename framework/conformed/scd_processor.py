"""Conformed layer SCD and append-only merge logic."""

from __future__ import annotations

from datetime import UTC, datetime


OPEN_ENDED_TS = "9999-12-31T00:00:00+00:00"


def merge_scd2_dimension(
    *,
    current_rows: list[dict[str, str]],
    staging_rows: list[dict[str, str]],
    business_key: str,
    surrogate_key: str,
    run_id: str,
    batch_timestamp: str,
    missing_record_action: str = "soft_delete",
) -> list[dict[str, str]]:
    """Merge latest resolved staging rows into an SCD Type 2 dimension."""

    output = [dict(row) for row in current_rows]
    latest_rows = _latest_resolved_rows(staging_rows, business_key)
    current_by_key = {
        row[business_key]: row
        for row in output
        if _is_true(row.get("is_current", "false"))
    }

    next_sk = _next_surrogate_key(output, surrogate_key)
    for key, source in latest_rows.items():
        current = current_by_key.get(key)
        if current is None:
            output.append(
                _new_scd2_row(
                    source=source,
                    business_key=business_key,
                    surrogate_key=surrogate_key,
                    surrogate_value=next_sk,
                    run_id=run_id,
                )
            )
            next_sk += 1
            continue

        if current.get("source_record_hash") == source["_record_hash"]:
            continue

        _close_row(
            current,
            effective_to=source.get("effective_at") or batch_timestamp,
            run_id=run_id,
            deleted_flag="false",
        )
        output.append(
            _new_scd2_row(
                source=source,
                business_key=business_key,
                surrogate_key=surrogate_key,
                surrogate_value=next_sk,
                run_id=run_id,
            )
        )
        next_sk += 1

    if missing_record_action == "soft_delete":
        source_keys = set(latest_rows)
        for current in list(current_by_key.values()):
            if current[business_key] not in source_keys:
                _close_row(
                    current,
                    effective_to=batch_timestamp,
                    run_id=run_id,
                    deleted_flag="true",
                )
    elif missing_record_action != "ignore":
        raise ValueError(f"Unsupported missing_record_action: {missing_record_action}")

    return output


def merge_append_only_events(
    *,
    current_rows: list[dict[str, str]],
    staging_rows: list[dict[str, str]],
    event_key: str,
    run_id: str,
) -> list[dict[str, str]]:
    """Merge append-only event rows by event id without expiring missing records."""

    output = [dict(row) for row in current_rows]
    existing_keys = {row[event_key] for row in output}
    for source in staging_rows:
        if source.get("_is_exact_duplicate") == "true":
            continue
        key = source[event_key]
        if key in existing_keys:
            continue
        output.append(
            {
                **_business_payload(source),
                "event_business_key": key,
                "source_system_id": source.get("_source_system_id", ""),
                "source_dataset_id": source.get("_source_dataset_id", ""),
                "batch_date": source.get("_batch_date", ""),
                "source_record_hash": source.get("_record_hash", ""),
                "created_run_id": run_id,
                "created_at": _now(),
            }
        )
        existing_keys.add(key)
    return output


def _latest_resolved_rows(staging_rows: list[dict[str, str]], business_key: str) -> dict[str, dict[str, str]]:
    return {
        row[business_key]: row
        for row in staging_rows
        if row.get("_is_latest_for_business_key") == "true"
        and row.get("_latest_resolution_status") == "resolved"
        and row.get("_is_exact_duplicate") != "true"
        and row.get("_delta_action", "UPSERT") != "DELETE"
    }


def _new_scd2_row(
    *,
    source: dict[str, str],
    business_key: str,
    surrogate_key: str,
    surrogate_value: int,
    run_id: str,
) -> dict[str, str]:
    return {
        **_business_payload(source),
        surrogate_key: str(surrogate_value),
        "business_key": source[business_key],
        "effective_from": source.get("effective_at", ""),
        "effective_to": OPEN_ENDED_TS,
        "is_current": "true",
        "deleted_flag": "false",
        "source_system_id": source.get("_source_system_id", ""),
        "source_dataset_id": source.get("_source_dataset_id", ""),
        "source_effective_at": source.get("effective_at", ""),
        "source_updated_at": source.get("updated_at", ""),
        "source_record_hash": source.get("_record_hash", ""),
        "created_run_id": run_id,
        "updated_run_id": run_id,
        "created_at": _now(),
        "updated_at": _now(),
    }


def _close_row(row: dict[str, str], *, effective_to: str, run_id: str, deleted_flag: str) -> None:
    row["effective_to"] = effective_to
    row["is_current"] = "false"
    row["deleted_flag"] = deleted_flag
    row["updated_run_id"] = run_id
    row["updated_at"] = _now()


def _business_payload(source: dict[str, str]) -> dict[str, str]:
    return {key: value for key, value in source.items() if not key.startswith("_")}


def _next_surrogate_key(rows: list[dict[str, str]], surrogate_key: str) -> int:
    values = [int(row[surrogate_key]) for row in rows if row.get(surrogate_key, "").isdigit()]
    return max(values, default=0) + 1


def _is_true(value: str) -> bool:
    return value.lower() == "true"


def _now() -> str:
    return datetime.now(UTC).isoformat()
