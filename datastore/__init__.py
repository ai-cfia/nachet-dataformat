"""
This module is responsible for handling the user data in the database 
and the user container in the blob storage.
"""

import json
import datastore.db.queries.user as user
import datastore.db.queries.group as group
import datastore.db.queries.picture as picture
import datastore.db.queries.container as container_db
import datastore.db.metadata.picture_set as data_picture_set
import datastore.blob as blob
import datastore.blob.azure_storage_api as azure_storage
from azure.storage.blob import BlobServiceClient, ContainerClient

from typing import Optional
from dotenv import load_dotenv

from psycopg import Cursor
from uuid import UUID

load_dotenv()


class UserAlreadyExistsError(Exception):
    pass


class UserNotOwnerError(Exception):
    pass


class BlobUploadError(Exception):
    pass


class ContainerCreationError(Exception):
    pass


class FolderCreationError(Exception):
    pass


class Container():
    def __init__(self, id: UUID, tier: str = "user",name: str = None, user_id: UUID = None,group_id: UUID = None):
        if id is None:
            raise ValueError("The container id must be provided")
        else:
            self.id = id
        self.storage_prefix = tier
        self.container_client: Optional[ContainerClient]  = None
        self.name = name
        self.group_ids = [UUID]
        if group_id is not None:
            self.group_ids.append(group_id)
        self.user_ids = [UUID]
        if user_id is not None:
            self.user_ids.append(user_id)
        self.folders ={}

    # This could be achieved by fetching the storage and performing Azure API calls
    def fetch_all_folders_metadata(self,cursor:Cursor):
        """
        This function retrieves all the folders metadata from the database then stores it in the container object.

        Parameters:
        - cursor: The cursor object to interact with the database.
        """
        db_folders = picture.get_picture_sets_by_container(cursor, self.id)
        for folder in db_folders:
            folder_id = folder[0]
            folder_metadata = data_picture_set.PictureSet(picture_set_id=folder_id, name=folder[1], link=folder[2], pictures=folder[3])
            self.folders[str(folder_id)] = folder_metadata.model_dump()
    
    #Note: The default credentials have a time limit of 5 minutes
    def get_container_client(self, connection_str: str,credentials:str):
        """
        This function gets the container client from the blob storage if the container exists.

        Parameters:
        - connection_str (str): The connection string to connect with the Azure storage account
        - credentials (str): The credentials to connect with the Azure storage account
        """
        self.container_client = azure_storage.mount_container(
            connection_string=connection_str, 
            container_uuid=self.id, 
            create_container=False,
            storage_prefix=self.storage_prefix,
            credentials=credentials)

    def get_id(self):
        return self.id
    
    def add_user(self,cursor:Cursor, user_id: UUID, performed_by: UUID): 
        """
        This function adds a user to the container rights.

        Parameters:
        - cursor: The cursor object to interact with the database.
        - user_id (str): The UUID of the user.
        """
        if not container_db.has_user_access_to_container(cursor, user_id, self.id):
            if not container_db.has_user_group_access_to_container(cursor, user_id, self.id):
                # Link the container to the user in the database
                container_db.add_user_to_container(cursor, user_id, self.id, performed_by)
        self.user_ids.append(user_id)

    def add_group(self,cursor:Cursor, group_id: UUID, performed_by: UUID): 
        # Link the container to the user in the database
        container_db.add_group_to_container(cursor, group_id, self.id, performed_by)
        self.group_ids.append(group_id)

    async def create_container_storage(self, connection_str: str,credentials:str):
        """
        Create a container in the blob storage
        
        Parameters:
        - connection_str (str): The connection string to connect with the Azure storage account
        - credentials (str): The credentials to connect with the Azure storage account
        """
        blob_service_client = BlobServiceClient.from_connection_string(
            conn_str=connection_str,
            credential=credentials
        )
        container_client = blob_service_client.create_container(
            azure_storage.build_container_name(str(self.id), self.storage_prefix)
        )
        if not container_client.exists():
            raise ContainerCreationError(
            "Error creating the user container: container does not exists"
        )
        self.container_client = container_client
    
    async def create_folder(self,cursor:Cursor, performed_by: UUID, folder_name: str="General",nb_pictures=0)->UUID: 
        """
        Create a folder (picture_set) in the container

        Parameters:
        - cursor: The cursor object to interact with the database.
        - performed_by (str): The UUID of the user creating the folder.
        - folder_name (str): The name of the folder.
        - nb_pictures (int): The number of pictures in the folder.

        Returns:
        - The UUID of the folder created.
        """
        if self.container_client is None:
            raise ValueError(f"The container client must be set before creating a folder in the Container {self.name}: id:{self.id}")
        if not user.is_a_user_id(cursor=cursor, user_id=performed_by):
            raise user.UserNotFoundError(
                f"User not found based on the given id: {performed_by}"
            )
        pic_set_metadata = data_picture_set.build_picture_set_metadata(
            user_id=performed_by, nb_picture=nb_pictures
        )
        pic_set_id = picture.new_picture_set(
            cursor=cursor, 
            pic_set_metadata=pic_set_metadata,
            user_id=performed_by,
            folder_name=folder_name,
            container_id=self.id
        )
        if (await azure_storage.create_folder(
            self.container_client, str(pic_set_id), folder_name
        )):
            # add the folder to the container structure
            self.folders[str(pic_set_id)] = []
            return pic_set_id
        else:
            raise FolderCreationError(f"Error creating the folder {folder_name} in the Container {self.name}: id:{self.id}")

    async def upload_pictures(self,cursor:Cursor, user_id: UUID, hashed_pictures, picture_set_id: UUID=None)->list[UUID]:
        """
        Upload a picture that we don't know the seed to the user container

        Parameters:
        - cursor: The cursor object to interact with the database.
        - user_id (str): The UUID of the user.
        - hashed_pictures ([str]): The images to upload.
        - picture_set_id: The id of the picture set to upload the pictures to.
        """
        # check if the user was added to the Container rights
        if user_id not in self.user_ids:
            raise UserNotOwnerError(
                f"User can't access this Container, user uuid :{user_id}, Container id : {self.id}"
            )
        # Create a folder if not provided
        if picture_set_id is None:
            picture_set_id= self.create_folder(
                cursor =cursor, 
                performed_by=user_id,
                folder_name=None,
                nb_pictures=len(hashed_pictures)
            )
        pic_ids = []
        for picture_hash in hashed_pictures:
            link = azure_storage.build_blob_name(
                str(self.id), str(picture_set_id), picture_hash
            )
            description = "Uploaded through the API"
            picture_metadata = data_picture_set.PictureMetadata(
                link=link,
                description=description
            )
            # Create picture instance in DB
            picture_id = picture.new_picture_unknown(
                cursor=cursor,
                picture=picture_metadata,
                nb_objects=len(hashed_pictures),
                picture_set_id=picture_set_id,
            )
            # Upload the picture to the Blob Storage
            response = await azure_storage.upload_image(
                self.container_client,
                str(picture_set_id),
                str(picture_set_id),
                picture_hash,
                str(picture_id),
            )
            if not response:
                raise BlobUploadError("Error uploading the picture")
            pic_ids.append(picture_id)
        return pic_ids

