import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.loterias.lotofacil import baixar

if __name__ == "__main__":
    caminho = baixar()
    print(f"\nArquivo baixado para: {caminho}" if caminho else "\nFalha no download.")
    
