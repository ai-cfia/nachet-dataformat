CREATE OR REPLACE FUNCTION "fertiscan_0.0.18".get_specification_json(
label_info_id uuid)
RETURNS jsonb 
LANGUAGE plpgsql
AS $function$
DECLARE
    result_json jsonb;
BEGIN
    SELECT jsonb_build_object(
        'specifications', jsonb_build_object(
            'en',COALESCE(jsonb_agg(
                jsonb_build_object(
                    'ph', COALESCE(specification.ph, Null),
                    'humidity', COALESCE(specification.humidity,Null),
                    'solubility', COALESCE(specification.solubility,Null),
                    'edited', COALESCE(specification.edited,Null)
                )
            ) FILTER (WHERE specification.language = 'en'), '[]'::jsonb), 
            'fr', COALESCE(jsonb_agg(
                jsonb_build_object(
                    'ph', COALESCE(specification.ph,Null),
                    'humidity', COALESCE(specification.humidity,Null),
                    'solubility', COALESCE(specification.solubility,Null),
                    'edited', COALESCE(specification.edited,Null)
                )
            ) FILTER (WHERE specification.language = 'fr'), '[]'::jsonb)
        )
    )
    INTO result_json
    FROM specification
    WHERE specification.label_id = label_info_id;
    RETURN result_json;
END;
$function$;
