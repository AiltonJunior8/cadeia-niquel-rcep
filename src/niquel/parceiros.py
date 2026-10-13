"""Mudança na composição dos parceiros e no volume comercializado pelos membros da RCEP.

Para cada membro com data de vigência, produto e sentido (exportações por destino ou importações por
origem), compara-se a janela simétrica anterior à entrada em vigor com a posterior (mesma convenção de
`indicadores.antes_depois`: o ano de entrada é o primeiro ano posterior).

Medida de mudança de composição: índice de dissimilaridade
    D = ½ Σ_p |s_p,depois − s_p,antes|,
em que s_p é a parcela do parceiro p no comércio do membro naquele produto e período. D vai de 0
(mesma distribuição de parceiros) a 1 (nenhum parceiro em comum) e equivale a 1 menos o índice de
similaridade de Finger-Kreinin.

Referência de variação habitual (placebo): o mesmo D calculado para todas as janelas de igual
comprimento inteiramente anteriores à vigência (por exemplo, para quem entrou em 2022, 2012–2014 vs.
2015–2017 até 2016–2018 vs. 2019–2021). Um D real acima de todos os placebos indica uma recomposição
maior do que a observada entre quaisquer janelas anteriores; não identifica causa.
"""
import numpy as np
import pandas as pd

from . import config as cfg
from . import indicadores as ind

LIMIAR_RELEVANCIA_USD = 10e6  # comércio médio anual mínimo (antes ou depois) para o par membro × produto entrar nas figuras


def entrada(unica=False):
    """Ano de entrada em vigor por membro; `unica=True` usa `config.ANO_RCEP` (2022) para todos, convenção
    do texto do artigo."""
    return {c: (cfg.ANO_RCEP if unica else d.year) for c, d in cfg.RCEP_VIGENCIA.items() if d is not None}


def janelas(ano_entrada):
    """Janela simétrica: (anos antes, anos depois)."""
    depois = list(range(ano_entrada, cfg.ANOS[-1] + 1))
    antes = list(range(ano_entrada - len(depois), ano_entrada))
    return antes, depois


def janelas_placebo(ano_entrada):
    """Pares de janelas de mesmo comprimento, inteiramente anteriores à vigência."""
    n = cfg.ANOS[-1] - ano_entrada + 1
    return [(list(range(t - n, t)), list(range(t, t + n)))
            for t in range(cfg.ANOS[0] + n, ano_entrada - n + 1)]


def fluxos_membros(df, nivel, lado):
    """Fluxos dos membros (com data de vigência) com seus parceiros: colunas ano, produto, membro,
    parceiro, grupo do parceiro, valor, qtd. `lado="exp"`: membro exportador, parceiro = destino."""
    m, p = ("exp", "imp") if lado == "exp" else ("imp", "exp")
    d = df[df[m].isin(entrada())]
    d = d.groupby(["ano", nivel, m, p], as_index=False)[["valor", "qtd"]].sum(min_count=1)
    d = d.rename(columns={m: "membro", p: "parceiro"})
    d["grupo_parceiro"] = d["parceiro"].map(ind.grupo_rcep)
    return d


def _somas(d, nivel, anos):
    return d[d["ano"].isin(anos)].groupby([nivel, "parceiro"])["valor"].sum()


def dissimilaridade(soma_antes, soma_depois, nivel):
    """D por produto a partir das somas por (produto, parceiro) de cada janela. Produtos sem comércio
    em uma das janelas ficam fora (D indefinido)."""
    tot_a = soma_antes.groupby(level=0).sum()
    tot_d = soma_depois.groupby(level=0).sum()
    validos = tot_a[tot_a > 0].index.intersection(tot_d[tot_d > 0].index)
    sa = soma_antes[soma_antes.index.get_level_values(0).isin(validos)]
    sd = soma_depois[soma_depois.index.get_level_values(0).isin(validos)]
    sa = sa / sa.groupby(level=0).transform("sum")
    sd = sd / sd.groupby(level=0).transform("sum")
    j = pd.concat([sa, sd], axis=1, keys=["antes", "depois"]).fillna(0)
    return (0.5 * (j["depois"] - j["antes"]).abs()).groupby(level=0).sum().rename_axis(nivel)


def composicao(df, nivel, lado, unica=False):
    """Parcela de cada parceiro no comércio de cada membro × produto, antes e depois (janela simétrica)."""
    d = fluxos_membros(df, nivel, lado)
    partes = []
    for membro, ano in entrada(unica).items():
        a, b = janelas(ano)
        dm = d[d["membro"] == membro]
        s = pd.concat([_somas(dm, nivel, a), _somas(dm, nivel, b)], axis=1, keys=["valor_antes", "valor_depois"]).fillna(0)
        for per in ("antes", "depois"):
            s[f"share_{per}"] = s[f"valor_{per}"] / s.groupby(level=0)[f"valor_{per}"].transform("sum")
        s = s.reset_index().assign(membro=membro, lado=lado)
        partes.append(s)
    out = pd.concat(partes, ignore_index=True)
    out["grupo_parceiro"] = out["parceiro"].map(ind.grupo_rcep)
    out["var_pp"] = (out["share_depois"].fillna(0) - out["share_antes"].fillna(0)) * 100
    return out


