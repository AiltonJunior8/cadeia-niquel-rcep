"""Síntese da cadeia mercantil destacada (`config.ELOS_DESTACADOS`) para o resumo: três figuras e as
tabelas que as sustentam, nos recortes mundo, Ásia e RCEP.

- Figura R1: valor anual do comércio mundial por produto e participação da Ásia e da RCEP;
- Figura R2: principais exportadores e importadores do total da cadeia, 2019–2021 e 2022–2024;
- Figura R3: participação de Ásia, RCEP e principais países em cada produto, 2022–2024, com a
  variação em pontos percentuais desde 2019–2021.

As legendas (título, fonte e nota com os SH6) ficam em `outputs/figuras/legendas_resumo.md`.
"""
import textwrap

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from . import config as cfg
from . import graficos as gr
from . import indicadores as ind

PERIODOS = {"2019–2021": [2019, 2020, 2021], "2022–2024": [2022, 2023, 2024]}
COR_GRUPO = {"China": "#d62728", "ASEAN": "#ff7f0e", "Demais RCEP": "#8c564b", "Resto do mundo": "#1f77b4"}


def sh6_destacados():
    return [sh for elo in cfg.ELOS_DESTACADOS for sh in cfg.CADEIA[elo]]


def recorte(df):
    """Fluxos da cadeia destacada, com marcação de Ásia e RCEP para exportador e importador."""
    d = df[df["elo"].isin(cfg.ELOS_DESTACADOS)].copy()
    for lado in ("exp", "imp"):
        d[f"asia_{lado}"] = d[f"reg_{lado}"].isin(cfg.ASIA)
        d[f"rcep_{lado}"] = d[lado].isin(cfg.RCEP)
    return d


# --------------------------------------------------------------------------------------------------
# Tabelas
# --------------------------------------------------------------------------------------------------
def agregado_anual(d):
    """Por ano: valor mundial da cadeia e, para Ásia e RCEP, exportações, importações e comércio
    interno ao recorte, em valor e como parcela do total mundial."""
    g = d.groupby("ano")
    out = pd.DataFrame({"valor_mundo": g["valor"].sum()})
    for nome in ("asia", "rcep"):
        out[f"exp_{nome}"] = d[d[f"{nome}_exp"]].groupby("ano")["valor"].sum()
        out[f"imp_{nome}"] = d[d[f"{nome}_imp"]].groupby("ano")["valor"].sum()
        out[f"intra_{nome}"] = d[d[f"{nome}_exp"] & d[f"{nome}_imp"]].groupby("ano")["valor"].sum()
        for col in ("exp", "imp", "intra"):
            out[f"share_{col}_{nome}"] = out[f"{col}_{nome}"] / out["valor_mundo"]
    return out.fillna(0).reset_index()


def participacao_produtos(d):
    """Valor anual e parcela de cada SH6 no total da cadeia."""
    p = d.groupby(["ano", "sh6"], as_index=False)["valor"].sum()
    p["share"] = p["valor"] / p.groupby("ano")["valor"].transform("sum")
    p["produto"] = p["sh6"].map(cfg.ROTULO_CURTO)
    return p


def participacao_paises_total(d):
    """Parcela de cada país nas exportações e importações mundiais do total da cadeia, por período."""
    linhas = []
    for per, anos in PERIODOS.items():
        x = d[d["ano"].isin(anos)]
        for lado in ("exp", "imp"):
            s = x.groupby(lado)["valor"].sum()
            linhas.append(pd.DataFrame({"pais": s.index, "lado": lado, "periodo": per,
                                        "valor": s.values, "share": (s / s.sum()).values}))
    out = pd.concat(linhas, ignore_index=True)
    out["pais_nome"] = out["pais"].map(ind.nome)
    out["grupo"] = out["pais"].map(ind.grupo_rcep)
    return out


