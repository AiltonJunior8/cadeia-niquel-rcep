"""Figuras do artigo. Cada função devolve a figura e grava PNG em `outputs/figuras/` e os dados que a
geraram em CSV em `outputs/tabelas/dados_figuras/`, para que todo número visível possa ser conferido."""
import re
import unicodedata

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

from . import config as cfg
from . import indicadores as ind

plt.rcParams.update({
    "figure.dpi": 110, "savefig.dpi": 300, "savefig.bbox": "tight",
    "font.size": 9, "axes.titlesize": 10, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.3, "legend.frameon": False,
})
PALETA = plt.get_cmap("tab10").colors
COR_OUTROS = "#bbbbbb"
COR_REGIAO = {
    "Ásia Oriental": "#d62728", "Sudeste Asiático": "#ff7f0e", "Oceania": "#8c564b",
    "Sul da Ásia": "#e377c2", "Ásia Ocidental e Central": "#bcbd22", "Europa": "#1f77b4",
    "América do Norte": "#17becf", "América Latina e Caribe": "#2ca02c", "África": "#9467bd",
}


def slug(texto):
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", t.lower()).strip("_")


def nome_produto(codigo, nivel):
    return f"sh6_{codigo}" if nivel == "sh6" else f"elo{slug(codigo)}"


def _num(x, casas=1):
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


fmt_bi = mticker.FuncFormatter(lambda x, _: _num(x / 1e9))
fmt_pct = mticker.FuncFormatter(lambda x, _: f"{x * 100:.0f}%")


def _marca_rcep(ax):
    ax.set_xticks(cfg.ANOS[::2])  # anos inteiros, de dois em dois
    ax.axvline(cfg.ANO_RCEP - 0.5, color="k", lw=0.8, ls="--")
    ax.text(cfg.ANO_RCEP - 0.4, 1.0, "RCEP", transform=ax.get_xaxis_transform(), va="top", fontsize=7)


def salvar(fig, nome, dados=None):
    cfg.DIR_FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(cfg.DIR_FIG / f"{nome}.png")
    if dados is not None:
        d = cfg.DIR_TAB / "dados_figuras"
        d.mkdir(parents=True, exist_ok=True)
        dados.to_csv(d / f"{nome}.csv", encoding="utf-8-sig")


# --------------------------------------------------------------------------------------------------
# Figuras de síntese
# --------------------------------------------------------------------------------------------------
def valor_por_elo(tot_elo, nome="fig01_valor_anual_por_elo"):
    """Valor anual do comércio mundial de cada elo (US$ bilhões), um painel por elo."""
    elos = [e for e in cfg.CADEIA if e in tot_elo["elo"].unique()]
    w = tot_elo.pivot(index="ano", columns="elo", values="valor")[elos]
    n = len(elos)
    fig, axs = plt.subplots(int(np.ceil(n / 3)), 3, figsize=(10, 2.4 * np.ceil(n / 3)), sharex=True)
    for ax, elo, cor in zip(axs.flat, elos, PALETA * 2):
        ax.plot(w.index, w[elo], marker="o", ms=3, color=cor)
        ax.set_title(elo)
        ax.yaxis.set_major_formatter(fmt_bi)
        ax.set_ylim(bottom=0)
        _marca_rcep(ax)
    for ax in list(axs.flat)[n:]:
        ax.set_visible(False)
    fig.supylabel("US$ bilhões correntes")
    fig.tight_layout()
    salvar(fig, nome, w)
    return fig


def antes_depois_membros(ad, nivel, codigos, lado_rotulo, nome, limiar=0.001):
    """Participação média de cada membro da RCEP antes (○) e depois (●) da entrada em vigor,
    um painel por produto. Membros ordenados pela participação posterior; o gráfico omite os membros
    abaixo de `limiar` nos dois períodos (o CSV de dados mantém todos)."""
    n = len(codigos)
    ncol = min(4, n)
    nlin = int(np.ceil(n / ncol))
    fig, axs = plt.subplots(nlin, ncol, figsize=(3.0 * ncol, 3.6 * nlin), squeeze=False)
    axs = list(axs.flat)
    for ax in axs[n:]:
        ax.set_visible(False)
    for ax, cod in zip(axs, codigos):
        d = ad[ad[nivel] == cod]
        d = d[d[["share_antes", "share_depois"]].max(axis=1) >= limiar].sort_values("share_depois")
        y = np.arange(len(d))
        ax.hlines(y, d["share_antes"], d["share_depois"], color="#999999", lw=1)
        ax.scatter(d["share_antes"], y, facecolor="white", edgecolor="k", s=18, zorder=3, label="antes")
        ax.scatter(d["share_depois"], y, color="k", s=18, zorder=3, label="depois")
        ax.set_yticks(y, [ind.nome(c) for c in d["pais"]])
        ax.xaxis.set_major_formatter(fmt_pct)
        ax.set_title(ind.rotulo(cod, nivel), fontsize=8, wrap=True)
    axs[0].legend(loc="lower right", fontsize=7)
    fig.suptitle(f"Participação nas {lado_rotulo} mundiais, antes e depois da entrada em vigor da RCEP\n"
                 f"(membros com participação ≥ {_num(limiar * 100)}% em algum dos períodos)")
    fig.tight_layout()
    salvar(fig, nome, ad[ad[nivel].isin(codigos)].set_index([nivel, "pais"]))
    return fig


