import asyncio
import io
import os
import unittest
import uuid
from unittest.mock import Mock

from PIL import Image

import datastore.blob.__init__ as blob
from datastore.blob.azure_storage_api import (
    ConnectionStringError,
    CreateDirectoryError,
    FolderListError,
    GenerateHashError,
    GetBlobError,
    GetFolderUUIDError,
    MountContainerError,
    build_blob_name,
    build_container_name,
    create_folder,
    generate_hash,
    get_blob,
    get_blobs_from_tag,
    get_directories,
    get_folder_uuid,
    is_a_folder,
    mount_container,
    move_blob,
    upload_image,
    get_image_count,
)

BLOB_CONNECTION_STRING = os.environ["NACHET_STORAGE_URL_TESTING"]
if BLOB_CONNECTION_STRING is None or BLOB_CONNECTION_STRING == "":
    raise ValueError("NACHET_STORAGE_URL_TESTING is not set")

BLOB_ACCOUNT = os.environ["NACHET_BLOB_ACCOUNT_TESTING"]
if BLOB_ACCOUNT is None or BLOB_ACCOUNT == "":
    raise ValueError("NACHET_BLOB_ACCOUNT is not set")

BLOB_KEY = os.environ["NACHET_BLOB_KEY_TESTING"]
if BLOB_KEY is None or BLOB_KEY == "":
    raise ValueError("NACHET_BLOB_KEY is not set")


class TestBuildContainerNameFunction(unittest.TestCase):
    def setUp(self):
        self.tier = "test-user"
        self.container_uuid = str(uuid.uuid4())

    def test_build_container_name(self):
        result = build_container_name(self.container_uuid, self.tier)
        expected_result = "{}-{}".format(self.tier, self.container_uuid)
        self.assertEqual(result, expected_result)


class TestBuildBlobNameFunction(unittest.TestCase):
    def setUp(self):
        self.tier = "test-user"
        self.container_uuid = str(uuid.uuid4())
        self.blob_name = "test_blob"
        self.blob_type = "png"
        self.container_name = build_container_name(self.container_uuid, self.tier)
        self.folder_name = "test_folder"
        self.folder_path = "{}/{}".format(self.container_name, self.folder_name)

    def test_build_blob_name(self):
        result = build_blob_name(self.folder_path, self.blob_name, self.blob_type)
        expected_blob_path = "{}/{}.{}".format(
            self.folder_path, self.blob_name, self.blob_type
        )
        self.assertEqual(result, expected_blob_path)


class TestMountContainerFunction(unittest.TestCase):
    def setUp(self):
        self.storage_url = BLOB_CONNECTION_STRING
        self.account_name = BLOB_ACCOUNT
        self.account_key = BLOB_KEY
        self.credential = blob.get_account_sas(self.account_name, self.account_key)
        self.tier = "test-user"
        self.container_uuid = str(uuid.uuid4())

    def test_mount_existing_container(self):
        container_client = asyncio.run(
            mount_container(self.storage_url, self.container_uuid, True, self.tier)
        )

        self.assertTrue(container_client.exists())
        container_client.delete_container()

    def test_mount_nonexisting_container_create(self):
        """
        tests when a container does not exists and create_container flag is set to True,
        should create a new container and return the container client
        """
        not_uuid = "notauuid"
        container_client = asyncio.run(
            mount_container(
                self.storage_url, not_uuid, True, self.tier, self.credential
            )
        )
        self.assertTrue(container_client.exists())
        container_client.delete_container()

    def test_mount_nonexisting_container_no_create(self):
        not_uuid = "alsonotuuid"
        with self.assertRaises(MountContainerError):
            asyncio.run(
                mount_container(
                    self.storage_url, not_uuid, False, self.tier, self.credential
                )
            )

    def test_mount_container_connection_string_error(self):
        with self.assertRaises(ConnectionStringError):
            asyncio.run(
                mount_container("invalid-url", self.container_uuid, True, self.tier)
            )


class TestGetBlob(unittest.TestCase):
    def setUp(self):
        self.storage_url = BLOB_CONNECTION_STRING
        self.tier = "testuser"
        self.container_uuid = str(uuid.uuid4())
        self.container_name = f"{self.tier}-{self.container_uuid}"
        self.blob_service_client = blob.create_BlobServiceClient(self.storage_url)
        self.container_client = self.blob_service_client.create_container(
            self.container_name
        )
        self.blob_name = "test_blob"
        self.blob = "test_blob_content"
        self.container_client.upload_blob(name=self.blob_name, data=self.blob)

    def tearDown(self):
        self.container_client.delete_container()

    def test_get_blob(self):
        self.assertTrue(self.container_client.exists())
        result = asyncio.run(get_blob(self.container_client, self.blob_name))

        self.assertEqual(str(result.decode()), self.blob)

    def test_get_blob_error(self):
        blob = "nonexisting_blob"
        mock_blob_client = Mock()
        mock_blob_client.download_blob.side_effect = Exception("test error triggered")

        mock_container_client = Mock()
        mock_container_client.get_blob_client.return_value = mock_blob_client

        with self.assertRaises(GetBlobError):
            asyncio.run(get_blob(mock_container_client, blob))


