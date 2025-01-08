"""
This module is responsible for handling the user data in the database 
and the user container in the blob storage.
"""

import datastore.db.queries.user as user
import datastore.db.queries.group as group
import datastore.db.queries.picture as picture
import datastore.db.queries.container as container_db
import datastore.db.metadata.picture_set as data_picture_set
import datastore.blob.azure_storage_api as azure_storage
from azure.storage.blob import BlobServiceClient, ContainerClient

from pydantic import BaseModel

from abc import ABC, abstractmethod

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

class Container(BaseModel):
    id: UUID
    name: Optional[str] = None
    is_public: Optional[bool]=False
    storage_prefix: Optional[str]="user"
    group_ids: Optional[List[UUID]]=[]
    user_ids: Optional[List[UUID]]=[]
    folders: Optional[Dict[UUID, Folder]] = {}
    path: Optional[str] = None


class ContainerController:
    def __init__(self, container_model: Container):
        container_model.path = azure_storage.build_container_name(str(container_model.id), container_model.storage_prefix)
        self.id = container_model.id
        self.model = container_model
        self.container_client: Optional[ContainerClient] = None

    #def __init__(self, id: UUID):
    #    self.id = id
    #    self.model: Optional[Container] = None
    #    self.container_client: Optional[ContainerClient] = None

    # This could be achieved by fetching the storage and performing Azure API calls
    def fetch_all_folders_metadata(self, cursor: Cursor):
        """
        This function retrieves all the folders metadata from the database then stores it in the container object.

        Parameters:
        - cursor: The cursor object to interact with the database.
        """
        db_folders = picture.get_picture_sets_by_container(cursor, self.id)
        # the root folders should be the first one to be iterated over
        list_folder_child: List[Folder] = []
        list_folder_root: List[Folder] = []
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
                list_folder_child.append(folder_metadata)
            else:
                list_folder_root.append(folder_metadata)
            self.model.folders[folder_id] = folder_metadata
        # loop through the folders to add the children
        for folder in list_folder_child:
            self.model.folders[folder.parent_id].children.append(folder.id)
        # loop through the folders to add the path
        for folder in list_folder_root:
            self.__build_children_path(folder.id)

    def __build_children_path(self, folder_id: UUID):
        """
        This function builds the path of the children of a folder.
        """
        folder = self.model.folders[folder_id]
        for child_id in folder.children:
            self.model.folders[child_id].path = folder.path + "/" + self.model.folders[child_id].name
            self.__build_children_path(child_id)

    def fetch_all_data(self, cursor: Cursor):
        """
        This function retrieves all the users and groups that have access to the container.
        """
        db_container = container_db.get_container(cursor, self.id)
        self.model.user_ids = []
        self.model.group_ids = []
        container_model = Container(
            id=self.id,
            name=db_container[0],
            is_public=db_container[1],
            storage_prefix=db_container[2],
            path=azure_storage.build_container_name(str(self.id), db_container[2]),
            user_ids=db_container[5],
            group_ids=db_container[6],
            folders={},
        )
        self.model=container_model
        self.fetch_all_folders_metadata(cursor)

    def __remove_folder_and_children(self, folder_id: UUID):
        """
        Remove the children of a folder from the object.
        """
        for child in self.model.folders[folder_id].children:
            self.remove_folder_children(child)
        self.model.folders.pop(folder_id)

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
            storage_prefix=self.model.storage_prefix,
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
        self.model.user_ids.append(user_id)

    def remove_user(self, cursor: Cursor, user_id: UUID):
        """
        This function removes a user from the container rights.

        Parameters:
        - cursor: The cursor object to interact with the database.
        - user_id (str): The UUID of the user.
        """
        if container_db.has_user_access_to_container(cursor, user_id, self.id):
            # Unlink the container to the user in the database
            container_db.delete_user_from_container(cursor, user_id, self.id)
        if user_id in self.model.user_ids:
            self.model.user_ids.remove(user_id)

    def add_group(self, cursor: Cursor, group_id: UUID, performed_by: UUID):
        # Link the container to the user in the database
        container_db.add_group_to_container(cursor, group_id, self.id, performed_by)
        self.model.group_ids.append(group_id)

    def remove_group(self, cursor: Cursor, group_id: UUID):
        # Unlink the container to the user in the database
        container_db.delete_group_from_container(cursor, group_id, self.id)
        if group_id in self.model.group_ids:
            self.model.group_ids.remove(group_id)
        # remove users from the group
        users = group.get_group_users(cursor, group_id)
        for user_id in users:
            # Check if the user has personnal access to the container, if so, don't remove it
            if not container_db.has_user_access_to_container(cursor, user_id, self.id):
                self.remove_user(cursor, user_id)

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
        container_client = blob_service_client.create_container(self.model.path)
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
            self.model.folders[parent_folder_id].children.append(pic_set_id)
            parent_path = self.model.folders[parent_folder_id].path
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
        self.model.folders[pic_set_id] = folder
        return pic_set_id

    async def upload_pictures(
        self,
        cursor: Cursor,
        user_id: UUID,
        hashed_pictures: List[str],
        folder_id: UUID = None,
        nb_objects: int = 0,
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
        if user_id not in self.model.user_ids:
            raise UserNotOwnerError(
                f"User can't access this Container, user uuid :{user_id}, Container id : {self.id}"
            )
        if self.container_client is None or not self.container_client.exists():
            raise ContainerCreationError(
                "Error: container client does not exist or not set, please set the container client first"
            )
        # Create a folder if not provided
        if folder_id is None:
            folder_id = await self.create_folder(
                cursor=cursor,
                performed_by=user_id,
                folder_name=None,
                nb_pictures=len(hashed_pictures),
            )
        else:
            # Check if folder exists in the database in the container
            if not picture.is_a_picture_set_id(cursor, folder_id):
                raise FolderCreationError(
                    f"Folder does not exist in the container: {folder_id}"
                )
        # Get the folder metadata
        try:
            folder = self.model.folders[folder_id]
        except KeyError:
            self.fetch_all_folders_metadata(cursor)
            folder = self.model.folders[folder_id]
        # Get the path of the folder in the Blob Storage
        # folder_name = folder.name
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
            blob_name = await azure_storage.upload_image(
                self.container_client,
                str(folder_path),
                str(folder_id),
                picture_hash,
                str(picture_id),
            )
            if not blob_name:
                raise BlobUploadError("Error uploading the picture")
            pic_ids.append(picture_id)

            # Update the picture metadata with the link
            picture_metadata.picture_id = picture_id
            picture_metadata.link = blob_name
            picture.update_picture_metadata(
            cursor=cursor,
            picture_id=picture_id,
            metadata=picture_metadata.model_dump_json(),
            nb_objects=nb_objects,
            )
        self.model.folders[folder_id].pictures.extend(pic_ids)
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
        if (folder_id not in list(self.model.folders.keys())):
            raise FolderCreationError(
                f"Folder does not exist in the container: {folder_id}"
            )
        # Check if user has access to the container
        if user_id not in self.model.user_ids:
            raise UserNotOwnerError(
                f"User can't access this Container, user uuid :{user_id}, Container id : {self.id}"
            )
        # Get the picture
        folder = self.model.folders[folder_id]
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
            ).model_dump_json()
            blob_obj = azure_storage.get_blob(self.container_client, blob_path)
            pic_metadata["blob"] = blob_obj
            result.append(pic_metadata)
        return result

    async def get_picture_blob(self, cursor: Cursor, picture_id: UUID, user_id: UUID):
        """
        This function downloads a picture from the blob storage.

        Parameters:
        - cursor: The cursor object to interact with the database.
        - picture_id (str): The UUID of the picture.
        - user_id (str): The UUID of the user.

        Returns:
        - The picture blob obj.
        """
        # Check if user exists
        if self.container_client is None or not self.container_client.exists():
            raise ValueError(
                "The container client must be set before downloading pictures.\n Use 'get_container_client()' to set the container client."
            )
        if not user.is_a_user_id(cursor=cursor, user_id=str(user_id)):
            raise user.UserNotFoundError(
                f"User not found based on the given id: {user_id}"
            )
        # Check if user has access to the container
        # TODO
        # Check if picture exists
        if not picture.is_a_picture_id(cursor, picture_id):
            raise picture.PictureNotFoundError(
                f"Picture not found based on the given id: {picture_id}"
            )
        folder_id = picture.get_picture_picture_set_id(cursor, picture_id)
        folder = self.model.folders[folder_id]
        # Get the picture
        blob_path = azure_storage.build_blob_name(folder.path, str(picture_id), None)
        picture_blob = azure_storage.get_blob(self.container_client, blob_path)
        return picture_blob

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
        # for child_folder in self.model.folders[folder_id].children:
        #    await self.delete_folder_permanently(cursor, user_id, child_folder)
        # This will delete the folder and all its underlying folders
        await azure_storage.delete_folder_path(
            self.container_client, self.model.folders[folder_id].path
        )
        # Delete the picture set
        # for child in self.model.folders[folder_id].children:
        #    picture.delete_picture_set(cursor, child)
        # children should be deleted by the cascade in the database
        picture.delete_picture_set(cursor, folder_id)
        # remove folder from the object
        self.__remove_folder_and_children(folder_id)

    async def delete_picture_permanently(self, cursor: Cursor, user_id: UUID, picture_id: UUID):
        """
        This function deletes a picture from the blob storage and the database.
        """
        # Get the picture set id
        picture_set_id = picture.get_picture_picture_set_id(cursor, picture_id)
        
        folder = self.model.folders[picture_set_id]

        # Delete from the blob storage
        blob_path = azure_storage.build_blob_name(folder.path, str(picture_id), None)
        await azure_storage.delete_blob(self.container_client,blob_path)
        
        # Delete from the database
        picture.delete_picture(cursor, picture_id)

        # Remove the picture from the folder
        folder.pictures.remove(picture_id)

