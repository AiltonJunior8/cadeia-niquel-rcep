"""Configuração central da análise de comércio da cadeia do níquel.

Este é o único arquivo a editar para mudar o escopo da análise: caminhos, anos, códigos SH6 de cada
elo da cadeia, datas de vigência da RCEP e agrupamento regional. Os notebooks e os demais módulos
leem tudo daqui.
"""
from datetime import date
from pathlib import Path

# --------------------------------------------------------------------------------------------------
# Caminhos
# --------------------------------------------------------------------------------------------------
RAIZ = Path(__file__).resolve().parents[2]
ARQ_BACI = RAIZ / "data" / "raw" / "trade_i_baci_a_12.parquet"  # BACI-CEPII HS2012 via OEC (USD correntes)
DIR_PROC = RAIZ / "data" / "processed"    # extrações intermediárias (regeneráveis, fora do git)
DIR_REF = RAIZ / "data" / "referencia"    # tabelas de referência versionadas (países, produtos)
DIR_FIG = RAIZ / "outputs" / "figuras"
DIR_TAB = RAIZ / "outputs" / "tabelas"

ANOS = list(range(2012, 2025))  # cobertura da base HS2012 no OEC


# --------------------------------------------------------------------------------------------------
# Cadeia do níquel: elo -> {SH6: rótulo}
# A ordem dos elos segue a cadeia, da extração aos usos finais. Rótulos em português para figuras.
# --------------------------------------------------------------------------------------------------
_INOX_SH4 = {  # aço inoxidável agrupado por posição SH4 para rotular as subposições
    "7218": "Aço inox: lingotes e semimanufaturados",
    "7219": "Aço inox: laminados planos (≥600 mm)",
    "7220": "Aço inox: laminados planos (<600 mm)",
    "7221": "Aço inox: fio-máquina",
    "7222": "Aço inox: barras e perfis",
    "7223": "Aço inox: fios",
}
_INOX_SH6 = [
    "721810", "721891", "721899",
    "721911", "721912", "721913", "721914", "721921", "721922", "721923", "721924",
    "721931", "721932", "721933", "721934", "721935", "721990",
    "722011", "722012", "722020", "722090",
    "722100",
    "722211", "722219", "722220", "722230", "722240",
    "722300",
]

CADEIA = {
    "1. Minério": {
        "260400": "Minérios e concentrados de níquel",
    },
    "2. Intermediários": {
        "750110": "Mates de níquel",
        "750120": "Sínteres de óxido e outros intermediários (inclui MHP)",
        "720260": "Ferroníquel (inclui NPI)",
    },
    "3. Níquel refinado": {
        "750210": "Níquel não ligado, em bruto",
        "750220": "Ligas de níquel, em bruto",
    },
    "4. Químicos de níquel": {
        "283324": "Sulfato de níquel",
        "282540": "Óxidos e hidróxidos de níquel",
        "282735": "Cloreto de níquel",
    },
    "5. Semimanufaturas e sucata": {
        "750300": "Desperdícios e sucata de níquel",
        "750400": "Pós e escamas de níquel",
        "750511": "Barras e perfis de níquel não ligado",
        "750512": "Barras e perfis de ligas de níquel",
        "750521": "Fios de níquel não ligado",
        "750522": "Fios de ligas de níquel",
        "750610": "Chapas e tiras de níquel não ligado",
        "750620": "Chapas e tiras de ligas de níquel",
        "750711": "Tubos de níquel não ligado",
        "750712": "Tubos de ligas de níquel",
        "750720": "Acessórios para tubos de níquel",
        "750810": "Telas e grades de fios de níquel",
        "750890": "Outras obras de níquel",
    },
    "6. Aço inoxidável": {c: f"{_INOX_SH4[c[:4]]} ({c})" for c in _INOX_SH6},
    "7. Baterias": {
        "850760": "Acumuladores de íons de lítio",
        "850750": "Acumuladores de níquel-hidreto metálico",
        "850730": "Acumuladores de níquel-cádmio",
        "850740": "Acumuladores de níquel-ferro",
    },
    "8. Outros usos": {
        "381511": "Catalisadores em suporte, à base de níquel",
        "740822": "Fios de cuproníquel",
        "740940": "Chapas e tiras de cuproníquel",
        "741122": "Tubos de cuproníquel",
    },
    # Elo aproximado: a subposição contém os óxidos de lítio-níquel-cobalto-manganês usados em cátodos,
    # mas também outros sais. Mantido à parte e nunca somado aos elos 1–8 nas sínteses.
    "9. Cátodos (aproximado)": {
        "284190": "Outros sais de ácidos oxometálicos (inclui cátodos NMC/NCA)",
    },
}
ELOS_APROXIMADOS = ["9. Cátodos (aproximado)"]