def participacao_paises_produto(d):
    """Parcela de cada país, da Ásia e da RCEP nas exportações e importações mundiais de cada SH6 e do
    total da cadeia, por período (soma dos valores do período sobre o total do período)."""
    linhas = []
    for per, anos in PERIODOS.items():
        x = d[d["ano"].isin(anos)]
        for lado in ("exp", "imp"):
            for prod, xp in [(sh, x[x["sh6"] == sh]) for sh in sh6_destacados()] + [("Total", x)]:
                tot = xp["valor"].sum()
                s = xp.groupby(lado)["valor"].sum() / tot
                blocos = pd.Series({"Ásia": xp.loc[xp[f"asia_{lado}"], "valor"].sum() / tot,
                                    "RCEP": xp.loc[xp[f"rcep_{lado}"], "valor"].sum() / tot})
                s = pd.concat([blocos, s])
                linhas.append(pd.DataFrame({"pais": s.index, "sh6": prod, "lado": lado, "periodo": per, "share": s.values}))
    out = pd.concat(linhas, ignore_index=True)
    w = out.pivot_table(index=["pais", "sh6", "lado"], columns="periodo", values="share").fillna(0)
    w["var_pp"] = (w["2022–2024"] - w["2019–2021"]) * 100
    w = w.reset_index()
    w["pais_nome"] = w["pais"].map(lambda c: c if c in ("Ásia", "RCEP") else ind.nome(c))
    return w


# --------------------------------------------------------------------------------------------------
# Figuras
# --------------------------------------------------------------------------------------------------
# Tipos de fluxo do painel b da figura R1, de baixo para cima; os dois primeiros formam o comércio
# interno à RCEP (linha preta)
TIPOS_FLUXO = {
    "ASEAN → China": "#e6550d",
    "outros fluxos entre membros da RCEP": "#fdae6b",
    "RCEP → resto do mundo": "#8c6d31",
    "resto do mundo → RCEP": "#6baed6",
    "fora da RCEP": "#d9d9d9",
}


def fluxos_por_tipo(d):
    """Valor anual do comércio da cadeia por tipo de fluxo (`TIPOS_FLUXO`), segundo o pertencimento do
    exportador e do importador à RCEP, com o fluxo ASEAN → China separado."""
    tipo = np.select(
        [(d["exp"].isin(cfg.ASEAN)) & (d["imp"] == "chn"),
         d["rcep_exp"] & d["rcep_imp"], d["rcep_exp"], d["rcep_imp"]],
        list(TIPOS_FLUXO)[:4], default="fora da RCEP")
    return d.assign(tipo=tipo).pivot_table(index="ano", columns="tipo", values="valor", aggfunc="sum").fillna(0)


def figura_r1(prod, tipos, nome="figR1_cadeia_mundo_asia_rcep"):
    produtos = sh6_destacados()
    w = prod.pivot(index="ano", columns="sh6", values="valor").reindex(columns=produtos).fillna(0) / 1e9
    cores = plt.get_cmap("tab10").colors
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.2), gridspec_kw={"width_ratios": [1.25, 1]})
    base = np.zeros(len(w))
    for sh, cor in zip(produtos, cores):
        ax1.bar(w.index, w[sh], bottom=base, color=cor, width=0.8, label=f"{cfg.ROTULO_CURTO[sh]} ({sh})")
        base += w[sh].values
    for x, y in zip(w.index, base):
        ax1.text(x, y + 0.4, gr._num(y, 0), ha="center", fontsize=7)
    ax1.set_ylabel("US$ bilhões correntes")
    ax1.set_title("(a) Comércio mundial da cadeia, por produto")
    ax1.set_xticks(cfg.ANOS[::2])
    ax1.axvline(cfg.ANO_RCEP - 0.5, color="k", lw=0.8, ls="--")
    ax1.legend(fontsize=7, loc="upper left", ncol=2)
    ax1.grid(axis="x", visible=False)

    t = tipos.reindex(columns=list(TIPOS_FLUXO)).fillna(0)
    t = t.div(t.sum(axis=1), axis=0)
    ax2.stackplot(t.index, *[t[c] for c in TIPOS_FLUXO], colors=list(TIPOS_FLUXO.values()),
                  labels=list(TIPOS_FLUXO), edgecolor="white", linewidth=0.4)
    intra = t[list(TIPOS_FLUXO)[:2]].sum(axis=1)
    ax2.plot(t.index, intra, color="k", lw=1.2)
    for ano in (2012, 2018, 2021, 2024):
        ax2.annotate(f"{intra[ano] * 100:.1f}%".replace(".", ","), (ano, intra[ano]), xytext=(0, 5),
                     textcoords="offset points", ha="left" if ano == cfg.ANOS[0] else ("right" if ano == cfg.ANOS[-1] else "center"),
                     fontsize=7, fontweight="bold", bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.8))
    ax2.yaxis.set_major_formatter(gr.fmt_pct)
    ax2.set_ylim(0, 1)
    ax2.set_xlim(t.index.min(), t.index.max())
    ax2.set_xticks(cfg.ANOS[::2])
    ax2.axvline(cfg.ANO_RCEP - 0.5, color="k", lw=0.8, ls="--")
    ax2.grid(False)
    ax2.set_title("(b) Comércio mundial da cadeia, por origem e destino")
    alcas, rots = ax2.get_legend_handles_labels()
    ax2.legend(alcas[::-1], rots[::-1], fontsize=7, loc="upper left", bbox_to_anchor=(1.01, 1))
    fig.tight_layout()
    dados = pd.concat({"valor_bi_por_produto": w.rename(columns=cfg.ROTULO_CURTO),
                       "parcela_por_tipo_de_fluxo": t}, axis=1)
    gr.salvar(fig, nome, dados)
    return fig


