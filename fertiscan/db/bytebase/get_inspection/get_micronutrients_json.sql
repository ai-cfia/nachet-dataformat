
CREATE OR REPLACE FUNCTION "fertiscan_0.0.18".get_micronutrient_json(
label_info_id uuid)
RETURNS jsonb 
LANGUAGE plpgsql
AS $function$
DECLARE
    result_json jsonb;
BEGIN
    SELECT jsonb_build_object(
                'micronutrients', 
                jsonb_build_object(
                    'en', COALESCE(jsonb_agg(
                        jsonb_build_object(
                            'name', COALESCE(micronutrient.read_name,Null),
                            'unit', COALESCE(micronutrient.unit,Null),
                            'value', COALESCE(micronutrient.value,Null),
                            'edited', COALESCE(micronutrient.edited,Null)
                        )
                    ) FILTER (WHERE micronutrient.language = 'en'), '[]'::jsonb), 
                    'fr', COALESCE(jsonb_agg(
                        jsonb_build_object(
                            'name', COALESCE(micronutrient.read_name,Null),
                            'unit', COALESCE(micronutrient.unit,Null),
                            'value', COALESCE(micronutrient.value,Null),
                            'edited', COALESCE(micronutrient.edited,Null)
                        )
                    ) FILTER (WHERE micronutrient.language = 'fr'), '[]'::jsonb)
                )
           )
    INTO result_json
    FROM micronutrient
    WHERE micronutrient.label_id = label_info_id;
    RETURN result_json;
END;
$function$;