# SH6 do núcleo da cadeia, analisados um a um com o conjunto completo de figuras
SH6_NUCLEO = ["260400", "750110", "750120", "720260", "750210", "750220", "283324", "282540"]

# Cadeia mercantil destacada no artigo (da extração aos insumos para aço inoxidável e baterias): base das
# figuras de síntese do resumo. Aço inoxidável e baterias ficam fora porque o valor deles, dominado por
# produtos sem relação exclusiva com o níquel (baterias LFP, por exemplo), encobriria o restante da cadeia.
ELOS_DESTACADOS = ["1. Minério", "2. Intermediários", "3. Níquel refinado", "4. Químicos de níquel"]

# Rótulos curtos para as figuras de síntese
ROTULO_CURTO = {
    "260400": "Minério", "750110": "Mate", "750120": "Sínter e MHP", "720260": "Ferroníquel e NPI",
    "750210": "Níquel não ligado", "750220": "Ligas em bruto", "283324": "Sulfato",
    "282540": "Óxidos e hidróxidos", "282735": "Cloreto",
}


# Índices derivados (não editar)
SH6_ELO = {sh6: elo for elo, prods in CADEIA.items() for sh6 in prods}
SH6_ROTULO = {sh6: rot for prods in CADEIA.values() for sh6, rot in prods.items()}
TODOS_SH6 = list(SH6_ELO)

# --------------------------------------------------------------------------------------------------
# RCEP: entrada em vigor por membro (códigos ISO3 em minúsculas, como na base)
# Fontes conferidas em 06/10/2026:
#   - 1/1/2022 para os dez primeiros, Coreia 1/2/2022, Malásia 18/3/2022: Australian Border Force,
#     página do RCEP (abf.gov.au) e anúncios do MITI da Malásia.
#   - Indonésia 2/1/2023: ASEAN Secretariat, "RCEP Agreement enters into force for Indonesia" (asean.org).
#   - Filipinas 2/6/2023: MITI Malásia, "RCEP announcement for Philippines on 2 June 2023" (25/5/2023),
#     que lista 13 partes em vigor e não inclui Mianmar.
#   - Mianmar: vigência decidida bilateralmente por cada parte e não reconhecida por várias delas.
#     Tratada como None (sem data) e excluída das comparações antes/depois.
# --------------------------------------------------------------------------------------------------
RCEP_VIGENCIA = {
    "aus": date(2022, 1, 1), "brn": date(2022, 1, 1), "khm": date(2022, 1, 1),
    "chn": date(2022, 1, 1), "jpn": date(2022, 1, 1), "lao": date(2022, 1, 1),
    "nzl": date(2022, 1, 1), "sgp": date(2022, 1, 1), "tha": date(2022, 1, 1),
    "vnm": date(2022, 1, 1),
    "kor": date(2022, 2, 1),
    "mys": date(2022, 3, 18),
    "idn": date(2023, 1, 2),
    "phl": date(2023, 6, 2),   # ano de entrada parcial (7 meses em vigor em 2023)
    "mmr": None,
}
RCEP = list(RCEP_VIGENCIA)
ASEAN = ["brn", "khm", "idn", "lao", "mys", "mmr", "phl", "sgp", "tha", "vnm"]
ANO_RCEP = 2022  # primeiro ano de vigência do acordo (para o bloco como um todo)

