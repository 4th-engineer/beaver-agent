"""Tests for DataStore - user/system data separation and migration management."""

import json
from pathlib import Path

import pytest

from beaver_agent.core.data_store import (
    DataStore,
    DataVersion,
    get_data_store,
)


class TestDataVersion:
    """Tests for DataVersion comparison and parsing."""

    def test_version_parsing(self):
        """Test basic version string parsing"""
        v = DataVersion("1.2.3")
        assert v.raw == "1.2.3"

    def test_version_comparison_lt(self):
        """Test less-than comparison"""
        assert DataVersion("1.0.0") < DataVersion("2.0.0")
        assert DataVersion("1.0.0") < DataVersion("1.1.0")
        assert DataVersion("1.0.0") < DataVersion("1.0.1")

    def test_version_comparison_le(self):
        """Test less-than-or-equal comparison"""
        assert DataVersion("1.0.0") <= DataVersion("1.0.0")
        assert DataVersion("1.0.0") <= DataVersion("2.0.0")

    def test_version_comparison_gt(self):
        """Test greater-than comparison"""
        assert DataVersion("2.0.0") > DataVersion("1.0.0")
        assert DataVersion("1.1.0") > DataVersion("1.0.0")

    def test_version_comparison_ge(self):
        """Test greater-than-or-equal comparison"""
        assert DataVersion("1.0.0") >= DataVersion("1.0.0")
        assert DataVersion("2.0.0") >= DataVersion("1.0.0")

    def test_version_equality(self):
        """Test version equality"""
        assert DataVersion("1.0.0") == DataVersion("1.0.0")
        assert DataVersion("1.0.0") != DataVersion("2.0.0")

    def test_version_hash(self):
        """Test version can be used in sets/dicts"""
        versions = {DataVersion("1.0.0"), DataVersion("2.0.0")}
        assert DataVersion("1.0.0") in versions

    def test_version_with_prerelease(self):
        """Test version with prerelease suffix is parsed correctly"""
        v = DataVersion("1.0.0-alpha")
        assert v.raw == "1.0.0-alpha"
        # Should not raise on comparison
        assert v < DataVersion("1.0.0")

    def test_version_str_repr(self):
        """Test string representation"""
        v = DataVersion("1.2.3")
        assert str(v) == "1.2.3"
        assert repr(v) == "DataVersion(1.2.3)"


class TestDataStoreInit:
    """Tests for DataStore initialization with temp directories."""

    @pytest.fixture
    def temp_root(self, tmp_path):
        """Create a temp project root for DataStore."""
        return tmp_path

    @pytest.fixture
    def store(self, temp_root):
        """Create a DataStore instance with temp root."""
        return DataStore(project_root=temp_root)

    def test_init_creates_data_directories(self, store, temp_root):
        """Test that __post_init__ creates all required directories."""
        assert store.data_dir.exists()
        assert store.logs_dir.exists()
        assert store.config_dir.exists()
        assert store.skills_builtin.exists()
        assert store.skills_user.exists()

    def test_init_sets_correct_paths(self, store, temp_root):
        """Test that paths are set relative to project_root."""
        assert store.data_dir == temp_root / "data"
        assert store.logs_dir == temp_root / "data" / "logs"
        assert store.config_dir == temp_root / "data" / "config"
        assert store.skills_builtin == temp_root / "data" / "skills" / "builtin"
        assert store.skills_user == temp_root / "data" / "skills" / "user"

    def test_legacy_paths_set(self, store, temp_root):
        """Test legacy paths are computed correctly."""
        assert store.legacy_logs == temp_root / "logs"
        assert store.legacy_skills == temp_root / "skills"
        assert store.legacy_config == temp_root / "config"

    def test_migration_registry_initialized(self, store):
        """Test that built-in migrations are registered."""
        assert len(store._migrations) >= 2
        assert "0.1.0" in store._migrations
        assert "0.2.0" in store._migrations


class TestDataStoreVersion:
    """Tests for DataStore version management."""

    @pytest.fixture
    def store(self, tmp_path):
        return DataStore(project_root=tmp_path)

    def test_get_version_returns_zero_when_no_file(self, store):
        """Test get_version returns 0.0.0 when version file doesn't exist."""
        assert store.get_version().raw == "0.0.0"

    def test_set_and_get_version(self, store, tmp_path):
        """Test set_version writes and get_version reads correctly."""
        store.set_version("1.2.3")
        version_file = tmp_path / "data" / ".version"
        assert version_file.read_text().strip() == "1.2.3"
        assert store.get_version().raw == "1.2.3"

    def test_set_version_strips_whitespace(self, store):
        """Test set_version strips leading/trailing whitespace."""
        store.set_version("  1.0.0  ")
        assert store.get_version().raw == "1.0.0"


