"""
This is a test script for the database packages.
It tests the functions in the organization module.
"""

import os
import unittest
import uuid

import json
import datastore.db as db
from datastore.db.metadata import validator
from fertiscan.db.metadata.inspection import OrganizationInformation
from fertiscan.db.queries import label, organization

DB_CONNECTION_STRING = os.environ.get("FERTISCAN_DB_URL")
if DB_CONNECTION_STRING is None or DB_CONNECTION_STRING == "":
    raise ValueError("FERTISCAN_DB_URL is not set")

DB_SCHEMA = os.environ.get("FERTISCAN_SCHEMA_TESTING")
if DB_SCHEMA is None or DB_SCHEMA == "":
    raise ValueError("FERTISCAN_SCHEMA_TESTING is not set")


class test_province(unittest.TestCase):
    def setUp(self):
        self.con = db.connect_db(DB_CONNECTION_STRING, DB_SCHEMA)
        self.cursor = self.con.cursor()
        db.create_search_path(self.con, self.cursor, DB_SCHEMA)

        self.name = "test-province"

    def tearDown(self):
        self.con.rollback()
        db.end_query(self.con, self.cursor)

    def test_new_province(self):
        province_id = organization.new_province(self.cursor, self.name)
        self.assertIsInstance(province_id, int)

    def test_get_province(self):
        province_id = organization.new_province(self.cursor, self.name)
        province_data = organization.get_province(self.cursor, province_id)
        self.assertEqual(province_data[0], self.name)

    def test_get_province_not_found(self):
        with self.assertRaises(organization.ProvinceNotFoundError):
            organization.get_province(self.cursor, 0)

    def test_get_all_province(self):
        province_id = organization.new_province(self.cursor, self.name)
        province_2_id = organization.new_province(self.cursor, "test-province-2")
        province_data = organization.get_all_province(self.cursor)
        self.assertEqual(len(province_data), 2)
        self.assertEqual(province_data[0][0], province_id)
        self.assertEqual(province_data[1][0], province_2_id)


class test_region(unittest.TestCase):
    def setUp(self):
        self.con = db.connect_db(DB_CONNECTION_STRING, DB_SCHEMA)
        self.cursor = self.con.cursor()
        db.create_search_path(self.con, self.cursor, DB_SCHEMA)

        self.province_name = "test-province"
        self.name = "test-region"
        self.province_id = organization.new_province(self.cursor, self.province_name)

    def tearDown(self):
        self.con.rollback()
        db.end_query(self.con, self.cursor)

    def test_new_region(self):
        region_id = organization.new_region(self.cursor, self.name, self.province_id)
        self.assertTrue(validator.is_valid_uuid(region_id))

    def test_get_region(self):
        region_id = organization.new_region(self.cursor, self.name, self.province_id)
        region_data = organization.get_region(self.cursor, region_id)
        self.assertEqual(region_data[0], self.name)
        self.assertEqual(region_data[1], self.province_id)

    def test_get_region_not_found(self):
        with self.assertRaises(organization.RegionNotFoundError):
            organization.get_region(self.cursor, str(uuid.uuid4()))

    def test_get_full_region(self):
        region_id = organization.new_region(self.cursor, self.name, self.province_id)
        region_data = organization.get_full_region(self.cursor, region_id)
        self.assertEqual(region_data[0], region_id)
        self.assertEqual(region_data[1], self.name)
        self.assertEqual(region_data[2], self.province_name)

    def get_region_by_province(self):
        region_id = organization.new_region(self.cursor, self.name, self.province_id)
        region_data = organization.get_region_by_province(self.cursor, self.province_id)
        self.assertEqual(len(region_data), 1)
        self.assertEqual(region_data[0][0], region_id)
        self.assertEqual(region_data[0][1], self.name)