def intra_rcep(intra, nivel, codigos, nome):
    """Parcela do comércio mundial realizada entre membros da RCEP, por produto."""
    w = intra[intra[nivel].isin(codigos)].pivot(index="ano", columns=nivel, values="intra_no_mundo")[codigos]
    fig, ax = plt.subplots(figsize=(7, 3.6))
    for cod, cor in zip(codigos, PALETA * 2):
        ax.plot(w.index, w[cod], marker="o", ms=3, color=cor, label=ind.rotulo(cod, nivel))
    ax.yaxis.set_major_formatter(fmt_pct)
    ax.set_ylim(0, 1)
    ax.set_ylabel("Comércio intra-RCEP / comércio mundial")
    _marca_rcep(ax)
    ax.legend(fontsize=7, bbox_to_anchor=(1.01, 1), loc="upper left")
    salvar(fig, nome, w)
    return fig


# --------------------------------------------------------------------------------------------------
# Painel por produto (replicado para cada SH6 do núcleo e cada elo)
# --------------------------------------------------------------------------------------------------
def painel_produto(tot, part_pais, part_reg, codigo, nivel, n=5):
    """Quatro painéis para um produto: valor e quantidade; principais exportadores; principais
    importadores; participação das macrorregiões nas exportações e nas importações."""
    t = tot[tot[nivel] == codigo].set_index("ano").reindex(cfg.ANOS)
    pe = ind.principais(part_pais["exp"], codigo, nivel, n)
    pi = ind.principais(part_pais["imp"], codigo, nivel, n)
    re_ = part_reg["exp"][part_reg["exp"][nivel] == codigo].pivot(index="ano", columns="regiao", values="share")
    ri = part_reg["imp"][part_reg["imp"][nivel] == codigo].pivot(index="ano", columns="regiao", values="share")
    regioes = [r for r in COR_REGIAO if r in set(re_.columns) | set(ri.columns)]
    re_, ri = re_.reindex(index=cfg.ANOS, columns=regioes).fillna(0), ri.reindex(index=cfg.ANOS, columns=regioes).fillna(0)

    fig, axs = plt.subplots(2, 3, figsize=(12, 6.6))
    # (a) valor e quantidade
    ax = axs[0, 0]
    ax.bar(t.index, t["valor"], color="#4c72b0", label="Valor (US$ bi)")
    ax.yaxis.set_major_formatter(fmt_bi)
    ax.set_title("(a) Comércio mundial")
    ax.set_ylabel("US$ bilhões")
    if nivel == "sh6":  # quantidades só fazem sentido somadas dentro de uma subposição
        ax2 = ax.twinx()
        ax2.plot(t.index, t["qtd"] / 1e3, color="k", marker="o", ms=3, label="Quantidade (mil t)")
        ax2.set_ylabel("mil toneladas")
        ax2.set_ylim(bottom=0)
        ax2.grid(False)
        ax2.spines["right"].set_visible(True)
    _marca_rcep(ax)
    # (b), (c) principais países
    for ax, w, tit in ((axs[0, 1], pe, "(b) Principais exportadores"), (axs[0, 2], pi, "(c) Principais importadores")):
        cores = list(PALETA[: len(w.columns) - 1]) + [COR_OUTROS]
        ax.stackplot(w.index, w.T.values, colors=cores,
                     labels=[ind.nome(c) if c != "Outros" else c for c in w.columns])
        ax.yaxis.set_major_formatter(fmt_pct)
        ax.set_ylim(0, 1)
        ax.set_title(tit)
        ax.legend(fontsize=7, loc="upper left", bbox_to_anchor=(0, -0.08), ncol=3)
        _marca_rcep(ax)
    # (d), (e) regiões
    for ax, w, tit in ((axs[1, 0], re_, "(d) Exportações por região"), (axs[1, 1], ri, "(e) Importações por região")):
        base = np.zeros(len(w))
        for r in w.columns:
            ax.bar(w.index, w[r], bottom=base, color=COR_REGIAO[r], label=r, width=0.8)
            base += w[r].values
        ax.yaxis.set_major_formatter(fmt_pct)
        ax.set_ylim(0, 1)
        ax.set_title(tit)
        _marca_rcep(ax)
    axs[1, 1].legend(fontsize=7, loc="upper left", bbox_to_anchor=(1.02, 1))
    axs[1, 2].set_visible(False)
    fig.suptitle(f"{ind.rotulo(codigo, nivel)}" + (f" (SH {codigo})" if nivel == "sh6" else ""), fontsize=11)
    fig.tight_layout()

    dados = pd.concat({"total": t[["valor", "qtd", "cobertura_qtd"]],
                       "exportadores": pe.rename(columns=ind.nome), "importadores": pi.rename(columns=ind.nome),
                       "regioes_exp": re_, "regioes_imp": ri}, axis=1)
    salvar(fig, f"painel_{nome_produto(codigo, nivel)}", dados)
    return fig


