"""Grava os resultados em Excel (sempre) e Google Sheets (se configurado)."""
import json, os
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

# Planilha "Revenda de PCs" no Drive do João
SHEET_ID_PADRAO = "1pv_HIJKkv-p8HOKNOEPAFi1qEz7aEpgKIvDK61hdFGk"

def excel(abas: dict, caminho="saida/revenda.xlsx"):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    wb = Workbook(); wb.remove(wb.active)
    for nome, linhas in abas.items():
        ws = wb.create_sheet(nome)
        for row in linhas:
            ws.append(row)
        if linhas:
            for c in ws[1]:
                c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="305496")
            ws.freeze_panes = "A2"; ws.auto_filter.ref = ws.dimensions
            for i, col in enumerate(zip(*linhas), 1):
                ws.column_dimensions[get_column_letter(i)].width = min(60, max(10, max(len(str(v or "")) for v in col) + 2))
    wb.save(caminho)
    return caminho

def google_sheets(abas: dict):
    """Precisa de GOOGLE_SERVICE_ACCOUNT_JSON e SHEET_ID. A aba 'Parametros' nunca é sobrescrita."""
    cred, sid = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"), os.getenv("SHEET_ID") or SHEET_ID_PADRAO
    if not (cred and sid):
        print("[Sheets] não configurado; pulando"); return None
    import gspread
    gc = gspread.service_account_from_dict(json.loads(cred))
    sh = gc.open_by_key(sid)
    for nome, linhas in abas.items():
        try:
            ws = sh.worksheet(nome)
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(nome, rows=max(100, len(linhas) + 10), cols=max(10, len(linhas[0]) if linhas else 10))
        ws.clear()
        if linhas:
            ws.update(linhas, value_input_option="USER_ENTERED")
    return sh.url

def ler_parametros(padrao: dict):
    cred, sid = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"), os.getenv("SHEET_ID") or SHEET_ID_PADRAO
    p = dict(padrao)
    if not (cred and sid):
        return p
    import gspread
    sh = gspread.service_account_from_dict(json.loads(cred)).open_by_key(sid)
    try:
        ws = sh.worksheet("Parametros")
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet("Parametros", rows=30, cols=3)
        ws.update([["parametro", "valor"]] + [[k, v] for k, v in padrao.items()])
        return p
    for linha in ws.get_all_values()[1:]:
        if len(linha) < 2:
            continue
        k, v = linha[0], linha[1]
        if k in p:
            try: p[k] = type(p[k])(str(v).replace(",", "."))
            except ValueError: pass
    return p
