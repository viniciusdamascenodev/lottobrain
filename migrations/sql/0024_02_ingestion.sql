CREATE TABLE lb.ingestion_run (
 id uuid PRIMARY KEY, lottery_id uuid NOT NULL, source_id uuid NOT NULL,
 idempotency_key text NOT NULL, request_hash lb.sha256 NOT NULL,
 source_config_snapshot jsonb NOT NULL CHECK (jsonb_typeof(source_config_snapshot) = 'object'
   AND source_config_snapshot @> '{"schema_version":1}'::jsonb
   AND source_config_snapshot - ARRAY['schema_version','authority','readiness','base_url','policy_reference','configuration_origin'] = '{}'::jsonb
   AND pg_column_size(source_config_snapshot) <= 16384),
 mode text NOT NULL, status text NOT NULL CHECK (status IN ('running','completed','failed','stopped')),
 started_at timestamptz NOT NULL, finished_at timestamptz, correlation_id uuid NOT NULL,
 CHECK (finished_at IS NULL OR finished_at >= started_at),
 UNIQUE(source_id,idempotency_key), UNIQUE(id,source_id,lottery_id),
 FOREIGN KEY(source_id,lottery_id) REFERENCES lb.data_source(id,lottery_id) ON DELETE RESTRICT
);
CREATE TABLE lb.fetch_attempt (
 id uuid PRIMARY KEY, run_id uuid NOT NULL, source_id uuid NOT NULL, lottery_id uuid NOT NULL,
 ordinal integer NOT NULL CHECK (ordinal > 0), requested_identity text, url text NOT NULL,
 started_at timestamptz NOT NULL, finished_at timestamptz,
 outcome text NOT NULL CHECK (outcome IN ('running','response','transport_error')),
 http_status integer CHECK (http_status BETWEEN 100 AND 599), error_code text,
 CHECK (finished_at IS NULL OR finished_at >= started_at),
 CHECK ((outcome = 'running' AND finished_at IS NULL AND http_status IS NULL)
 OR (outcome = 'response' AND finished_at IS NOT NULL AND http_status IS NOT NULL)
 OR (outcome = 'transport_error' AND finished_at IS NOT NULL AND http_status IS NULL AND error_code IS NOT NULL)),
 UNIQUE(run_id,ordinal), UNIQUE(id,source_id,lottery_id),
 FOREIGN KEY(run_id,source_id,lottery_id) REFERENCES lb.ingestion_run(id,source_id,lottery_id) ON DELETE RESTRICT
);
CREATE TABLE lb.raw_artifact (
 id uuid PRIMARY KEY, sha256 lb.sha256 NOT NULL UNIQUE, byte_count bigint NOT NULL CHECK (byte_count >= 0),
 object_key text NOT NULL UNIQUE, storage_state text NOT NULL CHECK (storage_state IN ('available','missing','quarantined')),
 registered_at timestamptz NOT NULL, UNIQUE(id,byte_count)
);
CREATE TABLE lb.capture_receipt (
 id uuid PRIMARY KEY, lottery_id uuid NOT NULL, source_id uuid NOT NULL, fetch_attempt_id uuid UNIQUE,
 artifact_id uuid NOT NULL, capture_kind text NOT NULL CHECK (capture_kind IN ('http','legacy_import')),
 captured_at timestamptz NOT NULL, effective_url text NOT NULL,
 http_status integer CHECK (http_status BETWEEN 100 AND 599), content_type text NOT NULL,
 byte_count bigint NOT NULL, legacy_reference text,
 CHECK ((capture_kind = 'http' AND fetch_attempt_id IS NOT NULL AND http_status IS NOT NULL)
 OR (capture_kind = 'legacy_import' AND legacy_reference IS NOT NULL)),
 UNIQUE(id,lottery_id), UNIQUE(id,source_id,lottery_id),
 FOREIGN KEY(source_id,lottery_id) REFERENCES lb.data_source(id,lottery_id) ON DELETE RESTRICT,
 FOREIGN KEY(fetch_attempt_id,source_id,lottery_id) REFERENCES lb.fetch_attempt(id,source_id,lottery_id) ON DELETE RESTRICT,
 FOREIGN KEY(artifact_id,byte_count) REFERENCES lb.raw_artifact(id,byte_count) ON DELETE RESTRICT
);
CREATE INDEX capture_source_time ON lb.capture_receipt(source_id,captured_at);
CREATE TABLE lb.processing_run (
 id uuid PRIMARY KEY, receipt_id uuid NOT NULL, lottery_id uuid NOT NULL,
 adapter_version text NOT NULL, code_version text NOT NULL, canonicalization_version text NOT NULL,
 validation_policy_version text NOT NULL, catalog_fingerprint lb.sha256 NOT NULL,
 status text NOT NULL CHECK (status IN ('running','completed','failed')),
 started_at timestamptz NOT NULL, finished_at timestamptz,
 CHECK (finished_at IS NULL OR finished_at >= started_at),
 UNIQUE(receipt_id,adapter_version,code_version,canonicalization_version,validation_policy_version,catalog_fingerprint),
 UNIQUE(id,lottery_id), FOREIGN KEY(receipt_id,lottery_id) REFERENCES lb.capture_receipt(id,lottery_id) ON DELETE RESTRICT
);
CREATE TABLE lb.processing_attempt (
 id uuid PRIMARY KEY, processing_run_id uuid NOT NULL REFERENCES lb.processing_run ON DELETE RESTRICT,
 ordinal integer NOT NULL CHECK (ordinal > 0), command_key text NOT NULL UNIQUE, request_hash lb.sha256 NOT NULL,
 outcome text NOT NULL, started_at timestamptz NOT NULL, finished_at timestamptz, error_code text,
 CHECK (finished_at IS NULL OR finished_at >= started_at), UNIQUE(processing_run_id,ordinal)
);
CREATE TABLE lb.draw (
 id uuid PRIMARY KEY, lottery_id uuid NOT NULL REFERENCES lb.lottery ON DELETE RESTRICT,
 created_at timestamptz NOT NULL, latest_candidate_revision_id uuid, published_revision_id uuid,
 row_version bigint NOT NULL DEFAULT 0 CHECK (row_version >= 0), UNIQUE(id,lottery_id),
 -- Gate: nenhuma publicação sem implementar T5/decisões/outbox.
 CONSTRAINT publication_not_implemented CHECK (published_revision_id IS NULL)
);
CREATE TABLE lb.draw_revision (
 id uuid PRIMARY KEY, draw_id uuid NOT NULL, lottery_id uuid NOT NULL,
 revision_no integer NOT NULL CHECK (revision_no > 0), draw_date_local date NOT NULL CHECK (isfinite(draw_date_local)),
 rule_version_id uuid NOT NULL, content_hash lb.sha256 NOT NULL, canonicalization_version text NOT NULL,
 seal_state text NOT NULL CHECK (seal_state IN ('building','sealed')), sealed_at timestamptz,
 created_at timestamptz NOT NULL, metadata jsonb NOT NULL DEFAULT '{}' CHECK (jsonb_typeof(metadata) = 'object'),
 CHECK ((seal_state = 'building' AND sealed_at IS NULL) OR (seal_state = 'sealed' AND sealed_at IS NOT NULL)),
 UNIQUE(draw_id,revision_no), UNIQUE(id,draw_id,lottery_id), UNIQUE(id,rule_version_id,lottery_id),
 FOREIGN KEY(draw_id,lottery_id) REFERENCES lb.draw(id,lottery_id) ON DELETE RESTRICT,
 FOREIGN KEY(rule_version_id,lottery_id) REFERENCES lb.rule_version(id,lottery_id) ON DELETE RESTRICT
);
ALTER TABLE lb.draw ADD FOREIGN KEY(latest_candidate_revision_id,id,lottery_id)
 REFERENCES lb.draw_revision(id,draw_id,lottery_id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE lb.draw ADD FOREIGN KEY(published_revision_id,id,lottery_id)
 REFERENCES lb.draw_revision(id,draw_id,lottery_id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
CREATE TABLE lb.candidate_observation (
 id uuid PRIMARY KEY, processing_run_id uuid NOT NULL, row_locator text NOT NULL,
 lottery_id uuid NOT NULL, draw_id uuid, revision_id uuid,
 decision text NOT NULL CHECK (decision IN ('new','unchanged','correction_candidate','replayed','quarantined','rejected')),
 semantic_hash lb.sha256, diagnostic_payload jsonb, completed_at timestamptz NOT NULL,
 CHECK ((decision IN ('new','unchanged','correction_candidate','replayed') AND draw_id IS NOT NULL AND revision_id IS NOT NULL AND semantic_hash IS NOT NULL)
 OR (decision IN ('quarantined','rejected') AND revision_id IS NULL)),
 UNIQUE(processing_run_id,row_locator), UNIQUE(id,processing_run_id), UNIQUE(id,draw_id,lottery_id),
 FOREIGN KEY(processing_run_id,lottery_id) REFERENCES lb.processing_run(id,lottery_id) ON DELETE RESTRICT,
 FOREIGN KEY(draw_id,lottery_id) REFERENCES lb.draw(id,lottery_id) ON DELETE RESTRICT,
 FOREIGN KEY(revision_id,draw_id,lottery_id) REFERENCES lb.draw_revision(id,draw_id,lottery_id) ON DELETE RESTRICT
);
CREATE INDEX observation_revision ON lb.candidate_observation(revision_id);
CREATE TABLE lb.validation_issue (
 id uuid PRIMARY KEY, processing_run_id uuid NOT NULL REFERENCES lb.processing_run ON DELETE RESTRICT,
 observation_id uuid, code text NOT NULL, severity text NOT NULL CHECK (severity IN ('info','warning','error')),
 field_path text NOT NULL, observed_value text, expected_value text, resolution_reference text,
 FOREIGN KEY(observation_id,processing_run_id) REFERENCES lb.candidate_observation(id,processing_run_id) ON DELETE RESTRICT
);
CREATE TABLE lb.draw_identity (
 id uuid PRIMARY KEY, lottery_id uuid NOT NULL, draw_id uuid NOT NULL, namespace lb.key NOT NULL,
 value text NOT NULL CHECK (btrim(value) <> ''), assurance text NOT NULL CHECK (assurance IN ('official','provisional')),
 active boolean NOT NULL, evidence_observation_id uuid NOT NULL,
 UNIQUE(lottery_id,namespace,value),
 FOREIGN KEY(draw_id,lottery_id) REFERENCES lb.draw(id,lottery_id) ON DELETE RESTRICT,
 FOREIGN KEY(evidence_observation_id,draw_id,lottery_id) REFERENCES lb.candidate_observation(id,draw_id,lottery_id) ON DELETE RESTRICT
);
CREATE UNIQUE INDEX active_draw_identity ON lb.draw_identity(draw_id,namespace) WHERE active;
CREATE TABLE lb.external_draw_reference (
 id uuid PRIMARY KEY, lottery_id uuid NOT NULL, source_id uuid NOT NULL, draw_id uuid NOT NULL,
 namespace lb.key NOT NULL, value text NOT NULL CHECK (btrim(value) <> ''), evidence_observation_id uuid NOT NULL,
 UNIQUE(source_id,namespace,value),
 FOREIGN KEY(source_id,lottery_id) REFERENCES lb.data_source(id,lottery_id) ON DELETE RESTRICT,
 FOREIGN KEY(draw_id,lottery_id) REFERENCES lb.draw(id,lottery_id) ON DELETE RESTRICT,
 FOREIGN KEY(evidence_observation_id,draw_id,lottery_id) REFERENCES lb.candidate_observation(id,draw_id,lottery_id) ON DELETE RESTRICT
);
CREATE TABLE lb.result_series (
 id uuid PRIMARY KEY, revision_id uuid NOT NULL, rule_version_id uuid NOT NULL, lottery_id uuid NOT NULL,
 series_definition_id uuid NOT NULL,
 UNIQUE(revision_id,series_definition_id), UNIQUE(id,revision_id,series_definition_id), UNIQUE(id,revision_id),
 FOREIGN KEY(revision_id,rule_version_id,lottery_id) REFERENCES lb.draw_revision(id,rule_version_id,lottery_id) ON DELETE RESTRICT,
 FOREIGN KEY(series_definition_id,rule_version_id) REFERENCES lb.series_definition(id,rule_version_id) ON DELETE RESTRICT
);
CREATE TABLE lb.component_value (
 result_series_id uuid NOT NULL, revision_id uuid NOT NULL, series_definition_id uuid NOT NULL,
 component_definition_id uuid NOT NULL, ordinal integer NOT NULL CHECK (ordinal > 0),
 integer_value integer, text_value text, extraction_ordinal integer CHECK (extraction_ordinal > 0),
 CHECK (num_nonnulls(integer_value,text_value) = 1),
 PRIMARY KEY(result_series_id,component_definition_id,ordinal),
 FOREIGN KEY(result_series_id,revision_id,series_definition_id) REFERENCES lb.result_series(id,revision_id,series_definition_id) ON DELETE RESTRICT,
 FOREIGN KEY(component_definition_id,series_definition_id) REFERENCES lb.component_definition(id,series_definition_id) ON DELETE RESTRICT
);
CREATE TABLE lb.result_attribute (
 result_series_id uuid NOT NULL, revision_id uuid NOT NULL, key lb.key NOT NULL,
 value_type text NOT NULL CHECK (value_type IN ('integer','decimal','text','boolean')),
 integer_value bigint, decimal_value numeric, text_value text, boolean_value boolean,
 PRIMARY KEY(result_series_id,key),
 CHECK (num_nonnulls(integer_value,decimal_value,text_value,boolean_value) = 1),
 CHECK ((value_type = 'integer' AND integer_value IS NOT NULL) OR (value_type = 'decimal' AND decimal_value IS NOT NULL
   AND decimal_value NOT IN ('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric))
   OR (value_type = 'text' AND text_value IS NOT NULL) OR (value_type = 'boolean' AND boolean_value IS NOT NULL)),
 FOREIGN KEY(result_series_id,revision_id) REFERENCES lb.result_series(id,revision_id) ON DELETE RESTRICT
);
CREATE TABLE lb.prize_tier_result (
 id uuid PRIMARY KEY, revision_id uuid NOT NULL, rule_version_id uuid NOT NULL, lottery_id uuid NOT NULL,
 tier_definition_id uuid NOT NULL, scope_id uuid NOT NULL, variant_key lb.key NOT NULL DEFAULT 'base',
 winners_status lb.value_status NOT NULL, winners bigint CHECK (winners >= 0),
 CHECK ((winners_status = 'known' AND winners IS NOT NULL) OR (winners_status <> 'known' AND winners IS NULL)),
 UNIQUE(revision_id,tier_definition_id,scope_id,variant_key), UNIQUE(id,revision_id,scope_id),
 FOREIGN KEY(revision_id,rule_version_id,lottery_id) REFERENCES lb.draw_revision(id,rule_version_id,lottery_id) ON DELETE RESTRICT,
 FOREIGN KEY(tier_definition_id,rule_version_id) REFERENCES lb.prize_tier_definition(id,rule_version_id) ON DELETE RESTRICT,
 FOREIGN KEY(scope_id,lottery_id) REFERENCES lb.lottery_scope(id,lottery_id) ON DELETE RESTRICT
);
CREATE TABLE lb.monetary_fact (
 id uuid PRIMARY KEY, revision_id uuid NOT NULL, lottery_id uuid NOT NULL, rule_version_id uuid NOT NULL,
 tier_result_id uuid, scope_id uuid NOT NULL, kind lb.key NOT NULL,
 payout_form text NOT NULL CHECK (payout_form IN ('unspecified','cash','annuity','not_applicable')),
 status lb.value_status NOT NULL, amount numeric, currency lb.currency, source_text text,
 CHECK ((status = 'known' AND amount IS NOT NULL AND currency IS NOT NULL)
 OR (status <> 'known' AND amount IS NULL AND currency IS NULL)),
 CHECK (amount IS NULL OR (amount >= 0 AND amount <= 1000000000000000000
   AND amount NOT IN ('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric) AND scale(amount) <= 6)),
 UNIQUE NULLS NOT DISTINCT(revision_id,tier_result_id,scope_id,kind,payout_form,currency),
 FOREIGN KEY(revision_id,rule_version_id,lottery_id) REFERENCES lb.draw_revision(id,rule_version_id,lottery_id) ON DELETE RESTRICT,
 FOREIGN KEY(tier_result_id,revision_id,scope_id) REFERENCES lb.prize_tier_result(id,revision_id,scope_id) ON DELETE RESTRICT,
 FOREIGN KEY(scope_id,lottery_id) REFERENCES lb.lottery_scope(id,lottery_id) ON DELETE RESTRICT
);

-- Todo conteúdo carrega revision_id: o mesmo guard protege INSERT/UPDATE/DELETE,
-- inclusive trocas do pai. FOR UPDATE serializa edição concorrente com o selo.
CREATE FUNCTION lb.guard_content() RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog, lb AS $$
DECLARE rid uuid; state text;
BEGIN
 FOR rid IN SELECT DISTINCT v FROM unnest(ARRAY[
   CASE WHEN TG_OP <> 'INSERT' THEN (to_jsonb(OLD)->>'revision_id')::uuid END,
   CASE WHEN TG_OP <> 'DELETE' THEN (to_jsonb(NEW)->>'revision_id')::uuid END]) v WHERE v IS NOT NULL ORDER BY v
 LOOP
   SELECT seal_state INTO state FROM lb.draw_revision WHERE id = rid FOR UPDATE;
   IF state = 'sealed' THEN RAISE EXCEPTION 'sealed_revision_content' USING ERRCODE = '23514'; END IF;
 END LOOP;
 IF TG_OP = 'DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
END $$;
CREATE FUNCTION lb.guard_revision() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, lb AS $$
BEGIN
 IF TG_OP <> 'INSERT' AND OLD.seal_state = 'sealed' THEN
   RAISE EXCEPTION 'sealed_revision' USING ERRCODE = '23514';
 END IF;
 IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
 -- Não permitir redefinir uma revisão em construção para outro agregado.
 IF TG_OP = 'UPDATE' AND (NEW.id,NEW.draw_id,NEW.lottery_id,NEW.rule_version_id)
     IS DISTINCT FROM (OLD.id,OLD.draw_id,OLD.lottery_id,OLD.rule_version_id) THEN
   RAISE EXCEPTION 'revision_context_immutable' USING ERRCODE = '23514';
 END IF;
 PERFORM 1 FROM lb.rule_version WHERE id = NEW.rule_version_id FOR SHARE;
 RETURN NEW;
END $$;
CREATE TRIGGER revision_guard BEFORE INSERT OR UPDATE OR DELETE ON lb.draw_revision FOR EACH ROW EXECUTE FUNCTION lb.guard_revision();

CREATE FUNCTION lb.validate_revision(rid uuid) RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, lb AS $$
DECLARE r lb.draw_revision; rule lb.rule_version; s record; c record; n integer; known_order integer;
BEGIN
 SELECT * INTO r FROM lb.draw_revision WHERE id = rid;
 IF NOT FOUND THEN RETURN; END IF;
 SELECT * INTO rule FROM lb.rule_version WHERE id = r.rule_version_id FOR SHARE;
 IF r.seal_state <> 'sealed' OR rule.status <> 'validated'
   OR r.draw_date_local < rule.valid_from OR (rule.valid_to IS NOT NULL AND r.draw_date_local >= rule.valid_to)
   OR NOT EXISTS (SELECT FROM lb.candidate_observation o JOIN lb.processing_run p ON p.id = o.processing_run_id
      WHERE o.revision_id = rid AND o.draw_id = r.draw_id AND o.semantic_hash = r.content_hash
      AND p.canonicalization_version = r.canonicalization_version
      AND o.decision IN ('new','unchanged','correction_candidate','replayed')) THEN
   RAISE EXCEPTION 'incomplete_or_unsupported_revision' USING ERRCODE = '23514';
 END IF;
 FOR s IN SELECT sd.*, rs.id AS result_id FROM lb.series_definition sd
   LEFT JOIN lb.result_series rs ON rs.series_definition_id = sd.id AND rs.revision_id = rid
   WHERE sd.rule_version_id = r.rule_version_id
 LOOP
   IF s.required AND s.result_id IS NULL THEN RAISE EXCEPTION 'required_series_missing' USING ERRCODE = '23514'; END IF;
   IF s.result_id IS NULL THEN CONTINUE; END IF;
   FOR c IN SELECT * FROM lb.component_definition WHERE series_definition_id = s.id LOOP
     SELECT count(*),count(extraction_ordinal) INTO n,known_order FROM lb.component_value
       WHERE result_series_id = s.result_id AND component_definition_id = c.id;
     IF n < c.min_count OR n > c.max_count OR EXISTS (
       SELECT FROM lb.component_value v WHERE v.result_series_id = s.result_id AND v.component_definition_id = c.id
       AND (v.ordinal > n OR (c.value_type = 'integer' AND
         (v.integer_value IS NULL OR v.integer_value < c.min_value OR v.integer_value > c.max_value))
       OR (c.value_type = 'text' AND v.text_value IS NULL))
     ) THEN RAISE EXCEPTION 'invalid_component_count_or_bounds' USING ERRCODE = '23514'; END IF;
     IF c.unique_values AND EXISTS (SELECT FROM lb.component_value v
       WHERE v.result_series_id = s.result_id AND v.component_definition_id = c.id
       GROUP BY v.integer_value,v.text_value HAVING count(*) > 1) THEN
       RAISE EXCEPTION 'duplicate_component_value' USING ERRCODE = '23514'; END IF;
     IF known_order <> 0 AND (known_order <> n OR EXISTS (SELECT FROM lb.component_value v
       WHERE v.result_series_id = s.result_id AND v.component_definition_id = c.id
       AND v.extraction_ordinal > n) OR (SELECT count(DISTINCT extraction_ordinal) FROM lb.component_value
       WHERE result_series_id = s.result_id AND component_definition_id = c.id) <> n) THEN
       RAISE EXCEPTION 'invalid_extraction_order' USING ERRCODE = '23514'; END IF;
     IF c.order_semantics = 'sorted' AND EXISTS (SELECT FROM (
       SELECT integer_value,text_value,lag(integer_value) OVER (ORDER BY ordinal) pi,
         lag(text_value) OVER (ORDER BY ordinal) pt FROM lb.component_value
         WHERE result_series_id = s.result_id AND component_definition_id = c.id) q
       WHERE integer_value < pi OR text_value < pt) THEN
       RAISE EXCEPTION 'noncanonical_component_order' USING ERRCODE = '23514'; END IF;
   END LOOP;
 END LOOP;
END $$;
CREATE FUNCTION lb.check_revision() RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog, lb AS $$
BEGIN
 IF TG_TABLE_NAME = 'candidate_observation' THEN
   IF NEW.revision_id IS NOT NULL AND NOT EXISTS (
     SELECT FROM lb.draw_revision r JOIN lb.processing_run p ON p.id = NEW.processing_run_id
     WHERE r.id = NEW.revision_id AND r.content_hash = NEW.semantic_hash AND r.canonicalization_version = p.canonicalization_version
   ) THEN RAISE EXCEPTION 'observation_hash_or_version_mismatch' USING ERRCODE = '23514'; END IF;
 END IF;
 PERFORM lb.validate_revision(CASE WHEN TG_TABLE_NAME = 'draw_revision' THEN NEW.id
   ELSE (to_jsonb(NEW)->>'revision_id')::uuid END);
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER revision_complete AFTER INSERT OR UPDATE ON lb.draw_revision
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION lb.check_revision();
CREATE CONSTRAINT TRIGGER observation_support AFTER INSERT ON lb.candidate_observation
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION lb.check_revision();

-- Catálogo referenciado não pode ser reescrito sob resultados já selados.
-- Apenas fechar vigência, sem excluir resultados, é permitido em rule_version.
CREATE FUNCTION lb.guard_catalog() RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog, lb AS $$
DECLARE rid uuid; sid uuid;
BEGIN
 IF TG_TABLE_NAME = 'rule_version' THEN rid := OLD.id;
 ELSIF TG_TABLE_NAME IN ('series_definition','prize_tier_definition') THEN
   rid := CASE WHEN TG_OP = 'INSERT' THEN NEW.rule_version_id ELSE OLD.rule_version_id END;
 ELSE
   sid := CASE WHEN TG_OP = 'INSERT' THEN NEW.series_definition_id ELSE OLD.series_definition_id END;
   SELECT rule_version_id INTO rid FROM lb.series_definition WHERE id = sid;
 END IF;
 IF TG_OP = 'UPDATE' AND TG_TABLE_NAME <> 'rule_version' AND (
   (to_jsonb(NEW)->>'id') IS DISTINCT FROM (to_jsonb(OLD)->>'id') OR
   (to_jsonb(NEW)->>'rule_version_id') IS DISTINCT FROM (to_jsonb(OLD)->>'rule_version_id') OR
   (to_jsonb(NEW)->>'series_definition_id') IS DISTINCT FROM (to_jsonb(OLD)->>'series_definition_id')) THEN
   RAISE EXCEPTION 'catalog_context_immutable' USING ERRCODE = '23514';
 END IF;
 PERFORM 1 FROM lb.rule_version WHERE id = rid FOR UPDATE;
 IF EXISTS (SELECT FROM lb.draw_revision WHERE rule_version_id = rid) THEN
   IF TG_TABLE_NAME = 'rule_version' AND TG_OP = 'UPDATE' THEN
     IF (to_jsonb(NEW) - 'valid_to') IS DISTINCT FROM (to_jsonb(OLD) - 'valid_to') OR EXISTS (
       SELECT FROM lb.draw_revision WHERE rule_version_id = rid AND NEW.valid_to IS NOT NULL AND draw_date_local >= NEW.valid_to
     ) THEN RAISE EXCEPTION 'referenced_rule_immutable' USING ERRCODE = '23514'; END IF;
   ELSE RAISE EXCEPTION 'referenced_catalog_immutable' USING ERRCODE = '23514'; END IF;
 END IF;
 IF TG_OP = 'DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
END $$;
CREATE TRIGGER rule_guard BEFORE UPDATE OR DELETE ON lb.rule_version FOR EACH ROW EXECUTE FUNCTION lb.guard_catalog();
CREATE TRIGGER series_guard BEFORE INSERT OR UPDATE OR DELETE ON lb.series_definition FOR EACH ROW EXECUTE FUNCTION lb.guard_catalog();
CREATE TRIGGER component_guard BEFORE INSERT OR UPDATE OR DELETE ON lb.component_definition FOR EACH ROW EXECUTE FUNCTION lb.guard_catalog();
CREATE TRIGGER tier_guard BEFORE INSERT OR UPDATE OR DELETE ON lb.prize_tier_definition FOR EACH ROW EXECUTE FUNCTION lb.guard_catalog();

CREATE FUNCTION lb.check_component_catalog() RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog, lb AS $$
DECLARE sid uuid;
BEGIN
 sid := CASE WHEN TG_OP = 'DELETE' THEN OLD.series_definition_id ELSE NEW.series_definition_id END;
 IF EXISTS (SELECT FROM lb.series_definition s JOIN lb.rule_version r ON r.id = s.rule_version_id
   WHERE s.id = sid AND r.status = 'validated'
   AND NOT EXISTS (SELECT FROM lb.component_definition c WHERE c.series_definition_id = s.id)) THEN
   RAISE EXCEPTION 'series_without_components' USING ERRCODE = '23514'; END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER component_catalog AFTER INSERT OR UPDATE OR DELETE ON lb.component_definition
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION lb.check_component_catalog();

CREATE FUNCTION lb.append_only() RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog, lb AS $$
BEGIN RAISE EXCEPTION 'append_only_evidence' USING ERRCODE = '23514'; END $$;
CREATE FUNCTION lb.guard_evidence_context() RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog, lb AS $$
BEGIN
 IF (to_jsonb(NEW) - TG_ARGV) IS DISTINCT FROM (to_jsonb(OLD) - TG_ARGV) THEN
   RAISE EXCEPTION 'evidence_context_immutable' USING ERRCODE = '23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER run_context BEFORE UPDATE ON lb.ingestion_run FOR EACH ROW EXECUTE FUNCTION lb.guard_evidence_context('status','finished_at');
CREATE TRIGGER processing_context BEFORE UPDATE ON lb.processing_run FOR EACH ROW EXECUTE FUNCTION lb.guard_evidence_context('status','finished_at');
CREATE TRIGGER attempt_context BEFORE UPDATE ON lb.processing_attempt FOR EACH ROW EXECUTE FUNCTION lb.guard_evidence_context('outcome','finished_at','error_code');
CREATE TRIGGER fetch_context BEFORE UPDATE ON lb.fetch_attempt FOR EACH ROW EXECUTE FUNCTION lb.guard_evidence_context('outcome','finished_at','http_status','error_code');
CREATE TRIGGER alias_context BEFORE UPDATE ON lb.draw_identity FOR EACH ROW EXECUTE FUNCTION lb.guard_evidence_context('active');
CREATE TRIGGER alias_reserved BEFORE DELETE ON lb.draw_identity FOR EACH ROW EXECUTE FUNCTION lb.append_only();
CREATE FUNCTION lb.check_receipt() RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog, lb AS $$
BEGIN
 IF NEW.capture_kind = 'http' AND NOT EXISTS (SELECT FROM lb.fetch_attempt f WHERE f.id = NEW.fetch_attempt_id
   AND f.outcome = 'response' AND f.http_status = NEW.http_status) THEN
   RAISE EXCEPTION 'receipt_without_matching_response' USING ERRCODE = '23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER receipt_response BEFORE INSERT ON lb.capture_receipt FOR EACH ROW EXECUTE FUNCTION lb.check_receipt();
CREATE FUNCTION lb.guard_finished_fetch() RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog, lb AS $$
BEGIN
 IF OLD.outcome <> 'running' THEN RAISE EXCEPTION 'finished_fetch_immutable' USING ERRCODE = '23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER fetch_finished BEFORE UPDATE ON lb.fetch_attempt FOR EACH ROW EXECUTE FUNCTION lb.guard_finished_fetch();
DO $$ DECLARE tab text; BEGIN
 FOREACH tab IN ARRAY ARRAY['result_series','component_value','result_attribute','prize_tier_result','monetary_fact'] LOOP
   EXECUTE format('CREATE TRIGGER content_guard BEFORE INSERT OR UPDATE OR DELETE ON lb.%I FOR EACH ROW EXECUTE FUNCTION lb.guard_content()',tab);
 END LOOP;
 FOREACH tab IN ARRAY ARRAY['raw_artifact','capture_receipt','candidate_observation','validation_issue','external_draw_reference'] LOOP
   EXECUTE format('CREATE TRIGGER evidence_immutable BEFORE UPDATE OR DELETE ON lb.%I FOR EACH ROW EXECUTE FUNCTION lb.append_only()',tab);
 END LOOP;
END $$;

REVOKE ALL ON ALL FUNCTIONS IN SCHEMA lb FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA lb FROM PUBLIC;
