import os
import requests

def baixar_arquivo_por_url(url, pasta_destino, nome_arquivo):
    os.makedirs(pasta_destino, exist_ok=True)
    caminho = os.path.join(pasta_destino, nome_arquivo)

    resposta = requests.get(url)

    if resposta.status_code == 200:
        with open(caminho, "wb") as f:
            f.write(resposta.content)
        
        print(f"Arquivo salvo em {caminho}")
        return caminho

    else:
        print(f"Erro {resposta.status_code} ao baixar o arquivo")
        return None
    