# --------------------------------------------------------------------------------------------------
# Parceiros e volume dos membros da RCEP (ver niquel.parceiros)
# --------------------------------------------------------------------------------------------------
def _grade_membros(res, nivel, codigos, coluna):
    membros = [m for m in cfg.RCEP if m in set(res["membro"])]
    val = res.pivot(index="membro", columns=nivel, values=coluna).reindex(index=membros, columns=codigos)
    rel = res.pivot(index="membro", columns=nivel, values="relevante").reindex(index=membros, columns=codigos)
    rel = rel.fillna(False).astype(bool)
    com_comercio = rel.any(axis=1)  # omite membros sem nenhum produto acima do limiar
    return val[com_comercio], rel[com_comercio]


def _rotulos_colunas(codigos, nivel):
    import textwrap
    return [textwrap.fill(ind.rotulo(c, nivel) if nivel == "elo" else f"{c} {ind.rotulo(c, nivel)}", 16) for c in codigos]


def heatmap_mudanca(res, nivel, codigos, lado_rotulo, nome):
    """Índice de dissimilaridade dos parceiros (0–1) por membro × produto; * = acima de todas as
    janelas placebo; células cinzas = comércio médio abaixo do limiar de relevância."""
    val, rel = _grade_membros(res, nivel, codigos, "indice_mudanca")
    acima = res.pivot(index="membro", columns=nivel, values="acima_placebos").reindex(index=val.index, columns=codigos)
    fig, ax = plt.subplots(figsize=(1.35 * len(codigos) + 2, 0.42 * len(val) + 2))
    mostrado = val.where(rel)
    im = ax.imshow(mostrado.values.astype(float), cmap="Purples", vmin=0, vmax=1, aspect="auto")
    ax.imshow(np.where(rel.values, np.nan, 1.0), cmap=mcolors_cinza(), vmin=0, vmax=1, aspect="auto")
    for i in range(val.shape[0]):
        for j in range(val.shape[1]):
            if rel.iat[i, j] and pd.notna(val.iat[i, j]):
                marca = "*" if acima.iat[i, j] == True else ""  # noqa: E712 (pode ser NaN)
                ax.text(j, i, f"{_num(val.iat[i, j], 2)}{marca}", ha="center", va="center", fontsize=7,
                        color="white" if val.iat[i, j] > 0.6 else "black")
    ax.set_xticks(range(len(codigos)), _rotulos_colunas(codigos, nivel), fontsize=7, rotation=0)
    ax.set_yticks(range(len(val)), [ind.nome(m) for m in val.index], fontsize=8)
    ax.grid(False)
    fig.colorbar(im, ax=ax, shrink=0.7, label="Índice de dissimilaridade dos parceiros")
    ax.set_title(f"Mudança na composição dos parceiros ({lado_rotulo}), janela simétrica antes × depois da vigência\n"
                 f"* acima de todas as janelas placebo anteriores; cinza: comércio < US$ 10 mi/ano", fontsize=9)
    fig.tight_layout()
    salvar(fig, nome, val.rename(index=ind.nome))
    return fig


def mcolors_cinza():
    import matplotlib.colors as mcolors
    return mcolors.ListedColormap(["#e6e6e6"])


