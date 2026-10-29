"""Carga completa controlada e auditoria snapshot; não promove baselines."""
import json

from app.application.historical_coverage import coverage_report
from app.application.historical_content import digest
from app.application.historical_import import CODE_VERSION, HistoricalImportPlan, XLSX_SOURCE
from app.application.persistence import PersistenceError
from app.infrastructure.postgres.content_reader import read_contents
from app.infrastructure.postgres.historical_pilot import PgHistoricalPilotRepository, _row_key


class PgHistoricalImportRepository(PgHistoricalPilotRepository):
    run_mode = "historical_import"
    code_version = CODE_VERSION
    receipt_schema = "historical-import-receipt-v1"
    observation_schema = "historical-import-observation-v1"
    command_namespace = "historical-plan"
    row_namespace = "historical-row"
    row_event = "after_historical_row"

    def register(self, plan, key, object_key):
        if not isinstance(plan,HistoricalImportPlan) or plan.source_key != XLSX_SOURCE:
            raise PersistenceError("historical_input_not_qualified")
        return super().register(plan,key,object_key)

    def pending(self, registration, plan):
        completed = self.db.execute("""SELECT a.command_key FROM lb.processing_attempt a
            JOIN lb.processing_run p ON p.id=a.processing_run_id WHERE p.receipt_id=%s""",
            (registration["receipt_id"],)).fetchall()
        keys = {item["command_key"] for item in completed}
        return tuple(row for row in plan.rows if _row_key(registration["run_id"],row,self.row_namespace) not in keys)

    def _registration(self, key, plan):
        saved = self.describe(XLSX_SOURCE,key)
        if saved["manifest"] != plan.manifest:
            raise PersistenceError("historical_manifest_mismatch")
        return {key:saved[key] for key in ("run_id","receipt_id","request_hash","catalog_fingerprint")},saved["status"]

    def describe(self, source_key, key):
        # Ler evidência encerrada não reautoriza a fonte. Escritas continuam
        # passando por register/process e pela qualificação do catálogo atual.
        if source_key != XLSX_SOURCE:
            raise PersistenceError("historical_input_not_qualified")
        run = self.db.execute("""SELECT run.id,run.source_id,run.request_hash,run.status
            FROM lb.ingestion_run run JOIN lb.data_source s ON s.id=run.source_id
            JOIN lb.lottery l ON l.id=run.lottery_id
            WHERE s.key=%s AND l.slug='mega_sena' AND run.idempotency_key=%s AND run.mode=%s""",
            (source_key,key,self.run_mode)).fetchone()
        if not run:
            raise PersistenceError("historical_plan_not_found")
        receipts = self.db.execute("""SELECT c.id,c.legacy_reference,a.object_key,a.sha256,a.byte_count
            FROM lb.capture_receipt c JOIN lb.raw_artifact a ON a.id=c.artifact_id
            WHERE c.source_id=%s AND c.capture_kind='legacy_import' AND c.legacy_reference LIKE %s""",
            (run["source_id"],f'%"run_id":"{run["id"]}"%')).fetchall()
        if len(receipts) != 1:
            raise PersistenceError("historical_manifest_mismatch")
        receipt = receipts[0]
        try:
            reference = json.loads(receipt["legacy_reference"])
            manifest, fingerprint = reference["manifest"],reference["catalog_fingerprint"]
            if (reference["schema_version"] != self.receipt_schema or reference["run_id"] != str(run["id"])
                    or manifest["source_key"] != source_key or manifest["raw_sha256"] != receipt["sha256"]
                    or manifest["byte_count"] != receipt["byte_count"]
                    or run["request_hash"] != digest({"plan":digest(manifest),"catalog":fingerprint})):
                raise ValueError("receipt/run incompatíveis")
        except (KeyError,TypeError,ValueError):
            raise PersistenceError("historical_manifest_mismatch") from None
        return {"manifest":manifest,"catalog_fingerprint":fingerprint,"run_id":run["id"],
                "receipt_id":receipt["id"],"request_hash":run["request_hash"],"status":run["status"],
                "object_key":receipt["object_key"],"sha256":receipt["sha256"],"byte_count":receipt["byte_count"]}

    def _coverage(self, registration, plan, status):
        observations = self.db.execute("""SELECT o.*,p.code_version,p.adapter_version,p.catalog_fingerprint,
            p.validation_policy_version,p.canonicalization_version,r.seal_state,
            d.latest_candidate_revision_id,d.published_revision_id FROM lb.candidate_observation o
            JOIN lb.processing_run p ON p.id=o.processing_run_id
            LEFT JOIN lb.draw_revision r ON r.id=o.revision_id LEFT JOIN lb.draw d ON d.id=o.draw_id
            WHERE p.receipt_id=%s ORDER BY o.row_locator""",(registration["receipt_id"],)).fetchall()
        attempts = self.db.execute("""SELECT a.command_key,a.processing_run_id,a.request_hash,a.outcome
            FROM lb.processing_attempt a JOIN lb.processing_run p ON p.id=a.processing_run_id
            WHERE p.receipt_id=%s""",(registration["receipt_id"],)).fetchall()
        draws = list({o["draw_id"] for o in observations if o["draw_id"] is not None})
        aliases = self.db.execute("SELECT draw_id,namespace,value,active,assurance FROM lb.draw_identity WHERE draw_id=ANY(%s)",(draws,)).fetchall() if draws else []
        ids = {o[k] for o in observations for k in ("revision_id","latest_candidate_revision_id") if o[k] is not None}
        contents = read_contents(self.db,ids)
        continuity = {table:self.db.execute(f"SELECT count(*) AS n FROM lb.{table}").fetchone()["n"]
                      for table in ("ingestion_baseline","sync_checkpoint","sync_step")}
        return coverage_report(plan,registration,status,observations,attempts,aliases,contents,continuity)

    def audit(self, key, plan):
        # Primeiro comando de dados desta UoW: snapshot consistente e sem escrita.
        self.db.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        return self.coverage_snapshot(key,plan)[1]

    def coverage_snapshot(self, key, plan):
        """Chamador abre snapshot consistente; também usado na ativação atômica."""
        registration,status = self._registration(key,plan)
        return registration,self._coverage(registration,plan,status)

    def finish(self, registration, plan):
        self.db.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        run = self.db.execute("SELECT status FROM lb.ingestion_run WHERE id=%s FOR UPDATE",(registration["run_id"],)).fetchone()
        if not run:
            raise PersistenceError("historical_plan_not_found")
        report = self._coverage(registration,plan,run["status"])
        if run["status"] == "running":
            status = "completed" if report["qualified"] else "stopped"
            updated = self.db.execute("""UPDATE lb.ingestion_run SET status=%s,finished_at=clock_timestamp()
                WHERE id=%s AND status='running' RETURNING status""",(status,registration["run_id"])).fetchone()
            if not updated:
                raise PersistenceError("historical_state_conflict")
            self.db.execute("UPDATE lb.processing_run SET status='completed',finished_at=clock_timestamp() WHERE receipt_id=%s AND status='running'",
                            (registration["receipt_id"],))
            report["run_status"] = updated["status"]
        # qualified descreve o snapshot atual; run_status conserva o fato
        # histórico do encerramento, inclusive se uma auditoria posterior falhar.
        return report
