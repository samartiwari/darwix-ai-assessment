"""Build the knowledge base.

    python scripts/build_kb.py --stage collect     # fetch, extract, clean
    python scripts/build_kb.py --stage collect --no-cache

Stages run in order and each writes its output to data/interim/ so a later
stage can be re-run without repeating the network work.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

STAGES = ("collect",)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=STAGES + ("all",), default="all")
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="re-fetch sources instead of using data/raw/",
    )
    args = parser.parse_args()

    if args.stage in ("collect", "all"):
        from core.kb import ingest

        ingest.main(use_cache=not args.no_cache)

    return 0


if __name__ == "__main__":
    sys.exit(main())
