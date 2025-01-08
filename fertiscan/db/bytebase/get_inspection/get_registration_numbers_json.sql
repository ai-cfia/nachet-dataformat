
CREATE OR REPLACE FUNCTION "fertiscan_0.0.18".get_registration_numbers_json(
label_info_id uuid)
RETURNS jsonb 
LANGUAGE plpgsql
AS $function$
DECLARE
    result_json jsonb;
BEGIN
    SELECT jsonb_build_object(
                'registration_numbers', 
                    COALESCE(jsonb_agg(
                        jsonb_build_object(
                            'registration_number', COALESCE(registration_number_information.identifier,Null),
                            'is_an_ingredient', COALESCE(registration_number_information.is_an_ingredient,Null),
                            'edited', COALESCE(registration_number_information.edited,Null)
                        )
                    ), '[]'::jsonb)
           )
    INTO result_json
    FROM registration_number_information
    WHERE registration_number_information.label_id = label_info_id;
    RETURN result_json;
END;
$function$;