class TestDataStoreMigrations:
    """Tests for DataStore migration tracking."""

    @pytest.fixture
    def store(self, tmp_path):
        return DataStore(project_root=tmp_path)

    def test_get_applied_migrations_returns_empty_when_no_file(self, store):
        """Test get_applied_migrations returns [] when file doesn't exist."""
        assert store.get_applied_migrations() == []

    def test_save_and_get_applied_migrations(self, store, tmp_path):
        """Test _save_applied and get_applied_migrations round-trip."""
        store._save_applied(["migration_a", "migration_b"])
        applied_file = tmp_path / "data" / ".applied_migrations"
        assert json.loads(applied_file.read_text()) == ["migration_a", "migration_b"]
        assert store.get_applied_migrations() == ["migration_a", "migration_b"]

    def test_get_applied_migrations_handles_empty_file(self, store, tmp_path):
        """Test get_applied_migrations handles empty file gracefully."""
        applied_file = tmp_path / "data" / ".applied_migrations"
        applied_file.write_text("")
        assert store.get_applied_migrations() == []

    def test_get_applied_migrations_handles_invalid_json(self, store, tmp_path):
        """Test get_applied_migrations handles corrupt JSON gracefully."""
        applied_file = tmp_path / "data" / ".applied_migrations"
        applied_file.write_text("not valid json{{{")
        # Should return empty list and log warning
        assert store.get_applied_migrations() == []

    def test_get_pending_migrations_returns_all_when_none_applied(self, store):
        """Test get_pending_migrations returns all registered when none applied."""
        store.set_version("0.0.0")
        pending = store.get_pending_migrations()
        assert len(pending) == 2
        # Migration.name is the human-readable name, not the version string
        assert pending[0].name == "initial_user_system_separation"
        assert pending[1].name == "add_structured_skill_format"

    def test_get_pending_migrations_skips_already_applied(self, store):
        """Test get_pending_migrations skips already-applied migrations."""
        store.set_version("0.1.0")
        store._save_applied(["initial_user_system_separation"])
        pending = store.get_pending_migrations()
        assert len(pending) == 1
        assert pending[0].name == "add_structured_skill_format"

    def test_get_pending_migrations_returns_empty_when_all_applied(self, store):
        """Test get_pending_migrations returns [] when all migrations applied."""
        store.set_version("0.2.0")
        store._save_applied(["initial_user_system_separation", "add_structured_skill_format"])
        assert store.get_pending_migrations() == []

    def test_is_legacy_true_when_no_version_file(self, store):
        """Test is_legacy returns True when version file doesn't exist."""
        assert store.is_legacy() is True

    def test_is_legacy_false_when_version_file_exists(self, store, tmp_path):
        """Test is_legacy returns False when version file exists."""
        (tmp_path / "data" / ".version").write_text("0.1.0")
        store = DataStore(project_root=tmp_path)
        assert store.is_legacy() is False

    def test_is_migration_needed_true_when_pending(self, store):
        """Test is_migration_needed returns True when migrations are pending."""
        store.set_version("0.0.0")
        assert store.is_migration_needed() is True

    def test_is_migration_needed_false_when_up_to_date(self, store, tmp_path):
        """Test is_migration_needed returns False when up to date."""
        store.set_version("0.2.0")
        store._save_applied(["initial_user_system_separation", "add_structured_skill_format"])
        assert store.is_migration_needed() is False

    def test_migrate_runs_pending_migrations(self, store, tmp_path):
        """Test migrate() executes pending migrations in order."""
        store.set_version("0.0.0")
        called = []

        def migration_1(ds):
            called.append("m1")
            return True

        def migration_2(ds):
            called.append("m2")
            return True

        store.register_migration("0.1.0", "migration_one", "First migration", migration_1)
        store.register_migration("0.2.0", "migration_two", "Second migration", migration_2)

        result = store.migrate()

        assert result is True
        assert called == ["m1", "m2"]
        assert store.get_version() == DataVersion("0.2.0")

    def test_migrate_returns_true_when_nothing_pending(self, store):
        """Test migrate() returns True when no migrations are pending."""
        # Apply all built-in migrations so nothing is pending
        store._save_applied(["initial_user_system_separation", "add_structured_skill_format"])
        store.set_version("0.2.0")
        result = store.migrate()
        assert result is True

    def test_migrate_returns_false_when_migration_raises(self, store, tmp_path):
        """Test migrate() returns False when a migration raises an exception."""
        # Override the first built-in migration with a bad one
        store._migrations.clear()

        def bad_migration(ds):
            raise RuntimeError("migration error")

        store.register_migration("0.1.0", "bad_migration", "Bad migration", bad_migration)
        store.set_version("0.0.0")

        result = store.migrate()

        assert result is False
        # Version should not advance past the failed migration
        assert store.get_version() == DataVersion("0.0.0")

    def test_migrate_returns_false_when_migration_returns_false(self, store, tmp_path):
        """Test migrate() returns False when a migration returns False."""
        store._migrations.clear()

        def failing_migration(ds):
            return False

        store.register_migration(
            "0.1.0", "failing_migration", "Failing migration", failing_migration
        )
        store.set_version("0.0.0")

        result = store.migrate()

        assert result is False
        assert store.get_version() == DataVersion("0.0.0")

    def test_migrate_skips_already_applied_migrations(self, store, tmp_path):
        """Test migrate() skips migrations that are already applied."""
        # Override with clean migrations for this test
        store._migrations.clear()
        called = []

        def migration_1(ds):
            called.append("m1")
            return True

        def migration_2(ds):
            called.append("m2")
            return True

        store.register_migration("0.1.0", "migration_one", "First migration", migration_1)
        store.register_migration("0.2.0", "migration_two", "Second migration", migration_2)
        store.set_version("0.0.0")
        # Pre-apply the first migration
        store._save_applied(["migration_one"])

        result = store.migrate()

        assert result is True
        assert called == ["m2"]
        assert store.get_version() == DataVersion("0.2.0")

    def test_register_migration_stores_migration(self, store):
        """Test register_migration() stores the migration in the registry."""
        initial_count = len(store._migrations)

        def dummy(ds):
            return True

        store.register_migration("9.9.9", "test_migration", "Test migration", dummy)
        pending = store.get_pending_migrations()

        assert len(pending) == initial_count + 1
        test_mig = next(m for m in pending if m.name == "test_migration")
        assert test_mig.description == "Test migration"
        assert test_mig.version == DataVersion("9.9.9")


