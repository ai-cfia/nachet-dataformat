
CREATE OR REPLACE FUNCTION "fertiscan_0.0.18".olap_ingredient_creation()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'INSERT') THEN
        IF (NEW.id IS NOT NULL) AND (NEW.label_id IS NOT NULL) THEN
        -- Update the label_dimension table with the new ingredient_analysis_id
        UPDATE "fertiscan_0.0.18"."label_dimension" 
        SET ingredient_ids = array_append(ingredient_ids, NEW.id)
        WHERE label_dimension.label_id = NEW.label_id;
        ELSE
            -- Raise a warning if the condition is not met
            RAISE WARNING 'The OLAP dimension of this ingredient is not updated because the condition is not met';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS ingredient_creation ON "fertiscan_0.0.18".ingredient;
CREATE TRIGGER ingredient_creation
AFTER INSERT ON "fertiscan_0.0.18".ingredient
FOR EACH ROW
EXECUTE FUNCTION olap_ingredient_creation();

CREATE OR REPLACE FUNCTION "fertiscan_0.0.18".olap_ingredient_deletion()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'DELETE') THEN
        IF (OLD.id IS NOT NULL) AND (OLD.label_id IS NOT NULL) THEN
        -- Update the label_dimension table with the new ingredient_analysis_id
        UPDATE "fertiscan_0.0.18"."label_dimension" 
        SET ingredient_ids = array_remove(ingredient_ids, OLD.id)
        WHERE label_dimension.label_id = OLD.label_id;
        ELSE
            -- Raise a warning if the condition is not met
            RAISE WARNING 'The OLAP dimension of this ingredient is not updated because the condition is not met';
        END IF;
    END IF;
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS ingredient_deletion ON "fertiscan_0.0.18".ingredient;
CREATE TRIGGER ingredient_deletion
AFTER DELETE ON "fertiscan_0.0.18".ingredient
FOR EACH ROW
EXECUTE FUNCTION olap_ingredient_deletion();
