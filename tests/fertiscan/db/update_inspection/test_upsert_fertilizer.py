import os
import unittest

from dotenv import load_dotenv

import datastore.db.__init__ as db
from datastore.db.queries import user, picture
from datastore.db.metadata import picture_set
from fertiscan.db.queries import inspection, organization, label

load_dotenv()

# Fetch database connection URL and schema from environment variables
DB_CONNECTION_STRING = os.environ.get("FERTISCAN_DB_URL")
if DB_CONNECTION_STRING is None or DB_CONNECTION_STRING == "":
    raise ValueError("FERTISCAN_DB_URL is not set")

DB_SCHEMA = os.environ.get("FERTISCAN_SCHEMA_TESTING")
if DB_SCHEMA is None or DB_SCHEMA == "":
    raise ValueError("FERTISCAN_SCHEMA_TESTING is not set")


class TestUpsertFertilizerFunction(unittest.TestCase):
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

        self.label_info_id = label.new_label_information(
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

        # Insert an inspection record
        self.inspection_id = inspection.new_inspection(
            self.cursor, self.inspector_id, None, False
        )

        self.organization_id = organization.new_organization(
            cursor=self.cursor,
            name="Test Organization",
            address="123 Test St.",
            website="www.test.com",
            phone_number="123-456-7890",
        )

    def tearDown(self):
        # Rollback any changes to leave the database state as it was before the test
        self.conn.rollback()
        db.end_query(self.conn, self.cursor)

    def test_insert_new_fertilizer(self):
        fertilizer_name = "Test Fertilizer"
        registration_number = "T12345"
        owner_id = self.organization_id
        latest_inspection_id = self.inspection_id  # Use the pre-inserted inspection ID

        # Insert new fertilizer
        self.cursor.execute(
            "SELECT upsert_fertilizer(%s, %s, %s, %s);",
            (fertilizer_name, registration_number, owner_id, latest_inspection_id),
        )
        fertilizer_id = self.cursor.fetchone()[0]

        # Assertions to verify insertion
        self.assertIsNotNone(fertilizer_id, "New fertilizer ID should not be None")

        # Verify that the data is correctly saved
        self.cursor.execute(
            "SELECT name, registration_number, main_contact_id, latest_inspection_id FROM fertilizer WHERE id = %s;",
            (fertilizer_id,),
        )
        saved_fertilizer_data = self.cursor.fetchone()
        self.assertIsNotNone(
            saved_fertilizer_data, "Saved fertilizer data should not be None"
        )
        self.assertEqual(
            saved_fertilizer_data[0],
            fertilizer_name,
            "Name should match the inserted value",
        )
        self.assertEqual(
            saved_fertilizer_data[1],
            registration_number,
            "Registration number should match the inserted value",
        )
        self.assertEqual(
            saved_fertilizer_data[2],
            owner_id,
            "Owner ID should match the inserted value",
        )
        self.assertEqual(
            saved_fertilizer_data[3],
            latest_inspection_id,
            "Latest inspection ID should match the inserted value",
        )

    def test_update_existing_fertilizer(self):
        fertilizer_name = "Test Fertilizer"
        registration_number = "T12345"
        owner_id = self.organization_id
        latest_inspection_id = self.inspection_id

        # Insert new fertilizer to get a valid fertilizer_id
        self.cursor.execute(
            "SELECT upsert_fertilizer(%s, %s, %s, %s);",
            (fertilizer_name, registration_number, owner_id, latest_inspection_id),
        )
        fertilizer_id = self.cursor.fetchone()[0]

        # Update the fertilizer information
        updated_registration_number = "T67890"

        self.cursor.execute(
            "SELECT upsert_fertilizer(%s, %s, %s, %s);",
            (
                fertilizer_name,
                updated_registration_number,
                owner_id,
                latest_inspection_id,
            ),
        )
        updated_fertilizer_id = self.cursor.fetchone()[0]

        # Assertions to verify update
        self.assertEqual(
            fertilizer_id,
            updated_fertilizer_id,
            "Fertilizer ID should remain the same after update",
        )

        # Verify that the data is correctly updated
        self.cursor.execute(
            "SELECT name, registration_number, main_contact_id, latest_inspection_id FROM fertilizer WHERE id = %s;",
            (updated_fertilizer_id,),
        )
        updated_fertilizer_data = self.cursor.fetchone()
        self.assertIsNotNone(
            updated_fertilizer_data, "Updated fertilizer data should not be None"
        )
        self.assertEqual(
            updated_fertilizer_data[1],
            updated_registration_number,
            "Registration number should match the updated value",
        )
        self.assertEqual(
            updated_fertilizer_data[3],
            latest_inspection_id,
            "Latest inspection ID should remain unchanged",
        )


if __name__ == "__main__":
    unittest.main()
