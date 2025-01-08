import asyncio
import json
import os
import unittest

from dotenv import load_dotenv

import datastore.db.__init__ as db
from fertiscan import get_full_inspection_json
from fertiscan.db.metadata.inspection import Inspection
from fertiscan.db.queries.inspection import update_inspection

load_dotenv()

# Constants for test configuration
DB_CONNECTION_STRING = os.environ.get("FERTISCAN_DB_URL")
if not DB_CONNECTION_STRING:
    raise ValueError("FERTISCAN_DB_URL is not set")

DB_SCHEMA = os.environ.get("FERTISCAN_SCHEMA_TESTING")
if not DB_SCHEMA:
    raise ValueError("FERTISCAN_SCHEMA_TESTING is not set")

TEST_INSPECTION_JSON_PATH = "tests/fertiscan/inspection.json"


class TestInspectionUpdatePythonFunction(unittest.TestCase):
    def setUp(self):
        # Connect to the PostgreSQL database with the specified schema
        self.conn = db.connect_db(DB_CONNECTION_STRING, DB_SCHEMA)
        self.cursor = db.cursor(self.conn)
        db.create_search_path(self.conn, self.cursor, DB_SCHEMA)

        # Create a user to act as inspector
        self.cursor.execute(
            """
            INSERT INTO users (email) 
            VALUES (%s)
            ON CONFLICT (email) DO UPDATE 
            SET email = EXCLUDED.email 
            RETURNING id;
            """,
            ("inspector@example.com",),
        )
        self.inspector_id = self.cursor.fetchone()[0]

        # Load the JSON data for creating a new inspection
        with open(TEST_INSPECTION_JSON_PATH, "r") as file:
            create_input_json = json.load(file)

        create_input_json_str = json.dumps(create_input_json)

        # Create initial inspection data in the database
        self.picture_set_id = None
        self.cursor.execute(
            "SELECT new_inspection(%s, %s, %s);",
            (self.inspector_id, self.picture_set_id, create_input_json_str),
        )
        self.created_data = self.cursor.fetchone()[0]
        self.created_inspection = Inspection.model_validate(self.created_data)

        # Store the inspection ID for later use
        self.inspection_id = str(self.created_data.get("inspection_id"))

    def tearDown(self):
        # Roll back any changes to maintain database state
        self.conn.rollback()
        self.cursor.close()
        self.conn.close()

    def test_python_function_update_inspection_with_verified_false(self):
        # Create a model copy and update fields directly via the model
        altered_inspection = self.created_inspection.model_copy()
        new_value = 66.6

        # Update model fields instead of dictionary keys
        altered_inspection.organizations[0].name = "Updated Company Name"
        altered_inspection.product.metrics.weight[0].value = new_value
        altered_inspection.product.metrics.density.value = new_value
        altered_inspection.guaranteed_analysis.en[0].value = new_value
        altered_inspection.verified = False  # Ensure verified is false

        # Use the updated model for the update
        update_inspection(
            self.cursor,
            self.inspection_id,
            self.inspector_id,
            altered_inspection.model_dump(),
        )

        # Fetch the updated inspection data from the database using asyncio
        task = get_full_inspection_json(self.cursor, self.inspection_id)
        updated_inspection = asyncio.run(task)
        updated_inspection = json.loads(updated_inspection)
        print(updated_inspection)
        updated_inspection = Inspection.model_validate(updated_inspection)

        # Assertions using the Inspection model
        self.assertEqual(
            updated_inspection.organizations[0].name,
            "Updated Company Name",
            "The company name should reflect the update.",
        )
        self.assertEqual(
            updated_inspection.product.metrics.weight[0].value,
            new_value,
            "The weight metric should reflect the updated value.",
        )
        self.assertEqual(
            updated_inspection.product.metrics.density.value,
            new_value,
            "The density metric should reflect the updated value.",
        )
        self.assertEqual(
            updated_inspection.guaranteed_analysis.en[0].value,
            new_value,
            "The guaranteed analysis value should reflect the updated amount.",
        )

        # Verify that no fertilizer record was created
        self.cursor.execute(
            "SELECT COUNT(*) FROM fertilizer WHERE latest_inspection_id = %s;",
            (self.inspection_id,),
        )
        fertilizer_count = self.cursor.fetchone()[0]
        self.assertEqual(
            fertilizer_count,
            0,
            "No fertilizer should be created when verified is false.",
        )

    def test_python_function_update_inspection_with_verified_true(self):
        # Create a model copy and update the verified status via the model
        altered_inspection = self.created_inspection.model_copy()
        altered_inspection.verified = True

        # Use the updated model for the update
        update_inspection(
            self.cursor,
            self.inspection_id,
            self.inspector_id,
            altered_inspection.model_dump(),
        )

        # Fetch the updated inspection data from the database using asyncio
        task = get_full_inspection_json(self.cursor, self.inspection_id)
        updated_inspection = asyncio.run(task)
        updated_inspection = json.loads(updated_inspection)
        updated_inspection = Inspection.model_validate(updated_inspection)

        # Assertions using the Inspection model
        self.assertTrue(
            updated_inspection.verified,
            "The verified status should be True as updated.",
        )

        self.cursor.execute(
            "SELECT id FROM fertilizer WHERE latest_inspection_id = %s;",
            (self.inspection_id,),
        )
        fertilizer_id = self.cursor.fetchone()
        self.assertIsNotNone(
            fertilizer_id, "A fertilizer record should have been created."
        )


if __name__ == "__main__":
    unittest.main()
