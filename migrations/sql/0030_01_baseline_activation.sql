-- A origem continua no XLSX; somente um vínculo auditado autoriza o checkpoint JSON.
ALTER TABLE lb.ingestion_baseline ADD CONSTRAINT baseline_lottery_identity UNIQUE(id,lottery_id);
ALTER TABLE lb.sync_checkpoint ADD CONSTRAINT checkpoint_activation_identity UNIQUE(id,baseline_id,source_id,lottery_id,stream_key);
CREATE TABLE lb.baseline_activation (
 id uuid PRIMARY KEY, baseline_id uuid NOT NULL UNIQUE, lottery_id uuid NOT NULL,
 historical_source_id uuid NOT NULL, historical_run_id uuid NOT NULL, historical_receipt_id uuid NOT NULL,
 target_source_id uuid NOT NULL, checkpoint_id uuid NOT NULL UNIQUE,
 stream_key lb.key NOT NULL CHECK (stream_key='mega_sena_forward'),
 command_key text NOT NULL UNIQUE, request_hash lb.sha256 NOT NULL, historical_plan_hash lb.sha256 NOT NULL,
 policy_version text NOT NULL CHECK (policy_version='mega-sena-baseline-activation-v1'),
 target_catalog_fingerprint lb.sha256 NOT NULL, target_config_snapshot jsonb NOT NULL
   CHECK (jsonb_typeof(target_config_snapshot)='object' AND pg_column_size(target_config_snapshot)<=16384),
 coverage_hash lb.sha256 NOT NULL, coverage_report jsonb NOT NULL CHECK (
   jsonb_typeof(coverage_report)='object' AND pg_column_size(coverage_report)<=32768
   AND coverage_report @> '{"report_version":"mega-sena-historical-coverage-v1","qualified":true,"run_status":"completed","expected_records":2954,"verified_records":2954,"missing":[],"duplicates":[],"unexpected":[],"problems":[],"quarantined_records":0,"unexpected_commands":[]}'::jsonb
   AND coverage_report->'missing'='[]'::jsonb AND coverage_report->'duplicates'='[]'::jsonb
   AND coverage_report->'unexpected'='[]'::jsonb AND coverage_report->'problems'='[]'::jsonb
   AND coverage_report->'unexpected_commands'='[]'::jsonb),
 approval_reference text NOT NULL CHECK (length(btrim(approval_reference)) BETWEEN 1 AND 512),
 approved_by text NOT NULL, approved_at timestamptz NOT NULL,
 UNIQUE(lottery_id,target_source_id),
 FOREIGN KEY(baseline_id,historical_source_id,lottery_id) REFERENCES lb.ingestion_baseline(id,source_id,lottery_id) ON DELETE RESTRICT,
 FOREIGN KEY(historical_run_id,historical_source_id,lottery_id) REFERENCES lb.ingestion_run(id,source_id,lottery_id) ON DELETE RESTRICT,
 FOREIGN KEY(historical_receipt_id,historical_source_id,lottery_id) REFERENCES lb.capture_receipt(id,source_id,lottery_id) ON DELETE RESTRICT,
 FOREIGN KEY(target_source_id,lottery_id) REFERENCES lb.data_source(id,lottery_id) ON DELETE RESTRICT,
 FOREIGN KEY(checkpoint_id,baseline_id,target_source_id,lottery_id,stream_key)
   REFERENCES lb.sync_checkpoint(id,baseline_id,source_id,lottery_id,stream_key) DEFERRABLE INITIALLY DEFERRED,
 CHECK (historical_source_id<>target_source_id)
);
CREATE TRIGGER baseline_activation_immutable BEFORE UPDATE OR DELETE ON lb.baseline_activation
 FOR EACH ROW EXECUTE FUNCTION lb.append_only();