def heatmap_volume(res, nivel, codigos, lado_rotulo, nome, medida="valor"):
    """Variação (%) da média anual de valor ou quantidade, depois × antes da vigência, por membro ×
    produto. A primeira linha traz a variação do comércio mundial do produto na janela de 2022."""
    col = f"var_{medida}_pct"
    val, rel = _grade_membros(res, nivel, codigos, col)
    ref = res[res["ano_entrada"] == cfg.ANO_RCEP].groupby(nivel)[f"var_{medida}_mundo_pct"].first().reindex(codigos)
    val = pd.concat([ref.to_frame("Mundo (2019–21 → 2022–24)").T, val])
    rel = pd.concat([pd.DataFrame([[True] * len(codigos)], index=["Mundo (2019–21 → 2022–24)"], columns=codigos), rel])
    fig, ax = plt.subplots(figsize=(1.35 * len(codigos) + 2, 0.42 * len(val) + 2))
    mostrado = val.where(rel).astype(float).clip(-100, 200)
    norma = mcolors_div()
    im = ax.imshow(mostrado.values, cmap="RdBu_r", norm=norma, aspect="auto")
    ax.imshow(np.where(rel.values, np.nan, 1.0), cmap=mcolors_cinza(), vmin=0, vmax=1, aspect="auto")
    for i in range(val.shape[0]):
        for j in range(val.shape[1]):
            v = val.iat[i, j]
            if rel.iat[i, j] and pd.notna(v):
                ax.text(j, i, f"{v:+.0f}%" if abs(v) < 1000 else ">+999%", ha="center", va="center", fontsize=7,
                        color="white" if (v > 120 or v < -60) else "black")
    ax.axhline(0.5, color="k", lw=1)
    ax.set_xticks(range(len(codigos)), _rotulos_colunas(codigos, nivel), fontsize=7)
    ax.set_yticks(range(len(val)), [ind.nome(m) if m in cfg.RCEP else m for m in val.index], fontsize=8)
    ax.grid(False)
    fig.colorbar(im, ax=ax, shrink=0.7, label="variação % (escala limitada a −100% e +200%)")
    unidade = "valor (US$ correntes)" if medida == "valor" else "quantidade (t)"
    ax.set_title(f"Variação da média anual de {unidade} das {lado_rotulo}, depois × antes da vigência\n"
                 f"cinza: comércio < US$ 10 mi/ano", fontsize=9)
    fig.tight_layout()
    salvar(fig, nome, val.rename(index=lambda m: ind.nome(m) if m in cfg.RCEP else m))
    return fig


def mcolors_div():
    import matplotlib.colors as mcolors
    return mcolors.TwoSlopeNorm(vmin=-100, vcenter=0, vmax=200)


def barras_composicao(comp, pares, nivel, nome, n=5):
    """Composição dos parceiros antes e depois para pares (membro, produto, lado): os `n` maiores
    parceiros pela soma dos dois períodos e Outros."""
    ncol = 4
    nlin = int(np.ceil(len(pares) / ncol))
    fig, axs = plt.subplots(nlin, ncol, figsize=(3.6 * ncol, 2.5 * nlin), squeeze=False)
    axs = list(axs.flat)
    for ax in axs[len(pares):]:
        ax.set_visible(False)
    dados = []
    for ax, (membro, cod, lado) in zip(axs, pares):
        c = comp[(comp["membro"] == membro) & (comp[nivel] == cod) & (comp["lado"] == lado)].fillna(0)
        top = c.assign(t=c["share_antes"] + c["share_depois"]).nlargest(n, "t")["parceiro"].tolist()
        c = c.assign(p=np.where(c["parceiro"].isin(top), c["parceiro"], "Outros"))
        w = c.groupby("p")[["share_antes", "share_depois"]].sum().reindex(top + ["Outros"]).fillna(0)
        esq = np.zeros(2)
        for k, (parc, linha) in enumerate(w.iterrows()):
            v = linha[["share_antes", "share_depois"]].values
            cor = COR_OUTROS if parc == "Outros" else PALETA[k % 10]
            ax.barh([1, 0], v, left=esq, color=cor, label=ind.nome(parc) if parc != "Outros" else parc)
            for y, (x0, dv) in zip([1, 0], zip(esq, v)):
                if dv >= 0.08:
                    ax.text(x0 + dv / 2, y, f"{dv * 100:.0f}", ha="center", va="center", fontsize=6.5)
            esq += v
        ax.set_yticks([1, 0], ["antes", "depois"], fontsize=7)
        ax.set_xlim(0, 1)
        ax.xaxis.set_major_formatter(fmt_pct)
        ax.tick_params(axis="x", labelsize=7)
        sentido = "exportações por destino" if lado == "exp" else "importações por origem"
        ax.set_title(f"{ind.nome(membro)}: {sentido}\n{ind.rotulo(cod, nivel)[:40]}", fontsize=7.5)
        ax.legend(fontsize=6, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.18))
        ax.grid(False)
        dados.append(w.assign(membro=ind.nome(membro), produto=cod, lado=lado).rename(index=ind.nome))
    fig.suptitle("Composição dos parceiros dos membros da RCEP, janela simétrica antes × depois da vigência (%)", fontsize=10)
    fig.tight_layout()
    salvar(fig, nome, pd.concat(dados))
    return fig
