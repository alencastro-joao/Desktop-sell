"""Coletores de anúncios. Cada função devolve lista de dicts:
{fonte, id, titulo, preco, url, cidade, uf, texto}"""
import json, os, re, time
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131 Safari/537.36",
      "Accept-Language": "pt-BR,pt;q=0.9"}

# ---------------- Mercado Livre (API oficial) ----------------
_ML_TOKEN = None

def _ml_token():
    """A busca do ML exige token. Usa app próprio (ML_CLIENT_ID / ML_CLIENT_SECRET) via client_credentials."""
    global _ML_TOKEN
    if _ML_TOKEN:
        return _ML_TOKEN
    cid, sec = os.getenv("ML_CLIENT_ID"), os.getenv("ML_CLIENT_SECRET")
    if not (cid and sec):
        return None
    r = requests.post("https://api.mercadolibre.com/oauth/token", timeout=30,
                      data={"grant_type": "client_credentials", "client_id": cid, "client_secret": sec})
    r.raise_for_status()
    _ML_TOKEN = r.json()["access_token"]
    return _ML_TOKEN

def mercado_livre(query, paginas=3, condicao="used", categoria="MLB1649"):
    """categoria MLB1649 = Computadores > PCs (ajustável)."""
    tok = _ml_token()
    h = {"Authorization": f"Bearer {tok}"} if tok else {}
    out = []
    for pg in range(paginas):
        params = {"q": query, "offset": pg * 50, "limit": 50, "condition": condicao}
        if categoria:
            params["category"] = categoria
        r = requests.get("https://api.mercadolibre.com/sites/MLB/search", params=params, headers=h, timeout=30)
        if r.status_code != 200:
            print(f"[ML] {r.status_code} para '{query}': {r.text[:200]}")
            break
        res = r.json().get("results", [])
        for it in res:
            end = it.get("address") or {}
            out.append({"fonte": "Mercado Livre", "id": it["id"], "titulo": it["title"], "preco": it["price"],
                        "url": it["permalink"], "cidade": end.get("city_name"), "uf": end.get("state_name"),
                        "texto": it["title"] + " " + " ".join(f"{a.get('name')} {a.get('value_name')}" for a in it.get("attributes", []))})
        if len(res) < 50:
            break
        time.sleep(1)
    return out

# ---------------- OLX (página pública) ----------------
def olx(query, paginas=3, caminho="informatica/computadores-e-desktops"):
    out = []
    s = requests.Session(); s.headers.update(UA)
    for pg in range(1, paginas + 1):
        r = s.get(f"https://www.olx.com.br/{caminho}", params={"q": query, "o": pg}, timeout=30)
        if r.status_code != 200:
            # Bloqueio: registra e segue sem OLX; não tenta contornar.
            print(f"[OLX] {r.status_code} (possível bloqueio) para '{query}'")
            break
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.S)
        if not m:
            print("[OLX] estrutura da página mudou; nada extraído"); break
        ads = _achar_ads(json.loads(m.group(1)))
        for a in ads:
            preco = re.sub(r"[^\d]", "", str(a.get("price") or ""))
            if not preco:
                continue
            loc = a.get("locationDetails") or {}
            out.append({"fonte": "OLX", "id": str(a.get("listId")), "titulo": a.get("subject") or a.get("title"),
                        "preco": float(preco), "url": a.get("url") or a.get("friendlyUrl"),
                        "cidade": loc.get("municipality"), "uf": loc.get("uf"),
                        "texto": f"{a.get('subject','')} {' '.join(str(p.get('value','')) for p in a.get('properties', []))}"})
        if not ads:
            break
        time.sleep(4)  # ritmo mínimo entre páginas; não reduzir
    return out

def _achar_ads(node):
    """Procura recursivamente a lista de anúncios dentro do JSON do Next.js."""
    if isinstance(node, dict):
        if isinstance(node.get("ads"), list):
            return [a for a in node["ads"] if isinstance(a, dict) and a.get("listId")]
        for v in node.values():
            if (r := _achar_ads(v)):
                return r
    elif isinstance(node, list):
        for v in node:
            if (r := _achar_ads(v)):
                return r
    return []

def buscar(query, paginas=3, **kw):
    res = []
    for f in (mercado_livre, olx):
        try:
            res += f(query, paginas, **kw.get(f.__name__, {}))
        except Exception as e:
            print(f"[{f.__name__}] erro: {e}")
    return res
