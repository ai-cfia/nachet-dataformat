import datetime
import hashlib
import json
import os

from datastore.db.metadata.validator import is_valid_uuid
from typing import List
from uuid import UUID


from azure.storage.blob import BlobServiceClient, ContainerClient, BlobProperties


class GenerateHashError(Exception):
    pass


class MountContainerError(Exception):
    pass


class GetBlobError(Exception):
    pass


class UploadImageError(Exception):
    pass


class UploadInferenceResultError(Exception):
    pass


class GetFolderUUIDError(Exception):
    pass


class FolderListError(Exception):
    pass


class CreateDirectoryError(Exception):
    pass


class ConnectionStringError(Exception):
    pass


"""
---- user-container based structure -----
- container name is user id
- whenever a new user is created, a new container is created with the user uuid
- inside the container, there are project folders (project name = project uuid)
- for each project folder, there is a json file with the project info and creation
date, in the container
- inside the project folder, there is an image file and a json file with
the image inference results
"""


async def generate_hash(image):
    """
    generates a hash value for the image to be used as the image name in the container
    """
    try:
        hash = hashlib.sha256(image).hexdigest()
        return hash

    except TypeError as error:
        print(error.__str__())
        raise GenerateHashError("The image is not in the correct format")
    except Exception as error:
        print(error.__str__())
        raise Exception("Unhandeled Datastore.blob.azure_storage Error")


def build_container_name(name: str, tier: str = "user") -> str:
    """
    This function builds the container name based on the tier and the name.
    We include a tier to better structure the container names in the future. Other tiers could be 'dev' or 'test-user'
    Used as a Storage Prefix

    Parameters:
    - name (str): the name of the container. Usually the container uuid
    - tier (str): the tier of the container; Default is 'user'.
    """
    if not name or name.strip() == "":
        raise ValueError("Name is required")
    return "{}-{}".format(tier, name)


def build_blob_name(folder_path: str, blob_name: str, file_type: str = None) -> str:
    """
    This function builds the blob name based on the folder name and the image uuid

    Parameters:
    - folder_path (str): The path to the folder
    - blob_name (str): Usually the uuid of the image
    - file_type (str): the type of the file (ex: png, jpg, json)
    """
    if not folder_path or folder_path.strip() == "":
        raise ValueError("Folder name is required")
    if not blob_name or blob_name.strip() == "":
        raise ValueError("Image uuid is required (parameter: blob_name)")
    if file_type is not None and file_type.strip() != "":
        return "{}/{}.{}".format(folder_path, blob_name, file_type)
    else:
        return "{}/{}".format(folder_path, blob_name)


async def mount_container(
    connection_string,
    container_uuid,
    create_container=True,
    storage_prefix="user",
    credentials="",
) -> ContainerClient:
    """
    Creates a container_client as an object that can be used in other functions.

    Parameters:
    - connection_string: the connection string to the azure storage account
    - container_uuid: the uuid of the container (usually the user uuid)
    - create_container: a boolean value to specify if the container should be created if it doesnt exist (default is True)
    - tier: the tier of the container (default is user, should be changed if the structure changes to accomodate other type of containers)

    Returns:
    - container_client: the container client object
    """
    try:
        blob_service_client = BlobServiceClient.from_connection_string(
            conn_str=connection_string, credential=credentials
        )
        if blob_service_client:
            container_name = build_container_name(str(container_uuid), storage_prefix)
            container_client = blob_service_client.get_container_client(container_name)
            if container_client.exists():
                return container_client
            elif create_container and not container_client.exists():
                container_client = blob_service_client.create_container(container_name)
                if container_client.exists():
                    return container_client
                else:
                    raise MountContainerError("Error creating container")
            elif not create_container and not container_client.exists():
                raise MountContainerError(f"Container {container_name} does not exist")
        else:
            raise ConnectionStringError("Invalid connection string")
    except ValueError as error:
        raise ConnectionStringError(
            "The given connection string is invalid: " + error.__str__()
        )
    except MountContainerError as error:
        raise error
    except ConnectionStringError as error:
        raise error
    except Exception as error:
        raise Exception("Unhandeled error:" + error.__str__())


async def get_blob(container_client, blob_name):
    """
    gets the contents of a specified blob in the user's container
    """
    try:
        blob_client = container_client.get_blob_client(str(blob_name))
        blob = blob_client.download_blob()
        blob_content = blob.readall()
        return blob_content
    except Exception as error:
        raise GetBlobError(str(error) + "\nError getting blob:" + blob_name)


