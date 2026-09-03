"""Shared presentation helpers; analytical transformations live in the QMDs and in `epi_rates.py`."""
from pathlib import Path
from html import escape
import numbers
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from IPython.display import HTML, display

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output_files" / "consolidacion"
DATA = ROOT / "data"
POSITION_LABELS = {
    "principal": "Principal",
    "solo_secundario": "Solo secundario",
    "principal_y_secundario": "Principal y secundario",
    "mixto_mismo_dia": "Posiciones mixtas el mismo día",
    "cualquiera": "Cualquier posición",
}
ROLE_ORDER = ["principal", "principal_y_secundario", "solo_secundario", "cualquiera"]
DEFINITION_LABELS = {
    "autismo_F840": "Autismo específico (F84.0)",
    "TEA_operacional": "TEA operacional (F84.0/.1/.5/.8/.9)",
    "F84_historico": "F84 histórico (todas las subcategorías)",
}
GROUP_LABELS = {
    "Animo_ansiedad_estres": "Ánimo, ansiedad y estrés",
    "Epilepsia": "Epilepsia",
    "Signos_desarrollo_habla": "Signos del desarrollo y del habla",
    "Lenguaje_aprendizaje_desarrollo": "Lenguaje, aprendizaje y desarrollo",
    "Conducta_emociones_infancia": "Conducta y emociones en la infancia",
    "Discapacidad_intelectual": "Discapacidad intelectual",
    "Hiperactividad_atencion": "Hiperactividad y atención",
    "Psicosis": "Psicosis",
    "Audicion": "Audición",
}
SUBCODE_LABELS = {
    "F84": "F84 sin subcategoría",
    "F840": "F84.0 Autismo infantil",
    "F841": "F84.1 Autismo atípico",
    "F842": "F84.2 Síndrome de Rett",
    "F843": "F84.3 Trastorno desintegrativo",
    "F844": "F84.4 Hiperactividad con retraso mental y estereotipias",
    "F845": "F84.5 Síndrome de Asperger",
    "F848": "F84.8 Otros TGD",
    "F849": "F84.9 TGD no especificado",
}
AGE_GROUPS = [f"{i}-{i + 4}" for i in range(0, 80, 5)] + ["80+"]
AGE_BANDS = ["0-4", "5-9", "10-14", "15-19", "20-29", "30-44", "45+"]
LOS_BINS = ["0", "1", "2", "3-4", "5-7", "8-14", "15-30", "31-90", "91+"]
SEX_LABELS = {"HOMBRE": "Hombres", "MUJER": "Mujeres", "TOTAL": "Ambos sexos", "Hombres": "Hombres", "Mujeres": "Mujeres"}
MONTHS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
REGION_NAMES = {
    15: "Arica y Parinacota", 1: "Tarapacá", 2: "Antofagasta", 3: "Atacama", 4: "Coquimbo",
    5: "Valparaíso", 13: "Metropolitana", 6: "O'Higgins", 7: "Maule", 16: "Ñuble", 8: "Biobío",
    9: "La Araucanía", 14: "Los Ríos", 10: "Los Lagos", 11: "Aysén", 12: "Magallanes",
}
REGION_ORDER = [15, 1, 2, 3, 4, 5, 13, 6, 7, 16, 8, 9, 14, 10, 11, 12]
COLORS = ["#167482", "#405d99", "#b9783c", "#738779", "#8c4a5b", "#5b7f3f", "#6d6d6d"]
SEX_COLORS = {"HOMBRE": "#405d99", "MUJER": "#b9783c", "TOTAL": "#167482", "Hombres": "#405d99", "Mujeres": "#b9783c"}
CLUSTER_COLORS = {"Alto-Alto": "#b2182b", "Bajo-Bajo": "#2166ac", "Alto-Bajo": "#f4a582", "Bajo-Alto": "#92c5de",
                  "No significativo": "#e8e8e8"}
