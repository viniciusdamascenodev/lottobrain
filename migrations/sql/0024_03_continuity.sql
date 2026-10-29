CREATE TABLE lb.ingestion_baseline (
 id uuid PRIMARY KEY, lottery_id uuid NOT NULL, source_id uuid NOT NULL,
 artifact_id uuid NOT NULL REFERENCES lb.raw_artifact ON DELETE RESTRICT,
 first_sequence bigint NOT NULL CHECK (first_sequence > 0), last_sequence bigint NOT NULL CHECK (last_sequence >= first_sequence),
 manifest_hash lb.sha256 NOT NULL, audit_reference text NOT NULL, audited_at timestamptz NOT NULL,
 materialization_status text NOT NULL CHECK (materialization_status IN ('referenced','loaded')),
 UNIQUE(id,source_id,lottery_id),
 FOREIGN KEY(source_id,lottery_id) REFERENCES lb.data_source(id,lottery_id) ON DELETE RESTRICT
);
CREATE TRIGGER baseline_immutable BEFORE UPDATE OR DELETE ON lb.ingestion_baseline FOR EACH ROW EXECUTE FUNCTION lb.append_only();
CREATE TABLE lb.sync_checkpoint (
 id uuid PRIMARY KEY, lottery_id uuid NOT NULL, source_id uuid NOT NULL, stream_key lb.key NOT NULL,
 strategy text NOT NULL CHECK (strategy = 'official_numeric_sequence'), baseline_id uuid NOT NULL,
 cursor_sequence bigint NOT NULL, review_next bigint NOT NULL CHECK (review_next > 0), cooldown_until timestamptz,
 row_version bigint NOT NULL DEFAULT 0 CHECK (row_version >= 0),
 lease_token bigint NOT NULL DEFAULT 0 CHECK (lease_token >= 0), lease_until timestamptz,
 CHECK (lease_until IS NULL OR lease_token > 0),
 UNIQUE(lottery_id,source_id,stream_key),
 FOREIGN KEY(baseline_id,source_id,lottery_id) REFERENCES lb.ingestion_baseline(id,source_id,lottery_id) ON DELETE RESTRICT
);
CREATE TABLE lb.sync_step (
 checkpoint_id uuid NOT NULL REFERENCES lb.sync_checkpoint ON DELETE RESTRICT,
 sequence_no bigint NOT NULL CHECK (sequence_no > 0),
 observation_id uuid NOT NULL REFERENCES lb.candidate_observation ON DELETE RESTRICT,
 lease_token bigint NOT NULL CHECK (lease_token > 0), completed_at timestamptz NOT NULL,
 PRIMARY KEY(checkpoint_id,sequence_no)
);
CREATE TRIGGER step_immutable BEFORE UPDATE OR DELETE ON lb.sync_step FOR EACH ROW EXECUTE FUNCTION lb.append_only();

CREATE FUNCTION lb.guard_checkpoint() RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog, lb AS $$
DECLARE anchor bigint;
BEGIN
 IF TG_OP = 'INSERT' THEN
   SELECT last_sequence INTO anchor FROM lb.ingestion_baseline WHERE id = NEW.baseline_id;
   IF NEW.cursor_sequence IS DISTINCT FROM anchor OR NEW.row_version <> 0 OR NEW.lease_token <> 0 OR NEW.lease_until IS NOT NULL THEN
     RAISE EXCEPTION 'checkpoint_must_start_at_baseline' USING ERRCODE = '23514'; END IF;
 ELSE
   IF (NEW.id,NEW.lottery_id,NEW.source_id,NEW.stream_key,NEW.strategy,NEW.baseline_id)
      IS DISTINCT FROM (OLD.id,OLD.lottery_id,OLD.source_id,OLD.stream_key,OLD.strategy,OLD.baseline_id)
      OR NEW.row_version <> OLD.row_version + 1 THEN
     RAISE EXCEPTION 'checkpoint_context_or_version' USING ERRCODE = '23514'; END IF;
   IF NEW.lease_token < OLD.lease_token OR NEW.lease_token > OLD.lease_token + 1 THEN
     RAISE EXCEPTION 'invalid_fencing_token' USING ERRCODE = '23514'; END IF;
   IF NEW.lease_token > OLD.lease_token AND (NEW.lease_until IS NULL OR NEW.lease_until <= clock_timestamp()) THEN
     RAISE EXCEPTION 'invalid_new_lease' USING ERRCODE = '23514'; END IF;
   IF NEW.lease_token = OLD.lease_token AND NEW.lease_until IS DISTINCT FROM OLD.lease_until
      AND (OLD.lease_until IS NULL OR OLD.lease_until <= clock_timestamp() OR NEW.lease_until IS NULL) THEN
     RAISE EXCEPTION 'lease_lost' USING ERRCODE = '23514'; END IF;
   IF NEW.cursor_sequence <> OLD.cursor_sequence THEN
     IF NEW.cursor_sequence <> OLD.cursor_sequence + 1 OR NEW.lease_token <> OLD.lease_token
       OR OLD.lease_until IS NULL OR OLD.lease_until <= clock_timestamp()
       OR NEW.lease_until IS DISTINCT FROM OLD.lease_until THEN
       RAISE EXCEPTION 'noncontiguous_or_unleased_cursor' USING ERRCODE = '23514'; END IF;
   END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER checkpoint_guard BEFORE INSERT OR UPDATE ON lb.sync_checkpoint FOR EACH ROW EXECUTE FUNCTION lb.guard_checkpoint();