class User:
    def __init__(self, email: str, id: UUID = None, tier: str = "user"):
        if id is None:
            raise ValueError("The user id must be provided")
        self.id = id
        self.email = email
        self.tier = tier
        self.containers = Optional[list[Container]] = None

    def get_email(self):
        return self.email

    def get_id(self):
        return self.id
    
    
    async def create_user_container(self,cursor:Cursor, connection_str:str, name:str, user_id:UUID, is_public=False, storage_prefix="user") -> Container:
        """
        This function creates a container in the database and the blob storage.
        """
        container_id = container_db.create_container(
            cursor=cursor, name=name, user_id=user_id, is_public=is_public, storage_prefix=storage_prefix
        )
        container_obj = Container(container_id, storage_prefix, name, user_id)

        container_obj.create_container_storage(connection_str=connection_str)
        container_obj.add_user(cursor, user_id, user_id)
        container_obj.create_folder(cursor, user_id)
        return container_obj
        
    def fetch_all_containers(self,cursor:Cursor, connection_str:str,credentials:str):
        db_containers = container_db.get_user_containers(cursor, self.id)
        for container in db_containers:
            if container[1] is None:
                name = container[3]
            else:
                name = container[1]
            container_obj = Container(id=container[0], tier=container[4], name=name, user_id=self.id)
            container_obj.get_container_client(connection_str=connection_str,credentials=credentials)
            container_obj.fetch_all_folders_metadata(cursor)
            self.add_container(container_obj)

    def add_container(self, container: Container):
        if self.containers is None:
            self.containers = [container]
        else:
            self.containers.append(container)


