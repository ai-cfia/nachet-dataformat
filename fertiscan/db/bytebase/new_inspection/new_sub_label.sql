CREATE OR REPLACE FUNCTION "fertiscan_0.0.18".new_sub_label(
	content_fr text DEFAULT NULL::text, 
	content_en text DEFAULT NULL::text, 
	label_id uuid DEFAULT NULL::uuid, 
	sub_type_id uuid DEFAULT NULL::uuid, 
	edited boolean DEFAULT false)
 RETURNS uuid
 LANGUAGE plpgsql
AS $function$
DECLARE
    sub_label_id uuid;
    record RECORD;
    _id uuid;
BEGIN
	-- Check if label_id is null
    IF label_id IS NULL THEN
        RAISE EXCEPTION 'label_id cannot be null when creating a new sub_label';
    END IF;

    -- Check if sub_type_id is null
    IF sub_type_id IS NULL THEN
        RAISE EXCEPTION 'sub_type_id cannot be null when creating a new sub_label';
    END IF;

    INSERT INTO sub_label (text_content_fr,text_content_en, label_id, edited, sub_type_id)
	VALUES (
	    content_fr,
		content_en,
		label_id,
		edited,
		sub_type_id
	)
    RETURNING id INTO sub_label_id;
    RETURN sub_label_id;
END;
$function$;