def figura_r2(paises_total, n=10, nome="figR2_paises_total_cadeia"):
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.4))
    dados = {}
    for ax, (lado, tit) in zip(axs, (("exp", "(a) Exportadores"), ("imp", "(b) Importadores"))):
        p = paises_total[paises_total["lado"] == lado].pivot(index="pais", columns="periodo", values="share").fillna(0)
        p = p.nlargest(n, "2022–2024").iloc[::-1]
        y = np.arange(len(p))
        cores = [COR_GRUPO[ind.grupo_rcep(c)] for c in p.index]
        ax.barh(y, p["2022–2024"], color=cores, height=0.65)
        ax.scatter(p["2019–2021"], y, marker="|", s=160, color="k", lw=1.6, zorder=3)
        for yi, v, v0 in zip(y, p["2022–2024"], p["2019–2021"]):
            ax.text(max(v, v0) + 0.008, yi, f"{v * 100:.1f}".replace(".", ","), va="center", fontsize=7)
        ax.set_yticks(y, [ind.nome(c) for c in p.index], fontsize=8)
        ax.xaxis.set_major_formatter(gr.fmt_pct)
        ax.set_xlim(0, p.values.max() * 1.15)
        ax.set_title(f"{tit}: participação no total da cadeia")
        ax.grid(axis="y", visible=False)
        dados[lado] = p.iloc[::-1].rename(index=ind.nome)
    alcas = [Patch(color=c, label=g) for g, c in COR_GRUPO.items()]
    alcas.append(Line2D([], [], marker="|", ls="", color="k", ms=10, mew=1.6, label="2019–2021"))
    fig.legend(handles=alcas, loc="lower center", ncol=5, fontsize=8, bbox_to_anchor=(0.5, -0.04),
               title="Barras: 2022–2024, cor pelo grupo do país", title_fontsize=8)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    gr.salvar(fig, nome, pd.concat(dados, axis=1))
    return fig