ICD_CHAPTERS = [
    ("A00", "B99", "Infecciosas y parasitarias"), ("C00", "D48", "Neoplasias"), ("D50", "D89", "Sangre e inmunidad"),
    ("E00", "E90", "Endocrinas, nutricionales y metabólicas"), ("F00", "F99", "Trastornos mentales y del comportamiento"),
    ("G00", "G99", "Sistema nervioso"), ("H00", "H59", "Ojo y anexos"), ("H60", "H95", "Oído y apófisis mastoides"),
    ("I00", "I99", "Sistema circulatorio"), ("J00", "J99", "Sistema respiratorio"), ("K00", "K93", "Sistema digestivo"),
    ("L00", "L99", "Piel y tejido subcutáneo"), ("M00", "M99", "Osteomuscular y tejido conectivo"),
    ("N00", "N99", "Sistema genitourinario"), ("O00", "O99", "Embarazo, parto y puerperio"),
    ("P00", "P96", "Afecciones del período perinatal"), ("Q00", "Q99", "Malformaciones congénitas"),
    ("R00", "R99", "Síntomas y signos no clasificados"), ("S00", "T98", "Traumatismos y envenenamientos"),
    ("V01", "Y98", "Causas externas"), ("Z00", "Z99", "Factores que influyen en el estado de salud"),
]
MENTAL_BLOCKS = [
    ("F00", "F09", "Trastornos mentales orgánicos"), ("F10", "F19", "Uso de sustancias psicoactivas"),
    ("F20", "F29", "Esquizofrenia y psicosis"), ("F30", "F39", "Trastornos del ánimo"),
    ("F40", "F48", "Ansiedad, estrés y somatomorfos"), ("F50", "F59", "Síndromes conductuales fisiológicos"),
    ("F60", "F69", "Personalidad y comportamiento adulto"), ("F70", "F79", "Discapacidad intelectual"),
    ("F80", "F83", "Desarrollo del habla, aprendizaje y motor"), ("F84", "F84", "Trastornos generalizados del desarrollo"),
    ("F88", "F89", "Otros trastornos del desarrollo psicológico"), ("F90", "F90", "Trastornos hipercinéticos"),
    ("F91", "F98", "Conducta y emociones de inicio en la infancia"), ("F99", "F99", "Trastorno mental no especificado"),
]
ICD_LABELS = {
    "G40": "Epilepsia", "G41": "Estado epiléptico", "J45": "Asma", "J46": "Estado asmático", "E66": "Obesidad",
    "F32": "Episodio depresivo", "F33": "Trastorno depresivo recurrente", "F41": "Otros trastornos de ansiedad",
    "F43": "Reacción a estrés grave y adaptación", "F90": "Trastornos hipercinéticos", "F91": "Trastornos de la conducta",
    "F92": "Trastornos mixtos de conducta y emociones", "F93": "Trastornos emocionales de la infancia",
    "F94": "Trastornos del funcionamiento social infantil", "F95": "Trastornos por tics", "F98": "Otros trastornos emocionales y de conducta infantiles",
    "F60": "Trastornos específicos de la personalidad", "F63": "Trastornos de los hábitos e impulsos",
    "F70": "Retraso mental leve", "F71": "Retraso mental moderado", "F72": "Retraso mental grave", "F73": "Retraso mental profundo",
    "F79": "Retraso mental no especificado", "F80": "Trastornos del desarrollo del habla y lenguaje", "F81": "Trastornos del aprendizaje escolar",
    "F82": "Trastorno del desarrollo de la función motriz", "F83": "Trastornos mixtos del desarrollo", "F88": "Otros trastornos del desarrollo psicológico",
    "F89": "Trastorno del desarrollo psicológico no especificado", "F50": "Trastornos de la ingestión de alimentos",
    "F51": "Trastornos no orgánicos del sueño", "F20": "Esquizofrenia", "F25": "Trastornos esquizoafectivos", "F29": "Psicosis no orgánica no especificada",
    "F23": "Trastornos psicóticos agudos", "F31": "Trastorno afectivo bipolar", "F10": "Trastornos por uso de alcohol",
    "F12": "Trastornos por uso de cannabinoides", "F19": "Uso de múltiples drogas", "F06": "Otros trastornos mentales por lesión cerebral",
    "F07": "Trastornos de personalidad por enfermedad cerebral", "F09": "Trastorno mental orgánico no especificado",
    "Z92": "Historia personal de tratamiento médico", "Z91": "Historia personal de factores de riesgo",
    "Z87": "Historia personal de otras enfermedades", "Z88": "Historia personal de alergia", "Z86": "Historia personal de otras enfermedades",
    "Z63": "Problemas relacionados con el grupo de apoyo primario", "Z51": "Otra atención médica", "Z53": "Atención no realizada",
    "Z61": "Problemas relacionados con hechos negativos en la niñez", "Z62": "Problemas relacionados con la crianza",
    "Z65": "Problemas psicosociales", "Z73": "Problemas relacionados con dificultades de la vida", "Z00": "Examen general",
    "Z01": "Otros exámenes especiales", "Z03": "Observación por sospecha", "Z04": "Examen y observación por otras razones",
    "Z71": "Consulta y consejo", "Z74": "Problemas relacionados con dependencia del cuidador", "Z75": "Problemas relacionados con facilidades de atención",
    "Z76": "Contacto con servicios de salud en otras circunstancias", "Z80": "Historia familiar de neoplasia",
    "Z81": "Historia familiar de trastornos mentales", "Z82": "Historia familiar de discapacidades",
    "Z96": "Presencia de implantes funcionales", "Z98": "Otros estados posquirúrgicos", "Z99": "Dependencia de máquinas y dispositivos",
    "R45": "Síntomas del estado emocional", "R46": "Síntomas de apariencia y comportamiento", "R56": "Convulsiones",
    "R62": "Retardo del desarrollo esperado", "R63": "Síntomas de ingestión de alimentos y líquidos", "R47": "Trastornos del habla",
    "R48": "Dislexia y otras disfunciones simbólicas", "R10": "Dolor abdominal", "R11": "Náusea y vómito", "R50": "Fiebre",
    "R06": "Anormalidades de la respiración", "R09": "Otros síntomas respiratorios", "R41": "Síntomas cognitivos",
    "J96": "Insuficiencia respiratoria", "J12": "Neumonía viral", "J15": "Neumonía bacteriana", "J18": "Neumonía, organismo no especificado",
    "J21": "Bronquiolitis aguda", "J20": "Bronquitis aguda", "J06": "Infección respiratoria superior aguda", "J35": "Enfermedades crónicas de amígdalas y adenoides",
    "J05": "Laringitis obstructiva aguda", "J22": "Infección respiratoria inferior aguda", "J98": "Otros trastornos respiratorios",
    "K59": "Otros trastornos funcionales del intestino", "K02": "Caries dental", "K04": "Enfermedades de la pulpa y periapicales",
    "K08": "Otros trastornos de dientes y estructuras", "K00": "Trastornos del desarrollo dentario", "K01": "Dientes incluidos e impactados",
    "K21": "Enfermedad por reflujo gastroesofágico", "K35": "Apendicitis aguda", "K40": "Hernia inguinal", "K29": "Gastritis y duodenitis",
    "K52": "Otras gastroenteritis y colitis", "K56": "Íleo paralítico y obstrucción intestinal", "K80": "Colelitiasis", "K92": "Otras enfermedades del sistema digestivo",
    "N47": "Prepucio redundante, fimosis y parafimosis", "N39": "Otros trastornos del sistema urinario", "N10": "Nefritis tubulointersticial aguda",
    "N43": "Hidrocele y espermatocele", "N45": "Orquitis y epididimitis", "Q90": "Síndrome de Down", "Q89": "Otras malformaciones congénitas",
    "Q99": "Otras anomalías cromosómicas", "Q87": "Otros síndromes de malformaciones congénitas", "Q38": "Malformaciones de lengua, boca y faringe",
    "E10": "Diabetes mellitus tipo 1", "E11": "Diabetes mellitus tipo 2", "E86": "Depleción de volumen", "E87": "Otros trastornos hidroelectrolíticos",
    "E44": "Desnutrición proteicocalórica moderada", "E46": "Desnutrición proteicocalórica no especificada", "E78": "Trastornos del metabolismo de lipoproteínas",
    "E03": "Otro hipotiroidismo", "E34": "Otros trastornos endocrinos", "E30": "Trastornos de la pubertad", "E22": "Hiperfunción de la hipófisis",
    "G80": "Parálisis cerebral", "G93": "Otros trastornos del encéfalo", "G47": "Trastornos del sueño", "G43": "Migraña", "G91": "Hidrocefalia",
    "G25": "Otros trastornos extrapiramidales y del movimiento", "G24": "Distonía", "G12": "Atrofia muscular espinal", "G71": "Trastornos musculares primarios",
    "G96": "Otros trastornos del sistema nervioso central", "H90": "Hipoacusia conductiva y neurosensorial", "H91": "Otras hipoacusias",
    "H65": "Otitis media no supurativa", "H66": "Otitis media supurativa", "H50": "Otros estrabismos", "H52": "Trastornos de la acomodación y refracción",
    "H26": "Otras cataratas", "H10": "Conjuntivitis", "I10": "Hipertensión esencial", "I47": "Taquicardia paroxística", "L20": "Dermatitis atópica",
    "L02": "Absceso cutáneo, furúnculo y ántrax", "L03": "Celulitis", "M41": "Escoliosis", "M79": "Otros trastornos de tejidos blandos",
    "S06": "Traumatismo intracraneal", "S00": "Traumatismo superficial de la cabeza", "S01": "Herida de la cabeza", "S52": "Fractura del antebrazo",
    "S42": "Fractura del hombro y brazo", "S72": "Fractura del fémur", "S82": "Fractura de pierna y tobillo", "S61": "Herida de muñeca y mano",
    "S62": "Fractura a nivel de la muñeca y mano", "S32": "Fractura de columna lumbar y pelvis", "S02": "Fractura de huesos del cráneo y cara",
    "T39": "Envenenamiento por analgésicos no opiáceos", "T42": "Envenenamiento por antiepilépticos, sedantes e hipnóticos",
    "T43": "Envenenamiento por psicotrópicos", "T50": "Envenenamiento por otros medicamentos", "T36": "Envenenamiento por antibióticos sistémicos",
    "T78": "Efectos adversos no clasificados", "T14": "Traumatismo de región no especificada", "T30": "Quemadura de región no especificada",
    "T18": "Cuerpo extraño en tubo digestivo", "T17": "Cuerpo extraño en vías respiratorias", "X60": "Envenenamiento autoinfligido por analgésicos",
    "X61": "Envenenamiento autoinfligido por psicotrópicos", "X62": "Envenenamiento autoinfligido por narcóticos", "X64": "Envenenamiento autoinfligido por otras drogas",
    "X70": "Lesión autoinfligida por ahorcamiento", "X78": "Lesión autoinfligida por objeto cortante", "X84": "Lesión autoinfligida por medios no especificados",
    "Y83": "Complicaciones de intervención quirúrgica", "Y84": "Complicaciones de otros procedimientos", "Y92": "Lugar de ocurrencia",
    "W19": "Caída no especificada", "W01": "Caída en el mismo nivel", "W10": "Caída en o desde escaleras", "W18": "Otras caídas en el mismo nivel",
    "A09": "Diarrea y gastroenteritis de presunto origen infeccioso", "A08": "Infecciones intestinales virales", "B34": "Infección viral de sitio no especificado",
    "B97": "Agentes virales como causa de enfermedades", "B95": "Estreptococos y estafilococos como causa", "B96": "Otros agentes bacterianos como causa",
    "U07": "COVID-19", "D50": "Anemia por deficiencia de hierro", "D64": "Otras anemias", "D69": "Púrpura y otras afecciones hemorrágicas",
    "C91": "Leucemia linfoide", "C71": "Tumor maligno del encéfalo", "D33": "Tumor benigno del encéfalo y SNC", "P07": "Trastornos relacionados con gestación corta y bajo peso",
    "O80": "Parto único espontáneo", "O82": "Parto único por cesárea", "O34": "Atención materna por anormalidad de órganos pélvicos",
}


