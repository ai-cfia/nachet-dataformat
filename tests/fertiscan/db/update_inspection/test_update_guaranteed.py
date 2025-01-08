import json
import os
import unittest

from dotenv import load_dotenv

import datastore.db.__init__ as db
import fertiscan.db.queries.label as label
import fertiscan.db.queries.nutrients as guaranteed
from fertiscan.db.metadata.inspection import GuaranteedAnalysis

load_dotenv()

# Fetch database connection URL and schema from environment variables
DB_CONNECTION_STRING = os.environ.get("FERTISCAN_DB_URL")
if DB_CONNECTION_STRING is None or DB_CONNECTION_STRING == "":
    raise ValueError("FERTISCAN_DB_URL is not set")

DB_SCHEMA = os.environ.get("FERTISCAN_SCHEMA_TESTING")
if DB_SCHEMA is None or DB_SCHEMA == "":
    raise ValueError("FERTISCAN_SCHEMA_TESTING is not set")


class TestUpdateGuaranteedFunction(unittest.TestCase):
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

        # Set up test data for guaranteed analysis
        with open("tests/fertiscan/inspection_export.json") as f:
            inspection_data = json.load(f)
        self.sample_guaranteed = json.dumps(inspection_data["guaranteed_analysis"])
        self.nb_guaranteed = len(inspection_data["guaranteed_analysis"]["en"]) + len(
            inspection_data["guaranteed_analysis"]["fr"]
        )
        self.updated_guaranteed = {
            "inspection": {
                "guaranteed_analysis": {
                    "en": [
                        {"name": "Total Nitrogen (N)", "value": 22, "unit": "%"},
                        {
                            "name": "Available Phosphate (P2O5)",
                            "value": 22,
                            "unit": "%",
                        },
                        {"name": "Soluble Potash (K2O)", "value": 22, "unit": "%"},
                    ],
                    "fr": [
                        {"name": "Total Nitrogen (N)", "value": 22, "unit": "%"},
                        {
                            "name": "Available Phosphate (P2O5)",
                            "value": 22,
                            "unit": "%",
                        },
                        {"name": "Soluble Potash (K2O)", "value": 22, "unit": "%"},
                    ],
                }
            }
        }

    def tearDown(self):
        # Rollback any changes to leave the database state as it was before the test
        self.conn.rollback()
        db.end_query(self.conn, self.cursor)

    def test_update_guaranteed(self):
        # Insert initial guaranteed analysis

        self.cursor.execute(
            "SELECT update_guaranteed(%s, %s);",
            (self.label_id, self.sample_guaranteed),
        )

        # Verify that the data is correctly saved
        basic_data = guaranteed.get_guaranteed_analysis_json(self.cursor, self.label_id)
        basic_data = GuaranteedAnalysis.model_validate(basic_data)
        self.assertEqual(
            len(basic_data.en) + len(basic_data.fr),
            self.nb_guaranteed,
            f"There should be {self.nb_guaranteed} guaranteed analysis records inserted",
        )

        # Update guaranteed analysis
        self.cursor.execute(
            "SELECT update_guaranteed(%s, %s);",
            (self.label_id, json.dumps(self.updated_guaranteed)),
        )

        # Verify that the data is correctly updated
        updated_data = guaranteed.get_guaranteed_analysis_json(
            self.cursor, self.label_id
        )
        updated_data = GuaranteedAnalysis.model_validate(updated_data)
        for value in updated_data.en:
            self.assertEqual(value.value, 22)


if __name__ == "__main__":
    unittest.main()
