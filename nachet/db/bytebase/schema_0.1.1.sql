--Schema creation nachet_0.0.10
DO
$do$
BEGIN
IF (EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'nachet_0.1.1')) THEN

drop schema "nachet_0.1.1" cascade;
create schema "nachet_0.1.1";

    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";


    CREATE TABLE "nachet_0.1.1"."users" (
    "id" uuid PRIMARY KEY DEFAULT uuid_.uuid_generate_v4(),
    "email" text NOT NULL UNIQUE,
    "registration_date" timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" timestamp
    );

    Create table "nachet_0.1.1"."groups" (
        "id" uuid NOT NULL DEFAULT uuid_.uuid_generate_v4() PRIMARY KEY,
        "name" text NOT NULL,
        "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        "created_by_id" uuid NOT NULL REFERENCES "nachet_0.1.1".users(id)
    );

    Create table "nachet_0.1.1"."user_group" (
        "id" uuid NOT NULL DEFAULT uuid_.uuid_generate_v4() PRIMARY KEY,
        "user_id" uuid NOT NULL REFERENCES "nachet_0.1.1".users(id),
        "group_id" uuid NOT NULL REFERENCES "nachet_0.1.1".groups(id),
        "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        "assigned_by_id" uuid NOT NULL REFERENCES "nachet_0.1.1".users(id)
    );

    CREATE TABLE "nachet_0.1.1"."container" (
        "id" uuid NOT NULL DEFAULT uuid_.uuid_generate_v4() PRIMARY KEY,
        "name" text,
        "is_public" boolean NOT NULL DEFAULT false,
        "storage_prefix" text default 'user',
        "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        "created_by_id" uuid NOT NULL REFERENCES "nachet_0.1.1".users(id),
        "last_updated_by_id" uuid NOT NULL REFERENCES "nachet_0.1.1".users(id)
    );

    CREATE TABLE "nachet_0.1.1"."container_user" (
        "id" uuid NOT NULL DEFAULT uuid_.uuid_generate_v4() PRIMARY KEY,
        "user_id" uuid NOT NULL REFERENCES "nachet_0.1.1".users(id) ON DELETE cascade,
        "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        "created_by_id" uuid NOT NULL REFERENCES "nachet_0.1.1".users(id) ON DELETE SET NULL,
        "last_updated_by_id" uuid NOT NULL REFERENCES "nachet_0.1.1".users(id) ON DELETE SET NULL,
        "container_id" uuid NOT NULL REFERENCES "nachet_0.1.1".container(id) ON DELETE CASCADE
    );

    CREATE TABLE "nachet_0.1.1"."container_group" (
        "id" uuid NOT NULL DEFAULT uuid_.uuid_generate_v4() PRIMARY KEY,
        "group_id" uuid NOT NULL REFERENCES "nachet_0.1.1".groups(id) ON DELETE cascade,
        "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        "created_by_id" uuid NOT NULL REFERENCES "nachet_0.1.1".users(id) ON DELETE SET NULL,
        "last_updated_by_id" uuid NOT NULL REFERENCES "nachet_0.1.1".users(id) ON DELETE SET NULL,
        "container_id" uuid NOT NULL REFERENCES "nachet_0.1.1".container(id) ON DELETE CASCADE
    );

    CREATE TABLE "nachet_0.1.1"."picture_set" (
        "id" uuid NOT NULL DEFAULT uuid_.uuid_generate_v4() PRIMARY KEY,
        "picture_set" json NOT NULL,
        "owner_id" uuid NOT NULL REFERENCES "nachet_0.1.1".users(id),
        "upload_date" date NOT NULL DEFAULT current_timestamp,
        "name" text,
        "container_id" uuid NOT NULL REFERENCES "nachet_0.1.1".container(id) ON DELETE CASCADE
    );
    
    CREATE TABLE "nachet_0.1.1"."picture" (
        "id" uuid NOT NULL DEFAULT uuid_.uuid_generate_v4() PRIMARY KEY,
        "picture" json NOT NULL,
        "picture_set_id" uuid NOT null,
        "nb_obj" integer NOT NULL,
        "verified" boolean NOT NULL DEFAULT false,
        "upload_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY ("picture_set_id") REFERENCES "nachet_0.1.1"."picture_set"(id) ON DELETE CASCADE
    );
    CREATE TABLE "nachet_0.1.1"."object_type" (
        "id" SERIAL PRIMARY KEY,
        "name" text NOT NULL
    );

    -- Creating seed table and object type seed
    INSERT INTO "nachet_0.1.1"."object_type" ("name") VALUES ('seed');

    CREATE TABLE "nachet_0.1.1"."seed" (
        "id" uuid NOT NULL DEFAULT uuid_.uuid_generate_v4() PRIMARY KEY,
        "name" text NOT NULL,
        "object_type_id" integer GENERATED ALWAYS AS (1) STORED
    );

    CREATE TABLE "nachet_0.1.1"."picture_seed" (
        "id" uuid DEFAULT uuid_.uuid_generate_v4() PRIMARY KEY,
        "picture_id" uuid NOT NULL,
        "seed_id" uuid NOT NULL REFERENCES "nachet_0.1.1".seed(id),
        "upload_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY ("picture_id") REFERENCES "nachet_0.1.1"."picture"(id) ON DELETE CASCADE
    );

    CREATE TABLE "nachet_0.1.1"."inference" (
        "id" uuid NOT NULL DEFAULT uuid_.uuid_generate_v4() PRIMARY KEY,
        "inference" json NOT NULL,
        "picture_id" uuid NOT NULL,
        "upload_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        "user_id" uuid NOT NULL REFERENCES "nachet_0.1.1".users(id),
        "feedback_user_id" uuid,
        "verified" boolean DEFAULT false NOT NULL,
        FOREIGN KEY ("picture_id") REFERENCES "nachet_0.1.1"."picture"(id) ON DELETE CASCADE
    );

    CREATE TABLE "nachet_0.1.1"."task" (
        "id" SERIAL PRIMARY KEY,
        "name" text NOT NULL
    );
 
    CREATE TABLE "nachet_0.1.1"."model" (
        "id" uuid NOT NULL DEFAULT uuid_.uuid_generate_v4() PRIMARY KEY,
        "name" text NOT NULL,
        "endpoint_name" text NOT NULL,
        "task_id" integer NOT NULL REFERENCES "nachet_0.1.1".task(id),
        "upload_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP NOT NULL
    );
    
    CREATE TABLE "nachet_0.1.1"."model_version" (
        "id" uuid NOT NULL DEFAULT uuid_.uuid_generate_v4() PRIMARY KEY,
        "model_id" uuid NOT NULL REFERENCES "nachet_0.1.1".model(id),
        "data" json NOT NULL,
        "version" text NOT NULL,
        "upload_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    
    Alter table "nachet_0.1.1".model ADD "active_version" uuid REFERENCES "nachet_0.1.1".model_version(id);

    CREATE TABLE "nachet_0.1.1"."object" (
        "id" uuid NOT NULL DEFAULT uuid_.uuid_generate_v4() PRIMARY KEY,
        "box_metadata" json NOT NULL,
        "inference_id" uuid NOT NULL,
        "type_id" integer NOT NULL REFERENCES "nachet_0.1.1".object_type(id),
        "verified_id" uuid ,
        "valid" boolean NOT NULL DEFAULT true,
        "top_id" uuid,
        "upload_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        "manual_detection" boolean NOT NULL DEFAULT false,
        FOREIGN KEY ("inference_id") REFERENCES "nachet_0.1.1"."inference"(id) ON DELETE CASCADE
    );
    
    
    CREATE TABLE "nachet_0.1.1"."pipeline" (
        "id" uuid NOT NULL DEFAULT uuid_.uuid_generate_v4() PRIMARY KEY,
        "name" text NOT NULL,
        "active" boolean NOT NULL DEFAULT false,
        "is_default" boolean NOT NULL default false,
        "data" json
    );
    
    Alter table "nachet_0.1.1"."inference" ADD "pipeline_id" uuid REFERENCES "nachet_0.1.1"."pipeline"(id);


    CREATE FUNCTION "nachet_0.1.1".pipeline_default_trigger() RETURNS TRIGGER AS $$
    BEGIN
        IF NEW.is_default THEN
            UPDATE "nachet_0.1.1".pipeline SET is_default=false WHERE is_default=true;
        END IF;
        RETURN NEW;
    END;
   $$language plpgsql;
  
    CREATE TRIGGER "pipeline_default_trigger" BEFORE insert OR UPDATE ON "nachet_0.1.1"."pipeline"
    FOR EACH ROW EXECUTE FUNCTION "nachet_0.1.1".pipeline_default_trigger();

    CREATE TABLE "nachet_0.1.1"."pipeline_default" (
        "id" uuid NOT NULL DEFAULT uuid_.uuid_generate_v4() PRIMARY KEY,
        "pipeline_id" uuid NOT NULL REFERENCES "nachet_0.1.1".pipeline(id),
        "user_id" uuid NOT NULL REFERENCES "nachet_0.1.1".users(id)
    );

    CREATE UNIQUE INDEX "nachet_0.0.10_pipeline_default" ON "nachet_0.1.1".pipeline ("is_default") where is_default=true;
    
    CREATE TABLE "nachet_0.1.1"."pipeline_model" (
        "id" uuid NOT NULL DEFAULT uuid_.uuid_generate_v4() PRIMARY KEY,
        "pipeline_id" uuid NOT NULL REFERENCES "nachet_0.1.1".pipeline(id),
        "model_id" uuid NOT NULL REFERENCES "nachet_0.1.1".model(id)
    );
    
    CREATE TABLE "nachet_0.1.1"."seed_obj" (
        "id" uuid NOT NULL DEFAULT uuid_.uuid_generate_v4() PRIMARY KEY,
        "seed_id" uuid NOT NULL REFERENCES "nachet_0.1.1".seed(id),
        "object_id" uuid NOT NULL,
        "score" float NOT NULL,
        FOREIGN KEY ("object_id") REFERENCES "nachet_0.1.1"."object"(id) ON DELETE CASCADE
    );  

    CREATE OR REPLACE FUNCTION verified_inference() RETURNS TRIGGER LANGUAGE plpgsql AS $$
  BEGIN
    IF NEW.verified = true THEN
        INSERT INTO picture_seed (picture_id, seed_id)
          SELECT 
            New.picture_id, 
            so.seed_id  
          FROM object obj 
            LEFT JOIN seed_obj so 
              ON so.id = obj.verified_id  
          WHERE obj.inference_id = NEW.id and obj.verified_id is not null;
    END IF;
    RETURN NEW;
  END;
$$;

CREATE TRIGGER verified_inference_trigger 
AFTER UPDATE ON "nachet_0.1.1".inference
FOR EACH ROW 
WHEN (NEW.verified = true)
EXECUTE FUNCTION verified_inference();

    INSERT INTO "nachet_0.1.1".seed(name) VALUES
    ('Brassica napus'),
    ('Brassica juncea'),
    ('Cirsium arvense'),
    ('Cirsium vulgare'),
    ('Carduus nutans'),
    ('Bromus secalinus'),
    ('Bromus hordeaceus'),
    ('Bromus japonicus'),
    ('Lolium temulentum'),
    ('Solanum carolinense'),
    ('Solanum nigrum'),
    ('Solanum rostratum'),
    ('Ambrosia artemisiifolia'),
    ('Ambrosia trifida'),
    ('Ambrosia psilostachya');

    INSERT INTO "nachet_0.1.1".task(name) VALUES
    ('Object Detection'),
    ('Classification'),
    ('Segmentation');

    INSERT INTO "nachet_0.1.1".model(endpoint_name,name,task_id) VALUES
    ('Nachet-6seeds','m-14of15seeds-6seedsmag',1),
    ('Seed-detector','seed-detector-1',1),
    ('Swin','swinv1-base-dataaugv2-1',2);

    INSERT INTO "nachet_0.1.1".pipeline(name,active,is_default) VALUES
    ('6 Seed Detector',true,false),
    ('Swin transformer',true,true);

    INSERT INTO "nachet_0.1.1".pipeline_model(pipeline_id,model_id) 
    (Select p.id,m.id from "nachet_0.1.1".model as m, "nachet_0.1.1".pipeline as p where 
    (m.endpoint_name='Nachet-6seeds' and p.name='6 Seed Detector') or 
    (m.endpoint_name='Seed-detector' and p.name='Swin transformer') or
   	(m.endpoint_name='Swin' and p.name='Swin transformer')); 

    CREATE OR REPLACE FUNCTION "nachet_0.1.1".picture_set_default_name() 
    RETURNS TRIGGER 
    LANGUAGE plpgsql 
    AS $$
    BEGIN
        IF NEW.name IS NULL THEN
            NEW.name := NEW.id::text;
        END IF;
        RETURN NEW;
    END;
    $$;

    CREATE TRIGGER picture_set_default_name_trigger 
    BEFORE INSERT ON "nachet_0.1.1".picture_set
    FOR EACH ROW 
    WHEN (NEW.name IS NULL)
    EXECUTE FUNCTION "nachet_0.1.1".picture_set_default_name();

END
$do$
