import os

import datastore.blob.__init__ as blob
import datastore.db.metadata.validator as validator

NACHET_BLOB_ACCOUNT = os.environ.get("NACHET_BLOB_ACCOUNT")
if NACHET_BLOB_ACCOUNT is None or NACHET_BLOB_ACCOUNT == "":
    raise ValueError("NACHET_BLOB_ACCOUNT is not set")

NACHET_BLOB_KEY = os.environ.get("NACHET_BLOB_KEY")
if NACHET_BLOB_KEY is None or NACHET_BLOB_KEY == "":
    raise ValueError("NACHET_BLOB_KEY is not set")

NACHET_STORAGE_URL = os.environ.get("NACHET_STORAGE_URL")
if NACHET_STORAGE_URL is None or NACHET_STORAGE_URL == "":
    raise ValueError("NACHET_STORAGE_URL is not set")


def purge_azure_storage():
    """
    This function purges the Azure storage account.
    """
    blob_service_client = blob.create_BlobServiceClient(NACHET_STORAGE_URL)
    count = 0
    print("Purging Azure storage account")
    # loop through all the containers
    for container in blob_service_client.list_containers():
        container_client = blob.create_container_client(
            blob_service_client, container.name
        )
        name = container_client.container_name
        # check naming
        if name.startswith("test"):
            count += 1
            print(f"Deleting container #{count}: {name}")
            container_client.delete_container()
        elif validator.is_valid_uuid(name):
            count += 1
            print(f"Deleting container #{count}: {name}")
            container_client.delete_container()
        elif name.startswith("dev"):
            nb_blob = 0
            for content in container_client.list_blob_names():
                nb_blob += 1
            if nb_blob <= 1:
                print(f"Deleting container #{count}: {name}")
                container_client.delete_container()


if __name__ == "__main__":
    purge_azure_storage()
