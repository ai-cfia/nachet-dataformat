-- Trigger function
CREATE OR REPLACE FUNCTION "fertiscan_0.0.18".olap_registration_number_creation()
RETURNS TRIGGER AS $$
BEGIN
    -- Check if the operation is an INSERT
    IF (TG_OP = 'INSERT') THEN
        -- Check if the NEW.id is not NULL
        IF (NEW.id IS NOT NULL) AND (NEW.label_id IS NOT NULL) AND (NEW.identifier IS NOT NULL) THEN
            -- Update the label_dimension table with the new guaranteed_analysis_id
            UPDATE "fertiscan_0.0.18"."label_dimension" 
            SET registration_number_ids = array_append(registration_number_ids, NEW.id)
            WHERE label_dimension.label_id = NEW.label_id;
            ELSE
            -- Raise a warning if the condition is not met
            RAISE WARNING 'The OLAP dimension of this registration_number is not updated because the condition is not met';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger
DROP TRIGGER IF EXISTS registration_number_creation ON "fertiscan_0.0.18".registration_number_information;
CREATE TRIGGER registration_number_creation
AFTER INSERT ON "fertiscan_0.0.18".registration_number_information
FOR EACH ROW
EXECUTE FUNCTION olap_registration_number_creation();

-- Trigger function
CREATE OR REPLACE FUNCTION "fertiscan_0.0.18".olap_registration_number_deletion()
RETURNS TRIGGER AS $$
BEGIN
    -- Check if the operation is an INSERT
    IF (TG_OP = 'DELETE') THEN
        -- Check if the NEW.id is not NULL
        IF (OLD.id IS NOT NULL) AND (OLD.label_id IS NOT NULL) THEN
            -- Update the label_dimension table with the new guaranteed_analysis_id
            UPDATE "fertiscan_0.0.18"."label_dimension" 
            SET registration_number_ids = array_remove(registration_number_ids, OLD.id)
            WHERE label_dimension.label_id = OLD.label_id;
            ELSE
            -- Raise a warning if the condition is not met
            RAISE WARNING 'The OLAP dimension of this registration_number is not updated because the condition is not met';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger
DROP TRIGGER IF EXISTS registration_number_deletion ON "fertiscan_0.0.18".registration_number_information;
CREATE TRIGGER registration_number_deletion
AFTER INSERT ON "fertiscan_0.0.18".registration_number_information
FOR EACH ROW
EXECUTE FUNCTION olap_registration_number_deletion();