class TestUploadImage(unittest.TestCase):
    def setUp(self):
        self.storage_url = BLOB_CONNECTION_STRING
        self.tier = "testuser"
        self.container_uuid = str(uuid.uuid4())
        self.container_name = f"{self.tier}-{self.container_uuid}"
        self.blob_service_client = blob.create_BlobServiceClient(self.storage_url)
        self.container_client = self.blob_service_client.create_container(
            self.container_name
        )
        self.image = Image.new("RGB", (1980, 1080), "blue")
        self.image_byte_array = io.BytesIO()
        self.image.save(self.image_byte_array, format="TIFF")
        self.image_byte = self.image.tobytes()
        self.image_hash = asyncio.run(generate_hash(self.image_byte))
        self.image_uuid = str(uuid.uuid4())
        # self.container_client.upload_blob(name=self.blob_name, data=self.blob)
        self.folder_name = "test_folder"
        self.folder_uuid = str(uuid.uuid4())
        asyncio.run(
            create_folder(
                self.container_client, self.folder_uuid, None, self.folder_name
            )
        )

    def tearDown(self):
        self.container_client.delete_container()

    def test_upload_image(self):
        expected_result = build_blob_name(self.folder_name, self.image_uuid)
        result = asyncio.run(
            upload_image(
                self.container_client,
                self.folder_name,
                self.folder_uuid,
                self.image_hash,
                self.image_uuid,
            )
        )

        self.assertEqual(result, expected_result)

    def test_upload_image_wrong_folder(self):
        """
        This test checkes if the function raises an error when the folder does not exist
        """
        not_folder_name = "not_folder"
        with self.assertRaises(CreateDirectoryError):
            asyncio.run(
                upload_image(
                    self.container_client,
                    not_folder_name,
                    str(uuid.uuid4()),
                    self.image_hash,
                    self.image_uuid,
                )
            )


class TestIsAFolder(unittest.TestCase):
    def setUp(self):
        self.storage_url = BLOB_CONNECTION_STRING
        self.tier = "testuser"
        self.container_uuid = str(uuid.uuid4())
        self.container_name = f"{self.tier}-{self.container_uuid}"
        self.blob_service_client = blob.create_BlobServiceClient(self.storage_url)
        self.container_client = self.blob_service_client.create_container(
            self.container_name
        )
        self.folder_uuid = str(uuid.uuid4())
        self.folder_name = "test_folder"
        asyncio.run(
            create_folder(
                self.container_client, str(self.folder_uuid), None, self.folder_name
            )
        )

    def tearDown(self):
        self.container_client.delete_container()

    def test_is_a_folder(self):
        self.assertTrue(self.container_client.exists())
        result = asyncio.run(is_a_folder(self.container_client, str(self.folder_uuid)))
        self.assertTrue(result)

    def test_is_not_a_folder(self):
        self.assertTrue(self.container_client.exists())
        not_folder_uuid = str(uuid.uuid4())
        result = asyncio.run(is_a_folder(self.container_client, not_folder_uuid))
        self.assertFalse(result)


class TestCreateFolder(unittest.TestCase):
    def setUp(self):
        self.storage_url = BLOB_CONNECTION_STRING
        self.tier = "testuser"
        self.container_uuid = str(uuid.uuid4())
        self.container_name = f"{self.tier}-{self.container_uuid}"
        self.blob_service_client = blob.create_BlobServiceClient(self.storage_url)
        self.container_client = self.blob_service_client.create_container(
            self.container_name
        )
        self.folder_name = "test_folder"
        self.folder_uuid = str(uuid.uuid4())

    def tearDown(self):
        self.container_client.delete_container()

    def test_create_folder(self):
        result = asyncio.run(
            create_folder(
                self.container_client, self.folder_uuid, None, self.folder_name
            )
        )
        self.assertTrue(result)
        expected_name = build_blob_name(self.folder_name, self.folder_uuid, "json")
        blob_name = self.container_client.list_blob_names()
        for blob_obj in blob_name:
            self.assertEqual(blob_obj, expected_name)

    def test_create_existing_folder(self):
        result = asyncio.run(
            create_folder(
                self.container_client, self.folder_uuid, None, self.folder_name
            )
        )
        self.assertTrue(result)
        with self.assertRaises(CreateDirectoryError):
            asyncio.run(
                create_folder(
                    self.container_client, str(uuid.uuid4()), None, self.folder_name
                )
            )

    def test_create_folder_error(self):
        folder_name = "tessst_folder"
        mock_container_client = Mock()
        mock_container_client.list_blobs.side_effect = Exception(
            "Mocking Resource not found"
        )
        with self.assertRaises(CreateDirectoryError):
            asyncio.run(create_folder(mock_container_client, folder_name))


