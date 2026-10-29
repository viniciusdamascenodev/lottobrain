"""Fluxo SQL opt-in: T1 → GET/PUT → T2 → parsing → T3, sem trocar o legado."""
from dataclasses import asdict
import hashlib

from app.application.collect_mega_sena import CollectionError
from app.application.mega_sena_content import CODE_VERSION as LEGACY_CODE, POLICY_VERSION as LEGACY_POLICY, VERSION, digest, source_texts, to_content
from app.application.mega_sena_incremental import CODE_VERSION, POLICY_VERSION
from app.application.historical_content import source_evidence
from app.application.persistence import Advance, BatchIntent, PersistenceError, ProcessingResult, command_key, transact
from app.domain import RawProvenance, ValidationIssue
from app.ingestion.mega_sena_api import ADAPTER_VERSION, SOURCE_KEY, normalize_response


def _result(receipt_id, observation, outcome, advance):
    return ProcessingResult(receipt_id,observation["observation_id"],outcome,observation["draw_id"],
        observation["revision_id"],observation["revision_no"],
        advance.expected_cursor+1 if advance is not None and observation["revision_id"] is not None else None)


class ProcessMegaSena:
    def __init__(self, units, storage):
        self.units = units
        self.storage = storage

    def execute(self, receipt_id, key, *, advance: Advance | None = None, batch: BatchIntent | None = None):
        key = command_key(key)
        if batch is not None and advance is not None: raise ValueError("batch e advance são exclusivos")

        def prepare(unit):
            binding = unit.catalog.qualify()
            receipt = unit.captures.receipt(receipt_id)
            if receipt.source_id != binding.source_id:
                raise PersistenceError("source_mismatch")
            phase=unit.batches.phase(batch,receipt_id) if batch is not None else None
            def fingerprint(code,policy):
                payload={"format":"process-command-v1","receipt":str(receipt_id),
                    "adapter":ADAPTER_VERSION,"code":code,"canonicalization":VERSION,"policy":policy,
                    "catalog":binding.fingerprint,"advance":{**asdict(advance),"checkpoint_id":str(advance.checkpoint_id)} if advance else None}
                if batch is not None:
                    payload["batch"]={**asdict(batch),"checkpoint_id":str(batch.checkpoint_id),"operation_id":str(batch.operation_id)}
                return digest(payload)
            request_hash = fingerprint(CODE_VERSION,POLICY_VERSION)
            compatible = (fingerprint(LEGACY_CODE,LEGACY_POLICY),)
            previous = unit.processing.lock_command(key,request_hash,compatible_hashes=compatible)
            return binding,receipt,request_hash,compatible,previous,unit.processing.observation(previous["processing_run_id"]) if previous else None,phase

        binding,receipt,request_hash,compatible,previous,completed,phase = transact(self.units,prepare)
        effective_advance=Advance(batch.checkpoint_id,batch.expected_cursor,batch.lease_token) if phase=="forward" else advance
        if previous:
            if completed is None:
                raise PersistenceError("invalid_revision")
            return _result(receipt.id,completed,previous["outcome"],effective_advance)
        throttle_intent=batch if batch is not None else advance
        if receipt.status == 429 and throttle_intent is not None:
            # T2 já está confirmado. Este cooldown não pode desaparecer com falha de T3.
            transact(self.units,lambda unit: unit.sync.throttle(receipt,throttle_intent.checkpoint_id))
        body = self.storage.read(receipt.object_key,receipt.sha256,receipt.byte_count)
        issues = []
        content = None
        texts = {}
        evidence = None
        if receipt.status != 200:
            issues.append(ValidationIssue(f"http.status_{receipt.status}","response","resposta HTTP não promovida"))
        elif receipt.content_type.split(";",1)[0].strip().lower() != "application/json":
            issues.append(ValidationIssue("http.invalid_content_type","response","Content-Type não qualificado"))
        else:
            normalized = normalize_response(body,RawProvenance(SOURCE_KEY,receipt.sha256,receipt.captured_at,ADAPTER_VERSION),
                                             expected_contest=receipt.expected_contest)
            issues.extend(normalized.issues)
            if normalized.is_valid:
                content = to_content(normalized.candidate)
                texts = source_texts(normalized.candidate)
                evidence = source_evidence(normalized.candidate)
        if effective_advance is not None and content is not None and int(content["identity"]) != effective_advance.expected_cursor+1:
            raise PersistenceError("checkpoint_conflict")

        def write(unit):
            existing = unit.processing.lock_command(key,request_hash,compatible_hashes=compatible)
            if existing:
                observation = unit.processing.observation(existing["processing_run_id"])
                return _result(receipt.id,observation,existing["outcome"],effective_advance)
            operation=None
            if batch is not None: checkpoint,operation=unit.batches.lock_operation(batch,binding,key)
            else: checkpoint = unit.sync.lock(advance,binding) if advance is not None and content is not None else None
            if unit.catalog.qualify().fingerprint != binding.fingerprint:
                raise PersistenceError("catalog_changed")
            unit.checkpoint("before_recipe_claim")
            processing_id = unit.processing.claim(binding,receipt)
            observation = unit.processing.observation(processing_id)
            if observation:
                outcome = "replayed" if observation["revision_id"] is not None else "quarantined"
            elif issues:
                observation = unit.processing.quarantine(binding,processing_id,issues)
                outcome = "quarantined"
            elif content is not None:
                observation = unit.draws.reconcile(binding,processing_id,content,digest(content),texts,evidence=evidence)
                outcome = observation["outcome"]
            else:
                raise PersistenceError("invalid_revision")
            if checkpoint is not None and observation["revision_id"] is not None:
                if effective_advance is not None: unit.sync.advance(effective_advance,checkpoint,observation)
                elif phase=="review": unit.sync.mark_review(batch,checkpoint,operation["review_after"])
            unit.processing.record(processing_id,key,request_hash,outcome)
            unit.processing.complete(processing_id)
            if batch is not None:
                unit.batches.complete_operation(batch,operation,observation,outcome)
                unit.captures.finish(receipt.id,outcome)
            unit.checkpoint("after_processing")
            return _result(receipt.id,observation,outcome,effective_advance)

        return transact(self.units,write)


