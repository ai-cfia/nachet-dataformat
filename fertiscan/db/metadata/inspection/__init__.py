"""
This module contains the function to generate the metadata necessary to interact with the database and the other layers of Fertiscan for all the inspection related objects.
The metadata is generated in a json format and is used to store the metadata in the database.

"""

from datetime import datetime
from typing import List, Optional

from pydantic import UUID4, BaseModel, ValidationError

from fertiscan.db.queries import (
    ingredient,
    label,
    metric,
    nutrients,
    organization,
    specification,
    sub_label,
)


class MissingKeyError(Exception):
    pass


class NPKError(Exception):
    pass


class MetadataFormattingError(Exception):
    pass


class OrganizationInformation(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    address: Optional[str] = None
    website: Optional[str] = None
    phone_number: Optional[str] = None


class Value(BaseModel):
    value: Optional[float] = None
    unit: Optional[str] = None
    name: Optional[str] = None
    edited: Optional[bool] = False


class ValuesObjects(BaseModel):
    en: List[Value] = []
    fr: List[Value] = []


class SubLabel(BaseModel):
    en: List[str] = []
    fr: List[str] = []


class Metric(BaseModel):
    value: Optional[float] = None
    unit: Optional[str] = None
    edited: Optional[bool] = False


class Metrics(BaseModel):
    weight: Optional[List[Metric]] = []
    volume: Optional[Metric] = Metric()
    density: Optional[Metric] = Metric()


class ProductInformation(BaseModel):
    name: str | None = None
    label_id: str | None = None
    registration_number: str | None = None
    lot_number: str | None = None
    metrics: Metrics
    npk: str | None = None
    warranty: str | None = None
    n: float | None = None
    p: float | None = None
    k: float | None = None


class Specification(BaseModel):
    humidity: float | None = None
    ph: float | None = None
    solubility: float | None = None
    edited: Optional[bool] = False


class Specifications(BaseModel):
    en: List[Specification]
    fr: List[Specification]


# Awkwardly named so to avoid name conflict
class DBInspection(BaseModel):
    id: UUID4
    verified: bool = False
    upload_date: datetime | None = None
    updated_at: datetime | None = None
    inspector_id: UUID4 | None = None
    label_info_id: UUID4 | None = None
    sample_id: UUID4 | None = None
    picture_set_id: UUID4 | None = None


class Inspection(BaseModel):
    inspection_id: Optional[str] = None
    verified: Optional[bool] = False
    company: Optional[OrganizationInformation] = OrganizationInformation()
    manufacturer: Optional[OrganizationInformation] = OrganizationInformation()
    product: ProductInformation
    cautions: SubLabel
    instructions: SubLabel
    micronutrients: ValuesObjects
    ingredients: ValuesObjects
    specifications: Specifications
    first_aid: SubLabel
    guaranteed_analysis: List[Value]


def build_inspection_import(analysis_form: dict) -> str:
    """
    This funtion build an inspection json object from the pipeline of digitalization analysis.
    This serves as the metadata for the inspection object in the database.

    Parameters:
    - analysis_form: (dict) The digitalization of the label.

    Returns:
    - The inspection db object in a string format.
    """
    try:
        requiered_keys = [
            "company_name",
            "company_address",
            "company_website",
            "company_phone_number",
            "manufacturer_name",
            "manufacturer_address",
            "manufacturer_website",
            "manufacturer_phone_number",
            "fertiliser_name",
            "registration_number",
            "lot_number",
            "weight",
            "density",
            "volume",
            "npk",
            "warranty",
            "cautions_en",
            "instructions_en",
            "micronutrients_en",
            "ingredients_en",
            "specifications_en",
            "first_aid_en",
            "cautions_fr",
            "instructions_fr",
            "micronutrients_fr",
            "ingredients_fr",
            "specifications_fr",
            "first_aid_fr",
            "guaranteed_analysis",
        ]
        missing_keys = []
        for key in requiered_keys:
            if key not in analysis_form:
                missing_keys.append(key)
        if len(missing_keys) > 0:
            raise MissingKeyError(missing_keys)

        npk = extract_npk(analysis_form.get("npk"))

        company = OrganizationInformation(
            name=analysis_form.get("company_name"),
            address=analysis_form.get("company_address"),
            website=analysis_form.get("company_website"),
            phone_number=analysis_form.get("company_phone_number"),
        )
        manufacturer = OrganizationInformation(
            name=analysis_form.get("manufacturer_name"),
            address=analysis_form.get("manufacturer_address"),
            website=analysis_form.get("manufacturer_website"),
            phone_number=analysis_form.get("manufacturer_phone_number"),
        )

        weights: list[Metric] = [
            Metric(
                unit=weight.get("unit"),
                value=weight.get("value"),
            )
            for weight in analysis_form.get("weight", [])
        ]

        volume_obj = Metric()
        if volume := analysis_form.get("volume"):
            volume_obj = Metric(unit=volume.get("unit"), value=volume.get("value"))

        density_obj = Metric()
        if density := analysis_form.get("density"):
            density_obj = Metric(unit=density.get("unit"), value=density.get("value"))

        metrics = Metrics(weight=weights, volume=volume_obj, density=density_obj)

        product = ProductInformation(
            name=analysis_form.get("fertiliser_name"),
            registration_number=analysis_form.get("registration_number"),
            lot_number=analysis_form.get("lot_number"),
            metrics=metrics,
            npk=analysis_form.get("npk"),
            warranty=analysis_form.get("warranty"),
            n=npk[0],
            p=npk[1],
            k=npk[2],
            verified=False,
        )

        cautions = SubLabel(
            en=analysis_form.get("cautions_en", []),
            fr=analysis_form.get("cautions_fr", []),
        )

        instructions = SubLabel(
            en=analysis_form.get("instructions_en", []),
            fr=analysis_form.get("instructions_fr", []),
        )

        micro_en: list[Value] = [
            Value(
                unit=nutrient.get("unit") or None,
                value=nutrient.get("value") or None,
                name=nutrient.get("nutrient"),
            )
            for nutrient in analysis_form.get("micronutrients_en", [])
        ]
        micro_fr: list[Value] = [
            Value(
                unit=nutrient.get("unit") or None,
                value=nutrient.get("value") or None,
                name=nutrient.get("nutrient"),
            )
            for nutrient in analysis_form.get("micronutrients_fr", [])
        ]
        micronutrients = ValuesObjects(en=micro_en, fr=micro_fr)

        ingredients_en: list[Value] = [
            Value(
                unit=ingredient.get("unit") or None,
                value=ingredient.get("value") or None,
                name=ingredient.get("nutrient"),
            )
            for ingredient in analysis_form.get("ingredients_en", [])
        ]
        ingredients_fr: list[Value] = [
            Value(
                unit=ingredient.get("unit") or None,
                value=ingredient.get("value") or None,
                name=ingredient.get("nutrient"),
            )
            for ingredient in analysis_form.get("ingredients_fr", [])
        ]
        ingredients = ValuesObjects(en=ingredients_en, fr=ingredients_fr)

        specifications = Specifications(
            en=[
                Specification(**s)
                for s in analysis_form.get("specifications_en", [])
                if any(value is not None for _, value in s.items())
            ],
            fr=[
                Specification(**s)
                for s in analysis_form.get("specifications_fr", [])
                if any(value is not None for _, value in s.items())
            ],
        )

        first_aid = SubLabel(
            en=analysis_form.get("first_aid_en", []),
            fr=analysis_form.get("first_aid_fr", []),
        )

        guaranteed: list[Value] = [
            Value(
                unit=item.get("unit") or None,
                value=item.get("value") or None,
                name=item.get("nutrient"),
            )
            for item in analysis_form.get("guaranteed_analysis", [])
        ]

        inspection_formatted = Inspection(
            company=company,
            manufacturer=manufacturer,
            product=product,
            cautions=cautions,
            instructions=instructions,
            micronutrients=micronutrients,
            ingredients=ingredients,
            specifications=specifications,
            first_aid=first_aid,
            guaranteed_analysis=guaranteed,
        )
        Inspection(**inspection_formatted.model_dump())
    except MissingKeyError as e:
        raise MissingKeyError("Missing keys:" + str(e))
    except ValidationError as e:
        print(analysis_form.get("cautions_en", []))
        print(analysis_form.get("cautions_fr", []))
        raise MetadataFormattingError(
            "Error InspectionCreationError not created: " + str(e)
        ) from None
    # print(inspection_formatted.model_dump_json())
    return inspection_formatted.model_dump_json()


def build_inspection_export(cursor, inspection_id, label_info_id) -> str:
    """
    This funtion build an inspection json object from the database.
    """
    try:
        inspection_json = {"inspection_id": str(inspection_id)}
        # get the label information
        label_json = label.get_label_information_json(cursor, label_info_id)

        metrics_json = metric.get_metrics_json(cursor, label_info_id)
        if metrics_json["metrics"]["weight"] is None:
            metrics_json["metrics"]["weight"] = []
        if metrics_json["metrics"]["volume"] is None:
            metrics_json["metrics"]["volume"] = Metric()
        if metrics_json["metrics"]["density"] is None:
            metrics_json["metrics"]["density"] = Metric()
        label_json.update(metrics_json)
        ProductInformation(**label_json)

        product_json = {"product": label_json}

        inspection_json.update(product_json)

        # get the organizations information (Company and Manufacturer)
        organization_json = organization.get_organizations_info_json(
            cursor, label_info_id
        )
        if "company" in organization_json.keys():
            OrganizationInformation(**organization_json.get("company"))
        if "manufacturer" in organization_json.keys():
            OrganizationInformation(**organization_json.get("manufacturer"))

        inspection_json.update(organization_json)

        # Get all the sub labels
        sub_label_json = sub_label.get_sub_label_json(cursor, label_info_id)
        if sub_label_json is None:
            sub_label_json = {
                "cautions": {"en": [], "fr": []},
                "instructions": {"en": [], "fr": []},
                "first_aid": {"en": [], "fr": []},
            }
        else:
            for key in sub_label_json:
                SubLabel(**sub_label_json[key])

        inspection_json.update(sub_label_json)
        # Get the ingredients
        ingredients_json = ingredient.get_ingredient_json(cursor, label_info_id)

        ValuesObjects(**ingredients_json)

        inspection_json.update(ingredients_json)

        # Get the nutrients
        nutrients_json = nutrients.get_micronutrient_json(cursor, label_info_id)

        ValuesObjects(**nutrients_json)

        inspection_json.update(nutrients_json)

        # Get the guaranteed analysis
        guaranteed_analysis_json = nutrients.get_guaranteed_analysis_json(
            cursor, label_info_id
        )
        if guaranteed_analysis_json.get("guaranteed_analysis") is None:
            guaranteed_analysis_json["guaranteed_analysis"] = []
        for i in range(len(guaranteed_analysis_json.get("guaranteed_analysis"))):
            Value(**(guaranteed_analysis_json.get("guaranteed_analysis")[i]))

        inspection_json.update(guaranteed_analysis_json)

        # Get the specifications
        specifications_json = specification.get_specification_json(
            cursor, label_info_id
        )

        Specifications(**(specifications_json.get("specifications")))

        inspection_json.update(specifications_json)

        # Verify the inspection object
        inspection_formatted = Inspection(**inspection_json)
        # Return the inspection object
        return inspection_formatted.model_dump_json()
    except (
        label.LabelInformationNotFoundError
        or metric.MetricNotFoundError
        or organization.OrganizationNotFoundError
        or sub_label.SubLabelNotFoundError
        or ingredient.IngredientNotFoundError
        or nutrients.MicronutrientNotFoundError
        or nutrients.GuaranteedNotFoundError
        or specification.SpecificationNotFoundError
    ):
        raise
    except Exception as e:
        raise MetadataFormattingError(
            "Error Inspection Form not created: " + str(e)
        ) from None


def split_value_unit(value_unit: str) -> dict:
    """
    This function splits the value and unit from a string.
    The string must be in the format of "value unit".

    Parameters:
    - value_unit: (str) The string to split.

    Returns:
    - A dictionary containing the value and unit.
    """
    if value_unit is None or value_unit == "" or len(value_unit) < 2:
        return {"value": None, "unit": None}
    # loop through the string and split the value and unit
    for i in range(len(value_unit)):
        if not (
            value_unit[i].isnumeric() or value_unit[i] == "." or value_unit[i] == ","
        ):
            value = value_unit[:i]
            unit = value_unit[i:]
            break
    # trim the unit of any leading or trailing whitespaces
    unit = unit.strip()
    if unit == "":
        unit = None
    return {"value": value, "unit": unit}


def extract_npk(npk: str):
    """
    This function extracts the npk values from the string npk.
    The string must be in the format of "N-P-K".

    Parameters:
    - npk: (str) The string to split.

    Returns:
    - A list containing the npk values.
    """
    if npk is None or npk == "" or len(npk) < 5:
        return [None, None, None]
    npk_formated = npk.replace("N", "-")
    npk_formated = npk_formated.replace("P", "-")
    npk_formated = npk_formated.replace("K", "-")
    npk_reformated = npk.split("-")
    for i in range(len(npk_reformated)):
        if not npk_reformated[i].isnumeric():
            NPKError(
                "NPK values must be numeric. Issue with: "
                + npk_reformated[i]
                + "in the NPK string: "
                + npk
            )
    return [
        float(npk_reformated[0]),
        float(npk_reformated[1]),
        float(npk_reformated[2]),
    ]