"""
Abstract Pydanctic model for the client object.
"""
class Client(BaseModel):
    id: UUID
    name: str
    is_public: bool
    storage_prefix: str
    containers: Dict[UUID,Container]

class ClientController(ABC):
    def __init__(self, client_model: Client):
        self.model = client_model
        self.id = client_model.id

    def get_name(self):
        return self.model.name
    
    def get_id(self):
        return self.model.id
    
    def get_containers(self):
        return self.model.containers

    async def create_container(
        self,
        cursor: Cursor,
        connection_str: str,
        name: str,
        user_id: UUID,
        is_public=False,
    ) -> ContainerController:
        """
        This function creates a container in the database and the blob storage.
        """
        container_obj = await create_container(
            cursor=cursor,
            connection_str=connection_str,
            container_name=name,
            user_id=user_id,
            is_public=is_public,
            storage_prefix=self.model.storage_prefix,
            add_user_to_storage=True,
        )
        self.model.containers[container_obj.id] = container_obj.model
        return container_obj

    @abstractmethod
    def fetch_all_containers():
        pass

class User(ClientController):
    def __init__(self, email: str, id: UUID = None, tier: str = "user"):
        if id is None:
            raise ValueError("The user id must be provided")
        client_model = Client(
            id=id,
            name=email,
            is_public=False,
            storage_prefix=tier,
            containers={},
        )
        super().__init__(client_model)

    async def fetch_all_containers(
        self, cursor: Cursor, connection_str: str, credentials: str
    ):
        db_containers = container_db.get_user_containers(cursor, self.id)
        for container in db_containers:
            empty_model = Container(
                id=container[0],
                name=None,
                is_public=None,
                storage_prefix=None,
                group_ids=None,
                user_ids=None,
                folders={},
                path=None,
            )

            container_obj = ContainerController(
                container_model = empty_model
            )
            container_obj.fetch_all_data(cursor)
            #await container_obj.get_container_client(
            #    connection_str=connection_str, credentials=credentials
            #)
            #self.add_container(container_obj)
            self.model.containers[container_obj.model.id] = container_obj.model
        # Add the groups containers
        db_containers = container_db.get_user_group_containers(cursor, self.id)
        for container in db_containers:
            container_id = container[0]
            empty_model = Container(
                id=container_id,
                name=None,
                is_public=None,
                storage_prefix=None,
                group_ids=None,
                user_ids=None,
                folders={},
                path=None,
            )
            container_obj = ContainerController(
                container_model=empty_model
            )
            container_obj.fetch_all_data(cursor)
            #await container_obj.get_container_client(
            #    connection_str=connection_str, credentials=credentials
            #)
            #self.add_container(container_obj)
            self.model.containers[container_id]=container_obj.model


