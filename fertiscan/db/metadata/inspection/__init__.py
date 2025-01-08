"""
This module contains the function to generate the metadata necessary to interact with the database and the other layers of Fertiscan for all the inspection related objects.
The metadata is generated in a json format and is used to store the metadata in the database.

"""

from datetime import datetime
from typing import List, Optional

from pydantic import UUID4, BaseModel, ValidationError, model_validator

from fertiscan.db.metadata.errors import (
    BuildInspectionExportError,
    BuildInspectionImportError,
    MetadataError,
    NPKError,
)
from fertiscan.db.queries import (
    inspection,
    label,
    metric,
    nutrients,
    organization,
    sub_label,
    registration_number,
    ingredient,
)
from fertiscan.db.queries.errors import QueryError


class ValidatedModel(BaseModel):
    @model_validator(mode="before")
    def handle_none(cls, values):
        if values is None:
            return {}
        return values


class OrganizationInformation(ValidatedModel):
    id: Optional[str] = None
    name: Optional[str] = None
    address: Optional[str] = None
    website: Optional[str] = None
    phone_number: Optional[str] = None
    edited: Optional[bool] = False
    is_main_contact: Optional[bool] = False


class Value(ValidatedModel):
    value: Optional[float] = None
    unit: Optional[str] = None
    name: Optional[str] = None
    edited: Optional[bool] = False


class Title(ValidatedModel):
    en: Optional[str] = None
    fr: Optional[str] = None


class GuaranteedAnalysis(ValidatedModel):
    title: Title | None = None
    is_minimal: Optional[bool] = False
    en: List[Value] = []
    fr: List[Value] = []


class ValuesObjects(ValidatedModel):
    en: List[Value] = []
    fr: List[Value] = []


class SubLabel(ValidatedModel):
    en: List[str] = []
    fr: List[str] = []


class Metric(ValidatedModel):
    value: Optional[float] = None
    unit: Optional[str] = None
    edited: Optional[bool] = False


class Metrics(ValidatedModel):
    weight: Optional[List[Metric]] = []
    volume: Optional[Metric] = Metric()
    density: Optional[Metric] = Metric()


class RegistrationNumber(ValidatedModel):
    registration_number: str | None = None
    is_an_ingredient: bool | None = None
    edited: Optional[bool] = False


class ProductInformation(ValidatedModel):
    name: str | None = None
    label_id: str | None = None
    lot_number: str | None = None
    metrics: Metrics | None = Metrics()
    npk: str | None = None
    warranty: str | None = None
    n: float | None = None
    p: float | None = None
    k: float | None = None
    verified: Optional[bool] = False
    registration_numbers: List[RegistrationNumber] | None = []
    record_keeping: Optional[bool] = None


class Specification(ValidatedModel):
    humidity: float | None = None
    ph: float | None = None
    solubility: float | None = None
    edited: Optional[bool] = False


class Specifications(ValidatedModel):
    en: List[Specification]
    fr: List[Specification]


# Awkwardly named so to avoid name conflict this represents the inspection object in the database
# and not the inspection object used as a form on the application
class DBInspection(ValidatedModel):
    id: UUID4
    verified: bool = False
    upload_date: datetime | None = None
    updated_at: datetime | None = None
    inspector_id: UUID4 | None = None
    label_info_id: UUID4 | None = None
    sample_id: UUID4 | None = None
    picture_set_id: UUID4 | None = None
    inspection_comment: str | None = None


class Inspection(ValidatedModel):
    inspection_id: Optional[str] = None
    inspector_id: Optional[str] = None
    inspection_comment: Optional[str] = None
    verified: Optional[bool] = False
    organizations: Optional[List[OrganizationInformation]] = []
    product: ProductInformation
    cautions: SubLabel
    instructions: SubLabel
    guaranteed_analysis: GuaranteedAnalysis
    registration_numbers: Optional[List[RegistrationNumber]] = []
    ingredients: ValuesObjects


