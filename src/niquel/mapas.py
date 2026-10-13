"""Mapas do comércio mundial: coropléticos de participação por país e mapas de fluxos bilaterais.

Base cartográfica: Natural Earth 1:50m (domínio público), processada uma vez por `preparar_base()` e
versionada em `data/referencia/mundo_natural_earth_50m.geojson`. Projeção Robinson.
"""
import geopandas as gpd
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from . import config as cfg
from . import graficos as gr
from . import indicadores as ind

ARQ_MAPA = cfg.DIR_REF / "mundo_natural_earth_50m.geojson"
URL_NE = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"
          "ne_50m_admin_0_countries.geojson")
PROJECAO = "ESRI:54030"  # Robinson

# Classes de participação (fração do comércio mundial) para os coropléticos
CLASSES = [0, 0.001, 0.01, 0.05, 0.10, 0.25, 1.0001]
ROTULOS_CLASSES = ["< 0,1%", "0,1–1%", "1–5%", "5–10%", "10–25%", "≥ 25%"]
CMAP_CLASSES = plt.get_cmap("YlOrRd", len(ROTULOS_CLASSES))
COR_SEM_COMERCIO = "#eeeeee"
COR_GRUPO = {"China": "#d62728", "ASEAN": "#ff7f0e", "Demais RCEP": "#8c564b", "Resto do mundo": "#1f77b4"}


def preparar_base(origem):
    """Processa o GeoJSON do Natural Earth (baixado de `URL_NE` para `origem`): código ISO3 em
    minúsculas (ISO_A3_EH, com ADM0_A3 onde o ISO é -99, caso de França e Noruega), geometrias
    agregadas por código (a Austrália tem territórios externos separados), simplificação leve e
    ponto de rótulo para ancorar os fluxos."""
    g = gpd.read_file(origem)
    g["iso3"] = g["ISO_A3_EH"].where(g["ISO_A3_EH"] != "-99", g["ADM0_A3"]).str.lower()
    g = g.sort_values("POP_EST", ascending=False)  # o território principal fornece o ponto de rótulo
    rotulo = g.groupby("iso3")[["LABEL_X", "LABEL_Y"]].first()
    g = g[["iso3", "geometry"]].dissolve(by="iso3").join(rotulo).reset_index()
    g["geometry"] = g.geometry.simplify(0.02, preserve_topology=True)
    g = g.rename(columns={"LABEL_X": "lon", "LABEL_Y": "lat"})
    cfg.DIR_REF.mkdir(parents=True, exist_ok=True)
    g.to_file(ARQ_MAPA, driver="GeoJSON")
    return g


def carregar_base():
    g = gpd.read_file(ARQ_MAPA)
    pontos = gpd.GeoSeries(gpd.points_from_xy(g["lon"], g["lat"]), crs=4326).to_crs(PROJECAO)
    g = g.to_crs(PROJECAO)
    g["x"], g["y"] = pontos.x.values, pontos.y.values
    return g[g["iso3"] != "ata"]  # sem Antártida


def participacao_periodo(df, lado, nivel, codigo, anos):
    """Participação de cada país no comércio mundial do produto, somando os anos do período."""
    d = df[(df[nivel] == codigo) & df["ano"].isin(anos)].groupby(lado)["valor"].sum()
    return (d / d.sum()).rename("share")


def _coropletico(ax, base, share, titulo):
    g = base.merge(share, left_on="iso3", right_index=True, how="left")
    g["classe"] = pd.cut(g["share"], CLASSES, labels=False, right=False)
    g[g["classe"].isna()].plot(ax=ax, color=COR_SEM_COMERCIO, edgecolor="white", linewidth=0.2)
    com = g[g["classe"].notna()]
    com.plot(ax=ax, color=[CMAP_CLASSES(int(c)) for c in com["classe"]], edgecolor="white", linewidth=0.2)
    ax.set_title(titulo, fontsize=9)
    ax.set_axis_off()


def _legenda_classes(fig):
    alcas = [Patch(color=CMAP_CLASSES(i), label=r) for i, r in enumerate(ROTULOS_CLASSES)]
    alcas.append(Patch(color=COR_SEM_COMERCIO, label="sem comércio"))
    fig.legend(handles=alcas, loc="lower center", ncol=len(alcas), fontsize=8, title="Participação no comércio mundial",
               title_fontsize=8, bbox_to_anchor=(0.5, -0.02))


def mapa_participacao(df, base, nivel, codigo, periodos):
    """Quatro mapas: exportações e importações, nos dois períodos de `periodos` ({rótulo: anos})."""
    fig, axs = plt.subplots(2, 2, figsize=(12, 6.4))
    dados = {}
    for i, (lado, rot_lado) in enumerate((("exp", "Exportações"), ("imp", "Importações"))):
        for j, (per, anos) in enumerate(periodos.items()):
            s = participacao_periodo(df, lado, nivel, codigo, anos)
            dados[(lado, per)] = s
            _coropletico(axs[i, j], base, s, f"{rot_lado}, {per}")
    _legenda_classes(fig)
    fig.suptitle(ind.rotulo(codigo, nivel) + (f" (SH {codigo})" if nivel == "sh6" else ""), fontsize=11)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    tab = pd.concat(dados, axis=1).fillna(0)
    tab.columns = [f"share_{lado}_{per}" for lado, per in tab.columns]
    tab.insert(0, "pais", tab.index.map(ind.nome))
    gr.salvar(fig, f"mapa_participacao_{gr.nome_produto(codigo, nivel)}", tab.sort_values(tab.columns[-1], ascending=False))
    return fig