class Group:
    def __init__(self, name: str, id: UUID = None):
        if id is None:
            raise ValueError("The group id must be provided")
        self.id = id
        self.name = name
        self.tier = "group"
        self.group_container = None

    def get_name(self):
        return self.name

    def get_id(self):
        return self.id
    
    async def create_group_container(self,cursor:Cursor, connection_str:str, name:str, user_id:UUID, is_public=False, storage_prefix="group") -> Container:
        """
        This function creates a container in the database and the blob storage.
        """
        container_id = container_db.create_container(
            cursor=cursor, name=name, user_id=user_id, is_public=is_public, storage_prefix=storage_prefix
        )
        container_obj = Container(container_id, storage_prefix, name, user_id)
        container_obj.create_container_storage(connection_str=connection_str)
        container_obj.add_group(cursor, self.id, user_id)
        container_obj.create_folder(cursor, user_id)
        self.container = container_obj
        return container_obj


async def get_user(cursor, email) -> User:
    """
    Get a user from the database

    Parameters:
    - email (str): The email of the user.
    - cursor: The cursor object to interact with the database.
    """
    user_id = user.get_user_id(cursor, email)
    return User(email=email, id=user_id, tier="user")



async def new_user(cursor:Cursor, email:str, connection_string, tier="user") -> User:
    """
    Create a new user in the database and blob storage.

    Parameters:
    - email (str): The email of the user.
    - cursor: The cursor object to interact with the database.
    - connection_string: The connection string to connect with the Azure storage account
    """
    try:
        # Register the user in the database
        if user.is_user_registered(cursor, email):
            raise UserAlreadyExistsError("User already exists")
        user_uuid = user.register_user(cursor, email)
        # Create the user object
        user_obj = User(email, user_uuid, tier)        
        # Create the user container in the blob storage
        container_obj = await User.create_user_container(
            cursor=cursor, 
            connection_string=connection_string, 
            name=None,
            user_id=user_uuid,
            is_public=False,
            storage_prefix=tier)
        user_obj.add_container(container_obj)
        return user_obj
    except azure_storage.CreateDirectoryError as e:
        raise FolderCreationError("Error creating the user folder:" + str(e))
    except UserAlreadyExistsError:
        raise
    except ContainerCreationError:
        raise
    except Exception as e:
        # print(e)
        raise Exception("Datastore Unhandled Error " + str(e))

# Depracated, soon to be deleted
async def get_picture_sets_info(cursor, user_id: str):
    """This function retrieves the picture sets names and number of pictures from the database.

    Args:
        user_id (str): id of the user
    """
    # Check if user exists
    if not user.is_a_user_id(cursor=cursor, user_id=user_id):
        raise user.UserNotFoundError(f"User not found based on the given id: {user_id}")

    result = {}
    picture_sets = picture.get_user_picture_sets(cursor, user_id)
    for picture_set in picture_sets:
        picture_set_id = picture_set[0]
        picture_set_name = picture_set[1]
        nb_picture = picture.count_pictures(cursor, picture_set_id)
        result[str(picture_set_id)] = [picture_set_name, nb_picture]
    return result

