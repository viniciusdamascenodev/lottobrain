from app.core.downloader import baixar_arquivo_por_url
from app.core.config import LOTERIAS

def baixar_megasena():
    config = LOTERIAS["mega_sena"]
    url = config["url_download"]
    pasta = config["pasta_destino"]
    nome_arquivo = config["nome_arquivo_base"] + config["extensao_arquivo"]

    return baixar_arquivo_por_url(url, pasta, nome_arquivo)
