"""Abre, um por vez, os anúncios de PC (tipo "PC completo" ou "PC-base") de uma coleta da OLX e lê
a descrição completa, os atributos (processador, memória, condição...) e a data de publicação.
Usa o Chrome visível, com 6 a 10 s entre anúncios. Só lê: não clica em chat, comprar ou telefone.
Se a OLX pedir verificação ou bloquear, PARA na hora e salva o que já leu. Não tenta contornar.

Uso:  python scripts/detalhar_olx_navegador.py [--entrada data/olx_AAAA-MM-DD.csv] [--limite N]
Saída: data/olx_detalhes_AAAA-MM-DD.csv  (link, titulo, preco, descricao, atributos_json, publicado, lido_em)
Retoma de onde parou: links que já estão na saída são pulados.
"""
import argparse, csv, datetime as dt, glob, html as H, json, os, random, re, sys, time

SINAIS_BLOQUEIO = re.compile(r"just a moment|verifique se você é humano|confirme que você é humano|cf-challenge|captcha|acesso negado", re.I)
TIPOS = {"PC completo", "PC-base"}
TITULO_FORA = re.compile(r"defeito|pe[çc]as?\b|troco|procuro", re.I)
COLUNAS = ["link", "titulo", "preco", "descricao", "atributos_json", "publicado", "lido_em"]
LOTE = 10


class Bloqueado(Exception):
    pass


def candidatos(entrada, ja_lidos):
    """Linhas da coleta que valem abrir: PC completo/PC-base, com preço, sem defeito/peças/troco/procuro."""
    vistos, saida = set(ja_lidos), []
    with open(entrada, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            link = r.get("link")
            if (not link or link in vistos or r.get("tipo") not in TIPOS
                    or not (r.get("preco") or "").strip("0") or TITULO_FORA.search(r.get("titulo") or "")):
                continue
            vistos.add(link)
            saida.append(r)
    return saida


def _texto(descricao):
    t = re.sub(r"<br\s*/?>", "\n", descricao or "", flags=re.I)
    return H.unescape(re.sub(r"<[^>]+>", "", t)).strip()


def _dados_anuncio(html):
    """Objeto "ad" da página: vem em <script id="initial-data" data-json="...">; se não, no payload __next_f."""
    m = re.search(r'<script[^>]*id="initial-data"[^>]*data-json="([^"]*)"', html)
    if m:
        try:
            return json.loads(H.unescape(m.group(1))).get("ad") or {}
        except ValueError:
            pass
    pedacos = re.findall(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)', html, re.S)
    txt = "".join(json.loads(p) for p in pedacos)
    i = txt.find('"ad":{')
    if i >= 0:
        try:
            return json.JSONDecoder().raw_decode(txt, i + len('"ad":'))[0]
        except ValueError:
            pass
    return {}


def ler_anuncio(pag, link):
    """Devolve a linha de detalhes, ou None se o anúncio saiu do ar. Levanta Bloqueado se a OLX barrar."""
    resp = pag.goto(link, wait_until="domcontentloaded", timeout=60000)
    status = resp.status if resp else None
    if status in (404, 410):
        return None
    html = pag.content()
    if status != 200 or SINAIS_BLOQUEIO.search(html[:20000]):
        raise Bloqueado(f"status {status}")
    ad = _dados_anuncio(html)
    if not ad:
        return None
    atributos = {}
    for p in ad.get("properties") or []:
        if p.get("name") == "category":
            continue
        valor = p.get("value") or ", ".join(v.get("label", "") for v in p.get("values") or [] if isinstance(v, dict))
        atributos[p.get("label") or p.get("name")] = valor
    return {
        "link": link,
        "titulo": ad.get("subject") or "",
        "preco": re.sub(r"[^\d]", "", str(ad.get("priceValue") or ad.get("price") or "")),
        "descricao": _texto(ad.get("description") or ad.get("body")),
        "atributos_json": json.dumps(atributos, ensure_ascii=False),
        "publicado": ad.get("listTime") or ad.get("origListTime") or "",
        "lido_em": dt.datetime.now().isoformat(timespec="seconds"),
    }


def _gravar(saida, linhas):
    novo = not os.path.exists(saida)
    with open(saida, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS)
        if novo:
            w.writeheader()
        w.writerows(linhas)


def saida_para(entrada):
    return re.sub(r"olx_(\d{4}-\d{2}-\d{2})\.csv$", r"olx_detalhes_\1.csv", entrada)


def detalhar(pag, entrada, limite=None):
    """Lê os anúncios de PC da coleta `entrada` usando a página `pag` já aberta. Devolve (lidos, bloqueado)."""
    saida = saida_para(entrada)
    ja = set()  # links já detalhados em qualquer dia: só abre anúncios novos
    for antigo in glob.glob(os.path.join(os.path.dirname(saida) or ".", "olx_detalhes_*.csv")):
        with open(antigo, encoding="utf-8") as f:
            ja |= {r["link"] for r in csv.DictReader(f)}
    fila = candidatos(entrada, ja)
    if limite:
        fila = fila[:limite]
    print(f"Detalhes: {len(fila)} anúncios de PC para abrir ({len(ja)} já lidos antes)")
    buffer, lidos, fora = [], 0, 0
    try:
        for n, r in enumerate(fila, 1):
            linha = ler_anuncio(pag, r["link"])
            if linha is None:
                fora += 1
                print(f"  [{n}/{len(fila)}] fora do ar ou sem dados: {r['link']}")
            else:
                buffer.append(linha)
                lidos += 1
                print(f"  [{n}/{len(fila)}] {linha['titulo'][:60]} ({len(linha['descricao'])} caracteres)")
            if len(buffer) >= LOTE:
                _gravar(saida, buffer); buffer = []
            if n < len(fila):
                time.sleep(random.uniform(6, 10))  # ritmo de pessoa; não reduzir
    except Bloqueado as e:
        print(f"PAREI: a OLX pediu verificação ou bloqueou ({e}). Nada foi contornado.")
        _gravar(saida, buffer)
        print(f"{lidos} detalhes salvos em {saida} ({fora} fora do ar)")
        return lidos, True
    _gravar(saida, buffer)
    print(f"{lidos} detalhes salvos em {saida} ({fora} fora do ar)")
    return lidos, False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--entrada", help="CSV da coleta (padrão: o data/olx_AAAA-MM-DD.csv mais recente)")
    ap.add_argument("--limite", type=int, help="abre no máximo N anúncios (para teste)")
    args = ap.parse_args()
    entrada = args.entrada or max(glob.glob("data/olx_[0-9][0-9][0-9][0-9]-*.csv"))
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        try:
            nav = p.chromium.launch(channel="chrome", headless=False)  # Chrome instalado no PC
        except Exception:
            nav = p.chromium.launch(headless=False)
        pag = nav.new_page()
        _, bloqueado = detalhar(pag, entrada, args.limite)
        nav.close()
    sys.exit(2 if bloqueado else 0)


if __name__ == "__main__":
    main()
