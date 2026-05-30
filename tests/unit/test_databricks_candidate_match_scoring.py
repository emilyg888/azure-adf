from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from databricks.notebooks.candidate_match_scoring import (
    ENTITY_CONFIG,
    format_private_key_body_as_der,
    format_private_key_for_snowflake,
    normalize_snowflake_host,
    recommended_decision,
    score_candidates,
    spark_snowflake_options,
)


def test_baseline_scorer_covers_v1_identity_entities():
    assert set(ENTITY_CONFIG) == {"CUSTOMER", "VEHICLE", "DEVICE_VEHICLE", "ACCOUNT_CUSTOMER"}
    for config in ENTITY_CONFIG.values():
        assert config["candidate_table"].startswith("IDENTITY.")
        assert config["score_table"].startswith("IDENTITY.STG_")


def test_baseline_scorer_preserves_writeback_contract():
    rows = [
        {
            "CANDIDATE_ID": "C1",
            "ENTITY_TYPE": "CUSTOMER",
            "MATCH_SCORE": 0.97,
            "MATCH_REASON_CODE": "name_address_domain_block",
        }
    ]

    scored = score_candidates(rows, "score_run_1", "mlflow_run_1")

    assert scored == [
        {
            "CANDIDATE_PAIR_ID": "C1",
            "ENTITY_TYPE": "CUSTOMER",
            "MATCH_SCORE": 0.97,
            "RECOMMENDED_DECISION": "MATCH",
            "REASON_CODES": ["name_address_domain_block"],
            "MODEL_NAME": "fleet_identity_candidate_baseline_scorer",
            "MODEL_VERSION": "v0",
            "MLFLOW_RUN_ID": "mlflow_run_1",
            "SCORING_RUN_ID": "score_run_1",
            "FEATURE_SNAPSHOT_ID": "candidate_feature_v1_score_run_1",
            "SCORED_AT": scored[0]["SCORED_AT"],
            "WRITEBACK_BATCH_ID": "score_run_1",
        }
    ]


def test_entity_thresholds_drive_recommended_decision():
    assert recommended_decision("CUSTOMER", 0.96) == "MATCH"
    assert recommended_decision("CUSTOMER", 0.80) == "REVIEW"
    assert recommended_decision("CUSTOMER", 0.20) == "NO_MATCH"
    assert recommended_decision("VEHICLE", 0.97) == "REVIEW"
    assert recommended_decision("ACCOUNT_CUSTOMER", 0.94) == "MATCH"


def test_private_key_formatter_returns_connector_safe_pkcs8_body():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    encrypted_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.BestAvailableEncryption(b"test-passphrase"),
    ).decode("utf-8")

    formatted = format_private_key_for_snowflake(encrypted_pem, "test-passphrase")

    assert "BEGIN" not in formatted
    assert "END" not in formatted
    assert "\n" not in formatted
    assert len(formatted) > 100


def test_private_key_formatter_ignores_passphrase_for_unencrypted_key():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    unencrypted_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    formatted = format_private_key_for_snowflake(unencrypted_pem, "stale-passphrase-secret")

    assert "BEGIN" not in formatted
    assert "END" not in formatted
    assert "\n" not in formatted
    assert len(formatted) > 100


def test_private_key_formatter_accepts_one_line_key_body():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    unencrypted_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    key_body = "".join(line.strip() for line in unencrypted_pem.splitlines() if "PRIVATE KEY" not in line)

    assert format_private_key_for_snowflake(key_body, "ignored") == key_body


def test_snowflake_host_normalizer_removes_scheme_and_trailing_slash():
    assert normalize_snowflake_host("https://abc.ap-southeast-2.aws.snowflakecomputing.com/") == (
        "abc.ap-southeast-2.aws.snowflakecomputing.com"
    )
    assert normalize_snowflake_host("abc.ap-southeast-2.aws.snowflakecomputing.com") == (
        "abc.ap-southeast-2.aws.snowflakecomputing.com"
    )


def test_private_key_body_can_be_converted_to_der_bytes():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    unencrypted_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    key_body = format_private_key_for_snowflake(unencrypted_pem)

    der_bytes = format_private_key_body_as_der(key_body)

    loaded_key = serialization.load_der_private_key(der_bytes, password=None)
    assert loaded_key.key_size == 2048


def test_spark_snowflake_options_excludes_python_connector_private_key_der():
    assert spark_snowflake_options({"host": "abc", "private_key_der": b"secret", "pem_private_key": "body"}) == {
        "host": "abc",
        "pem_private_key": "body",
    }
