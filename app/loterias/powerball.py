from app.core.downloader import baixar_html_tabela_usamega_completa
from app.core.config import LOTERIAS

def baixar():
    config = LOTERIAS["powerball"]
    url_page_resultados = config["url_page_resultados"]
    nome_arquivo = config["nome_arquivo_base"] + config["extensao_arquivo"]
    pasta_destino = config["pasta_destino"]
    tempo_espera = 1.5

    return baixar_html_tabela_usamega_completa(url_page_resultados, nome_arquivo, pasta_destino, tempo_espera)




