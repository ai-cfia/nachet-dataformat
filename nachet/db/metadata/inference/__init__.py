"""
This module contains the function to generate the metadata necessary to interact with the database and the other layers of Nachet for all the inference related objects. 
The metadata is generated in a json format and is used to store the metadata in the database.

"""

import json
import nachet.db.queries.seed as seed
import nachet.db.queries.inference as inference
import nachet.db.queries.machine_learning as machine_learning
from pydantic import BaseModel, ValidationError
from typing import Optional

class MissingKeyError(Exception):
    pass

class Seed(BaseModel):
    label: str
    object_id: str
    score: float
    
class Box(BaseModel):
    topX : float
    topY : float
    bottomX : float
    bottomY : float

class Model(BaseModel):
    name: str
    version: str

class InferenceObject(BaseModel):
    box : Box
    box_id : str
    color : str
    label : str
    object_type_id : int 
    overlapping : bool
    overlappingIndices : list[float]
    score : float
    topN: list[Seed]
    top_id : str
    is_verified : bool

class Inference(BaseModel):
    boxes: list[InferenceObject]
    filename: str
    inference_id: str
    labelOccurrence: dict[str, int]
    totalBoxes: int
    models: Optional[list[Model]]
    pipeline_id: Optional[str]

def build_inference_import(model_inference: dict) -> str:
    """
    This funtion build an inference json object from the model inference.
    This serves as the metadata for the inference object in the database.

    Parameters:
    - model_inference: (dict) The model inference object.

    Returns:
    - The inference db object in a string format.
    """
    try:
        if "filename" not in model_inference:
            raise MissingKeyError("filename")
        if "labelOccurrence" not in model_inference:
            raise MissingKeyError("labelOccurrence")
        if "totalBoxes" not in model_inference:
            raise MissingKeyError("totalBoxes")
        inference = {
            "filename": model_inference["filename"],
            "labelOccurrence": model_inference["labelOccurrence"],
            "totalBoxes": model_inference["totalBoxes"],
        }
        return json.dumps(inference)
    except MissingKeyError as e:
        raise MissingKeyError(f"Missing key: {e}")


def build_object_import(object: dict) -> str:
    """
    This function build the object from the model inference object.
    This serves as the metadata for the object in the database.

    Parameters:
    - object: (dict) The object from the model inference object.

    Returns:
    - The object db object in a string format.
    """
    data = {
        "box": object["box"],
        "color": object["color"],
        "overlapping": object["overlapping"],
        "overlappingIndices": object["overlappingIndices"],
    }
    return json.dumps(data)

def compare_object_metadata(object1:dict , object2:dict) -> bool:
    """
    This function compares two object metadata to check if they are the same.

    Parameters:
    - object1: (dict) The first object to compare.
    - object2: (dict) The second object to compare.

    Returns:
    - True if the objects are the same, False otherwise.
    """
    try :
        box1 = Box(**object1)
        box2 = Box(**object2)
        return box1 == box2
    except ValidationError as e :
        raise e

def rebuild_inference(cursor, inf) :
    """
    This function rebuilds the inference object from the database.

    Parameters:
    - inference: The inference from the database to convert into inference result.

    Returns:
    - The inference object as a dict.
    """
    print(inf)
    inference_id = str(inf[0])
    inference_data = json.loads(json.dumps(inf[1]))
    pipeline_id = str(inf[2])
    
    models = []
    if pipeline_id is not None :
        print("pipeline_id: ", pipeline_id)
        pipeline = machine_learning.get_pipeline(cursor, pipeline_id)
        models_data = pipeline["models"]
        version = pipeline["version"]
        for model_name in models_data :
            model = Model(name=model_name, version=version)
            models.append(model)
    
    objects = inference.get_objects_by_inference(cursor, inference_id)
    boxes = rebuild_boxes_export(cursor, objects)

    inf = Inference(
        boxes = boxes,
        filename= inference_data.get("filename"),
        inference_id = inference_id,
        labelOccurrence = inference_data.get("labelOccurrence"),
        totalBoxes= inference_data.get("totalBoxes"),
        models = models,
        pipeline_id = pipeline_id
    )
    return inf.model_dump()



def rebuild_boxes_export(cursor, objects) :
    """
    This function rebuilds the boxes object from the database.

    Parameters:
    - objects: The objects of an inference from the database to convert into boxes.

    Returns:
    - The boxes object as an array of dict.
    """
    try :
        boxes = []
        for object in objects:
            box_id = str(object[0])
            
            box_metadata = object[1]
            box_metadata = json.loads(json.dumps(box_metadata))
            
            if inference.is_object_verified(cursor, box_id):
                top_id = str(inference.get_inference_object_verified_id(cursor, box_id))
                is_verified = True
            else :
                top_id = str(inference.get_inference_object_top_id(cursor, box_id))
                is_verified = False
            top_seed_id = str(seed.get_seed_object_seed_id(cursor, top_id))
            
            seed_objects = inference.get_seed_object_by_object_id(cursor, box_id)
            topN = rebuild_topN_export(cursor, seed_objects)
            
            top_score = 0
            if inference.is_object_verified(cursor, box_id):
                top_score = 1
            else :
                top_score = max(topN, key=lambda seed: seed.score).score
            
            object = InferenceObject(
                    box = Box(**box_metadata.get("box")),
                    box_id = box_id,
                    color = box_metadata.get("color"),
                    label = seed.get_seed_name(cursor, top_seed_id),
                    object_type_id = 1,
                    overlapping = box_metadata.get("overlapping"),
                    overlappingIndices = box_metadata.get("overlappingIndices"),
                    score = top_score,
                    topN = topN,
                    top_id = top_id,
                    is_verified = is_verified
                )

            boxes.append(object)
        return boxes
    except ValidationError as e :
        raise e
    

def rebuild_topN_export(cursor, seed_objects) -> list[Seed]:
    """
    This function rebuilds the topN object from the database.

    Parameters:
    - seed_objects: The seed_objects from the database to convert into topN.

    Returns:
    - The topN object as an array of dict.
    """
    try :
        topN = []
        for seed_obj in seed_objects :
            res = Seed(
                label = seed.get_seed_name(cursor, str(seed_obj[1])), 
                object_id = str(seed_obj[0]), 
                score = seed_obj[2]
            )
            topN.append(res)
        return topN
    except ValidationError as e :
        raise e