def figura_r3(pais_prod, n_por_produto=2, nome="figR3_paises_por_produto"):
    """Heatmap país × produto (2022–2024) com a variação em p.p. desde 2019–2021, exportações acima e
    importações abaixo. Linhas: Ásia, RCEP e os países entre os `n_por_produto` maiores de algum
    produto, no lado correspondente."""
    colunas = sh6_destacados() + ["Total"]
    fig, axs = plt.subplots(2, 1, figsize=(10, 9.5))
    dados = {}
    for ax, (lado, tit) in zip(axs, (("exp", "(a) Exportações"), ("imp", "(b) Importações"))):
        p = pais_prod[pais_prod["lado"] == lado]
        paises = p[~p["pais"].isin(["Ásia", "RCEP"])]
        top = (paises.sort_values("2022–2024", ascending=False).groupby("sh6").head(n_por_produto)["pais"].unique())
        ordem_total = (paises[paises["sh6"] == "Total"].set_index("pais")["2022–2024"].reindex(top).sort_values(ascending=False).index)
        linhas = ["Ásia", "RCEP"] + list(ordem_total)
        val = p.pivot(index="pais", columns="sh6", values="2022–2024").reindex(index=linhas, columns=colunas).fillna(0)
        var = p.pivot(index="pais", columns="sh6", values="var_pp").reindex(index=linhas, columns=colunas).fillna(0)
        ax.imshow(val.values, cmap="Blues", vmin=0, vmax=1, aspect="auto")
        for i in range(val.shape[0]):
            for j in range(val.shape[1]):
                v, dv = val.iat[i, j], var.iat[i, j]
                if v < 0.005 and abs(dv) < 1:  # omite células sem comércio relevante nem variação
                    continue
                cor = "white" if v > 0.55 else "black"
                ax.text(j, i - 0.13, f"{v * 100:.0f}", ha="center", va="center", fontsize=7.5, color=cor, fontweight="bold")
                ax.text(j, i + 0.22, f"({round(dv):+d})" if round(dv) else "(0)", ha="center", va="center", fontsize=5.8, color=cor)
        ax.axhline(1.5, color="k", lw=1)
        ax.axvline(len(colunas) - 1.5, color="k", lw=1)
        rotulos_y = [r if r in ("Ásia", "RCEP") else ind.nome(r) for r in linhas]
        ax.set_yticks(range(len(linhas)), rotulos_y, fontsize=8)
        for rot, r in zip(ax.get_yticklabels(), linhas):  # membros da RCEP em negrito
            if r in cfg.RCEP or r in ("Ásia", "RCEP"):
                rot.set_fontweight("bold")
        ax.set_xticks(range(len(colunas)), [textwrap.fill(f"{cfg.ROTULO_CURTO.get(c, 'Total da cadeia')}" + (f" ({c})" if c != "Total" else ""), 12) for c in colunas], fontsize=7)
        ax.xaxis.tick_top()
        ax.grid(False)
        ax.set_title(tit, loc="left", fontsize=10, pad=34)
        dados[lado] = val.rename(index=lambda r: r if r in ("Ásia", "RCEP") else ind.nome(r))
        dados[f"{lado}_var_pp"] = var.rename(index=lambda r: r if r in ("Ásia", "RCEP") else ind.nome(r))
    fig.text(0.5, 0.005, "Participação no comércio mundial de cada produto em 2022–2024 (%); entre parênteses, variação em "
             "pontos percentuais desde 2019–2021. Em negrito, os membros da RCEP.", ha="center", fontsize=8)
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    gr.salvar(fig, nome, pd.concat(dados, axis=1))
    return fig


# Descrições das subposições no estilo da nomenclatura oficial, para a nota de rodapé
DESCRICAO_SH6 = {
    "260400": "minérios de níquel e seus concentrados",
    "750110": "mates de níquel",
    "750120": "sínteres de óxidos de níquel e outros produtos intermediários da metalurgia do níquel",
    "720260": "ferroníquel",
    "750210": "níquel não ligado, em formas brutas",
    "750220": "ligas de níquel, em formas brutas",
    "283324": "sulfatos de níquel",
    "282540": "óxidos e hidróxidos de níquel",
    "282735": "cloreto de níquel",
}