class TestGenerateHash(unittest.TestCase):
    def setUp(self):
        self.image = Image.new("RGB", (1980, 1080), "blue")
        self.image_byte_array = io.BytesIO()
        self.image.save(self.image_byte_array, format="TIFF")
        self.image_byte = self.image.tobytes()

    def test_generate_hash(self):
        result = asyncio.run(generate_hash(self.image_byte))
        self.assertEqual(len(result), 64)

    def test_generate_hash_error(self):
        with self.assertRaises(GenerateHashError):
            asyncio.run(generate_hash("not an image"))


class TestGetFolderUUID(unittest.TestCase):
    def setUp(self):
        self.storage_url = BLOB_CONNECTION_STRING
        self.tier = "testuser"
        self.container_uuid = str(uuid.uuid4())
        self.container_name = f"{self.tier}-{self.container_uuid}"
        self.blob_service_client = blob.create_BlobServiceClient(self.storage_url)
        self.container_client = self.blob_service_client.create_container(
            self.container_name
        )
        self.folder_name = "test_folder"
        self.folder_uuid = str(uuid.uuid4())
        asyncio.run(
            create_folder(self.container_client, self.folder_uuid, self.folder_name)
        )

    def tearDown(self):
        self.container_client.delete_container()

    def test_get_folder_uuid(self):
        result = asyncio.run(get_folder_uuid(self.container_client, self.folder_name))
        self.assertEqual(result, self.folder_uuid)

    def test_get_folder_uuid_error(self):
        not_folder_name = "not_folder"
        with self.assertRaises(GetFolderUUIDError):
            asyncio.run(get_folder_uuid(self.container_client, not_folder_name))


class TestGetBlobsFromTag(unittest.TestCase):
    def setUp(self):
        self.storage_url = BLOB_CONNECTION_STRING
        self.tier = "testuser"
        self.container_uuid = str(uuid.uuid4())
        self.container_name = f"{self.tier}-{self.container_uuid}"
        self.blob_service_client = blob.create_BlobServiceClient(self.storage_url)
        self.container_client = self.blob_service_client.create_container(
            self.container_name
        )
        self.image = Image.new("RGB", (1980, 1080), "blue")
        self.image_byte_array = io.BytesIO()
        self.image.save(self.image_byte_array, format="TIFF")
        self.image_byte = self.image.tobytes()
        self.image_hash = asyncio.run(generate_hash(self.image_byte))
        self.image_uuid = str(uuid.uuid4())
        self.folder_name = "test_folder"
        self.folder_uuid = str(uuid.uuid4())
        asyncio.run(
            create_folder(
                self.container_client, self.folder_uuid, None, self.folder_name
            )
        )
        asyncio.run(
            upload_image(
                self.container_client,
                self.folder_name,
                self.folder_uuid,
                self.image_hash,
                self.image_uuid,
            )
        )

    def tearDown(self):
        self.container_client.delete_container()

    def test_get_blobs_from_tag(self):
        tag = "picture_set_uuid"
        result = asyncio.run(
            get_blobs_from_tag(self.container_client, tag, str(self.folder_uuid))
        )
        self.assertGreater(len(result), 0)

    def test_get_blobs_from_wrong_tag_value(self):
        tag = "picture_set_uuid"
        res = asyncio.run(get_blobs_from_tag(self.container_client, tag, "something"))
        self.assertEqual(len(res), 0)


class TestGetDirectories(unittest.TestCase):
    def setUp(self):
        self.storage_url = BLOB_CONNECTION_STRING
        self.tier = "testuser"
        self.container_uuid = str(uuid.uuid4())
        self.container_name = f"{self.tier}-{self.container_uuid}"
        self.blob_service_client = blob.create_BlobServiceClient(self.storage_url)
        self.container_client = self.blob_service_client.create_container(
            self.container_name
        )
        self.folder_name = "test_folder"
        self.folder_uuid = str(uuid.uuid4())
        self.image = Image.new("RGB", (1980, 1080), "blue")
        self.image_byte_array = io.BytesIO()
        self.image.save(self.image_byte_array, format="TIFF")
        self.image_byte = self.image.tobytes()
        self.image_hash = asyncio.run(generate_hash(self.image_byte))
        self.image_uuid = str(uuid.uuid4())
        asyncio.run(
            create_folder(self.container_client, self.folder_uuid, self.folder_name)
        )

    def tearDown(self):
        self.container_client.delete_container()

    def test_get_directories(self):
        try:
            result = asyncio.run(get_directories(self.container_client))
            self.assertEqual(len(result), 1)
            self.assertEqual(result.get(self.folder_name), 0)

            asyncio.run(
                upload_image(
                    self.container_client,
                    self.folder_name,
                    self.image_hash,
                    self.image_uuid,
                )
            )

            result = asyncio.run(get_directories(self.container_client))
            self.assertEqual(len(result), 1)
            self.assertEqual(result.get(self.folder_name), 1)
        except Exception as e:
            print(f"Test failed with exception: {e}")

    def test_get_directories_error(self):
        mock_container_client = Mock()
        mock_container_client.upload_blob.side_effect = FolderListError(
            "Resource not found"
        )
        with self.assertRaises(FolderListError):
            asyncio.run(get_directories(mock_container_client))


