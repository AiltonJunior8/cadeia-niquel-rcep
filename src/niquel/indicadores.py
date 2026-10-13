"""Indicadores de comércio calculados sobre os fluxos bilaterais da cadeia.

Todas as funções recebem o DataFrame de `preparar()` e um `nivel` de agregação de produto:
`"sh6"` (subposição) ou `"elo"` (elo da cadeia definido em `config.CADEIA`). Como o BACI reconcilia
exportações e importações num único fluxo, o comércio mundial de um produto é a soma de todos os fluxos
bilaterais, e as participações de exportadores e de importadores partem do mesmo denominador.
"""
import numpy as np
import pandas as pd

from . import config as cfg

GRUPOS = ["China", "ASEAN", "Demais RCEP", "Resto do mundo"]


def grupo_rcep(iso3):
    """Classifica o país em China, ASEAN, demais membros da RCEP ou resto do mundo."""
    if iso3 == "chn":
        return "China"
    if iso3 in cfg.ASEAN:
        return "ASEAN"
    if iso3 in cfg.RCEP:
        return "Demais RCEP"
    return "Resto do mundo"


def preparar(fluxos, paises):
    """Acrescenta elo, rótulo do produto, macrorregião e grupo RCEP de exportador e importador."""
    df = fluxos.copy()
    df["elo"] = df["sh6"].map(cfg.SH6_ELO)
    df["produto"] = df["sh6"].map(cfg.SH6_ROTULO)
    regiao = paises.set_index("iso3")["macrorregiao"]
    for lado in ("exp", "imp"):
        df[f"reg_{lado}"] = df[lado].map(regiao)
        df[f"grupo_{lado}"] = df[lado].map(grupo_rcep)
    return df


_NOMES_BASE = None


def nome(iso3):
    """Nome do país para figuras: português quando definido em `config.NOMES_PT`, senão o da base."""
    global _NOMES_BASE
    if _NOMES_BASE is None:
        arq = cfg.DIR_REF / "paises.csv"
        _NOMES_BASE = (pd.read_csv(arq, keep_default_na=False).set_index("iso3")["nome_oec"].to_dict()
                       if arq.exists() else {})
    return cfg.NOMES_PT.get(iso3) or _NOMES_BASE.get(iso3) or iso3


def rotulo(codigo, nivel):
    return cfg.SH6_ROTULO[codigo] if nivel == "sh6" else codigo


# --------------------------------------------------------------------------------------------------
# Volumes
# --------------------------------------------------------------------------------------------------
def totais(df, nivel="sh6"):
    """Valor (USD), quantidade (t), número de fluxos, cobertura da quantidade e valor unitário por ano."""
    chave = ["ano", nivel]
    out = df.groupby(chave).agg(valor=("valor", "sum"), qtd=("qtd", "sum"), n_fluxos=("valor", "size"))
    com_qtd = df[df["qtd"].notna()].groupby(chave)["valor"].sum().reindex(out.index).fillna(0)
    out["cobertura_qtd"] = com_qtd / out["valor"]          # parcela do valor com quantidade informada
    out["valor_unit"] = com_qtd / out["qtd"].replace(0, np.nan)  # USD por tonelada
    return out.reset_index()


# --------------------------------------------------------------------------------------------------
# Participações
# --------------------------------------------------------------------------------------------------
def participacoes(df, lado="exp", nivel="sh6", por="pais"):
    """Participação de cada país (`por="pais"`), macrorregião (`"regiao"`) ou grupo (`"grupo"`)
    no comércio mundial do produto, pelo lado exportador (`"exp"`) ou importador (`"imp"`)."""
    col = {"pais": lado, "regiao": f"reg_{lado}", "grupo": f"grupo_{lado}"}[por]
    g = df.groupby(["ano", nivel, col], as_index=False)["valor"].sum()
    g["share"] = g["valor"] / g.groupby(["ano", nivel])["valor"].transform("sum")
    return g.rename(columns={col: por})


def principais(part, codigo, nivel="sh6", n=5, por="pais"):
    """Tabela larga (ano × principais + Outros) de participações. Os principais são os `n` maiores
    pelo valor acumulado no período inteiro, para que a composição seja estável entre os anos."""
    p = part[part[nivel] == codigo]
    top = p.groupby(por)["valor"].sum().nlargest(n).index.tolist()
    p = p.assign(grupo=np.where(p[por].isin(top), p[por], "Outros"))
    w = p.pivot_table(index="ano", columns="grupo", values="share", aggfunc="sum").fillna(0)
    cols = top + (["Outros"] if "Outros" in w.columns else [])
    return w.reindex(index=cfg.ANOS, columns=cols).fillna(0)


def concentracao(part, nivel="sh6"):
    """Índice Herfindahl-Hirschman (0–10.000), CR1 e CR4 por ano e produto."""
    def f(s):
        s = s.sort_values(ascending=False)
        return pd.Series({"hhi": (s ** 2).sum() * 1e4, "cr1": s.iloc[:1].sum(), "cr4": s.iloc[:4].sum()})
    return part.groupby(["ano", nivel])["share"].apply(f).unstack().reset_index()