def legendas(agregado):
    """Texto das legendas no padrão ABNT (título acima; fonte e nota abaixo), sem travessões, e uma nota
    de rodapé única com os SH6 para a primeira menção à cadeia no texto."""
    codigos = "; ".join(f"{sh}, {DESCRICAO_SH6[sh]}" for sh in sh6_destacados())
    rodape = (f"A cadeia considerada reúne nove subposições do Sistema Harmonizado, versão 2012: {codigos}. "
              "A subposição 720260 inclui o ferro-gusa de níquel (NPI), e a 750120, o precipitado de hidróxido misto (MHP).")
    nota = "Nota: subposições do Sistema Harmonizado (versão 2012) consideradas: " + ", ".join(sh6_destacados()) + "."
    fonte = "Fonte: elaboração própria com dados do BACI-CEPII (HS2012), obtidos no Observatório de Complexidade Econômica."
    ini, fim = agregado["valor_mundo"].iloc[0] / 1e9, agregado["valor_mundo"].iloc[-1] / 1e9
    paragrafos = {
        "R1": ("figR1_cadeia_mundo_asia_rcep.png",
               "Comércio mundial da cadeia do níquel, por produto e por origem e destino em relação à RCEP (2012–2024)",
               f"Valores em dólares correntes (US$ {gr._num(ini, 1)} bilhões em 2012 e US$ {gr._num(fim, 1)} bilhões em 2024). "
               "No painel b, os fluxos são classificados pelo pertencimento do exportador e do importador à RCEP, com o fluxo "
               "da ASEAN para a China separado dos demais fluxos entre membros; a linha preta marca o comércio entre membros. "
               "A linha vertical tracejada marca 2022, primeiro ano de vigência do acordo."),
        "R5": ("figR5_mapa_fluxos_cadeia.png",
               "Maiores fluxos bilaterais do comércio da cadeia do níquel (2019–2021 e 2022–2024)",
               "Vinte maiores fluxos bilaterais do total da cadeia em cada período, pela média anual do valor; espessura "
               "proporcional ao valor, na mesma escala nos dois mapas, e cor segundo o grupo do exportador."),
        "R2": ("figR2_paises_total_cadeia.png",
               "Participação dos principais exportadores e importadores no comércio mundial da cadeia do níquel (2019–2021 e 2022–2024)",
               "Participações calculadas sobre a soma do valor nos três anos de cada período. Constam os dez países de maior "
               "participação em 2022–2024."),
        "R2-lollipop": ("figR2_membros_antes_depois.png",
               "Participação dos membros da RCEP no comércio mundial da cadeia do níquel (2019–2021 e 2022–2024)",
               "Média das participações anuais em cada período; círculo vazado para 2019–2021 e cheio para 2022–2024. Constam "
               "os membros com participação de ao menos 0,1% em algum período e sentido; Mianmar fica fora."),
        "R4": ("figR4_importancia_intra_rcep.png",
               "Peso do comércio entre membros da RCEP na cadeia do níquel e em todos os produtos (2012–2024)",
               "Parcela no comércio dos membros: (exportações para membros + importações de membros) / (exportações + "
               "importações totais dos membros). Parcela no comércio mundial: fluxos com exportador e importador membros sobre o "
               "comércio mundial. No painel b, 2019–2021 (círculo vazado) e 2022–2024 (cheio), e constam os membros com comércio "
               "médio anual da cadeia de ao menos US$ 10 milhões em algum dos períodos."),
        "R3": ("figR3_paises_por_produto.png",
               "Participação da Ásia, da RCEP e dos principais países no comércio mundial de cada produto da cadeia do níquel (2022–2024)",
               "Participações calculadas sobre a soma do valor em 2022–2024; entre parênteses, variação em pontos percentuais em "
               "relação a 2019–2021. Constam os dois maiores países de cada produto em cada sentido do comércio. Em negrito, os membros da RCEP."),
    }
    quebra = "\n"
    blocos = [quebra.join([f"## Figura {k} (`{arq}`)", f"**Título:** {tit}", "", fonte, "", f"{nota} {txt}"])
              for k, (arq, tit, txt) in paragrafos.items()]
    cabecalho = ["# Legendas das figuras do resumo", "", "## Nota de rodapé (primeira menção à cadeia no texto)", rodape, ""]
    return quebra.join(cabecalho + [(quebra * 2).join(blocos), ""])


# --------------------------------------------------------------------------------------------------
# Membros da RCEP antes e depois da entrada em vigor (janela simétrica de cada membro)
# --------------------------------------------------------------------------------------------------
def _janelas_membros():
    """2019–2021 e 2022–2024 para todos os membros: o texto toma 2022 como ano de referência do acordo,
    sem distinguir a adesão posterior de Indonésia e Filipinas."""
    from . import parceiros as pa
    return {c: pa.janelas(a) for c, a in pa.entrada(unica=True).items()}


def _rotulo_membro(c):
    return ind.nome(c)


