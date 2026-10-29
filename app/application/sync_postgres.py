"""Lotes SQL limitados e retomáveis; sem driver, rede concreta ou agendamento."""
from dataclasses import dataclass
from uuid import UUID

from app.application.collect_mega_sena import CollectionError
from app.application.persistence import BatchIntent, PersistenceError, command_key, transact
from app.application.persist_mega_sena import CaptureMegaSena, ProcessMegaSena
from app.application.sync_mega_sena import SyncPolicy

CODE_VERSION = "spec-0031-v1"


@dataclass(frozen=True)
class SyncBatchRequest:
    checkpoint_id: UUID
    command: str
    policy: SyncPolicy = SyncPolicy()

    def __post_init__(self):
        if not isinstance(self.checkpoint_id,UUID) or not isinstance(self.policy,SyncPolicy):
            raise ValueError("checkpoint UUID e SyncPolicy necessários")
        command_key(self.command)


def review_targets(anchor,cursor,pointer,window):
    low = max(anchor+1,cursor-window+1)
    if not window or low>cursor: return []
    start = pointer if low<=pointer<=cursor else low
    return list(range(start,cursor+1))+list(range(low,start))


def next_operation(batch,operations,cursor):
    """Planejamento puro sobre intenção congelada e operações confirmadas."""
    pending = [op for op in operations if op["state"]=="pending"]
    if pending: return pending[0],None
    if not operations: return {"phase":"discovery","contest":None,"reuse_id":None,"review_after":None},None
    if operations[-1]["outcome"]=="quarantined": return None,"quarantined"
    expected = batch["cursor_start"]+sum(op["phase"]=="forward" for op in operations)
    if cursor!=expected: raise PersistenceError("checkpoint_conflict")
    latest = batch["latest_sequence"]
    if latest<batch["cursor_start"]: return None,"source_behind_cursor"
    policy,targets = batch["policy"],batch["review_targets"]
    slots = sum(op["reuse_id"] is None for op in operations)
    reviews = sum(op["phase"]=="review" for op in operations)
    reserve = int(bool(targets) and latest>batch["cursor_start"] and policy["max_requests"]>=3)
    if cursor<latest and not reviews:
        target = cursor+1
        if target==latest or slots<policy["max_requests"]-reserve:
            return {"phase":"forward","contest":target,"reuse_id":operations[0]["id"] if target==latest else None,
                    "review_after":None},None
    if reviews<len(targets) and (cursor==latest or not reviews):
        target = targets[reviews]
        if target==latest or slots<policy["max_requests"]:
            return {"phase":"review","contest":target,"reuse_id":operations[0]["id"] if target==latest else None,
                    "review_after":targets[(reviews+1)%len(targets)]},None
    return None,"caught_up" if cursor==latest else "budget_exhausted"


class _GuardedSource:
    def __init__(self, owner): self.owner=owner

    def fetch(self,contest):
        owner=self.owner
        owner._heartbeat()
        owner.wait(owner.request.policy.interval_seconds)
        owner._heartbeat()  # Sem transação aberta durante espera/HTTP/storage.
        return owner.source.fetch(contest)


class SyncMegaSenaPostgres:
    def __init__(self,units,storage,source,*,wait,observe=lambda stage,op:None):
        self.units,self.storage,self.source,self.wait,self.observe=units,storage,source,wait,observe
        # Cada execute cria um executor próprio; não compartilha estado de lease
        # entre duas chamadas concorrentes da mesma instância pública.

    def execute(self,request: SyncBatchRequest):
        if not isinstance(request,SyncBatchRequest): raise ValueError("pedido de lote necessário")
        return _BatchExecution(self,request).run()


class _BatchExecution:
    def __init__(self,service,request):
        self.units,self.storage,self.source,self.wait,self.observe=service.units,service.storage,service.source,service.wait,service.observe
        self.request=request
        self.batch_id=self.token=None

    def _heartbeat(self):
        return transact(self.units,lambda u:u.batches.heartbeat(self.batch_id,self.token))

    def run(self):
        opened=transact(self.units,lambda u:u.batches.open(self.request))
        if opened["report"] is not None: return opened["report"]
        self.batch_id,self.token=opened["id"],opened["lease_token"]
        capture=CaptureMegaSena(self.units,self.storage,_GuardedSource(self))
        process=ProcessMegaSena(self.units,self.storage)
        try:
            while True:
                snapshot=transact(self.units,lambda u:u.batches.snapshot(self.batch_id,self.token))
                planned,reason=next_operation(snapshot["batch"],snapshot["operations"],snapshot["cursor"])
                if reason:
                    return transact(self.units,lambda u:u.batches.finish(self.batch_id,self.token,reason))
                op=planned if "id" in planned else transact(self.units,lambda u:u.batches.reserve(self.batch_id,self.token,planned))
                self.observe("operation_reserved",op)
                if op["receipt_id"] is None:
                    if op["reuse_id"] is not None:
                        receipt=next(item["receipt_id"] for item in snapshot["operations"] if item["id"]==op["reuse_id"])
                    else:
                        try: receipt=capture.execute(op["contest"],op["capture_key"])
                        except CollectionError:
                            return transact(self.units,lambda u:u.batches.finish(self.batch_id,self.token,"collection_failed"))
                        except PersistenceError as error:
                            if error.code not in ("capture_in_progress","http.transport_failure","unexpected_response_url",
                                                  "response_too_large","invalid_content_length","truncated_response"):
                                raise
                            return transact(self.units,lambda u:u.batches.finish(self.batch_id,self.token,"capture_unresolved"))
                    self.observe("receipt_committed",op)
                    transact(self.units,lambda u:u.batches.attach(self.batch_id,self.token,op["id"],receipt))
                op=transact(self.units,lambda u:u.batches.prepare_operation(self.batch_id,self.token,op["id"]))
                intent=BatchIntent(self.request.checkpoint_id,op["expected_cursor"],self.token,op["id"])
                process.execute(op["receipt_id"],op["processing_key"],batch=intent)
                self.observe("operation_committed",op)
        finally:
            try: transact(self.units,lambda u:u.batches.release(self.batch_id,self.token))
            except Exception: pass  # Limpeza best-effort nunca mascara o erro/resultado principal.