def read_result(name: str, **kwargs) -> pd.DataFrame:
    path = OUTPUT / name
    if not path.is_file():
        raise FileNotFoundError(
            f"Falta {path.name}. Ejecute las extracciones indicadas en el README antes de renderizar."
        )
    dtypes = {"code": str, "CodigoPrestacion": str, "IdRegion": str, "IdComuna": str, "IdEstablecimiento": str,
              "first_principal": str, "last_prior_principal": str, "COD_HOSPITAL": str, "code3": str}
    return pd.read_csv(path, dtype=dtypes, **kwargs)


def number(value, decimals=0):
    if value is None or (isinstance(value, float) and np.isnan(value)) or (not isinstance(value, str) and pd.isna(value)):
        return "—"
    if isinstance(value, numbers.Number):
        if isinstance(value, float) and np.isinf(value):
            return "∞"
        return f"{value:,.{decimals}f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return str(value)


def ci(lo, hi, decimals=1):
    if pd.isna(lo) or pd.isna(hi):
        return "—"
    return f"{number(lo, decimals)} a {number(hi, decimals)}"


def pct(numerator, denominator, decimals=1):
    return number(100 * numerator / denominator, decimals) + "%" if denominator else "—"


def show_table(frame: pd.DataFrame, caption: str, decimals=None):
    """Escaped, scrollable tables; column-specific precision keeps years integral."""
    decimals = decimals or {}
    frame = frame.copy()
    frame.columns.name = None
    formatters = {c: (lambda v, d=decimals.get(c, 0): number(v, d)) for c in frame.columns}
    for column in ["Año", "Año inicial", "Año final", "Mes", "Código de región", "CUT"]:
        if column in frame.columns:
            formatters[column] = lambda v: "—" if pd.isna(v) else (str(int(v)) if isinstance(v, numbers.Number) else str(v))
    table = frame.to_html(index=False, escape=True, border=0, na_rep="—", formatters=formatters,
                          classes="table table-striped table-sm")
    caption_html = f"<caption>{escape(caption)}</caption>"
    table = table.replace("<thead>", caption_html + "<thead>", 1)
    display(HTML(f'<div class="analysis-table" role="region" aria-label="{escape(caption)}" tabindex="0">{table}</div>'))