# --------------------------------------------------------------------------------------------------
# Regiões: sub-região ONU (M49, via country_converter) -> macrorregião usada nas figuras
# --------------------------------------------------------------------------------------------------
MACRORREGIAO = {
    "Eastern Asia": "Ásia Oriental",
    "South-eastern Asia": "Sudeste Asiático",
    "Southern Asia": "Sul da Ásia",
    "Western Asia": "Ásia Ocidental e Central",
    "Central Asia": "Ásia Ocidental e Central",
    "Northern Europe": "Europa", "Western Europe": "Europa",
    "Southern Europe": "Europa", "Eastern Europe": "Europa",
    "Northern America": "América do Norte",
    "Central America": "América Latina e Caribe", "Caribbean": "América Latina e Caribe",
    "South America": "América Latina e Caribe",
    "Northern Africa": "África", "Western Africa": "África", "Eastern Africa": "África",
    "Middle Africa": "África", "Southern Africa": "África",
    "Australia and New Zealand": "Oceania", "Melanesia": "Oceania",
    "Micronesia": "Oceania", "Polynesia": "Oceania",
}

# Macrorregiões que compõem a Ásia nas figuras de síntese
ASIA = ["Ásia Oriental", "Sudeste Asiático", "Sul da Ásia", "Ásia Ocidental e Central"]