class test_location(unittest.TestCase):
    def setUp(self):
        self.con = db.connect_db(DB_CONNECTION_STRING, DB_SCHEMA)
        self.cursor = self.con.cursor()
        db.create_search_path(self.con, self.cursor, DB_SCHEMA)

        self.owner_id = organization.new_organization(
            cursor=self.cursor,
            name="test-owner",
            website="www.test.com",
            phone_number="123456789",
            address="test-address",
        )

        self.province_name = "test-province"
        self.region_name = "test-region"
        self.name = "test-location"
        self.address = "test-address"
        self.province_id = organization.new_province(self.cursor, self.province_name)
        self.region_id = organization.new_region(
            self.cursor, self.region_name, self.province_id
        )

    def tearDown(self):
        self.con.rollback()
        db.end_query(self.con, self.cursor)

    def test_new_location(self):
        location_id = organization.new_location(
            self.cursor, self.name, self.address, self.region_id, self.owner_id
        )
        self.assertTrue(validator.is_valid_uuid(location_id))

    def test_get_location(self):
        location_id = organization.new_location(
            self.cursor, self.name, self.address, self.region_id, self.owner_id
        )
        location_data = organization.get_location(self.cursor, location_id)

        self.assertEqual(location_data[0], self.name)
        self.assertEqual(location_data[1], self.address)
        self.assertEqual(location_data[2], self.region_id)
        self.assertEqual(location_data[3], self.owner_id)

    def test_get_location_not_found(self):
        with self.assertRaises(organization.LocationNotFoundError):
            organization.get_location(self.cursor, str(uuid.uuid4()))

    # def test_get_full_location(self):
    #     location_id = organization.new_location(
    #         self.cursor, self.name, self.address, self.region_id,self.owner_id
    #     )
    #     location_data = organization.get_full_location(self.cursor, location_id)
    #     self.assertEqual(location_data[0], location_id)
    #     self.assertEqual(location_data[1], self.name)
    #     self.assertEqual(location_data[2], self.address)
    #     self.assertEqual(location_data[3], self.region_name)
    #     self.assertEqual(location_data[4], self.province_name)

    def get_location_by_region(self):
        location_id = organization.new_location(
            self.cursor, self.name, self.address, self.region_id
        )
        location_data = organization.get_location_by_region(self.cursor, self.region_id)
        self.assertEqual(len(location_data), 1)
        self.assertEqual(location_data[0][0], location_id)
        self.assertEqual(location_data[0][1], self.name)


