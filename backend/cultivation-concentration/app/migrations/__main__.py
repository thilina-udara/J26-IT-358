"""Run explicitly before deployment: python -m app.migrations --database <path>."""
import argparse
import os
from pathlib import Path
from app.migrations import migrate


def main():
    default = Path(__file__).resolve().parents[2] / 'storage/cultivation_plans.sqlite3'
    parser = argparse.ArgumentParser(description='Apply additive Component 02 SQLite migrations')
    parser.add_argument('--database', default=os.getenv('CULTIVATION_PLAN_DB', str(default)))
    args = parser.parse_args()
    migrate(args.database)
    # Reuse the existing plan bootstrap; readiness itself never creates tables.
    from app.services.cultivation_plans import PlanStore
    PlanStore(args.database)
    print('Component 02 database migrations applied successfully.')


if __name__ == '__main__':
    main()