async def upload_image(
    container_client, folder_path, folder_uuid, image: str, image_uuid
):
    """
    uploads the image to the specified folder within the user's container,
    if the specified folder doesnt exist, it creates it with a uuid

    Parameters:
    - container_client: the Azure container client
    - folder_name: the name of the destination folder
    - folder_uuid : uuid of the picture_set
    - image:
    """
    try:
        if not await is_a_folder(container_client, folder_uuid):
            raise CreateDirectoryError(f"Folder:{folder_uuid} does not exist")
        else:
            blob_name = build_blob_name(str(folder_path), str(image_uuid), None)
            metadata = {
                "picture_uuid": f"{str(image_uuid)}",
                "picture_set_uuid": f"{str(folder_uuid)}",
            }
            blob_client = container_client.upload_blob(blob_name, image, overwrite=True)
            blob_client.set_blob_tags(metadata)
            return blob_name
    except CreateDirectoryError or UploadImageError as e:
        raise e
    except Exception as error:
        print(error)
        raise Exception("Datastore.blob.azure_storage unHandled Error")


async def is_a_folder(
    container_client: ContainerClient, folder_uuid: str, folder_path: str = None
) -> bool:
    """
    This function checks if a folder exists in the container

    Parameters:
    - container_client: the Azure container client
    - folder_name: the name of the folder to check

    Returns: True if the folder exists, False otherwise
    """
    try:
        directories = await get_directories(container_client)
        if str(folder_uuid) in directories:
            return True
        else:
            if folder_path in directories.values():
                return True
            return False
    except FolderListError as error:
        raise error
    except Exception as e:
        raise Exception(
            "Datastore.blob.azure_storage, Unhandled Error: \n" + e.__str__()
        )


async def create_folder(
    container_client: ContainerClient,
    folder_uuid: str = None,
    path_to_folder: str = None,
    folder_name: str = None,
) -> str:
    """
    creates a folder in the user's container

    Parameters:
    - container_client: the container client object to interact with the Azure storage account
    - folder_uuid: the uuid of the folder to be created
    - folder_name: the name of the folder to be created (usually it's uuid)
    """
    try:
        # We want to enable 2 types of folder creation
        if folder_uuid is None:
            raise CreateDirectoryError("uuid not provided")
        if folder_name is None:
            folder_name = str(folder_uuid)
        if path_to_folder is None:
            # This mean this folder is at the root of the container
            folder_path = str(folder_name)
        else:
            folder_path = path_to_folder + "/" + folder_name
        # Until we allow user to manually create folder and name them
        if not await is_a_folder(container_client, folder_uuid, folder_path):

            folder_data = {
                "folder_path": folder_path,
                "date_created": str(
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ),
                "folder_uuid": str(folder_uuid),
            }
            # Usually we create a folder named General after creating a container.
            # Those folder do not have a UUID and are used to store general data
            file_name = build_blob_name(str(folder_path), str(folder_uuid), "json")
            blob_client = container_client.upload_blob(
                file_name, json.dumps(folder_data), overwrite=True
            )
            metadata = {"picture_set_uuid": f"{str(folder_uuid)}"}
            blob_client.set_blob_tags(metadata)
            return folder_path
        else:
            raise CreateDirectoryError("Folder already exists")

    except CreateDirectoryError as error:
        raise error
    except FolderListError as error:
        raise CreateDirectoryError("could not create folder")
    except Exception as error:
        print(error)
        raise Exception("Datastore unHandled Error")


