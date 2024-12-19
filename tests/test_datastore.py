"""
This is a test script for the highest level of the datastore packages.
It tests the functions in the __init__.py files of the datastore packages.
"""

import asyncio
import io
import os
import unittest
import uuid
from unittest.mock import MagicMock, patch

from PIL import Image

import datastore.db.queries.user as user_db
import datastore.db.queries.picture as picture_db
import datastore.db.queries.container as container_db
import datastore.blob.azure_storage_api as azure_storage

import datastore.__init__ as datastore
import datastore.db.__init__ as db
import datastore.db.metadata.validator as validator

DB_CONNECTION_STRING = os.environ.get("NACHET_DB_URL")
if DB_CONNECTION_STRING is None or DB_CONNECTION_STRING == "":
    raise ValueError("NACHET_DB_URL is not set")

DB_SCHEMA = os.environ.get("NACHET_SCHEMA_TESTING")
if DB_SCHEMA is None or DB_SCHEMA == "":
    raise ValueError("NACHET_SCHEMA_TESTING is not set")

BLOB_CONNECTION_STRING = os.environ["NACHET_STORAGE_URL_TESTING"]
if BLOB_CONNECTION_STRING is None or BLOB_CONNECTION_STRING == "":
    raise ValueError("NACHET_STORAGE_URL_TESTING is not set")

BLOB_ACCOUNT = os.environ["NACHET_BLOB_ACCOUNT_TESTING"]
if BLOB_ACCOUNT is None or BLOB_ACCOUNT == "":
    raise ValueError("NACHET_BLOB_ACCOUNT is not set")

BLOB_KEY = os.environ["NACHET_BLOB_KEY_TESTING"]
if BLOB_KEY is None or BLOB_KEY == "":
    raise ValueError("NACHET_BLOB_KEY is not set")

