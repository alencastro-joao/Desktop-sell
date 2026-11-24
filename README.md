# Desktop-sell

Busca PCs usados à venda (Mercado Livre e OLX), sugere o melhor upgrade (GPU, RAM, fonte, SSD,
periféricos, Windows), estima a revenda pelos percentis de anúncios parecidos e grava tudo em
Excel e Google Sheets.

## Como roda
- **Todo dia às 07:00 (Brasília)** pelo GitHub Actions (`.github/workflows/diario.yml`).
- **Sob demanda**: aba *Actions* → *Busca diária de PCs* → *Run workflow*.
- O Excel de cada execução fica em *Actions* → execução → *Artifacts* → `planilha-excel`.

## Planilha
| Aba | Conteúdo |
|---|---|
| Oportunidades | cada PC, peças identificadas, melhor upgrade, custo total, revenda P25/mediana/P75, lucro, margem, "vale a pena" |
| Pecas | mediana de preço de cada peça, nova e usada |
| Comparaveis | anúncios usados para estimar a revenda |
| Parametros | margem mínima, lucro mínimo, fretes, desconto de venda rápida, taxa de venda (só no Google Sheets; edite lá) |

## Segredos (Settings → Secrets and variables → Actions)
| Nome | Para quê |
|---|---|
| `ML_CLIENT_ID`, `ML_CLIENT_SECRET` | app em developers.mercadolivre.com.br (a busca do ML exige token) |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | JSON da conta de serviço do Google com acesso à planilha |
| `SHEET_ID` | opcional; o padrão já é a planilha "Revenda de PCs" |

Sem os segredos do Google, só o Excel é gerado.

## Rodar localmente
```bash
pip install -r requirements.txt
PYTHONPATH=src python -m revenda.main --paginas 1
```

## Regras
- Só lê os sites; nada publica nem edita anúncio.
- OLX: acesso normal, 4 s entre páginas. Se bloquear, a execução segue só com o Mercado Livre.
