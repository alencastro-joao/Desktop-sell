"""Pipeline: coleta PCs à venda, precifica peças, simula upgrades, estima revenda e grava planilha."""
import argparse, datetime as dt, re
from . import config, coletores, saida
from .parser import parse
from .stats import percentil, sem_outliers
from .upgrades import opcoes, avaliar

BUSCAS_COMPRA = ["computador i5", "computador i7", "pc desktop core i5", "cpu ryzen 5", "computador completo monitor"]
PALAVRAS_RUINS = re.compile(r"\b(notebook|laptop|placa m[aã]e|gabinete vazio|defeito|pe[cç]as|retirada de pe[cç]as|all in one|macbook|imac)\b", re.I)

def precos_pecas(paginas):
    """Mediana de preço de cada peça, separando novo e usado."""
    precos, linhas = {}, [["peca", "condicao", "mediana", "p25", "p75", "amostras"]]
    pecas = config.GPUS + [config.SSD, config.FONTE, config.KIT_PERIFERICOS]
    for p in pecas:
        precos[p["nome"]] = {}
        for cond, ml_cond in (("usado", "used"), ("novo", "new")):
            ads = coletores.mercado_livre(p["busca"], paginas=1, condicao=ml_cond, categoria=None)
            if cond == "usado":
                ads += coletores.olx(p["busca"], paginas=1, caminho="informatica")
            termo = p["busca"].split()[-1].lower()
            vals = sem_outliers([a["preco"] for a in ads if termo in a["titulo"].lower() and a["preco"] > 30])
            if len(vals) >= 3:
                med = percentil(vals, 50)
                precos[p["nome"]][cond] = round(med)
                linhas.append([p["nome"], cond, round(med), round(percentil(vals, 25)), round(percentil(vals, 75)), len(vals)])
            else:
                linhas.append([p["nome"], cond, p.get(cond), None, None, f"{len(vals)} (usando padrão)"])
    return precos, linhas

_cache_rev = {}
def revenda(cpu_familia, gpu, ram_gb, paginas, comparaveis):
    chave = (cpu_familia, gpu, ram_gb >= 16)
    if chave in _cache_rev:
        return _cache_rev[chave]
    q = f"pc gamer {cpu_familia} {gpu or ''}".strip()
    ads = coletores.buscar(q, paginas)
    vals = []
    for a in ads:
        s = parse(a["texto"])
        if gpu and (not s.gpu or gpu.split()[1].lower() not in s.gpu.lower()):
            continue
        if s.cpu and cpu_familia.split()[0].lower() not in s.cpu.lower():
            continue
        if PALAVRAS_RUINS.search(a["titulo"]) or a["preco"] < 300:
            continue
        vals.append(a["preco"])
        comparaveis.append([q, a["fonte"], a["titulo"], a["preco"], s.cpu, s.gpu, s.ram_gb, a["url"]])
    vals = sem_outliers(vals)
    r = {"p25": percentil(vals, 25), "p50": percentil(vals, 50), "p75": percentil(vals, 75), "n": len(vals)}
    _cache_rev[chave] = r
    return r

def familia(cpu):
    m = re.match(r"(i[3579]|Ryzen [3579])", cpu or "")
    return m.group(1) if m else (cpu or "")

def rodar(paginas, saida_excel):
    params = saida.ler_parametros(config.PARAMS)
    paginas = paginas or int(params["max_paginas_busca"])
    precos, aba_pecas = precos_pecas(1)

    vistos, candidatos = set(), []
    sobre = [["data", "fonte", "termo", "anuncios_lidos", "descartados_como_ruido"]]
    # Anúncios colados à mão na planilha entram sempre, sem filtro de ruído.
    for a in saida.ler_anuncios_manuais():
        vistos.add(a["id"]); candidatos.append(a)
    if candidatos:
        sobre.append([dt.date.today().isoformat(), "Manual", "aba Anuncios manuais", len(candidatos), 0])
    for q in BUSCAS_COMPRA:
        cont = {}
        for a in coletores.buscar(q, paginas):
            c = cont.setdefault(a["fonte"], [0, 0]); c[0] += 1
            if PALAVRAS_RUINS.search(a["titulo"] or ""):
                c[1] += 1; continue
            if a["id"] in vistos:
                continue
            vistos.add(a["id"]); candidatos.append(a)
        for fonte, (n, ruido) in cont.items():
            sobre.append([dt.date.today().isoformat(), fonte, q, n, ruido])

    comparaveis = [["busca", "fonte", "titulo", "preco", "cpu", "gpu", "ram_gb", "link"]]
    cab = ["data", "fonte", "titulo", "preco_compra", "cidade", "uf", "cpu", "ram_gb", "ram_tipo", "gpu_atual",
           "ssd", "fonte_w", "monitor", "upgrade_sugerido", "custo_pecas", "fretes", "custo_total",
           "revenda_p25", "revenda_mediana", "revenda_p75", "n_comparaveis",
           "lucro_p25", "lucro_mediana", "lucro_p75", "margem_mediana_%",
           "preco_venda_rapida", "vale_a_pena", "link"]
    linhas = []
    hoje = dt.date.today().isoformat()
    for a in candidatos:
        s = parse(a["texto"])
        if not s.cpu:
            continue
        melhor = None
        for plano in opcoes(s, precos):
            rev = revenda(familia(s.cpu), plano["gpu"], plano["ram_gb"], 1, comparaveis)
            if rev["p50"] is None:
                continue
            av = avaliar(a["preco"], plano, rev, params)
            if not melhor or av["lucro_p50"] > melhor[2]["lucro_p50"]:
                melhor = (plano, rev, av)
        if not melhor:
            continue
        plano, rev, av = melhor
        itens = " + ".join(f"{n} (R${p:.0f})" for n, p in plano["itens"] if p) or "nenhum"
        rapida = rev["p50"] * (1 - params["desconto_venda_rapida_pct"] / 100)
        linhas.append([hoje, a["fonte"], a["titulo"], a["preco"], a["cidade"], a["uf"], s.cpu, s.ram_gb, s.ram_tipo, s.gpu,
                       "sim" if s.ssd else "não", s.fonte_w, "sim" if s.monitor else "não", itens,
                       av["custo_pecas"], av["fretes"], av["custo_total"],
                       *(round(rev[k]) if rev[k] is not None else None for k in ("p25", "p50", "p75")), rev["n"],
                       av["lucro_p25"], av["lucro_p50"], av["lucro_p75"], av["margem_p50"],
                       round(rapida), "SIM" if av["vale_a_pena"] else "não", a["url"]])
    linhas.sort(key=lambda l: l[22] or -1e9, reverse=True)
    abas = {"Oportunidades": [cab] + linhas, "Pecas": aba_pecas, "Comparaveis": comparaveis, "Sobre a busca": sobre}
    print(f"{len(candidatos)} anúncios, {len(linhas)} avaliados, {sum(1 for l in linhas if l[26]=='SIM')} oportunidades")
    print("Excel:", saida.excel(abas, saida_excel))
    print("Sheets:", saida.google_sheets(abas))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--paginas", type=int, default=None)
    ap.add_argument("--excel", default=f"saida/revenda_{dt.date.today().isoformat()}.xlsx")
    a = ap.parse_args()
    rodar(a.paginas, a.excel)
