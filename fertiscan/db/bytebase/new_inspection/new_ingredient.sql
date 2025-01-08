CREATE OR REPLACE FUNCTION "fertiscan_0.0.18".new_ingredient(
name TEXT,
value FLOAt,
read_unit TEXT,
label_id UUID,
language "fertiscan_0.0.18".language,
organic BOOLEAN,
active BOOLEAN,
edited BOOLEAN = FALSE
)
RETURNS uuid 
LANGUAGE plpgsql
AS $function$
DECLARE
    ingredient_id uuid;
    record RECORD;
    _id uuid;
BEGIN
    IF COALESCE(name, value::text, read_unit,'') = '' THEN
        RAISE EXCEPTION 'ALL of the input parameters are null';
    END IF;
    INSERT INTO ingredient (
        organic, 
        active, 
        name,
        value, 
        unit, 
        edited, 
        label_id, 
        language)
    VALUES (
        organic, 
        active,  
        name,
        value,
        read_unit,
        edited, -- Assuming edited status
        label_id,  
        language
    )
    RETURNING id INTO ingredient_id;
    RETURN ingredient_id;
END;
$function$;