def kpis(items):
    cards = "".join(f'<div class="metric"><strong>{escape(str(value))}</strong><span>{escape(label)}</span></div>'
                    for value, label in items)
    display(HTML(f'<div class="metrics">{cards}</div>'))


def note(text: str):
    display(HTML(f'<p class="source-note">{escape(text)}</p>'))


def plot_style():
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.titleweight": "bold", "figure.dpi": 130, "savefig.dpi": 170,
                         "axes.grid": True, "grid.alpha": .25, "legend.frameon": False})


def share(numerator, denominator):
    return 100 * numerator / denominator if denominator else float("nan")


def icd_label(code3: str) -> str:
    return ICD_LABELS.get(code3, "")


def icd_chapter(code3: str) -> str:
    code = str(code3).upper()[:3]
    for start, end, label in ICD_CHAPTERS:
        if start <= code <= end:
            return label
    return "Otros o no válidos"


def mental_block(code3: str) -> str:
    code = str(code3).upper()[:3]
    for start, end, label in MENTAL_BLOCKS:
        if start <= code <= end:
            return label
    return "No F"


def weighted_quantile(values, weights, quantile):
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)
    order = np.argsort(values)
    values, weights = values[order], weights[order]
    cumulative = np.cumsum(weights)
    if cumulative[-1] == 0:
        return np.nan
    return float(np.interp(quantile * cumulative[-1], cumulative, values))


