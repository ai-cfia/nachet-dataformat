import json
import os
import unittest

from dotenv import load_dotenv

import datastore.db.__init__ as db
from datastore.db.metadata import picture_set
from datastore.db.queries import user, picture
from fertiscan.db.queries import label
from fertiscan.db.metadata.inspection import (
    DBInspection,
    Inspection,
)
from fertiscan.db.queries.inspection import get_inspection_dict, update_inspection

load_dotenv()

# Database connection and schema settings
DB_CONNECTION_STRING = os.environ.get("FERTISCAN_DB_URL")
if not DB_CONNECTION_STRING:
    raise ValueError("FERTISCAN_DB_URL is not set")

DB_SCHEMA = os.environ.get("FERTISCAN_SCHEMA_TESTING")
if not DB_SCHEMA:
    raise ValueError("FERTISCAN_SCHEMA_TESTING is not set")

INPUT_JSON_PATH = "tests/fertiscan/inspection.json"


class TestUpdateInspectionFunction(unittest.TestCase):
    def setUp(self):
        # Connect to the PostgreSQL database with the specified schema
        self.conn = db.connect_db(DB_CONNECTION_STRING, DB_SCHEMA)
        self.cursor = db.cursor(self.conn)
        db.create_search_path(self.conn, self.cursor, DB_SCHEMA)

        self.user_email = "test-update-inspection@email"
        self.inspector_id = user.register_user(self.cursor, self.user_email)
        self.folder_name = "test-folder"
        self.picture_set = picture_set.build_picture_set_metadata(self.inspector_id, 1)
        self.picture_set_id = picture.new_picture_set(
            self.cursor, self.picture_set, self.inspector_id, self.folder_name
        )

        self.F = label.new_label_information(
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

        self.cursor.execute(
            "INSERT INTO users (email) VALUES ('other_user@example.com') RETURNING id;"
        )
        self.other_user_id = self.cursor.fetchone()[0]

        # Load the JSON data for creating a new inspection
        with open(INPUT_JSON_PATH, "r") as file:
            create_input_json = json.load(file)

        create_input_json_str = json.dumps(create_input_json)
        #print(create_input_json["organizations"])

        # Create initial inspection data in the database
        self.picture_set_id = None  # No picture set ID for this test case
        self.cursor.execute(
            "SELECT new_inspection(%s, %s, %s);",
            (self.inspector_id, self.picture_set_id, create_input_json_str),
        )
        self.created_data = self.cursor.fetchone()[0]
        #print(self.created_data["organizations"])
        self.created_inspection = Inspection.model_validate(self.created_data)

        # Store the inspection ID for later use
        self.inspection_id = self.created_data.get("inspection_id")

    def tearDown(self):
        # Roll back any changes to maintain database state
        self.conn.rollback()
        db.end_query(self.conn, self.cursor)

    def test_update_inspection_with_verified_false(self):
        # Update the JSON data for testing the update function
        altered_inspection = self.created_inspection.model_copy()

        # Prepare updated values for fields
        new_value = 66.3
        inspection_comment = "Updated feedback for inspection."
        company_name = "Updated Company Name"

        # Update the inspection model fields using model-style updates
        altered_inspection.organizations[0].name = company_name
        altered_inspection.product.metrics.weight[0].value = new_value
        altered_inspection.product.metrics.density.value = new_value
        altered_inspection.guaranteed_analysis.en[0].value = new_value
        altered_inspection.verified = False  # Ensure verified is false
        altered_inspection.inspection_comment = inspection_comment

        # Use the updated model for the update
        update_inspection_result = update_inspection(
            self.cursor,
            self.inspection_id,
            self.inspector_id,
            altered_inspection.model_dump(),
        )
        print(update_inspection_result)
        Inspection.model_validate(update_inspection_result)

        # Verify the inspection record was updated in the database
        updated_inspection = get_inspection_dict(self.cursor, self.inspection_id)
        updated_inspection = DBInspection.model_validate(updated_inspection)
        self.assertIsNotNone(updated_inspection, "The inspection record should exist.")
        self.assertEqual(
            str(updated_inspection.id),
            str(self.inspection_id),
            "The inspection ID should match the expected value.",
        )
        self.assertEqual(
            str(updated_inspection.inspector_id),
            str(self.inspector_id),
            "The inspector ID should match the expected value.",
        )
        self.assertFalse(
            updated_inspection.verified,
            "The verified status should be False as updated.",
        )
        self.assertEqual(
            updated_inspection.inspection_comment,
            inspection_comment,
            "The user feedback should be updated.",
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
        # Verify the company name was updated in the database
        self.cursor.execute(
            "SELECT name FROM organization_information where id=%s;",
            (self.created_data["organizations"][0]["id"],),
        )
        updated_company_name = self.cursor.fetchone()[0]
        self.assertEqual(
            updated_company_name,
            "Updated Company Name",
            "The company name should reflect the update.",
        )

        # Verify the metrics were updated
        self.cursor.execute(
            "SELECT value FROM metric WHERE label_id = %s AND metric_type = %s;",
            (self.created_data["product"]["label_id"], "weight"),
        )
        updated_weight_metric = self.cursor.fetchone()[0]
        self.assertEqual(
            updated_weight_metric,
            new_value,
            "The weight metric should reflect the updated value.",
        )

        self.cursor.execute(
            "SELECT value FROM metric WHERE label_id = %s AND metric_type = %s;",
            (self.created_data["product"]["label_id"], "density"),
        )
        updated_density_metric = self.cursor.fetchone()[0]
        self.assertEqual(
            updated_density_metric,
            new_value,
            "The density metric should reflect the updated value.",
        )

        # Verify the guaranteed analysis value was updated
        self.cursor.execute(
            "SELECT value FROM guaranteed WHERE label_id = %s AND read_name = %s;",
            (self.created_data["product"]["label_id"], "Total Nitrogen (N)"),
        )
        #print(self.created_data["product"]["label_id"])
        updated_nitrogen_value = self.cursor.fetchone()[0]
        #print(updated_nitrogen_value)
        self.assertEqual(
            updated_nitrogen_value,
            new_value,
            "The guaranteed analysis value for Total Nitrogen (N) should reflect the updated amount.",
        )

    def test_update_inspection_with_verified_true(self):
        # Update the inspection model for testing the update function
        altered_inspection = self.created_inspection.model_copy()

        # Prepare updated values for fields
        altered_inspection.verified = True  # Set verified to true

        # Use the updated model for the update
        update_inspection(
            self.cursor,
            self.inspection_id,
            self.inspector_id,
            altered_inspection.model_dump(),
        )

        # Verify the inspection record was updated in the database
        updated_inspection = get_inspection_dict(self.cursor, self.inspection_id)
        updated_inspection = DBInspection.model_validate(updated_inspection)

        self.assertIsNotNone(updated_inspection, "The inspection record should exist.")
        self.assertEqual(
            str(updated_inspection.id),
            str(self.inspection_id),
            "The inspection ID should match the expected value.",
        )
        self.assertEqual(
            updated_inspection.inspector_id,
            self.inspector_id,
            "The inspector ID should match the expected value.",
        )
        self.assertTrue(
            updated_inspection.verified,
            "The verified status should be True as updated.",
        )

        # Verify that a fertilizer record was created
        self.cursor.execute(
            "SELECT id FROM fertilizer WHERE latest_inspection_id = %s;",
            (self.inspection_id,),
        )
        fertilizer_id = self.cursor.fetchone()[0]
        self.assertIsNotNone(
            fertilizer_id, "A fertilizer record should have been created."
        )

        # Verify the fertilizer details are correct
        self.cursor.execute(
            "SELECT name, registration_number, main_contact_id FROM fertilizer WHERE id = %s;",
            (fertilizer_id,),
        )
        fertilizer_data = self.cursor.fetchone()
        self.assertEqual(
            fertilizer_data[0],
            altered_inspection.product.name,
            "The fertilizer name should match the product name in the input model.",
        )
        # self.assertEqual(
        #     fertilizer_data[1],
        #     altered_inspection.product.registration_number,
        #     "The registration number should match the input model.",
        # )

        # Check if the organization was created for the fertilizer
        self.cursor.execute(
            "SELECT id FROM organization WHERE name = %s;",
            (altered_inspection.organizations[0].name,),
        )
        organization_id = self.cursor.fetchone()[0]
        self.assertIsNotNone(
            organization_id, "An organization record should have been created."
        )

    def test_update_inspection_unauthorized_user(self):
        # Update the inspection model for testing the update function
        altered_inspection = self.created_inspection.model_copy()

        # Modify the company name in the inspection model
        altered_inspection.organizations[0].name = "Unauthorized Update"

        # Use a different inspector_id that is not associated with the inspection
        unauthorized_inspector_id = self.other_user_id

        # Attempt to invoke the update_inspection function with an unauthorized inspector_id
        with self.assertRaises(Exception):
            update_inspection(
                self.cursor,
                self.inspection_id,
                unauthorized_inspector_id,
                altered_inspection.model_dump(),
            )

    def test_update_inspection_without_organizations(self):
        # Update the inspection model with null company and manufacturer for testing
        altered_inspection = self.created_inspection.model_copy()
        altered_inspection.organizations = []  # orgs is empty
        altered_inspection.verified = False  # Ensure verified is false

        # Invoke the update_inspection function
        update_inspection(
            self.cursor,
            self.inspection_id,
            self.inspector_id,
            altered_inspection.model_dump(),
        )

        # Verify that the inspection record was updated
        updated_inspection = get_inspection_dict(self.cursor, self.inspection_id)
        updated_inspection = DBInspection.model_validate(updated_inspection)

        self.assertIsNotNone(updated_inspection, "The inspection record should exist.")
        self.assertEqual(
            updated_inspection.inspector_id,
            self.inspector_id,
            "The inspector ID should match the expected value.",
        )
        self.assertFalse(
            updated_inspection.verified,
            "The verified status should be False as updated.",
        )

        # Verify that no organization record was created for the null company or manufacturer
        self.cursor.execute(
            "SELECT COUNT(*) FROM organization WHERE name IS NULL;",
        )
        organization_count = self.cursor.fetchone()[0]
        self.assertEqual(
            organization_count,
            0,
            "No organization record should be created when organizations is empty.",
        )


if __name__ == "__main__":
    unittest.main()
