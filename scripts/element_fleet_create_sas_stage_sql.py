"""Create a Snowflake stage SQL file with a short-lived Azure user-delegation SAS."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
from pathlib import Path

from azure.identity import InteractiveBrowserCredential
from azure.storage.blob import BlobServiceClient, ContainerSasPermissions, generate_container_sas


DEFAULT_ACCOUNT_NAME = "emilygcovidreportingdl"
DEFAULT_TENANT_ID = "4255f836-8ff1-4e78-a7b9-602e32708e78"
DEFAULT_FILESYSTEM = "fabric-foundry-sit"
DEFAULT_OUTPUT = Path(".local/element_fleet_sas_stage.sql")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Snowflake SQL for an Azure SAS-backed stage.")
    parser.add_argument("--account-name", default=DEFAULT_ACCOUNT_NAME)
    parser.add_argument("--tenant-id", default=DEFAULT_TENANT_ID)
    parser.add_argument("--filesystem", default=DEFAULT_FILESYSTEM)
    parser.add_argument("--hours", type=int, default=8)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    credential = InteractiveBrowserCredential(tenant_id=args.tenant_id)
    service = BlobServiceClient(
        account_url=f"https://{args.account_name}.blob.core.windows.net/",
        credential=credential,
    )
    now = datetime.now(UTC).replace(microsecond=0)
    delegation_key = service.get_user_delegation_key(
        key_start_time=now - timedelta(minutes=5),
        key_expiry_time=now + timedelta(hours=args.hours),
    )
    sas = generate_container_sas(
        account_name=args.account_name,
        container_name=args.filesystem,
        user_delegation_key=delegation_key,
        permission=ContainerSasPermissions(read=True, list=True),
        start=now - timedelta(minutes=5),
        expiry=now + timedelta(hours=args.hours),
    )
    token = sas[1:] if sas.startswith("?") else sas
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        f"""USE ROLE ACCOUNTADMIN;
USE DATABASE FLEET_MVP_SIT;
USE WAREHOUSE FLEET_MVP_SIT_WH;

CREATE OR REPLACE STAGE STG_FLEET.ADLS_STAGING_STAGE
  URL = 'azure://{args.account_name}.blob.core.windows.net/{args.filesystem}/staging/'
  CREDENTIALS = (AZURE_SAS_TOKEN = '{token}')
  FILE_FORMAT = STG_FLEET.PARQUET_FF;

LIST @STG_FLEET.ADLS_STAGING_STAGE;
""",
        encoding="utf-8",
    )
    print(f"Wrote SAS-backed stage SQL to {args.output}")
    print(f"SAS expires at {(now + timedelta(hours=args.hours)).isoformat()}")


if __name__ == "__main__":
    main()
