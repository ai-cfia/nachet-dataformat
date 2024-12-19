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

from pydantic import BaseModel

from typing import List, Optional, Dict
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


class Folder(BaseModel):
    id: UUID
    name: str
    path: str
    children: List[UUID]
    pictures: List[UUID]
    parent_id: Optional[UUID] = None


class Container:
    def __init__(
        self, id: UUID, tier: str = "user", name: str = None, public: bool = False
    ):
        if id is None:
            raise ValueError("The container id must be provided")
        else:
            self.id = id
        self.storage_prefix = tier
        self.container_client: Optional[ContainerClient] = None
        if name is None:
            self.name = str(id)
        else:
            self.name = name
        self.group_ids: List[UUID] = []
        self.user_ids: List[UUID] = []
        self.folders: Dict[UUID, Folder] = {}
        self.is_public = public
        self.path = azure_storage.build_container_name(
            str(self.id), self.storage_prefix
        )

    # This could be achieved by fetching the storage and performing Azure API calls
    def fetch_all_folders_metadata(self, cursor: Cursor):
        """
        This function retrieves all the folders metadata from the database then stores it in the container object.

        Parameters:
        - cursor: The cursor object to interact with the database.
        """
        db_folders = picture.get_picture_sets_by_container(cursor, self.id)
        # the root folders should be the first one to be iterated over
        list_folder_parent: List[Folder] = []
        for folder in db_folders:
            folder_id = folder[0]
            folder_metadata = Folder(
                id=folder_id,
                name=folder[1],
                path=folder[2],
                children=[],
                pictures=folder[3],
                parent_id=folder[4],
            )
            if folder_metadata.parent_id is not None:
                list_folder_parent.append(folder_metadata)
            self.folders[folder_id] = folder_metadata
        # loop through the folders to add the children
        for folder in list_folder_parent:
            self.folders[folder.parent_id].children.append(folder.id)

    def fetch_all_data(self, cursor: Cursor):
        """
        This function retrieves all the users and groups that have access to the container.
        """
        db_container = container_db.get_container(cursor, self.id)
        self.user_ids.clear()
        self.group_ids.clear()
        self.name = db_container[0]
        self.is_public = db_container[1]
        self.storage_prefix = db_container[2]
        self.path = db_container[3]
        for user_id in db_container[5]:
            self.user_ids.append(user_id)
        for group_id in db_container[6]:
            self.group_ids.append(group_id)
        self.fetch_all_folders_metadata(cursor)

    def __remove_folder_and_children(self, folder_id: UUID):
        """
        Remove the children of a folder from the object.
        """
        for child in self.folders[folder_id].children:
            self.remove_folder_children(child)
        self.folders.pop(folder_id)

    # The default credentials have a time limit of 5 minutes
    async def get_container_client(self, connection_str: str, credentials: str):
        """
        This function gets the container client from the blob storage if the container exists and attach it to the object attribute.

        Parameters:
        - connection_str (str): The connection string to connect with the Azure storage account
        - credentials (str): The credentials to connect with the Azure storage account
        """
        self.container_client = await azure_storage.mount_container(
            connection_string=connection_str,
            container_uuid=self.id,
            create_container=False,
            storage_prefix=self.storage_prefix,
            credentials=credentials,
        )

    def get_id(self):
        return self.id

    def add_user(self, cursor: Cursor, user_id: UUID, performed_by: UUID):
        """
        This function adds a user to the container rights.

        Parameters:
        - cursor: The cursor object to interact with the database.
        - user_id (str): The UUID of the user.
        """
        if not container_db.has_user_access_to_container(cursor, user_id, self.id):
            if not container_db.has_user_group_access_to_container(
                cursor, user_id, self.id
            ):
                # Link the container to the user in the database
                container_db.add_user_to_container(
                    cursor, user_id, self.id, performed_by
                )
        self.user_ids.append(user_id)

    def add_group(self, cursor: Cursor, group_id: UUID, performed_by: UUID):
        # Link the container to the user in the database
        container_db.add_group_to_container(cursor, group_id, self.id, performed_by)
        self.group_ids.append(group_id)

    async def create_storage(self, connection_str: str, credentials: str):
        """
        Create a container in the blob storage

        Parameters:
        - connection_str (str): The connection string to connect with the Azure storage account
        - credentials (str): The credentials to connect with the Azure storage account
        """
        blob_service_client = BlobServiceClient.from_connection_string(
            conn_str=connection_str, credential=credentials
        )
        # To not restrict the Users in unique naming, we will use the
        # container id to name the Azure container
        container_client = blob_service_client.create_container(self.path)
        if not container_client.exists():
            raise ContainerCreationError(
                "Error creating the user container: container does not exists"
            )
        self.container_client = container_client

    async def create_folder(
        self,
        cursor: Cursor,
        performed_by: UUID,
        folder_name: str = None,
        nb_pictures=0,
        parent_folder_id: UUID = None,
    ) -> UUID:
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
            raise ValueError(
                f"The container client must be set before creating a folder in the Container {self.name}: id:{self.id}"
            )
        if not user.is_a_user_id(cursor=cursor, user_id=performed_by):
            raise user.UserNotFoundError(
                f"User not found based on the given id: {performed_by}"
            )
        # Check if folder exists in the database in the container & parent folder
        if folder_name is not None:
            # This is also a trigger in the db to create the folder
            if picture.already_contain_folder(
                cursor=cursor,
                container_id=self.id,
                parent_id=parent_folder_id,
                folder_name=folder_name,
            ):
                raise FolderCreationError(
                    f"Folder already exists in the container: {folder_name} under the folder {parent_folder_id}. Name must be unique inside the same folder."
                )
        pic_set_metadata = data_picture_set.build_picture_set_metadata(
            user_id=performed_by, nb_picture=nb_pictures
        )
        pic_set_id = picture.new_picture_set(
            cursor=cursor,
            picture_set_metadata=pic_set_metadata,
            user_id=performed_by,
            folder_name=folder_name,
            container_id=self.id,
            parent_id=parent_folder_id,
        )
        #This is a trigger in the db to create the folder
        if folder_name is None:
            folder_name = str(pic_set_id)
        parent_path = None
        # Add the folder to the parent folder
        if parent_folder_id is not None:
            self.folders[parent_folder_id].children.append(pic_set_id)
            parent_path = self.folders[parent_folder_id].path
        folder_path = await azure_storage.create_folder(
            self.container_client, str(pic_set_id), parent_path, folder_name
        )
        folder = Folder(
            id=pic_set_id,
            name=folder_name,
            children=[],
            pictures=[],
            parent_id=parent_folder_id,
            path=folder_path,
        )
        self.folders[pic_set_id] = folder
        return pic_set_id

    async def upload_pictures(
        self,
        cursor: Cursor,
        user_id: UUID,
        hashed_pictures: List[str],
        folder_id: UUID = None,
    ) -> list[UUID]:
        """
        Upload a picture that we don't know the content to the user container.

        This function allows to create a folder for all the provided pictures but does
        not allow to name the folder. Use 'create_folder()' to create a folder with a name then provide the id.

        Parameters:
        - cursor: The cursor object to interact with the database.
        - user_id (str): The UUID of the user uploading the pictures.
        - hashed_pictures ([str]): The images to upload.
        - picture_set_id: The id of the picture set (folder) to upload the pictures to.

        Returns:
        - A list of UUID of the pictures created ([UUID]).
        """
        # check if the user was added to the Container rights
        if user_id not in self.user_ids:
            raise UserNotOwnerError(
                f"User can't access this Container, user uuid :{user_id}, Container id : {self.id}"
            )
        # Create a folder if not provided
        if folder_id is None:
            folder_id = self.create_folder(
                cursor=cursor,
                performed_by=user_id,
                folder_name=None,
                nb_pictures=len(hashed_pictures),
            )
        # folder_name = picture.get_picture_set_name(cursor, folder_id)
        folder = self.folders[folder_id]
        # Get the path of the folder in the Blob Storage
        folder_name = folder.name
        folder_path = folder.path
        pic_ids: List[UUID] = []
        for picture_hash in hashed_pictures:

            description = "Uploaded through the API"
            picture_metadata = data_picture_set.PictureMetadata(
                link=folder_path + "/", description=description
            )
            # Create picture instance in DB
            picture_id = picture.new_picture_unknown(
                cursor=cursor,
                picture=picture_metadata.model_dump_json(),
                nb_objects=len(hashed_pictures),
                picture_set_id=folder_id,
            )

            # Upload the picture to the Blob Storage
            response = await azure_storage.upload_image(
                self.container_client,
                str(folder_path),
                str(folder_id),
                picture_hash,
                str(picture_id),
            )
            if not response:
                raise BlobUploadError("Error uploading the picture")
            pic_ids.append(picture_id)
        self.folders[folder_id].pictures.extend(pic_ids)
        return pic_ids

    async def get_folder_pictures(self, cursor: Cursor, folder_id: UUID, user_id: UUID):
        """
        This function downloads all the pictures of a folder from the blob storage.

        Parameters:
        - cursor: The cursor object to interact with the database.
        - folder_id (str): The UUID of the folder.
        - user_id (str): The UUID of the user.

        Returns:
        - A list of the pictures of the folder.
        """
        # Check if user exists
        if self.container_client is None or not self.container_client.exists():
            raise ValueError(
                "The container client must be set before downloading pictures.\n Use 'get_container_client()' to set the container client."
            )
        self.fetch_all_data(cursor)
        if not user.is_a_user_id(cursor=cursor, user_id=str(user_id)):
            raise user.UserNotFoundError(
                f"User not found based on the given id: {user_id}"
            )
        if not (folder_id in self.folders.keys()):
            raise FolderCreationError(
                f"Folder does not exist in the container: {folder_id}"
            )
        # Check if user has access to the container
        if not user_id in self.user_ids:
            raise UserNotOwnerError(
                f"User can't access this Container, user uuid :{user_id}, Container id : {self.id}"
            )
        # Get the picture
        folder = self.folders[folder_id]
        pictures = folder.pictures
        result = []
        if len(pictures) == 0:
            return result
        elif len(pictures) != await azure_storage.get_image_count(
            self.container_client, folder_path=str(folder.path)
        ):
            raise Warning(
                "The number of pictures in the database '"
                + str(len(pictures))
                + "' does not match the number of pictures in the blob storage"
            )
        for pic_id in pictures:
            blob_path = azure_storage.build_blob_name(folder.path, str(pic_id), None)
            pic_metadata = data_picture_set.PictureMetadata(
                id=pic_id, link=blob_path, name=None
            )
            blob_obj = azure_storage.get_blob(self.container_client, blob_path)
            pic_metadata["blob"] = blob_obj
            result.append(pic_metadata)
        return result

    async def delete_folder_permanently(
        self, cursor: Cursor, user_id: UUID, folder_id: UUID
    ):
        """
        Delete a picture set from the database and the blob storage

        Args:
            cursor: The cursor object to interact with the database.
            user_id (str): id of the user deleting
            folder_id (str): id of the picture_set to delete
        """
        # Check if the Container_Client is set
        if self.container_client is None or not self.container_client.exists():
            raise ValueError(
                "The container client must be set before deleting a picture set.\n Use 'get_container_client()' to set the container client."
            )
        # Check if user exists
        if not user.is_a_user_id(cursor=cursor, user_id=user_id):
            raise user.UserNotFoundError(
                f"User not found based on the given id: {user_id}"
            )
        # Check if picture set exists
        if not picture.is_a_picture_set_id(cursor, folder_id):
            raise picture.PictureSetNotFoundError(
                f"Picture set not found based on the given id: {folder_id}"
            )
        # TODO : Check user is owner of the picture set
        # if picture.get_picture_set_owner_id(cursor, folder_id) != user_id:
       
        # Delete the folder in the blob storage
        # for child_folder in self.folders[folder_id].children:
        #    await self.delete_folder_permanently(cursor, user_id, child_folder)
        # This will delete the folder and all its underlying folders
        await azure_storage.delete_folder_path(
            self.container_client, self.folders[folder_id].path
        )
        # Delete the picture set
        # for child in self.folders[folder_id].children:
        #    picture.delete_picture_set(cursor, child)
        # children should be deleted by the cascade in the database
        picture.delete_picture_set(cursor, folder_id)
        # remove folder from the object
        self.__remove_folder_and_children(folder_id)