class CaptureMegaSena:
    def __init__(self, units, storage, source):
        self.units = units
        self.storage = storage
        self.source = source

    def execute(self, contest, key):
        key = command_key(key)
        if contest is not None and (type(contest) is not int or contest < 1):
            raise ValueError("Concurso deve ser inteiro positivo")
        request_hash = digest({"format":"capture-command-v1","source":SOURCE_KEY,"contest":contest})

        def start(unit):
            binding = unit.catalog.qualify()
            return binding,unit.captures.start(binding,key,request_hash,contest)

        binding,ticket = transact(self.units,start)
        if ticket.receipt_id is not None:
            return ticket.receipt_id
        if not ticket.fresh:
            raise PersistenceError(ticket.error or "capture_in_progress")
        try:
            response = self.source.fetch(contest)
        except CollectionError as error:
            error_message = str(error)
            transact(self.units,lambda unit: unit.captures.fail(ticket,error_message))
            raise
        sha,key_object = self.storage.put(response.body)
        if sha != hashlib.sha256(response.body).hexdigest():
            raise PersistenceError("artifact_hash_mismatch")
        return transact(self.units,lambda unit: unit.captures.complete(binding,ticket,response,sha,key_object))


class CollectMegaSenaPostgres:
    def __init__(self, units, storage, source):
        self.units = units
        self.capture = CaptureMegaSena(units,storage,source)
        self.process = ProcessMegaSena(units,storage)

    def execute(self, contest, key, *, advance: Advance | None = None):
        receipt_id = self.capture.execute(contest,key)
        result = self.process.execute(receipt_id,key,advance=advance)
        # T6/resumo curto, não autoridade de continuidade; falha aqui é retomável.
        transact(self.units,lambda unit: unit.captures.finish(receipt_id,result.outcome))
        return result