CREATE FUNCTION lb.check_step() RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog, lb AS $$
DECLARE cp lb.sync_checkpoint; o lb.candidate_observation; receipt_source uuid;
BEGIN
 SELECT * INTO cp FROM lb.sync_checkpoint WHERE id = NEW.checkpoint_id FOR UPDATE;
 SELECT * INTO o FROM lb.candidate_observation WHERE id = NEW.observation_id;
 SELECT c.source_id INTO receipt_source FROM lb.processing_run p JOIN lb.capture_receipt c ON c.id = p.receipt_id
   WHERE p.id = o.processing_run_id;
 IF cp.lease_token <> NEW.lease_token OR cp.lease_until IS NULL OR cp.lease_until <= clock_timestamp()
   OR NEW.sequence_no <> cp.cursor_sequence + 1 OR cp.lottery_id IS DISTINCT FROM o.lottery_id
   OR receipt_source IS DISTINCT FROM cp.source_id
   OR o.decision NOT IN ('new','unchanged','correction_candidate','replayed')
   OR NOT EXISTS (SELECT FROM lb.draw_identity i WHERE i.draw_id = o.draw_id AND i.active
      AND i.assurance = 'official' AND i.namespace = 'official_draw_number' AND i.value = NEW.sequence_no::text)
 THEN RAISE EXCEPTION 'invalid_sync_step_or_lease_lost' USING ERRCODE = '23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER step_guard BEFORE INSERT ON lb.sync_step FOR EACH ROW EXECUTE FUNCTION lb.check_step();

CREATE FUNCTION lb.verify_checkpoint() RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog, lb AS $$
DECLARE cp lb.sync_checkpoint; anchor bigint; expected_step bigint;
BEGIN
 SELECT * INTO cp FROM lb.sync_checkpoint WHERE id = COALESCE((to_jsonb(NEW)->>'checkpoint_id')::uuid,(to_jsonb(NEW)->>'id')::uuid);
 SELECT last_sequence INTO anchor FROM lb.ingestion_baseline WHERE id = cp.baseline_id;
 expected_step := CASE WHEN TG_TABLE_NAME = 'sync_step' THEN (to_jsonb(NEW)->>'sequence_no')::bigint ELSE cp.cursor_sequence END;
 IF cp.cursor_sequence < anchor OR (TG_TABLE_NAME = 'sync_step' AND expected_step > cp.cursor_sequence)
 OR cp.cursor_sequence - anchor <> (SELECT count(*) FROM lb.sync_step WHERE checkpoint_id = cp.id AND sequence_no > anchor AND sequence_no <= cp.cursor_sequence)
 THEN RAISE EXCEPTION 'checkpoint_without_contiguous_evidence' USING ERRCODE = '23514'; END IF;
 IF TG_TABLE_NAME = 'sync_step' AND (cp.lease_token <> NEW.lease_token OR cp.lease_until IS NULL OR cp.lease_until <= clock_timestamp()) THEN
   RAISE EXCEPTION 'lease_lost_at_commit' USING ERRCODE = '23514'; END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER checkpoint_complete AFTER INSERT OR UPDATE ON lb.sync_checkpoint
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION lb.verify_checkpoint();
CREATE CONSTRAINT TRIGGER step_complete AFTER INSERT ON lb.sync_step
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION lb.verify_checkpoint();
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA lb FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA lb FROM PUBLIC;
