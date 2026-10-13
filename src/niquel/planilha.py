"""Planilha para compartilhar com os coautores: os fluxos bilaterais da cadeia destacada (dados brutos) e as
métricas citadas no capítulo de dados do artigo, numa aba cada, com uma aba de leia-me.

As métricas seguem as convenções do texto: 2022 como marco para todos os membros (2019–2021 × 2022–2024),
participações calculadas sobre a soma do valor de cada período (ou média das parcelas anuais, nas figuras de
membros), valores em US$ correntes e quantidades em toneladas.
"""
import pandas as pd

from . import config as cfg
from . import indicadores as ind
from . import parceiros as pa
from . import sintese as si

ARQ_PLANILHA = cfg.RAIZ / "outputs" / "planilha_artigo_niquel_rcep.xlsx"
FONTE = ("Fonte: elaboração própria com dados do BACI-CEPII (HS2012), obtidos no Observatório de Complexidade "
         "Econômica.")
P1, P2 = list(si.PERIODOS)
ELOS_POSTERIORES = ["6. Aço inoxidável", "7. Baterias"]


def _pct(s):
    return s * 100


def dados_brutos(df):
    """Fluxos bilaterais (ano × exportador × importador × SH6) da cadeia destacada."""
    d = df[df["sh6"].isin(si.sh6_destacados())]
    out = pd.DataFrame({
        "Ano": d["ano"], "SH6": d["sh6"], "Produto": d["sh6"].map(cfg.ROTULO_CURTO), "Etapa": d["elo"],
        "Exportador (ISO3)": d["exp"].str.upper(), "Exportador": d["exp"].map(ind.nome),
        "Importador (ISO3)": d["imp"].str.upper(), "Importador": d["imp"].map(ind.nome),
        "Valor (US$ correntes)": d["valor"], "Quantidade (t)": d["qtd"],
    })
    return out.sort_values(["Ano", "SH6", "Valor (US$ correntes)"], ascending=[True, True, False]).reset_index(drop=True)


