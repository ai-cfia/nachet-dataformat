import json
import os
import unittest

from dotenv import load_dotenv

import datastore.db.__init__ as db
import fertiscan.db.queries.sub_label as sub_label
import fertiscan.db.queries.label as label
from fertiscan.db.metadata.inspection import (
    Inspection,
    SubLabel,
)

load_dotenv()

# Fetch database connection URL and schema from environment variables
DB_CONNECTION_STRING = os.environ.get("FERTISCAN_DB_URL")
if DB_CONNECTION_STRING is None or DB_CONNECTION_STRING == "":
    raise ValueError("FERTISCAN_DB_URL is not set")

DB_SCHEMA = os.environ.get("FERTISCAN_SCHEMA_TESTING")
if DB_SCHEMA is None or DB_SCHEMA == "":
    raise ValueError("FERTISCAN_SCHEMA_TESTING is not set")


TEST_INPUT_JSON_PATH = "tests/fertiscan/inspection_export.json"


class TestUpdateSubLabelsFunction(unittest.TestCase):
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

        # Load and validate the inspection data from the JSON file using the Inspection model
        with open(TEST_INPUT_JSON_PATH) as f:
            inspection_data = json.load(f)
        inspection_data = Inspection.model_validate(inspection_data)

        # Set up test data for sub labels using the SubLabel Pydantic model
        self.sample_sub_labels = {
            "instructions": inspection_data.instructions.model_dump(),
            "cautions": inspection_data.cautions.model_dump(),
        }

        # Calculate the number of sub-labels for the initial insertion
        self.nb_sub_labels = len(inspection_data.instructions.en) + len(
            inspection_data.cautions.en
        )

        # Set up updated sub labels using the SubLabel Pydantic model
        self.updated_sub_labels = {
            "instructions": SubLabel(
                en=[
                    "1. Dissolve 50g in 10L of water.",
                    "2. Apply every 2 weeks.",
                    "3. Store in a cool place.",
                    "4. Test instruction.",
                    "5. Test instruction.",
                ],
                fr=[
                    "1. Dissoudre 50g dans 10L d'eau.",
                    "2. Appliquer toutes les 2 semaines.",
                    "3. Conserver dans un endroit frais.",
                    "4. Test instruction.",
                    "5. Test instruction.",
                ],
            ).model_dump(),
            "cautions": SubLabel(
                en=[
                    "Keep out of reach of children.",
                    "Avoid contact with skin and eyes.",
                    "If in eyes, rinse immediately.",
                    "Limited warranty of 1 year.",
                    "Test caution.",
                ],
                fr=[
                    "Tenir hors de portée des enfants.",
                    "Éviter le contact avec la peau et les yeux.",
                    "En cas de contact avec les yeux, rincer immédiatement.",
                    "Garantie limitée de 1 an.",
                    "Test caution.",
                ],
            ).model_dump(),
        }
        self.nb_updated = 10

    def tearDown(self):
        # Rollback any changes to leave the database state as it was before the test
        self.conn.rollback()
        db.end_query(self.conn, self.cursor)

    def test_update_sub_labels(self):
        # Insert initial sub labels
        self.cursor.execute(
            "SELECT update_sub_labels(%s, %s);",
            (self.label_id, json.dumps(self.sample_sub_labels)),
        )

        saved_data = sub_label.get_sub_label_json(self.cursor, self.label_id)
        nb_sub_labels = len(saved_data["instructions"]["en"]) + len(
            saved_data["cautions"]["en"]
        )

        self.assertEqual(
            nb_sub_labels,
            self.nb_sub_labels,
            f"There should be {self.nb_sub_labels} sub label records inserted",
        )

        # Update sub labels
        self.cursor.execute(
            "SELECT update_sub_labels(%s, %s);",
            (self.label_id, json.dumps(self.updated_sub_labels)),
        )

        # Verify that the data is correctly updated
        updated_data = sub_label.get_sub_label_json(self.cursor, self.label_id)
        nb_updated = len(updated_data["instructions"]["en"]) + len(
            updated_data["cautions"]["en"]
        )

        self.assertEqual(
            nb_updated,
            self.nb_updated,
            f"There should be {self.nb_updated} sub label records updated",
        )

    def test_update_sub_labels_with_mismatched_arrays(self):
        # Load the sub-labels from sample data
        instructions = self.sample_sub_labels["instructions"]

        # Remove the last item from 'fr' array
        instructions["fr"] = instructions["fr"][:-1]

        # Create mismatched sub-labels JSON, where 'fr' is shorter
        mismatched_sub_labels = json.dumps({"instructions": instructions})

        try:
            # Attempt to update the sub-labels in the database
            self.cursor.execute(
                "SELECT update_sub_labels(%s, %s);",
                (self.label_id, mismatched_sub_labels),
            )
        except Exception as e:
            self.fail(f"update_sub_labels raised an unexpected exception: {e}")

        # Retrieve the saved sub-label data from the database
        saved_data = sub_label.get_sub_label_json(self.cursor, self.label_id)
        saved_instructions = saved_data["instructions"]

        # Check that the 'fr' array was padded with an empty string
        self.assertEqual(
            len(saved_instructions["fr"]),
            len(
                instructions["en"]
            ),  # 'fr' should be padded to match the length of 'en'
            f"Mismatch in length of 'fr' array: expected {len(instructions['en'])}, got {len(saved_instructions['fr'])}.",
        )

        # Assert that the content in 'fr' is correctly padded with an empty string
        self.assertEqual(
            saved_instructions["fr"],
            instructions["fr"]
            + [""],  # Expecting the missing value replaced by an empty string
            f"Mismatch in 'fr' content: expected {instructions['fr'] + ['']}, got {saved_instructions['fr']}.",
        )

        # Assert that the 'en' array was not modified
        self.assertEqual(
            saved_instructions["en"],
            instructions["en"],
            f"Mismatch in 'en' content: expected {instructions['en']}, got {saved_instructions['en']}.",
        )

    def test_update_sub_labels_with_empty_arrays(self):
        # Test with empty 'fr' and 'en' arrays
        empty_sub_labels = json.dumps({"instructions": {"fr": [], "en": []}})

        try:
            # Execute the function with empty sub labels
            self.cursor.execute(
                "SELECT update_sub_labels(%s, %s);", (self.label_id, empty_sub_labels)
            )
        except Exception as e:
            self.fail(f"update_sub_labels raised an exception with empty arrays: {e}")

        # Verify that no new data was inserted
        self.cursor.execute(
            "SELECT text_content_fr, text_content_en FROM sub_label WHERE label_id = %s;",
            (self.label_id,),
        )
        saved_data_empty = self.cursor.fetchall()

        self.assertEqual(
            len(saved_data_empty),
            0,
            "No sub label records should be inserted when arrays are empty",
        )


if __name__ == "__main__":
    unittest.main()
