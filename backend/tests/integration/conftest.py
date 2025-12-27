"""
Pytest configuration for integration tests.

This conftest sets up database configuration BEFORE any app modules are imported.
"""

import os
import sys
import tempfile
import pytest


# CRITICAL: Set test database URL at pytest collection time (before any imports)
_test_db_fd, _test_db_path = tempfile.mkstemp(suffix=".db")
os.close(_test_db_fd)
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db_path}"

print(f"\n{'='*80}")
print(f"INTEGRATION TEST DATABASE SETUP")
print(f"{'='*80}")
print(f"Test database path: {_test_db_path}")
print(f"DATABASE_URL: {os.environ['DATABASE_URL']}")
print(f"{'='*80}\n")

# Clear any cached app modules so they pick up the new DATABASE_URL
for module_name in list(sys.modules.keys()):
    if module_name.startswith('app.'):
        del sys.modules[module_name]


@pytest.fixture(scope="function", autouse=True)
def apply_test_config(monkeypatch):
    """
    Override parent conftest's apply_test_config to use our integration test database.

    This fixture runs before every test and ensures the DATABASE_URL environment
    variable points to our integration test database, not the :memory: database
    from the parent conftest.
    """
    # Keep the DATABASE_URL we set at module level
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{_test_db_path}")

    # Force reload of database module to pick up the correct DATABASE_URL
    if 'app.db.database' in sys.modules:
        del sys.modules['app.db.database']
    if 'app.config' in sys.modules:
        del sys.modules['app.config']
    # Clear all app modules to ensure they reload with correct database
    for module_name in list(sys.modules.keys()):
        if module_name.startswith('app.'):
            del sys.modules[module_name]

    print(f"Test config applied - DATABASE_URL: {os.environ['DATABASE_URL']}")


def pytest_sessionfinish(session, exitstatus):
    """Clean up test database after all tests complete."""
    try:
        os.unlink(_test_db_path)
    except:
        pass