def antes_depois_agregado(d):
    """Participação média anual de cada membro da RCEP nas exportações e importações mundiais do total
    da cadeia destacada, na janela anterior e na posterior à entrada em vigor para ele."""
    mundo = d.groupby("ano")["valor"].sum()
    linhas = []
    for pais, (antes, depois) in _janelas_membros().items():
        for lado in ("exp", "imp"):
            s = d[d[lado] == pais].groupby("ano")["valor"].sum().reindex(cfg.ANOS, fill_value=0)
            sh = s / mundo
            linhas.append({"pais": pais, "lado": lado, "anos_antes": f"{antes[0]}–{antes[-1]}",
                           "anos_depois": f"{depois[0]}–{depois[-1]}",
                           "valor_antes": s[antes].mean(), "valor_depois": s[depois].mean(),
                           "share_antes": sh[antes].mean(), "share_depois": sh[depois].mean()})
    out = pd.DataFrame(linhas)
    out["var_pp"] = (out["share_depois"] - out["share_antes"]) * 100
    out["pais_nome"] = out["pais"].map(ind.nome)
    return out


def _comercio_rcep(b):
    """Por ano e membro: exportações + importações totais e com parceiros da RCEP."""
    partes = []
    for lado, outro in (("exp", "imp"), ("imp", "exp")):
        x = b[b[lado].isin(cfg.RCEP)]
        tot = x.groupby(["ano", lado])["valor"].sum()
        com = x[x[outro].isin(cfg.RCEP)].groupby(["ano", lado])["valor"].sum()
        partes.append(pd.DataFrame({"total": tot, "rcep": com}).fillna(0).rename_axis(["ano", "pais"]))
    return pd.concat(partes).groupby(["ano", "pais"]).sum()


def importancia_intra(d, bilateral):
    """Peso do comércio com parceiros da RCEP no comércio dos membros, na cadeia e em todos os produtos.

    Devolve (anual, membros):
    - anual: por ano e recorte, parcela intrabloco no comércio dos membros, (X_rr + M_rr) / (X_r + M_r),
      e parcela do comércio interno ao bloco no comércio mundial;
    - membros: por membro e recorte, a mesma parcela nas janelas anterior e posterior à vigência para
      ele, com o valor médio anual do comércio (X + M) do membro.
    """
    recortes = {"cadeia": d[["ano", "exp", "imp", "valor"]], "total": bilateral}
    anual, membros = [], []
    for rec, b in recortes.items():
        c = _comercio_rcep(b)
        a = c.groupby("ano").sum()
        mundo = b.groupby("ano")["valor"].sum()
        intra = b[b["exp"].isin(cfg.RCEP) & b["imp"].isin(cfg.RCEP)].groupby("ano")["valor"].sum()
        anual.append(pd.DataFrame({"recorte": rec, "parcela_intra_membros": a["rcep"] / a["total"],
                                   "intra_no_mundo": intra / mundo, "valor_mundo": mundo,
                                   "valor_intra": intra}))
        c = c.unstack("pais").reindex(cfg.ANOS).fillna(0)
        for pais, (antes, depois) in _janelas_membros().items():
            t, r = c[("total", pais)], c[("rcep", pais)]
            membros.append({"pais": pais, "recorte": rec,
                            "comercio_antes": t[antes].mean(), "comercio_depois": t[depois].mean(),
                            "parcela_antes": r[antes].sum() / t[antes].sum() if t[antes].sum() else np.nan,
                            "parcela_depois": r[depois].sum() / t[depois].sum() if t[depois].sum() else np.nan})
    anual = pd.concat(anual).rename_axis("ano").reset_index()
    membros = pd.DataFrame(membros)
    membros["var_pp"] = (membros["parcela_depois"] - membros["parcela_antes"]) * 100
    membros["pais_nome"] = membros["pais"].map(ind.nome)
    return anual, membros


