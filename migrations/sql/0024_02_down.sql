DO $$ DECLARE tab text; populated boolean; BEGIN
 FOREACH tab IN ARRAY ARRAY['ingestion_run','fetch_attempt','raw_artifact','capture_receipt','processing_run',
 'processing_attempt','draw','draw_revision','candidate_observation','validation_issue','draw_identity',
 'external_draw_reference','result_series','component_value','result_attribute','prize_tier_result','monetary_fact'] LOOP
   EXECUTE format('SELECT EXISTS (SELECT FROM lb.%I)',tab) INTO populated;
   IF populated THEN RAISE EXCEPTION 'Rollback bloqueado: evidência em %; recuperar forward/backup',tab; END IF;
 END LOOP;
END $$;
DROP TRIGGER rule_guard ON lb.rule_version;
DROP TRIGGER series_guard ON lb.series_definition;
DROP TRIGGER component_guard ON lb.component_definition;
DROP TRIGGER tier_guard ON lb.prize_tier_definition;
DROP TRIGGER component_catalog ON lb.component_definition;
DROP TABLE lb.ingestion_run,lb.fetch_attempt,lb.raw_artifact,lb.capture_receipt,lb.processing_run,
 lb.processing_attempt,lb.draw,lb.draw_revision,lb.candidate_observation,lb.validation_issue,lb.draw_identity,
 lb.external_draw_reference,lb.result_series,lb.component_value,lb.result_attribute,lb.prize_tier_result,lb.monetary_fact;
DROP FUNCTION lb.guard_content(),lb.guard_revision(),lb.validate_revision(uuid),lb.check_revision(),
 lb.guard_catalog(),lb.check_component_catalog(),lb.append_only(),lb.guard_evidence_context(),lb.check_receipt(),lb.guard_finished_fetch();