def build_inspection_import(analysis_form: dict, user_id) -> str:
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
            "organizations",
            "fertiliser_name",
            "registration_number",
            "lot_number",
            "weight",
            "density",
            "volume",
            "npk",
            "cautions_en",
            "instructions_en",
            "cautions_fr",
            "instructions_fr",
            "guaranteed_analysis_fr",
            "guaranteed_analysis_en",
        ]
        missing_keys = []
        for key in requiered_keys:
            if key not in analysis_form:
                missing_keys.append(key)
        if len(missing_keys) > 0:
            raise BuildInspectionImportError(
                f"The analysis form is missing keys: {missing_keys}"
            )

        npk = extract_npk(analysis_form.get("npk"))
        organization_list = []
        if len(analysis_form.get("organizations", [])) > 0:
            for org in analysis_form.get("organizations", []):
                # organization_list.append(OrganizationInformation(**org))
                organization_list.append(
                    OrganizationInformation(
                        name=org.get("name"),
                        address=org.get("address"),
                        website=org.get("website"),
                        phone_number=org.get("phone_number"),
                        edited=False,
                        is_main_contact=False,
                    )
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

        reg_numbers = []
        for reg_number in analysis_form.get("registration_number", []):
            reg_numbers.append(
                RegistrationNumber(
                    registration_number=reg_number.get("identifier"),
                    is_an_ingredient=(reg_number.get("type") == "Ingredient"),
                )
            )

        # record keeping is set as null since the pipeline cant output a value yet
        product = ProductInformation(
            name=analysis_form.get("fertiliser_name"),
            lot_number=analysis_form.get("lot_number"),
            metrics=metrics,
            registration_numbers=reg_numbers,
            npk=analysis_form.get("npk"),
            warranty=analysis_form.get("warranty"),
            n=npk[0],
            p=npk[1],
            k=npk[2],
            verified=False,
            record_keeping=None,
        )

        cautions = SubLabel(
            en=analysis_form.get("cautions_en", []),
            fr=analysis_form.get("cautions_fr", []),
        )

        instructions = SubLabel(
            en=analysis_form.get("instructions_en", []),
            fr=analysis_form.get("instructions_fr", []),
        )

        # Commented and kept as reference for future implementation, but not used at the moment
        # micro_en: list[Value] = [
        #     Value(
        #         unit=nutrient.get("unit") or None,
        #         value=nutrient.get("value") or None,
        #         name=nutrient.get("nutrient"),
        #     )
        #     for nutrient in analysis_form.get("micronutrients_en", [])
        # ]
        # micro_fr: list[Value] = [
        #     Value(
        #         unit=nutrient.get("unit") or None,
        #         value=nutrient.get("value") or None,
        #         name=nutrient.get("nutrient"),
        #     )
        #     for nutrient in analysis_form.get("micronutrients_fr", [])
        # ]
        # micronutrients = ValuesObjects(en=micro_en, fr=micro_fr)

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

        # specifications = Specifications(
        #     en=[
        #         Specification(**s)
        #         for s in analysis_form.get("specifications_en", [])
        #         if any(value is not None for _, value in s.items())
        #     ],
        #     fr=[
        #         Specification(**s)
        #         for s in analysis_form.get("specifications_fr", [])
        #         if any(value is not None for _, value in s.items())
        #     ],
        # )

        # first_aid = SubLabel(
        #     en=analysis_form.get("first_aid_en", []),
        #     fr=analysis_form.get("first_aid_fr", []),
        # )

        guaranteed_fr: list[Value] = [
            Value(
                unit=item.get("unit") or None,
                value=item.get("value") or None,
                name=item.get("nutrient"),
            )
            for item in analysis_form.get("guaranteed_analysis_fr", []).get(
                "nutrients", []
            )
        ]

        guaranteed_en: list[Value] = [
            Value(
                unit=item.get("unit") or None,
                value=item.get("value") or None,
                name=item.get("nutrient"),
            )
            for item in analysis_form.get("guaranteed_analysis_en", []).get(
                "nutrients", []
            )
        ]

        guaranteed = GuaranteedAnalysis(
            title=Title(
                en=analysis_form.get("guaranteed_analysis_en", {}).get("title"),
                fr=analysis_form.get("guaranteed_analysis_fr", {}).get("title"),
            ),
            # is_minimal=analysis_form.get("guaranteed_analysis_is_minimal"),
            is_minimal=None,  # Not processed yet by the pipeline
            en=guaranteed_en,
            fr=guaranteed_fr,
        )

        inspection_formatted = Inspection(
            inspector_id=str(user_id),
            organizations=organization_list,
            product=product,
            cautions=cautions,
            instructions=instructions,
            guaranteed_analysis=guaranteed,
            registration_numbers=reg_numbers,
            ingredients=ingredients,
        )
        Inspection(**inspection_formatted.model_dump())
        return inspection_formatted.model_dump_json()
    except MetadataError:
        raise
    except ValidationError as e:
        raise BuildInspectionImportError(f"Validation error: {e}") from e
    except Exception as e:
        raise BuildInspectionImportError(f"Unexpected error: {e}") from e


def build_inspection_export(cursor, inspection_id) -> str:
    """
    This funtion build an inspection json object from the database.
    """
    try:
        label_info_id = inspection.get_inspection(cursor, inspection_id)[
            inspection.LABEL_INFO_ID
        ]
        # get the label information
        product_info = label.get_label_information_json(cursor, label_info_id)
        product_info = ProductInformation(**product_info)

        # get metrics information
        metrics = metric.get_metrics_json(cursor, label_info_id)
        metrics = Metrics.model_validate(metrics)
        metrics.volume = metrics.volume or Metric()
        metrics.density = metrics.density or Metric()
        product_info.metrics = metrics

        # Retrieve the registration numbers
        reg_numbers = registration_number.get_registration_numbers_json(
            cursor, label_info_id
        )
        reg_number_model_list = []
        for reg_number in reg_numbers["registration_numbers"]:

            reg_number_model_list.append(RegistrationNumber.model_validate(reg_number))
        product_info.registration_numbers = reg_number_model_list

        # get the organizations information (Company and Manufacturer)
        orgs = organization.get_organizations_info_json(cursor, label_info_id)
        org_list = []
        if len(orgs["organizations"]) > 0:
            for org in orgs["organizations"]:
                org_list.append(OrganizationInformation.model_validate(org))

        # Get all the sub labels
        sub_labels = sub_label.get_sub_label_json(cursor, label_info_id)
        cautions = SubLabel.model_validate(sub_labels.get("cautions"))
        instructions = SubLabel.model_validate(sub_labels.get("instructions"))

        # Get the guaranteed analysis
        guaranteed_analysis = nutrients.get_guaranteed_analysis_json(
            cursor, label_info_id
        )
        guaranteed_analysis = GuaranteedAnalysis.model_validate(guaranteed_analysis)

        # Get the ingredients but if the fertilizer is record keeping, the ingredients are not displayed
        if not product_info.record_keeping:
            ingredients = ingredient.get_ingredient_json(cursor, label_info_id)
        else:
            ingredients = ValuesObjects(en=[], fr=[])

        # Get the inspection information
        db_inspection = inspection.get_inspection_dict(cursor, inspection_id)
        db_inspection = DBInspection.model_validate(db_inspection)

        inspection_formatted = Inspection(
            inspection_id=str(inspection_id),
            inspector_id=str(db_inspection.inspector_id),
            inspection_comment=db_inspection.inspection_comment,
            cautions=cautions,
            organizations=org_list,
            guaranteed_analysis=guaranteed_analysis,
            instructions=instructions,
            product=product_info,
            verified=db_inspection.verified,
            registration_numbers=reg_number_model_list,
            ingredients=ingredients,
        )

        return inspection_formatted.model_dump_json()
    except QueryError as e:
        raise BuildInspectionExportError(f"Error fetching data: {e}") from e
    except Exception as e:
        raise BuildInspectionImportError(f"Unexpected error: {e}") from e


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
    try:
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
    except NPKError:
        raise
    except Exception as e:
        raise NPKError(f"Unexpected error: {e}") from e
