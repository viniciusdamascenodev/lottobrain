"""Casos de uso dos conjuntos privados; aprovação explícita por operador autorizado."""

import re
from hashlib import sha256
from uuid import UUID

from app.application.persistence import command_key, transact

MANIFEST_VERSION = "dataset_members_v1"


def actor_name(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 160:
        raise ValueError("Ator administrativo obrigatório, até 160 caracteres.")
    return value


def manifest_hash(slug, policy_hash, catalog_hash, members):
    header = f"{slug}\n{policy_hash}\n{catalog_hash}\n"
    lines = "".join(
        f"{m['draw_id']}|{m['revision_id']}|{m['observation_id']}|{m['draw_date']}|{m['content_hash']}\n"
        for m in members
    )
    return sha256((header + lines).encode("utf-8")).hexdigest()


class DatasetService:
    def __init__(self, units):
        self.units = units

    def policy(self, lottery, version, source_keys, actor):
        if not isinstance(version, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", version):
            raise ValueError("Versão de política inválida.")
        actor_name(actor)
        sources = tuple(sorted(set(source_keys)))
        if not sources or len(sources) != len(source_keys):
            raise ValueError("Fontes explícitas, sem repetição.")
        return transact(
            self.units, lambda unit: unit.datasets.policy(lottery, version, sources, actor)
        )

    def approve(self, policy_id, revision_ids, actor, key):
        actor_name(actor)
        command_key(key)
        if not isinstance(policy_id, UUID) or not 1 <= len(revision_ids) <= 6000:
            raise ValueError("Política e seleção explícita de revisões necessárias.")
        if any(not isinstance(r, UUID) for r in revision_ids) or len(set(revision_ids)) != len(
            revision_ids
        ):
            raise ValueError("Revisões UUID sem repetição.")
        return transact(
            self.units, lambda unit: unit.datasets.approve(policy_id, revision_ids, actor, key)
        )

    def activate(self, dataset_id, expected_version, actor, key):
        actor_name(actor)
        command_key(key)
        if (
            not isinstance(dataset_id, UUID)
            or type(expected_version) is not int
            or expected_version < 0
        ):
            raise ValueError("Dataset e versão esperada inválidos.")
        return transact(
            self.units,
            lambda unit: unit.datasets.activate(dataset_id, expected_version, actor, key),
        )

    def read(self, lottery, *, dataset_id=None, offset=0, limit=50):
        if dataset_id is not None and not isinstance(dataset_id, UUID):
            raise ValueError("Dataset UUID necessário.")
        if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("Paginação inválida; limite entre 1 e 100.")
        return transact(
            self.units, lambda unit: unit.datasets.read(lottery, dataset_id, offset, limit)
        )
