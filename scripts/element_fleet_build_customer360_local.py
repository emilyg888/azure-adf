"""Build a local Customer 360 identity-resolution snapshot from staged CSVs.

This is a local verification harness for the Snowflake-first identity design.
It uses the same two-day staged outputs produced by `element_fleet_pipeline_driver.py`
and writes CSV artifacts that mirror the Snowflake IDENTITY, GOLDEN, GOLD, and
SEMANTIC layers.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from framework.conformed.scd_processor import merge_scd2_dimension


DEFAULT_DAY1_ROOT = Path(".local/element_fleet_full_20260525")
DEFAULT_DAY2_ROOT = Path(".local/element_fleet_full_20260526")
DEFAULT_OUTPUT_ROOT = Path(".local/customer360_identity")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build local Customer 360 identity artifacts.")
    parser.add_argument("--day1-root", type=Path, default=DEFAULT_DAY1_ROOT)
    parser.add_argument("--day2-root", type=Path, default=DEFAULT_DAY2_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()

    day1 = _load_day(args.day1_root, "2026-05-25")
    day2 = _load_day(args.day2_root, "2026-05-26")

    dim_client = _merge_dimension(
        day1_rows=day1["clients"],
        day2_rows=day2["clients"],
        business_key="client_id",
        surrogate_key="client_sk",
    )
    dim_vehicle = _merge_dimension(
        day1_rows=day1["vehicles"],
        day2_rows=day2["vehicles"],
        business_key="vehicle_id",
        surrogate_key="vehicle_sk",
    )
    current_clients = [row for row in dim_client if row["is_current"] == "true" and row["deleted_flag"] == "false"]
    current_vehicles = [row for row in dim_vehicle if row["is_current"] == "true" and row["deleted_flag"] == "false"]

    std_customer = [_std_customer(row) for row in current_clients]
    std_vehicle = [_std_vehicle(row) for row in current_vehicles]
    golden_customer = [_golden_customer(row) for row in std_customer]
    customer_by_source = {row["primary_source_customer_id"]: row for row in golden_customer}
    golden_vehicle = [_golden_vehicle(row, customer_by_source) for row in std_vehicle]
    vehicle_by_source = {row["vehicle_id"]: row for row in golden_vehicle}

    xref_customer = [
        {
            "golden_customer_id": row["golden_customer_id"],
            "source_system": row["primary_source_system_id"],
            "source_customer_id": row["primary_source_customer_id"],
            "match_confidence": row["identity_resolution_confidence"],
            "match_method": row["match_method"],
            "match_reason_code": "same_source_customer_id",
        }
        for row in golden_customer
    ]
    rel_customer_vehicle = [
        {
            "golden_customer_id": row["golden_customer_id"],
            "golden_vehicle_id": row["golden_vehicle_id"],
            "relationship_status": "active" if row["vehicle_status"].lower() == "active" else "inactive",
        }
        for row in golden_vehicle
        if row["golden_customer_id"]
    ]
    std_device = _std_device(std_vehicle, day2["telematics_daily"])
    device_xref = _xref_device(std_device, vehicle_by_source)
    account_xref = _xref_account(day2["finance_billing_invoices"], customer_by_source)
    fuel_card_xref = _xref_fuel_card(day2["fuel_cards"], customer_by_source, vehicle_by_source)
    review_queue = _review_queue(std_customer, std_vehicle)
    customer360 = _customer360_mart(
        golden_customer=golden_customer,
        rel_customer_vehicle=rel_customer_vehicle,
        leasing=day2["leasing_contracts"],
        fuel=day2["fuel_card_transactions"],
        maintenance=day2["maintenance_work_orders"],
        claims=day2["insurance_claims"],
        portal=day2["crm_client_portal_events"],
        ev=day2["ev_charging_sessions"],
    )

    outputs = {
        "conformed_dim_client": dim_client,
        "conformed_dim_vehicle": dim_vehicle,
        "identity_std_customer": std_customer,
        "identity_std_vehicle": std_vehicle,
        "identity_std_device": std_device,
        "golden_golden_customer": golden_customer,
        "golden_golden_vehicle": golden_vehicle,
        "golden_xref_customer_source": xref_customer,
        "golden_xref_account_source": account_xref,
        "golden_xref_fuel_card_source": fuel_card_xref,
        "golden_xref_device_source": device_xref,
        "golden_rel_customer_vehicle": rel_customer_vehicle,
        "governance_identity_review_queue": review_queue,
        "gold_customer_360_mart": customer360,
        "semantic_customer_360": [row for row in customer360 if row["data_quality_status"] == "certified"],
    }
    args.output_root.mkdir(parents=True, exist_ok=True)
    for name, rows in outputs.items():
        _write_csv(args.output_root / f"{name}.csv", rows)

    print(f"Wrote {len(outputs)} Customer 360 artifacts to {args.output_root}")
    print(f"Current clients: {len(current_clients)}")
    print(f"Current vehicles: {len(current_vehicles)}")
    print(f"Semantic Customer 360 rows: {len(outputs['semantic_customer_360'])}")


def _load_day(root: Path, batch_date: str) -> dict[str, list[dict[str, str]]]:
    datasets = [
        "clients",
        "vehicles",
        "leasing_contracts",
        "fuel_cards",
        "fuel_card_transactions",
        "telematics_daily",
        "maintenance_work_orders",
        "insurance_claims",
        "finance_billing_invoices",
        "crm_client_portal_events",
        "ev_charging_sessions",
    ]
    return {
        dataset: _read_csv(root / "staging" / "domain=fleet_management" / f"dataset={dataset}" / f"batch_date={batch_date}" / "part-00000.csv")
        for dataset in datasets
    }


def _merge_dimension(
    *,
    day1_rows: list[dict[str, str]],
    day2_rows: list[dict[str, str]],
    business_key: str,
    surrogate_key: str,
) -> list[dict[str, str]]:
    rows = merge_scd2_dimension(
        current_rows=[],
        staging_rows=day1_rows,
        business_key=business_key,
        surrogate_key=surrogate_key,
        run_id="RUN_CUSTOMER360_FULL_20260525",
        batch_timestamp="2026-05-25T23:59:59",
    )
    return merge_scd2_dimension(
        current_rows=rows,
        staging_rows=day2_rows,
        business_key=business_key,
        surrogate_key=surrogate_key,
        run_id="RUN_CUSTOMER360_FULL_20260526",
        batch_timestamp="2026-05-26T23:59:59",
    )


def _std_customer(row: dict[str, str]) -> dict[str, str]:
    return {
        "source_system_id": "CONFORMED",
        "source_customer_id": row["client_id"],
        "customer_name": row["client_name"],
        "std_customer_name": _std_text(re.sub(r"\bPTY LTD\b|\bPROPRIETARY LIMITED\b|\bLIMITED\b|\bLTD\b", "", row["client_name"], flags=re.I)),
        "std_abn": re.sub(r"[^0-9]", "", row.get("abn", "")),
        "std_email_domain": row.get("email_domain", "").strip().lower(),
        "std_address_line_1": _std_text(row.get("address_line_1", "")),
        "std_suburb": _std_text(row.get("suburb", "")),
        "std_state": row.get("state", row.get("headquarters_state", "")).strip().upper(),
        "std_postcode": re.sub(r"[^0-9]", "", row.get("postcode", "")),
        "std_country": row.get("country", "AU").strip().upper(),
        "customer_segment": row.get("industry_segment") or row.get("fleet_size_band", ""),
        "customer_status": row.get("client_status", ""),
        "source_updated_at": row.get("source_updated_at", ""),
    }


def _std_vehicle(row: dict[str, str]) -> dict[str, str]:
    return {
        "source_system_id": "CONFORMED",
        "source_vehicle_id": row["vehicle_id"],
        "source_customer_id": row["client_id"],
        "std_vin": re.sub(r"[^A-Z0-9]", "", row.get("vin", "").upper()),
        "std_registration_plate": re.sub(r"[^A-Z0-9]", "", row.get("registration_plate", "").upper()),
        "std_telematics_device_id": row.get("telematics_device_id", "").strip().upper(),
        "telematics_device_model": row.get("telematics_device_model", ""),
        "state_registered": row.get("state_registered", ""),
        "asset_type": row.get("asset_type", ""),
        "make": row.get("make", ""),
        "model": row.get("model", ""),
        "model_year": row.get("model_year", ""),
        "fuel_type": row.get("fuel_type", ""),
        "vehicle_status": row.get("vehicle_status", ""),
    }


def _golden_customer(row: dict[str, str]) -> dict[str, str]:
    return {
        "golden_customer_id": f"GCUST_{_hash(row['source_customer_id'])[:16]}",
        "customer_name": row["customer_name"],
        "customer_segment": row["customer_segment"],
        "customer_status": row["customer_status"],
        "primary_source_system_id": row["source_system_id"],
        "primary_source_customer_id": row["source_customer_id"],
        "identity_resolution_confidence": "1.000000",
        "match_method": "deterministic_source_customer_id",
        "survivorship_rule_version": "customer_survivorship_v0.1",
    }


def _golden_vehicle(row: dict[str, str], customer_by_source: dict[str, dict[str, str]]) -> dict[str, str]:
    customer = customer_by_source.get(row["source_customer_id"], {})
    return {
        "golden_vehicle_id": f"GVEH_{_hash(row['source_vehicle_id'])[:16]}",
        "golden_customer_id": customer.get("golden_customer_id", ""),
        "vehicle_id": row["source_vehicle_id"],
        "vin": row["std_vin"],
        "registration_plate": row["std_registration_plate"],
        "telematics_device_id": row["std_telematics_device_id"],
        "state_registered": row["state_registered"],
        "asset_type": row["asset_type"],
        "make": row["make"],
        "model": row["model"],
        "model_year": row["model_year"],
        "fuel_type": row["fuel_type"],
        "vehicle_status": row["vehicle_status"],
        "identity_resolution_confidence": "1.000000",
        "match_method": "deterministic_vin" if row["std_vin"] else "deterministic_vehicle_id",
        "survivorship_rule_version": "vehicle_survivorship_v0.1",
    }


def _std_device(std_vehicle: list[dict[str, str]], telematics: list[dict[str, str]]) -> list[dict[str, str]]:
    rows = []
    seen = set()
    for vehicle in std_vehicle:
        device_id = vehicle["std_telematics_device_id"]
        if device_id and (device_id, vehicle["source_vehicle_id"]) not in seen:
            rows.append({"source_device_id": device_id, "source_vehicle_id": vehicle["source_vehicle_id"], "provider_name": ""})
            seen.add((device_id, vehicle["source_vehicle_id"]))
    for event in telematics:
        device_id = event.get("telematics_device_id", "").strip().upper()
        vehicle_id = event.get("vehicle_id", "")
        if device_id and (device_id, vehicle_id) not in seen:
            rows.append({"source_device_id": device_id, "source_vehicle_id": vehicle_id, "provider_name": event.get("provider_name", "")})
            seen.add((device_id, vehicle_id))
    return rows


def _xref_device(std_device: list[dict[str, str]], vehicle_by_source: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    rows = []
    for device in std_device:
        vehicle = vehicle_by_source.get(device["source_vehicle_id"], {})
        rows.append(
            {
                "golden_device_id": f"GDEV_{_hash(device['source_device_id'])[:16]}",
                "golden_vehicle_id": vehicle.get("golden_vehicle_id", ""),
                "golden_customer_id": vehicle.get("golden_customer_id", ""),
                "source_device_id": device["source_device_id"],
                "match_confidence": "1.000000",
                "match_method": "deterministic_provider_device_id",
            }
        )
    return rows


def _xref_account(invoices: list[dict[str, str]], customer_by_source: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    return [
        {
            "golden_account_id": f"GACCT_{_hash(row['invoice_id'])[:16]}",
            "golden_customer_id": customer_by_source.get(row["client_id"], {}).get("golden_customer_id", ""),
            "source_account_id": row["invoice_id"],
            "match_confidence": "1.000000",
            "match_method": "deterministic_invoice_customer_id",
        }
        for row in _latest_rows(invoices, "invoice_id")
    ]


def _xref_fuel_card(
    fuel_cards: list[dict[str, str]],
    customer_by_source: dict[str, dict[str, str]],
    vehicle_by_source: dict[str, dict[str, str]],
) -> list[dict[str, str]]:
    rows = []
    for row in _latest_rows(fuel_cards, "fuel_card_id"):
        rows.append(
            {
                "golden_fuel_card_id": f"GFCARD_{_hash(row['fuel_card_id'])[:16]}",
                "golden_vehicle_id": vehicle_by_source.get(row["vehicle_id"], {}).get("golden_vehicle_id", ""),
                "golden_customer_id": customer_by_source.get(row["client_id"], {}).get("golden_customer_id", ""),
                "source_fuel_card_id": row["fuel_card_id"],
                "match_confidence": "1.000000",
                "match_method": "deterministic_fuel_card_id",
            }
        )
    return rows


def _review_queue(std_customer: list[dict[str, str]], std_vehicle: list[dict[str, str]]) -> list[dict[str, str]]:
    rows = []
    by_abn = defaultdict(list)
    by_vin = defaultdict(list)
    for row in std_customer:
        if row["std_abn"]:
            by_abn[row["std_abn"]].append(row)
    for row in std_vehicle:
        if row["std_vin"]:
            by_vin[row["std_vin"]].append(row)
    for abn, customers in by_abn.items():
        if len({row["std_customer_name"] for row in customers}) > 1:
            rows.append({"entity_type": "customer", "match_reason": f"conflicting names for ABN {abn}", "review_status": "open"})
    for vin, vehicles in by_vin.items():
        if len({row["source_customer_id"] for row in vehicles}) > 1:
            rows.append({"entity_type": "vehicle", "match_reason": f"VIN assigned to multiple customers {vin}", "review_status": "open"})
    return rows


def _customer360_mart(
    *,
    golden_customer: list[dict[str, str]],
    rel_customer_vehicle: list[dict[str, str]],
    leasing: list[dict[str, str]],
    fuel: list[dict[str, str]],
    maintenance: list[dict[str, str]],
    claims: list[dict[str, str]],
    portal: list[dict[str, str]],
    ev: list[dict[str, str]],
) -> list[dict[str, str]]:
    customer_ids = {row["primary_source_customer_id"]: row for row in golden_customer}
    active_vehicles = defaultdict(int)
    for rel in rel_customer_vehicle:
        if rel["relationship_status"] == "active":
            active_vehicles[rel["golden_customer_id"]] += 1
    rows = []
    for customer in golden_customer:
        source_id = customer["primary_source_customer_id"]
        gid = customer["golden_customer_id"]
        active_contracts = sum(1 for row in _latest_rows(leasing, "lease_id") if row["client_id"] == source_id and row.get("lease_status", "").lower() == "active")
        monthly_tco = sum(_num(row.get("monthly_rental_amount")) + _num(row.get("management_fee_amount")) for row in _latest_rows(leasing, "lease_id") if row["client_id"] == source_id)
        fuel_cost = sum(_num(row.get("gross_amount")) for row in fuel if row["client_id"] == source_id)
        maintenance_cost = sum(_num(row.get("invoice_amount")) or _num(row.get("authorised_amount")) for row in _latest_rows(maintenance, "work_order_id") if row["client_id"] == source_id)
        ev_cost = sum(_num(row.get("gross_amount")) for row in _latest_rows(ev, "charging_session_id") if row["client_id"] == source_id)
        open_claims = sum(1 for row in _latest_rows(claims, "claim_id") if row["client_id"] == source_id and row.get("claim_status", "").lower() not in {"closed", "settled", "declined"})
        portal_score = min(100, sum(1 for row in _latest_rows(portal, "portal_event_id") if row["client_id"] == source_id) * 0.5)
        rows.append(
            {
                "golden_customer_id": gid,
                "customer_name": customer["customer_name"],
                "customer_segment": customer["customer_segment"],
                "active_vehicle_count": str(active_vehicles[gid]),
                "active_contract_count": str(active_contracts),
                "monthly_tco": f"{monthly_tco:.2f}",
                "maintenance_cost_90d": f"{maintenance_cost:.2f}",
                "fuel_cost_90d": f"{fuel_cost:.2f}",
                "ev_charging_cost_90d": f"{ev_cost:.2f}",
                "open_claim_count": str(open_claims),
                "portal_activity_score": f"{portal_score:.2f}",
                "service_risk_score": f"{min(100, active_vehicles[gid] * 1.5 + open_claims * 8):.2f}",
                "fleet_growth_opportunity_score": "50.00" if active_vehicles[gid] else "0.00",
                "data_quality_status": "certified" if source_id in customer_ids else "failed",
                "identity_resolution_confidence": customer["identity_resolution_confidence"],
            }
        )
    return rows


def _latest_rows(rows: list[dict[str, str]], key: str) -> list[dict[str, str]]:
    if not rows or "_is_latest_for_business_key" not in rows[0]:
        return rows
    return [
        row
        for row in rows
        if row.get("_is_latest_for_business_key") == "true"
        and row.get("_latest_resolution_status") == "resolved"
        and row.get("_is_exact_duplicate") != "true"
    ]


def _std_text(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9 ]", "", value.upper())).strip()


def _num(value: str | None) -> float:
    if not value:
        return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
