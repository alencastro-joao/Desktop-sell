"""Parâmetros padrão. Os valores da aba 'Parametros' da planilha sobrescrevem estes."""
PARAMS = {
    "margem_minima_pct": 20.0,      # % sobre custo total
    "lucro_minimo_rs": 300.0,
    "frete_compra_rs": 80.0,        # estimativa se não houver frete no anúncio
    "frete_pecas_rs": 40.0,
    "desconto_venda_rapida_pct": 10.0,
    "taxa_venda_pct": 0.0,          # ex.: tarifa ML ~ 12-16% se vender lá
    "max_paginas_busca": 5,
}

# Catálogo de upgrades: preço é atualizado pela busca de peças; estes são fallbacks.
# 'tier' é ganho aproximado de desempenho para escolher a GPU certa por CPU.
GPUS = [
    {"nome": "RX 580 8GB", "busca": "rx 580 8gb", "tier": 30, "tdp": 185, "fonte_min": 450, "usado": 450, "novo": 700},
    {"nome": "GTX 1660 Super", "busca": "gtx 1660 super", "tier": 40, "tdp": 125, "fonte_min": 450, "usado": 750, "novo": 1100},
    {"nome": "RX 5700 XT", "busca": "rx 5700 xt", "tier": 50, "tdp": 225, "fonte_min": 600, "usado": 900, "novo": None},
    {"nome": "RX 6600", "busca": "rx 6600", "tier": 55, "tdp": 132, "fonte_min": 450, "usado": 950, "novo": 1300},
]
RAM = {"DDR3": {"8gb": {"usado": 60, "novo": 90}}, "DDR4": {"8gb": {"usado": 90, "novo": 140}}, "DDR5": {"8gb": {"usado": 150, "novo": 200}}}
SSD = {"nome": "SSD 240GB", "busca": "ssd 240gb", "usado": 80, "novo": 110}
FONTE = {"nome": "Fonte 500W 80 Plus", "busca": "fonte 500w 80 plus", "usado": 150, "novo": 250}
KIT_PERIFERICOS = {"nome": "Kit gamer teclado+mouse+headset", "busca": "kit gamer teclado mouse headset", "novo": 150}
WINDOWS = {"nome": "Licença Windows", "novo": 50}

# Evita gargalo: GPU com tier muito acima da CPU não vale o custo.
GARGALO_FOLGA = 0
