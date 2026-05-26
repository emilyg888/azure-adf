from framework.conformed.scd_processor import merge_append_only_events, merge_scd2_dimension


def test_scd2_dimension_expires_changed_hash_and_inserts_new_version():
    current_rows = [
        {
            "client_sk": "1",
            "client_id": "C1",
            "business_key": "C1",
            "client_status": "Active",
            "source_record_hash": "old_hash",
            "effective_from": "2026-05-25T00:00:00",
            "effective_to": "9999-12-31T00:00:00+00:00",
            "is_current": "true",
            "deleted_flag": "false",
        }
    ]
    staging_rows = [
        {
            "client_id": "C1",
            "client_status": "Suspended",
            "effective_at": "2026-05-26T10:00:00",
            "updated_at": "2026-05-26T10:05:00",
            "_record_hash": "new_hash",
            "_source_system_id": "SRC",
            "_source_dataset_id": "DS",
            "_is_exact_duplicate": "false",
            "_is_latest_for_business_key": "true",
            "_latest_resolution_status": "resolved",
            "_delta_action": "UPDATE",
        }
    ]

    rows = merge_scd2_dimension(
        current_rows=current_rows,
        staging_rows=staging_rows,
        business_key="client_id",
        surrogate_key="client_sk",
        run_id="RUN_TEST",
        batch_timestamp="2026-05-26T12:00:00",
    )

    assert len(rows) == 2
    assert rows[0]["is_current"] == "false"
    assert rows[0]["effective_to"] == "2026-05-26T10:00:00"
    assert rows[0]["deleted_flag"] == "false"
    assert rows[1]["is_current"] == "true"
    assert rows[1]["client_status"] == "Suspended"
    assert rows[1]["source_record_hash"] == "new_hash"


def test_full_extract_soft_deletes_missing_current_dimension_row():
    current_rows = [
        {
            "client_sk": "1",
            "client_id": "C1",
            "business_key": "C1",
            "source_record_hash": "hash_1",
            "effective_to": "9999-12-31T00:00:00+00:00",
            "is_current": "true",
            "deleted_flag": "false",
        },
        {
            "client_sk": "2",
            "client_id": "C2",
            "business_key": "C2",
            "source_record_hash": "hash_2",
            "effective_to": "9999-12-31T00:00:00+00:00",
            "is_current": "true",
            "deleted_flag": "false",
        },
    ]
    staging_rows = [
        {
            "client_id": "C1",
            "effective_at": "2026-05-26T10:00:00",
            "updated_at": "2026-05-26T10:05:00",
            "_record_hash": "hash_1",
            "_is_exact_duplicate": "false",
            "_is_latest_for_business_key": "true",
            "_latest_resolution_status": "resolved",
        }
    ]

    rows = merge_scd2_dimension(
        current_rows=current_rows,
        staging_rows=staging_rows,
        business_key="client_id",
        surrogate_key="client_sk",
        run_id="RUN_TEST",
        batch_timestamp="2026-05-26T12:00:00",
        missing_record_action="soft_delete",
    )

    deleted = [row for row in rows if row["client_id"] == "C2"][0]
    assert deleted["is_current"] == "false"
    assert deleted["deleted_flag"] == "true"
    assert deleted["effective_to"] == "2026-05-26T12:00:00"


def test_append_only_events_insert_new_keys_without_expiring_missing_rows():
    current_rows = [
        {
            "telematics_event_id": "T1",
            "event_business_key": "T1",
            "source_record_hash": "hash_1",
        }
    ]
    staging_rows = [
        {
            "telematics_event_id": "T2",
            "event_date": "2026-05-26",
            "_record_hash": "hash_2",
            "_source_system_id": "SRC",
            "_source_dataset_id": "DS",
            "_batch_date": "2026-05-26",
            "_is_exact_duplicate": "false",
        }
    ]

    rows = merge_append_only_events(
        current_rows=current_rows,
        staging_rows=staging_rows,
        event_key="telematics_event_id",
        run_id="RUN_TEST",
    )

    assert len(rows) == 2
    assert {row["event_business_key"] for row in rows} == {"T1", "T2"}
