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
    "solo_secundario": "Secondary only",
    "principal_y_secundario": "Principal and secondary",
    "mixto_mismo_dia": "Mixed positions on the same day",
    "cualquiera": "Any position",
}
ROLE_ORDER = ["principal", "principal_y_secundario", "solo_secundario", "cualquiera"]
DEFINITION_LABELS = {
    "autismo_F840": "Specific autism (F84.0)",
    "TEA_operacional": "Operational ASD (F84.0/.1/.5/.8/.9)",
    "F84_historico": "Historical F84 (all subcategories)",
}
GROUP_LABELS = {
    "Animo_ansiedad_estres": "Mood, anxiety and stress",
    "Epilepsia": "Epilepsy",
    "Signos_desarrollo_habla": "Developmental and speech signs",
    "Lenguaje_aprendizaje_desarrollo": "Language, learning and development",
    "Conducta_emociones_infancia": "Childhood conduct and emotions",
    "Discapacidad_intelectual": "Intellectual disability",
    "Hiperactividad_atencion": "Hyperactivity and attention",
    "Psicosis": "Psychosis",
    "Audicion": "Hearing",
}
SUBCODE_LABELS = {
    "F84": "F84 without subcategory",
    "F840": "F84.0 Childhood autism",
    "F841": "F84.1 Atypical autism",
    "F842": "F84.2 Rett syndrome",
    "F843": "F84.3 Disintegrative disorder",
    "F844": "F84.4 Overactive disorder with mental retardation and stereotyped movements",
    "F845": "F84.5 Asperger syndrome",
    "F848": "F84.8 Other PDD",
    "F849": "F84.9 PDD, unspecified",
}
AGE_GROUPS = [f"{i}-{i + 4}" for i in range(0, 80, 5)] + ["80+"]
AGE_BANDS = ["0-4", "5-9", "10-14", "15-19", "20-29", "30-44", "45+"]
LOS_BINS = ["0", "1", "2", "3-4", "5-7", "8-14", "15-30", "31-90", "91+"]
SEX_LABELS = {"HOMBRE": "Males", "MUJER": "Females", "TOTAL": "Both sexes", "Hombres": "Males", "Mujeres": "Females"}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
REGION_NAMES = {
    15: "Arica y Parinacota", 1: "Tarapacá", 2: "Antofagasta", 3: "Atacama", 4: "Coquimbo",
    5: "Valparaíso", 13: "Metropolitan", 6: "O'Higgins", 7: "Maule", 16: "Ñuble", 8: "Biobío",
    9: "La Araucanía", 14: "Los Ríos", 10: "Los Lagos", 11: "Aysén", 12: "Magallanes",
}
REGION_ORDER = [15, 1, 2, 3, 4, 5, 13, 6, 7, 16, 8, 9, 14, 10, 11, 12]
COLORS = ["#167482", "#405d99", "#b9783c", "#738779", "#8c4a5b", "#5b7f3f", "#6d6d6d"]
SEX_COLORS = {"HOMBRE": "#405d99", "MUJER": "#b9783c", "TOTAL": "#167482", "Hombres": "#405d99", "Mujeres": "#b9783c"}
# Cluster labels are stored in Spanish in grd_spatial_lisa.csv; CLUSTER_LABELS translates them for display.
CLUSTER_COLORS = {"Alto-Alto": "#b2182b", "Bajo-Bajo": "#2166ac", "Alto-Bajo": "#f4a582", "Bajo-Alto": "#92c5de",
                  "No significativo": "#e8e8e8"}
CLUSTER_LABELS = {"Alto-Alto": "High-High", "Bajo-Bajo": "Low-Low", "Alto-Bajo": "High-Low", "Bajo-Alto": "Low-High",
                  "No significativo": "Not significant"}
