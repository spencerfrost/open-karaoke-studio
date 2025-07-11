# Migrating from SQLite to PostgreSQL in Open Karaoke Studio

## Why Migrate?

- PostgreSQL supports full ALTER TABLE operations, constraints, and advanced features.
- Better for production, scaling, and migrations.
- Avoids SQLite limitations (like column nullability changes).

## Migration Steps

### 1. Install PostgreSQL

- On Ubuntu: `sudo apt install postgresql postgresql-contrib`
- Or use Docker, Homebrew, or a managed service.

### 2. Create a Database and User

- `sudo -u postgres psql`
- `CREATE DATABASE karaoke;`
- `CREATE USER karaoke_user WITH PASSWORD 'yourpassword';`
- `GRANT ALL PRIVILEGES ON DATABASE karaoke TO karaoke_user;`
- `\q`

### 3. Install psycopg2

- `pip install psycopg2-binary`

### 4. Update SQLAlchemy Connection String

- In your config (env var or settings):
  - `postgresql://karaoke_user:yourpassword@localhost/karaoke`

### 5. Run Alembic Migrations

- `alembic upgrade head`
- This will create all tables in the new Postgres database.

### 6. (Optional) Migrate Data

- Use tools like `pgloader`, `sqlalchemy`, or custom scripts to copy data from SQLite to Postgres if needed.

### 7. Update Your App

- Make sure your backend uses the new connection string.
- Test all endpoints and jobs.

## Notes

- You may need to update some SQLAlchemy types (e.g., use `Text` instead of `String` for long text fields).
- Test thoroughly after migration.
- You can keep your old SQLite DB as a backup.

---

_This guide is for Open Karaoke Studio but applies to most Flask/SQLAlchemy projects._
