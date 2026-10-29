from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.application.mega_sena_content import canonical_bytes, digest, to_content
from app.application.persistence import PersistenceError
from app.domain import RawProvenance, ValueStatus
from app.ingestion.mega_sena_api import normalize_response, SOURCE_KEY, ADAPTER_VERSION
from app.infrastructure.raw_storage import LocalRawStorage

ROOT = Path(__file__).resolve().parents[1]
BODY = (ROOT / "tests/fixtures/mega_sena_api_2954.json").read_bytes()


def candidate(body=BODY):
    result = normalize_response(body,RawProvenance(SOURCE_KEY,hashlib.sha256(body).hexdigest(),
        datetime(2026,10,21,tzinfo=timezone.utc),ADAPTER_VERSION),expected_contest=2954)
    assert result.is_valid, result.issues
    return result.candidate


class RelationalContentTests(unittest.TestCase):
    def test_fixed_real_vector(self):
        vector = json.loads((ROOT / "tests/fixtures/mega_sena_relational_v1.json").read_text(encoding="utf-8"))
        content = to_content(candidate())
        self.assertEqual(vector["content"],content)
        self.assertEqual(vector["sha256"],digest(content))

    def test_extraction_is_not_sorted_ordinal(self):
        values = to_content(candidate())["series"][0]["components"][0]["values"]
        self.assertEqual([1,9,37,39,42,44],[v["integer_value"] for v in values])
        self.assertEqual([2,6,1,5,3,4],[v["extraction_ordinal"] for v in values])

    def test_no_fabricated_extraction_and_changed_order_changes_hash(self):
        c = candidate()
        missing = replace(c,metadata=tuple((k,v) for k,v in c.metadata if k != "draw_order"))
        self.assertTrue(all(v["extraction_ordinal"] is None for v in to_content(missing)["series"][0]["components"][0]["values"]))
        ordered = replace(c,metadata=tuple((k,"1,9,37,39,42,44" if k == "draw_order" else v) for k,v in c.metadata))
        self.assertNotEqual(digest(to_content(c)),digest(to_content(ordered)))

    def test_decimal_scale_and_transport_do_not_change_hash(self):
        c = candidate()
        changed = replace(c,provenance=replace(c.provenance,adapter_version="another-test-version"),
            monetary_amounts=tuple(replace(m,amount=Decimal(str(m.amount)+"0") if "." in str(m.amount) else m.amount,
                                          source_text="texto de teste") for m in c.monetary_amounts))
        self.assertEqual(digest(to_content(c)),digest(to_content(changed)))

    def test_known_zero_and_unknown_remain_distinct(self):
        c = candidate()
        content = to_content(c)
        sena = next(t for t in content["prize_tiers"] if t["key"] == "sena")
        self.assertEqual(("known","0","BRL"),(sena["prize"]["status"],sena["prize"]["amount"],sena["prize"]["currency"]))
        unknown = to_content(replace(c,monetary_amounts=tuple(
            replace(m,status=ValueStatus.UNKNOWN,amount=None,currency=None) if m.kind == "sales_total" else m
            for m in c.monetary_amounts)))
        sales = next(m for m in unknown["money"] if m["kind"] == "sales_total")
        self.assertEqual(("unknown",None,None),(sales["status"],sales["amount"],sales["currency"]))
        self.assertNotEqual(digest(content),digest(unknown))
        self.assertEqual(canonical_bytes(content),canonical_bytes(json.loads(canonical_bytes(content))))


class RawStorageTests(unittest.TestCase):
    def test_preserves_wire_bytes_and_deduplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            store = LocalRawStorage(Path(directory))
            sha,key = store.put(BODY)
            self.assertEqual((sha,key),store.put(BODY))
            self.assertEqual(BODY,store.read(key,sha,len(BODY)))

    def test_corruption_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            store = LocalRawStorage(Path(directory)); sha,key = store.put(BODY)
            with (Path(directory)/key).open("wb") as output:
                output.write(b"negative-test-corruption")
            with self.assertRaisesRegex(PersistenceError,"artifact_hash_mismatch"):
                store.put(BODY)
            self.assertEqual(b"negative-test-corruption",(Path(directory)/key).read_bytes())

    def test_missing_and_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            store = LocalRawStorage(Path(directory))
            sha = hashlib.sha256(BODY).hexdigest()
            with self.assertRaisesRegex(PersistenceError,"evidence_missing"):
                store.read(f"{sha[:2]}/{sha}.bin",sha,len(BODY))
            with self.assertRaisesRegex(PersistenceError,"invalid_artifact"):
                store.read("../file",sha,len(BODY))


class SqlCliTests(unittest.TestCase):
    def test_sql_cli_requires_configuration_and_protects_raw(self):
        from app.interfaces.collect_mega_sena_postgres import main
        with patch.dict("os.environ",{},clear=True),patch("builtins.print"):
            self.assertEqual(1,main(["--command-key","test","--object-root",str(ROOT/"data/raw")]))
            self.assertEqual(1,main(["--command-key","test","--object-root",str(ROOT/"data/postgres-artifacts")]))