# --------------------------------------------------------------------------------------------------
# RCEP
# --------------------------------------------------------------------------------------------------
def painel_rcep(part, nivel="sh6"):
    """Painel balanceado ano × produto × membro da RCEP, com zero onde o membro não comerciou."""
    idx = pd.MultiIndex.from_product([cfg.ANOS, sorted(part[nivel].unique()), cfg.RCEP],
                                     names=["ano", nivel, "pais"])
    return (part.set_index(["ano", nivel, "pais"])[["valor", "share"]]
            .reindex(idx, fill_value=0).reset_index())


def antes_depois(part, nivel="sh6", janela="completa"):
    """Participação média de cada membro antes e depois da entrada em vigor da RCEP para ele.

    O ano de entrada conta como primeiro ano do período posterior. `janela="completa"` usa todos os
    anos anteriores disponíveis; `janela="simetrica"` usa, antes, o mesmo número de anos do período
    posterior (3 anos para quem entrou em 2022; 2 para Indonésia e Filipinas). Mianmar fica de fora.
    """
    p = painel_rcep(part, nivel)
    entrada = {c: d.year for c, d in cfg.RCEP_VIGENCIA.items() if d is not None}
    p = p[p["pais"].isin(entrada)].copy()
    p["ano_entrada"] = p["pais"].map(entrada)
    p["periodo"] = np.where(p["ano"] >= p["ano_entrada"], "depois", "antes")
    if janela == "simetrica":
        n_depois = cfg.ANOS[-1] - p["ano_entrada"] + 1
        p = p[p["ano"] >= p["ano_entrada"] - n_depois]
    r = p.pivot_table(index=[nivel, "pais", "ano_entrada"], columns="periodo",
                      values=["share", "valor"], aggfunc="mean")
    r.columns = [f"{v}_{per}" for v, per in r.columns]
    anos = p.groupby(["pais", "periodo"])["ano"].agg(["min", "max", "nunique"]).unstack()
    r = r.reset_index()
    r["var_pp"] = (r["share_depois"] - r["share_antes"]) * 100
    r["anos_antes"] = r["pais"].map(lambda c: f"{anos.loc[c, ('min', 'antes')]}–{anos.loc[c, ('max', 'antes')]}")
    r["anos_depois"] = r["pais"].map(lambda c: f"{anos.loc[c, ('min', 'depois')]}–{anos.loc[c, ('max', 'depois')]}")
    r["janela"] = janela
    return r


def matriz_grupos(df, nivel, codigo, anos):
    """Participação de cada par (grupo exportador → grupo importador) no comércio mundial do produto,
    somando os anos indicados."""
    p = df[(df[nivel] == codigo) & df["ano"].isin(anos)]
    m = p.pivot_table(index="grupo_exp", columns="grupo_imp", values="valor", aggfunc="sum")
    m = m.reindex(index=GRUPOS, columns=GRUPOS).fillna(0)
    return m / m.values.sum()


def intra_rcep(df, nivel="sh6"):
    """Por ano e produto: parcela do comércio mundial entre membros da RCEP e parcela das exportações
    dos membros que se destina a outros membros."""
    d = df.assign(exp_rcep=df["exp"].isin(cfg.RCEP), imp_rcep=df["imp"].isin(cfg.RCEP))
    d["intra"] = d["exp_rcep"] & d["imp_rcep"]
    g = d.groupby(["ano", nivel])
    out = pd.DataFrame({
        "valor_mundo": g["valor"].sum(),
        "valor_intra": d[d["intra"]].groupby(["ano", nivel])["valor"].sum(),
        "valor_exp_rcep": d[d["exp_rcep"]].groupby(["ano", nivel])["valor"].sum(),
    }).fillna(0)
    out["intra_no_mundo"] = out["valor_intra"] / out["valor_mundo"]
    out["intra_nas_exp_rcep"] = out["valor_intra"] / out["valor_exp_rcep"].replace(0, np.nan)
    return out.reset_index()


# --------------------------------------------------------------------------------------------------
# Validações (levantam AssertionError com mensagem; devolvem um resumo quando passam)
# --------------------------------------------------------------------------------------------------
def checar_shares(part, nivel, tol=1e-9):
    s = part.groupby(["ano", nivel])["share"].sum()
    ruins = s[(s - 1).abs() > tol]
    assert ruins.empty, f"Participações não somam 1 em {len(ruins)} combinações ano×produto:\n{ruins.head()}"
    return f"OK: {len(s)} combinações ano×{nivel}, soma das participações entre {s.min():.12f} e {s.max():.12f}"


def checar_total(parte, todo, chave, col="valor", tol=1e-6):
    """Confere que a soma de `parte` por `chave` reproduz `todo` (diferença relativa ≤ tol)."""
    a = parte.groupby(chave)[col].sum()
    b = todo.groupby(chave)[col].sum()
    dif = ((a - b).abs() / b).reindex(b.index)
    assert dif.notna().all() and (dif <= tol).all(), f"Totais divergentes:\n{dif[dif > tol].head()}"
    return f"OK: {len(b)} totais conferidos, maior diferença relativa {dif.max():.2e}"