# Depracated, soon to be deleted
async def get_picture_set_pictures(cursor, user_id, picture_set_id, container_client):
    """
    This function retrieves the pictures of a picture set from the database.
    """
    try:
        # Check if user exists
        if not user.is_a_user_id(cursor=cursor, user_id=str(user_id)):
            raise user.UserNotFoundError(
                f"User not found based on the given id: {user_id}"
            )
        # Check if picture set exists
        if not picture.is_a_picture_set_id(cursor, picture_set_id):
            raise picture.PictureSetNotFoundError(
                f"Picture set not found based on the given id: {picture_set_id}"
            )
        # Check user is owner of the picture set
        if str(picture.get_picture_set_owner_id(cursor, picture_set_id)) != str(
            user_id
        ):
            raise UserNotOwnerError(
                f"User can't access this folder, user uuid :{user_id}, folder name : {picture_set_id}"
            )
        picture_set_name = picture.get_picture_set_name(cursor, picture_set_id)
        # Get the pictures
        pictures = picture.get_picture_set_pictures(cursor, picture_set_id)
        result = []
        if len(pictures) == 0:
            return result
        elif len(pictures) != await azure_storage.get_image_count(
            container_client, str(picture_set_name)
        ):
            raise Warning(
                "The number of pictures in the database '"
                + str(len(pictures))
                + "' does not match the number of pictures in the blob storage"
            )
        for pic in pictures:
            pic_id = pic[0]
            pic_metadata = pic[1]
            pic_metadata["id"] = pic_id
            if "link" in pic_metadata:
                blob_link = pic_metadata["link"]
            else:
                blob_link = azure_storage.build_blob_name(
                    str(picture_set_name), str(pic_id), None
                )
            blob_obj = azure_storage.get_blob(container_client, blob_link)
            pic_metadata.pop("link", None)
            pic_metadata["blob"] = blob_obj
            result.append(pic_metadata)
        return result
    except (
        user.UserNotFoundError,
        picture.PictureSetNotFoundError,
        UserNotOwnerError,
    ) as e:
        raise e
    except Exception as e:
        # print(e)
        raise Exception("Datastore Unhandled Error " + str(e))

# Depracated, soon to be deleted
async def delete_picture_set_permanently(
    cursor, user_id, picture_set_id, container_client
):
    """
    Delete a picture set from the database and the blob storage

    Args:
        cursor: The cursor object to interact with the database.
        user_id (str): id of the user
        picture_set_id (str): id of the picture set to delete
        container_client: The container client of the user.
    """
    try:
        # Check if user exists
        if not user.is_a_user_id(cursor=cursor, user_id=user_id):
            raise user.UserNotFoundError(
                f"User not found based on the given id: {user_id}"
            )
        # Check if picture set exists
        if not picture.is_a_picture_set_id(cursor, picture_set_id):
            raise picture.PictureSetNotFoundError(
                f"Picture set not found based on the given id: {picture_set_id}"
            )
        # Check user is owner of the picture set
        if picture.get_picture_set_owner_id(cursor, picture_set_id) != user_id:
            raise UserNotOwnerError(
                f"User can't delete this folder, user uuid :{user_id}, folder name : {picture_set_id}"
            )
        # Check if the picture set is the default picture set
        general_folder_id = user.get_default_picture_set(cursor, user_id)
        if general_folder_id == picture_set_id:
            raise picture.PictureSetDeleteError(
                f"User can't delete the default picture set, user uuid :{user_id}"
            )

        # Delete the folder in the blob storage
        await azure_storage.delete_folder(container_client, str(picture_set_id))
        # Delete the picture set
        picture.delete_picture_set(cursor, picture_set_id)

        return True
    except (
        user.UserNotFoundError,
        picture.PictureSetNotFoundError,
        picture.PictureSetDeleteError,
        UserNotOwnerError,
    ) as e:
        raise e
    except Exception as e:
        # print(e)
        raise Exception("Datastore Unhandled Error " + str(e))