def figura_r2_lollipop(ad, limiar=0.001, nome="figR2_membros_antes_depois"):
    """Participação de cada membro nas exportações e importações mundiais do total da cadeia, antes (○)
    e depois (●) da entrada em vigor do acordo para ele. Omite membros abaixo de `limiar` nos dois
    períodos e sentidos; o CSV mantém todos."""
    w = ad.pivot(index="pais", columns="lado", values=["share_antes", "share_depois"])
    visiveis = w[w.max(axis=1) >= limiar].index
    fig, axs = plt.subplots(1, 2, figsize=(10, 4.2))
    for ax, (lado, tit) in zip(axs, (("exp", "(a) Exportações"), ("imp", "(b) Importações"))):
        x = ad[(ad["lado"] == lado) & ad["pais"].isin(visiveis)].sort_values("share_depois").set_index("pais")
        y = np.arange(len(x))
        ax.hlines(y, x["share_antes"], x["share_depois"], color="#999999", lw=1.2)
        ax.scatter(x["share_antes"], y, facecolor="white", edgecolor="k", s=24, zorder=3, label="antes")
        ax.scatter(x["share_depois"], y, color="k", s=24, zorder=3, label="depois")
        ax.set_yticks(y, [_rotulo_membro(c) for c in x.index])
        ax.xaxis.set_major_formatter(gr.fmt_pct)
        ax.grid(axis="y", visible=False)
        ax.set_xlim(left=0)
        ax.set_title(tit, loc="left")
    axs[0].legend(loc="lower right", fontsize=8)
    fig.supxlabel("Participação no comércio mundial da cadeia (média anual de cada janela)", fontsize=8)
    fig.tight_layout()
    gr.salvar(fig, nome, ad.set_index(["lado", "pais"]))
    return fig


