import json
import os
import unittest
import uuid

import psycopg
from dotenv import load_dotenv

load_dotenv()

DB_CONNECTION_STRING = os.environ.get("FERTISCAN_DB_URL")
if not DB_CONNECTION_STRING:
    raise ValueError("FERTISCAN_DB_URL is not set")

DB_SCHEMA = os.environ.get("FERTISCAN_SCHEMA_TESTING")
if not DB_SCHEMA:
    raise ValueError("FERTISCAN_SCHEMA_TESTING is not set")

INPUT_JSON_PATH = "tests/fertiscan/inspection.json"


class TestDeleteInspectionFunction(unittest.TestCase):
    def setUp(self):
        # Set up database connection and cursor
        self.conn = psycopg.connect(
            DB_CONNECTION_STRING, options=f"-c search_path={DB_SCHEMA},public"
        )
        self.conn.autocommit = False
        self.cursor = self.conn.cursor()

        # Insert an inspector user into the users table and retrieve the inspector_id
        self.cursor.execute(
            """
            INSERT INTO users (email)
            VALUES ('inspector@example.com')
            RETURNING id;
            """
        )
        self.inspector_id = self.cursor.fetchone()[0]

        # Load the JSON data for creating a new inspection
        with open(INPUT_JSON_PATH, "r") as file:
            create_input_json = json.load(file)

        create_input_json_str = json.dumps(create_input_json)

        # Create initial inspection data using the new_inspection function
        self.cursor.execute(
            "SELECT new_inspection(%s, %s, %s);",
            (self.inspector_id, None, create_input_json_str),
        )
        inspection_data = self.cursor.fetchone()[0]  # Get the returned JSON

        self.inspection_id = inspection_data["inspection_id"]
        self.label_info_id = inspection_data["product"]["label_id"]
        # self.company_info_id = inspection_data["company"]["id"]
        # self.manufacturer_info_id = inspection_data["manufacturer"]["id"]

        # Update the inspection to verified true
        inspection_data["verified"] = True
        updated_inspection_json = json.dumps(inspection_data)

        self.cursor.execute(
            "SELECT update_inspection(%s, %s, %s);",
            (self.inspection_id, self.inspector_id, updated_inspection_json),
        )

    def tearDown(self):
        self.conn.rollback()
        self.cursor.close()
        self.conn.close()

    def test_delete_inspection_success(self):
        # Call the delete_inspection function and get the returned inspection record
        self.cursor.execute(
            "SELECT delete_inspection(%s, %s);",
            (self.inspection_id, self.inspector_id),
        )
        deleted_inspection = self.cursor.fetchone()[0]

        # Validate that the returned inspection record matches the expected data
        self.assertIsNotNone(
            deleted_inspection, "Deleted inspection should be returned."
        )
        self.assertEqual(
            deleted_inspection["id"],
            str(self.inspection_id),
            "Inspection ID should match.",
        )
        self.assertEqual(
            deleted_inspection["inspector_id"],
            str(self.inspector_id),
            "Inspector ID should match.",
        )

        # Verify that the inspection record was deleted
        self.cursor.execute(
            "SELECT COUNT(*) FROM inspection WHERE id = %s;",
            (self.inspection_id,),
        )
        inspection_count = self.cursor.fetchone()[0]
        self.assertEqual(inspection_count, 0, "Inspection should be deleted.")

        # Verify that the related sample was deleted
        self.cursor.execute(
            "SELECT COUNT(*) FROM sample WHERE id = %s;",
            (deleted_inspection["sample_id"],),
        )
        sample_count = self.cursor.fetchone()[0]
        self.assertEqual(sample_count, 0, "Sample should be deleted.")

        # Verify that related fertilizer information was deleted
        self.cursor.execute(
            "SELECT COUNT(*) FROM fertilizer WHERE latest_inspection_id = %s;",
            (self.inspection_id,),
        )
        sample_count = self.cursor.fetchone()[0]
        self.assertEqual(sample_count, 0, "Sample should be deleted.")

        # Verify that the label information was deleted
        self.cursor.execute(
            "SELECT COUNT(*) FROM label_information WHERE id = %s;",
            (self.label_info_id,),
        )
        label_count = self.cursor.fetchone()[0]
        self.assertEqual(label_count, 0, "Label information should be deleted.")

        # Verify that the related metrics were deleted
        self.cursor.execute(
            "SELECT COUNT(*) FROM metric WHERE label_id = %s;",
            (self.label_info_id,),
        )
        metric_count = self.cursor.fetchone()[0]
        self.assertEqual(metric_count, 0, "Metrics should be deleted.")

        # Verify that the related specifications were deleted
        self.cursor.execute(
            "SELECT COUNT(*) FROM specification WHERE label_id = %s;",
            (self.label_info_id,),
        )
        specification_count = self.cursor.fetchone()[0]
        self.assertEqual(specification_count, 0, "Specifications should be deleted.")

        # Verify that the related sub-labels were deleted
        self.cursor.execute(
            "SELECT COUNT(*) FROM sub_label WHERE label_id = %s;",
            (self.label_info_id,),
        )
        sub_label_count = self.cursor.fetchone()[0]
        self.assertEqual(sub_label_count, 0, "Sub-labels should be deleted.")

        # Verify that the related micronutrients were deleted
        self.cursor.execute(
            "SELECT COUNT(*) FROM micronutrient WHERE label_id = %s;",
            (self.label_info_id,),
        )
        micronutrient_count = self.cursor.fetchone()[0]
        self.assertEqual(micronutrient_count, 0, "Micronutrients should be deleted.")

        # Verify that the related guaranteed records were deleted
        self.cursor.execute(
            "SELECT COUNT(*) FROM guaranteed WHERE label_id = %s;",
            (self.label_info_id,),
        )
        guaranteed_count = self.cursor.fetchone()[0]
        self.assertEqual(guaranteed_count, 0, "Guaranteed records should be deleted.")

        # Verify that the related ingredients were deleted
        self.cursor.execute(
            "SELECT COUNT(*) FROM ingredient WHERE label_id = %s;",
            (self.label_info_id,),
        )
        ingredient_count = self.cursor.fetchone()[0]
        self.assertEqual(ingredient_count, 0, "Ingredients should be deleted.")

    def test_delete_inspection_unauthorized(self):
        # Generate a random UUID to simulate an unauthorized inspector
        unauthorized_inspector_id = str(uuid.uuid4())

        # Attempt to delete the inspection with a different inspector
        with self.assertRaises(psycopg.errors.RaiseException) as context:
            self.cursor.execute(
                "SELECT delete_inspection(%s, %s);",
                (
                    self.inspection_id,
                    unauthorized_inspector_id,
                ),  # Using a random UUID as unauthorized inspector ID
            )

        # Check that the exception message indicates unauthorized access
        self.assertIn(
            f"Inspector {unauthorized_inspector_id} is not the creator of inspection {self.inspection_id}",
            str(context.exception),
        )


if __name__ == "__main__":
    unittest.main()
