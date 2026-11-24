"""Extrai especificações (CPU, RAM, GPU, armazenamento, fonte) do título/descrição de anúncios."""
import re
from dataclasses import dataclass, field, asdict

@dataclass
class Specs:
    cpu: str | None = None
    cpu_tier: int = 0          # pontuação aproximada de desempenho (0-100)
    ram_gb: int | None = None
    ram_tipo: str | None = None
    gpu: str | None = None
    ssd: bool = False
    hd: bool = False
    fonte_w: int | None = None
    monitor: bool = False
    extras: list = field(default_factory=list)

    def dict(self):
        return asdict(self)

INTEL_RE = re.compile(r"\bi([3579])[\s\-]?(\d{4,5})?[a-z]?\b", re.I)
INTEL_GEN_RE = re.compile(r"\bi([3579])\D{0,15}?(\d{1,2})\s*[ªaº°]?\s*(?:gera[cç][aã]o|gen|ger)\b", re.I)
RYZEN_RE = re.compile(r"\bryzen\s*([3579])\s*(\d{4})?", re.I)
RAM_RE = re.compile(r"(\d{1,3})\s*gb\s*(?:de\s*)?(?:ram|mem[oó]ria|ddr[345])", re.I)
RAM_TIPO_RE = re.compile(r"\bddr([345])\b", re.I)
GPU_RE = re.compile(r"\b(rtx\s*\d{4}(?:\s*ti|\s*super)?|gtx\s*\d{3,4}(?:\s*ti|\s*super)?|rx\s*\d{3,4}(?:\s*xt)?|gt\s*\d{3,4})\b", re.I)
FONTE_RE = re.compile(r"\bfonte\D{0,20}?(\d{3,4})\s*w|(\d{3,4})\s*w\b", re.I)

def _intel_tier(serie: int, gen: int) -> int:
    base = {3: 10, 5: 20, 7: 28, 9: 34}[serie]
    return min(100, base + gen * 5)

def _ryzen_tier(serie: int, gen: int) -> int:
    base = {3: 25, 5: 38, 7: 46, 9: 52}[serie]
    return min(100, base + gen * 6)

def parse(texto: str) -> Specs:
    t = texto.lower()
    s = Specs()
    if m := RYZEN_RE.search(t):
        serie = int(m.group(1)); modelo = m.group(2)
        gen = int(modelo[0]) if modelo else 2
        s.cpu = f"Ryzen {serie} {modelo or ''}".strip(); s.cpu_tier = _ryzen_tier(serie, gen)
    elif m := INTEL_GEN_RE.search(t):
        serie, gen = int(m.group(1)), int(m.group(2))
        s.cpu = f"i{serie} {gen}ª ger"; s.cpu_tier = _intel_tier(serie, gen)
    elif m := INTEL_RE.search(t):
        serie = int(m.group(1)); modelo = m.group(2)
        gen = (int(modelo[:2]) if len(modelo) == 5 else int(modelo[0])) if modelo else 4
        s.cpu = f"i{serie}-{modelo}" if modelo else f"i{serie}"; s.cpu_tier = _intel_tier(serie, gen)
    if m := RAM_RE.search(t):
        s.ram_gb = int(m.group(1))
    if m := RAM_TIPO_RE.search(t):
        s.ram_tipo = f"DDR{m.group(1)}"
    if m := GPU_RE.search(t):
        s.gpu = re.sub(r"\s+", " ", m.group(1)).upper()
    s.ssd = "ssd" in t or "nvme" in t
    s.hd = bool(re.search(r"\bhd\b|\bhdd\b|\d\s*tb", t))
    if m := FONTE_RE.search(t):
        w = int(m.group(1) or m.group(2))
        if 200 <= w <= 1600:
            s.fonte_w = w
    s.monitor = "monitor" in t
    for k in ("teclado", "mouse", "headset", "windows"):
        if k in t:
            s.extras.append(k)
    return s