def metricas(df, bilateral):
    """Lista de (título, nota, DataFrame), na ordem em que aparecem no capítulo."""
    d = si.recorte(df)
    blocos = []

    # 1. Valor, composição e quantidade por produto
    tot = ind.totais(d, "sh6")
    val = tot.pivot(index="ano", columns="sh6", values="valor")[si.sh6_destacados()]
    val.columns = [f"{cfg.ROTULO_CURTO[c]} ({c})" for c in val.columns]
    val["Total da cadeia"] = val.sum(axis=1)
    blocos.append(("1. Valor do comércio mundial da cadeia, por produto (US$ bilhões correntes)",
                   "Figura 1, painel a.", (val / 1e9).rename_axis("Ano").reset_index()))
    comp = val.drop(columns="Total da cadeia").div(val["Total da cadeia"], axis=0)
    blocos.append(("2. Participação de cada produto no valor da cadeia (%)", "Figura 1, painel a.",
                   _pct(comp).rename_axis("Ano").reset_index()))
    qtd = tot.pivot(index="ano", columns="sh6", values="qtd")[si.sh6_destacados()] / 1e3
    qtd.columns = [f"{cfg.ROTULO_CURTO[c]} ({c})" for c in qtd.columns]
    qtd["Valor unitário do níquel não ligado (US$ mil/t)"] = (
        tot.query("sh6 == '750210'").set_index("ano")["valor_unit"] / 1e3)
    blocos.append(("3. Quantidade comercializada por produto (mil toneladas) e valor unitário do níquel não ligado",
                   "Valor unitário calculado a partir dos próprios fluxos (valor / quantidade).",
                   qtd.rename_axis("Ano").reset_index()))

    # 4. Tipos de fluxo
    tipos = si.fluxos_por_tipo(d)[list(si.TIPOS_FLUXO)]
    t = tipos.div(tipos.sum(axis=1), axis=0)
    t["Comércio entre membros da RCEP (soma das duas primeiras colunas)"] = t.iloc[:, :2].sum(axis=1)
    t.columns = [c[0].upper() + c[1:] for c in t.columns]
    blocos.append(("4. Comércio mundial da cadeia por origem e destino em relação à RCEP (% do valor mundial)",
                   "Figura 1, painel b.", _pct(t).rename_axis("Ano").reset_index()))

    # 5. Ásia e RCEP
    ag = si.agregado_anual(d).set_index("ano")
    asia = pd.DataFrame({
        "RCEP: exportações": ag["share_exp_rcep"], "RCEP: importações": ag["share_imp_rcep"],
        "RCEP: comércio interno": ag["share_intra_rcep"], "Ásia: exportações": ag["share_exp_asia"],
        "Ásia: importações": ag["share_imp_asia"], "Ásia: comércio interno": ag["share_intra_asia"]})
    blocos.append(("5. Participação da RCEP e da Ásia no comércio mundial da cadeia (%)",
                   "Ásia: sub-regiões da ONU Ásia Oriental, Sudeste Asiático, Sul da Ásia, Ásia Ocidental e Ásia Central. "
                   "Comércio interno: exportador e importador no mesmo recorte.",
                   _pct(asia).rename_axis("Ano").reset_index()))

    # 6 e 7. Peso do comércio entre membros
    anual, membros = si.importancia_intra(d, bilateral)
    w = anual.pivot(index="ano", columns="recorte", values=["parcela_intra_membros", "intra_no_mundo"])
    w = pd.DataFrame({
        "Cadeia: parcela no comércio dos membros": w[("parcela_intra_membros", "cadeia")],
        "Todos os produtos: parcela no comércio dos membros": w[("parcela_intra_membros", "total")],
        "Cadeia: parcela no comércio mundial": w[("intra_no_mundo", "cadeia")],
        "Todos os produtos: parcela no comércio mundial": w[("intra_no_mundo", "total")]})
    blocos.append(("6. Peso do comércio entre membros da RCEP: cadeia e todos os produtos (%)",
                   "Figura 2, painel a. Parcela no comércio dos membros = (exportações para membros + importações de "
                   "membros) / (exportações + importações totais dos membros).",
                   _pct(w).rename_axis("Ano").reset_index()))
    m = membros.pivot(index="pais", columns="recorte",
                      values=["parcela_antes", "parcela_depois", "comercio_antes", "comercio_depois"])
    m = pd.DataFrame({
        "Membro": m.index.map(ind.nome),
        f"Cadeia: parcela da RCEP, {P1} (%)": _pct(m[("parcela_antes", "cadeia")]),
        f"Cadeia: parcela da RCEP, {P2} (%)": _pct(m[("parcela_depois", "cadeia")]),
        f"Todos os produtos: parcela da RCEP, {P1} (%)": _pct(m[("parcela_antes", "total")]),
        f"Todos os produtos: parcela da RCEP, {P2} (%)": _pct(m[("parcela_depois", "total")]),
        f"Cadeia: comércio médio anual, {P1} (US$ milhões)": m[("comercio_antes", "cadeia")] / 1e6,
        f"Cadeia: comércio médio anual, {P2} (US$ milhões)": m[("comercio_depois", "cadeia")] / 1e6,
    }).sort_values(f"Cadeia: parcela da RCEP, {P2} (%)", ascending=False)
    blocos.append(("7. Parcela dos parceiros da RCEP no comércio de cada membro",
                   "Figura 2, painel b (que mostra só membros com comércio médio da cadeia de ao menos US$ 10 milhões). "
                   "Para membros com comércio da cadeia pequeno (Brunei, Laos, Camboja, Nova Zelândia), as parcelas "
                   "dependem de poucas transações e oscilam muito.", m))

    # 8. Membros no comércio mundial da cadeia
    ad = si.antes_depois_agregado(d)
    a = ad.pivot(index="pais", columns="lado", values=["share_antes", "share_depois"])
    a = pd.DataFrame({
        "Membro": a.index.map(ind.nome),
        f"Exportações, {P1} (%)": _pct(a[("share_antes", "exp")]),
        f"Exportações, {P2} (%)": _pct(a[("share_depois", "exp")]),
        f"Importações, {P1} (%)": _pct(a[("share_antes", "imp")]),
        f"Importações, {P2} (%)": _pct(a[("share_depois", "imp")]),
    }).sort_values(f"Exportações, {P2} (%)", ascending=False)
    blocos.append(("8. Participação de cada membro da RCEP no comércio mundial da cadeia",
                   "Figura 3. Média das participações anuais de cada período.", a))

    # 9. Principais países no total da cadeia
    pt = si.participacao_paises_total(d)
    for lado, rot in (("exp", "exportadores"), ("imp", "importadores")):
        x = pt[pt["lado"] == lado].pivot(index="pais", columns="periodo", values="share").fillna(0)
        x = x.sort_values(P2, ascending=False).head(15)
        x = pd.DataFrame({"País": x.index.map(ind.nome), "Membro da RCEP": x.index.isin(cfg.RCEP),
                          f"{P1} (%)": _pct(x[P1]), f"{P2} (%)": _pct(x[P2]),
                          "Variação (p.p.)": _pct(x[P2] - x[P1])})
        blocos.append((f"9{'a' if lado == 'exp' else 'b'}. Quinze maiores {rot} do total da cadeia",
                       "Participação sobre a soma do valor de cada período.", x))

    # 10. País × produto
    pp = si.participacao_paises_produto(d)
    pp = pp[(pp[[P1, P2]].max(axis=1) >= 0.01) | pp["pais"].isin(["Ásia", "RCEP"])]
    pp = pd.DataFrame({
        "Sentido": pp["lado"].map({"exp": "Exportações", "imp": "Importações"}),
        "Produto": pp["sh6"].map(lambda c: f"{cfg.ROTULO_CURTO[c]} ({c})" if c != "Total" else "Total da cadeia"),
        "País ou recorte": pp["pais_nome"], "Membro da RCEP": pp["pais"].isin(cfg.RCEP),
        f"{P1} (%)": _pct(pp[P1]), f"{P2} (%)": _pct(pp[P2]), "Variação (p.p.)": pp["var_pp"]})
    ordem = {f"{cfg.ROTULO_CURTO[c]} ({c})": i for i, c in enumerate(si.sh6_destacados())} | {"Total da cadeia": 99}
    pp = pp.sort_values(["Sentido", "Produto", f"{P2} (%)"], key=lambda s: s.map(ordem) if s.name == "Produto" else s,
                        ascending=[True, True, False])
    blocos.append(("10. Participação da Ásia, da RCEP e dos países no comércio mundial de cada produto",
                   "Figura 4. Constam Ásia, RCEP e os países com ao menos 1% em algum período.", pp))

    # 11. Maiores fluxos bilaterais
    linhas = []
    for per, anos in si.PERIODOS.items():
        f = d[d["ano"].isin(anos)].groupby(["exp", "imp"])["valor"].sum().div(len(anos)).nlargest(20)
        linhas.append(pd.DataFrame({"Período": per, "Exportador": f.index.get_level_values(0).map(ind.nome),
                                    "Importador": f.index.get_level_values(1).map(ind.nome),
                                    "Valor médio anual (US$ milhões)": f.values / 1e6}))
    blocos.append(("11. Vinte maiores fluxos bilaterais do total da cadeia", "Figura 5.",
                   pd.concat(linhas, ignore_index=True)))

    # 12. Séries citadas no texto
    x = d[d["sh6"] == "260400"]
    s = pd.DataFrame({
        "Indonésia: parcela nas exportações mundiais de minério (%)":
            _pct(x[x["exp"] == "idn"].groupby("ano")["valor"].sum() / x.groupby("ano")["valor"].sum()),
        "Indonésia: importações de minério (US$ milhões)": x[x["imp"] == "idn"].groupby("ano")["valor"].sum() / 1e6,
        "Indonésia: importações de minério das Filipinas (US$ milhões)":
            x[(x["imp"] == "idn") & (x["exp"] == "phl")].groupby("ano")["valor"].sum() / 1e6,
    })
    mt = d[(d["sh6"] == "750110") & (d["imp"] == "chn")]
    s["China: importações de mates da Rússia (US$ milhões)"] = mt[mt["exp"] == "rus"].groupby("ano")["valor"].sum() / 1e6
    s["China: importações de mates da Indonésia (US$ milhões)"] = mt[mt["exp"] == "idn"].groupby("ano")["valor"].sum() / 1e6
    blocos.append(("12. Séries citadas no texto", "Minério (260400) e mates (750110).",
                   s.reindex(cfg.ANOS).fillna(0).rename_axis("Ano").reset_index()))

    # 13. Parceiros
    res = pd.concat([pa.resumo(df, "sh6", lado, unica=True) for lado in ("exp", "imp")], ignore_index=True)
    sel = ([("chn", "imp", c) for c in ("750110", "750120", "283324", "720260", "260400")]
           + [("idn", "exp", c) for c in ("720260", "750120", "750110")] + [("phl", "exp", "260400")])
    r = pd.concat([res.query("membro == @mb and lado == @l and sh6 == @c") for mb, l, c in sel])
    r = pd.DataFrame({
        "Membro": r["membro"].map(ind.nome), "Sentido": r["lado"].map({"exp": "Exportações", "imp": "Importações"}),
        "Produto": r["sh6"].map(lambda c: f"{cfg.ROTULO_CURTO[c]} ({c})"),
        f"Valor médio anual, {P1} (US$ bilhões)": r["valor_medio_antes"] / 1e9,
        f"Valor médio anual, {P2} (US$ bilhões)": r["valor_medio_depois"] / 1e9,
        "Variação do valor (%)": r["var_valor_pct"], "Variação da quantidade (%)": r["var_qtd_pct"],
        "Variação do valor mundial do produto (%)": r["var_valor_mundo_pct"],
        "Variação da quantidade mundial do produto (%)": r["var_qtd_mundo_pct"],
        f"Principal parceiro, {P1}": r["principal_antes"].map(ind.nome),
        f"Parcela do principal parceiro, {P1} (%)": _pct(r["share_principal_antes"]),
        f"Principal parceiro, {P2}": r["principal_depois"].map(ind.nome),
        f"Parcela do principal parceiro, {P2} (%)": _pct(r["share_principal_depois"]),
        "Índice de dissimilaridade": r["indice_mudanca"], "Máximo dos placebos": r["placebo_max"],
        "Acima de todos os placebos": r["acima_placebos"]})
    blocos.append(("13. Volume e composição dos parceiros, membros e fluxos selecionados", "Tabela 1. Índice de "
                   "dissimilaridade = ½ Σ |parcela do parceiro em 2022–2024 − parcela em 2019–2021|; placebos: os "
                   "cinco pares de triênios consecutivos entre 2012 e 2021.", r))

    # 14. Etapas posteriores
    post = df[df["elo"].isin(ELOS_POSTERIORES)]
    linhas = []
    for elo in ELOS_POSTERIORES:
        e = post[post["elo"] == elo]
        for lado in ("exp", "imp"):
            sh = {}
            for per, anos in si.PERIODOS.items():
                g = e[e["ano"].isin(anos)].groupby(lado)["valor"].sum()
                sh[per] = g / g.sum()
            w = pd.DataFrame(sh).fillna(0).sort_values(P2, ascending=False).head(5)
            media = e[e["ano"].isin(si.PERIODOS[P2])]["valor"].sum() / 3 / 1e9
            linhas.append(pd.DataFrame({
                "Etapa": elo, "Valor médio anual 2022–2024 (US$ bilhões)": media,
                "Sentido": "Exportações" if lado == "exp" else "Importações", "País": w.index.map(ind.nome),
                f"{P1} (%)": _pct(w[P1]).values, f"{P2} (%)": _pct(w[P2]).values}))
    blocos.append(("14. Etapas posteriores: cinco maiores exportadores e importadores de aço inoxidável e baterias",
                   "SH6 de cada etapa em config.CADEIA; a subposição de baterias inclui baterias sem níquel.",
                   pd.concat(linhas, ignore_index=True)))
    return blocos