CREATE FUNCTION lb.check_baseline_activation() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,lb AS $$
DECLARE b lb.ingestion_baseline; r lb.ingestion_run; c lb.capture_receipt; a lb.raw_artifact;
BEGIN
 SELECT * INTO b FROM lb.ingestion_baseline WHERE id=NEW.baseline_id;
 SELECT * INTO r FROM lb.ingestion_run WHERE id=NEW.historical_run_id;
 SELECT * INTO c FROM lb.capture_receipt WHERE id=NEW.historical_receipt_id;
 SELECT * INTO a FROM lb.raw_artifact WHERE id=b.artifact_id;
 IF NOT COALESCE(NEW.approved_by=current_user AND b.materialization_status='loaded' AND b.first_sequence=1 AND b.last_sequence=2954
   AND r.mode='historical_import' AND r.status='completed' AND c.capture_kind='legacy_import'
   AND c.artifact_id=b.artifact_id AND a.storage_state='available'
   AND c.legacy_reference::jsonb->>'run_id'=r.id::text
   AND c.legacy_reference::jsonb->'manifest'->>'raw_sha256'=a.sha256
   AND NEW.coverage_report->>'raw_sha256'=a.sha256
   AND NEW.coverage_report->>'plan_hash'=NEW.historical_plan_hash
   AND NEW.coverage_report->>'expected_records_manifest_sha256'=b.manifest_hash
   AND NEW.coverage_report->>'observed_records_manifest_sha256'=b.manifest_hash
   AND b.audit_reference='urn:lottobrain:baseline-activation:'||NEW.id::text
   AND EXISTS (SELECT FROM lb.lottery l JOIN lb.data_source s ON s.lottery_id=l.id
      WHERE l.id=NEW.lottery_id AND l.slug='mega_sena' AND s.id=NEW.historical_source_id AND s.key='caixa_mega_sena_xlsx')
   AND EXISTS (SELECT FROM lb.data_source s WHERE s.id=NEW.target_source_id AND s.key='caixa_mega_sena_json'
      AND s.authority='official' AND s.readiness IN ('contract_observed','approved')
      AND NEW.target_config_snapshot=jsonb_build_object('schema_version',1,'authority',s.authority,
          'readiness',s.readiness,'base_url',s.base_url,'policy_reference',s.policy_reference,'configuration_origin','captured')),false)
 THEN RAISE EXCEPTION 'invalid_baseline_activation' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER baseline_activation_guard BEFORE INSERT ON lb.baseline_activation
 FOR EACH ROW EXECUTE FUNCTION lb.check_baseline_activation();

ALTER TABLE lb.sync_checkpoint DROP CONSTRAINT sync_checkpoint_baseline_id_source_id_lottery_id_fkey;
ALTER TABLE lb.sync_checkpoint ADD CONSTRAINT checkpoint_baseline_lottery_fk
 FOREIGN KEY(baseline_id,lottery_id) REFERENCES lb.ingestion_baseline(id,lottery_id) ON DELETE RESTRICT;
ALTER TABLE lb.sync_checkpoint ADD CONSTRAINT checkpoint_source_lottery_fk
 FOREIGN KEY(source_id,lottery_id) REFERENCES lb.data_source(id,lottery_id) ON DELETE RESTRICT;
CREATE FUNCTION lb.check_checkpoint_handoff() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,lb AS $$
DECLARE origin uuid;
BEGIN
 SELECT source_id INTO origin FROM lb.ingestion_baseline WHERE id=NEW.baseline_id;
 IF origin IS DISTINCT FROM NEW.source_id AND NOT EXISTS (
   SELECT FROM lb.baseline_activation h WHERE h.baseline_id=NEW.baseline_id AND h.lottery_id=NEW.lottery_id
     AND h.target_source_id=NEW.source_id AND h.stream_key=NEW.stream_key AND h.checkpoint_id=NEW.id)
 THEN RAISE EXCEPTION 'checkpoint_requires_audited_handoff' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER checkpoint_handoff BEFORE INSERT ON lb.sync_checkpoint
 FOR EACH ROW EXECUTE FUNCTION lb.check_checkpoint_handoff();
REVOKE ALL ON lb.baseline_activation FROM PUBLIC;
REVOKE ALL ON FUNCTION lb.check_baseline_activation(),lb.check_checkpoint_handoff() FROM PUBLIC;
