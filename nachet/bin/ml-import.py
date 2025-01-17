import datastore.db.__init__ as db
import datastore.nachet as datastore
import json
import sys
import asyncio
import os

NACHET_DB_URL = os.getenv("NACHET_DB_URL")
NACHET_DB_USER = os.getenv("NACHET_DB_USER")
NACHET_DB_PASSWORD = os.getenv("NACHET_DB_PASSWORD")
DB_CONNECTION_STRING = f"postgresql://{NACHET_DB_USER}:{NACHET_DB_PASSWORD}@{NACHET_DB_URL}"
if NACHET_DB_URL is None or NACHET_DB_URL == "":
    raise ValueError("NACHET_DB_URL is not set")

NACHET_SCHEMA = os.environ.get("NACHET_SCHEMA")
if NACHET_SCHEMA is None or NACHET_SCHEMA == "":
    raise ValueError("NACHET_SCHEMA is not set")

def getFile(path: str):
    """
    This function reads a file and returns the content of the file.

    Parameters:
    - path (str): The path of the file.

    Returns:
    - The content of the file.
    """
    try:
        # Open the JSON file
        with open(path) as f:
            # Load JSON data from file
            data = json.load(f)
            return data
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {path}")


def writeJsonFile(data: dict, path: str):
    """
    This function writes a dictionary to a JSON file.

    Parameters:
    - data (dict): The dictionary to write to the file.
    - path (str): The path of the file.

    Returns:
    - None
    """
    try:
        # Open the JSON file
        with open(path, "w") as f:
            # Write JSON data to file
            json.dump(data, f, indent=4)
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {path}")


if __name__ == "__main__":

    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        raise Exception("Error: No file path provided as argument")
    connection = db.connect_db(DB_CONNECTION_STRING, NACHET_SCHEMA)
    cur = db.cursor(connection)
    db.create_search_path(connection, cur, NACHET_SCHEMA)
    file = getFile(file_path)
    print("Importing ML structure from JSON file...")
    # for key in file.keys():
    #    print("key: "+key+" value: "+str(file[key]))
    asyncio.run(datastore.import_ml_structure_from_json_version(cur, file))
    structure = asyncio.run(datastore.get_ml_structure(cur))
    # for key in structure.keys():
    #     for element in structure[key]:
    #         print("\n"+key+": "+str(element))
    writeJsonFile(structure, "ml_structure.json")
    db.end_query(connection, cur)
    print("\n \nML structure imported successfully")
