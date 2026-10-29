import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from app.domain import RawProvenance
from app.ingestion.mega_sena import file_sha256, iter_xlsx_rows, normalize_row


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "raw" / "mega_sena" / "mega_sena_resultados.xlsx"
EXPECTED_SHA256 = "0e1936e3ac94a35a89c13ef31d705d3fb363239779ad6224b5e41171a3238686"
FIXTURE = ROOT / "tests" / "fixtures" / "mega_sena_rows.json"


class MegaSenaXlsxContractTests(unittest.TestCase):
    def test_reader_gets_controlled_sample_from_immutable_source(self):
        before = file_sha256(SOURCE)
        rows = list(iter_xlsx_rows(SOURCE, limit=2))
        after = file_sha256(SOURCE)

        self.assertEqual(EXPECTED_SHA256, before)
        self.assertEqual(before, after)
        self.assertEqual([1, 2], [row["Concurso"] for row in rows])
        self.assertEqual([4, 5, 30, 33, 41, 52], [rows[0][f"Bola{i}"] for i in range(1, 7)])

    def test_fixture_normalizes_like_the_corresponding_source_rows(self):
        source_rows = list(iter_xlsx_rows(SOURCE, limit=2))
        fixture_rows = json.loads(FIXTURE.read_text(encoding="utf-8"))[:2]
        provenance = RawProvenance(
            source_key="caixa_mega_sena_xlsx",
            raw_sha256=EXPECTED_SHA256,
            captured_at=datetime(2025, 12, 20, 12, tzinfo=timezone.utc),
            adapter_version="spec-0004",
        )
        source_results = [normalize_row(row, provenance) for row in source_rows]
        fixture_results = [normalize_row(row, provenance) for row in fixture_rows]
        self.assertEqual(fixture_results, source_results)


if __name__ == "__main__":
    unittest.main()