# Depracated, soon to be deleted
async def upload_pictures(
    cursor, user_id, hashed_pictures, container_client, picture_set_id=None
):
    """
    Upload a picture that we don't know the seed to the user container

    Parameters:
    - cursor: The cursor object to interact with the database.
    - user_id (str): The UUID of the user.
    - hashed_pictures ([str]): The images to upload.
    - container_client: The container client of the user.
    """
    try:

        if not user.is_a_user_id(cursor=cursor, user_id=user_id):
            raise user.UserNotFoundError(
                f"User not found based on the given id: {user_id}"
            )

        empty_picture = data_picture_set.build_picture_set_metadata(
            user_id, len(hashed_pictures)
        )

        default_picture_set = str(user.get_default_picture_set(cursor, user_id))
        if picture_set_id is None or str(picture_set_id) == default_picture_set:
            picture_set_id = default_picture_set
            folder_name = "General"
        else:
            folder_name = picture.get_picture_set_name(cursor, picture_set_id)
            if folder_name is None:
                folder_name = str(picture_set_id)
        pic_ids = []
        for picture_hash in hashed_pictures:
            # Create picture instance in DB
            picture_id = picture.new_picture_unknown(
                cursor=cursor,
                picture=empty_picture,
                nb_objects=len(hashed_pictures),
                picture_set_id=picture_set_id,
            )
            # Upload the picture to the Blob Storage
            response = await azure_storage.upload_image(
                container_client,
                str(folder_name),
                str(picture_set_id),
                picture_hash,
                str(picture_id),
            )
            # Update the picture metadata in the DB
            data = {
                "link": azure_storage.build_blob_name(
                    folder_name, str(picture_id), None
                ),
                "description": "Uploaded through the API",
            }

            if not response:
                raise BlobUploadError("Error uploading the picture")

            picture.update_picture_metadata(
                cursor, str(picture_id), json.dumps(data), len(hashed_pictures)
            )
            pic_ids.append(picture_id)
        return pic_ids
    except BlobUploadError or azure_storage.UploadImageError:
        raise BlobUploadError("Error uploading the picture")
    except user.UserNotFoundError:
        raise
    except Exception as e:
        # print(e)
        raise Exception("Datastore Unhandled Error " + str(e))


async def create_group(
    cursor : Cursor, group_name: str, user_id: UUID, connection_string: str
) -> Group:
    """
    Create a new group in the database

    Parameters:
    - cursor: The cursor object to interact with the database.
    - group_name (str): The name of the group.
    - user_id (str): The UUID of the user creating the group.
    - connection_string: The connection string to connect with the Azure storage account
    """
    try:
        group_id = group.create_group(cursor, group_name, user_id)
        group_obj = Group(group_name, group_id)
        # Create the user container in the blob storage
        if connection_string is not None:
            group_obj.create_group_container(
                cursor=cursor, 
                connection_str=connection_string, 
                name=None, 
                user_id=user_id,
                is_public=False,
                storage_prefix="group")
        return group_obj
    except Exception as e:
        raise Exception("Datastore Unhandled Error " + str(e))

async def create_container(
    cursor: Cursor, connection_str:str, container_name :str=None,user_id:UUID=None,is_public=False,storage_prefix="user",add_user_to_storage : bool = False) -> Container:
    """
    This function creates a container in the database and the blob storage.
    """
    if user_id is None:
        raise ValueError("The user id must be provided")
    container_id = container_db.create_container(
        cursor=cursor, name=container_name, user_id=user_id, is_public=is_public, storage_prefix=storage_prefix
    )
    container_obj = Container(container_id, storage_prefix, container_name, user_id)

    container_obj.create_container_storage(connection_str=connection_str)
    if add_user_to_storage:
        container_obj.add_user(cursor, user_id, user_id)
    container_obj.create_folder(cursor, user_id)
    return container_obj
