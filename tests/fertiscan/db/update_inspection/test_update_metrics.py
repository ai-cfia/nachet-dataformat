import os
import unittest

from dotenv import load_dotenv

import datastore.db.__init__ as db
import fertiscan.db.queries.label as label
from fertiscan.db.metadata.inspection import Metric, Metrics

load_dotenv()

# Fetch database connection URL and schema from environment variables
DB_CONNECTION_STRING = os.environ.get("FERTISCAN_DB_URL")
if DB_CONNECTION_STRING is None or DB_CONNECTION_STRING == "":
    raise ValueError("FERTISCAN_DB_URL is not set")

DB_SCHEMA = os.environ.get("FERTISCAN_SCHEMA_TESTING")
if DB_SCHEMA is None or DB_SCHEMA == "":
    raise ValueError("FERTISCAN_SCHEMA_TESTING is not set")


class TestUpdateMetricsFunction(unittest.TestCase):
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

        # Set up test data for metrics using Pydantic models
        self.sample_metrics = Metrics(
            weight=[Metric(value=5, unit="kg"), Metric(value=11, unit="lb")],
            density=Metric(value=1.2, unit="g/cm³"),
            volume=Metric(value=20.8, unit="L"),
        )

        self.updated_metrics = Metrics(
            weight=[Metric(value=6, unit="kg"), Metric(value=13, unit="lb")],
            density=Metric(value=1.3, unit="g/cm³"),
            volume=Metric(value=25.0, unit="L"),
        )

    def tearDown(self):
        # Rollback any changes to leave the database state as it was before the test
        self.conn.rollback()
        db.end_query(self.conn, self.cursor)

    def test_update_metrics(self):
        # Insert initial metrics using Pydantic model
        self.cursor.execute(
            "SELECT update_metrics(%s, %s);",
            (self.label_id, self.sample_metrics.model_dump_json()),
        )

        # Verify that the data is correctly saved
        self.cursor.execute(
            "SELECT value, unit_id FROM metric WHERE label_id = %s;",
            (self.label_id,),
        )
        saved_data = self.cursor.fetchall()
        expected_data = [
            (5.0, "kg"),  # weight kg
            (11.0, "lb"),  # weight lb
            (1.2, "g/cm³"),  # density
            (20.8, "L"),  # volume
        ]
        self.assertEqual(len(saved_data), 4, "There should be four metrics inserted")
        self.assertListEqual(
            [(d[0], self._get_unit_name(d[1])) for d in saved_data],
            expected_data,
            "Saved data should match the expected values",
        )

        # Update metrics using Pydantic model
        self.cursor.execute(
            "SELECT update_metrics(%s, %s);",
            (self.label_id, self.updated_metrics.model_dump_json()),
        )

        # Verify that the data is correctly updated
        self.cursor.execute(
            "SELECT value, unit_id FROM metric WHERE label_id = %s;",
            (self.label_id,),
        )
        updated_data = self.cursor.fetchall()
        expected_updated_data = [
            (6.0, "kg"),  # weight kg
            (13.0, "lb"),  # weight lb
            (1.3, "g/cm³"),  # density
            (25.0, "L"),  # volume
        ]
        self.assertEqual(
            len(updated_data), 4, "There should be four metrics after update"
        )
        self.assertListEqual(
            [(d[0], self._get_unit_name(d[1])) for d in updated_data],
            expected_updated_data,
            "Updated data should match the new values",
        )

    def _get_unit_name(self, unit_id):
        # Helper function to fetch the unit name by unit_id
        self.cursor.execute("SELECT unit FROM unit WHERE id = %s;", (unit_id,))
        return self.cursor.fetchone()[0]


if __name__ == "__main__":
    unittest.main()
