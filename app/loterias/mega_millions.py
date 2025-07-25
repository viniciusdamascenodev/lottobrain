import pandas as pd
import os

from bs4 import BeautifulSoup
from app.core.downloader import baixar_html_tabela_usamega_completa
from app.core.config import LOTERIAS

def baixar():
    config = LOTERIAS["mega_millions"]
    url_page_resultados = config["url_page_resultados"]
    nome_arquivo = config["nome_arquivo_base"] + config["extensao_arquivo"]
    pasta_destino = config["pasta_destino"]
    tempo_espera = 1.5

    return baixar_html_tabela_usamega_completa(url_page_resultados, nome_arquivo, pasta_destino, tempo_espera)




    


def extrair_dados_html(html_tabela):
    soup = BeautifulSoup(html_tabela, "html.parser")

    # Encontra todos os <tr>
    trs = soup.find_all("tr")

    dados = []

    for tr in trs:
        try:
            # Encontra a data
            data_tag = tr.find("a")
            if not data_tag:
                continue  # pula tr inválido
            data = data_tag.text.strip()

            # Encontra todas as bolas (normalmente 6 <li>: 5 + mega ball)
            bolas = tr.find_all("li")
            if len(bolas) < 6:
                continue  # pula se não tiver 6 bolas

            numeros = [b.text.strip() for b in bolas]

            # Separa as bolas
            bola1, bola2, bola3, bola4, bola5 = numeros[:5]
            mega_ball = numeros[5]

            # Jackpot
            jackpot_tag = tr.find_all("td")[-1].text.strip().replace("$", "").replace("Million", "").strip()
            jackpot = float(jackpot_tag)  # opcional: float para facilitar análise

            dados.append({
                "data": data,
                "bola1": bola1,
                "bola2": bola2,
                "bola3": bola3,
                "bola4": bola4,
                "bola5": bola5,
                "mega_ball": mega_ball,
                "jackpot_milhoes_usd": jackpot
            })
        except Exception as e:
            print(f"⚠️ Erro ao processar uma linha: {e}")
            continue

    return dados
