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
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    return result.returncode


def create_migration(message: str) -> int:
    """Create a new migration with autogenerate."""
    if not message:
        print("Error: Migration message is required")
        print("Usage: python migrate.py create 'Your migration message'")
        return 1
    
    return run_alembic_command(["revision", "--autogenerate", "-m", message])


def upgrade(revision: str = "head") -> int:
    """Upgrade to a later version."""
    return run_alembic_command(["upgrade", revision])


def downgrade(revision: str = "-1") -> int:
    """Revert to a previous version."""
    return run_alembic_command(["downgrade", revision])


def current() -> int:
    """Display the current revision."""
    return run_alembic_command(["current"])


def history() -> int:
    """List changeset scripts in chronological order."""
    return run_alembic_command(["history", "--verbose"])


def stamp(revision: str = "head") -> int:
    """'stamp' the revision table with the given revision."""
    return run_alembic_command(["stamp", revision])


def show(revision: str = "head") -> int:
    """Show the revision(s) denoted by the given symbol."""
    return run_alembic_command(["show", revision])


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    
    command = sys.argv[1].lower()
    
    if command == "create":
        message = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        return create_migration(message)
    
    elif command == "upgrade":
        revision = sys.argv[2] if len(sys.argv) > 2 else "head"
        return upgrade(revision)
    
    elif command == "downgrade":
        revision = sys.argv[2] if len(sys.argv) > 2 else "-1"
        return downgrade(revision)
    
    elif command == "current":
        return current()
    
    elif command == "history":
        return history()
    
    elif command == "stamp":
        revision = sys.argv[2] if len(sys.argv) > 2 else "head"
        return stamp(revision)
    
    elif command == "show":
        revision = sys.argv[2] if len(sys.argv) > 2 else "head"
        return show(revision)
    
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        return 1


if __name__ == "__main__":
    sys.exit(main())
