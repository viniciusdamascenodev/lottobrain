-- Executar explicitamente pelo provisionador, no banco correto; não são logins.
-- Associar logins/segredos via infraestrutura, fora do repositório.
DO $$ BEGIN
 IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'lottobrain_ingest') THEN
   CREATE ROLE lottobrain_ingest NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
 END IF;
 IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'lottobrain_audit') THEN
   CREATE ROLE lottobrain_audit NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
 END IF;
 IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'lottobrain_bootstrap') THEN
   CREATE ROLE lottobrain_bootstrap NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
 END IF;
END $$;
GRANT USAGE ON SCHEMA lb TO lottobrain_ingest,lottobrain_audit;
GRANT SELECT ON ALL TABLES IN SCHEMA lb TO lottobrain_ingest,lottobrain_audit;
GRANT USAGE ON SCHEMA lb TO lottobrain_bootstrap;
GRANT SELECT ON ALL TABLES IN SCHEMA lb TO lottobrain_bootstrap;
GRANT INSERT ON lb.ingestion_baseline,lb.baseline_activation,lb.sync_checkpoint TO lottobrain_bootstrap;
GRANT INSERT ON lb.ingestion_run,lb.fetch_attempt,lb.raw_artifact,lb.capture_receipt,
 lb.processing_run,lb.processing_attempt,lb.draw,lb.draw_revision,lb.candidate_observation,
 lb.validation_issue,lb.draw_identity,lb.external_draw_reference,lb.result_series,
 lb.component_value,lb.result_attribute,lb.prize_tier_result,lb.monetary_fact,lb.sync_step TO lottobrain_ingest;
GRANT INSERT ON lb.sync_batch,lb.sync_batch_operation TO lottobrain_ingest;
GRANT UPDATE(lease_token,latest_sequence,status,finished_at,stop_reason,report) ON lb.sync_batch TO lottobrain_ingest;
GRANT UPDATE(receipt_id,processing_key,lease_token,state,observation_id,outcome,observed_sequence,completed_at)
 ON lb.sync_batch_operation TO lottobrain_ingest;
GRANT UPDATE(status,finished_at) ON lb.ingestion_run,lb.processing_run TO lottobrain_ingest;
GRANT UPDATE(outcome,finished_at,http_status,error_code) ON lb.fetch_attempt TO lottobrain_ingest;
GRANT UPDATE(outcome,finished_at,error_code) ON lb.processing_attempt TO lottobrain_ingest;
GRANT UPDATE(latest_candidate_revision_id,row_version) ON lb.draw TO lottobrain_ingest;
GRANT UPDATE(seal_state,sealed_at) ON lb.draw_revision TO lottobrain_ingest;
GRANT UPDATE(cursor_sequence,review_next,cooldown_until,row_version,lease_token,lease_until) ON lb.sync_checkpoint TO lottobrain_ingest;
-- Funções invoker: precisam apenas das mesmas leituras/locks permitidos ao papel.
GRANT EXECUTE ON FUNCTION lb.validate_revision(uuid) TO lottobrain_ingest;
-- Sem DELETE, TRUNCATE, DDL, alteração de catálogo/baseline ou publicação.
