CREATE OR REPLACE FUNCTION "fertiscan_0.0.18".new_guaranteed_analysis(
name TEXT,
value FLOAT,
unit TEXT,
label_id UUID,
language "fertiscan_0.0.18".language,
edited BOOLEAN = FALSE,
element_id int = NULL
)
RETURNS uuid 
LANGUAGE plpgsql
AS $function$
DECLARE
    guaranteed_id uuid;
    record RECORD;
    _id uuid;
BEGIN
	IF COALESCE(name, value::text, unit,'') = '' THEN
		RAISE EXCEPTION 'ALL of the input parameters are null';
	END IF;
	INSERT INTO guaranteed (read_name, value, unit, edited, label_id, element_id, language)
	VALUES (
		name,
	    value,
	    unit,
		edited,
		label_id,
		element_id,
		language)
	RETURNING id INTO guaranteed_id;
    RETURN guaranteed_id;
END;
$function$;
