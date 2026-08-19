from __future__ import annotations

import argparse
from pathlib import Path

from app.etl.importer import build_database


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Moneki analytics database")
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    args = parser.parse_args()
    summary = build_database(args.data_dir, args.database)
    print(summary.to_json())


if __name__ == "__main__":
    main()