class test_container(unittest.TestCase):
    def setUp(self):
        self.con = db.connect_db(DB_CONNECTION_STRING, DB_SCHEMA)
        self.cursor = self.con.cursor()
        db.create_search_path(self.con, self.cursor, DB_SCHEMA)
        self.user_email = "test-email-container"

        # We create directly from the db because some operation needs to keep track of a user in the db
        self.user_id = user_db.register_user(self.cursor, self.user_email)
        self.user_obj = datastore.User(self.user_id, self.user_email)
        self.prefix = "test-user"
        self.connection_str = BLOB_CONNECTION_STRING

        self.container_client = None


    def tearDown(self):
        if self.container_client is not None:
            self.container_client.delete_container()
            self.container_client = None
        self.con.rollback()
        db.end_query(self.con, self.cursor)

    def test_create_container(self):
        """
        Test the create container function.
        """
        container_name = "test-container-class-create-container"
        container_obj = asyncio.run(
            datastore.create_container(
                cursor=self.cursor,
                connection_str=self.connection_str,
                container_name=container_name,
                user_id=self.user_id,
                is_public=False,
                storage_prefix=self.prefix,
                add_user_to_storage=False,
            )
        )
        self.container_client = container_obj.container_client
        #self.assertIsNotNone(self.container_client)
        self.assertIsNotNone(container_obj.container_client)
        self.assertTrue(self.container_client.exists())
        self.assertTrue(container_obj.container_client.exists())
        # Check to make sure the user is not added to the storage
        self.assertListEqual(container_obj.user_ids, [])
        folder_name = "General"
        folder_id = next(iter(container_obj.folders.keys()))
        # Check if the Default "Genereal" folder is created in the storage
        # There is a blob created to index the folder path in the storage
        # blob_name = General/<Folder_id>.json 
        blob_name = azure_storage.build_blob_name(str(folder_name),str(folder_id),"json")
        blob_name_list = self.container_client.list_blob_names()
        # There should be only one blob in the container, but an ItemPage
        # Is a pain to test, so I just loop through the list and collect its length
        length = 0
        for item in blob_name_list:
            length += 1
            self.assertTrue(item == blob_name)
        

    def test_create_container_no_name(self):
        container_obj = asyncio.run(
            datastore.create_container(
                cursor=self.cursor,
                connection_str=self.connection_str,
                container_name=None,
                user_id=self.user_id,
                is_public=False,
                storage_prefix=self.prefix,
                add_user_to_storage=False,
            )
        )
        self.container_client = container_obj.container_client
        self.assertTrue(self.container_client.exists())
        self.assertListEqual(container_obj.user_ids, [])

    def test_create_container_adding_user(self):
        """
        This test checks if the user is added to the container when the add_user_to_storage is set to True
        """
        container_name = "test-container-class-adding-user"
        container_obj = asyncio.run(
            datastore.create_container(
                cursor=self.cursor,
                connection_str=self.connection_str,
                container_name=container_name,
                user_id=self.user_id,
                is_public=False,
                storage_prefix=self.prefix,
                add_user_to_storage=True,
            )
        )
        self.container_client = container_obj.container_client
        self.assertTrue(self.container_client.exists())
        self.assertListEqual(container_obj.user_ids, [self.user_id])
        self.assertTrue(container_db.has_user_access_to_container(self.cursor, self.user_id, container_obj.id))

    def test_add_user(self):
        """
        This test if the add_user function correctly add a user to a container
        """
        container_name = "test-container-class-add-user"
        container_obj = asyncio.run(
            datastore.create_container(
                cursor=self.cursor,
                connection_str=self.connection_str,
                container_name=container_name,
                user_id=self.user_id,
                is_public=False,
                storage_prefix=self.prefix,
                add_user_to_storage=False,
            )
        )
        self.container_client = container_obj.container_client
        self.assertTrue(self.container_client.exists())
        container_obj.add_user(self.cursor,self.user_id,self.user_id)
        self.assertListEqual(container_obj.user_ids, [self.user_id])
        self.assertTrue(container_db.has_user_access_to_container(self.cursor, self.user_id, container_obj.id))

    def test_get_container_client(self):
        """
        Test the get container client function.
        """
        container_name = "test-container-class-get-container-client"
        container_obj = asyncio.run(
            datastore.create_container(
                cursor=self.cursor,
                connection_str=self.connection_str,
                container_name=container_name,
                user_id=self.user_id,
                is_public=False,
                storage_prefix=self.prefix,
                add_user_to_storage=False,
            )
        )
        self.container_client = container_obj.container_client
        self.assertTrue(self.container_client.exists())
        
        container_obj.container_client = None
        asyncio.run(
            container_obj.get_container_client(self.connection_str,None)
        )
        self.assertIsNotNone(container_obj.container_client)
        self.assertTrue(container_obj.container_client.exists())

    def test_create_storage(self):
        """
        Test the create storage function.
        """
        container_name = "test-container-class-create-storage"
        container_id = container_db.create_container(
            self.cursor,
            container_name,
            self.user_id,
            False,
            self.prefix
        )
        container_obj = datastore.Container(id=container_id, tier=self.prefix, name=container_name, public=False)
        container_obj.add_user(self.cursor,self.user_id,self.user_id)
        asyncio.run(container_obj.create_storage(self.connection_str,None))
        self.container_client = container_obj.container_client
        self.assertIsNotNone(container_obj.container_client)
        self.assertIsNotNone(self.container_client)
        self.assertTrue(container_obj.container_client.exists())
        self.assertTrue(self.container_client.exists())

    def test_create_folder(self):
        """
        Test the create folder function.
        """
        container_name = "test-container-class-create-folder"
        container_id = container_db.create_container(
            self.cursor,
            container_name,
            self.user_id,
            False,
            self.prefix
        )
        container_obj = datastore.Container(id=container_id, tier=self.prefix, name=container_name, public=False)
        container_obj.add_user(self.cursor,self.user_id,self.user_id)
        asyncio.run(container_obj.create_storage(self.connection_str,None))
        self.container_client = container_obj.container_client
        self.assertIsNotNone(container_obj.container_client)
        self.assertIsNotNone(self.container_client)
        self.assertTrue(container_obj.container_client.exists())
        self.assertTrue(self.container_client.exists())


        folder_name = "test-folder"
        folder_id = asyncio.run(container_obj.create_folder(cursor=self.cursor, folder_name=folder_name,performed_by=self.user_id))
        # Check if the folder is created in the object
        self.assertTrue(folder_id in container_obj.folders.keys())
        # Check if the folder is created in the storage
        # There is a blob created to index the folder path in the storage
        blob_name = azure_storage.build_blob_name(str(folder_name),str(folder_id),"json")
        blob_name_list = self.container_client.list_blob_names()
        # There should be only one blob in the container, but an ItemPage
        # Is a pain to test, so I just loop through the list and collect its length
        length = 0
        for item in blob_name_list:
            length += 1
            self.assertTrue(item == blob_name)
        self.assertEqual(length, 1)
        # Check if the folder is created in the DB
        fetched_name = picture_db.get_picture_set_name(self.cursor, folder_id) 
        self.assertEqual(fetched_name, folder_name)

    def test_create_unnamed_folder(self):
        """
        Test the create folder function with no name.
        In this case, the folder name is the folder id.
        """
        container_name = "test-container-class-create-unnamed-folder"
        container_id = container_db.create_container(
            self.cursor,
            container_name,
            self.user_id,
            False,
            self.prefix
        )
        container_obj = datastore.Container(id=container_id, tier=self.prefix, name=container_name, public=False)
        container_obj.add_user(self.cursor,self.user_id,self.user_id)
        asyncio.run(container_obj.create_storage(self.connection_str,None))
        self.container_client = container_obj.container_client
        self.assertTrue(self.container_client.exists())
        folder_id = asyncio.run(container_obj.create_folder(cursor=self.cursor, performed_by=self.user_id))
        # Check if the folder is created in the object
        
        self.assertTrue(folder_id in container_obj.folders.keys())
        # Check if the folder is created in the storage
        # There is a blob created to index the folder path in the storage
        blob_name = azure_storage.build_blob_name(str(folder_id),str(folder_id),"json")
        blob_name_list = self.container_client.list_blob_names()
        # There should be only one blob in the container, but an ItemPage
        # Is a pain to test, so I just loop through the list and collect its length
        length = 0
        for item in blob_name_list:
            length += 1

            self.assertTrue(item == blob_name)
        self.assertEqual(length, 1)
        # Check if the folder is created in the DB
        fetched_name = picture_db.get_picture_set_name(self.cursor, folder_id) 
        self.assertEqual(str(fetched_name), str(folder_id))

    def test_create_folder_within_folder(self):
        """
        Test the create folder function with a parent-folder.
        """
        container_name = "test-container-class-create-folder"
        container_id = container_db.create_container(
            self.cursor,
            container_name,
            self.user_id,
            False,
            self.prefix
        )
        container_obj = datastore.Container(id=container_id, tier=self.prefix, name=container_name, public=False)
        container_obj.add_user(self.cursor,self.user_id,self.user_id)
        asyncio.run(container_obj.create_storage(self.connection_str,None))
        self.container_client = container_obj.container_client
        self.assertIsNotNone(container_obj.container_client)
        self.assertIsNotNone(self.container_client)
        self.assertTrue(container_obj.container_client.exists())
        self.assertTrue(self.container_client.exists())


        folder_name = "test-folder-1"
        folder_id = asyncio.run(container_obj.create_folder(cursor=self.cursor, folder_name=folder_name,performed_by=self.user_id))
        # Check if the folder is created in the object
        self.assertTrue(folder_id in container_obj.folders.keys())
        # Check if the folder is created in the storage
        # There is a blob created to index the folder path in the storage
        blob_name = azure_storage.build_blob_name(str(folder_name),str(folder_id),"json")
        blob_name_list = self.container_client.list_blob_names()
        # There should be only one blob in the container, but an ItemPage
        # Is a pain to test, so I just loop through the list and collect its length
        length = 0
        for item in blob_name_list:
            length += 1
            self.assertTrue(item == blob_name)
        self.assertEqual(length, 1)
        # Check if the folder is created in the DB
        fetched_name = picture_db.get_picture_set_name(self.cursor, folder_id) 
        self.assertEqual(fetched_name, folder_name)

        # Create a folder within the folder
        folder_name = "test-folder-2"
        folder_id2 = asyncio.run(container_obj.create_folder(cursor=self.cursor, folder_name=folder_name,performed_by=self.user_id, parent_folder_id=folder_id))
        # Check if the folder is created in the object
        self.assertTrue(folder_id2 in container_obj.folders.keys())
        self.assertEqual(1, len(container_obj.folders[folder_id].children))
        self.assertTrue(folder_id2 == container_obj.folders[folder_id].children[0])
        self.assertTrue(folder_id == container_obj.folders[folder_id2].parent_id)
        # Check if the folder is created in the storage
        blob_name_2 = azure_storage.build_blob_name(
            container_obj.folders[folder_id2].path,
            str(folder_id2),
            "json")
        flag = False
        length = 0
        blob_name_list = self.container_client.list_blob_names()
        for item in blob_name_list:
            length += 1
            if item == blob_name_2:
                flag = True
        self.assertTrue(flag)
        self.assertEqual(length, 2)

    def test_create_duplicate_folder(self):
        """
        Test the create folder function with a parent-folder.
        """
        container_name = "test-container-class-create-folder"
        container_id = container_db.create_container(
            self.cursor,
            container_name,
            self.user_id,
            False,
            self.prefix
        )
        container_obj = datastore.Container(id=container_id, tier=self.prefix, name=container_name, public=False)
        container_obj.add_user(self.cursor,self.user_id,self.user_id)
        asyncio.run(container_obj.create_storage(self.connection_str,None))
        self.container_client = container_obj.container_client
        self.assertIsNotNone(container_obj.container_client)
        self.assertIsNotNone(self.container_client)
        self.assertTrue(container_obj.container_client.exists())
        self.assertTrue(self.container_client.exists())


        folder_name = "test-folder-1"
        folder_id = asyncio.run(container_obj.create_folder(cursor=self.cursor, folder_name=folder_name,performed_by=self.user_id))
        # Check if the folder is created in the object
        self.assertTrue(folder_id in container_obj.folders.keys())
        # Check if the folder is created in the storage
        # There is a blob created to index the folder path in the storage
        blob_name = azure_storage.build_blob_name(str(folder_name),str(folder_id),"json")
        blob_name_list = self.container_client.list_blob_names()
        # There should be only one blob in the container, but an ItemPage
        # Is a pain to test, so I just loop through the list and collect its length
        length = 0
        for item in blob_name_list:
            length += 1
            self.assertTrue(item == blob_name)
        self.assertEqual(length, 1)
        # Check if the folder is created in the DB
        fetched_name = picture_db.get_picture_set_name(self.cursor, folder_id) 
        self.assertEqual(fetched_name, folder_name)

        # Create a second folder with the same name
        self.assertRaises(datastore.FolderCreationError, asyncio.run, container_obj.create_folder(cursor=self.cursor, folder_name=folder_name,performed_by=self.user_id, parent_folder_id=None))   

    def test_create_duplicate_folder_within_folder(self):
        """
        Test the create folder function with a parent-folder.
        """
        container_name = "test-container-class-create-folder"
        container_id = container_db.create_container(
            self.cursor,
            container_name,
            self.user_id,
            False,
            self.prefix
        )
        container_obj = datastore.Container(id=container_id, tier=self.prefix, name=container_name, public=False)
        container_obj.add_user(self.cursor,self.user_id,self.user_id)
        asyncio.run(container_obj.create_storage(self.connection_str,None))
        self.container_client = container_obj.container_client
        self.assertIsNotNone(container_obj.container_client)
        self.assertIsNotNone(self.container_client)
        self.assertTrue(container_obj.container_client.exists())
        self.assertTrue(self.container_client.exists())


        folder_name = "test-folder-1"
        folder_id = asyncio.run(container_obj.create_folder(cursor=self.cursor, folder_name=folder_name,performed_by=self.user_id))
        # Check if the folder is created in the object
        self.assertTrue(folder_id in container_obj.folders.keys())
        # Check if the folder is created in the storage
        # There is a blob created to index the folder path in the storage
        blob_name = azure_storage.build_blob_name(str(folder_name),str(folder_id),"json")
        blob_name_list = self.container_client.list_blob_names()
        # There should be only one blob in the container, but an ItemPage
        # Is a pain to test, so I just loop through the list and collect its length
        length = 0
        for item in blob_name_list:
            length += 1
            self.assertTrue(item == blob_name)
        self.assertEqual(length, 1)
        # Check if the folder is created in the DB
        fetched_name = picture_db.get_picture_set_name(self.cursor, folder_id) 
        self.assertEqual(fetched_name, folder_name)

        # Create a folder within the folder
        folder_name = "test-folder-2"
        folder_id2 = asyncio.run(container_obj.create_folder(cursor=self.cursor, folder_name=folder_name,performed_by=self.user_id, parent_folder_id=folder_id))
        # Check if the folder is created in the object
        self.assertTrue(folder_id2 in container_obj.folders.keys())
        self.assertEqual(1, len(container_obj.folders[folder_id].children))
        self.assertTrue(folder_id2 == container_obj.folders[folder_id].children[0])
        self.assertTrue(folder_id == container_obj.folders[folder_id2].parent_id)
        # Check if the folder is created in the storage
        blob_name_2 = azure_storage.build_blob_name(
            container_obj.folders[folder_id2].path,
            str(folder_id2),
            "json")
        flag = False
        length = 0
        blob_name_list = self.container_client.list_blob_names()
        for item in blob_name_list:
            length += 1
            if item == blob_name_2:
                flag = True
        self.assertTrue(flag)
        self.assertEqual(length, 2) 
        # Create a second folder with the same name
        self.assertRaises(datastore.FolderCreationError, asyncio.run, container_obj.create_folder(cursor=self.cursor, folder_name=folder_name,performed_by=self.user_id, parent_folder_id=folder_id))      

    def test_upload_pictures(self):
        """
        Test the upload picture function within the container object.
        """
        # Create the container
        container_name = "test-container-class-upload-pics"
        container_id = container_db.create_container(
            self.cursor,
            container_name,
            self.user_id,
            False,
            self.prefix
        )
        container_obj = datastore.Container(id=container_id, tier=self.prefix, name=container_name, public=False)
        container_obj.add_user(self.cursor,self.user_id,self.user_id)
        asyncio.run(container_obj.create_storage(self.connection_str,None))
        self.container_client = container_obj.container_client
        self.assertIsNotNone(self.container_client)
        self.assertTrue(self.container_client.exists())

        # Create the folder
        folder_name = "test-folder"
        folder_id = asyncio.run(container_obj.create_folder(cursor=self.cursor, folder_name=folder_name,performed_by=self.user_id))
        
        # Create the picture to upload
        image = Image.new("RGB", (1980, 1080), "blue")
        image_byte_array = io.BytesIO()
        image.save(image_byte_array, format="TIFF")
        pic_encoded = image.tobytes()
        
        # Add the upload permission to the user and then Upload the picture
        container_obj.add_user(self.cursor,self.user_id,self.user_id)
        picture_id =  asyncio.run(container_obj.upload_pictures(cursor=self.cursor, hashed_pictures=[pic_encoded], folder_id=folder_id, user_id=self.user_id))
        
        # Check if the picture is created in the storage
        blob_name = azure_storage.build_blob_name(str(folder_name),str(picture_id[0]),None)
        blob_name_list = self.container_client.list_blob_names()
        for item in blob_name_list:
            if item[-4:] != "json":
                self.assertEqual(item, blob_name)
        # Check if the picture is created in the DB
        nb_pictures = picture_db.count_pictures(self.cursor, folder_id)
        self.assertEqual(nb_pictures, 1)

    def test_get_container(self):
        """
        Test the get container object function.
        """
        container_name = "test-container-class-get-container"
        container_id = container_db.create_container(
            self.cursor,
            container_name,
            self.user_id,
            False,
            self.prefix
        )
        container_obj = datastore.Container(id=container_id, tier=self.prefix, name=container_name, public=False)
        container_obj.add_user(self.cursor,self.user_id,self.user_id)
        asyncio.run(container_obj.create_storage(self.connection_str,None))
        self.container_client = container_obj.container_client
        self.assertIsNotNone(self.container_client)
        self.assertTrue(self.container_client.exists())
        # Test if the container is correctly fetched
        container_get = asyncio.run(datastore.get_container(self.cursor, container_id,self.connection_str,None))
        self.assertEqual(container_obj.id, container_get.id)
        self.assertEqual(container_obj.name, container_get.name)
        self.assertEqual(container_obj.user_ids[0], container_get.user_ids[0])
        self.assertEqual(container_obj.is_public, container_get.is_public)
        # Test the container.folders
        # Create the picture to upload
        image = Image.new("RGB", (1980, 1080), "blue")
        image_byte_array = io.BytesIO()
        image.save(image_byte_array, format="TIFF")
        pic_encoded = image.tobytes()
        folder_name = "test-folder"
        folder_id = asyncio.run(container_obj.create_folder(cursor=self.cursor, folder_name=folder_name,performed_by=self.user_id))
        picture_id = asyncio.run(container_obj.upload_pictures(cursor=self.cursor,user_id=self.user_id ,hashed_pictures=[pic_encoded], folder_id=next(iter(container_obj.folders.keys()),None)))
        self.assertEqual(len(container_obj.folders), 1)
        self.assertIn(folder_id,container_obj.folders.keys())
        self.assertEqual(container_obj.folders[folder_id].name, "test-folder")
        # Path to the picture should be: <folder_name>/<picture_id>
        folder_path = container_obj.folders[folder_id].path
        self.assertEqual(picture_id[0], container_obj.folders[folder_id].pictures[0])
        self.assertEqual(len(container_get.folders), 0)
        # Verify the data in the getter
        container_get = asyncio.run(datastore.get_container(self.cursor, container_id,self.connection_str,None))
        self.assertEqual(len(container_get.folders), len(container_obj.folders))
        self.assertEqual(container_get.folders[folder_id].name, folder_name)
        self.assertEqual(container_get.folders[folder_id].path, folder_path)
        self.assertEqual(container_get.folders[folder_id].pictures[0], picture_id[0])

    def test_delete_folder(self):
        container_name = "test-container-class-delete-folder"
        container_id = container_db.create_container(
            self.cursor,
            container_name,
            self.user_id,
            False,
            self.prefix
        )
        container_obj = datastore.Container(id=container_id, tier=self.prefix, name=container_name, public=False)
        container_obj.add_user(self.cursor,self.user_id,self.user_id)
        asyncio.run(container_obj.create_storage(self.connection_str,None))
        self.container_client = container_obj.container_client
        self.assertIsNotNone(container_obj.container_client)
        self.assertIsNotNone(self.container_client)
        self.assertTrue(container_obj.container_client.exists())
        self.assertTrue(self.container_client.exists())


        folder_name = "test-folder"
        folder_id = asyncio.run(container_obj.create_folder(cursor=self.cursor, folder_name=folder_name,performed_by=self.user_id))
        #folder_id2 = asyncio.run(container_obj.create_folder(cursor=self.cursor, folder_name="test-folder-2",performed_by=self.user_id))
        # Check if the folder is created in the object
        self.assertTrue(folder_id in container_obj.folders.keys())
        # Check if the folder is created in the storage
        # There is a blob created to index the folder path in the storage
        blob_name = azure_storage.build_blob_name(str(folder_name),str(folder_id),"json")
        blob_name_list = self.container_client.list_blob_names()
        # There should be only one blob in the container, but an ItemPage
        # Is a pain to test, so I just loop through the list and collect its length
        length = 0
        for item in blob_name_list:
            length += 1
            self.assertEqual(item, blob_name)
        self.assertEqual(length, 1)
        # Check if the folder is created in the DB
        fetched_name = picture_db.get_picture_set_name(self.cursor, folder_id) 
        self.assertEqual(fetched_name, folder_name)

        # Delete the folder
        asyncio.run(container_obj.delete_folder_permanently(cursor=self.cursor, user_id=self.user_id, folder_id=folder_id))
        
        # Check if the folder is deleted in the object
        self.assertTrue(folder_id not in container_obj.folders.keys())
        # Check if the folder is deleted in the storage
        #blob_name_list = self.container_client.list_blob_names()
        blob_name_list = self.container_client.list_blobs(name_starts_with=folder_name)
        for item in blob_name_list:
            print(item.print())
            self.assertTrue(item.name != blob_name)
        blob_name_list = self.container_client.list_blob_names()
        length = 0
        for item in blob_name_list:
            length += 1
        self.assertEqual(length, 0)

