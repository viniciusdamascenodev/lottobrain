"""Auditoria offline dos mapeamentos. Só lê arquivos e emite JSON em stdout."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from app.application.collect_mega_sena import canonical_json
from app.application.historical_content import (
    VERSION, CODE_VERSION, POLICY_VERSION, compare_shared, digest, source_evidence, to_content,
)
from app.application.mega_sena_content import digest as mega_digest, to_content as mega_content
from app.catalog import CATALOG
from app.domain import RawProvenance
from app.ingestion import mega_sena, lotofacil, mais_milionaria, powerball, mega_millions, euro_millions
from app.ingestion import (
    mega_sena_history, lotofacil_history, mais_milionaria_history,
    powerball_history, mega_millions_history, euro_millions_history,
)
from app.ingestion.mega_sena_api import ADAPTER_VERSION, SOURCE_KEY, normalize_response

ROOT = Path(__file__).resolve().parents[2]
HISTORIES = (
    (mega_sena, mega_sena_history, "xlsx", mega_sena.iter_xlsx_rows, "spec-0004"),
    (lotofacil, lotofacil_history, "xlsx", lotofacil.iter_xlsx_rows, "spec-0006"),
    (mais_milionaria, mais_milionaria_history, "xlsx", mais_milionaria.iter_xlsx_rows, "spec-0007"),
    (powerball, powerball_history, "html", powerball.read_html_rows, powerball.NORMALIZER_VERSION),
    (mega_millions, mega_millions_history, "html", mega_millions.read_html_rows, mega_millions.NORMALIZER_VERSION),
    (euro_millions, euro_millions_history, "json", euro_millions.read_json_rows, euro_millions.NORMALIZER_VERSION),
)


def _select_vectors(records):
    """Casos reais: fronteiras de regras e estados semânticos, sem sorteio aleatório."""
    selected = defaultdict(set)
    groups = defaultdict(list)
    seen_states = set()
    for record in records:
        content = record["content"]
        groups[content["rule_version"]].append(record)
        states = []
        for key in ("power_play_state", "multiplier_state"):
            if key in content["metadata"]:
                states.append(f"{key}:{content['metadata'][key]}")
        for series in content["series"]:
            states.extend(f"attribute:{a['key']}:{a['value']}" for a in series["attributes"] if a["value_type"] == "boolean")
        states.extend(f"money:{m['kind']}:{m['status']}" for m in content["money"] if m["status"] != "known")
        for state in states:
            if state not in seen_states:
                selected[record["data_record_ordinal"]].add(state)
                seen_states.add(state)
    for rule, values in groups.items():
        selected[values[0]["data_record_ordinal"]].add(f"rule_first:{rule}")
        selected[values[-1]["data_record_ordinal"]].add(f"rule_last:{rule}")
    return [{**record, "coverage": sorted(selected[record["data_record_ordinal"]])}
            for record in records if record["data_record_ordinal"] in selected]


def qualify(root: Path = ROOT, *, observed_at: datetime | None = None):
    # Instante desta leitura não é uma captura histórica da fonte. Não integra hashes.
    observed_at = observed_at or datetime.now(timezone.utc)
    reports, vectors, overlap = [], [], None
    for module, history, extension, reader, adapter in HISTORIES:
        slug = module.__name__.rsplit(".", 1)[-1]
        relative = f"data/raw/{slug}/{slug}_resultados.{extension}"
        path = root / relative
        baseline = history.HistoryBaseline()
        before = mega_sena.file_sha256(path)
        provenance = RawProvenance(module.SOURCE_KEY, before, observed_at, adapter)
        records, errors, alias_rows, reference_rows = [], [], defaultdict(list), defaultdict(list)
        for ordinal, row in enumerate(reader(path), 1):
            result = module.normalize_row(row, provenance)
            if not result.is_valid:
                errors.append({"data_record_ordinal": ordinal, "issues": [i.code for i in result.issues]})
                continue
            try:
                content = to_content(result.candidate)
                evidence = source_evidence(result.candidate)
            except ValueError as error:
                errors.append({"data_record_ordinal": ordinal, "mapping_error": str(error)})
                continue
            alias = content["identity"]
            alias_rows[(alias["namespace"], alias["value"])].append(ordinal)
            for ref in evidence["external_references"]:
                reference_rows[(ref["source_key"], ref["namespace"], ref["value"])].append(ordinal)
            records.append({"data_record_ordinal": ordinal, "content": content,
                "sha256": digest(content), "source_evidence": evidence, "evidence_sha256": digest(evidence)})
            if slug == "mega_sena" and alias["value"] == "2954":
                overlap = content
        records.sort(key=lambda r: (r["content"]["draw_date"], r["data_record_ordinal"]))
        selected = _select_vectors(records)
        vectors.append({"lottery": slug, "source": relative, "raw_sha256": before,
                        "normalizer_version": adapter, "vectors": selected})
        rules, money_states, attributes, series_counts, states = Counter(), Counter(), Counter(), Counter(), Counter()
        for record in records:
            c = record["content"]
            rules[c["rule_version"]] += 1
            for key in ("power_play_state", "multiplier_state"):
                if key in c["metadata"]:
                    states[f"{key}:{c['metadata'][key]}"] += 1
            for m in c["money"]:
                money_states[f"{m['kind']}:{m['status']}"] += 1
            for t in c["prize_tiers"]:
                money_states[f"tier.{t['key']}:{t['prize']['status']}"] += 1
            for s in c["series"]:
                series_counts[s["key"]] += 1
                for a in s["attributes"]:
                    attributes[f"{s['key']}.{a['key']}:{str(a['value']).lower()}"] += 1
        after = mega_sena.file_sha256(path)
        duplicates = [{"namespace": n, "value": v, "rows": rows}
                      for (n, v), rows in sorted(alias_rows.items()) if len(rows) > 1]
        duplicate_refs = [{"source_key": s, "namespace": n, "value": v, "rows": rows}
                          for (s, n, v), rows in sorted(reference_rows.items()) if len(rows) > 1]
        first_date = records[0]["content"]["draw_date"] if records else None
        last_date = records[-1]["content"]["draw_date"] if records else None
        first_contest = records[0]["content"]["identity"]["value"] if records and baseline.first_contest else None
        last_contest = records[-1]["content"]["identity"]["value"] if records and baseline.last_contest else None
        baseline_matches = (len(records) + len(errors) == baseline.total_rows and before == baseline.source_sha256
                            and first_date == baseline.first_date and last_date == baseline.last_date
                            and first_contest == (str(baseline.first_contest) if baseline.first_contest else None)
                            and last_contest == (str(baseline.last_contest) if baseline.last_contest else None))
        recipe = {"source_key": module.SOURCE_KEY, "normalizer_version": adapter,
            "code_version": CODE_VERSION, "canonicalization_version": VERSION, "policy_version": POLICY_VERSION,
            "catalog_fingerprint": hashlib.sha256(canonical_json(asdict(CATALOG.get(slug).lottery)).encode()).hexdigest()}
        manifest = [{"row": r["data_record_ordinal"], "content": r["sha256"], "evidence": r["evidence_sha256"]} for r in records]
        reports.append({"lottery": slug, "source": relative, "raw_sha256_before": before, "raw_sha256_after": after,
            "source_unchanged": before == after, "baseline_matches": baseline_matches, "recipe": recipe,
            "total_records": len(records) + len(errors), "representable_records": len(records), "errors": errors,
            "first_date": first_date, "last_date": last_date,
            "first_official_draw_number": first_contest, "last_official_draw_number": last_contest,
            "rule_counts": dict(sorted(rules.items())), "money_status_counts": dict(sorted(money_states.items())),
            "attribute_counts": dict(sorted(attributes.items())), "series_counts": dict(sorted(series_counts.items())),
            "semantic_state_counts": dict(sorted(states.items())), "duplicate_identities": duplicates,
            "duplicate_external_references": duplicate_refs, "vector_count": len(selected),
            "mapping_manifest_sha256": digest({"recipe": recipe, "raw_sha256": before, "records": manifest})})
    body = (root / "tests/fixtures/mega_sena_api_2954.json").read_bytes()
    api_result = normalize_response(body, RawProvenance(SOURCE_KEY, hashlib.sha256(body).hexdigest(),
        observed_at, ADAPTER_VERSION), expected_contest=2954)
    if not api_result.is_valid or overlap is None:
        raise ValueError("comparação Mega-Sena indisponível")
    api = to_content(api_result.candidate)
    comparison = {"contest": "2954", "json_input": "tests/fixtures/mega_sena_api_2954.json",
        "json_fixture_sha256": hashlib.sha256(body).hexdigest(),
        "json_fixture_is_original_wire": False, "legacy_json_v1_sha256": mega_digest(mega_content(api_result.candidate)),
        "historical_json_sha256": digest(api), "historical_xlsx_sha256": digest(overlap),
        "comparison": compare_shared(overlap, api)}
    report = {"report_version": "spec-0026-v1", "canonicalization_version": VERSION,
        "mode": "offline_mapping_only_no_sql", "histories": reports, "mega_sena_overlap": comparison}
    report["qualified"] = all(r["source_unchanged"] and r["baseline_matches"] and not r["errors"]
        and not r["duplicate_identities"] and not r["duplicate_external_references"] for r in reports) and not comparison["comparison"]["different"]
    return report, {"canonicalization_version": VERSION, "sources": vectors, "mega_sena_overlap": comparison}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Qualifica históricos em memória; sem SQL, rede ou escrita de dados")
    parser.add_argument("--vectors", action="store_true", help="emitir vetores reais em vez do relatório")
    args = parser.parse_args(argv)
    report, vectors = qualify()
    # JSON escapado é portável também em pipes Windows cp1252. O conteúdo
    # canônico continua UTF-8/Unicode, independente da codificação de stdout.
    print(json.dumps(vectors if args.vectors else report, ensure_ascii=True, sort_keys=True, indent=2))
    return 0 if report["qualified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
