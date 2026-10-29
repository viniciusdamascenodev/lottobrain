"""Lease curta, CAS e conclusão contígua na mesma conexão da revisão."""
from datetime import timedelta

from app.application.persistence import Lease, PersistenceError
from app.infrastructure.postgres.common import insert


class PgSyncRepository:
    def __init__(self, db, observe):
        self.db = db
        self.observe = observe

    def _checkpoint(self, checkpoint_id, binding):
        row = self.db.execute("SELECT *,clock_timestamp() AS now FROM lb.sync_checkpoint WHERE id=%s FOR UPDATE",(checkpoint_id,)).fetchone()
        if not row or (row["lottery_id"],row["source_id"],row["strategy"]) != (binding.lottery_id,binding.source_id,"official_numeric_sequence"):
            raise PersistenceError("checkpoint_conflict")
        return row

    def lock(self, advance, binding):
        cp = self._checkpoint(advance.checkpoint_id,binding)
        if cp["lease_token"] != advance.lease_token or cp["lease_until"] is None or cp["lease_until"] <= cp["now"]:
            raise PersistenceError("lease_lost")
        if cp["cursor_sequence"] != advance.expected_cursor:
            raise PersistenceError("checkpoint_conflict")
        return cp

    def claim_lease(self, checkpoint_id, binding, seconds=300):
        if type(seconds) is not int or not 5 <= seconds <= 300:
            raise ValueError("lease entre 5 e 300 segundos")
        cp = self._checkpoint(checkpoint_id,binding)
        if cp["cooldown_until"] is not None and cp["cooldown_until"] > cp["now"]:
            raise PersistenceError("source_cooldown")
        if cp["lease_until"] is not None and cp["lease_until"] > cp["now"]:
            raise PersistenceError("lease_busy")
        until = cp["now"] + timedelta(seconds=seconds)
        self.db.execute("UPDATE lb.sync_checkpoint SET lease_token=lease_token+1,lease_until=%s,row_version=row_version+1 WHERE id=%s",
                        (until,checkpoint_id))
        return Lease(checkpoint_id,cp["lease_token"]+1,cp["cursor_sequence"],until)

    def advance(self, intent, checkpoint, observation):
        sequence = intent.expected_cursor + 1
        insert(self.db,"sync_step",checkpoint_id=intent.checkpoint_id,sequence_no=sequence,
            observation_id=observation["observation_id"],lease_token=intent.lease_token,
            completed_at=self.db.execute("SELECT clock_timestamp() AS t").fetchone()["t"])
        self.observe("after_step")
        result = self.db.execute("""UPDATE lb.sync_checkpoint SET cursor_sequence=%s,row_version=row_version+1
            WHERE id=%s AND cursor_sequence=%s AND lease_token=%s AND row_version=%s AND lease_until > clock_timestamp()""",
            (sequence,intent.checkpoint_id,intent.expected_cursor,intent.lease_token,checkpoint["row_version"]))
        if result.rowcount != 1:
            raise PersistenceError("checkpoint_conflict")
        self.observe("after_cursor")

    def throttle(self, receipt, checkpoint_id):
        if receipt.status != 429:
            raise PersistenceError("not_throttled")
        cp = self.db.execute("SELECT * FROM lb.sync_checkpoint WHERE id=%s FOR UPDATE",(checkpoint_id,)).fetchone()
        if not cp or cp["source_id"] != receipt.source_id:
            raise PersistenceError("checkpoint_conflict")
        self.db.execute("""UPDATE lb.sync_checkpoint SET cooldown_until=greatest(cooldown_until,clock_timestamp()+interval '15 minutes'),
            row_version=row_version+1 WHERE id=%s""",(checkpoint_id,))

    def mark_review(self,intent,checkpoint,next_review):
        anchor=self.db.execute("SELECT last_sequence FROM lb.ingestion_baseline WHERE id=%s",(checkpoint["baseline_id"],)).fetchone()["last_sequence"]
        if not anchor<next_review<=checkpoint["cursor_sequence"]+1: raise PersistenceError("checkpoint_conflict")
        changed=self.db.execute("""UPDATE lb.sync_checkpoint SET review_next=%s,row_version=row_version+1 WHERE id=%s
            AND lease_token=%s AND row_version=%s AND lease_until>clock_timestamp()""",
            (next_review,intent.checkpoint_id,intent.lease_token,checkpoint["row_version"]))
        if changed.rowcount!=1: raise PersistenceError("lease_lost")
        self.observe("after_review")
