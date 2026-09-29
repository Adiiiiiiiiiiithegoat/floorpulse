"""`python -m app.seed [--reset]`: create the demo organization."""

import argparse
import time

from sqlalchemy import select

from app.core.db import SessionLocal, engine
from app.models import Base, Organization
from app.seed.demo import DEMO_PASSWORD, DEMO_PIN, seed


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--reset", action="store_true", help="drop and recreate all tables first (dev only)")
    args = p.parse_args()
    if args.reset:
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
    t0 = time.perf_counter()
    with SessionLocal() as db:
        if db.scalar(select(Organization).where(Organization.slug == "demo")):
            print("Demo org already exists; use --reset to rebuild.")
            return
        refs = seed(db)
    print(f"Seeded '{refs.org.name}' in {time.perf_counter() - t0:.1f}s")
    print(f"  password for all email users: {DEMO_PASSWORD}   PIN for shop-floor users: {DEMO_PIN}")
    for code, tok in refs.device_tokens.items():
        print(f"  device token {code}: {tok}")


if __name__ == "__main__":
    main()