class test_organization_information(unittest.TestCase):
    def setUp(self):
        self.con = db.connect_db(DB_CONNECTION_STRING, DB_SCHEMA)
        self.cursor = self.con.cursor()
        db.create_search_path(self.con, self.cursor, DB_SCHEMA)

        self.name = "test-organization"
        self.website = "www.test.com"
        self.phone = "123456789"
        self.address = "test-address"

        self.lot_number = "lot_number"
        self.product_name = "product_name"
        self.npk = "npk"
        self.registration_number = "registration_number"
        self.n = 10.0
        self.p = 20.0
        self.k = 30.0
        self.weight = None
        self.density = None
        self.volume = None
        self.warranty = "warranty"
        self.title_en = "title_en"
        self.title_fr = "title_fr"
        self.is_minimal = False
        self.record_keeping = False

        self.label_information_id = label.new_label_information(
            self.cursor,
            self.product_name,
            self.lot_number,
            self.npk,
            self.n,
            self.p,
            self.k,
            self.title_en,
            self.title_fr,
            self.is_minimal,
            self.record_keeping,
        )

    def tearDown(self):
        self.con.rollback()
        db.end_query(self.con, self.cursor)

    def test_new_organization_information_with_address(self):
        id = organization.new_organization_information(
            self.cursor,
            self.address,
            self.name,
            self.website,
            self.phone,
            self.label_information_id,
            False,
            True,
        )
        self.assertTrue(validator.is_valid_uuid(id))

    def test_new_organization_info_no_address(self):
        id = organization.new_organization_information(
            cursor=self.cursor,
            address=None,
            name=self.name,
            website=self.website,
            phone_number=self.phone,
            label_id=self.label_information_id,
            edited=False,
            is_main_contact=True,
        )
        self.assertTrue(validator.is_valid_uuid(id))

    def test_new_organization_empty(self):
        with self.assertRaises(organization.OrganizationInformationCreationError):
            organization.new_organization(self.cursor, None, None, None, None)

    def test_get_organization_info(self):
        id = organization.new_organization_information(
            self.cursor,
            self.address,
            self.name,
            self.website,
            self.phone,
            self.label_information_id,
            False,
            True,
        )
        data = organization.get_organization_info(self.cursor, id)
        self.assertEqual(data[0], self.name)
        self.assertEqual(data[1], self.website)
        self.assertEqual(data[2], self.phone)
        self.assertEqual(data[3], self.address)
        self.assertEqual(data[4], self.label_information_id)
        self.assertEqual(data[5], False)
        self.assertEqual(data[6], True)

    def test_get_organization_info_not_found(self):
        with self.assertRaises(organization.OrganizationInformationNotFoundError):
            organization.get_organization_info(self.cursor, str(uuid.uuid4()))

    def test_get_organization_info_label(self):
        organization.new_organization_information(
            self.cursor,
            self.address,
            self.name,
            self.website,
            self.phone,
            self.label_information_id,
            False,
            True,
        )
        data = organization.get_organizations_info_label(
            self.cursor, self.label_information_id
        )
        self.assertEqual(data[0][0], self.name)
        self.assertEqual(data[0][1], self.website)
        self.assertEqual(data[0][2], self.phone)
        self.assertEqual(data[0][3], self.address)

    def test_update_organization_info(self):
        new_name = "new-name"
        new_website = "www.new.com"
        new_phone = "987654321"
        id = organization.new_organization_information(
            self.cursor,
            self.address,
            self.name,
            self.website,
            self.phone,
            self.label_information_id,
            False,
            True,
        )
        old_data = organization.get_organization_info(self.cursor, id)
        self.assertEqual(old_data[0], self.name)
        self.assertEqual(old_data[1], self.website)
        self.assertEqual(old_data[2], self.phone)
        self.assertEqual(old_data[3], self.address)
        organization.update_organization_info(
            self.cursor, id, new_name, new_website, new_phone
        )
        data = organization.get_organization_info(self.cursor, id)
        self.assertEqual(data[0], new_name)
        self.assertEqual(data[1], new_website)
        self.assertEqual(data[2], new_phone)

    def test_new_organization_information(self):
        id = organization.new_organization_information(
            cursor=self.cursor,
            address=self.address,
            name=self.name,
            website=self.website,
            phone_number=self.phone,
            label_id=self.label_information_id,
        )
        self.assertTrue(validator.is_valid_uuid(id))

    def test_get_organizations_info_json(self):
        company_id = organization.new_organization_information(
            self.cursor,
            address=self.address,
            name=self.name,
            website=self.website,
            phone_number=self.phone,
            label_id=self.label_information_id,
        )
        manufacturer_id = organization.new_organization_information(
            self.cursor,
            address=self.address,
            name=self.name,
            website=self.website,
            phone_number=self.phone,
            label_id=self.label_information_id,
        )
        data = organization.get_organizations_info_json(
            self.cursor, self.label_information_id
        )
        self.assertEqual(len(data["organizations"]), 2)
        self.assertEqual(data["organizations"][0]["id"], str(company_id))
        self.assertEqual(data["organizations"][1]["id"], str(manufacturer_id))

    def test_get_organizations_info_json_not_found(self):
        data = organization.get_organizations_info_json(
            self.cursor, self.label_information_id
        )
        self.assertDictEqual(data, {"organizations": []})

    def test_upsert_organizations_info(self):
        new_name = "new-name"
        new_website = "www.new.com"
        new_phone = "987654321"
        new_address = "new-address"

        old_org = OrganizationInformation(
            name=self.name,
            website=self.website,
            phone_number=self.phone,
            address=self.address,
            edited=False,
            is_main_contact=True,
        ).model_dump_json()

        old_org = json.dumps([old_org])

        organizations_dict = {
            "organizations": [
                {
                    "name": self.name,
                    "website": self.website,
                    "phone_number": self.phone,
                    "address": self.address,
                    "edited": True,
                    "is_main_contact": True,
                }
            ]
        }

        # Test inserting a new organization information
        self.assertRaises(
            organization.OrganizationInformationNotFoundError,
            organization.get_organizations_info_label,
            self.cursor,
            self.label_information_id,
        )
        received_data = organization.upsert_organization_info(
            self.cursor,
            json.dumps(organizations_dict["organizations"]),
            self.label_information_id,
        )
        upserted_data = organization.get_organizations_info_label(
            self.cursor, self.label_information_id
        )
        self.assertIsNotNone(upserted_data)
        self.assertIsNotNone(received_data[0]["name"])
        self.assertIsNotNone(received_data[0]["id"])
        self.assertEqual(len(upserted_data), 1)
        self.assertEqual(upserted_data[0][0], self.name)

        # Test updating an existing organization information
        received_data[0]["name"] = new_name
        received_data[0]["website"] = new_website
        received_data[0]["phone_number"] = new_phone
        received_data[0]["address"] = new_address

        organization.upsert_organization_info(
            self.cursor, json.dumps(received_data), self.label_information_id
        )
        new_data = organization.get_organizations_info_label(
            self.cursor, self.label_information_id
        )
        self.assertIsNotNone(new_data)
        self.assertEqual(len(new_data), 1)
        self.assertEqual(new_data[0][0], new_name)
        self.assertEqual(new_data[0][1], new_website)
        self.assertEqual(new_data[0][2], new_phone)
        self.assertNotEqual(
            new_data[0][3], upserted_data[0][3]
        )  # Address should be updated therefore the id must have changed

    def test_delete_label_with_linked_organization_information(self):
        # create a organization information
        organization_id = organization.new_organization_information(
            self.cursor,
            self.address,
            self.name,
            self.website,
            self.phone,
            self.label_information_id,
            False,
            True,
        )
        # label_info = label.get_label_information_json(self.cursor, self.label_information_id)
        # Attempt to delete the inspection, which should raise a notice but not fail
        deleted_rows = label.delete_label_info(self.cursor, self.label_information_id)
        self.assertGreaterEqual(deleted_rows, 1)

        self.cursor.execute(
            "SELECT COUNT(*) FROM organization_information WHERE id = %s;",
            (organization_id,),
        )
        org_count = self.cursor.fetchone()[0]
        self.assertEqual(
            org_count,
            0,
            "Organization information should have been deleted when the label was deleted",
        )