def leia_me():
    linhas = [
        ("Planilha de dados do capítulo sobre o comércio da cadeia do níquel e a RCEP (2012–2024)", ""),
        ("", ""),
        ("Fonte", "BACI-CEPII, versão HS2012, obtida no Observatório de Complexidade Econômica (oec.world). O BACI "
                  "reconcilia as declarações de exportadores e importadores da UN Comtrade; exportações e importações "
                  "mundiais coincidem."),
        ("Unidades", "Valores em US$ correntes; quantidades em toneladas."),
        ("Aba 'Dados brutos'", "Fluxos bilaterais anuais dos nove SH6 da cadeia destacada, 2012–2024."),
        ("Aba 'Métricas'", "Tabelas que sustentam as figuras, a tabela e os números citados no capítulo, na ordem do "
                           "texto. Percentuais em pontos (52,6 = 52,6%)."),
        ("Marco temporal", "2022, ano de entrada em vigor da RCEP, para todos os membros: 2019–2021 × 2022–2024. "
                           "Mianmar fica fora das comparações por país."),
        ("RCEP", "Austrália, Brunei, Camboja, China, Coreia do Sul, Filipinas, Indonésia, Japão, Laos, Malásia, Mianmar, "
                 "Nova Zelândia, Singapura, Tailândia e Vietnã."),
        ("ASEAN", "Brunei, Camboja, Filipinas, Indonésia, Laos, Malásia, Mianmar, Singapura, Tailândia e Vietnã."),
        ("", ""),
        ("SH6 da cadeia destacada", ""),
    ]
    linhas += [(sh, f"{cfg.ROTULO_CURTO[sh]}: {si.DESCRICAO_SH6[sh]} ({cfg.SH6_ELO[sh]})") for sh in si.sh6_destacados()]
    linhas += [("", ""), ("Observações", "720260 inclui o ferro-gusa de níquel (NPI); 750120 inclui o precipitado de "
                                         "hidróxido misto (MHP). Aço inoxidável e baterias ficam fora do agregado.")]
    return pd.DataFrame(linhas, columns=["Item", "Descrição"])