def figura_r4(anual, membros, limiar=10e6, nome="figR4_importancia_intra_rcep"):
    """(a) Parcela do comércio com parceiros da RCEP no comércio dos membros e parcela do comércio
    interno ao bloco no comércio mundial, na cadeia e em todos os produtos; (b) a parcela por membro,
    antes (○) e depois (●) da vigência para ele. Em (b), só membros cujo comércio médio da cadeia
    (X + M) atinge `limiar` em alguma janela."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.6), gridspec_kw={"width_ratios": [1, 1.1]})
    cores = {"cadeia": "#d62728", "total": "#1f77b4"}
    rot = {"cadeia": "cadeia do níquel", "total": "todos os produtos"}
    a = anual.set_index("ano")
    for rec, cor in cores.items():
        x = a[a["recorte"] == rec]
        ax1.plot(x.index, x["parcela_intra_membros"], color=cor, lw=1.8, marker="o", ms=3)
        ax1.plot(x.index, x["intra_no_mundo"], color=cor, lw=1.4, ls="--", marker="o", ms=2.5)
    ax1.set_ylim(0, 1)
    ax1.yaxis.set_major_formatter(gr.fmt_pct)
    ax1.set_xticks(cfg.ANOS[::2])
    ax1.axvline(cfg.ANO_RCEP - 0.5, color="k", lw=0.8, ls=":")
    ax1.set_title("(a) Comércio entre membros da RCEP", loc="left")
    alcas = [Line2D([], [], color=c, lw=2, label=rot[r]) for r, c in cores.items()]
    alcas += [Line2D([], [], color="#555555", lw=1.8, label="no comércio dos membros"),
              Line2D([], [], color="#555555", lw=1.4, ls="--", label="no comércio mundial")]
    ax1.legend(handles=alcas, fontsize=7.5, loc="upper left", ncol=2)

    cad = membros[membros["recorte"] == "cadeia"].set_index("pais")
    tot = membros[membros["recorte"] == "total"].set_index("pais")
    vis = cad[cad[["comercio_antes", "comercio_depois"]].max(axis=1) >= limiar].index
    ordem = cad.loc[vis].sort_values("parcela_depois").index.tolist()
    y = np.arange(len(ordem))
    for dados, cor, desl in ((cad, cores["cadeia"], 0.17), (tot, cores["total"], -0.17)):
        x = dados.loc[ordem]
        ax2.hlines(y + desl, x["parcela_antes"], x["parcela_depois"], color=cor, lw=1.2, alpha=0.7)
        ax2.scatter(x["parcela_antes"], y + desl, facecolor="white", edgecolor=cor, s=22, zorder=3)
        ax2.scatter(x["parcela_depois"], y + desl, color=cor, s=22, zorder=3)
    ax2.set_yticks(y, [_rotulo_membro(c) for c in ordem])
    ax2.set_xlim(0, 1)
    ax2.xaxis.set_major_formatter(gr.fmt_pct)
    ax2.grid(axis="y", visible=False)
    ax2.set_title("(b) Parcela da RCEP no comércio de cada membro", loc="left")
    alcas = [Line2D([], [], color=c, lw=2, label=rot[r]) for r, c in cores.items()]
    alcas += [Line2D([], [], ls="", marker="o", mfc="white", mec="k", label="antes"),
              Line2D([], [], ls="", marker="o", color="k", label="depois")]
    ax2.legend(handles=alcas, fontsize=7.5, loc="lower right")
    fig.tight_layout()
    dados = pd.concat({"anual": anual.set_index(["recorte", "ano"]),
                       "membros": membros.set_index(["recorte", "pais"])}, axis=0)
    gr.salvar(fig, nome, dados)
    return fig


def figura_r5_mapa(d, base, n=20, nome="figR5_mapa_fluxos_cadeia"):
    """Mapa dos `n` maiores fluxos bilaterais do total da cadeia destacada, 2019–2021 e 2022–2024."""
    from . import mapas as mp
    return mp.mapa_fluxos(d.assign(cadeia="total"), base, "cadeia", "total", PERIODOS, n=n,
                          nome=nome, titulo="", empilhar=True)


# --------------------------------------------------------------------------------------------------
# Tabela 1 do capítulo como imagem (o docx desconfigura a tabela em pipe)
# --------------------------------------------------------------------------------------------------
LINHAS_TABELA_PARCEIROS = [
    ("chn", "imp", "750110", "Mates"), ("chn", "imp", "750120", "Sínteres e MHP"),
    ("chn", "imp", "283324", "Sulfato"), ("chn", "imp", "720260", "Ferroníquel e NPI"),
    ("chn", "imp", "260400", "Minério"), ("idn", "exp", "720260", "Ferroníquel e NPI"),
    ("idn", "exp", "750120", "Sínteres e MHP"), ("idn", "exp", "750110", "Mates"),
    ("phl", "exp", "260400", "Minério"),
]


def tabela_parceiros(res, linhas=LINHAS_TABELA_PARCEIROS):
    """Linhas da Tabela 1 a partir de `parceiros.resumo(..., unica=True)` (t19)."""
    lado_pt = {"exp": "exportações", "imp": "importações"}
    reg = []
    for m, lado, sh6, rot in linhas:
        r = res[(res["membro"] == m) & (res["lado"] == lado) & (res["sh6"].astype(str) == sh6)].iloc[0]
        reg.append({
            "Membro e fluxo": f"{ind.nome(m)}, {lado_pt[lado]}", "Produto": rot,
            "Valor antes": gr._num(r["valor_medio_antes"] / 1e9, 2),
            "Valor depois": gr._num(r["valor_medio_depois"] / 1e9, 2),
            "Principal parceiro, antes e depois":
                f"{ind.nome(r['principal_antes'])} ({r['share_principal_antes'] * 100:.0f}%); "
                f"{ind.nome(r['principal_depois'])} ({r['share_principal_depois'] * 100:.0f}%)",
            "Índice": gr._num(r["indice_mudanca"], 2) + ("*" if r["acima_placebos"] else ""),
            "Placebo máx.": gr._num(r["placebo_max"], 2),
        })
    return pd.DataFrame(reg)


def figura_tabela_parceiros(tab, nome="tab01_parceiros_marco_2022"):
    larg = [0.18, 0.15, 0.07, 0.07, 0.33, 0.08, 0.12]
    alinh = ["left", "left", "right", "right", "left", "right", "right"]
    n = len(tab)
    fig, ax = plt.subplots(figsize=(10.5, 0.27 * (n + 2)))
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(n + 1.3, 0)
    xs = np.concatenate([[0], np.cumsum(larg)[:-1]])

    def escrever(y, valores, **kw):
        for x, w, a, v in zip(xs, larg, alinh, valores):
            ax.text(x + (w - 0.01 if a == "right" else 0.005), y, v, ha=a, va="center", fontsize=8, **kw)

    escrever(0.5, ["Membro e fluxo", "Produto", "Valor\nantes", "Valor\ndepois",
                   "Principal parceiro, antes e depois", "Índice", "Placebo\nmáx."], fontweight="bold")
    for y in (0, 1.1):
        ax.axhline(y, color="k", lw=0.8)
    for i, linha in enumerate(tab.itertuples(index=False)):
        escrever(1.6 + i, list(linha))
    ax.axhline(n + 1.1, color="k", lw=0.8)
    gr.salvar(fig, nome, tab.set_index("Membro e fluxo"))
    return fig
