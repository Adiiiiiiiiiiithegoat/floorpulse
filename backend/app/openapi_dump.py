"""`python -m app.openapi_dump <path>`: write the OpenAPI schema without starting a server."""

import json
import sys
from pathlib import Path

from app.main import app

if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("openapi.json")
    out.write_text(json.dumps(app.openapi(), indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {out}")