def gravar(df, bilateral, destino=ARQ_PLANILHA):
    """Grava a planilha com as abas Leia-me, Dados brutos e Métricas; devolve (brutos, blocos)."""
    brutos = dados_brutos(df)
    blocos = metricas(df, bilateral)
    with pd.ExcelWriter(destino, engine="xlsxwriter") as xls:
        wb = xls.book
        tit = wb.add_format({"bold": True, "font_size": 11})
        nota = wb.add_format({"italic": True, "font_color": "#555555"})
        cab = wb.add_format({"bold": True, "bg_color": "#DDEBF7", "border": 1, "text_wrap": True, "valign": "top"})
        num = wb.add_format({"num_format": "#,##0.0"})
        dec2 = wb.add_format({"num_format": "0.00"})
        inteiro = wb.add_format({"num_format": "#,##0"})
        quebra = wb.add_format({"text_wrap": True, "valign": "top"})

        lm = leia_me()
        lm.to_excel(xls, sheet_name="Leia-me", index=False, header=False)
        ws = xls.sheets["Leia-me"]
        ws.set_column(0, 0, 26, tit)
        ws.set_column(1, 1, 110, quebra)

        brutos.to_excel(xls, sheet_name="Dados brutos", index=False, startrow=1, header=False)
        ws = xls.sheets["Dados brutos"]
        for j, c in enumerate(brutos.columns):
            ws.write(0, j, c, cab)
        ws.set_column(0, 1, 8)
        ws.set_column(2, 3, 20)
        ws.set_column(4, 7, 18)
        ws.set_column(8, 9, 20, inteiro)
        ws.freeze_panes(1, 0)
        ws.autofilter(0, 0, len(brutos), len(brutos.columns) - 1)

        ws = wb.add_worksheet("Métricas")
        xls.sheets["Métricas"] = ws
        lin = 0
        ws.write(lin, 0, FONTE, nota)
        lin += 2
        for titulo, obs, t in blocos:
            ws.write(lin, 0, titulo, tit)
            ws.write(lin + 1, 0, obs, nota)
            for j, c in enumerate(t.columns):
                ws.write(lin + 2, j, c, cab)
            for i, row in enumerate(t.itertuples(index=False), start=lin + 3):
                for j, v in enumerate(row):
                    if isinstance(v, bool):
                        ws.write(i, j, "sim" if v else "não")
                    elif isinstance(v, (int, float)) and not pd.isna(v):
                        c = t.columns[j]
                        fmt = inteiro if c == "Ano" else (dec2 if c in ("Índice de dissimilaridade", "Máximo dos placebos") else num)
                        ws.write_number(i, j, v, fmt)
                    elif pd.isna(v) if not isinstance(v, str) else False:
                        ws.write_blank(i, j, None)
                    else:
                        ws.write(i, j, v)
            ws.set_row(lin + 2, 45)
            lin += len(t) + 5
        ws.set_column(0, 0, 22)
        ws.set_column(1, 20, 16)
    return brutos, blocos
