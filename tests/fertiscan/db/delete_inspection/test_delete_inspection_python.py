import json
import os
import unittest

from dotenv import load_dotenv
from psycopg import connect

from fertiscan.db.metadata.inspection import DBInspection
from fertiscan.db.queries.inspection import (
    delete_inspection,
    new_inspection_with_label_info,
)

load_dotenv()

# Constants for test configuration
TEST_DB_CONNECTION_STRING = os.environ.get("FERTISCAN_DB_URL")
if not TEST_DB_CONNECTION_STRING:
    raise ValueError("FERTISCAN_DB_URL is not set")

TEST_DB_SCHEMA = os.environ.get("FERTISCAN_SCHEMA_TESTING")
if not TEST_DB_SCHEMA:
    raise ValueError("FERTISCAN_SCHEMA_TESTING is not set")

TEST_INSPECTION_JSON_PATH = "tests/fertiscan/inspection.json"


class TestInspectionDeleteFunction(unittest.TestCase):
    def setUp(self):
        # Set up database connection and cursor
        self.conn = connect(
            TEST_DB_CONNECTION_STRING, options=f"-c search_path={TEST_DB_SCHEMA},public"
        )
        self.conn.autocommit = False
        self.cursor = self.conn.cursor()

        # Create a user to act as inspector
        self.cursor.execute(
            "INSERT INTO users (email) VALUES (%s) RETURNING id;",
            ("inspector@example.com",),
        )
        self.inspector_id = str(self.cursor.fetchone()[0])

        # Load the JSON data for creating a new inspection
        with open(TEST_INSPECTION_JSON_PATH, "r") as file:
            input_json = json.load(file)

        # Create a new inspection record with the input JSON data
        self.picture_set_id = None
        self.inspection_id = new_inspection_with_label_info(
            self.cursor, self.inspector_id, self.picture_set_id, json.dumps(input_json)
        )["inspection_id"]

    def tearDown(self):
        self.conn.rollback()
        self.cursor.close()
        self.conn.close()

    def test_delete_inspection(self):
        deleted_inspection = delete_inspection(
            self.cursor, self.inspection_id, self.inspector_id
        )
        deleted_inspection = DBInspection.model_validate(deleted_inspection)

        # Check if the returned object is a DBInspection instance
        self.assertIsInstance(deleted_inspection, DBInspection)

        # Verify that the inspection ID matches the one we deleted
        self.assertEqual(str(deleted_inspection.id), self.inspection_id)

        # Ensure that the inspection no longer exists in the database
        self.cursor.execute(
            "SELECT EXISTS(SELECT 1 FROM inspection WHERE id = %s);",
            (self.inspection_id,),
        )
        inspection_exists = self.cursor.fetchone()[0]
        self.assertFalse(
            inspection_exists, "The inspection should be deleted from the database."
        )


if __name__ == "__main__":
    unittest.main()
