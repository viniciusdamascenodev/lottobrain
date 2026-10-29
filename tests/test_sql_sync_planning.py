"""Planejamento puro: contadores dublês em memória, não sorteios novos."""
from uuid import uuid4
import pytest

from app.application.persistence import BatchIntent, PersistenceError
from app.application.sync_postgres import SyncBatchRequest, SyncMegaSenaPostgres, next_operation, review_targets
from app.application.sync_mega_sena import SyncPolicy


def batch(cursor=2954,latest=3071,targets=None,budget=2):
    return {"cursor_start":cursor,"latest_sequence":latest,"review_targets":targets or [],
            "policy":{"max_requests":budget}}


def operation(phase="discovery",target=None,reuse=None,state="done",outcome="new"):
    return {"id":uuid4(),"phase":phase,"contest":target,"reuse_id":reuse,"state":state,"outcome":outcome}


@pytest.mark.parametrize("kwargs", [{"checkpoint_id":"not-uuid"},{"command":"bad key"},{"policy":None}])
def test_request_requires_explicit_valid_intent(kwargs):
    with pytest.raises(ValueError): SyncBatchRequest(**{"checkpoint_id":uuid4(),"command":"batch",**kwargs})


@pytest.mark.parametrize("kwargs", [{"max_requests":0},{"max_requests":11},{"max_requests":True},
    {"review_window":-1},{"review_window":21},{"interval_seconds":1},{"interval_seconds":31},{"interval_seconds":float("nan")}])
def test_reuses_bounded_policy(kwargs):
    with pytest.raises(ValueError): SyncPolicy(**kwargs)


def test_batch_intent_validates_operation_id():
    with pytest.raises(ValueError): BatchIntent(uuid4(),2954,1,"not-uuid")


@pytest.mark.parametrize("window,pointer,expected", [(0,2955,[]),(3,2956,[2956,2957,2955]),(20,1,[2955,2956,2957])])
def test_review_window_is_incremental_and_rotates(window,pointer,expected):
    assert review_targets(2954,2957,pointer,window)==expected


def test_pending_operation_is_reused_without_new_reservation():
    op=operation(state="pending")
    assert next_operation(batch(),[op],2954)==(op,None)


def test_discovery_is_first_and_only_contiguous_forward_is_planned():
    planned,reason=next_operation(batch(),[],2954)
    assert planned["phase"]=="discovery" and reason is None
    planned,reason=next_operation(batch(),[operation()],2954)
    assert planned["contest"]==2955 and planned["reuse_id"] is None
    assert next_operation(batch(),[operation(),operation("forward",2955)],2955)==(None,"budget_exhausted")


def test_discovery_receipt_can_advance_with_only_one_slot():
    discovery=operation()
    planned,reason=next_operation(batch(latest=2955,budget=1),[discovery],2954)
    assert planned["reuse_id"]==discovery["id"] and planned["contest"]==2955
    assert next_operation(batch(latest=2955,budget=1),[discovery,operation("forward",2955,discovery["id"])],2955)==(None,"caught_up")


def test_backlog_reserves_one_review_slot_and_keeps_original_window():
    header=batch(cursor=2955,targets=[2955],budget=3)
    operations=[operation(),operation("forward",2956)]
    planned,_=next_operation(header,operations,2956)
    assert planned=={"phase":"review","contest":2955,"reuse_id":None,"review_after":2955}
    assert next_operation(header,operations+[operation("review",2955)],2956)==(None,"budget_exhausted")


def test_current_discovery_can_be_reused_for_review_without_get():
    op=operation()
    planned,_=next_operation(batch(cursor=2955,latest=2955,targets=[2955],budget=1),[op],2955)
    assert planned["phase"]=="review" and planned["reuse_id"]==op["id"]


def test_quarantine_behind_source_and_foreign_cursor_fail_closed():
    assert next_operation(batch(),[operation(outcome="quarantined")],2954)==(None,"quarantined")
    assert next_operation(batch(cursor=2955,latest=2954),[operation()],2955)==(None,"source_behind_cursor")
    with pytest.raises(PersistenceError,match="checkpoint_conflict"):
        next_operation(batch(),[operation()],3071)


def test_cleanup_failure_never_masks_original_error():
    class Unit:
        def __enter__(self): self.batches=self; return self
        def __exit__(self,*args): return False
        def open(self,request): return {"id":uuid4(),"lease_token":1,"report":None}
        def snapshot(self,*args): raise ValueError("original failure")
        def release(self,*args): raise RuntimeError("cleanup failure")
    service=SyncMegaSenaPostgres(Unit,object(),object(),wait=lambda seconds:None)
    with pytest.raises(ValueError,match="original failure"):
        service.execute(SyncBatchRequest(uuid4(),"batch"))