def load_comunas(simplify: float = 400.0):
    """Continental comuna polygons keyed by CUT code; simplified for plotting."""
    import geopandas as gpd
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        shapes = gpd.read_file(DATA / "comunas.shp")
    shapes = shapes.loc[shapes.cod_comuna > 0, ["cod_comuna", "Comuna", "codregion", "geometry"]].rename(
        columns={"cod_comuna": "cut_comuna"})
    shapes["geometry"] = shapes.geometry.simplify(simplify)
    return shapes


def load_regions(simplify: float = 800.0):
    import geopandas as gpd
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        shapes = gpd.read_file(DATA / "Regional.shp")
    shapes = shapes.loc[shapes.codregion > 0, ["codregion", "Region", "geometry"]].rename(columns={"codregion": "cut_region"})
    shapes["geometry"] = shapes.geometry.simplify(simplify)
    return shapes


# Continental extent in EPSG:3857 (longitude -76.5 to -66.0, latitude -56.3 to -17.4); excludes oceanic islands.
CONTINENTAL_EXTENT = (-8_516_000, -7_620_000, -7_347_000, -1_968_000)


def continental_bounds(shapes=None):
    """Fixed bounding box that excludes oceanic islands so that maps stay compact."""
    return CONTINENTAL_EXTENT


