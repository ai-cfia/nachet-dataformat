import os
import unittest

import psycopg
from dotenv import load_dotenv


load_dotenv()

# Fetch database connection URL and schema from environment variables
DB_CONNECTION_STRING = os.environ.get("FERTISCAN_DB_URL")
if DB_CONNECTION_STRING is None or DB_CONNECTION_STRING == "":
    raise ValueError("FERTISCAN_DB_URL is not set")

DB_SCHEMA = os.environ.get("FERTISCAN_SCHEMA_TESTING")
if DB_SCHEMA is None or DB_SCHEMA == "":
    raise ValueError("FERTISCAN_SCHEMA_TESTING is not set")


class TestUpsertLocationFunction(unittest.TestCase):
    def setUp(self):
        # Connect to the PostgreSQL database with the specified schema
        self.conn = psycopg.connect(
            DB_CONNECTION_STRING, options=f"-c search_path={DB_SCHEMA},public"
        )
        self.conn.autocommit = False  # Ensure transaction is managed manually
        self.cursor = self.conn.cursor()

    def tearDown(self):
        # Rollback any changes to leave the database state as it was before the test
        self.conn.rollback()
        self.cursor.close()
        self.conn.close()

    def test_insert_new_location(self):
        sample_new_address = "123 New Blvd, Springfield IL 62701 USA"

        # Insert a new location
        self.cursor.execute(
            "SELECT upsert_location(%s, %s);", (None, sample_new_address)
        )
        new_location_result = self.cursor.fetchone()

        # Assertions
        self.assertIsNotNone(
            new_location_result, "New location result should not be None"
        )
        new_location_id = new_location_result[0]
        self.assertTrue(new_location_id, "New location ID should be present")

        # Verify that the data is correctly saved
        self.cursor.execute(
            "SELECT address FROM location WHERE id = %s;",
            (new_location_id,),
        )
        saved_data = self.cursor.fetchone()
        self.assertIsNotNone(saved_data, "Saved data should not be None")
        self.assertEqual(
            saved_data[0], sample_new_address, "Address should match the inserted value"
        )

    def test_update_existing_location(self):
        sample_new_address = "123 New Blvd, Springfield IL 62701 USA"
        sample_updated_address = "456 Updated Blvd, Springfield IL 62701 USA"

        # Insert a new location to update
        self.cursor.execute(
            "SELECT upsert_location(%s, %s);", (None, sample_new_address)
        )
        new_location_result = self.cursor.fetchone()
        new_location_id = new_location_result[0]

        # Update the location
        self.cursor.execute(
            "SELECT upsert_location(%s, %s);",
            (new_location_id, sample_updated_address),
        )
        updated_location_result = self.cursor.fetchone()

        # Assertions
        self.assertIsNotNone(
            updated_location_result, "Updated location result should not be None"
        )
        self.assertEqual(
            updated_location_result[0],
            new_location_id,
            "Location ID should remain the same after update",
        )

        # Verify that the data is correctly updated
        self.cursor.execute(
            "SELECT address FROM location WHERE id = %s;",
            (new_location_id,),
        )
        updated_data = self.cursor.fetchone()
        self.assertIsNotNone(updated_data, "Updated data should not be None")
        self.assertEqual(
            updated_data[0],
            sample_updated_address,
            "Address should match the updated value",
        )


if __name__ == "__main__":
    unittest.main()
