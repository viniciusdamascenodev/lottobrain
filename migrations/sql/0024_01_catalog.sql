CREATE EXTENSION IF NOT EXISTS btree_gist WITH SCHEMA public;
CREATE SCHEMA lb;
REVOKE ALL ON SCHEMA lb FROM PUBLIC;

CREATE DOMAIN lb.sha256 AS text CHECK (VALUE ~ '^[0-9a-f]{64}$');
CREATE DOMAIN lb.key AS text CHECK (VALUE ~ '^[a-z][a-z0-9_]*$');
CREATE DOMAIN lb.currency AS text CHECK (VALUE ~ '^[A-Z]{3}$');
CREATE DOMAIN lb.value_status AS text CHECK (VALUE IN ('known','unknown','not_applicable','rejected'));

CREATE TABLE lb.lottery (
 id uuid PRIMARY KEY, slug lb.key NOT NULL UNIQUE, display_name text NOT NULL CHECK (btrim(display_name) <> ''),
 origin_jurisdiction text NOT NULL, status text NOT NULL CHECK (status IN ('draft','validating','active','suspended','archived')),
 default_timezone text, default_currency lb.currency, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE lb.lottery_scope (
 id uuid PRIMARY KEY, lottery_id uuid NOT NULL REFERENCES lb.lottery ON DELETE RESTRICT,
 key lb.key NOT NULL, kind text NOT NULL CHECK (kind IN ('common_result','territorial','provider_context')),
 jurisdiction_code text, label text NOT NULL, default_currency lb.currency,
 UNIQUE(lottery_id,key), UNIQUE(id,lottery_id)
);
CREATE TABLE lb.rule_version (
 id uuid PRIMARY KEY, lottery_id uuid NOT NULL REFERENCES lb.lottery ON DELETE RESTRICT,
 version_label lb.key NOT NULL, valid_from date NOT NULL, valid_to date,
 status text NOT NULL CHECK (status IN ('draft','validated','retired')),
 evidence_reference text NOT NULL, evidence_level text NOT NULL,
 CHECK (isfinite(valid_from) AND (valid_to IS NULL OR (isfinite(valid_to) AND valid_to > valid_from))),
 UNIQUE(lottery_id,version_label), UNIQUE(id,lottery_id),
 EXCLUDE USING gist (lottery_id WITH =, daterange(valid_from,valid_to,'[)') WITH &&) WHERE (status = 'validated')
);
CREATE TABLE lb.series_definition (
 id uuid PRIMARY KEY, rule_version_id uuid NOT NULL REFERENCES lb.rule_version ON DELETE RESTRICT,
 key lb.key NOT NULL, label text NOT NULL, role text NOT NULL CHECK (role IN ('primary','additional')),
 required boolean NOT NULL, CHECK (role <> 'primary' OR required),
 UNIQUE(rule_version_id,key), UNIQUE(id,rule_version_id)
);
CREATE TABLE lb.component_definition (
 id uuid PRIMARY KEY, series_definition_id uuid NOT NULL REFERENCES lb.series_definition ON DELETE RESTRICT,
 key lb.key NOT NULL, value_type text NOT NULL CHECK (value_type IN ('integer','text')),
 min_count integer NOT NULL CHECK (min_count >= 0), max_count integer NOT NULL CHECK (max_count >= min_count),
 min_value integer, max_value integer, unique_values boolean NOT NULL,
 order_semantics text NOT NULL CHECK (order_semantics IN ('draw_order','sorted','none')),
 position integer NOT NULL CHECK (position >= 0),
 CHECK ((value_type = 'integer' AND min_value IS NOT NULL AND max_value IS NOT NULL AND min_value <= max_value)
     OR (value_type = 'text' AND min_value IS NULL AND max_value IS NULL)),
 UNIQUE(series_definition_id,key), UNIQUE(series_definition_id,position), UNIQUE(id,series_definition_id)
);
CREATE TABLE lb.prize_tier_definition (
 id uuid PRIMARY KEY, rule_version_id uuid NOT NULL REFERENCES lb.rule_version ON DELETE RESTRICT,
 key lb.key NOT NULL, label text NOT NULL, criterion_key lb.key NOT NULL, criterion_description text NOT NULL,
 position integer NOT NULL CHECK (position >= 0),
 UNIQUE(rule_version_id,key), UNIQUE(rule_version_id,position), UNIQUE(id,rule_version_id)
);
CREATE TABLE lb.data_source (
 id uuid PRIMARY KEY, lottery_id uuid NOT NULL REFERENCES lb.lottery ON DELETE RESTRICT,
 key lb.key NOT NULL, authority text NOT NULL, readiness text NOT NULL,
 base_url text NOT NULL, data_format text NOT NULL, purposes text[] NOT NULL, policy_reference text,
 UNIQUE(lottery_id,key), UNIQUE(id,lottery_id)
);

CREATE FUNCTION lb.check_rule_catalog() RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog, lb AS $$
DECLARE rid uuid; r lb.rule_version;
BEGIN
 IF TG_TABLE_NAME = 'rule_version' THEN rid := NEW.id;
 ELSE rid := COALESCE(NEW.rule_version_id, OLD.rule_version_id); END IF;
 SELECT * INTO r FROM lb.rule_version WHERE id = rid;
 IF r.status = 'validated' AND (
   (SELECT count(*) FROM lb.series_definition WHERE rule_version_id = rid AND role = 'primary') <> 1
   OR EXISTS (SELECT FROM lb.series_definition s WHERE s.rule_version_id = rid
     AND NOT EXISTS (SELECT FROM lb.component_definition c WHERE c.series_definition_id = s.id))
 ) THEN RAISE EXCEPTION 'invalid_rule_catalog' USING ERRCODE = '23514'; END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER rule_catalog AFTER INSERT OR UPDATE ON lb.rule_version
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION lb.check_rule_catalog();
CREATE CONSTRAINT TRIGGER series_catalog AFTER INSERT OR UPDATE OR DELETE ON lb.series_definition
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION lb.check_rule_catalog();
