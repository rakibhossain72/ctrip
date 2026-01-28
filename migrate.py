#!/usr/bin/env python3
"""
Database Migration Helper Script

This script provides convenient commands for managing Alembic migrations.
It wraps common Alembic commands with better defaults and error handling.

Usage:
    python migrate.py create "Add new column"  # Create a new migration
    python migrate.py upgrade                   # Apply all pending migrations
    python migrate.py downgrade                 # Rollback one migration
    python migrate.py current                   # Show current revision
    python migrate.py history                   # Show migration history
    python migrate.py stamp head                # Mark DB as up-to-date without running migrations
"""

import subprocess
import sys
from pathlib import Path


def run_alembic_command(args: list[str]) -> int:
    """Run an alembic command and return the exit code."""
    cmd = ["alembic"] + args
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=Path(__file__).parent, check=False)
    return result.returncode


def create_migration(message: str) -> int:
    """Create a new migration with autogenerate."""
    if not message:
        print("Error: Migration message is required")
        print("Usage: python migrate.py create 'Your migration message'")
        return 1

    return run_alembic_command(["revision", "--autogenerate", "-m", message])


def upgrade(revision_id: str = "head") -> int:
    """Upgrade to a later version."""
    return run_alembic_command(["upgrade", revision_id])


def downgrade(revision_id: str = "-1") -> int:
    """Revert to a previous version."""
    return run_alembic_command(["downgrade", revision_id])


def current() -> int:
    """Display the current revision."""
    return run_alembic_command(["current"])


def history() -> int:
    """List changeset scripts in chronological order."""
    return run_alembic_command(["history", "--verbose"])


def stamp(revision_id: str = "head") -> int:
    """'stamp' the revision table with the given revision."""
    return run_alembic_command(["stamp", revision_id])


def show(revision_id: str = "head") -> int:
    """Show the revision(s) denoted by the given symbol."""
    return run_alembic_command(["show", revision_id])


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    command = sys.argv[1].lower()
    arg = sys.argv[2] if len(sys.argv) > 2 else None

    if command == "create":
        message = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        return create_migration(message)

    commands = {
        "upgrade": lambda: upgrade(arg or "head"),
        "downgrade": lambda: downgrade(arg or "-1"),
        "current": current,
        "history": history,
        "stamp": lambda: stamp(arg or "head"),
        "show": lambda: show(arg or "head"),
    }

    if command in commands:
        return commands[command]()

    print(f"Unknown command: {command}")
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
