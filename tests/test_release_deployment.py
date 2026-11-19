"""Test the release configuration without credentials or network access."""
from pathlib import Path
import tempfile
import tomllib
import unittest

from deploy.start import config_from_env, write_secrets, storage_mode
from mobile.release_url import release_url


class TestReleaseConfig(unittest.TestCase):
    def setUp(self):
        self.env = dict(
            RAILWAY_PUBLIC_DOMAIN="medpredict.example.invalid",
            DATABASE_URL="postgresql://fixture:placeholder@example.invalid/postgres",
            GOOGLE_CLIENT_ID="fixture.apps.googleusercontent.com",
            GOOGLE_CLIENT_SECRET='test"secret\\with\nescaping',
            MEDPREDICT_COOKIE_SECRET="0" * 40,
        )

    def test_independent_domain_and_oauth(self):
        base, settings = config_from_env(self.env)
        self.assertEqual(base, "https://medpredict.example.invalid")
        self.assertEqual(settings["auth"]["redirect_uri"], base + "/oauth2callback")
        self.assertEqual(release_url(base), base + "/")

    def test_missing_shared_database_is_not_silently_replaced(self):
        del self.env["DATABASE_URL"]
        with self.assertRaisesRegex(ValueError, "DATABASE_URL"):
            config_from_env(self.env)

    def test_explicit_sqlite_requires_the_durable_path(self):
        del self.env["DATABASE_URL"]
        self.env["MEDPREDICT_STORAGE"] = "sqlite"
        with self.assertRaisesRegex(ValueError, "durable data volume"):
            config_from_env(self.env)
        self.env["MEDPREDICT_DB_PATH"] = "/data/healthai.db"
        self.assertEqual(storage_mode(self.env), "sqlite")
        config_from_env(self.env)
        self.env["DATABASE_URL"] = "postgresql://example.invalid/postgres"
        with self.assertRaisesRegex(ValueError, "cannot be combined"):
            config_from_env(self.env)

    def test_bad_release_urls(self):
        for value in ("http://example.com/", "https://example.streamlit.app/",
                      "https://example.com/?embed=true", "https://user:pass@example.com/",
                      "https://example.com:1234/", "https://example.com/path"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                release_url(value)

    def test_secrets_written_privately_with_valid_escaping(self):
        _, settings = config_from_env(self.env)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".streamlit" / "secrets.toml"
            write_secrets(path, settings)
            self.assertEqual(tomllib.loads(path.read_text()), settings)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
