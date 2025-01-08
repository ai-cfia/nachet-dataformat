
CREATE OR REPLACE FUNCTION "fertiscan_0.0.18".get_ingredients_json(
label_info_id uuid)
RETURNS jsonb 
LANGUAGE plpgsql
AS $function$
DECLARE
    result_json jsonb;
    record_keeping_option boolean;
BEGIN

    -- Fetch the record_keeping value
    SELECT record_keeping
    INTO record_keeping_option
    FROM label_information
    WHERE id = label_info_id;
   
    IF record_keeping_option THEN
        RETURN jsonb_build_object('ingredients',jsonb_build_object('en', '[]'::jsonb, 'fr', '[]'::jsonb));
    END IF;

    SELECT jsonb_build_object(
        'ingredients', jsonb_build_object(
            'en',COALESCE(jsonb_agg(
                jsonb_build_object(
                    'name', COALESCE(ingredient.name, Null),
                    'value', COALESCE(ingredient.value,Null),
                    'unit', COALESCE(ingredient.unit,Null),
                    'edited', COALESCE(ingredient.edited,Null)
                )
            ) FILTER (WHERE ingredient.language = 'en'), '[]'::jsonb), 
            'fr', COALESCE(jsonb_agg(
                jsonb_build_object(
                    'name', COALESCE(ingredient.name, Null),
                    'value', COALESCE(ingredient.value,Null),
                    'unit', COALESCE(ingredient.unit,Null),
                    'edited', COALESCE(ingredient.edited,Null)
                )
            ) FILTER (WHERE ingredient.language = 'fr'), '[]'::jsonb)
        )
    )
    INTO result_json
    FROM ingredient
    WHERE ingredient.label_id = label_info_id;
    RETURN result_json;
END;
$function$;
