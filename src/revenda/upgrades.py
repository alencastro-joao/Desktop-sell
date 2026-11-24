"""Gera combinações de upgrade para um PC e calcula custo, revenda e retorno."""
from itertools import product
from . import config
from .parser import Specs

def _preco(peca, precos, condicao):
    p = precos.get(peca["nome"], {}).get(condicao) if precos else None
    return p or peca.get(condicao) or peca.get("novo") or peca.get("usado")

def opcoes(specs: Specs, precos: dict, condicao="usado"):
    """Retorna lista de planos [{itens:[(nome,preco)], gpu_resultante, ram_resultante}]."""
    gpus = [None]
    if not specs.gpu:
        limite = specs.cpu_tier + config.GARGALO_FOLGA
        gpus += [g for g in config.GPUS if g["tier"] <= limite] or [config.GPUS[0]]
    ram_opts = [0]
    if specs.ram_gb is not None and specs.ram_gb < 16 and specs.ram_tipo in config.RAM:
        ram_opts.append(8)
    ssd_opts = [False] if specs.ssd else [False, True]
    planos = []
    for gpu, ram_add, ssd in product(gpus, ram_opts, ssd_opts):
        itens = []
        if gpu:
            itens.append((gpu["nome"], _preco(gpu, precos, condicao)))
            if (specs.fonte_w or 0) < gpu["fonte_min"]:
                itens.append((config.FONTE["nome"], _preco(config.FONTE, precos, condicao)))
        if ram_add:
            r = config.RAM[specs.ram_tipo]["8gb"]
            itens.append((f"RAM {specs.ram_tipo} 8GB", r.get(condicao) or r["novo"]))
        if ssd:
            itens.append((config.SSD["nome"], _preco(config.SSD, precos, condicao)))
        if not {"teclado", "mouse"} <= set(specs.extras):
            itens.append((config.KIT_PERIFERICOS["nome"], _preco(config.KIT_PERIFERICOS, precos, "novo")))
        if "windows" not in specs.extras:
            itens.append((config.WINDOWS["nome"], config.WINDOWS["novo"]))
        planos.append({
            "itens": itens,
            "gpu": gpu["nome"] if gpu else specs.gpu,
            "ram_gb": (specs.ram_gb or 0) + ram_add,
            "ssd": specs.ssd or ssd,
        })
    return planos

def avaliar(preco_compra, plano, revenda, params):
    """revenda: dict com p25, p50, p75 de anúncios comparáveis à configuração final."""
    custo_pecas = sum(p for _, p in plano["itens"] if p)
    fretes = params["frete_compra_rs"] + params["frete_pecas_rs"] * len(plano["itens"])
    custo = preco_compra + custo_pecas + fretes
    taxa = params["taxa_venda_pct"] / 100
    out = {"custo_pecas": custo_pecas, "fretes": fretes, "custo_total": custo}
    for k in ("p25", "p50", "p75"):
        v = revenda.get(k)
        if v is None:
            out[f"lucro_{k}"] = out[f"margem_{k}"] = None
            continue
        liquido = v * (1 - taxa)
        out[f"lucro_{k}"] = round(liquido - custo, 2)
        out[f"margem_{k}"] = round(100 * (liquido - custo) / custo, 1)
    l = out.get("lucro_p50")
    out["vale_a_pena"] = bool(l is not None and l >= params["lucro_minimo_rs"]
                              and out["margem_p50"] >= params["margem_minima_pct"])
    return out
