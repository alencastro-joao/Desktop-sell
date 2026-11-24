"""Coleta anúncios da OLX abrindo as páginas num navegador de verdade (Chrome/Chromium visível),
no computador do João, com ritmo de pessoa. Só lê. Se a OLX pedir verificação ou bloquear, PARA:
não tenta contornar.

Uso:  python scripts/coletar_olx_navegador.py [--paginas 2]
Saída: data/olx_AAAA-MM-DD.csv  (data, busca, categoria_busca, titulo, preco, cidade, uf, publicado, link)
"""
import argparse, csv, datetime as dt, json, os, random, re, sys, time
from playwright.sync_api import sync_playwright

BUSCAS = {
    # PCs completos (para preço de mercado das configurações-alvo)
    "pc gamer rx 580": "PC completo", "pc gamer gtx 1660": "PC completo", "pc gamer rx 5500": "PC completo",
    "pc gamer gtx 1650": "PC completo", "pc gamer rx 6600": "PC completo", "pc gamer rtx 3060": "PC completo",
    # Peças usadas
    "rx 580 8gb": "Peça", "gtx 1660 super": "Peça", "rx 5500 xt": "Peça", "gtx 1650": "Peça",
    "rx 6600": "Peça", "rtx 3060": "Peça", "fonte 500w": "Peça", "memoria ddr4 8gb": "Peça", "memoria ddr3 8gb": "Peça",
    # PCs-base
    "computador i5": "PC-base", "pc i5 6 geracao": "PC-base", "computador i7": "PC-base", "cpu i5 sem placa de video": "PC-base",
}
SINAIS_BLOQUEIO = re.compile(r"just a moment|verifique se você é humano|confirme que você é humano|cf-challenge|captcha|acesso negado", re.I)

def achar_ads(node):
    if isinstance(node, dict):
        if isinstance(node.get("ads"), list):
            return [a for a in node["ads"] if isinstance(a, dict) and a.get("listId")]
        for v in node.values():
            if (r := achar_ads(v)):
                return r
    elif isinstance(node, list):
        for v in node:
            if (r := achar_ads(v)):
                return r
    return []

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paginas", type=int, default=2)
    args = ap.parse_args()
    hoje = dt.date.today().isoformat()
    os.makedirs("data", exist_ok=True)
    saida = f"data/olx_{hoje}.csv"
    linhas, vistos = [], set()
    with sync_playwright() as p:
        try:
            nav = p.chromium.launch(channel="chrome", headless=False)  # Chrome instalado no PC
        except Exception:
            nav = p.chromium.launch(headless=False)
        pag = nav.new_page()
        for busca, tipo in BUSCAS.items():
            for n in range(1, args.paginas + 1):
                url = f"https://www.olx.com.br/informatica?q={busca.replace(' ', '+')}&o={n}"
                resp = pag.goto(url, wait_until="domcontentloaded", timeout=60000)
                html = pag.content()
                if (resp and resp.status != 200) or SINAIS_BLOQUEIO.search(html[:20000]):
                    print(f"PAREI: a OLX pediu verificação ou bloqueou em '{busca}' (status {resp.status if resp else '?'}). Nada foi contornado.")
                    nav.close(); gravar(saida, linhas); sys.exit(2)
                m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
                ads = achar_ads(json.loads(m.group(1))) if m else []
                if not ads:
                    print(f"[{busca}] página {n}: nenhum anúncio lido (layout mudou ou fim da lista)")
                    break
                for a in ads:
                    link = a.get("url") or a.get("friendlyUrl")
                    if not link or link in vistos:
                        continue
                    vistos.add(link)
                    preco = re.sub(r"[^\d]", "", str(a.get("price") or ""))
                    loc = a.get("locationDetails") or {}
                    linhas.append([hoje, busca, tipo, a.get("subject") or a.get("title"), preco,
                                   loc.get("municipality"), loc.get("uf"), a.get("date") or a.get("origListTime"), link])
                print(f"[{busca}] página {n}: {len(ads)} anúncios")
                time.sleep(random.uniform(6, 10))  # ritmo de pessoa; não reduzir
        nav.close()
    gravar(saida, linhas)

def gravar(saida, linhas):
    with open(saida, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["data", "busca", "tipo", "titulo", "preco", "cidade", "uf", "publicado", "link"])
        w.writerows(linhas)
    print(f"{len(linhas)} anúncios salvos em {saida}")

if __name__ == "__main__":
    main()
