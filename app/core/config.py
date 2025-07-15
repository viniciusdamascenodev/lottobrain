mega_sena_config = {
    "nome": "Mega-Sena",
    "sigla": "mega_sena",
    "pais": "Brasil",
    "url_download": "https://servicebus2.caixa.gov.br/portaldeloterias/api/resultados/download?modalidade=Mega-Sena",
    "frequencia_sorteios": ["quarta", "sábado"],
    "tipo_download": "url_direta",
    "extensao_arquivo": ".xlsx",
    "pasta_destino": "data/raw/mega_sena",
    "nome_arquivo_base": "mega_sena_resultados",
    "tempo_max_espera": 10
}



LOTERIAS = {
    "mega_sena": mega_sena_config
}