class test_user(unittest.TestCase):
    def setUp(self):
        self.con = db.connect_db(DB_CONNECTION_STRING, DB_SCHEMA)
        self.cursor = self.con.cursor()
        db.create_search_path(self.con, self.cursor, DB_SCHEMA)
        self.user_email = "tests-user-class@email"
        self.user_id = None
        self.user_obj = None
        self.prefix = "test-user"
        self.connection_str = BLOB_CONNECTION_STRING

    def tearDown(self):
        self.con.rollback()
        if self.user_id is not None:
            if self.user_obj is not None:
                # delete the container
                for container_obj in self.user_obj.containers:
                    container_client = container_obj.container_client
                    container_client.delete_container()
        self.user_obj = None
        self.user_id = None
        db.end_query(self.con, self.cursor)

    def test_new_user(self):
        """
        Test the new user function.
        """
        self.user_obj = asyncio.run(
            datastore.new_user(
                self.cursor, self.user_email, self.connection_str, self.prefix
            )
        )
        self.assertIsInstance(self.user_obj, datastore.User)
        # self.user_id=user_obj.id
        self.user_id = datastore.User.get_id(self.user_obj)
        self.assertTrue(validator.is_valid_uuid(self.user_id))
        self.assertEqual(datastore.User.get_email(self.user_obj), self.user_email)

    def test_already_existing_user(self):
        """
        Test the already existing user function.
        """
        self.user_obj = asyncio.run(
            datastore.new_user(
                self.cursor, self.user_email, self.connection_str, self.prefix
            )
        )
        self.user_id = datastore.User.get_id(self.user_obj)
        self.assertTrue(validator.is_valid_uuid(self.user_id))
        with self.assertRaises(datastore.UserAlreadyExistsError):
            asyncio.run(
                datastore.new_user(
                    self.cursor, self.user_email, self.connection_str, self.prefix
                )
            )

    @patch("azure.storage.blob.ContainerClient.exists")
    def test_new_user_container_error(self, MockExists):
        """
        Test the new user container error function.
        """
        MockExists.return_value = False
        with self.assertRaises(datastore.ContainerCreationError):
            asyncio.run(
                datastore.new_user(
                    self.cursor, self.user_email, self.connection_str, self.prefix
                )
            )

    @patch("datastore.blob.azure_storage_api.create_folder")
    def test_new_user_folder_error(self, MockCreateFolder):
        """
        Test the new user folder error function.
        """
        MockCreateFolder.side_effect = datastore.azure_storage.CreateDirectoryError(
            "Test error"
        )
        with self.assertRaises(datastore.FolderCreationError):
            asyncio.run(
                datastore.new_user(
                    self.cursor, self.user_email, self.connection_str, "test-user"
                )
            )

    def test_get_User(self):
        """
        Test the get User object function.
        """
        user_obj = asyncio.run(
            datastore.new_user(
                self.cursor, self.user_email, self.connection_str, "test-user"
            )
        )
        user_get = asyncio.run(datastore.get_user(self.cursor, self.user_email))
        user_get_id = datastore.User.get_id(user_get)
        self.assertEqual(user_obj.id, user_get_id)
        self.assertEqual(
            user_obj.email, user_get.email
        )

    def test_get_user_container_client(self):
        """
        Test the get user container client function.
        """
        user_obj = asyncio.run(
            datastore.new_user(
                self.cursor, self.user_email, self.connection_str, "test-user"
            )
        )
        user_get = asyncio.run(datastore.get_user(self.cursor, self.user_email))
        
        self.assertTrue(user_obj.containers[0].container_client.exists())

        self.assertTrue(0==len(user_get.containers))
        asyncio.run(user_get.fetch_all_containers(cursor=self.cursor, connection_str=self.connection_str,credentials=None))
        self.assertTrue(len(user_obj.containers)==1)
        self.assertTrue(len(user_get.containers)==1)
        self.assertTrue(len(user_obj.containers)==len(user_get.containers))
        self.assertTrue(user_get.containers[0].container_client.exists())


if __name__ == "__main__":
    unittest.main()