# Nomes em português dos países (figuras, tabelas e planilha)
NOMES_PT = {
    "chn": "China", "idn": "Indonésia", "phl": "Filipinas", "jpn": "Japão", "kor": "Coreia do Sul",
    "aus": "Austrália", "nzl": "Nova Zelândia", "mys": "Malásia", "sgp": "Singapura",
    "tha": "Tailândia", "vnm": "Vietnã", "khm": "Camboja", "lao": "Laos", "mmr": "Mianmar",
    "brn": "Brunei", "twn": "Taiwan", "hkg": "Hong Kong", "ind": "Índia", "rus": "Rússia",
    "can": "Canadá", "usa": "Estados Unidos", "mex": "México", "bra": "Brasil", "col": "Colômbia",
    "gtm": "Guatemala", "cub": "Cuba", "dom": "Rep. Dominicana", "ncl": "Nova Caledônia",
    "nor": "Noruega", "fin": "Finlândia", "swe": "Suécia", "deu": "Alemanha", "fra": "França",
    "gbr": "Reino Unido", "nld": "Países Baixos", "bel": "Bélgica", "ita": "Itália",
    "esp": "Espanha", "aut": "Áustria", "che": "Suíça", "pol": "Polônia", "hun": "Hungria",
    "cze": "Tchéquia", "svk": "Eslováquia", "ukr": "Ucrânia", "tur": "Turquia", "zaf": "África do Sul",
    "mdg": "Madagascar", "zwe": "Zimbábue", "bwa": "Botsuana", "zmb": "Zâmbia", "tza": "Tanzânia",
    "cod": "RD Congo", "mkd": "Macedônia do Norte", "grc": "Grécia", "alb": "Albânia",
    "kaz": "Cazaquistão", "are": "Emirados Árabes", "sau": "Arábia Saudita", "isr": "Israel",
    "png": "Papua-Nova Guiné", "ven": "Venezuela", "dnk": "Dinamarca", "irl": "Irlanda",
    "prt": "Portugal", "rou": "Romênia", "svn": "Eslovênia", "est": "Estônia", "ltu": "Lituânia",
    "lva": "Letônia", "blr": "Belarus", "chl": "Chile", "arg": "Argentina", "per": "Peru",
}
# Demais economias da base, para que tabelas e planilhas não misturem nomes em inglês e português
NOMES_PT.update({
    "abw": "Aruba", "afg": "Afeganistão", "ago": "Angola", "aia": "Anguila", "and": "Andorra",
    "arm": "Armênia", "asm": "Samoa Americana", "atf": "Terras Austrais Francesas", "atg": "Antígua e Barbuda",
    "aze": "Azerbaijão", "bdi": "Burundi", "ben": "Benin", "bes": "Bonaire", "bfa": "Burkina Faso",
    "bgd": "Bangladesh", "bgr": "Bulgária", "bhr": "Bahrein", "bhs": "Bahamas", "bih": "Bósnia e Herzegovina",
    "blm": "São Bartolomeu", "blz": "Belize", "bmu": "Bermudas", "bol": "Bolívia", "brb": "Barbados",
    "btn": "Butão", "caf": "República Centro-Africana", "cck": "Ilhas Cocos (Keeling)", "civ": "Costa do Marfim",
    "cmr": "Camarões", "cog": "República do Congo", "cok": "Ilhas Cook", "com": "Comores", "cpv": "Cabo Verde",
    "cri": "Costa Rica", "cuw": "Curaçao", "cxr": "Ilha Christmas", "cym": "Ilhas Cayman", "cyp": "Chipre",
    "dji": "Djibuti", "dma": "Dominica", "dza": "Argélia", "ecu": "Equador", "egy": "Egito", "eri": "Eritreia",
    "eth": "Etiópia", "fji": "Fiji", "flk": "Ilhas Malvinas", "fsm": "Micronésia", "gab": "Gabão",
    "geo": "Geórgia", "gha": "Gana", "gib": "Gibraltar", "gin": "Guiné", "gmb": "Gâmbia", "gnb": "Guiné-Bissau",
    "gnq": "Guiné Equatorial", "grd": "Granada", "grl": "Groenlândia", "gum": "Guam", "guy": "Guiana",
    "hnd": "Honduras", "hrv": "Croácia", "hti": "Haiti", "iot": "Território Britânico do Oceano Índico",
    "irn": "Irã", "irq": "Iraque", "isl": "Islândia", "jam": "Jamaica", "jor": "Jordânia", "ken": "Quênia",
    "kgz": "Quirguistão", "kir": "Kiribati", "kna": "São Cristóvão e Névis", "kwt": "Kuwait", "lbn": "Líbano",
    "lbr": "Libéria", "lby": "Líbia", "lca": "Santa Lúcia", "lka": "Sri Lanka", "lso": "Lesoto",
    "lux": "Luxemburgo", "mac": "Macau", "maf": "São Martinho", "mar": "Marrocos", "mda": "Moldávia",
    "mdv": "Maldivas", "mhl": "Ilhas Marshall", "mli": "Mali", "mlt": "Malta", "mne": "Montenegro",
    "mng": "Mongólia", "mnp": "Ilhas Marianas do Norte", "moz": "Moçambique", "mrt": "Mauritânia",
    "msr": "Montserrat", "mus": "Maurício", "mwi": "Malawi", "myt": "Mayotte", "nam": "Namíbia", "ner": "Níger",
    "nfk": "Ilha Norfolk", "nga": "Nigéria", "nic": "Nicarágua", "niu": "Niue", "npl": "Nepal", "nru": "Nauru",
    "omn": "Omã", "pak": "Paquistão", "pan": "Panamá", "pcn": "Ilhas Pitcairn", "plw": "Palau",
    "prk": "Coreia do Norte", "pry": "Paraguai", "pse": "Palestina", "pyf": "Polinésia Francesa", "qat": "Catar",
    "rwa": "Ruanda", "sdn": "Sudão", "sen": "Senegal", "shn": "Santa Helena", "slb": "Ilhas Salomão",
    "sle": "Serra Leoa", "slv": "El Salvador", "smr": "San Marino", "som": "Somália",
    "spm": "São Pedro e Miquelão", "srb": "Sérvia", "ssd": "Sudão do Sul", "stp": "São Tomé e Príncipe",
    "sur": "Suriname", "swz": "Essuatíni", "syc": "Seicheles", "syr": "Síria", "tca": "Ilhas Turcas e Caicos",
    "tcd": "Chade", "tgo": "Togo", "tjk": "Tajiquistão", "tkl": "Tokelau", "tkm": "Turcomenistão",
    "tls": "Timor-Leste", "ton": "Tonga", "tto": "Trinidad e Tobago", "tun": "Tunísia", "tuv": "Tuvalu",
    "uga": "Uganda", "ury": "Uruguai", "uzb": "Uzbequistão", "vct": "São Vicente e Granadinas",
    "vgb": "Ilhas Virgens Britânicas", "vut": "Vanuatu", "wlf": "Wallis e Futuna", "wsm": "Samoa", "yem": "Iêmen",
})
