"""
This is a test script for the database packages. 
It tests the functions in the user, seed and picture modules.
"""

import unittest
import os
from unittest.mock import MagicMock

import datastore.db.__init__ as db
from datastore.db.metadata import validator
from nachet.db.queries import seed

NACHET_DB_URL = os.getenv("NACHET_DB_URL")
NACHET_DB_USER = os.getenv("NACHET_DB_USER")
NACHET_DB_PASSWORD = os.getenv("NACHET_DB_PASSWORD")
DB_CONNECTION_STRING = f"postgresql://{NACHET_DB_USER}:{NACHET_DB_PASSWORD}@{NACHET_DB_URL}"
if DB_CONNECTION_STRING is None or DB_CONNECTION_STRING == "":
    raise ValueError("NACHET_DB_URL_TESTING is not set")

DB_SCHEMA = os.environ.get("NACHET_SCHEMA_TESTING")
if DB_SCHEMA is None or DB_SCHEMA == "":
    raise ValueError("NACHET_SCHEMA_TESTING is not set")


# --------------------  SEED FUNCTIONS --------------------
class test_seed_functions(unittest.TestCase):
    def setUp(self):
        self.con = db.connect_db(DB_CONNECTION_STRING, DB_SCHEMA)
        self.cursor = db.cursor(self.con)
        db.create_search_path(self.con, self.cursor, DB_SCHEMA)
        self.seed_name = "test-name"

    def tearDown(self):
        self.con.rollback()
        db.end_query(self.con, self.cursor)

    def test_get_all_seeds_names(self):
        """
        This test checks if the get_all_seeds_names function returns a list of seeds
        with at least the one seed we added
        """
        seed.new_seed(self.cursor, self.seed_name)
        seeds = seed.get_all_seeds_names(self.cursor)

        self.assertNotEqual(len(seeds), 0)
        self.assertIn((self.seed_name,), seeds)

    def test_get_all_seeds_names_error(self):
        """
        This test checks if the get_all_seeds_names function raises an exception when the connection fails
        """
        mock_cursor = MagicMock()
        mock_cursor.fetchall.side_effect = Exception("Connection error")
        with self.assertRaises(Exception):
            seed.get_all_seeds_names(mock_cursor)

    def test_get_seed_id(self):
        """
        This test checks if the get_seed_id function returns the correct UUID
        """
        seed_uuid = seed.new_seed(self.cursor, self.seed_name)
        fetch_id = seed.get_seed_id(self.cursor, self.seed_name)

        self.assertTrue(validator.is_valid_uuid(fetch_id))
        self.assertEqual(seed_uuid, fetch_id)

    def test_get_nonexistant_seed_id(self):
        """
        This test checks if the get_seed_id function raises an exception when the seed does not exist
        """
        with self.assertRaises(seed.SeedNotFoundError):
            seed.get_seed_id(self.cursor, "nonexistant_seed")

    def test_get_seed_id_error(self):
        """
        This test checks if the get_seed_id function raises an exception when the connection fails
        """
        seed.new_seed(self.cursor, self.seed_name)
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = Exception("Connection error")
        with self.assertRaises(Exception):
            seed.get_seed_id(mock_cursor, self.seed_name)

    def test_new_seed(self):
        """
        This test checks if the new_seed function returns a valid UUID
        """
        seed_id = seed.new_seed(self.cursor, self.seed_name)

        self.assertTrue(validator.is_valid_uuid(seed_id))

    def test_new_seed_error(self):
        """
        This test checks if the new_seed function raises an exception when the connection fails
        """
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = Exception("Connection error")
        with self.assertRaises(seed.SeedCreationError):
            seed.new_seed(mock_cursor, self.seed_name)

    def test_is_seed_registered(self):
        """
        This test checks if the is_seed_registered function returns the correct value
        for a seed that is not yet registered and one that is.
        """
        self.assertFalse(
            seed.is_seed_registered(self.cursor, self.seed_name),
            "The seed should not already be registered",
        )

        seed.new_seed(self.cursor, self.seed_name)

        self.assertTrue(
            seed.is_seed_registered(self.cursor, self.seed_name),
            "The seed should be registered",
        )

    def test_is_seed_registered_error(self):
        """
        This test checks if the is_seed_registered function raises an exception when the connection fails
        """
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = Exception("Connection error")
        with self.assertRaises(Exception):
            seed.is_seed_registered(mock_cursor, self.seed_name)
