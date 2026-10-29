"""Conjuntos imutáveis, promoção otimista e leitura por views privadas."""

from uuid import uuid4

from app.application.datasets import MANIFEST_VERSION, manifest_hash
from app.application.historical_content import PROFILES, digest
from app.application.persistence import PersistenceError
from app.catalog import CATALOG
from app.infrastructure.postgres.common import advisory_command, insert
from app.infrastructure.postgres.content_reader import read_contents
from app.infrastructure.postgres.profile_catalog import (
    PgProfileCatalogRepository,
    policy_catalog_hash,
)


class PgDatasetRepository:
    def __init__(self, db, observe):
        self.db, self.observe = db, observe

    def policy(self, lottery, version, sources, actor):
        if any(s not in PROFILES or PROFILES[s].lottery != lottery for s in sources):
            raise PersistenceError("unsupported_persistence_profile")
        game = self.db.execute(
            "SELECT id FROM lb.lottery WHERE slug=%s AND status='active'", (lottery,)
        ).fetchone()
        if game is None:
            raise PersistenceError("catalog_not_qualified")
        catalog_hash = policy_catalog_hash(lottery, sources)
        rules = [r.version_label for r in CATALOG.get(lottery).lottery.rules]
        value = digest(
            {
                "schema": "dataset-policy-v1",
                "lottery": lottery,
                "version": version,
                "sources": list(sources),
                "rules": rules,
                "catalog": catalog_hash,
            }
        )
        advisory_command(self.db, "dataset-policy", f"{lottery}:{version}")
        old = self.db.execute(
            "SELECT * FROM lb.dataset_policy WHERE lottery_id=%s AND version_label=%s",
            (game["id"], version),
        ).fetchone()
        if old:
            if old["policy_hash"] != value:
                raise PersistenceError("idempotency_conflict")
            return old["id"]
        return insert(
            self.db,
            "dataset_policy",
            id=uuid4(),
            lottery_id=game["id"],
            version_label=version,
            source_keys=list(sources),
            rule_labels=rules,
            catalog_fingerprint=catalog_hash,
            policy_hash=value,
            approved_by=actor,
        )

    def approve(self, policy_id, revision_ids, actor, key):
        request = digest(
            {"policy": str(policy_id), "revisions": sorted(map(str, revision_ids)), "actor": actor}
        )
        advisory_command(self.db, "dataset-decision", key)
        prior_decision = self.db.execute(
            "SELECT * FROM lb.dataset_decision WHERE command_key=%s", (key,)
        ).fetchone()
        if prior_decision:
            if prior_decision["request_hash"] != request or prior_decision["action"] not in {
                "approve",
                "reuse",
            }:
                raise PersistenceError("idempotency_conflict")
            return prior_decision["dataset_id"]
        prior = self.db.execute(
            "SELECT * FROM lb.approved_dataset WHERE request_key=%s", (key,)
        ).fetchone()
        if prior:
            if prior["request_hash"] != request:
                raise PersistenceError("idempotency_conflict")
            if prior["status"] != "approved":
                raise PersistenceError("dataset_not_approved")
            return prior["id"]
        policy = self.db.execute(
            """SELECT p.*,l.slug FROM lb.dataset_policy p
            JOIN lb.lottery l ON l.id=p.lottery_id WHERE p.id=%s""",
            (policy_id,),
        ).fetchone()
        if policy is None:
            raise PersistenceError("dataset_policy_not_found")
        if policy["catalog_fingerprint"] != policy_catalog_hash(
            policy["slug"], policy["source_keys"]
        ):
            raise PersistenceError("dataset_policy_outdated")
        contents = read_contents(self.db, revision_ids)
        members = self.db.execute(
            """SELECT r.id AS revision_id,r.draw_id,r.draw_date_local AS draw_date,r.content_hash,
            r.lottery_id,r.seal_state FROM lb.draw_revision r WHERE r.id=ANY(%s)
            ORDER BY r.draw_date_local,r.draw_id""",
            (list(revision_ids),),
        ).fetchall()
        if len({m["draw_id"] for m in members}) != len(members):
            raise PersistenceError("dataset_duplicate_draw")
        support = []
        for m in members:
            if m["lottery_id"] != policy["lottery_id"] or m["seal_state"] != "sealed":
                raise PersistenceError("invalid_dataset_member")
            observation = self.db.execute(
                """SELECT o.id,pr.catalog_fingerprint,s.key AS source_key FROM lb.candidate_observation o
                JOIN lb.processing_run pr ON pr.id=o.processing_run_id
                JOIN lb.capture_receipt c ON c.id=pr.receipt_id JOIN lb.data_source s ON s.id=c.source_id
                WHERE o.revision_id=%s AND o.semantic_hash=%s AND o.decision IN ('new','unchanged','correction_candidate','replayed')
                AND pr.status='completed' AND s.key=ANY(%s) AND s.readiness IN ('approved','contract_observed')
                ORDER BY o.completed_at,o.id LIMIT 1""",
                (m["revision_id"], m["content_hash"], policy["source_keys"]),
            ).fetchone()
            if observation is None or contents[m["revision_id"]]["lottery"] != policy["slug"]:
                raise PersistenceError("invalid_dataset_member")
            content = contents[m["revision_id"]]
            if content["rule_version"] not in policy["rule_labels"]:
                raise PersistenceError("dataset_policy_outdated")
            PgProfileCatalogRepository(self.db).qualify(
                observation["source_key"], content["rule_version"]
            )
            m["observation_id"] = observation["id"]
            support.append(observation)
        catalog_hash = digest(sorted({s["catalog_fingerprint"] for s in support}))
        manifest = manifest_hash(policy["slug"], policy["policy_hash"], catalog_hash, members)
        advisory_command(self.db, "dataset-manifest", f"{policy_id}:{manifest}")
        existing = self.db.execute(
            "SELECT id,status FROM lb.approved_dataset WHERE lottery_id=%s AND policy_id=%s AND manifest_version=%s AND manifest_hash=%s",
            (policy["lottery_id"], policy_id, MANIFEST_VERSION, manifest),
        ).fetchone()
        if existing:
            if existing["status"] != "approved":
                raise PersistenceError("dataset_not_approved")
            insert(
                self.db,
                "dataset_decision",
                id=uuid4(),
                dataset_id=existing["id"],
                lottery_id=policy["lottery_id"],
                action="reuse",
                actor=actor,
                command_key=key,
                request_hash=request,
            )
            return existing["id"]
        dataset = insert(
            self.db,
            "approved_dataset",
            id=uuid4(),
            lottery_id=policy["lottery_id"],
            policy_id=policy_id,
            catalog_fingerprint=catalog_hash,
            manifest_hash=manifest,
            member_count=len(members),
            first_date=members[0]["draw_date"],
            last_date=members[-1]["draw_date"],
            status="building",
            request_key=key,
            request_hash=request,
        )
        for ordinal, (member, observation) in enumerate(zip(members, support, strict=True), 1):
            insert(
                self.db,
                "dataset_member",
                dataset_id=dataset,
                lottery_id=policy["lottery_id"],
                draw_id=member["draw_id"],
                revision_id=member["revision_id"],
                observation_id=observation["id"],
                ordinal=ordinal,
            )
        insert(
            self.db,
            "dataset_decision",
            id=uuid4(),
            dataset_id=dataset,
            lottery_id=policy["lottery_id"],
            action="approve",
            actor=actor,
            command_key=key,
            request_hash=request,
        )
        self.db.execute(
            """UPDATE lb.approved_dataset SET status='approved',approved_at=clock_timestamp(),approved_by=%s
            WHERE id=%s""",
            (actor, dataset),
        )
        self.observe("after_dataset_approval")
        return dataset

    def activate(self, dataset, expected_version, actor, key):
        request = digest(
            {"dataset": str(dataset), "expected_version": expected_version, "actor": actor}
        )
        advisory_command(self.db, "dataset-decision", key)
        prior = self.db.execute(
            "SELECT * FROM lb.dataset_decision WHERE command_key=%s", (key,)
        ).fetchone()
        if prior:
            if prior["request_hash"] != request or prior["action"] != "activate":
                raise PersistenceError("idempotency_conflict")
            return {"dataset_id": prior["dataset_id"], "active_version": prior["active_version"]}
        d = self.db.execute(
            "SELECT lottery_id FROM lb.approved_dataset WHERE id=%s AND status='approved'",
            (dataset,),
        ).fetchone()
        if d is None:
            raise PersistenceError("dataset_not_approved")
        advisory_command(self.db, "active-dataset", str(d["lottery_id"]))
        old = self.db.execute(
            "SELECT * FROM lb.active_dataset WHERE lottery_id=%s FOR UPDATE", (d["lottery_id"],)
        ).fetchone()
        if (old["row_version"] if old else 0) != expected_version:
            raise PersistenceError("dataset_activation_conflict")
        version = expected_version + 1
        if old:
            self.db.execute(
                "UPDATE lb.active_dataset SET dataset_id=%s,row_version=%s WHERE lottery_id=%s",
                (dataset, version, d["lottery_id"]),
            )
        else:
            insert(
                self.db,
                "active_dataset",
                lottery_id=d["lottery_id"],
                dataset_id=dataset,
                row_version=version,
            )
        insert(
            self.db,
            "dataset_decision",
            id=uuid4(),
            dataset_id=dataset,
            lottery_id=d["lottery_id"],
            action="activate",
            actor=actor,
            command_key=key,
            request_hash=request,
            active_version=version,
            previous_dataset_id=old["dataset_id"] if old else None,
        )
        self.observe("after_dataset_activation")
        return {"dataset_id": dataset, "active_version": version}

    def read(self, lottery, dataset_id, offset, limit):
        condition = "d.id=%s" if dataset_id is not None else "d.active"
        params = (lottery, dataset_id) if dataset_id is not None else (lottery,)
        d = self.db.execute(
            f"SELECT * FROM lb.approved_dataset_info d WHERE d.slug=%s AND {condition}", params
        ).fetchone()
        if d is None:
            raise PersistenceError("dataset_not_approved")
        if d["manifest_version"] != MANIFEST_VERSION:
            raise PersistenceError("unsupported_dataset_manifest")
        members = self.db.execute(
            """SELECT id AS revision_id,draw_id,dataset_observation_id AS observation_id,draw_date_local AS draw_date,content_hash
            FROM lb.approved_draw_revision WHERE dataset_id=%s ORDER BY dataset_ordinal""",
            (d["id"],),
        ).fetchall()
        if (
            len(members) != d["member_count"]
            or manifest_hash(lottery, d["policy_hash"], d["catalog_fingerprint"], members)
            != d["manifest_hash"]
        ):
            raise PersistenceError("artifact_hash_mismatch")
        selected = members[offset : offset + limit]
        contents = read_contents(self.db, [m["revision_id"] for m in selected], dataset_id=d["id"])
        references = self.db.execute(
            """SELECT draw_id,namespace,value,source_key FROM lb.approved_external_draw_reference
            WHERE dataset_id=%s AND draw_id=ANY(%s) ORDER BY source_key,namespace,value""",
            (d["id"], [m["draw_id"] for m in selected]),
        ).fetchall()
        return {
            "dataset_id": d["id"],
            "lottery": lottery,
            "manifest_hash": d["manifest_hash"],
            "total": d["member_count"],
            "offset": offset,
            "limit": limit,
            "next_offset": offset + limit if offset + limit < d["member_count"] else None,
            "first_date": d["first_date"],
            "last_date": d["last_date"],
            "items": [
                {
                    "draw_id": m["draw_id"],
                    "revision_id": m["revision_id"],
                    "content": contents[m["revision_id"]],
                    "references": [
                        {k: v for k, v in r.items() if k != "draw_id"}
                        for r in references
                        if r["draw_id"] == m["draw_id"]
                    ],
                }
                for m in selected
            ],
        }