def choropleth(ax, shapes, column, title, cmap="YlGnBu", legend_label="", clip_quantile=0.98, diverging_center=None,
               missing_color="#f2f2f2"):
    """Comuna or region choropleth; extreme values are clipped at a quantile to keep the scale readable."""
    from matplotlib.colors import Normalize, TwoSlopeNorm
    data = shapes.copy()
    values = data[column].astype(float)
    finite = values.dropna()
    if finite.empty:
        data.plot(color=missing_color, ax=ax)
        ax.set_axis_off()
        ax.set_title(title, fontsize=10)
        return
    vmax = float(np.nanquantile(finite, clip_quantile)) if clip_quantile else float(finite.max())
    vmin = float(np.nanquantile(finite, 1 - clip_quantile)) if (clip_quantile and diverging_center is not None) else float(finite.min())
    if diverging_center is not None:
        spread = max(diverging_center - vmin, vmax - diverging_center, 1e-9)
        norm = TwoSlopeNorm(vcenter=diverging_center, vmin=diverging_center - spread, vmax=diverging_center + spread)
    else:
        norm = Normalize(vmin=vmin, vmax=vmax)
    data.plot(column=column, cmap=cmap, norm=norm, linewidth=.15, edgecolor="#777777", ax=ax, legend=True,
              missing_kwds={"color": missing_color, "edgecolor": "#999999", "linewidth": .15, "label": "Sin datos"},
              legend_kwds={"label": legend_label, "shrink": .5, "pad": .01, "extend": "max" if diverging_center is None else "both"})
    minx, miny, maxx, maxy = continental_bounds(shapes)
    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)
    ax.set_axis_off()
    ax.set_title(title, fontsize=10)


def cluster_map(ax, shapes, column, title):
    from matplotlib.patches import Patch
    colors = shapes[column].map(CLUSTER_COLORS).fillna("#ffffff")
    shapes.plot(color=colors, linewidth=.15, edgecolor="#777777", ax=ax)
    minx, miny, maxx, maxy = continental_bounds(shapes)
    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)
    ax.set_axis_off()
    ax.set_title(title, fontsize=10)
    handles = [Patch(facecolor=color, edgecolor="#555555", label=label) for label, color in CLUSTER_COLORS.items()]
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.0, 1.0), fontsize=7, frameon=False)
