"""Catálogo consolidado e independente de persistência das loterias suportadas."""

from datetime import date, time

from app.domain import (
    CollectionReadiness,
    DataSourceDefinition,
    DrawTime,
    ExtensionDefinition,
    ExtensionKind,
    LotteryCatalog,
    LotteryCatalogEntry,
    MarketDefinition,
    ScheduleDefinition,
    SourceAuthority,
)
from app.ingestion.euro_millions import EURO_MILLIONS
from app.ingestion.lotofacil import LOTOFACIL
from app.ingestion.mais_milionaria import MAIS_MILIONARIA
from app.ingestion.mega_millions import MEGA_MILLIONS
from app.ingestion.mega_sena import MEGA_SENA
from app.ingestion.powerball import POWERBALL


VERIFIED_AT = date(2026, 10, 20)


def _source(key, name, authority, purposes, data_format, url, readiness):
    return DataSourceDefinition(
        key, name, authority, purposes, data_format, url, readiness
    )


def _schedule(key, timezone, days_and_hours, url):
    return ScheduleDefinition(
        key=key,
        timezone=timezone,
        draw_times=tuple(DrawTime(day, time(hour, minute)) for day, hour, minute in days_and_hours),
        observed_at=VERIFIED_AT,
        source_url=url,
    )


CAIXA_SCHEDULE_URL = "https://loterias.caixa.gov.br/Paginas/regras-sorteios.aspx"

