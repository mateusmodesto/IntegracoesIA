import pandas as pd
from io import BytesIO


def preparar_conta_certa(file_certa):
    conta_certa = pd.read_excel(file_certa)
    if "Unnamed: 0" in conta_certa.columns:
        conta_certa.drop(columns=["Unnamed: 0"], inplace=True)
    conta_certa.drop(0, inplace=True, errors="ignore")
    conta_certa.reset_index(drop=True, inplace=True)
    conta_certa["DT_APROVACAO"] = pd.to_datetime(
        conta_certa["DT_APROVACAO"], format="%d/%m/%Y", errors="coerce"
    )
    conta_certa["VALOR"] = pd.to_numeric(conta_certa["VALOR"], errors="coerce")
    return conta_certa


def comparar_planilha(conta_certa, file_comparar, tolerancia):
    conta_comparar = pd.read_excel(file_comparar)
    conta_comparar["Data"] = pd.to_datetime(conta_comparar["Data"], errors="coerce")

    # Identificar coluna de valor: "R$" ou "VALOR EM REAIS"
    col_valor = "R$"
    if "VALOR EM REAIS" in conta_comparar.columns:
        col_valor = "VALOR EM REAIS"
    conta_comparar[col_valor] = pd.to_numeric(conta_comparar[col_valor], errors="coerce")

    ids_encontrados = []
    for _, row in conta_comparar.iterrows():
        data = row["Data"]
        valor = row[col_valor]

        if pd.isna(data) or pd.isna(valor):
            ids_encontrados.append(None)
            continue

        mask = (
            (conta_certa["DT_APROVACAO"] == data)
            & ((conta_certa["VALOR"] - valor).abs() <= tolerancia)
        )
        matches = conta_certa.loc[mask]

        if len(matches) > 0:
            ids_encontrados.append(int(matches.iloc[0]["ID_ORDEM_COMPRA"]))
        else:
            ids_encontrados.append(None)

    conta_comparar["ID_ORDEM_COMPRA"] = ids_encontrados
    return conta_comparar


def processar(file_certa, files_comparar, tolerancia):
    """Recebe o arquivo conta_certa e uma lista de arquivos conta_comparar.
    Retorna um dict com estatísticas, dados para JSON e bytes do xlsx."""
    conta_certa = preparar_conta_certa(file_certa)

    resultados = []
    for f in files_comparar:
        resultado = comparar_planilha(conta_certa, f, tolerancia)
        resultados.append(resultado)

    resultado_final = pd.concat(resultados, ignore_index=True)

    # Gerar xlsx em bytes
    buffer = BytesIO()
    resultado_final.to_excel(buffer, index=False, engine="openpyxl")
    xlsx_bytes = buffer.getvalue()

    # Estatísticas
    total = len(resultado_final)
    encontrados = int(resultado_final["ID_ORDEM_COMPRA"].notna().sum())

    # Preparar dados para JSON (substituir NaN)
    resultado_final["Data"] = resultado_final["Data"].dt.strftime("%d/%m/%Y").fillna("-")
    col_valor = "VALOR EM REAIS" if "VALOR EM REAIS" in resultado_final.columns else "R$"
    resultado_final[col_valor] = resultado_final[col_valor].apply(
        lambda x: f"{x:.2f}" if pd.notna(x) else "-"
    )
    resultado_final["ID_ORDEM_COMPRA"] = resultado_final["ID_ORDEM_COMPRA"].apply(
        lambda x: int(x) if pd.notna(x) else None
    )
    resultado_final = resultado_final.fillna("-")
    dados = resultado_final.where(resultado_final.notna(), None).to_dict(orient="records")

    return {
        "total": total,
        "encontrados": encontrados,
        "sem_match": total - encontrados,
        "dados": dados,
        "xlsx_bytes": xlsx_bytes,
    }
