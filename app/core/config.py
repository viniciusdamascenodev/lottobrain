mega_sena_config = {
    "nome": "Mega-Sena",
    "sigla": "mega_sena",
    "origem": "Brasil",
    "url_download": "https://servicebus2.caixa.gov.br/portaldeloterias/api/resultados/download?modalidade=Mega-Sena",
    "frequencia_sorteios": ["terça", "quinta", "sábado"],
    "tipo_download": "url_direta",
    "extensao_arquivo": ".xlsx",
    "pasta_destino": "data/raw/mega_sena",
    "nome_arquivo_base": "mega_sena_resultados",
    "tempo_max_espera": 10
}

mais_milionaria_config = {
    "nome": "+Milionária",
    "sigla": "mais_milionaria",
    "origem": "Brasil",
    "url_download": "https://servicebus2.caixa.gov.br/portaldeloterias/api/resultados/download?modalidade=+Milion%C3%A1ria",
    "frequencia_sorteios": ["quarta", "sábado"],
    "tipo_download": "url_direta",
    "extensao_arquivo": ".xlsx",
    "pasta_destino": "data/raw/mais_milionaria",
    "nome_arquivo_base": "mais_milionaria_resultados",
    "tempo_max_espera": 10
}

lotofacil_config = {
    "nome": "Lotofácil",
    "sigla": "lotofacil",
    "origem": "Brasil",
    "url_download": "https://servicebus2.caixa.gov.br/portaldeloterias/api/resultados/download?modalidade=Lotof%C3%A1cil",
    "frequencia_sorteios": ["segunda", "terça", "quarta", "quinta", "sexta", "sábado"],
    "tipo_download": "url_direta",
    "extensao_arquivo": ".xlsx",
    "pasta_destino": "data/raw/lotofacil",
    "nome_arquivo_base": "lotofacil_resultados",
    "tempo_max_espera": 10
}

mega_millions_config = {
    "nome": "Mega Millions",
    "sigla": "mega_millions",
    "origem": "Estados Unidos",
    "url_page_resultados": "https://www.usamega.com/mega-millions/results",
    "frequencia_sorteios": ["terça", "sexta"],
    "tipo_download": "scraping",
    "extensao_arquivo": ".html",
    "pasta_destino": "data/raw/mega_millions",
    "nome_arquivo_base": "mega_millions_resultados",
    "tempo_max_espera": 10
}

powerball_config = {
    "nome": "Powerball",
    "sigla": "powerball",
    "origem": "Estados Unidos",
    "url_page_resultados": "https://www.usamega.com/powerball/results",
    "frequencia_sorteios": ["segunda", "quarta", "sábado"],
    "tipo_download": "scraping",
    "extensao_arquivo": ".html",  
    "pasta_destino": "data/raw/powerball",
    "nome_arquivo_base": "powerball_resultados",
    "tempo_max_espera": 10
}

euro_millions_config = {
    "nome": "Euro Millions",
    "sigla": "euro_millions",
    "origem": "Europa",
    "url_download": "https://euromillions.api.pedromealha.dev/draws",
    "frequencia_sorteios": ["terça", "sexta"],
    "tipo_download": "url_direta",
    "extensao_arquivo": ".json",
    "pasta_destino": "data/raw/euro_millions",
    "nome_arquivo_base": "euro_millions_resultados",
    "tempo_max_espera": 10
}


LOTERIAS = {
    "mega_sena": mega_sena_config,
    "mais_milionaria": mais_milionaria_config,
    "lotofacil": lotofacil_config,
    "mega_millions": mega_millions_config,
    "powerball": powerball_config,
    "euro_millions": euro_millions_config
}