class User:
    def __init__(self, email: str, id: UUID = None, tier: str = "user"):
        if id is None:
            raise ValueError("The user id must be provided")
        self.id = id
        self.email = email
        self.tier = tier
        self.containers: List[Container] = []

    def get_email(self):
        return self.email

    def get_id(self):
        return self.id

    async def create_user_container(
        self,
        cursor: Cursor,
        connection_str: str,
        name: str,
        user_id: UUID,
        is_public=False,
        storage_prefix="user",
    ) -> Container:
        """
        This function creates a container in the database and the blob storage.
        """
        container_id = container_db.create_container(
            cursor=cursor,
            name=name,
            user_id=user_id,
            is_public=is_public,
            storage_prefix=storage_prefix,
        )
        container_obj = Container(container_id, storage_prefix, name, user_id)

        await container_obj.create_storage(
            connection_str=connection_str, credentials=None
        )
        container_obj.add_user(cursor, user_id, user_id)
        await container_obj.create_folder(cursor, user_id)
        self.add_container(container_obj)
        return container_obj

    async def fetch_all_containers(
        self, cursor: Cursor, connection_str: str, credentials: str
    ):
        db_containers = container_db.get_user_containers(cursor, self.id)
        for container in db_containers:
            if container[1] is None:
                name = container[3]
            else:
                name = container[1]
            container_obj = Container(
                id=container[0], tier=container[4], name=name
            )
            container_obj.fetch_all_data(cursor)
            await container_obj.get_container_client(
                connection_str=connection_str, credentials=credentials
            )
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

    async def create_group_container(
        self,
        cursor: Cursor,
        connection_str: str,
        name: str,
        user_id: UUID,
        is_public=False,
        storage_prefix="group",
    ) -> Container:
        """
        This function creates a container in the database and the blob storage.
        """
        container_id = container_db.create_container(
            cursor=cursor,
            name=name,
            user_id=user_id,
            is_public=is_public,
            storage_prefix=storage_prefix,
        )
        container_obj = Container(container_id, storage_prefix, name, user_id)
        container_obj.create_storage(connection_str=connection_str)
        container_obj.add_group(cursor, self.id, user_id)
        container_obj.create_folder(cursor, user_id)
        self.container = container_obj
        return container_obj


