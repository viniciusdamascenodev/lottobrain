CREATE TABLE lb.sync_batch (
 id uuid PRIMARY KEY, checkpoint_id uuid NOT NULL REFERENCES lb.sync_checkpoint ON DELETE RESTRICT,
 command_key text NOT NULL UNIQUE, request_hash lb.sha256 NOT NULL, catalog_fingerprint lb.sha256 NOT NULL,
 policy jsonb NOT NULL CHECK (jsonb_typeof(policy)='object' AND pg_column_size(policy)<=1024
   AND policy ?& ARRAY['max_requests','review_window','interval_seconds']
   AND (policy->>'max_requests')::int BETWEEN 1 AND 10
   AND (policy->>'review_window')::int BETWEEN 0 AND 20
   AND (policy->>'interval_seconds')::numeric BETWEEN 2 AND 30),
 cursor_start bigint NOT NULL, review_start bigint NOT NULL, review_targets jsonb NOT NULL
   CHECK (jsonb_typeof(review_targets)='array' AND jsonb_array_length(review_targets)<=20),
 latest_sequence bigint, lease_token bigint NOT NULL CHECK (lease_token>0),
 status text NOT NULL CHECK (status IN ('running','completed','stopped')),
 started_at timestamptz NOT NULL, finished_at timestamptz, stop_reason text,
 report jsonb CHECK (pg_column_size(report)<=32768),
 CHECK (finished_at IS NULL OR finished_at>=started_at),
 CHECK ((status='running' AND report IS NULL AND finished_at IS NULL AND stop_reason IS NULL)
   OR (status<>'running' AND report IS NOT NULL AND finished_at IS NOT NULL AND stop_reason IS NOT NULL))
);
CREATE UNIQUE INDEX one_running_sync_batch ON lb.sync_batch(checkpoint_id) WHERE status='running';
CREATE TABLE lb.sync_batch_operation (
 id uuid PRIMARY KEY, batch_id uuid NOT NULL REFERENCES lb.sync_batch ON DELETE RESTRICT,
 ordinal integer NOT NULL CHECK (ordinal BETWEEN 1 AND 22),
 phase text NOT NULL CHECK (phase IN ('discovery','forward','review')), contest bigint CHECK (contest>0),
 expected_cursor bigint NOT NULL, review_after bigint, reuse_id uuid,
 capture_key text UNIQUE, receipt_id uuid REFERENCES lb.capture_receipt ON DELETE RESTRICT,
 processing_key text UNIQUE, lease_token bigint, state text NOT NULL CHECK (state IN ('pending','done')),
 observation_id uuid REFERENCES lb.candidate_observation ON DELETE RESTRICT,
 outcome text, observed_sequence bigint, created_at timestamptz NOT NULL, completed_at timestamptz,
 UNIQUE(id,batch_id), UNIQUE(batch_id,ordinal), UNIQUE NULLS NOT DISTINCT(batch_id,phase,contest),
 FOREIGN KEY(reuse_id,batch_id) REFERENCES lb.sync_batch_operation(id,batch_id) ON DELETE RESTRICT,
 CHECK ((phase='discovery' AND contest IS NULL) OR (phase<>'discovery' AND contest IS NOT NULL)),
 CHECK ((phase='review')=(review_after IS NOT NULL)),
 CHECK ((reuse_id IS NULL)=(capture_key IS NOT NULL)),
 CHECK ((state='pending' AND observation_id IS NULL AND outcome IS NULL AND completed_at IS NULL)
   OR (state='done' AND observation_id IS NOT NULL AND receipt_id IS NOT NULL AND processing_key IS NOT NULL
       AND lease_token>0 AND completed_at IS NOT NULL AND outcome IN ('new','unchanged','correction_candidate','replayed','quarantined')))
);
CREATE FUNCTION lb.guard_sync_batch() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,lb AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'append_only_batch' USING ERRCODE='23514'; END IF;
 IF TG_OP='INSERT' THEN
   IF NOT EXISTS (SELECT FROM lb.sync_checkpoint cp JOIN lb.baseline_activation a ON a.checkpoint_id=cp.id
       JOIN lb.ingestion_baseline b ON b.id=cp.baseline_id WHERE cp.id=NEW.checkpoint_id AND b.materialization_status='loaded'
       AND cp.lease_token=NEW.lease_token AND cp.lease_until>clock_timestamp())
   THEN RAISE EXCEPTION 'batch_requires_approved_baseline_and_lease' USING ERRCODE='23514'; END IF;
 ELSE
   IF OLD.status<>'running' OR (to_jsonb(NEW)-ARRAY['lease_token','latest_sequence','status','finished_at','stop_reason','report'])
       IS DISTINCT FROM (to_jsonb(OLD)-ARRAY['lease_token','latest_sequence','status','finished_at','stop_reason','report'])
       OR (OLD.latest_sequence IS NOT NULL AND NEW.latest_sequence IS DISTINCT FROM OLD.latest_sequence)
   THEN RAISE EXCEPTION 'immutable_batch_context' USING ERRCODE='23514'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sync_batch_guard BEFORE INSERT OR UPDATE OR DELETE ON lb.sync_batch FOR EACH ROW EXECUTE FUNCTION lb.guard_sync_batch();