class TestDataStoreDataAccess:
    """Tests for DataStore data access methods."""

    @pytest.fixture
    def store(self, tmp_path):
        return DataStore(project_root=tmp_path)

    def test_get_skills_dirs_returns_dict(self, store):
        """Test get_skills_dirs returns a dict with builtin and user paths."""
        dirs = store.get_skills_dirs()
        assert "builtin" in dirs
        assert "user" in dirs
        assert isinstance(dirs["builtin"], Path)
        assert isinstance(dirs["user"], Path)

    def test_get_log_files_returns_empty_when_no_logs(self, store):
        """Test get_log_files returns empty list when no logs exist."""
        assert store.get_log_files() == []

    def test_get_log_files_returns_sorted_newest_first(self, store, tmp_path):
        """Test get_log_files returns files sorted by mtime descending."""
        logs_dir = tmp_path / "data" / "logs"
        file_a = logs_dir / "conversation_a.jsonl"
        file_b = logs_dir / "conversation_b.jsonl"
        # Write A first
        file_a.write_text("entry a\n")
        import time

        time.sleep(0.05)
        # Write B after A — B should be newer
        file_b.write_text("entry b\n")
        files = store.get_log_files()
        assert len(files) == 2
        # Newest first
        assert files[0] == file_b
        assert files[1] == file_a

    def test_get_stats_returns_correct_structure(self, store):
        """Test get_stats returns expected keys and types."""
        stats = store.get_stats()
        assert "version" in stats
        assert "pending_migrations" in stats
        assert "logs" in stats
        assert "skills" in stats
        assert stats["logs"]["files"] == 0
        assert stats["logs"]["entries"] == 0
        assert stats["skills"]["builtin"] == 0
        assert stats["skills"]["user"] == 0

    def test_get_stats_counts_log_entries(self, store, tmp_path):
        """Test get_stats counts log file entries correctly."""
        log_file = tmp_path / "data" / "logs" / "conversation_test.jsonl"
        log_file.write_text('{"id": 1}\n{"id": 2}\n{"id": 3}\n')
        stats = store.get_stats()
        assert stats["logs"]["files"] == 1
        assert stats["logs"]["entries"] == 3


class TestInitDataStore:
    """Tests for global DataStore singleton initialization."""

    def test_get_data_store_returns_datastore_instance(self):
        """Test get_data_store returns a DataStore instance."""
        store = get_data_store()
        assert isinstance(store, DataStore)

    def test_get_data_store_returns_same_instance_on_repeated_calls(self):
        """Test get_data_store returns the same instance (singleton pattern)."""
        store1 = get_data_store()
        store2 = get_data_store()
        assert store1 is store2
