"""Upload Element Fleet SIT files to ADLS Gen2."""

from __future__ import annotations

import argparse
from pathlib import Path

from azure.core.exceptions import ResourceExistsError
from azure.identity import InteractiveBrowserCredential
from azure.storage.filedatalake import DataLakeServiceClient


DEFAULT_ACCOUNT_URL = "https://emilygcovidreportingdl.dfs.core.windows.net/"
DEFAULT_TENANT_ID = "4255f836-8ff1-4e78-a7b9-602e32708e78"
DEFAULT_FILESYSTEM = "fabric-foundry-sit"
DEFAULT_SOURCE_ROOT = Path(".local/element_fleet_sit_adls")


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload Element Fleet SIT files to ADLS.")
    parser.add_argument("--account-url", default=DEFAULT_ACCOUNT_URL)
    parser.add_argument("--tenant-id", default=DEFAULT_TENANT_ID)
    parser.add_argument("--filesystem", default=DEFAULT_FILESYSTEM)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    args = parser.parse_args()

    if not args.source_root.exists():
        raise FileNotFoundError(f"Missing local source root: {args.source_root}")

    credential = InteractiveBrowserCredential(tenant_id=args.tenant_id)
    service = DataLakeServiceClient(account_url=args.account_url, credential=credential)
    try:
        service.create_file_system(args.filesystem)
        print(f"Created filesystem: {args.filesystem}")
    except ResourceExistsError:
        print(f"Using existing filesystem: {args.filesystem}")

    filesystem = service.get_file_system_client(args.filesystem)
    files = [path for path in sorted(args.source_root.rglob("*")) if path.is_file()]
    for path in files:
        remote_path = path.relative_to(args.source_root).as_posix()
        file_client = filesystem.get_file_client(remote_path)
        with path.open("rb") as handle:
            file_client.upload_data(handle, overwrite=True)
        print(f"Uploaded {remote_path}")

    print(f"Uploaded {len(files)} files to {args.filesystem}")


if __name__ == "__main__":
    main()
