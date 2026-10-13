"""Extração dos subconjuntos usados na análise a partir do parquet bruto do BACI.

O parquet bruto (~142 milhões de linhas) nunca é carregado inteiro em pandas: cada função lê apenas as
colunas necessárias, com filtro aplicado pelo pyarrow, e grava o resultado em `data/processed/`.
As extrações são cacheadas; `forcar=True` refaz a leitura.
"""
import logging

import pandas as pd
import pyarrow.compute as pc
import pyarrow.dataset as ds

from . import config as cfg

COLUNAS = {  # nome na base -> nome usado na análise
    "year": "ano", "exporter_id": "exp", "importer_id": "imp", "hs_code": "sh6",
    "value": "valor", "quantity": "qtd",
}


def _dataset():
    return ds.dataset(cfg.ARQ_BACI, format="parquet")


def _cache(nome, gerar, forcar):
    destino = cfg.DIR_PROC / nome
    if destino.exists() and not forcar:
        return pd.read_parquet(destino)
    cfg.DIR_PROC.mkdir(parents=True, exist_ok=True)
    df = gerar()
    df.to_parquet(destino, index=False)
    return df


def fluxos_cadeia(forcar=False):
    """Fluxos bilaterais (ano, exp, imp, sh6, valor, qtd) de todos os SH6 definidos em `config.CADEIA`."""
    def gerar():
        t = _dataset().to_table(filter=pc.field("hs_code").isin(cfg.TODOS_SH6), columns=list(COLUNAS))
        df = t.to_pandas().rename(columns=COLUNAS)
        df["ano"] = df["ano"].astype(int)
        return df
    return _cache("baci_cadeia_niquel.parquet", gerar, forcar)


def totais_anuais(forcar=False):
    """Comércio mundial total (todos os produtos) por ano: valor, número de fluxos e de produtos."""
    def gerar():
        t = _dataset().to_table(columns=["year", "value"])
        agg = t.group_by("year").aggregate([("value", "sum"), ("value", "count")])
        df = agg.to_pandas().rename(columns={"year": "ano", "value_sum": "valor", "value_count": "n_fluxos"})
        df["ano"] = df["ano"].astype(int)
        return df.sort_values("ano").reset_index(drop=True)
    return _cache("baci_totais_anuais.parquet", gerar, forcar)


def bilateral_total(forcar=False):
    """Comércio bilateral de todos os produtos (ano, exp, imp, valor), para comparar a cadeia com o
    comércio total dos membros da RCEP. Agregado em modo streaming do Polars, sem materializar a base."""
    def gerar():
        import polars as pl
        df = (pl.scan_parquet(cfg.ARQ_BACI)
              .select(pl.col("year").cast(pl.Int32).alias("ano"), pl.col("exporter_id").alias("exp"),
                      pl.col("importer_id").alias("imp"), pl.col("value").alias("valor"))
              .group_by(["ano", "exp", "imp"]).agg(pl.col("valor").sum())
              .collect(engine="streaming").to_pandas())
        df["ano"] = df["ano"].astype(int)
        return df.sort_values(["ano", "exp", "imp"]).reset_index(drop=True)
    return _cache("baci_bilateral_total.parquet", gerar, forcar)


def catalogo_produtos(forcar=False):
    """Todos os SH6 presentes na base, com descrição do OEC e valor acumulado 2012–2024."""
    def gerar():
        t = _dataset().to_table(columns=["hs_code", "product_name", "value"])
        agg = t.group_by(["hs_code", "product_name"]).aggregate([("value", "sum")])
        df = agg.to_pandas().rename(columns={"hs_code": "sh6", "product_name": "descricao_oec",
                                             "value_sum": "valor_total"})
        return df.sort_values("sh6").reset_index(drop=True)
    return _cache("baci_catalogo_produtos.parquet", gerar, forcar)


def tabela_paises(forcar=False):
    """Países da base com nome, sub-região ONU (M49) e macrorregião; versionada em `data/referencia/`."""
    destino = cfg.DIR_REF / "paises.csv"
    if destino.exists() and not forcar:
        return pd.read_csv(destino, keep_default_na=False)
    import country_converter as coco
    logging.getLogger("country_converter").setLevel(logging.ERROR)
    t = _dataset().to_table(columns=["exporter_id", "exporter_name"])
    df = (t.group_by(["exporter_id", "exporter_name"]).aggregate([]).to_pandas()
          .rename(columns={"exporter_id": "iso3", "exporter_name": "nome_oec"}))
    df["subregiao_onu"] = coco.convert(df["iso3"].str.upper().tolist(), src="ISO3", to="UNregion",
                                       not_found="")
    df["macrorregiao"] = df["subregiao_onu"].map(cfg.MACRORREGIAO).fillna("")
    df["nome"] = df["iso3"].map(cfg.NOMES_PT).fillna(df["nome_oec"])
    df["rcep"] = df["iso3"].isin(cfg.RCEP)
    df["asean"] = df["iso3"].isin(cfg.ASEAN)
    df = df.sort_values("iso3").reset_index(drop=True)
    cfg.DIR_REF.mkdir(parents=True, exist_ok=True)
    df.to_csv(destino, index=False)
    return df


def soma_bruta(sh6, ano):
    """Valor somado diretamente no parquet bruto, para validar as extrações."""
    filtro = (pc.field("hs_code") == sh6) & (pc.field("year") == ano)
    t = _dataset().to_table(filter=filtro, columns=["value"])
    return float(pc.sum(t["value"]).as_py() or 0.0), t.num_rows