CATALOG = LotteryCatalog(
    entries=(
        LotteryCatalogEntry(
            lottery=MEGA_SENA,
            markets=(MarketDefinition("BR", "BRL"),),
            sources=(
                _source("caixa_mega_sena_xlsx", "Exportação histórica CAIXA", SourceAuthority.OFFICIAL, ("historical_results",), "xlsx", "https://servicebus3.caixa.gov.br/portaldeloterias/api/resultados/download?modalidade=Mega-Sena", CollectionReadiness.CONTRACT_OBSERVED),
                _source("caixa_mega_sena_rules", "Página Mega-Sena CAIXA", SourceAuthority.OFFICIAL, ("rules", "current_result"), "html", "https://loterias.caixa.gov.br/Paginas/mega-sena.aspx", CollectionReadiness.RESEARCH_REQUIRED),
                _source("caixa_mega_sena_json", "Resposta JSON pública CAIXA", SourceAuthority.OFFICIAL, ("current_result", "individual_result"), "json", "https://servicebus2.caixa.gov.br/portaldeloterias/api/megasena", CollectionReadiness.CONTRACT_OBSERVED),
            ),
            schedules=(_schedule("observed_2026", "America/Sao_Paulo", ((1, 21, 0), (3, 21, 0), (6, 11, 0)), CAIXA_SCHEDULE_URL),),
            extensions=(ExtensionDefinition("mega_da_virada", "Mega da Virada", ExtensionKind.SPECIAL_DRAW, ("BR",)),),
            capabilities=("official_draw_number", "prize_tiers", "sales_total", "winner_locations"),
        ),
        LotteryCatalogEntry(
            lottery=LOTOFACIL,
            markets=(MarketDefinition("BR", "BRL"),),
            sources=(
                _source("caixa_lotofacil_xlsx", "Exportação histórica CAIXA", SourceAuthority.OFFICIAL, ("historical_results",), "xlsx", "https://servicebus3.caixa.gov.br/portaldeloterias/api/resultados/download?modalidade=Lotof%C3%A1cil", CollectionReadiness.CONTRACT_OBSERVED),
                _source("caixa_lotofacil_rules", "Página Lotofácil CAIXA", SourceAuthority.OFFICIAL, ("rules", "current_result"), "html", "https://loterias.caixa.gov.br/Paginas/LOTOFACIL.aspx", CollectionReadiness.RESEARCH_REQUIRED),
            ),
            schedules=(_schedule("observed_2026", "America/Sao_Paulo", tuple((day, 21, 0) for day in range(5)) + ((6, 11, 0),), CAIXA_SCHEDULE_URL),),
            extensions=(ExtensionDefinition("independencia", "Lotofácil da Independência", ExtensionKind.SPECIAL_DRAW, ("BR",)),),
            capabilities=("official_draw_number", "fixed_and_parimutuel_tiers", "sales_total", "winner_locations"),
        ),
        LotteryCatalogEntry(
            lottery=MAIS_MILIONARIA,
            markets=(MarketDefinition("BR", "BRL"),),
            sources=(
                _source("caixa_mais_milionaria_xlsx", "Exportação histórica CAIXA", SourceAuthority.OFFICIAL, ("historical_results",), "xlsx", "https://servicebus3.caixa.gov.br/portaldeloterias/api/resultados/download?modalidade=%2BMilion%C3%A1ria", CollectionReadiness.CONTRACT_OBSERVED),
                _source("caixa_mais_milionaria_rules", "Página +Milionária CAIXA", SourceAuthority.OFFICIAL, ("rules", "current_result"), "html", "https://loterias.caixa.gov.br/paginas/mais-Milionaria.aspx", CollectionReadiness.RESEARCH_REQUIRED),
            ),
            schedules=(_schedule("observed_2026", "America/Sao_Paulo", ((2, 21, 0), (6, 11, 0)), CAIXA_SCHEDULE_URL),),
            capabilities=("official_draw_number", "prize_tiers", "guarantee_reserve", "sales_total"),
        ),
        LotteryCatalogEntry(
            lottery=POWERBALL,
            markets=(
                MarketDefinition("US_MULTI", "USD"),
                MarketDefinition("UK", "GBP", "shared_jackpot_participant"),
            ),
            sources=(
                _source("powerball_official", "Powerball", SourceAuthority.OFFICIAL, ("rules", "current_results"), "html", "https://www.powerball.com/", CollectionReadiness.RESEARCH_REQUIRED),
                _source("usamega_powerball_html", "USA Mega snapshot", SourceAuthority.SECONDARY, ("historical_results",), "html", "https://www.usamega.com/powerball/results", CollectionReadiness.CONTRACT_OBSERVED),
            ),
            schedules=(_schedule("observed_2026", "America/New_York", ((0, 22, 59), (2, 22, 59), (5, 22, 59)), "https://www.powerball.com/"),),
            extensions=(
                ExtensionDefinition("power_play", "Power Play", ExtensionKind.BET_FEATURE, ("US_MULTI",)),
                ExtensionDefinition("double_play", "Double Play", ExtensionKind.LINKED_DRAW, ("US_MULTI",), date(2021, 8, 23)),
            ),
            capabilities=("cash_or_annuity", "jurisdiction_exceptions", "linked_draw", "ticket_multiplier"),
        ),
        LotteryCatalogEntry(
            lottery=MEGA_MILLIONS,
            markets=(MarketDefinition("US_MULTI", "USD"),),
            sources=(
                _source("mega_millions_official", "Mega Millions", SourceAuthority.OFFICIAL, ("rules", "current_results"), "html", "https://www.megamillions.com/How-To-Play.aspx", CollectionReadiness.RESEARCH_REQUIRED),
                _source("usamega_mega_millions_html", "USA Mega snapshot", SourceAuthority.SECONDARY, ("historical_results",), "html", "https://www.usamega.com/mega-millions/results", CollectionReadiness.CONTRACT_OBSERVED),
            ),
            schedules=(_schedule("observed_2026", "America/New_York", ((1, 23, 0), (4, 23, 0)), "https://www.megamillions.com/faqs"),),
            extensions=(ExtensionDefinition("embedded_multiplier", "Multiplicador embutido", ExtensionKind.BET_FEATURE, ("US_MULTI",), date(2025, 4, 8)),),
            capabilities=("cash_or_annuity", "jurisdiction_exceptions", "ticket_multiplier"),
        ),
        LotteryCatalogEntry(
            lottery=EURO_MILLIONS,
            markets=(
                MarketDefinition("EU_MULTI", "EUR"),
                MarketDefinition("FR", "EUR", "national_product"),
                MarketDefinition("IE", "EUR", "national_product"),
            ),
            sources=(
                _source("fdj_euromillions_history", "Arquivo histórico FDJ", SourceAuthority.OFFICIAL, ("historical_results",), "zip", "https://www.fdj.fr/jeux-de-tirage/euromillions-my-million/historique", CollectionReadiness.RESEARCH_REQUIRED),
                _source("fdj_euromillions_rules", "EuroMillions–My Million FDJ", SourceAuthority.OFFICIAL, ("rules", "schedule"), "html", "https://www.fdj.fr/jeux-de-tirage/euromillions-my-million/comment-jouer", CollectionReadiness.RESEARCH_REQUIRED),
                _source("pedromealha_euromillions_api_json", "Snapshot API comunitária", SourceAuthority.SECONDARY, ("historical_results",), "json", "https://euromillions.api.pedromealha.dev/draws", CollectionReadiness.CONTRACT_OBSERVED),
            ),
            schedules=(_schedule("fr_observed_2026", "Europe/Paris", ((1, 21, 5), (4, 21, 5)), "https://www.fdj.fr/jeux-de-tirage/euromillions-my-million/comment-jouer"),),
            extensions=(
                ExtensionDefinition("my_million", "My Million", ExtensionKind.NATIONAL_RAFFLE, ("FR",)),
                ExtensionDefinition("ireland_only_raffle", "Ireland Only Raffle", ExtensionKind.NATIONAL_RAFFLE, ("IE",)),
            ),
            capabilities=("multinational_result", "national_extensions", "parimutuel_tiers"),
        ),
    )
)
