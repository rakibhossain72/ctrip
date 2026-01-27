# Database Migrations Guide

This project uses **Alembic** for database schema migrations with best practices configured.

## Quick Start

### Using the Helper Script (Recommended)

```bash
# Create a new migration (auto-generates based on model changes)
python migrate.py create "Add user table"

# Apply all pending migrations
python migrate.py upgrade

# Rollback the last migration
python migrate.py downgrade

# Show current migration version
python migrate.py current

# Show migration history
python migrate.py history
```

### Direct Alembic Commands

```bash
# Create a new migration
alembic revision --autogenerate -m "Add user table"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Show current version
alembic current

# Show history
alembic history --verbose
```

## Configuration

### Key Features

1. **Automatic Migration Generation**: Alembic detects model changes and generates migrations automatically
2. **Async Support**: Configured to work with both async (PostgreSQL) and sync (SQLite) drivers
3. **Batch Mode for SQLite**: Handles SQLite's limited ALTER TABLE support
4. **Timestamped Filenames**: Migration files include date/time for better organization
5. **Type Comparison**: Detects column type changes
6. **Environment-Aware**: Automatically uses correct database URL based on `env` setting

### File Structure

```
alembic/
├── versions/              # Migration scripts
│   └── 2026_01_27_1807-5ec6405addd0_initial_database_schema.py
├── env.py                # Alembic environment configuration
├── script.py.mako        # Migration template
└── README               # Alembic readme

alembic.ini               # Alembic configuration file
migrate.py                # Helper script for common operations
```

## Workflow

### Development Workflow

1. **Make Model Changes** in `/app/db/models/`
2. **Generate Migration**:
   ```bash
   python migrate.py create "Description of changes"
   ```
3. **Review Generated Migration** in `alembic/versions/`
4. **Apply Migration**:
   ```bash
   python migrate.py upgrade
   ```
5. **Commit** both the model changes and migration file to git

### Production Deployment

1. **Test migrations** in staging environment first
2. **Backup database** before applying migrations
3. **Apply migrations**:
   ```bash
   python migrate.py upgrade
   ```
4. **Verify** application works correctly
5. **Monitor** for any issues

## Best Practices

### DO

- Always review auto-generated migrations before applying
- Test migrations on a copy of production data
- Keep migrations reversible when possible
- Write descriptive migration messages
- Commit migration files to version control
- Create separate migrations for each logical change
- Run migrations before deploying application code

### DON'T

- Don't edit applied migrations (create a new one instead)
- Don't manually modify the database schema (use migrations)
- Don't skip migrations or cherry-pick them
- Don't use `Base.metadata.create_all()` in production (it's disabled)
- Don't force push migrations that have been deployed

## Common Tasks

### Create Initial Migration

Already done! The initial schema is in:
```
alembic/versions/2026_01_27_1807-5ec6405addd0_initial_database_schema.py
```

### Add a New Column

1. Add column to model:
   ```python
   class Payment(Base):
       # ... existing columns ...
       new_field = Column(String, nullable=True)
   ```

2. Generate migration:
   ```bash
   python migrate.py create "Add new_field to payments"
   ```

3. Apply migration:
   ```bash
   python migrate.py upgrade
   ```

### Modify Column Type

1. Change column in model
2. Generate migration (Alembic will detect type change)
3. Review migration for SQLite compatibility
4. Apply migration

### Drop a Table

1. Remove model class
2. Generate migration
3. **Important**: Review carefully - this is destructive!
4. Apply migration

### Rollback a Migration

```bash
# Rollback one migration
python migrate.py downgrade

# Rollback to specific version
alembic downgrade <revision>

# Rollback all migrations
alembic downgrade base
```

## Troubleshooting

### "This event loop is already running"

**Fixed!** The workers now use `asyncio.run()` which creates a new event loop for each task.

### SQLite ALTER TABLE Errors

The configuration includes `render_as_batch=True` for SQLite compatibility. If issues persist, you may need to manually edit the migration to use batch operations.

### Migration Not Detected

1. Ensure all models are imported in `alembic/env.py`
2. Check that model inherits from `Base`
3. Verify model is in `app/db/models/__init__.py`
4. Clear any `__pycache__` directories

### Database Out of Sync

```bash
# Mark database as current without running migrations
python migrate.py stamp head
```

## Configuration Details

### Database URL

- **Development**: SQLite (`dev_database.db`)
- **Production**: PostgreSQL (from environment variables)
- Configured in: `app/core/config.py`
- Override in: `alembic/env.py` (automatically reads from config)

### Migration Detection

Alembic detects:
- New tables
- Dropped tables
- New columns
- Dropped columns
- Column type changes
- Index changes
- Constraint changes

### Async vs Sync

The `env.py` automatically chooses:
- **PostgreSQL** → Async migrations
- **SQLite** → Sync migrations (batch mode enabled)

## Integration with Application

### Server Startup

The `server.py` lifespan no longer calls `Base.metadata.create_all()`. 

**Before starting the server:**
```bash
python migrate.py upgrade
```

### Docker Deployment

Add to your Dockerfile or docker-compose:
```dockerfile
# Apply migrations on startup
RUN python migrate.py upgrade
```

Or in docker-compose.yml:
```yaml
services:
  app:
    command: >
      sh -c "python migrate.py upgrade && 
             uvicorn server:app --host 0.0.0.0"
```

## Advanced Usage

### Creating Empty Migration

```bash
alembic revision -m "Custom migration"
```

Then manually edit the generated file.

### Branching and Merging

```bash
# Create branch
alembic revision -m "Branch migration" --head=<parent_rev>@branch

# Merge branches
alembic merge -m "Merge branches" <rev1> <rev2>
```

### SQL Generation (Offline Mode)

```bash
# Generate SQL without executing
alembic upgrade head --sql
```

## References

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- Project Models: `app/db/models/`
- Database Config: `app/core/config.py`