CREATE FUNCTION lb.guard_sync_operation() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,lb AS $$
DECLARE b lb.sync_batch;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'append_only_operation' USING ERRCODE='23514'; END IF;
 SELECT * INTO b FROM lb.sync_batch WHERE id=NEW.batch_id FOR UPDATE;
 IF b.status IS DISTINCT FROM 'running' THEN RAISE EXCEPTION 'batch_not_running' USING ERRCODE='23514'; END IF;
 IF TG_OP='INSERT' THEN
   IF NEW.ordinal<>(SELECT count(*)+1 FROM lb.sync_batch_operation WHERE batch_id=b.id)
     OR (NEW.reuse_id IS NULL AND (SELECT count(*) FROM lb.sync_batch_operation WHERE batch_id=b.id AND reuse_id IS NULL)>=(b.policy->>'max_requests')::int)
     OR (NEW.reuse_id IS NOT NULL AND NOT EXISTS (SELECT FROM lb.sync_batch_operation o WHERE o.id=NEW.reuse_id
          AND o.batch_id=b.id AND o.phase='discovery' AND o.state='done' AND o.observed_sequence=NEW.contest))
   THEN RAISE EXCEPTION 'invalid_operation_or_budget' USING ERRCODE='23514'; END IF;
 ELSE
   IF OLD.state='done' OR (OLD.receipt_id IS NOT NULL AND NEW.receipt_id IS DISTINCT FROM OLD.receipt_id)
     OR (to_jsonb(NEW)-ARRAY['receipt_id','processing_key','lease_token','state','observation_id','outcome','observed_sequence','completed_at'])
       IS DISTINCT FROM (to_jsonb(OLD)-ARRAY['receipt_id','processing_key','lease_token','state','observation_id','outcome','observed_sequence','completed_at'])
   THEN RAISE EXCEPTION 'immutable_operation_context' USING ERRCODE='23514'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sync_operation_guard BEFORE INSERT OR UPDATE OR DELETE ON lb.sync_batch_operation
 FOR EACH ROW EXECUTE FUNCTION lb.guard_sync_operation();
CREATE FUNCTION lb.verify_sync_operation() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,lb AS $$
DECLARE cp lb.sync_checkpoint; b lb.sync_batch; o lb.candidate_observation; source uuid; accepted boolean;
BEGIN
 IF NEW.state<>'done' THEN RETURN NULL; END IF;
 SELECT * INTO b FROM lb.sync_batch WHERE id=NEW.batch_id;
 SELECT * INTO cp FROM lb.sync_checkpoint WHERE id=b.checkpoint_id;
 SELECT * INTO o FROM lb.candidate_observation WHERE id=NEW.observation_id;
 SELECT c.source_id INTO source FROM lb.processing_run p JOIN lb.capture_receipt c ON c.id=p.receipt_id
    WHERE p.id=o.processing_run_id AND c.id=NEW.receipt_id;
 accepted:=o.revision_id IS NOT NULL AND NEW.outcome<>'quarantined';
 IF NOT COALESCE(b.status='running' AND cp.lease_token=NEW.lease_token AND b.lease_token=NEW.lease_token
   AND cp.lease_until>clock_timestamp() AND source=cp.source_id AND o.lottery_id=cp.lottery_id
   AND cp.cursor_sequence=NEW.expected_cursor+CASE WHEN accepted AND NEW.phase='forward' THEN 1 ELSE 0 END
   AND EXISTS (SELECT FROM lb.processing_attempt a WHERE a.command_key=NEW.processing_key
       AND a.processing_run_id=o.processing_run_id AND a.outcome=NEW.outcome)
   AND (NOT accepted OR EXISTS (SELECT FROM lb.draw_identity i WHERE i.draw_id=o.draw_id AND i.active
       AND i.namespace='official_draw_number' AND i.assurance='official' AND i.value=NEW.observed_sequence::text))
   AND (NOT accepted OR NEW.phase='discovery' OR NEW.contest=NEW.observed_sequence)
   AND (NOT accepted OR NEW.phase<>'forward' OR EXISTS (SELECT FROM lb.sync_step s WHERE s.checkpoint_id=cp.id
       AND s.sequence_no=NEW.contest AND s.observation_id=o.id AND s.lease_token=NEW.lease_token))
   AND (NOT accepted OR NEW.phase<>'review' OR cp.review_next=NEW.review_after),false)
 THEN RAISE EXCEPTION 'invalid_batch_operation_or_lease_lost' USING ERRCODE='23514'; END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER sync_operation_complete AFTER INSERT OR UPDATE ON lb.sync_batch_operation
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION lb.verify_sync_operation();
REVOKE ALL ON lb.sync_batch,lb.sync_batch_operation FROM PUBLIC;
REVOKE ALL ON FUNCTION lb.guard_sync_batch(),lb.guard_sync_operation(),lb.verify_sync_operation() FROM PUBLIC;
