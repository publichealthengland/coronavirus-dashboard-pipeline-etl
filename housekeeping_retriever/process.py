#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
from typing import List
from collections import defaultdict
from datetime import datetime, timedelta
import logging
import re

# 3rd party:

# Internal:
try:
    from __app__.storage import StorageClient
    from __app__.housekeeping_orchestrator.dtypes import RetrieverPayload, ArchiverPayload
except ImportError:
    from storage import StorageClient
    from housekeeping_orchestrator.dtypes import RetrieverPayload, ArchiverPayload

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    "main"
]


pattern = re.compile(
    r"""
    ^
    (?P<from_path>
    etl/
    (?P<category>[a-z-]+)/
    (?P<subcategory>[a-z-]+)?/?
    (?P<date>\d{4}-\d{2}-\d{2})/
    (?P<filename>.+\.ft)
    )
    $
    """,
    re.VERBOSE | re.IGNORECASE
)


def main(payload: RetrieverPayload) -> List[List[ArchiverPayload]]:
    logging.info(f"Triggered with payload: {payload}")

    timestamp = datetime.fromisoformat(payload['timestamp'])
    max_date = f"{timestamp - timedelta(days=7):%Y-%m-%d}"

    candidates = defaultdict(list)

    with StorageClient("pipeline", "etl/") as cli:
        for blob in cli.list_blobs():
            path = pattern.search(blob["name"])

            try:
                content_type = blob['content_settings']['content_type']
            except KeyError:
                content_type = "application/octet-stream"

            if path is None:
                logging.info(f'Unmatched pattern: {blob["name"]}')
                continue

            if path['date'] > max_date:
                continue

            blob_data = ArchiverPayload(**path.groupdict(), content_type=content_type)

            candidates[path['date']].append(blob_data)
            break

    logging.info(f"Done processing: {payload}")

    return list(candidates.values())