async def create_dev_container_folder(
    dev_container_client, folder_uuid=None, folder_name=None, user_id=None
):
    """
    creates a folder in the dev user's container, this is used to archive data

    Parameters:
    - container_client: the container client object to interact with the Azure storage account
    - folder_uuid: the uuid of the folder to be created
    - folder_name: the name of the folder to be created (usually it's uuid)
    - user_id : the user id of the user archiving a folder
    """
    try:
        raise Exception("This function is not used")
        # We want to enable 2 types of folder creation
        if folder_uuid is None and folder_name is None:
            raise CreateDirectoryError("Folder name and uuid not provided")
        elif folder_uuid is None:
            raise CreateDirectoryError("Folder uuid not provided")
        if user_id is None:
            raise CreateDirectoryError("User id not provided")
        # Until we allow user to manually create folder and name them
        if folder_name is None:
            folder_name = folder_uuid
        if not await is_a_folder(
            dev_container_client, "{}/{}".format(user_id, folder_name)
        ):
            folder_data = {
                "folder_name": "{}/{}".format(user_id, folder_name),
                "date_created": str(
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ),
            }
            # Usually we create a folder named General after creating a container.
            # Those folder do not have a UUID and are used to store general data
            if folder_uuid is not None:
                folder_data["folder_uuid"] = str(folder_uuid)
            file_name = build_blob_name(
                "{}/{}".format(str(user_id), str(folder_name)), str(folder_name), "json"
            )  # file_name = "{}/{}/{}.json".format(user_id, folder_name, folder_name)
            blob_client = dev_container_client.upload_blob(
                file_name, json.dumps(folder_data), overwrite=True
            )
            metadata = {"picture_set_uuid": f"{str(folder_uuid)}"}
            blob_client.set_blob_tags(metadata)
            return True
        else:
            raise CreateDirectoryError("Folder already exists")

    except CreateDirectoryError as error:
        raise error
    except FolderListError as error:
        print(error)
        raise CreateDirectoryError("Error getting folder list, could not create folder")
    except Exception as error:
        print(error)
        raise Exception("Datastore unHandled Error")


async def upload_inference_result(container_client, folder_name, result, hash_value):
    """
    uploads the inference results json file to the specified folder
    in the users container
    """
    try:
        folder_uuid = await get_folder_uuid(container_client, folder_name)
        if folder_uuid:
            json_name = build_blob_name(str(folder_name), hash_value, "json")
            container_client.upload_blob(json_name, result, overwrite=True)
            return True

    except UploadInferenceResultError as error:
        print(error)
        return False


# This seems useless if the path are uuids
async def get_folder_uuid(container_client:ContainerClient, folder_path) -> List[UUID]:
    """
    gets the uuid of a folder in the user's container given the folder name by
    iterating through the folder json files and extracting the name
    to match given folder name
    """
    try:
        raise Exception("This function is not used")
        blob_list = container_client.list_blobs(name_starts_with=folder_path)
        for blob in blob_list:
            # if a folder exist a ...<folder_name>/<folder_uuid>.json exists
            if (
                blob.name.split(".")[-1] == "json"
                and is_valid_uuid((blob.name.split("/")[-1]).split(".")[0])
            ):
                folder_json = await get_blob(container_client, blob.name)

                if folder_json:
                    folder_json = json.loads(folder_json)

                    if "folder_uuid" not in folder_json:
                        raise GetFolderUUIDError(
                            "Folder UUID not found in folder metadata"
                        )
                    return folder_json["folder_uuid"]
        raise GetFolderUUIDError(f"Folder '{folder_path}' not found")
    except GetFolderUUIDError as error:
        raise error
    except Exception as error:
        print(error)
        raise Exception("Datastore.blob.azure_storage unHandled Error")


async def get_image_count(container_client: ContainerClient, folder_path):
    """
    gets the number of images in a folder in the user's container
    """
    try:
        if container_client.exists():
            blob_list = container_client.list_blobs(name_starts_with=folder_path)
            count = 0
            for blob in blob_list:

                if (blob.name.split("/")[0] == folder_path) and (
                    blob.name.split(".")[-1] != "json"
                ):
                    count += 1
            return count
        else:
            raise GetFolderUUIDError("Container does not exist")
    except GetFolderUUIDError as error:
        print(error)
        return False


async def get_directories(container_client):
    """
    returns a list of folder names in the user's container
    """
    try:
        directories = {}
        blob_list = container_client.list_blobs()
        for blob in blob_list:
            # if .../<uuid>.json exists
            if blob.name.split(".")[-1] == "json" and is_valid_uuid(
                blob.name.split("/")[-1].split(".")[0]
            ):
                json_blob = await get_blob(container_client, blob.name)
                if json_blob:
                    folder_json = json.loads(json_blob)
                    directories[str(folder_json["folder_uuid"])] = folder_json[
                        "folder_path"
                    ]
        return directories
    except FolderListError as error:
        raise error
    except Exception as error:
        raise FolderListError(f"Error getting directories: {str(error)}")


