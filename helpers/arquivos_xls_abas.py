import os
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

caminho_base = Path(os.getenv("PATH_TESTES_ARQUIVOS"))
arquivo = caminho_base / "TESTES GUSTAVO.xlsx"


def listar_abas() -> list[str]:
    xl = pd.ExcelFile(arquivo)
    return xl.sheet_names


def ler_aba(indice: int) -> pd.DataFrame:
    abas = listar_abas()
    aba = abas[indice]
    df = pd.read_excel(arquivo, sheet_name=aba)
    df.columns = df.columns.str.strip().str.upper().str.replace(" ", "_")
    df = df.dropna(how="all")
    print(f"Lendo aba [{indice}]: '{aba}'")
    return df


abas = listar_abas()
print("Abas disponíveis:")
for i, aba in enumerate(abas):
    print(f"  [{i}] {aba}")