class TestMoveBlob(unittest.TestCase):
    def setUp(self):
        self.storage_url = os.environ.get("NACHET_STORAGE_URL")
        self.blob_service_client = blob.create_BlobServiceClient(self.storage_url)
        self.tier = "testuser"

        self.container_uuid_source = str(uuid.uuid4())
        self.container_name_source = f"{self.tier}-{self.container_uuid_source}"
        self.container_client_source = self.blob_service_client.create_container(
            self.container_name_source
        )

        self.container_uuid_dest = str(uuid.uuid4())
        self.container_name_dest = f"{self.tier}-{self.container_uuid_dest}"
        self.container_client_dest = self.blob_service_client.create_container(
            self.container_name_dest
        )

        self.blob_name = "test_blob"
        self.blob = "test_blob_content"
        self.container_client_source.upload_blob(name=self.blob_name, data=self.blob)

    def tearDown(self):
        self.container_client_source.delete_container()
        self.container_client_dest.delete_container()

    def test_move_blob(self):
        asyncio.run(
            move_blob(
                self.blob_name,
                self.blob_name,
                None,
                self.container_client_source,
                self.container_client_dest,
            )
        )

        with self.assertRaises(Exception):
            asyncio.run(get_blob(self.container_client_source, self.blob_name))

        blob = asyncio.run(get_blob(self.container_client_dest, self.blob_name))
        self.assertEqual(str(blob.decode()), self.blob)

    def test_move_blob_error(self):
        mock_container_client_source = Mock()
        mock_container_client_source.get_blob_client.side_effect = Exception(
            "Resource not found"
        )
        with self.assertRaises(Exception):
            asyncio.run(
                move_blob(
                    self.blob_name,
                    self.blob_name,
                    None,
                    mock_container_client_source,
                    self.container_client_dest,
                )
            )

        mock_container_client_dest = Mock()
        mock_container_client_dest.get_blob_client.side_effect = Exception(
            "Get blob Error"
        )
        with self.assertRaises(Exception):
            asyncio.run(
                move_blob(
                    self.blob_name,
                    self.blob_name,
                    None,
                    self.container_client_source,
                    mock_container_client_dest,
                )
            )


class TestGetImageCount(unittest.TestCase):
    def setUp(self):
        self.storage_url = BLOB_CONNECTION_STRING
        self.tier = "testuser"
        self.container_uuid = str(uuid.uuid4())
        self.container_name = f"{self.tier}-{self.container_uuid}"
        self.blob_service_client = blob.create_BlobServiceClient(self.storage_url)
        self.container_client = self.blob_service_client.create_container(
            self.container_name
        )
        self.image = Image.new("RGB", (1980, 1080), "blue")
        self.image_byte_array = io.BytesIO()
        self.image.save(self.image_byte_array, format="TIFF")
        self.image_byte = self.image.tobytes()
        self.image_hash = asyncio.run(generate_hash(self.image_byte))
        self.image_uuid = str(uuid.uuid4())
        self.image2_uuid = str(uuid.uuid4())
        self.folder_name = "test_folder"
        self.folder_uuid = str(uuid.uuid4())
        asyncio.run(
            create_folder(self.container_client, self.folder_uuid, self.folder_name)
        )

    def tearDown(self):
        self.container_client.delete_container()

    def test_get_image_count(self):

        result = asyncio.run(get_image_count(self.container_client, self.folder_name))
        self.assertEqual(result, 0)

        asyncio.run(
            upload_image(
                self.container_client,
                self.folder_name,
                self.folder_uuid,
                self.image_hash,
                self.image_uuid,
            )
        )
        asyncio.run(
            upload_image(
                self.container_client,
                self.folder_name,
                self.folder_uuid,
                self.image_hash,
                self.image2_uuid,
            )
        )
        # folder_path = build_blob_name(build_container_name(self.container_uuid,self.tier),self.folder_uuid)
        # print("tests folder_path: " + folder_path)
        result = asyncio.run(get_image_count(self.container_client, self.folder_name))
        self.assertEqual(result, 2)


if __name__ == "__main__":
    unittest.main()