async def download_container(container_client, container_name, local_dir):
    """
    This function downloads all the files from a container in a storage account
    to the local directory "test"

    This serves as a way to locally download the container files for processing and importing within the db

    Parameters:
    - container_client: the Azure container client
    - local_dir: the local directory to download the files to

    Returns: None
    """
    try:
        # List blobs in the container
        blob_list = container_client.list_blobs()
        # Iterate through each blob
        for i, blob in enumerate(blob_list):
            # Create a blob client
            blob_client = container_client.get_blob_client(
                container=container_name, blob=blob
            )
            # Download the blob
            local_file_path = build_blob_name(str(local_dir), str(blob.name))
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)

            with open(local_file_path, "wb") as file:
                blob_data = blob_client.download_blob(blob=blob.name)
                blob_data.readinto(file)
                #  nb_downloaded_files = i
    except Exception:
        raise Exception("Error downloading container")


async def get_blobs_from_tag(
    container_client: ContainerClient, tag: str, tag_value: str
):
    """
    This function gets the names of blobs in a picture set folder

    Parameters:
    - container_client: the Azure container client
    - tag: the tag to search for in the blobs ex: 'folder_name'

    Returns: the list of blobs
    """
    try:
        # The find_blobs_by_tags methods should return a list of blobs with the given tag
        # blob_list = list(container_client.find_blobs_by_tags(filter_expression=tag))

        # Without the find_blobs_by_tags method
        blob_list = list(container_client.list_blobs(include=["tags"]))
        result: list[BlobProperties] = []
        for blob in blob_list:
            if tag in blob.get("tags") and blob.get("tags")[tag] == tag_value:
                result.append(blob)
        if len(result) > 0:
            return result
        else:
            return []
    except Exception as e:
        print(f"Exception during find_blobs_by_tags: {e}")


async def delete_folder_path(container_client: ContainerClient, folder_path):
    """
    This function deletes a folder in the user's container

    Parameters:
    - container_client: the Azure container client
    - folder_path: path of the folder related to the folder to delete

    Returns: True if the folder is deleted, False otherwise
    """
    try:
        if not container_client.exists():
            raise GetFolderUUIDError("Container does not exist")
        blobs = container_client.list_blobs(name_starts_with=folder_path)
        for blob in blobs:
            await container_client.delete_blob(blob.name)
        return True

    except GetFolderUUIDError:
        return False
    except Exception:
        return False
    
async def delete_blob(container_client: ContainerClient, blob_name):
    """
    This function deletes a blob in the user's container

    Parameters:
    - container_client: the Azure container client
    - blob_name: name of the blob to delete

    Returns: True if the blob is deleted, False otherwise
    """
    try:
        if not container_client.exists():
            raise GetFolderUUIDError("Container does not exist")
        await container_client.delete_blob(blob_name)
        return True

    except GetFolderUUIDError:
        return False
    except Exception:
        return False

async def delete_container(container_client: ContainerClient):
    """
    This function deletes a container in the user's container

    Parameters:
    - container_client: the Azure container client

    Returns: True if the container is deleted, False otherwise
    """
    try:
        if not container_client.exists():
            raise GetFolderUUIDError("Container does not exist")
        await container_client.delete_container()
        return True

    except GetFolderUUIDError:
        return False
    except Exception:
        return False


async def delete_folder(container_client: ContainerClient, picture_set_id):
    """
    This function deletes a folder in the user's container

    Parameters:
    - container_client: the Azure container client
    - picture_set_id: id of the picture set related to the folder to delete

    Returns: True if the folder is deleted, False otherwise
    """
    try:
        raise Exception("This function is not used")
        blobs = await get_blobs_from_tag(container_client, picture_set_id)
        for blob in blobs:
            container_client.delete_blob(blob.name)
        return True

    except GetFolderUUIDError:
        return False
    except Exception:
        return False


async def move_blob(
    blob_name_source,
    blob_name_dest,
    folder_uuid,
    container_client_source,
    container_client_destination,
):
    """
    This function move a blob from a container to another

    Parameters:
    - blob_name: the name of the blob to move
    - container_client_source: the Azure container client where the blob is
    - container_client_destination : the Azure container client where the blob will be moved
    """
    try:
        blob_client = container_client_source.get_blob_client(blob_name_source)

        blob = blob_client.download_blob().readall()

        blob_client_destination = container_client_destination.get_blob_client(
            blob_name_dest
        )

        blob_client_destination.upload_blob(blob, overwrite=True)
        metadata = {"picture_set_uuid": f"{str(folder_uuid)}"}
        blob_client_destination.set_blob_tags(metadata)

        container_client_source.delete_blob(blob_name_source)
        return True
    except Exception as e:
        raise Exception(f"Error moving blob: {e}")
