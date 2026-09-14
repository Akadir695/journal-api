-- Runs once, the first time the Postgres volume is initialised.
--
-- The test suite refuses to run against any database whose name does not end
-- in _test (see tests/conftest.py), so it needs one of its own. Creating it
-- here means a clean clone can run the tests without any manual setup.
CREATE DATABASE journaldb_test;