class Group(ClientController):
    def __init__(self, name: str, id: UUID = None, tier: str = "group"):
        if id is None:
            raise ValueError("The group id must be provided")
        client_model = Client(
            id=id,
            name=name,
            is_public=False,
            storage_prefix=tier,
            containers={},
        )
        super().__init__(client_model)

    async def create_container(
        self,
        cursor: Cursor,
        connection_str: str,
        name: str,
        user_id: UUID,
        is_public=False,
    ) -> ContainerController:
        """
        This function creates a container in the database and the blob storage.
        """
        container_obj = await super().create_container(
            cursor=cursor,
            connection_str=connection_str,
            name=name,
            user_id=user_id,
            is_public=is_public,
        )
        container_obj.add_group(cursor, self.id, user_id)
        return container_obj
    
    def fetch_all_containers(self, cursor: Cursor):
        db_containers = container_db.get_group_containers(cursor, self.id)
        for container in db_containers:
            container_id = container[0]
            container_obj = ContainerController(
                id=container_id
            )
            container_obj.fetch_all_data(cursor)
            self.model.containers[container_obj] = container_obj.model

    def add_user(self, cursor: Cursor, user_id: UUID, performed_by: UUID):
        """
        This function adds a user to the group rights.

        Parameters:
        - cursor: The cursor object to interact with the database.
        - user_id (str): The UUID of the user.
        """
        # TODO: Check permission
        #if not group.has_user_access_to_group(cursor, user_id, self.id):
            # Link the group to the user in the database
        group.add_user_to_group(cursor, user_id, self.model.id, performed_by)

    def remove_user(self, cursor: Cursor, user_id: UUID):
        """
        This function removes a user from the group rights.

        Parameters:
        - cursor: The cursor object to interact with the database.
        - user_id (str): The UUID of the user.
        """
        # TODO : Check permission
        group.remove_user_from_group(cursor, user_id, self.id)