async def get_user(cursor: Cursor, email: str) -> User:
    """
    Get a user from the database

    Parameters:
    - email (str): The email of the user.
    - cursor: The cursor object to interact with the database.
    """
    user_id = user.get_user_id(cursor, email)
    return User(email=email, id=user_id, tier="user")


async def new_user(cursor: Cursor, email: str, connection_string, tier="user") -> User:
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
        await user_obj.create_user_container(
            cursor=cursor,
            connection_str=connection_string,
            name=user_obj.email,
            user_id=user_uuid,
            is_public=False,
            storage_prefix=tier,
        )
        # user_obj.add_container(container_obj)
        return user_obj
    except azure_storage.CreateDirectoryError as e:
        raise FolderCreationError("Error creating the user folder:" + str(e))
    except UserAlreadyExistsError:
        raise
    except ContainerCreationError:
        raise


async def create_group(
    cursor: Cursor, group_name: str, user_id: UUID, connection_string: str
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
                name=group_name,
                user_id=user_id,
                is_public=False,
                storage_prefix="group",
            )
        return group_obj
    except Exception as e:
        raise Exception("Datastore Unhandled Error " + str(e))


async def create_container(
    cursor: Cursor,
    connection_str: str,
    container_name: str = None,
    user_id: UUID = None,
    is_public=False,
    storage_prefix="user",
    add_user_to_storage: bool = False,
) -> Container:
    """
    This function creates a container in the database and the blob storage.
    """
    if user_id is None:
        raise ValueError("The user id must be provided")
    container_id = container_db.create_container(
        cursor=cursor,
        name=container_name,
        user_id=user_id,
        is_public=is_public,
        storage_prefix=storage_prefix,
    )
    container_obj = Container(container_id, storage_prefix, container_name, user_id)

    await container_obj.create_storage(connection_str=connection_str, credentials=None)
    if add_user_to_storage:
        container_obj.add_user(cursor, user_id, user_id)
    await container_obj.create_folder(
        cursor=cursor, performed_by=user_id, folder_name="General", nb_pictures=0
    )
    return container_obj


async def get_container(
    cursor: Cursor, container_id: UUID, connection_str: str, credentials: str
) -> Container:
    """
    This function retrieves a container object
    It fetches all data from the database and build the container_client.
    """
    if container_db.is_a_container(cursor, container_id):
        container_obj = Container(container_id)
        
        container_obj.fetch_all_data(cursor)
        
        await container_obj.get_container_client(
            connection_str=connection_str, credentials=credentials
        )
        return container_obj
    else:
        raise ContainerCreationError("Error: container does not exist")
