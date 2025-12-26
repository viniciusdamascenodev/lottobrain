import os
import requests
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup


def baixar_arquivo_por_url(url, pasta_destino, nome_arquivo):
    os.makedirs(pasta_destino, exist_ok=True)
    caminho = os.path.join(pasta_destino, nome_arquivo)

    resposta = requests.get(url)

    if resposta.status_code == 200:
        with open(caminho, "wb") as f:
            f.write(resposta.content)
        
        print(f"✅ Arquivo salvo em {caminho}")
        return caminho

    else:
        print(f"❌ Erro {resposta.status_code} ao baixar o arquivo")
        return None
    

def baixar_html_tabela_usamega_completa(url_page_resultados, nome_arquivo, pasta_destino, tempo_espera=2.5):
    print(f"📄 Carregando página 1 -> {url_page_resultados}")
    response = pegar_html_usamega_com_selenium(url_page_resultados)
    if not response:
        print("❌ Erro ao acessar a página inicial.")
        return None

    soup_inicial = BeautifulSoup(response, "html.parser")

    # Encontra a tabela completa (com <thead> e <tbody>)
    tabela_completa = soup_inicial.find("table", class_="results")
    if tabela_completa is None:
        print("❌ Não foi possível encontrar a tabela na página inicial.")
        return None

    # Guarda a referência ao <tbody> da primeira tabela
    tbody_principal = tabela_completa.find("tbody")
    if tbody_principal is None:
        print("❌ Não foi possível encontrar o <tbody> da tabela principal.")
        return None

    # Coleta todos os <tr> da primeira página
    todos_os_tr = tbody_principal.find_all("tr")
    if not todos_os_tr:
        print("❌ Nenhum <tr> encontrado na página 1")
        return None

    # Começa a paginação
    pagina = 2
    while True:
        url = f"{url_page_resultados}/{pagina}"
        print(f"📄 Carregando página {pagina} -> {url}")

        response = pegar_html_usamega_com_selenium(url)
        if not response:
            print(f"❌ Página {pagina} não encontrada ou terminou a paginação.")
            break

        soup_pagina = BeautifulSoup(response, "html.parser")
        tabela_pagina = soup_pagina.find("table", class_="results")
        if tabela_pagina is None:
            print("❌ Tabela não encontrada na página", pagina)
            break

        tbody = tabela_pagina.find("tbody")
        if tbody is None:
            print("❌ <tbody> não encontrado na página", pagina)
            break

        # Adiciona os <tr> dessa página à lista geral
        trs_da_pagina = tbody.find_all("tr")
        if not trs_da_pagina:
            print(f"❌ Nenhum <tr> encontrado na página {pagina}")
            break

        todos_os_tr.extend(trs_da_pagina)

        pagina += 1
        time.sleep(tempo_espera)

    if not todos_os_tr:
        print("❌ Nenhuma linha de dados encontrada em todas as páginas.")
        return None

    tbody_principal.clear()
    for tr in todos_os_tr:
        tbody_principal.append(tr)

    os.makedirs(pasta_destino, exist_ok=True)
    caminho_arquivo = f"{pasta_destino}/{nome_arquivo}"
    with open(caminho_arquivo, "w", encoding="utf-8") as f:
        f.write(str(tabela_completa))
        print(f"💾 Arquivo HTML salvo em: {caminho_arquivo}")

    print("✅ Tabela completa com todas as páginas montada!")
    return caminho_arquivo


def pegar_html_usamega_com_selenium(url, timeout=2.5):
    print("🚗 Abrindo Google Chrome headless (Codespaces)...")

    options = Options()
    options.binary_location = "/usr/bin/google-chrome"

    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get(url)

        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "table.results tbody tr")
            )
        )

        time.sleep(1)
        return driver.page_source

    except Exception as e:
        print(f"❌ Erro ao carregar {url}: {e}")
        return None

    finally:
        driver.quit()
        print("🧹 Selenium finalizado.")