async def get_user(cursor: Cursor, email: str) -> User:
    """
    Get a user from the database

    Parameters:
    - email (str): The email of the user.
    - cursor: The cursor object to interact with the database.
    """
    user_id = user.get_user_id(cursor, email)
    user_obj = User(email, user_id)
    await user_obj.fetch_all_containers(cursor,None,None)
    return user_obj


async def new_user(cursor: Cursor, email: str, connection_string, tier="user") -> User:
    """
    Create a new user in the database and creates its personal container in the blob storage.

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
        await user_obj.create_container(
            cursor=cursor,
            connection_str=connection_string,
            name=email,
            user_id=user_uuid,
            is_public=False,
        )
        # user_obj.add_container(container_obj)
        return user_obj
    except azure_storage.CreateDirectoryError as e:
        raise FolderCreationError("Error creating the user folder:" + str(e))
    except UserAlreadyExistsError:
        raise
    except ContainerCreationError:
        raise


async def delete_user(cursor: Cursor, user_obj: User, connection_string: str= None, credentials: str = None):
    """
    Delete a user from the database and the blob storage.
    If the user has containers, it will check if there wont be containers without owner.

    Parameters:
    - cursor: The cursor object to interact with the database.
    - user_obj (User): The user object to delete.
    - connection_string (optional): The connection string to connect with the Azure storage account
    - credentials (optional): The credentials to connect with the Azure storage account
    """
    # Check if there will be a container left without owner
    lonely_containers: List[Container] = []
    await user_obj.fetch_all_containers(cursor, connection_string, credentials)
    for container_model in user_obj.model.containers.values():
        if container_db.has_user_sole_access_to_container(cursor, user_obj.id, container_model.id):
            lonely_containers.append(container_model)

    if len(lonely_containers) > 0 and connection_string is not None:
        # delete the containers without user access
        for lonely_container_model in lonely_containers:
            container_obj = ContainerController(lonely_container_model)
            await container_obj.get_container_client(
                connection_str=connection_string, credentials=credentials
            )
            await delete_container(cursor, container_obj, user_obj.model)
    elif len(lonely_containers) > 0 and connection_string is None :
        raise ValueError(
            "There are container that only this user has access to. Please provide the connection string and credentials to delete the containers"
        )
    user.delete_user(cursor, user_obj.model.id)
    user_obj.model = None
    user_obj.id = None
    del user_obj
    return


async def get_group(cursor: Cursor, group_id: UUID) -> Group:
    """
    Get a group from the database

    Parameters:
    - group_id (str): The UUID of the group.
    - cursor: The cursor object to interact with the database.
    """
    group_name = group.get_group_name(cursor, group_id)
    group_obj = Group(group_name, group_id)
    group_obj.fetch_all_containers(cursor)
    return group_obj


async def create_group(
    cursor: Cursor, group_name: str, user_id: UUID, connection_str: str, tier: str = "group"
) -> Group:
    """
    Create a new group in the database

    Parameters:
    - cursor: The cursor object to interact with the database.
    - group_name (str): The name of the group.
    - user_id (str): The UUID of the user creating the group.
    - connection_str: The connection string to connect with the Azure storage account
    """
    try:
        group_id = group.create_group(cursor, group_name, user_id)
        group_obj = Group(name=group_name, id=group_id,tier=tier)
        # Create the group container in the blob storage
        if connection_str is not None:
            await group_obj.create_container(
                cursor=cursor,
                connection_str=connection_str,
                name=group_name,
                user_id=user_id,
                is_public=False,
            )
        group_obj.add_user(cursor, user_id, user_id)
        return group_obj
    except Exception as e:
        raise Exception("Datastore Unhandled Error " + str(e))


async def delete_group(cursor: Cursor, group_obj: Group):
    """
    Delete a group from the database and the blob storage.

    Parameters:
    - cursor: The cursor object to interact with the database.
    - group_obj (Group): The group object to delete.
    """
    # We do not need to check if the group leaves containers without owner
    # because the container owner is always a single user so even if the group is deleted, 
    # the user should still have access to the container
    group.delete_group(cursor, group_obj.get_id())
    group_obj.model = None
    group_obj.id = None
    del group_obj


async def create_container(
    cursor: Cursor,
    connection_str: str,
    container_name: str = None,
    user_id: UUID = None,
    is_public=False,
    storage_prefix="user",
    add_user_to_storage: bool = False,
) -> ContainerController:
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
    if container_name is None or container_name.strip() == "":
        container_name = str(container_id)
    container_model = Container(
        id=container_id,
        name=container_name,
        is_public=is_public,
        storage_prefix=storage_prefix,
        group_ids=[],
        user_ids=[],
        folders= {},
        path=azure_storage.build_container_name(str(container_id), storage_prefix)
    )
    container_obj = ContainerController(container_model=container_model)
    
    await container_obj.create_storage(connection_str=connection_str, credentials=None)
    if add_user_to_storage:
        container_obj.add_user(cursor, user_id, user_id)
    await container_obj.create_folder(
        cursor=cursor, performed_by=user_id, folder_name="General", nb_pictures=0
    )
    return container_obj


async def get_container_controller(
    cursor: Cursor, container_id: UUID, connection_str: str, credentials: str
) -> ContainerController:
    """
    This function retrieves a container object
    It fetches all data from the database and build the container_client.
    """
    if container_db.is_a_container(cursor, container_id):
        temp_model = Container(id=container_id)
        container_obj = ContainerController(temp_model)
        
        container_obj.fetch_all_data(cursor)
        
        await container_obj.get_container_client(
            connection_str=connection_str, credentials=credentials
        )
        return container_obj
    else:
        raise ContainerCreationError("Error: container does not exist")


async def delete_container(cursor: Cursor, container_controller: ContainerController, client_model: Client):
    """
    This function deletes a container from the database and the blob storage.

    Parameters:
    - cursor: The cursor object to interact with the database.
    - container_id (str): The UUID of the container.
    - client_obj (Client): The client object (Can be a User or Group) that is the owner of the container.
    """
    # Check if the container client is set
    if container_controller.container_client is None or not container_controller.container_client.exists():
        raise ValueError(
            "The container client must be set before deleting a container.\n Use 'get_container_client()' to set the container client."
        )
    #TODO : Check if the user is the owner of the container
    # Check if the user has access to the container
    if not container_db.has_user_access_to_container(cursor, client_model.id, container_controller.id):
        raise UserNotOwnerError(
            f"User can't access this Container, user uuid :{client_model.id}, Container id : {container_controller.id}"
        )
    # Delete the container
    if container_controller.container_client is None or not container_controller.container_client.exists():
        raise ValueError(
            "The container client must be set before deleting a container.\n Use 'get_container_client()' to set the container client."
        )
    # Delete the container in the blob storage
    await azure_storage.delete_container(container_controller.container_client)
    # Delete the container in the database
    container_db.delete_container(cursor, container_controller.id)
    # Remove the container from the user
    client_model.containers.pop(container_controller.id)
