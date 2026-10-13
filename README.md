# Comércio mundial da cadeia do níquel e a RCEP (2012–2024)

Dados, pipeline de tratamento e geração das figuras da análise quantitativa do artigo *A cadeia regional do
níquel na transição energética: integração sob a RCEP*, de Ester Gruppelli Kurz, Augusto da Rosa Carioni e
Ailton Manoel Pereira Junior, apresentado no XIV Simpósio de Pós-Graduação em Relações Internacionais
(SimpoRI 2026).

A análise descreve o comércio mundial de nove subposições do Sistema Harmonizado (HS2012), da extração do
minério aos insumos para aço inoxidável e baterias, e compara 2019–2021 com 2022–2024, tomando 2022, ano de
entrada em vigor da Parceria Econômica Regional Abrangente (RCEP), como marco para todos os membros.

## Conteúdo

| Caminho | O que é |
|---|---|
| `outputs/planilha_artigo_niquel_rcep.xlsx` | Planilha para consulta: aba **Dados brutos** (fluxos bilaterais anuais dos nove SH6) e aba **Métricas** (dados de cada figura, da tabela e das séries citadas no texto), com uma aba de leia-me |
| `outputs/figuras/` | Figuras geradas pelo notebook; as do artigo são `figR1` a `figR5` e a Tabela 1, em imagem (`tab01_parceiros_marco_2022`) |
| `outputs/tabelas/` | Tabelas em CSV e os dados de cada figura em `dados_figuras/` |
| `notebooks/analises_artigo.ipynb` | Pipeline completo, passo a passo, com validações (`assert`) ao fim de cada tratamento |
| `src/niquel/` | Módulos: `config` (escopo: códigos, países, RCEP), `extracao`, `indicadores`, `parceiros`, `sintese`, `graficos`, `mapas`, `planilha` |
| `data/processed/` | Extrações do BACI usadas pelo notebook (fluxos bilaterais da cadeia e comércio bilateral total por ano) |
| `data/referencia/` | Tabela de países (ISO3, nome, região) e base cartográfica Natural Earth 1:50m |

## Cadeia analisada

| SH6 | Produto | Etapa |
|---|---|---|
| 260400 | Minérios de níquel e seus concentrados | Minério |
| 750110 | Mates de níquel | Intermediários |
| 750120 | Sínteres de óxidos de níquel e outros intermediários (inclui MHP) | Intermediários |
| 720260 | Ferroníquel (inclui ferro-gusa de níquel, NPI) | Intermediários |
| 750210 | Níquel não ligado, em formas brutas | Níquel refinado |
| 750220 | Ligas de níquel, em formas brutas | Níquel refinado |
| 283324 | Sulfatos de níquel | Químicos de níquel |
| 282540 | Óxidos e hidróxidos de níquel | Químicos de níquel |
| 282735 | Cloreto de níquel | Químicos de níquel |

Aço inoxidável e baterias (códigos em `src/niquel/config.py`) são tratados à parte, como destinos da cadeia.

## Como reproduzir

```bash
pip install -r requirements.txt
jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=1800 notebooks/analises_artigo.ipynb
```

O notebook roda a partir das extrações versionadas em `data/processed/` e regrava figuras, tabelas e planilha.
O parquet bruto do BACI (cerca de 1,35 GB, fora do repositório) só é necessário para refazer as extrações
(`extracao.fluxos_cadeia(forcar=True)` e `extracao.bilateral_total(forcar=True)`); nesse caso, coloque-o em
`data/raw/trade_i_baci_a_12.parquet`, e o notebook passa a conferir as extrações contra ele.

## Fonte dos dados e licenças

- **BACI-CEPII**, versão HS2012, obtida no Observatório de Complexidade Econômica (<https://oec.world>), com
  valores em dólares correntes e quantidades em toneladas. O BACI é distribuído pelo CEPII sob a licença aberta
  Etalab 2.0. Citação: GAULIER, G.; ZIGNAGO, S. *BACI: international trade database at the product-level: the
  1994-2007 version*. Paris: CEPII, 2010 (CEPII Working Paper, n. 2010-23).
- **Natural Earth** (base cartográfica), domínio público.
- **Código** deste repositório: licença MIT (arquivo `LICENSE`).

## Convenções

- Participações calculadas sobre a soma do valor de cada período; nas comparações por membro, média das
  participações anuais. O BACI reconcilia as declarações de exportadores e importadores, de modo que
  exportações e importações mundiais coincidem.
- Comércio entre membros da RCEP: fluxos com exportador e importador membros. Parcela no comércio dos membros:
  (exportações para membros + importações de membros) / (exportações + importações totais dos membros).
- Recomposição dos parceiros: índice de dissimilaridade (½ Σ |Δ parcela|), comparado aos cinco pares de
  triênios consecutivos entre 2012 e 2021.
- Mianmar fica fora das comparações por país.
