
CREATE OR REPLACE FUNCTION "fertiscan_0.0.18".olap_metrics_creation()
RETURNS TRIGGER AS $$
DECLARE
    metric_type TEXT;
BEGIN
    IF (TG_OP = 'INSERT') THEN
        IF (NEW.id IS NOT NULL) AND (NEW.label_id IS NOT NULL) AND (NEW.metric_type IS NOT NULL) THEN
        -- Update the label_dimension table with the new metrics_id
        metric_type = NEW.metric_type || '_ids';
        IF (metric_type ILIKE 'test%') THEN
                RETURN NEW;
        END IF;
        EXECUTE format('UPDATE "fertiscan_0.0.18"."label_dimension" 
                    SET %I = array_append(%I, %L) 
                    WHERE label_dimension.label_id = %L', 
                    metric_type, metric_type, NEW.id, NEW.label_id);
        ELSE
            -- Raise a warning if the condition is not met
            RAISE WARNING 'The OLAP dimension of this metrics is not updated because the condition is not met';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS metrics_creation ON "fertiscan_0.0.18".metric;
CREATE TRIGGER metrics_creation
AFTER INSERT ON "fertiscan_0.0.18".metric
FOR EACH ROW
EXECUTE FUNCTION olap_metrics_creation();

CREATE OR REPLACE FUNCTION "fertiscan_0.0.18".olap_metrics_deletion()
RETURNS TRIGGER AS $$
DECLARE
    metric_type TEXT;
BEGIN
    IF (TG_OP = 'DELETE') THEN
        IF (OLD.id IS NOT NULL) AND (OLD.label_id IS NOT NULL) AND (OLD.metric_type IS NOT NULL) THEN
        -- Update the label_dimension table with the new metrics_id
        metric_type = OLD.metric_type || '_ids';
        IF (metric_type ILIKE 'test%') THEN
                RETURN OLD;
        END IF;
        EXECUTE format('UPDATE "fertiscan_0.0.18"."label_dimension" 
                    SET %I = array_remove(%I, %L) 
                    WHERE label_dimension.label_id = %L', 
                    metric_type, metric_type, OLD.id, OLD.label_id);
        ELSE
            -- Raise a warning if the condition is not met
            RAISE WARNING 'The OLAP dimension of this metrics is not updated because the condition is not met';
        END IF;
    END IF;
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS metrics_deletion ON "fertiscan_0.0.18".metric;
CREATE TRIGGER metrics_deletion
AFTER DELETE ON "fertiscan_0.0.18".metric
FOR EACH ROW
EXECUTE FUNCTION olap_metrics_deletion();
