DO $$ BEGIN
 IF EXISTS (SELECT FROM lb.baseline_activation) OR EXISTS (
   SELECT FROM lb.sync_checkpoint cp JOIN lb.ingestion_baseline b ON b.id=cp.baseline_id WHERE cp.source_id<>b.source_id)
 THEN RAISE EXCEPTION 'Rollback bloqueado: ativação de baseline preenchida'; END IF;
END $$;
DROP TRIGGER checkpoint_handoff ON lb.sync_checkpoint;
DROP FUNCTION lb.check_checkpoint_handoff();
DROP TABLE lb.baseline_activation;
ALTER TABLE lb.sync_checkpoint DROP CONSTRAINT checkpoint_activation_identity;
DROP FUNCTION lb.check_baseline_activation();
ALTER TABLE lb.sync_checkpoint DROP CONSTRAINT checkpoint_baseline_lottery_fk;
ALTER TABLE lb.sync_checkpoint DROP CONSTRAINT checkpoint_source_lottery_fk;
ALTER TABLE lb.sync_checkpoint ADD CONSTRAINT sync_checkpoint_baseline_id_source_id_lottery_id_fkey
 FOREIGN KEY(baseline_id,source_id,lottery_id) REFERENCES lb.ingestion_baseline(id,source_id,lottery_id) ON DELETE RESTRICT;
ALTER TABLE lb.ingestion_baseline DROP CONSTRAINT baseline_lottery_identity;