def _arco(x0, y0, x1, y1, curvatura=0.2, n=40):
    """Curva de Bézier quadrática entre dois pontos projetados, com o controle deslocado
    perpendicularmente ao segmento (sentido horário em relação à origem)."""
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    dx, dy = x1 - x0, y1 - y0
    cx, cy = mx + curvatura * dy, my - curvatura * dx
    t = np.linspace(0, 1, n)
    return ((1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t ** 2 * x1,
            (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t ** 2 * y1)


def mapa_fluxos(df, base, nivel, codigo, periodos, n=20, nome=None, titulo=None, empilhar=False):
    """Os `n` maiores fluxos bilaterais (média anual de cada período), com espessura proporcional ao
    valor na mesma escala nos dois painéis e cor pelo grupo do exportador. `nome` e `titulo` substituem
    os derivados do produto (`titulo=""` omite o título); `empilhar` põe os períodos um sobre o outro."""
    coords = base.set_index("iso3")[["x", "y"]]
    medias = {per: (df[(df[nivel] == codigo) & df["ano"].isin(anos)]
                    .groupby(["exp", "imp", "grupo_exp"], as_index=False)["valor"].sum()
                    .assign(valor=lambda d: d["valor"] / len(anos))
                    .nlargest(n, "valor"))
              for per, anos in periodos.items()}
    vmax = max(m["valor"].max() for m in medias.values())
    if empilhar:
        fig, axs = plt.subplots(len(periodos), 1, figsize=(8, 3.0 * len(periodos)))
    else:
        fig, axs = plt.subplots(1, len(periodos), figsize=(6.2 * len(periodos), 3.9))
    for ax, (per, m) in zip(np.atleast_1d(axs), medias.items()):
        base.plot(ax=ax, color="#e6e6e6", edgecolor="white", linewidth=0.2)
        for r in m.sort_values("valor").itertuples():
            if r.exp not in coords.index or r.imp not in coords.index:
                continue
            (x0, y0), (x1, y1) = coords.loc[r.exp], coords.loc[r.imp]
            xs, ys = _arco(x0, y0, x1, y1)
            ax.plot(xs, ys, color=COR_GRUPO[r.grupo_exp], lw=0.4 + 5.5 * r.valor / vmax, alpha=0.75,
                    solid_capstyle="round")
            ax.annotate("", xy=(xs[-1], ys[-1]), xytext=(xs[-4], ys[-4]),
                        arrowprops=dict(arrowstyle="-|>", color=COR_GRUPO[r.grupo_exp], lw=0.6, mutation_scale=7))
        envolvidos = set(m["exp"]) | set(m["imp"])
        pts = coords.loc[coords.index.intersection(list(envolvidos))]
        ax.scatter(pts["x"], pts["y"], s=6, color="k", zorder=5)
        ax.set_title(f"{per}: {n} maiores fluxos (média anual)", fontsize=9)
        ax.set_ylim(-5.0e6, 8.0e6)  # cerca de 47°S a 77°N em Robinson: corta a Antártida
        ax.set_axis_off()
    rot_grupo = {"China": "China", "ASEAN": "ASEAN", "Demais RCEP": "Demais membros da RCEP", "Resto do mundo": "Resto do mundo"}
    presentes = set().union(*(m["grupo_exp"] for m in medias.values()))  # só os grupos que aparecem nos mapas
    alcas = [Line2D([], [], color=c, lw=2.5, label=f"Exportador: {rot_grupo[g]}") for g, c in COR_GRUPO.items()
             if g in presentes]
    alcas += [Line2D([], [], color="#777777", lw=0.4 + 5.5 * f, label=f"US$ {gr._num(vmax * f / 1e9, 2)} bi")
              for f in (0.1, 0.5, 1.0)]
    fig.legend(handles=alcas, loc="lower center", ncol=4, fontsize=7.5, bbox_to_anchor=(0.5, -0.06 if not empilhar else -0.03))
    titulo = ind.rotulo(codigo, nivel) + (f" (SH {codigo})" if nivel == "sh6" else "") if titulo is None else titulo
    if titulo:
        fig.suptitle(titulo, fontsize=11)
    fig.tight_layout(rect=(0, 0.05 if not empilhar else 0.03, 1, 1))
    tab = pd.concat({per: m.set_index(["exp", "imp"])["valor"] for per, m in medias.items()}, axis=1)
    tab.index = [f"{ind.nome(e)} → {ind.nome(i)}" for e, i in tab.index]
    gr.salvar(fig, nome or f"mapa_fluxos_{gr.nome_produto(codigo, nivel)}", tab)
    return fig
