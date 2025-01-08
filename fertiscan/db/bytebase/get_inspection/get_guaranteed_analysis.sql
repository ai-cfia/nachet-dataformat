CREATE OR REPLACE FUNCTION "fertiscan_0.0.18".get_guaranteed_analysis_json(
    label_info_id uuid
)
RETURNS jsonb 
LANGUAGE plpgsql
AS $function$
DECLARE
    result_json jsonb;
    result_json_title jsonb;
BEGIN
    -- build Guaranteed_analysis nutrients
    SELECT jsonb_build_object(
        'en', COALESCE(jsonb_agg(
            jsonb_build_object(
                'name', guaranteed.read_name,
                'value', guaranteed.value,
                'unit', guaranteed.unit,
                'edited', guaranteed.edited
            )
        ) FILTER (WHERE guaranteed.language = 'en'), '[]'::jsonb), 
        'fr', COALESCE(jsonb_agg(
            jsonb_build_object(
                'name', guaranteed.read_name,
                'value', guaranteed.value,
                'unit', guaranteed.unit,
                'edited', guaranteed.edited
            )
        ) FILTER (WHERE guaranteed.language = 'fr'), '[]'::jsonb)
    )
    INTO result_json
    FROM "fertiscan_0.0.18".guaranteed
    WHERE guaranteed.label_id = label_info_id;

    -- build Guaranteed_analysis title json
    SELECT jsonb_build_object(
        'title_en', guaranteed_title_en,
        'title_fr', guaranteed_title_fr, 
        'is_minimal', title_is_minimal
    )
    INTO result_json_title
    FROM "fertiscan_0.0.18".label_information 
    WHERE id = label_info_id;

    -- merge JSONs
    RETURN jsonb_build_object(
        'title', CASE 
            WHEN (result_json_title->>'title_en' IS NULL OR result_json_title->>'title_en' = '')
            AND (result_json_title->>'title_fr' IS NULL OR result_json_title->>'title_fr' = '') 
            THEN NULL
            ELSE jsonb_build_object(
                'en', COALESCE(result_json_title->>'title_en', ''),
                'fr', COALESCE(result_json_title->>'title_fr', '')
            )
        END,
        'is_minimal', result_json_title->'is_minimal',
        'en', COALESCE(result_json->'en', '[]'::jsonb),
        'fr', COALESCE(result_json->'fr', '[]'::jsonb)
    );
END;
$function$;