ICD_CHAPTERS = [
    ("A00", "B99", "Infectious and parasitic"), ("C00", "D48", "Neoplasms"), ("D50", "D89", "Blood and immune"),
    ("E00", "E90", "Endocrine, nutritional and metabolic"), ("F00", "F99", "Mental and behavioural disorders"),
    ("G00", "G99", "Nervous system"), ("H00", "H59", "Eye and adnexa"), ("H60", "H95", "Ear and mastoid process"),
    ("I00", "I99", "Circulatory system"), ("J00", "J99", "Respiratory system"), ("K00", "K93", "Digestive system"),
    ("L00", "L99", "Skin and subcutaneous tissue"), ("M00", "M99", "Musculoskeletal and connective tissue"),
    ("N00", "N99", "Genitourinary system"), ("O00", "O99", "Pregnancy, childbirth and the puerperium"),
    ("P00", "P96", "Perinatal period conditions"), ("Q00", "Q99", "Congenital malformations"),
    ("R00", "R99", "Symptoms and signs, not elsewhere classified"), ("S00", "T98", "Injury and poisoning"),
    ("V01", "Y98", "External causes"), ("Z00", "Z99", "Factors influencing health status"),
]
MENTAL_BLOCKS = [
    ("F00", "F09", "Organic mental disorders"), ("F10", "F19", "Psychoactive substance use"),
    ("F20", "F29", "Schizophrenia and psychosis"), ("F30", "F39", "Mood disorders"),
    ("F40", "F48", "Anxiety, stress and somatoform"), ("F50", "F59", "Behavioural syndromes with physiological disturbances"),
    ("F60", "F69", "Adult personality and behaviour"), ("F70", "F79", "Intellectual disability"),
    ("F80", "F83", "Speech, scholastic and motor development"), ("F84", "F84", "Pervasive developmental disorders"),
    ("F88", "F89", "Other disorders of psychological development"), ("F90", "F90", "Hyperkinetic disorders"),
    ("F91", "F98", "Childhood-onset behavioural and emotional disorders"), ("F99", "F99", "Unspecified mental disorder"),
]
ICD_LABELS = {
    "G40": "Epilepsy", "G41": "Status epilepticus", "J45": "Asthma", "J46": "Status asthmaticus", "E66": "Obesity",
    "F32": "Depressive episode", "F33": "Recurrent depressive disorder", "F41": "Other anxiety disorders",
    "F43": "Reaction to severe stress and adjustment disorders", "F90": "Hyperkinetic disorders", "F91": "Conduct disorders",
    "F92": "Mixed disorders of conduct and emotions", "F93": "Emotional disorders of childhood",
    "F94": "Disorders of social functioning in childhood", "F95": "Tic disorders", "F98": "Other childhood behavioural and emotional disorders",
    "F60": "Specific personality disorders", "F63": "Habit and impulse disorders",
    "F70": "Mild mental retardation", "F71": "Moderate mental retardation", "F72": "Severe mental retardation", "F73": "Profound mental retardation",
    "F79": "Unspecified mental retardation", "F80": "Developmental disorders of speech and language", "F81": "Developmental disorders of scholastic skills",
    "F82": "Developmental disorder of motor function", "F83": "Mixed developmental disorders", "F88": "Other disorders of psychological development",
    "F89": "Unspecified disorder of psychological development", "F50": "Eating disorders",
    "F51": "Nonorganic sleep disorders", "F20": "Schizophrenia", "F25": "Schizoaffective disorders", "F29": "Unspecified nonorganic psychosis",
    "F23": "Acute psychotic disorders", "F31": "Bipolar affective disorder", "F10": "Alcohol use disorders",
    "F12": "Cannabinoid use disorders", "F19": "Multiple drug use", "F06": "Other mental disorders due to brain damage",
    "F07": "Personality disorders due to brain disease", "F09": "Unspecified organic mental disorder",
    "Z92": "Personal history of medical treatment", "Z91": "Personal history of risk factors",
    "Z87": "Personal history of other diseases", "Z88": "Personal history of allergy", "Z86": "Personal history of other diseases",
    "Z63": "Problems related to primary support group", "Z51": "Other medical care", "Z53": "Care not carried out",
    "Z61": "Problems related to negative life events in childhood", "Z62": "Problems related to upbringing",
    "Z65": "Psychosocial problems", "Z73": "Problems related to life-management difficulty", "Z00": "General examination",
    "Z01": "Other special examinations", "Z03": "Observation for suspected conditions", "Z04": "Examination and observation for other reasons",
    "Z71": "Counselling and advice", "Z74": "Problems related to care-provider dependency", "Z75": "Problems related to medical facilities",
    "Z76": "Contact with health services in other circumstances", "Z80": "Family history of neoplasm",
    "Z81": "Family history of mental disorders", "Z82": "Family history of disabilities",
    "Z96": "Presence of functional implants", "Z98": "Other postsurgical states", "Z99": "Dependence on machines and devices",
    "R45": "Symptoms involving emotional state", "R46": "Symptoms involving appearance and behaviour", "R56": "Convulsions",
    "R62": "Lack of expected development", "R63": "Symptoms concerning food and fluid intake", "R47": "Speech disturbances",
    "R48": "Dyslexia and other symbolic dysfunctions", "R10": "Abdominal pain", "R11": "Nausea and vomiting", "R50": "Fever",
    "R06": "Abnormalities of breathing", "R09": "Other respiratory symptoms", "R41": "Cognitive symptoms",
    "J96": "Respiratory failure", "J12": "Viral pneumonia", "J15": "Bacterial pneumonia", "J18": "Pneumonia, organism unspecified",
    "J21": "Acute bronchiolitis", "J20": "Acute bronchitis", "J06": "Acute upper respiratory infection", "J35": "Chronic diseases of tonsils and adenoids",
    "J05": "Acute obstructive laryngitis", "J22": "Acute lower respiratory infection", "J98": "Other respiratory disorders",
    "K59": "Other functional intestinal disorders", "K02": "Dental caries", "K04": "Diseases of pulp and periapical tissues",
    "K08": "Other disorders of teeth and supporting structures", "K00": "Disorders of tooth development", "K01": "Embedded and impacted teeth",
    "K21": "Gastro-oesophageal reflux disease", "K35": "Acute appendicitis", "K40": "Inguinal hernia", "K29": "Gastritis and duodenitis",
    "K52": "Other gastroenteritis and colitis", "K56": "Paralytic ileus and intestinal obstruction", "K80": "Cholelithiasis", "K92": "Other diseases of digestive system",
    "N47": "Redundant prepuce, phimosis and paraphimosis", "N39": "Other disorders of urinary system", "N10": "Acute tubulo-interstitial nephritis",
    "N43": "Hydrocele and spermatocele", "N45": "Orchitis and epididymitis", "Q90": "Down syndrome", "Q89": "Other congenital malformations",
    "Q99": "Other chromosome abnormalities", "Q87": "Other congenital malformation syndromes", "Q38": "Congenital malformations of tongue, mouth and pharynx",
    "E10": "Type 1 diabetes mellitus", "E11": "Type 2 diabetes mellitus", "E86": "Volume depletion", "E87": "Other fluid and electrolyte disorders",
    "E44": "Moderate protein-energy malnutrition", "E46": "Unspecified protein-energy malnutrition", "E78": "Disorders of lipoprotein metabolism",
    "E03": "Other hypothyroidism", "E34": "Other endocrine disorders", "E30": "Disorders of puberty", "E22": "Hyperfunction of pituitary gland",
    "G80": "Cerebral palsy", "G93": "Other disorders of brain", "G47": "Sleep disorders", "G43": "Migraine", "G91": "Hydrocephalus",
    "G25": "Other extrapyramidal and movement disorders", "G24": "Dystonia", "G12": "Spinal muscular atrophy", "G71": "Primary disorders of muscles",
    "G96": "Other disorders of central nervous system", "H90": "Conductive and sensorineural hearing loss", "H91": "Other hearing loss",
    "H65": "Nonsuppurative otitis media", "H66": "Suppurative otitis media", "H50": "Other strabismus", "H52": "Disorders of refraction and accommodation",
    "H26": "Other cataract", "H10": "Conjunctivitis", "I10": "Essential hypertension", "I47": "Paroxysmal tachycardia", "L20": "Atopic dermatitis",
    "L02": "Cutaneous abscess, furuncle and carbuncle", "L03": "Cellulitis", "M41": "Scoliosis", "M79": "Other soft tissue disorders",
    "S06": "Intracranial injury", "S00": "Superficial injury of head", "S01": "Open wound of head", "S52": "Fracture of forearm",
    "S42": "Fracture of shoulder and upper arm", "S72": "Fracture of femur", "S82": "Fracture of lower leg and ankle", "S61": "Open wound of wrist and hand",
    "S62": "Fracture at wrist and hand level", "S32": "Fracture of lumbar spine and pelvis", "S02": "Fracture of skull and facial bones",
    "T39": "Poisoning by nonopioid analgesics", "T42": "Poisoning by antiepileptic, sedative-hypnotic drugs",
    "T43": "Poisoning by psychotropic drugs", "T50": "Poisoning by other drugs", "T36": "Poisoning by systemic antibiotics",
    "T78": "Adverse effects, not elsewhere classified", "T14": "Injury of unspecified body region", "T30": "Burn of unspecified body region",
    "T18": "Foreign body in alimentary tract", "T17": "Foreign body in respiratory tract", "X60": "Intentional self-poisoning by analgesics",
    "X61": "Intentional self-poisoning by psychotropic drugs", "X62": "Intentional self-poisoning by narcotics", "X64": "Intentional self-poisoning by other drugs",
    "X70": "Intentional self-harm by hanging", "X78": "Intentional self-harm by sharp object", "X84": "Intentional self-harm by unspecified means",
    "Y83": "Complications of surgical operation", "Y84": "Complications of other medical procedures", "Y92": "Place of occurrence",
    "W19": "Unspecified fall", "W01": "Fall on same level", "W10": "Fall on or from stairs", "W18": "Other fall on same level",
    "A09": "Diarrhoea and gastroenteritis of presumed infectious origin", "A08": "Viral intestinal infections", "B34": "Viral infection of unspecified site",
    "B97": "Viral agents as the cause of diseases", "B95": "Streptococcus and staphylococcus as the cause", "B96": "Other bacterial agents as the cause",
    "U07": "COVID-19", "D50": "Iron deficiency anaemia", "D64": "Other anaemias", "D69": "Purpura and other haemorrhagic conditions",
    "C91": "Lymphoid leukaemia", "C71": "Malignant neoplasm of brain", "D33": "Benign neoplasm of brain and CNS", "P07": "Disorders related to short gestation and low birth weight",
    "O80": "Single spontaneous delivery", "O82": "Single delivery by caesarean section", "O34": "Maternal care for abnormality of pelvic organs",
}