class test_organization(unittest.TestCase):
    def setUp(self):
        self.con = db.connect_db(DB_CONNECTION_STRING, DB_SCHEMA)
        self.cursor = self.con.cursor()
        db.create_search_path(self.con, self.cursor, DB_SCHEMA)

        self.province_name = "test-province"
        self.region_name = "test-region"
        self.name = "test-organization"
        self.website = "www.test.com"
        self.phone = "123456789"
        self.location_name = "test-location"
        self.address = "test-address"

        self.lot_number = "lot_number"
        self.product_name = "product_name"
        self.npk = "npk"
        self.registration_number = "registration_number"
        self.n = 10.0
        self.p = 20.0
        self.k = 30.0
        self.weight = None
        self.density = None
        self.volume = None
        self.warranty = "warranty"
        self.title_en = "title_en"
        self.title_fr = "title_fr"
        self.is_minimal = False
        self.record_keeping = False

        self.label_information_id = label.new_label_information(
            self.cursor,
            self.product_name,
            self.lot_number,
            self.npk,
            self.n,
            self.p,
            self.k,
            self.title_en,
            self.title_fr,
            self.is_minimal,
            self.record_keeping,
        )

        self.org_info_id = organization.new_organization_information(
            self.cursor,
            self.address,
            self.name,
            self.website,
            self.phone,
            self.label_information_id,
            False,
            True,
        )

    def tearDown(self):
        self.con.rollback()
        db.end_query(self.con, self.cursor)

    def test_new_organization(self):
        organization_id = organization.new_organization(
            self.cursor, self.name, self.website, self.phone, self.address
        )
        self.assertTrue(validator.is_valid_uuid(organization_id))

    def test_new_organization_no_location(self):
        organization_id = organization.new_organization(
            self.cursor, self.name, self.website, self.phone, None
        )
        self.assertTrue(validator.is_valid_uuid(organization_id))

    def test_upsert_organization(self):

        organization_id = organization.new_organization(
            self.cursor, self.name, "wrong-website", "wrong-phone", "wrong-address"
        )
        update_id = organization.upsert_organization(self.cursor, str(self.org_info_id))
        self.assertEqual(organization_id, update_id)
        organization_data = organization.get_organization(
            self.cursor, str(organization_id)
        )
        self.assertEqual(organization_data[0], self.name)
        self.assertEqual(organization_data[1], self.website)
        self.assertEqual(organization_data[2], self.phone)
        self.assertEqual(organization_data[3], self.address)

    def test_get_organization(self):
        organization_id = organization.new_organization(
            self.cursor, self.name, self.website, self.phone, self.address
        )
        organization_data = organization.get_organization(self.cursor, organization_id)
        self.assertEqual(organization_data[0], self.name)
        self.assertEqual(organization_data[1], self.website)
        self.assertEqual(organization_data[2], self.phone)
        self.assertEqual(organization_data[3], self.address)

    def test_get_organization_not_found(self):
        with self.assertRaises(organization.OrganizationNotFoundError):
            organization.get_organization(self.cursor, str(uuid.uuid4()))
