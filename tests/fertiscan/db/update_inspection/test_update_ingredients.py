import json
import os
import unittest

from dotenv import load_dotenv

import datastore.db.__init__ as db
import fertiscan.db.queries.label as label

load_dotenv()

# Fetch database connection URL and schema from environment variables
DB_CONNECTION_STRING = os.environ.get("FERTISCAN_DB_URL")
if DB_CONNECTION_STRING is None or DB_CONNECTION_STRING == "":
    raise ValueError("FERTISCAN_DB_URL is not set")

DB_SCHEMA = os.environ.get("FERTISCAN_SCHEMA_TESTING")
if DB_SCHEMA is None or DB_SCHEMA == "":
    raise ValueError("FERTISCAN_SCHEMA_TESTING is not set")


class TestUpdateIngredientsFunction(unittest.TestCase):
    def setUp(self):
        # Connect to the PostgreSQL database with the specified schema
        self.conn = db.connect_db(DB_CONNECTION_STRING, DB_SCHEMA)
        self.cursor = db.cursor(self.conn)
        db.create_search_path(self.conn, self.cursor, DB_SCHEMA)

        self.label_id = label.new_label_information(
            cursor=self.cursor,
            name="test-label",
            lot_number=None,
            npk=None,
            n=None,
            p=None,
            k=None,
            title_en=None,
            title_fr=None,
            is_minimal=False,
            record_keeping=False,
        )

        # Set up test data for ingredients
        self.sample_organic_ingredients = json.dumps(
            {
                "en": [
                    {"name": "Bone meal", "value": "5", "unit": "%"},
                    {"name": "Seaweed extract", "value": "3", "unit": "%"},
                ],
                "fr": [
                    {"name": "Farine d'os", "value": "5", "unit": "%"},
                    {"name": "Extrait d'algues", "value": "3", "unit": "%"},
                ],
            }
        )

        self.updated_organic_ingredients = json.dumps(
            {
                "en": [
                    {"name": "Bone meal", "value": "6", "unit": "%"},
                    {"name": "Seaweed extract", "value": "4", "unit": "%"},
                ],
                "fr": [
                    {"name": "Farine d'os", "value": "6", "unit": "%"},
                    {"name": "Extrait d'algues", "value": "4", "unit": "%"},
                ],
            }
        )

    def tearDown(self):
        # Rollback any changes to leave the database state as it was before the test
        self.conn.rollback()
        db.end_query(self.conn, self.cursor)

    def test_update_organic_ingredients(self):
        # Insert initial organic ingredients
        self.cursor.execute(
            "SELECT update_ingredients(%s, %s);",
            (self.label_id, self.sample_organic_ingredients),
        )

        # Verify that the data is correctly saved
        self.cursor.execute(
            "SELECT name, value, unit, language FROM ingredient WHERE label_id = %s;",
            (self.label_id,),
        )
        saved_data = self.cursor.fetchall()
        expected_data = [
            ("Bone meal", 5.0, "%", "en"),
            ("Seaweed extract", 3.0, "%", "en"),
            ("Farine d'os", 5.0, "%", "fr"),
            ("Extrait d'algues", 3.0, "%", "fr"),
        ]
        self.assertEqual(
            len(saved_data), 4, "There should be four organic ingredients inserted"
        )
        self.assertListEqual(
            saved_data, expected_data, "Saved data should match the expected values"
        )

        # Update organic ingredients
        self.cursor.execute(
            "SELECT update_ingredients(%s, %s);",
            (self.label_id, self.updated_organic_ingredients),
        )

        # Verify that the data is correctly updated
        self.cursor.execute(
            "SELECT name, value, unit, language FROM ingredient WHERE label_id = %s;",
            (self.label_id,),
        )
        updated_data = self.cursor.fetchall()
        expected_updated_data = [
            ("Bone meal", 6.0, "%", "en"),
            ("Seaweed extract", 4.0, "%", "en"),
            ("Farine d'os", 6.0, "%", "fr"),
            ("Extrait d'algues", 4.0, "%", "fr"),
        ]
        self.assertEqual(
            len(updated_data),
            4,
            "There should be four organic ingredients after update",
        )
        self.assertListEqual(
            updated_data,
            expected_updated_data,
            "Updated data should match the new values",
        )


if __name__ == "__main__":
    unittest.main()
