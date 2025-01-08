import os
import unittest

import psycopg
from dotenv import load_dotenv

load_dotenv()

# Database connection and schema settings
DB_CONNECTION_STRING = os.environ.get("FERTISCAN_DB_URL")
if not DB_CONNECTION_STRING:
    raise ValueError("FERTISCAN_DB_URL is not set")

DB_SCHEMA = os.environ.get("FERTISCAN_SCHEMA_TESTING")
if not DB_SCHEMA:
    raise ValueError("FERTISCAN_SCHEMA_TESTING is not set")


class TestDeleteOrganizationInformationFunction(unittest.TestCase):
    def setUp(self):
        # Set up database connection and cursor
        self.conn = psycopg.connect(
            DB_CONNECTION_STRING, options=f"-c search_path={DB_SCHEMA},public"
        )
        self.conn.autocommit = False  # Control transaction manually
        self.cursor = self.conn.cursor()

        # Insert a location record for testing
        self.cursor.execute(
            """
            INSERT INTO location (name, address, region_id)
            VALUES ('Test Location', '123 Test St', NULL)
            RETURNING id;
            """
        )
        self.location_id = self.cursor.fetchone()[0]

        # Insert an organization information record for testing
        self.cursor.execute(
            """
            INSERT INTO organization_information (name, location_id)
            VALUES ('Test Organization', %s)
            RETURNING id;
            """,
            (self.location_id,),
        )
        self.organization_information_id = self.cursor.fetchone()[0]

    def tearDown(self):
        # Roll back any changes to maintain database state
        self.conn.rollback()
        self.cursor.close()
        self.conn.close()

    def test_delete_organization_information_success(self):
        # Delete the organization information
        self.cursor.execute(
            """
            DELETE FROM organization_information
            WHERE id = %s;
            """,
            (self.organization_information_id,),
        )

        # Verify that the organization information was deleted
        self.cursor.execute(
            """
            SELECT COUNT(*)
            FROM organization_information
            WHERE id = %s;
            """,
            (self.organization_information_id,),
        )
        organization_count = self.cursor.fetchone()[0]
        self.assertEqual(
            organization_count, 0, "Organization information should be deleted."
        )

        # Verify that the associated location was also deleted
        self.cursor.execute(
            """
            SELECT COUNT(*)
            FROM location
            WHERE id = %s;
            """,
            (self.location_id,),
        )
        location_count = self.cursor.fetchone()[0]
        self.assertEqual(location_count, 0, "Associated location should be deleted.")

    def test_delete_organization_information_with_linked_records(self):
        # Insert an organization that links to the organization_information
        self.cursor.execute(
            """
            INSERT INTO organization (information_id, main_location_id)
            VALUES (%s, %s)
            RETURNING id;
            """,
            (self.organization_information_id, self.location_id),
        )
        _ = self.cursor.fetchone()[0]

        # Attempt to delete the organization information and expect a foreign key violation
        with self.assertRaises(psycopg.errors.ForeignKeyViolation) as _:
            self.cursor.execute(
                """
                DELETE FROM organization_information
                WHERE id = %s;
                """,
                (self.organization_information_id,),
            )

    def test_delete_organization_information_with_shared_location(self):
        # Insert another organization information that shares the same location
        self.cursor.execute(
            """
            INSERT INTO organization_information (name, location_id)
            VALUES ('Another Test Organization', %s)
            RETURNING id;
            """,
            (self.location_id,),
        )
        another_organization_information_id = self.cursor.fetchone()[0]

        # Delete the first organization information
        self.cursor.execute(
            """
            DELETE FROM organization_information
            WHERE id = %s;
            """,
            (self.organization_information_id,),
        )

        # Verify that the first organization information was deleted
        self.cursor.execute(
            """
            SELECT COUNT(*)
            FROM organization_information
            WHERE id = %s;
            """,
            (self.organization_information_id,),
        )
        organization_count = self.cursor.fetchone()[0]
        self.assertEqual(
            organization_count,
            0,
            "The first organization information should be deleted.",
        )

        # Verify that the location was not deleted since it is still referenced by the second organization information
        self.cursor.execute(
            """
            SELECT COUNT(*)
            FROM location
            WHERE id = %s;
            """,
            (self.location_id,),
        )
        location_count = self.cursor.fetchone()[0]
        self.assertEqual(
            location_count,
            1,
            "The location should not be deleted because it is still referenced.",
        )

        # Verify that the second organization information still exists
        self.cursor.execute(
            """
            SELECT COUNT(*)
            FROM organization_information
            WHERE id = %s;
            """,
            (another_organization_information_id,),
        )
        another_organization_count = self.cursor.fetchone()[0]
        self.assertEqual(
            another_organization_count,
            1,
            "The second organization information should still exist.",
        )


if __name__ == "__main__":
    unittest.main()
