"""
This module contains all the functions and classes that are used to store and retrieve metadata for machine learning models.
"""

import json


class MissingKeyError(Exception):
    pass


def build_pipeline_import(pipeline: dict) -> str:
    """
    This function builds the model metadata for the database.

    Parameters:
    - model (dict): The model object.

    Returns:
    - The model db object in a string format.
    """
    try:
        keys = [
            "models",
            "created_by",
            "creation_date",
            "description",
            "job_name",
            "version",
            "dataset",
        ]

        for key in keys:
            if key not in pipeline:
                raise MissingKeyError(key)

        pipeline_db = {
            "models": pipeline["models"],
            "created_by": pipeline["created_by"],
            "creation_date": pipeline["creation_date"],
            "description": pipeline["description"],
            "job_name": pipeline["job_name"],
            "version": pipeline["version"],
            "dataset": pipeline["dataset"],
            # "Accuracy": pipeline["Accuracy"]
        }
        return json.dumps(pipeline_db)
    except MissingKeyError as e:
        raise MissingKeyError(f"Missing key: {e}")


def build_pipeline_export(
    data: dict, name: str, id: str, default: bool, model_ids
) -> dict:
    """
    This function builds the model metadata for the database.

    Parameters:
    - model (dict): The model object.

    Returns:
    - The model db object in a string format.
    """
    pipeline_db = {
        "models": model_ids,
        "pipeline_id": str(id),
        "pipeline_name": name,
        "model_name": name,
        "default": default,
    }
    if data is not None:
        for key in data:
            pipeline_db[key] = data[key]
    return pipeline_db


def build_model_import(model: dict) -> str:
    """
    This function builds the model metadata for the database.

    Parameters:
    - model (dict): The model object.

    Returns:
    - The model db object in a string format.
    """
    try:
        keys = [
            "endpoint",
            "api_key",
            "content_type",
            "deployment_platform",
            "created_by",
            "creation_date",
            "description",
            "version",
            "job_name",
            "dataset",
        ]

        for key in keys:
            if key not in model:
                raise MissingKeyError(key)

        model_db = {
            "endpoint": model["endpoint"],
            "api_key": model["api_key"],
            "content_type": model["content_type"],
            "deployment_platform": model["deployment_platform"],
            "created_by": model["created_by"],
            "creation_date": model["creation_date"],
            "description": model["description"],
            "version": model["version"],
            "job_name": model["job_name"],
            # "Accuracy": model["Accuracy"],
            "dataset": model["dataset"],
        }
        return json.dumps(model_db)
    except MissingKeyError as e:
        raise MissingKeyError(f"Missing key: {e}")


def build_model_export(
    data: dict, id, name: str, endpoint: str, task_name: str, version: str
) -> dict:
    """
    This function builds the model metadata for the database.

    Parameters:
    - model (dict): The model object.

    Returns:
    - The model db object in a string format.
    """
    model_db = {
        "model_id": str(id),
        "model_name": name,
        "endpoint": endpoint,
        "task": task_name,
        "version": version,
    }
    if data is not None:
        for key in data.keys():
            model_db[key] = data[key]
    return model_db