def resumo(df, nivel, lado, unica=False):
    """Uma linha por membro × produto: volume antes/depois (média anual de valor e, no nível SH6,
    quantidade), variação do mundo no mesmo produto e janelas, número de parceiros, HHI dos
    parceiros, principal parceiro, parcelas de China/ASEAN/RCEP, D real e placebos."""
    d = fluxos_membros(df, nivel, lado)
    mundo = df.groupby(["ano", nivel])[["valor", "qtd"]].sum()
    linhas = []
    for membro, ano in entrada(unica).items():
        a, b = janelas(ano)
        dm = d[d["membro"] == membro]
        sa, sb = _somas(dm, nivel, a), _somas(dm, nivel, b)
        D = dissimilaridade(sa, sb, nivel)
        plac = pd.concat({i: dissimilaridade(_somas(dm, nivel, pa), _somas(dm, nivel, pb), nivel)
                          for i, (pa, pb) in enumerate(janelas_placebo(ano))}, axis=1)
        vol = dm.groupby([nivel, "ano"])[["valor", "qtd"]].sum(min_count=1)
        for prod in sorted(dm[nivel].unique()):
            v = vol.loc[prod].reindex(cfg.ANOS)
            wa, wb = mundo.xs(prod, level=nivel).reindex(a), mundo.xs(prod, level=nivel).reindex(b)
            r = {"membro": membro, nivel: prod, "lado": lado, "ano_entrada": ano,
                 "anos_antes": f"{a[0]}–{a[-1]}", "anos_depois": f"{b[0]}–{b[-1]}",
                 "valor_medio_antes": v.loc[a, "valor"].fillna(0).mean(),
                 "valor_medio_depois": v.loc[b, "valor"].fillna(0).mean(),
                 "var_valor_mundo_pct": (wb["valor"].mean() / wa["valor"].mean() - 1) * 100}
            if nivel == "sh6":
                r["qtd_media_antes"] = v.loc[a, "qtd"].fillna(0).mean()
                r["qtd_media_depois"] = v.loc[b, "qtd"].fillna(0).mean()
                r["var_qtd_mundo_pct"] = (wb["qtd"].mean() / wa["qtd"].mean() - 1) * 100
            for per, s in (("antes", sa), ("depois", sb)):
                s = s.loc[prod] if prod in s.index.get_level_values(0) else pd.Series(dtype=float)
                s = s[s > 0]
                sh = s / s.sum() if len(s) else s
                r[f"n_parceiros_{per}"] = len(s)
                r[f"hhi_parceiros_{per}"] = (sh ** 2).sum() * 1e4 if len(s) else np.nan
                r[f"principal_{per}"] = sh.idxmax() if len(s) else ""
                r[f"share_principal_{per}"] = sh.max() if len(s) else np.nan
                grupos = sh.groupby(sh.index.map(ind.grupo_rcep)).sum() if len(s) else pd.Series(dtype=float)
                r[f"share_china_{per}"] = grupos.get("China", 0.0) if len(s) else np.nan
                r[f"share_asean_{per}"] = grupos.get("ASEAN", 0.0) if len(s) else np.nan
                r[f"share_rcep_{per}"] = (grupos.get("China", 0) + grupos.get("ASEAN", 0) + grupos.get("Demais RCEP", 0)) if len(s) else np.nan
            r["indice_mudanca"] = D.get(prod, np.nan)
            p = plac.loc[prod].dropna() if prod in plac.index else pd.Series(dtype=float)
            r["placebo_n"] = len(p)
            r["placebo_media"] = p.mean() if len(p) else np.nan
            r["placebo_max"] = p.max() if len(p) else np.nan
            r["acima_placebos"] = bool(len(p) and r["indice_mudanca"] > p.max())
            linhas.append(r)
    out = pd.DataFrame(linhas)
    out["var_valor_pct"] = (out["valor_medio_depois"] / out["valor_medio_antes"].replace(0, np.nan) - 1) * 100
    if nivel == "sh6":
        out["var_qtd_pct"] = (out["qtd_media_depois"] / out["qtd_media_antes"].replace(0, np.nan) - 1) * 100
    out["relevante"] = out[["valor_medio_antes", "valor_medio_depois"]].max(axis=1) >= LIMIAR_RELEVANCIA_USD
    return out
