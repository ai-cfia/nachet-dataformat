CREATE OR REPLACE FUNCTION "fertiscan_0.0.18".get_sub_label_json(label_info_id uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
DECLARE
	result_json jsonb;
BEGIN
    SELECT jsonb_object_agg(
                sub_type.type_en, 
                jsonb_build_object(
				    'en', COALESCE(sub_label_data.texts_en, array[]::text[]),
				    'fr', COALESCE(sub_label_data.texts_fr, array[]::text[])
				)
           )
    INTO result_json
    FROM sub_type
    LEFT JOIN (
        SELECT 
            sub_type_id,
            array_agg(sub_label.text_content_en) AS texts_en,
            array_agg(sub_label.text_content_fr) AS texts_fr
        FROM sub_label
        WHERE sub_label.label_id = label_info_id 
        GROUP BY sub_label.sub_type_id
    ) AS sub_label_data
    ON sub_type.id = sub_label_data.sub_type_id;

    RETURN result_json;
END;
$function$;