# Columns printed as plain integers (no thousands separator) by show_table and markdown_table.
INTEGER_COLUMNS = ["Year", "Start year", "End year", "Month", "Region code", "CUT", "Año", "Año inicial", "Año final", "Mes", "Código de región"]


def read_result(name: str, **kwargs) -> pd.DataFrame:
    path = OUTPUT / name
    if not path.is_file():
        raise FileNotFoundError(
            f"{path.name} is missing. Run the extractions described in the README before rendering."
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
        return f"{value:,.{decimals}f}"
    return str(value)


def ci(lo, hi, decimals=1):
    if pd.isna(lo) or pd.isna(hi):
        return "—"
    return f"{number(lo, decimals)} to {number(hi, decimals)}"


def pct(numerator, denominator, decimals=1):
    return number(100 * numerator / denominator, decimals) + "%" if denominator else "—"


def show_table(frame: pd.DataFrame, caption: str, decimals=None):
    """Escaped, scrollable tables; column-specific precision keeps years integral."""
    decimals = decimals or {}
    frame = frame.copy()
    frame.columns.name = None
    formatters = {c: (lambda v, d=decimals.get(c, 0): number(v, d)) for c in frame.columns}
    for column in INTEGER_COLUMNS:
        if column in frame.columns:
            formatters[column] = lambda v: "—" if pd.isna(v) else (str(int(v)) if isinstance(v, numbers.Number) else str(v))
    table = frame.to_html(index=False, escape=True, border=0, na_rep="—", formatters=formatters,
                          classes="table table-striped table-sm")
    caption_html = f"<caption>{escape(caption)}</caption>"
    table = table.replace("<thead>", caption_html + "<thead>", 1)
    display(HTML(f'<div class="analysis-table" role="region" aria-label="{escape(caption)}" tabindex="0">{table}</div>'))


def markdown_table(frame: pd.DataFrame, caption: str, label: str, decimals=None):
    """Pipe table with a Quarto caption and cross-reference label, for DOCX and PDF outputs.

    Use inside a cell with `#| output: asis`; reference it as @tbl-<label>. Numbers are
    formatted with `number()` so pandoc does not reinterpret them.
    """
    decimals = decimals or {}
    frame = frame.copy()
    frame.columns = [str(c) for c in frame.columns]
    for column in frame.columns:
        if column in INTEGER_COLUMNS:
            frame[column] = frame[column].map(lambda v: "—" if pd.isna(v) else (str(int(v)) if isinstance(v, numbers.Number) else str(v)))
        else:
            frame[column] = frame[column].map(lambda v, d=decimals.get(column, 0): number(v, d))
    print(frame.to_markdown(index=False, disable_numparse=True))
    print()
    print(f": {caption} {{#tbl-{label}}}")
    print()


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
    return "Other or invalid"


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
              missing_kwds={"color": missing_color, "edgecolor": "#999999", "linewidth": .15, "label": "No data"},
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
    handles = [Patch(facecolor=color, edgecolor="#555555", label=CLUSTER_LABELS.get(label, label)) for label, color in CLUSTER_COLORS.items()]
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.0, 1.0), fontsize=7, frameon=False)
