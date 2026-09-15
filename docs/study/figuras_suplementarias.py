"""Supplementary figures S1–S9 of the manuscript (version 10), in English and Spanish, for docs/study.

Adapted copy of `technical/sources/build_v10_supp_figures.py` of revision 10. Every plate is now drawn
here: S1 (data flow) and S6 (territorial maps), which revision 09 shipped as static artwork, are redrawn
from the tracked tables of `docs/study/data/` and `docs/study/corpus/tables/`. S6 also needs the commune
polygons of `data/comunas.shp`, which git does not track (docs/grd.qmd already depends on that file on the
same terms). The sensitivity to the count threshold (S7d) is read precomputed from
`S7d_threshold_sensitivity.csv` because the complete commune file is not published.
Usage: python3 figuras_suplementarias.py [S1 S2 S3 S4 S5 S6 S7 S8 S9]
"""
import sys
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from matplotlib.patches import Ellipse, FancyArrowPatch, FancyBboxPatch, PathPatch
from matplotlib.path import Path as MplPath   # `Path` itself is pathlib's, re-exported by figstyle
from figstyle import *
from figuras_principales import load_grd_summary, load_age_rates, rem_series, YRS_GRD, YRS_REM
CHAP_EN = {'Factores que influyen en el estado de salud': 'Health status and contact with services', 'Sistema respiratorio': 'Respiratory diseases',
           'Sistema nervioso': 'Nervous-system diseases', 'Trastornos mentales y del comportamiento': 'Mental and behavioural, excluding F84',
           'Sistema digestivo': 'Digestive diseases', 'Endocrinas, nutricionales y metabólicas': 'Endocrine, nutritional and metabolic',
           'Síntomas y signos no clasificados': 'Symptoms and signs, unclassified', 'Malformaciones congénitas': 'Congenital malformations',
           'Traumatismos y envenenamientos': 'Injury and poisoning', 'Causas externas': 'External causes', 'Infecciosas y parasitarias': 'Infectious and parasitic',
           'Sistema genitourinario': 'Genitourinary diseases', 'Sangre e inmunidad': 'Blood and immune disorders', 'Sistema circulatorio': 'Circulatory diseases',
           'Piel y tejido subcutáneo': 'Skin and subcutaneous tissue', 'Sistema osteomuscular': 'Musculoskeletal', 'Ojo y anexos': 'Eye and adnexa', 'Oído': 'Ear',
           'Neoplasias': 'Neoplasms', 'Embarazo, parto y puerperio': 'Pregnancy and childbirth', 'Perinatales': 'Perinatal conditions'}

def age_sex_panel(ax, source, y0, y1, lang, ymin):
    for y, filled in ((y0, False), (y1, True)):
        for sex, col, mk in (('hombre', BLUE, 'o'), ('mujer', ORANGE, 's')):
            z = pd.read_csv(DATA/f'{source}_age_{sex}_{y}.csv')
            lab = f"{text('Males', 'Hombres', lang) if sex == 'hombre' else text('Females', 'Mujeres', lang)} {y}"
            ax.errorbar(range(len(z)), z.rate, yerr=[z.rate - z.lo, z.hi - z.rate], fmt=mk + ('-' if filled else '--'), color=col, ms=3, lw=1.0 if filled else 0.9,
                        mfc=col if filled else 'white', capsize=1.2, elinewidth=0.6, label=lab)
        groups = [s.replace('-', '–') for s in z.age_group]
    ax.set_xticks(range(len(groups))); ax.set_xticklabels(groups, rotation=45, ha='right', fontsize=6.6)
    log_axis(ax, 'y', lang); ax.set_ylim(ymin, 1000)
    ax.set_xlabel(text('Age group (years)', 'Grupo de edad (años)', lang)); ax.set_ylabel(text('Records per 100 000 residents\n(log scale)', 'Registros por 100 000 residentes\n(escala log)', lang))
    ax.legend(loc='upper right', fontsize=6.2, ncol=2, handlelength=1.4, columnspacing=0.8, borderaxespad=0.2)

# ------------------------------------------------------------------ S1 data-flow schematic
# Palette of the inherited revision-09 plate, sampled from docs/study/figures/*/Figure_S1.png.
# These are NOT the Okabe-Ito constants of figstyle; they are declared here so the redrawn plate
# stays visually identical to the one already printed in the manuscript.
S1_COLOURS = {'grd': ('#0B5FA5', '#E9F1FA'), 'a05': ('#0E7C7B', '#E5F4F3'),
              'p2': ('#177535', '#E9F4ED'), 'b': ('#6C4E94', '#EFEAF7')}
S1_RED, S1_GREY = '#B12D1D', '#474747'
S1_W, S1_H = 2067, 2245          # canvas of the inherited plate: 175.0 x 190.1 mm at 300 dpi
CORPUS = BASE/'corpus'/'tables'  # presentation tables of the version-02 corpus; figstyle exposes only DATA/TIDY


def _s1_in(x, y):
    """A pixel of the inherited 2067x2245 canvas -> inches, for fig.dpi_scale_trans.

    Everything in S1 is drawn in inches rather than in axes fractions so that the rounded corners
    and the cylinder lids stay circular whatever the aspect ratio of the anchor axes."""
    return x/300.0, (S1_H - y)/300.0


def _s1_box(fig, ax, x0, y0, x1, y1, ec, fc='white', lw=1.2, r=0.035):
    """Rounded box in plate pixels. FancyBboxPatch is neither a Rectangle nor a Polygon, so
    overlap_qa._marks() ignores it; set_gid('bg') repeats the exemption explicitly."""
    ix0, iy0 = _s1_in(x0, y1); ix1, iy1 = _s1_in(x1, y0)
    p = FancyBboxPatch((ix0, iy0), ix1 - ix0, iy1 - iy0, boxstyle=f'round,pad=0,rounding_size={r}',
                       transform=fig.dpi_scale_trans, fc=fc, ec=ec, lw=lw, zorder=2, mutation_aspect=1)
    p.set_gid('bg'); ax.add_patch(p); return p


def _s1_cyl(fig, ax, x0, y0, x1, y1, ec, fc='white', lw=1.2, ry=15):
    """Database cylinder in plate pixels; returns the vertical centre of its body (label anchor)."""
    cx, rx = (x0 + x1)/2, (x1 - x0)/2; yt, yb = y0 + ry, y1 - ry
    t = np.linspace(0, np.pi, 60)
    top = np.column_stack([cx + rx*np.cos(t), yt - ry*np.sin(t)])   # right -> left over the lid
    bot = np.column_stack([cx - rx*np.cos(t), yb + ry*np.sin(t)])   # left -> right under the base
    pts = np.vstack([top, [[x0, yb]], bot, [[x1, yt]]])
    verts = [_s1_in(px, py) for px, py in pts]
    body = PathPatch(MplPath(verts, [MplPath.MOVETO] + [MplPath.LINETO]*(len(verts) - 1)),
                     transform=fig.dpi_scale_trans, fc=fc, ec=ec, lw=lw, zorder=2)
    body.set_gid('bg'); ax.add_patch(body)
    lid = Ellipse(_s1_in(cx, yt), (x1 - x0)/300.0, 2*ry/300.0, transform=fig.dpi_scale_trans,
                  fc=fc, ec=ec, lw=lw, zorder=3)
    lid.set_gid('bg'); ax.add_patch(lid)
    return (yt + y1)/2


def _s1_arrow(fig, ax, x0, y0, x1, y1, ec, lw=1.3, ms=12):
    a = FancyArrowPatch(_s1_in(x0, y0), _s1_in(x1, y1), transform=fig.dpi_scale_trans, arrowstyle='-|>',
                        mutation_scale=ms, color=ec, lw=lw, shrinkA=0, shrinkB=0, zorder=4)
    a.set_gid('bg'); ax.add_patch(a)


def _s1_lines(fig, ax, x, y, lines, size=6.8, color=BLACK, weight='normal'):
    """One Text artist per box: the QA overlap check then only has to see that boxes do not collide."""
    ix, iy = _s1_in(x, y)
    return ax.text(ix, iy, '\n'.join(lines), transform=fig.dpi_scale_trans, ha='center', va='center',
                   fontsize=size, color=color, fontweight=weight, linespacing=1.235, zorder=5)


def figS1(lang):
    style(); fig = plt.figure(figsize=(S1_W/300, S1_H/300))
    axa = fig.add_axes([0.018, 0.417, 0.964, 0.530]); axb = fig.add_axes([0.018, 0.054, 0.964, 0.277])
    for ax in (axa, axb): ax.set_axis_off(); ax.grid(False); ax.set_xlim(0, 1); ax.set_ylim(0, 1)

    # ---- every number of the schematic, recomputed from the tracked tables -------------------
    g = pd.read_csv(TIDY/'grd_year_summary.csv').query("panel=='observed' and activity=='all'")
    gany = g.query("variant=='sin_rett' and position=='any'")
    tot = int(gany.n_episodes_total_same_panel_activity.sum())
    anys = int(gany.n_episodes_f84.sum())
    rett_only = int(g.query("variant=='con_rett' and position=='any'").n_episodes_f84.sum()) - anys
    prin = int(g.query("variant=='sin_rett' and position=='principal'").n_episodes_f84.sum())
    sec = int(g.query("variant=='sin_rett' and position=='secondary_only'").n_episodes_f84.sum())
    st = pd.read_csv(CORPUS/'ST10_grd_f84_subcodes.csv')
    yr0, yr1 = int(gany.year.min()), int(gany.year.max())
    rett_any = int(st[st['ICD-10 subcode'].str.startswith('F84.2') & (st['F84 code position'] == 'Any position')]
                   [[str(y) for y in range(yr0, yr1 + 1)]].iloc[0].astype(str).str.replace(',', '').astype(int).sum())
    rett_kept = rett_any - rett_only
    hosp = gany.set_index('year').hospitals_n
    fixed = int(pd.read_csv(TIDY/'grd_year_summary.csv')
                .query("panel=='fixed65' and activity=='all' and position=='any' and variant=='sin_rett'").hospitals_n.max())

    rp = pd.read_csv(TIDY/'rem_pathway_annual.csv', low_memory=False); rp['code'] = rp.code.astype(str)
    a05 = rp.query("module=='A05' and code=='05990022' and variant=='single_code'").set_index('year').sort_index()
    p2 = rp.query("module=='P2' and code=='P2500500' and measure=='december_stock'").set_index('year').sort_index()
    a_y0, a_y1 = int(a05.era_start.iloc[0]), int(a05.era_end.iloc[0])
    p_y0, p_y1 = int(p2.era_start.iloc[0]), int(p2.era_end.iloc[0])
    a_stable = int(a05.n_stable_panel_establishments.max()); p_stable = int(p2.n_stable_panel_establishments.max())
    a_rep0, a_rep1 = int(a05.n_reporting_establishments.iloc[0]), int(a05.n_reporting_establishments.iloc[-1])
    a_t0, a_t1 = int(a05.total.iloc[0]), int(a05.total.iloc[-1])
    # The plate quotes the P2 stock from the 2021 age-definition break, not from era_start (2019).
    # Like the age lines of box 2, that break year lives only in contenido_v10.json, not in a tracked CSV.
    p_yA = 2021
    p_tA, p_t1 = int(p2.total.loc[p_yA]), int(p2.total.iloc[-1])

    ed = pd.read_csv(TIDY/'education_summary_year.csv').set_index('year')
    pie = ed[ed.pie_harmonised_n.notna()]
    e_y0, e_y1 = int(pie.index.min()), int(pie.index.max())
    split = ed[ed.pie_tea_strict_n.notna() & ed.pie_tea_asperger_n.notna()].index
    s_y0, s_y1 = int(split.min()), int(split.max())
    sinaces = int(ed.index[ed.pie_harmonised_source.fillna('').str.contains('SINACES')].min())
    e_n0, e_n1 = int(pie.pie_harmonised_n.iloc[0]), int(pie.pie_harmonised_n.iloc[-1])

    sv = pd.read_csv(TIDY/'survey_estimates.csv'); tot_rows = sv[sv.subgroup_type == 'total']
    endide = tot_rows[tot_rows.survey.str.startswith('ENDIDE')]
    n_ad = int(endide[(endide.module == 'Adultos (18+)') & (endide.estimate_type == 'primary')].n.iloc[0])
    n_nna = int(endide[endide.module.str.startswith('NNA (2-17)') &
                       (endide.domain == 'ENDIDE NNA 2-17: autismo reportado')].n.iloc[0])
    encavi = tot_rows[tot_rows.survey.str.startswith('ENCAVI')]
    n_val = int(encavi[encavi.estimate_type == 'primary'].n.iloc[0])
    n_base = int(encavi[encavi.estimate_type == 'sensitivity'].n.iloc[0])
    n_exc = n_base - n_val
    endide_lbl = endide.survey.iloc[0].replace('-', '–'); encavi_lbl = encavi.survey.iloc[0].replace('-', '–')

    # ---- panel (a): the three administrative sources, processed in parallel -------------------
    bands = [('grd', 38, 670), ('a05', 716, 1350), ('p2', 1396, 2030)]
    heads = [text('GRD · hospital activity', 'GRD · actividad hospitalaria', lang),
             text('A05 · annual entries', 'A05 · ingresos anuales', lang),
             text('P2 · December follow-up', 'P2 · seguimiento en diciembre', lang)]
    cyls = [[f'{yr0}–{yr1}', f"{num(tot, lang)} {text('episodes', 'episodios', lang)}"],
            [f"{a_y0}–{a_y1} · {text('code', 'código', lang)} 05990022",
             text('Establishment-month records', 'Registros establecimiento-mes', lang)],
            [f"{p_y0}–{p_y1} · {text('code', 'código', lang)} P2500500",
             text('Autism among NANEAS', 'Autismo en NANEAS', lang)]]
    box2 = [[text('Eligible F84 codes¹', 'Códigos F84 elegibles¹', lang),
             f"{num(anys, lang)} {text('episodes retained', 'episodios incluidos', lang)}",
             f"{num(rett_only, lang)} {text('with Rett and no eligible code', 'con Rett sin código elegible', lang)}",
             text(f'excluded; {num(rett_kept, lang)} with Rett and another',
                  f'excluidos; {num(rett_kept, lang)} con Rett y otro', lang),
             text('eligible code retained', 'código elegible incluidos', lang)],
            [text('Strict autism', 'Autismo estricto', lang),
             text('Sum known monthly totals', 'Sumar totales mensuales conocidos', lang),
             f"{num(a_t0, lang)} ({a_y0}) {text('to', 'a', lang)} {num(a_t1, lang)} ({a_y1})",
             text('Missing cells remain missing', 'Celdas vacías siguen faltantes', lang)],
            # The P2 age universe is stored only as text (contenido_v10.json, manuscript Table 2 and
            # supplement Table S1); no tracked CSV carries it as a value, so it is written out here.
            [text('Select December cut', 'Seleccionar corte de diciembre', lang),
             text('2019–2020: ages 0–9 years', '2019–2020: 0–9 años', lang),
             text('2021–2025: ages 0–19 years', '2021–2025: 0–19 años', lang),
             text('Age-definition break in 2021', 'Quiebre de edad en 2021', lang)]]
    box3 = [[f"Principal: {num(prin, lang)}",
             f"{text('Exclusively secondary', 'Solo secundario', lang)}: {num(sec, lang)}",
             text('Mutually exclusive categories', 'Categorías excluyentes', lang)],
            [f"{num(a_stable, lang)} {text('stable establishments', 'establecimientos estables', lang)}",
             text('≥1 code row each year', '≥1 fila del código cada año', lang),
             f"{num(a_rep0, lang)} → {num(a_rep1, lang)} {text('annual reporters', 'reportantes anuales', lang)}"],
            [f"{num(p_stable, lang)} {text('stable establishments', 'establecimientos estables', lang)}",
             text('December code row every year', 'Fila del código cada diciembre', lang),
             text(f'{p_y0}–{p_y1} membership', f'Pertenencia durante {p_y0}–{p_y1}', lang)]]
    box4 = [[text(f'{num(fixed, lang)} fixed / {num(hosp.min(), lang)}–{num(hosp.max(), lang)} observed hospitals',
                  f'{num(fixed, lang)} hospitales fijos / {num(hosp.min(), lang)}–{num(hosp.max(), lang)} observados', lang),
             text('Coding-depth strata', 'Estratos de profundidad de códigos', lang),
             text('Inpatient / day-case surgery', 'Hospitalización / cirugía ambulatoria', lang),
             text('Matching activity denominator', 'Denominador de actividad propio', lang)],
            [text('Annual flow', 'Flujo anual', lang),
             text('Observed and stable panels', 'Paneles observado y estable', lang),
             text('Age and sex summaries', 'Resúmenes por edad y sexo', lang),
             text('Annual row ≠ full monthly reporting', 'Fila anual ≠ reporte mensual completo', lang)],
            [text('December stock, not a flow', 'Stock de diciembre, no flujo', lang),
             f"{num(p_tA, lang)} ({p_yA}) {text('to', 'a', lang)} {num(p_t1, lang)} ({p_y1})",
             text('Observed / stable / under-10', 'Observado / estable / menores de 10', lang),
             text('June and December never summed', 'Junio y diciembre no se suman', lang)]]
    rows = [(197, 396), (435, 721), (766, 1005), (1032, 1283)]
    for i, (key, bx0, bx1) in enumerate(bands):
        ec, fcb = S1_COLOURS[key]; cx = (bx0 + bx1)/2
        _s1_box(fig, axa, bx0, 118, bx1, 1311, 'none', fc=fcb, lw=0, r=0.05)
        _s1_lines(fig, axa, cx, 153, [heads[i]], size=7.8, color=ec, weight='bold')
        yc = _s1_cyl(fig, axa, bx0 + 26, rows[0][0], bx1 - 26, rows[0][1], ec)
        _s1_lines(fig, axa, cx, yc, cyls[i])
        for (y0, y1), lines in zip(rows[1:], (box2[i], box3[i], box4[i])):
            _s1_box(fig, axa, bx0 + 26, y0, bx1 - 26, y1, ec)
            _s1_lines(fig, axa, cx, (y0 + y1)/2, lines)
        for (ya, yb) in ((rows[0][1] + 2, rows[1][0] - 2), (rows[1][1] + 2, rows[2][0] - 2), (rows[2][1] + 2, rows[3][0] - 2)):
            _s1_arrow(fig, axa, cx, ya, cx, yb, ec)
    _s1_lines(fig, axa, S1_W/2, 1362,
              [text('Parallel processing; no person-level linkage or observed care cascade',
                    'Procesamiento paralelo; sin enlace individual ni cascada asistencial observada', lang)],
              size=7.4, color=S1_RED, weight='bold')

    # ---- panel (b): education records and the two household surveys --------------------------
    ec, fcb = S1_COLOURS['b']
    _s1_box(fig, axb, 38, 1500, 2030, 2126, 'none', fc=fcb, lw=0, r=0.05)
    yc = _s1_cyl(fig, axb, 64, 1528, 478, 1732, ec, ry=14.5)
    _s1_lines(fig, axb, 271, yc, ['PIE', f'{e_y0}–{e_y1}'])
    _s1_box(fig, axb, 565, 1528, 1348, 1732, ec)
    _s1_lines(fig, axb, 956, 1630, [text('Historical ASD + ASD–Asperger', 'TEA + TEA–Asperger históricos', lang),
                                    text(f'{s_y0}–{s_y1} categories combined', f'Categorías {s_y0}–{s_y1} combinadas', lang),
                                    text(f'SINACES source from {sinaces}', f'Fuente SINACES desde {sinaces}', lang)])
    _s1_box(fig, axb, 1475, 1528, 1997, 1732, ec)
    _s1_lines(fig, axb, 1736, 1630, [text('Students by year', 'Estudiantes por año', lang),
                                     f'{num(e_n0, lang)} → {num(e_n1, lang)}'])
    yc = _s1_cyl(fig, axb, 64, 1782, 980, 2092, ec, ry=14.5)
    _s1_lines(fig, axb, 522, yc, [endide_lbl,
                                  f"≥18 {text('years', 'años', lang)}: {num(n_ad, lang)} · 2–17 {text('years', 'años', lang)}: {num(n_nna, lang)}",
                                  encavi_lbl,
                                  f"≥15 {text('years', 'años', lang)}: {num(n_base, lang)} {text('respondents', 'participantes', lang)}"])
    _s1_box(fig, axb, 1096, 1782, 1997, 2092, ec)
    _s1_lines(fig, axb, 1546, 1937,
              [text('ENDIDE: complete autism item in both domains', 'ENDIDE: ítem completo en ambos dominios', lang),
               text(f'ENCAVI: {num(n_val, lang)} valid; {num(n_exc, lang)} excluded²',
                    f'ENCAVI: {num(n_val, lang)} válidas; {num(n_exc, lang)} excluidas²', lang),
               text('Domain analysis: weights, strata and clusters', 'Ponderadores, estratos y conglomerados', lang),
               text('Weighted proportions and design-based 95% CIs', 'Proporciones e IC del 95% según diseño', lang)])
    for x0, x1, y in ((480, 563, 1630), (1350, 1473, 1630), (982, 1094, 1937)):
        _s1_arrow(fig, axb, x0, y, x1, y, ec)
    _s1_lines(fig, axb, S1_W/2, 2186,
              [text('Arrows indicate data transformations within each source, not movement of people.',
                    'Las flechas indican transformaciones dentro de cada fuente, no desplazamientos de personas.', lang)],
              size=7.0, color=S1_GREY)
    letter(fig, axa, 'a', dx=-0.006, dy=0.033); letter(fig, axb, 'b', dx=-0.006, dy=0.020)
    save(fig, 'Figure_S1', lang)

# ------------------------------------------------------------------ S2 hospital robustness
def figS2(lang):
    style(); fig = plt.figure(figsize=(175/25.4, 172/25.4))
    gs = fig.add_gridspec(2, 2, left=0.10, right=0.975, top=0.965, bottom=0.08, hspace=0.50, wspace=0.42)
    g = load_grd_summary(); obs = g.query("panel=='observed' and position=='any'").set_index('year').reindex(YRS_GRD)
    # (a) coding-depth strata
    a = fig.add_subplot(gs[0, 0]); clean(a)
    cd = pd.read_csv(DATA/'grd_coding_depth_year.csv'); cd['depth_bin'] = cd.depth_bin.astype(str)
    cd = cd.query("variant=='sin_rett' and panel=='observed' and activity=='all' and depth_bin!='0'")
    bins = [b for b in ['1', '2', '3', '4', '5', '6-7', '8-10', '11+'] if b in set(cd.depth_bin)]
    x = np.arange(len(bins))
    for y, off, col, hatch in ((2019, -0.2, SKY, '//'), (2024, 0.2, BLUE, None)):
        z = cd[cd.year == y].set_index('depth_bin').reindex(bins)
        a.bar(x + off, z.rate_per_100k_episodes, width=0.38, color=col, hatch=hatch, edgecolor='white' if hatch is None else BLUE, lw=0.4, label=str(y), zorder=2)
        a.errorbar(x + off, z.rate_per_100k_episodes, yerr=[z.rate_per_100k_episodes - z.rate_lo, z.rate_hi - z.rate_per_100k_episodes], fmt='none', ecolor='#333333', elinewidth=0.6, capsize=1.2, zorder=3)
    a.set_xticks(x); a.set_xticklabels([b.replace('-', '–') for b in bins]); a.set_xlabel(text('Coded diagnoses per episode', 'Diagnósticos codificados por episodio', lang))
    a.set_ylabel(text('Eligible episodes per 100 000\nepisodes within stratum', 'Episodios elegibles por 100 000\nepisodios del estrato', lang)); a.yaxis.set_major_formatter(thousands(lang))
    a.legend(loc='upper left', fontsize=6.6, handlelength=1.2); a.set_ylim(0, 2300)
    ins = a.inset_axes([0.47, 0.62, 0.51, 0.36]); ins.grid(False); shade_pandemic(ins)
    ins.plot(obs.index, obs.coding_depth_mean_all, color=GREY, marker='o', ms=2.6, lw=1, label=text('All', 'Todos', lang))
    ins.plot(obs.index, obs.coding_depth_mean_f84, color=ORANGE, marker='s', ms=2.6, lw=1, label=text('Eligible', 'Elegibles', lang))
    ins.set_ylim(3.5, 7); ins.set_xticks([2019, 2021, 2024]); ins.tick_params(labelsize=6); ins.set_ylabel(text('Mean diagnoses', 'Diagnósticos medios', lang), fontsize=6, labelpad=1)
    ins.legend(fontsize=5.8, loc='lower right', handlelength=1, borderpad=0.2); [ins.spines[s_].set_visible(False) for s_ in ('top', 'right')]
    # (b) activity modality
    b = fig.add_subplot(gs[0, 1]); clean(b); shade_pandemic(b)
    ga = pd.read_csv(TIDY/'grd_year_summary.csv').query("variant=='sin_rett' and panel=='observed' and position=='any'")
    for act, col, mk, en, es in (('hospitalisation', GREEN, 's', 'Strict hospitalisation', 'Hospitalización estricta'), ('cma', PINK, '^', 'Major ambulatory surgery', 'Cirugía mayor ambulatoria')):
        z = ga[ga.activity == act].set_index('year').reindex(YRS_GRD)
        b.fill_between(z.index, z.rate_lo, z.rate_hi, color=col, alpha=0.15, lw=0); b.plot(z.index, z.rate_per_100k_episodes, color=col, marker=mk, label=text(en, es, lang))
        end_label(b, 2024, z.rate_per_100k_episodes[2024], num(z.rate_per_100k_episodes[2024], lang, 1), col, dy=6 if act == 'hospitalisation' else -6)
    b.set_ylim(0, 1100); b.yaxis.set_major_formatter(thousands(lang)); year_ticks(b, YRS_GRD, short=True); b.set_xlim(2018.6, 2024.9)
    b.set_ylabel(text('Eligible episodes per 100 000\nepisodes of each modality', 'Episodios elegibles por 100 000\nepisodios de cada modalidad', lang)); b.legend(loc='upper left', fontsize=6.6, handlelength=1.4)
    # (c) hospital distribution 2024
    c = fig.add_subplot(gs[1, 0]); clean(c)
    h = pd.read_csv(DATA/'Figure5_hospital_2024.csv'); hv = h[~h.display_suppressed].sort_values('display_rank')
    q = pd.read_csv(DATA/'expanded_hospital_quantiles.csv').set_index('quantile').rate_per_100k
    c.axhspan(q[0.25], q[0.75], color='#d9d9d9', alpha=0.45, zorder=0).set_gid('shade'); c.axhline(obs.rate_per_100k_episodes[2024], color='#333333', lw=0.85, ls='--', zorder=1)
    hv = hv.assign(in_fixed_panel=hv.in_fixed_panel.astype(str).str.lower().eq('true')); nfix = int(hv.in_fixed_panel.sum()); nadd = int((~hv.in_fixed_panel).sum())
    for fixed, col, mk, lab in ((True, BLUE, 'o', text(f'Stable hospitals ({nfix})', f'Hospitales estables ({nfix})', lang)), (False, ORANGE, 's', text(f'Added hospitals shown ({nadd})', f'Hospitales incorporados visibles ({nadd})', lang))):
        z = hv[hv.in_fixed_panel == fixed]
        c.errorbar(z.display_rank, z.rate, yerr=[z.rate - z.lo, z.hi - z.rate], fmt='none', ecolor='#999999', elinewidth=0.5, capsize=0, zorder=2)
        c.scatter(z.display_rank, z.rate, color=col, marker=mk, s=11, zorder=3, linewidth=0.25, edgecolor='white', label=lab)
    log_axis(c, 'y', lang); c.set_ylim(40, 8000); c.set_xlabel(text('Hospitals ranked by 2024 indicator (71 of 72 shown)', 'Hospitales ordenados por el indicador 2024 (71 de 72 visibles)', lang), fontsize=7.4)
    c.set_ylabel(text('Eligible episodes per 100 000\nepisodes of the hospital, 2024', 'Episodios elegibles por 100 000\nepisodios del hospital, 2024', lang))
    c.legend(loc='upper left', fontsize=6.4, handlelength=1.2); c.set_xticks([1, 20, 40, 60, 71])
    c.text(0.98, 0.04, text(f'Dashed: national {num(obs.rate_per_100k_episodes[2024], lang, 1)}; band: hospital IQR', f'Discontinua: nacional {num(obs.rate_per_100k_episodes[2024], lang, 1)}; banda: RIC hospitalario', lang), transform=c.transAxes, ha='right', fontsize=6.2, color='#444444')
    # (d) DEIS discharges versus GRD, principal diagnosis
    d = fig.add_subplot(gs[1, 1]); clean(d); shade_pandemic(d)
    dv = pd.read_csv(DATA/'expanded_deis_principal_comparison.csv').set_index('year').reindex(YRS_GRD)
    snss = dv.deis_f84_principal_snss / dv.deis_discharges_snss * 1e5
    d.fill_between(dv.index, dv.deis_rate_lo95, dv.deis_rate_hi95, color=GREY, alpha=0.15, lw=0)
    d.plot(dv.index, dv.deis_rate_f84_principal_per_100k_discharges, color=GREY, marker='D', label=text('DEIS, all establishments', 'DEIS, todos los establecimientos', lang))
    d.plot(dv.index, snss, color=GOLD, marker='v', ls='--', label=text('DEIS, public-hospital subset', 'DEIS, subconjunto hospitales públicos', lang))
    d.plot(dv.index, dv.grd_rate_f84_principal_per_100k_episodes, color=ORANGE, marker='o', label=text('GRD, all activity', 'GRD, toda actividad', lang))
    d.plot(dv.index, dv.grd_rate_f84_principal_hospitalisation_per_100k_episodes, color=BLUE, marker='s', ls='--', label=text('GRD, strict hospitalisation', 'GRD, hospitalización estricta', lang))
    d.set_ylim(0, 80); year_ticks(d, YRS_GRD, short=True); d.set_xlim(2018.6, 2024.6)
    d.set_ylabel(text('Principal-diagnosis F84 per 100 000\ndischarges or episodes', 'F84 principal por 100 000\negresos o episodios', lang)); d.legend(loc='upper left', fontsize=6.4, handlelength=1.4)
    for ax, ch in zip([a, b, c, d], 'abcd'): letter(fig, ax, ch, dx=-0.085)
    save(fig, 'Figure_S2', lang)

# ------------------------------------------------------------------ S3 age and sex detail
def figS3(lang):
    style(); fig = plt.figure(figsize=(175/25.4, 165/25.4))
    gs = fig.add_gridspec(2, 2, left=0.10, right=0.975, top=0.965, bottom=0.10, hspace=0.62, wspace=0.42)
    a = fig.add_subplot(gs[0, 0]); clean(a); age_sex_panel(a, 'grd', 2019, 2024, lang, 0.1)
    b = fig.add_subplot(gs[0, 1]); clean(b); age_sex_panel(b, 'a05', 2021, 2025, lang, 0.1)
    c = fig.add_subplot(gs[1, 0]); clean(c); shade_pandemic(c)
    pr = pd.read_csv(TIDY/'models_population_rates.csv').query("variant=='sin_rett' and position=='any'")
    for sex, col, mk, en, es in (('HOMBRE', BLUE, 'o', 'Males', 'Hombres'), ('MUJER', ORANGE, 's', 'Females', 'Mujeres')):
        z = pr[pr.sex == sex].set_index('year').reindex(YRS_GRD); c.fill_between(z.index, z.asr_lo, z.asr_hi, color=col, alpha=0.15, lw=0); c.plot(z.index, z.asr, color=col, marker=mk, label=text(en, es, lang))
        end_label(c, 2024, z.asr[2024], num(z.asr[2024], lang, 1), col, dy=6 if sex == 'HOMBRE' else -6)
    c.set_ylim(0, 100); year_ticks(c, YRS_GRD, short=True); c.set_xlim(2018.6, 2024.9); c.set_ylabel(text('GRD eligible episodes per 100 000\nresidents, WHO age-standardised', 'Episodios GRD elegibles por 100 000\nresidentes, estandarizados (OMS)', lang)); c.legend(loc='upper left', fontsize=6.6)
    d = fig.add_subplot(gs[1, 1]); clean(d)
    a5 = pd.read_csv(DATA/'models_a05_standardised_rates.csv').query("variant=='strict_autism'")
    for sex, col, mk, en, es in (('HOMBRE', BLUE, 'o', 'Males', 'Hombres'), ('MUJER', ORANGE, 's', 'Females', 'Mujeres')):
        z = a5[a5.sex == sex].set_index('year').reindex(YRS_REM); d.fill_between(z.index, z.asr_lo, z.asr_hi, color=col, alpha=0.15, lw=0); d.plot(z.index, z.asr, color=col, marker=mk, label=text(en, es, lang))
        end_label(d, 2025, z.asr[2025], num(z.asr[2025], lang, 1), col, dy=6 if sex == 'HOMBRE' else -6)
    law_line(d, lang, y=0.25); d.set_ylim(0, 160); year_ticks(d, YRS_REM, short=True); d.set_xlim(2020.6, 2025.9)
    d.set_ylabel(text('A05 strict-autism entries per 100 000\nresidents, WHO age-standardised', 'Ingresos A05 por 100 000\nresidentes, estandarizados (OMS)', lang)); d.legend(loc='upper left', fontsize=6.6)
    for ax, ch in zip([a, b, c, d], 'abcd'): letter(fig, ax, ch, dx=-0.085)
    save(fig, 'Figure_S3', lang)

# ------------------------------------------------------------------ S4 REM detail
A03_2024 = [('03700104', 'Evaluated at integral control', 'Evaluados en control integral'), ('03700105', 'Suspected elsewhere', 'Sospecha en otro lugar'),
            ('03700106', 'Alert signs: yes', 'Señales de alerta: sí'), ('03700107', 'Alert signs: no', 'Señales de alerta: no'), ('03700108', 'Referral: yes', 'Derivación: sí'), ('03700109', 'Referral: no', 'Derivación: no')]
A03_2025 = [('03710013', 'Motive: altered EEDP', 'Motivo: EEDP alterado'), ('03710014', 'Motive: risk or alert sign', 'Motivo: riesgo o señal de alerta'), ('03710015', 'Motive: both', 'Motivo: ambos'),
            ('03710016', 'M-CHAT-R/F low risk', 'M-CHAT-R/F riesgo bajo'), ('03710017', 'Medium risk, no referral', 'Riesgo medio, sin derivación'), ('03710018', 'Medium risk, referral', 'Riesgo medio, con derivación'),
            ('03710019', 'High risk, referral', 'Riesgo alto, con derivación'), ('03710020', '30–59 months, no referral', '30–59 meses, sin derivación'), ('03710021', '30–59 months, referral', '30–59 meses, con derivación')]

def figS4(lang):
    style(); fig = plt.figure(figsize=(175/25.4, 178/25.4))
    gs = fig.add_gridspec(2, 2, left=0.10, right=0.975, top=0.965, bottom=0.075, hspace=0.50, wspace=0.50)
    # (a) A05 entries: observed network vs stable panel, with establishments
    a = fig.add_subplot(gs[0, 0]); clean(a)
    ent = rem_series('05990022'); a2 = a.twinx(); a2.grid(False); a2.spines['top'].set_visible(False)
    [p_.set_gid('bg') for p_ in a2.bar(ent.index, ent.n_reporting_establishments, color='#dddddd', width=0.6, zorder=0)]; a2.set_ylim(0, 3000); a2.set_ylabel(text('Reporting establishments (bars)', 'Establecimientos informantes (barras)', lang), fontsize=7, color='#555555'); a2.tick_params(axis='y', colors='#555555')
    a.set_zorder(a2.get_zorder() + 1); a.patch.set_visible(False)
    a.plot(ent.index, ent.total, color=GREEN, marker='^', label=text('All reporting establishments', 'Todos los establecimientos informantes', lang))
    a.plot(ent.index, ent.stable_panel_total, color=BLACK, marker='s', mfc='white', ls='--', label=text('Stable panel (258)', 'Panel estable (258)', lang))
    for s_, col in ((ent.total, GREEN), (ent.stable_panel_total, BLACK)):
        end_label(a, 2025, s_[2025], num(s_[2025], lang), col, dx=-2, dy=7, ha='right')
    law_line(a, lang, y=0.30); a.set_ylim(0, 16000); a.yaxis.set_major_formatter(thousands(lang)); year_ticks(a, YRS_REM); a.set_xlim(2020.5, 2025.5)
    a.set_ylabel(text('A05 strict-autism entries (n)', 'Ingresos A05 autismo estricto (n)', lang)); a.legend(loc='upper left', fontsize=6.4, handlelength=1.4)
    # (b) P2 December and June stocks, observed vs stable panel
    b = fig.add_subplot(gs[0, 1]); clean(b)
    pd_ = rem_series('P2500500', measure='december_stock'); pj = rem_series('P2500500', measure='june_stock')
    b.plot(pd_.index, pd_.total, color=PINK, marker='o', label=text('Dec. stock, all', 'Stock dic., todos', lang))
    b.plot(pd_.index, pd_.stable_panel_total, color=PINK, marker='s', mfc='white', ls='--', label=text('Dec. stock, stable panel (193)', 'Stock dic., panel estable (193)', lang))
    b.plot(pj.index, pj.total, color=GREY, marker='o', mfc='white', ls=':', label=text('June stock, all (sensitivity)', 'Stock junio, todos (sensibilidad)', lang))
    b.axvline(2020.5, color='#444444', ls=':', lw=0.8); b.text(2020.55, 0.50, text('<10 y | <20 y', '<10 a | <20 a', lang), transform=b.get_xaxis_transform(), fontsize=6.2, va='bottom', color='#444444')
    end_label(b, 2025, pd_.total[2025], num(pd_.total[2025], lang), PINK, dx=-2, dy=7, ha='right')
    law_line(b, lang, y=0.40, label=False); b.set_ylim(0, 35000); b.yaxis.set_major_formatter(thousands(lang)); year_ticks(b, range(2019, 2026), short=True); b.set_xlim(2018.6, 2025.5)
    b.set_ylabel(text('P2 autism under follow-up (people)', 'P2 autismo en seguimiento (personas)', lang)); b.legend(loc='upper left', fontsize=6.2, handlelength=1.4)
    # (c) A03 2024 additional items and the 2025 redesign
    c = fig.add_subplot(gs[1, 0]); clean(c, grid='x'); pos = c.get_position(); c.set_position([pos.x0 + 0.17, pos.y0, pos.width - 0.07, pos.height])
    r = pd.read_csv(TIDY/'rem_pathway_annual.csv', low_memory=False); r['code'] = r.code.astype(str)
    rows = [(cd, en, es, 2024, BLUE) for cd, en, es in A03_2024] + [(cd, en, es, 2025, ORANGE) for cd, en, es in A03_2025]
    y = 0; ticks = []; labels = []; heads = []
    for i, (cd, en, es, yr, col) in enumerate(rows):
        if i == 0 or i == len(A03_2024):
            if i: y += 0.4
            ticks.append(y); labels.append(text('2024 items, 31–59 months', 'Ítems 2024, 31–59 meses', lang) if i == 0 else text('2025 redesign', 'Rediseño 2025', lang)); heads.append((len(ticks) - 1, col)); y += 1
        z = r[(r.code == cd) & (r.variant == 'single_code') & (r.year == yr)]; v = float(z.total.iloc[0]); n = int(z.n_reporting_establishments.iloc[0])
        c.barh(y, v, color=col, height=0.7); c.text(v * 1.08, y, f'{num(v, lang)} ({n})', va='center', fontsize=6.0); ticks.append(y); labels.append(text(en, es, lang)); y += 1
    c.set_yticks(ticks); c.set_yticklabels(labels, fontsize=6.2); c.invert_yaxis(); log_axis(c, 'x', lang); c.set_xlim(300, 400000); c.set_xticks([1000, 10000, 100000]); c.xaxis.set_major_formatter(thousands(lang))
    for idx, col in heads:
        t = c.get_yticklabels()[idx]; t.set_color(col); t.set_fontweight('bold')
    c.set_xlabel(text('Records in the year (log scale); label: count (reporting establishments)', 'Registros del año (escala log); etiqueta: recuento (establecimientos)', lang), fontsize=6.8)
    # (d) A05 entries by REM category, 2021–2025
    d = fig.add_subplot(gs[1, 1]); clean(d); pos = d.get_position(); d.set_position([pos.x0 + 0.03, pos.y0, pos.width - 0.03, pos.height])
    cats = [('05990022', 'Autism', 'Autismo', GREEN, '^'), ('05990026', 'PDD unspecified', 'TGD no especificado', GREY, 'o'), ('05990023', 'Asperger syndrome', 'Síndrome de Asperger', ORANGE, 's'), ('05990025', 'Disintegrative disorder', 'Trastorno desintegrativo', PINK, 'D')]
    for cd, en, es, col, mk in cats:
        z = rem_series(cd).reindex(YRS_REM); d.plot(z.index, z.total, color=col, marker=mk, label=text(en, es, lang)); end_label(d, 2025, z.total[2025], num(z.total[2025], lang), col, dx=3, size=6.2)
    log_axis(d, 'y', lang); d.set_ylim(10, 200000); year_ticks(d, YRS_REM); d.set_xlim(2020.6, 2025.9); law_line(d, lang, y=0.96)
    d.set_ylabel(text('A05 entries by category (log scale)', 'Ingresos A05 por categoría (escala log)', lang)); d.legend(loc='upper left', fontsize=6.4, handlelength=1.4)
    for ax, ch in zip([a, b, c, d], 'abcd'): letter(fig, ax, ch, dx=(-0.25 if ch == 'c' else -0.085))
    save(fig, 'Figure_S4', lang)

# ------------------------------------------------------------------ S5 education and population detail
def figS5(lang):
    style(); fig = plt.figure(figsize=(175/25.4, 150/25.4))
    gs = fig.add_gridspec(2, 2, left=0.10, right=0.975, top=0.96, bottom=0.09, hspace=0.62, wspace=0.42)
    ed = pd.read_csv(TIDY/'education_summary_year.csv').set_index('year'); pop = pd.read_csv(TIDY/'coverage_layers_year.csv').set_index('year').ine_population_base2017_30jun
    # (a) JUNAEB reported autism by grade
    a = fig.add_subplot(gs[0, 0]); clean(a)
    levels = [('parvularia', 'Pre-school', 'Prekínder–kínder', BLUE, 'o'), ('basico1', 'Grade 1', '1º básico', ORANGE, 's'), ('basico5', 'Grade 5', '5º básico', GREEN, '^'), ('medio1', 'Grade 9', '1º medio', PINK, 'D')]
    for key, en, es, col, mk in levels:
        w = ed[f'junaeb_{key}_pct_weighted']; lo = ed[f'junaeb_{key}_pct_weighted_lo']; hi = ed[f'junaeb_{key}_pct_weighted_hi']; u = ed[f'junaeb_{key}_pct_unweighted']
        yy = w.dropna().index
        a.errorbar(yy, w[yy], yerr=[w[yy] - lo[yy], hi[yy] - w[yy]], fmt=mk + '-', color=col, ms=3.2, capsize=1.5, lw=1, label=text(en, es, lang))
        u23 = u.get(2023, np.nan)
        if not np.isnan(u23): a.scatter([2023], [u23], marker=mk, s=14, facecolors='white', edgecolors=col, linewidths=1.0, zorder=3)
        if len(yy): end_label(a, yy[-1], w[yy[-1]], num(w[yy[-1]], lang, 1), col, dx=3, size=6.2)
    a.set_ylim(0, 10); a.set_xlim(2022.6, 2025.7); a.set_xticks([2023, 2024, 2025]); a.set_ylabel(text('Students with reported autism (%)', 'Estudiantes con autismo reportado (%)', lang))
    a.legend(loc='upper left', fontsize=6.4, handlelength=1.4); a.text(0.98, 0.03, text('Open markers: 2023 unweighted', 'Marcadores vacíos: 2023 sin ponderar', lang), transform=a.transAxes, ha='right', fontsize=6.2, color='#444444')
    # (b) records per 100 000 residents, crude, one strip per system
    b = fig.add_subplot(gs[0, 1]); clean(b, grid=None)
    g = load_grd_summary().query("panel=='observed' and position=='any'").set_index('year')
    strips = [('GRD eligible episodes', 'Episodios GRD elegibles', (g.n_episodes_f84 / pop.reindex(g.index) * 1e5), BLUE),
              ('GRD persons within year', 'Personas GRD dentro del año', (g.persons_within_year / pop.reindex(g.index) * 1e5), SKY),
              ('A05 strict-autism entries', 'Ingresos A05 autismo estricto', (rem_series('05990022').total / pop * 1e5).dropna(), GREEN),
              ('P2 December stock', 'Stock P2 de diciembre', (rem_series('P2500500', measure='december_stock').total / pop * 1e5).dropna(), PINK),
              ('PIE harmonised registrations', 'Registros PIE armonizados', (ed.pie_harmonised_n / pop.reindex(ed.index) * 1e5).dropna(), GOLD)]
    n = len(strips); yrs = list(range(2019, 2026))
    for i, (en, es, ser, col) in enumerate(strips):
        base = (n - 1 - i) * 1.25; mx = float(ser.max())
        for yv in yrs:
            if yv in ser.index and not np.isnan(ser[yv]): b.bar(yv, ser[yv] / mx, bottom=base, width=0.7, color=col, zorder=2)
        b.text(2018.45, base + 0.5, text(en, es, lang), ha='right', va='center', fontsize=6.4)
        b.text(2018.45, base + 1.0, num(mx, lang, 1 if mx < 100 else 0), ha='right', va='center', fontsize=5.8, color='#555555')
        b.axhline(base, color='#999999', lw=0.5)
    b.set_ylim(-0.1, n * 1.25); b.set_yticks([]); b.set_xticks(yrs); b.set_xticklabels(["’" + str(y)[2:] for y in yrs]); b.set_xlim(2018.5, 2025.5)
    b.set_xlabel(text('Year; strips scaled to their maximum\n(grey: max. per 100 000 residents)', 'Año; franjas escaladas a su máximo\n(gris: máx. por 100 000 residentes)', lang), fontsize=6.2)
    pos = b.get_position(); b.set_position([pos.x0 + 0.13, pos.y0 + 0.02, pos.width - 0.13, pos.height - 0.02])
    # (c) PIE share of total PIE enrolment
    c = fig.add_subplot(gs[1, 0]); clean(c); shade_pandemic(c)
    c.plot(ed.index, ed.pie_harmonised_share_of_pie_pct, color=SKY, marker='o', label=text('Harmonised autism / PIE enrolment (Apuntes 60)', 'Armonizado / matrícula PIE (Apuntes 60)', lang))
    c.plot(ed.index, ed.pie_harmonised_share_of_applicants_sinaces_pct, color=BLACK, marker='x', ls='--', label=text('Harmonised autism / PIE applicants (SINACES)', 'Armonizado / postulantes PIE (SINACES)', lang))
    c.plot(ed.index, ed.pie_tea_strict_share_of_pie_pct, color=BLUE, marker='s', ls=':', label=text('Autism category / PIE enrolment', 'Categoría autismo / matrícula PIE', lang))
    law_line(c, lang, y=0.30); c.set_ylim(0, 30); year_ticks(c, range(2019, 2026), short=True); c.set_xlim(2018.6, 2025.5)
    c.set_ylabel(text('Share of PIE students (%)', 'Proporción de estudiantes PIE (%)', lang)); c.legend(loc='upper left', fontsize=6.2, handlelength=1.4)
    # (d) special schools and exceptional entries
    d = fig.add_subplot(gs[1, 1]); clean(d)
    d.bar(ed.index, ed.pie_tea_exceptional_entry_n, color=GOLD, width=0.6, label=text('Exceptional PIE entries, autism', 'Ingresos excepcionales PIE, autismo', lang), zorder=2)
    d.plot(ed.index, ed.special_schools_autism_n, color=PINK, marker='v', label=text('Special schools, autism (students)', 'Escuelas especiales, autismo (estudiantes)', lang))
    d.set_ylim(0, 32000); d.yaxis.set_major_formatter(thousands(lang)); d.set_xticks([2022, 2023, 2024, 2025]); d.set_xlim(2021.4, 2025.6)
    d.set_ylabel(text('Students (n)', 'Estudiantes (n)', lang)); d.legend(loc='upper left', fontsize=6.4, handlelength=1.4)
    for ax, ch in zip([a, b, c, d], 'abcd'): letter(fig, ax, ch, dx=(-0.22 if ch == 'b' else -0.085))
    save(fig, 'Figure_S5', lang)

# ------------------------------------------------------------------ S6 territorial distribution
# The inherited revision-09 plate was built by build_territorial_revision.py, which does NOT
# reproject: it draws the shapefile in its native coordinates with an equal aspect ratio. This
# redraw uses an Albers equal-area projection instead, fitted to the printed artwork, so the map
# panels are geometrically equivalent but not identical to the inherited plate (band aspect ratios
# differ by 1-2%). That original source is not in this repository (it lives in the untracked
# version folders), which is why the projection is declared here rather than imported.
S6_ALBERS = ('+proj=aea +lat_1=-20 +lat_2=-50 +lat_0=-37 +lon_0=-71 +x_0=0 +y_0=0 '
             '+datum=WGS84 +units=m +no_defs')
S6_BANDS = [('North', 'Norte', (15, 1, 2, 3, 4)),
            ('Central', 'Centro', (5, 13, 6, 7, 16, 8, 9, 14, 10)),
            ('Austral', 'Austral', (11, 12))]
S6_OFFGRAPH = (5104, 5201, 12201, 12202)   # outside the spatial graph (342 of 346 comunas remain)
S6_OFFEXTENT = (5104, 5201)                # Juan Fernandez and Isla de Pascua: outside every band window
# Cluster colours sampled from the inherited plate. report_helpers.CLUSTER_COLORS carries the
# near-identical RdBu five-class set (#b2182b / #2166ac / #92c5de / #e8e8e8) that the rest of the site
# uses; the plate's own values are kept here so the redraw matches the printed figure.
S6_CLUSTER = {'High–High': '#c0392b', 'Low–Low': '#2471a3', 'Low–High': '#8bb8d8', 'none': '#f2f2f2'}
S6_MASKED, S6_OFF, S6_EDGE = '#d0d0d0', '#9a9a9a', '#9e9e9e'
S6_W, S6_H = 2067, 2516        # canvas of the inherited plate: 175.0 x 213.0 mm at 300 dpi
S6_TOP, S6_BOT, S6_MIDY = 198, 859, 528.5      # pixel band of the tallest strip, and its centre
S6_CENTRES = (251.5, 531.0, 810.5)             # x centres of the three strips of panel (a)
S6_PANEL_DX = 1087.0                           # panel (b) repeats them shifted by this much


_S6_GEOM = {}


def _s6_communes():
    """Commune polygons keyed by CUT, in the reconstructed Albers equal-area CRS (read once per run).

    data/comunas.shp is NOT tracked by git (.gitignore excludes /data/). docs/grd.qmd already draws
    its commune maps from that same shapefile, so Figure S6 depends on it on exactly the same terms.
    Antartica (CUT 12202, 1 episode) has no polygon in the file and can never be drawn."""
    if 'gdf' in _S6_GEOM: return _S6_GEOM['gdf']
    import warnings
    import geopandas as gpd
    shp = BASE.parents[1]/'data'/'comunas.shp'
    if not shp.exists():
        raise FileNotFoundError(f'Figure S6 needs the untracked commune shapefile {shp}; '
                                'it ships with the working copy, not with a clone.')
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        g = gpd.read_file(shp)
    g = g.loc[g.cod_comuna > 0, ['cod_comuna', 'codregion', 'geometry']].rename(columns={'cod_comuna': 'CUT'})
    g['geometry'] = g.geometry.simplify(700)
    _S6_GEOM['gdf'] = g.to_crs(S6_ALBERS)
    return _S6_GEOM['gdf']


def _s6_strips(fig, gdf, lang, dx, draw):
    """The three north-south strips of one map panel, all at one metric scale.

    A gridspec cannot do this: each strip gets its own axes sized in inches from its own extent in
    metres, so 'the three strips share a metric scale' is true by construction."""
    axes = []
    keep = [gdf[gdf.codregion.isin(regs) & ~gdf.CUT.isin(S6_OFFEXTENT)] for _, _, regs in S6_BANDS]
    bounds = [k.total_bounds for k in keep]
    scale = max(b[3] - b[1] for b in bounds) / ((S6_BOT - S6_TOP)/300)     # metres per inch
    fw, fh = fig.get_figwidth(), fig.get_figheight()
    for (en, es, regs), b, cx in zip(S6_BANDS, bounds, S6_CENTRES):
        w_in, h_in = (b[2] - b[0])/scale, (b[3] - b[1])/scale
        ax = fig.add_axes([((cx + dx)/300 - w_in/2)/fw, ((S6_H - S6_MIDY)/300 - h_in/2)/fh, w_in/fw, h_in/fh])
        ax.set_xlim(b[0], b[2]); ax.set_ylim(b[1], b[3]); ax.set_aspect('equal')
        ax.set_axis_off(); ax.grid(False)
        draw(ax, gdf[gdf.codregion.isin(regs)])
        fig.text((cx + dx)/S6_W, (S6_H - S6_TOP + 42)/S6_H, text(en, es, lang), ha='center', va='bottom', fontsize=8)
        axes.append(ax)
    return axes


def _s6_disclosure(ax, sub):
    """The two disclosure classes the plate shades identically in both maps: hatch colour follows the
    edge colour of the collection, so masked comunas get white slashes and zero comunas black dots."""
    off = sub[sub.CUT.isin(S6_OFFGRAPH)]
    if len(off): off.plot(ax=ax, color=S6_OFF, edgecolor=S6_EDGE, linewidth=0.17)
    msk = sub[sub.disclosure == 'masked']
    if len(msk): msk.plot(ax=ax, color=S6_MASKED, edgecolor='white', linewidth=0.17, hatch='///')
    zero = sub[sub.disclosure == 'zero']
    if len(zero): zero.plot(ax=ax, color='white', edgecolor='#333333', linewidth=0.17, hatch='....')


def figS6(lang):
    style(); plt.rcParams['hatch.linewidth'] = 0.55      # fine dots and slashes, as on the inherited plate
    fig = plt.figure(figsize=(S6_W/300, S6_H/300))
    import matplotlib.colors as mcolors
    from matplotlib.patches import Patch

    # ---- commune-level inputs of the two maps ------------------------------------------------
    e40 = pd.read_csv(CORPUS/'E40_grd_smoothed_ratio_comuna.csv')
    e40.columns = [c.lstrip('﻿') for c in e40.columns]                 # the header carries a BOM
    obs = e40['Observed episodes'].astype(str).str.strip()
    e40['disclosure'] = np.where(obs == '0', 'zero', np.where(obs == '<5', 'masked', 'shown'))
    e40['eb'] = e40['Empirical-Bayes smoothed standardised ratio'].astype(float)
    n_comunas = len(e40)
    e51 = pd.read_csv(CORPUS/'E51_lisa_significant_comunas.csv').query("Indicator=='GRD F84 episodes'")
    e42 = pd.read_csv(CORPUS/'E42_local_class_counts.csv').query("Indicator=='GRD F84 episodes'").iloc[0]
    counts = {'High–High': int(e42['LISA HH']), 'Low–Low': int(e42['LISA LL']),
              'Low–High': int(e42['LISA LH']), 'none': int(e42['LISA not significant'])}
    n_graph = sum(counts.values()) + int(e42['LISA HL'])
    assert e51.LISA.value_counts().to_dict() == {k: v for k, v in counts.items() if k != 'none' and v}, \
        'E51 rows and E42 counts disagree'                                  # legend counts cannot drift
    gdf = _s6_communes().merge(e40[['CUT', 'eb', 'disclosure']], on='CUT', how='left')
    gdf = gdf.merge(e51[['CUT', 'LISA']], on='CUT', how='left')
    gdf['LISA'] = gdf.LISA.fillna('none')

    # ---- (a) empirical-Bayes smoothed standardised ratio -------------------------------------
    norm = mcolors.TwoSlopeNorm(vmin=0, vcenter=1, vmax=3)

    def draw_a(ax, sub):
        shown = sub[(sub.disclosure == 'shown') & ~sub.CUT.isin(S6_OFFGRAPH)]
        if len(shown): shown.plot(ax=ax, column='eb', cmap='RdBu_r', norm=norm, edgecolor=S6_EDGE, linewidth=0.17)
        _s6_disclosure(ax, sub)

    axa = _s6_strips(fig, gdf, lang, 0.0, draw_a)
    cax = fig.add_axes([126/S6_W, (S6_H - 992)/S6_H, (919 - 126)/S6_W, 26/S6_H])
    ticks = [0, 0.5, 1, 2, 3]
    cb = fig.colorbar(plt.cm.ScalarMappable(cmap='RdBu_r', norm=norm), cax=cax, orientation='horizontal',
                      extend='both', ticks=ticks)
    labs = [num(v, lang, 1) for v in ticks]
    if lang == 'es': labs = [s[:-2] if s.endswith(',0') else s for s in labs]
    cb.ax.set_xticklabels(labs); cb.ax.tick_params(labelsize=7.2, length=2.5, width=0.7)
    cb.outline.set_linewidth(0.6)
    cb.set_label(text('EB ratio; national reference = 1', 'Razón EB; referencia nacional = 1', lang),
                 fontsize=7.4, labelpad=2)
    dots = text('Dotted: zero · Hatched: 1–4 episodes', 'Punteado: cero · Rayado: 1–4 episodios', lang)
    fig.text(S6_CENTRES[1]/S6_W, (S6_H - 1157)/S6_H, dots, ha='center', va='bottom', fontsize=7.2)

    # ---- (b) local Moran clusters -------------------------------------------------------------
    def draw_b(ax, sub):
        for key, col in S6_CLUSTER.items():
            z = sub[(sub.LISA == key) & ~sub.CUT.isin(S6_OFFGRAPH)]
            if len(z): z.plot(ax=ax, color=col, edgecolor=S6_EDGE, linewidth=0.17)
        _s6_disclosure(ax, sub)

    axb = _s6_strips(fig, gdf, lang, S6_PANEL_DX, draw_b)
    names = {'High–High': ('High–High', 'Alto–Alto'), 'Low–Low': ('Low–Low', 'Bajo–Bajo'),
             'Low–High': ('Low–High', 'Bajo–Alto'), 'none': ('No BH rejection', 'Sin rechazo BH')}
    order = ['High–High', 'Low–Low', 'Low–High', 'none']
    lax = fig.add_axes([1244/S6_W, (S6_H - 1078)/S6_H, (2030 - 1244)/S6_W, 116/S6_H])
    lax.set_axis_off(); lax.grid(False)
    lax.legend(handles=[Patch(fc=S6_CLUSTER[k], ec='#6b6b6b', lw=0.5,
                              label=f'{text(*names[k], lang)} ({num(counts[k], lang)})') for k in order],
               loc='upper center', ncol=2, fontsize=7.4, handlelength=1.1, handleheight=1.0,
               columnspacing=1.0, labelspacing=0.5, borderaxespad=0, frameon=False)
    fig.text((S6_CENTRES[1] + S6_PANEL_DX)/S6_W, (S6_H - 1194)/S6_H,
             dots + '\n' + text('Grey: outside the spatial graph', 'Gris: fuera del grafo espacial', lang),
             ha='center', va='bottom', fontsize=7.2, linespacing=1.3)

    # ---- (c) regional endpoints, 2019 and 2024 ------------------------------------------------
    ef9 = pd.read_csv(CORPUS/'EF9_territory.csv')
    ef9 = ef9[~ef9['Region of residence'].isin(['Without a linkable comuna', 'National total'])]
    y0, y1 = ef9.columns[1], ef9.columns[-1]

    def cell(s):
        rate, ci = s.split(';')[1].split('(')
        lo, hi = ci.rstrip(') ').split('–')
        return float(rate), float(lo), float(hi)

    c = fig.add_axes([351/S6_W, (S6_H - 2347)/S6_H, (951 - 351)/S6_W, (2347 - 1396)/S6_H]); clean(c, grid='x')
    for yr, col, mk in ((y0, BLUE, 'o'), (y1, ORANGE, 's')):
        v = np.array([cell(s) for s in ef9[yr]])
        c.errorbar(v[:, 0], np.arange(len(v)), xerr=[v[:, 0] - v[:, 1], v[:, 2] - v[:, 0]], fmt=mk,
                   color=col, ms=3.4, capsize=1.4, elinewidth=0.7, lw=0, label=yr)
    c.set_yticks(range(len(ef9)))
    c.set_yticklabels([r.replace('Arica y Parinacota', 'Arica y P.') for r in ef9['Region of residence']], fontsize=7.2)
    c.invert_yaxis(); c.set_xlim(left=0); c.set_ylim(len(ef9) - 0.4, -0.6)   # autoscale: a fixed
    # upper limit of 80 clipped the 2024 upper Poisson bounds of 81.2 and 86.6 out of the plot.
    c.set_xlabel(text('Episodes / 100 000 residents\n(Poisson 95% CI)', 'Episodios / 100 000 residentes\n(IC 95% de Poisson)', lang))
    c.legend(loc='lower center', bbox_to_anchor=(0.5, 1.005), ncol=2, fontsize=7.4, handlelength=1.3, columnspacing=2.6, borderaxespad=0)

    # ---- (d) concentration and coverage -------------------------------------------------------
    e47 = pd.read_csv(CORPUS/'E47_inequality_gini_theil.csv').query("Indicator=='GRD F84 episodes'")
    yrs = [int(p) for p in e47.Period if p.isdigit()]
    ann = e47[e47.Period.isin([str(y) for y in yrs])].set_index('Period')
    gini = [float(ann.loc[str(y), 'Gini index']) for y in yrs]
    with_records = [n_comunas - int(ann.loc[str(y), 'Comunas with zero']) for y in yrs]
    d1 = fig.add_axes([1200/S6_W, (S6_H - 1801)/S6_H, (2037 - 1200)/S6_W, (1801 - 1396)/S6_H]); clean(d1)
    d1.plot(yrs, gini, color=BLUE, marker='o')
    end_label(d1, yrs[0], gini[0], num(gini[0], lang, 3), BLUE, dx=-5, dy=10)
    end_label(d1, yrs[-1], gini[-1], num(gini[-1], lang, 3), BLUE, dx=-3, dy=11, ha='right')
    d1.set_ylim(0, 0.45); d1.set_yticks([0, 0.1, 0.2, 0.3, 0.4])
    gl = [num(v, lang, 1) for v in [0, 0.1, 0.2, 0.3, 0.4]]
    d1.set_yticklabels([g[:-2] if lang == 'es' and g.endswith(',0') else g for g in gl])
    d1.set_ylabel(text('Gini', 'Gini', lang))
    year_ticks(d1, yrs, short=True); d1.set_xlim(yrs[0] - 0.4, yrs[-1] + 0.4); d1.set_xticklabels([])
    d2 = fig.add_axes([1200/S6_W, (S6_H - 2347)/S6_H, (2037 - 1200)/S6_W, (2347 - 1941)/S6_H]); clean(d2)
    d2.plot(yrs, with_records, color=ORANGE, marker='s')
    end_label(d2, yrs[0], with_records[0], num(with_records[0], lang), ORANGE, dx=-5, dy=11)
    end_label(d2, yrs[-1], with_records[-1], num(with_records[-1], lang), ORANGE, dx=-3, dy=11, ha='right')
    d2.set_ylim(0, 340); d2.set_yticks([0, 100, 200, 300]); d2.yaxis.set_major_formatter(thousands(lang))
    d2.set_ylabel(text('Communes with records', 'Comunas con registros', lang))
    year_ticks(d2, yrs, short=True); d2.set_xlim(yrs[0] - 0.4, yrs[-1] + 0.4)
    d2.set_xlabel(text(f'Year ({yrs[0]}–{yrs[-1]})', f'Año ({yrs[0]}–{yrs[-1]})', lang))
    fig.text((1200 + 2037)/2/S6_W, (S6_H - 2492)/S6_H,
             text(f'GRD: residence · {num(n_comunas, lang)} communes; spatial graph: {num(n_graph, lang)}',
                  f'GRD: residencia · {num(n_comunas, lang)} comunas; grafo espacial: {num(n_graph, lang)}', lang),
             ha='center', va='bottom', fontsize=7.2)
    for ax, ch in ((axa[0], 'a'), (axb[0], 'b')): letter(fig, ax, ch, dx=-0.020, dy=0.062)
    letter(fig, c, 'c', dx=0.0, dy=0.020); letter(fig, d1, 'd', dx=0.0, dy=0.020)
    save(fig, 'Figure_S6', lang)

# ------------------------------------------------------------------ S7 territorial correlations
def figS7(lang):
    style(); fig = plt.figure(figsize=(175/25.4, 165/25.4))
    gs = fig.add_gridspec(2, 2, left=0.10, right=0.935, top=0.965, bottom=0.09, hspace=0.55, wspace=0.45)
    # Public extract: cells with 1-4 records are masked per variable, so dropna() leaves exactly the displayed communes.
    base = pd.read_csv(DATA/'communes_public.csv'); corr = pd.read_csv(DATA/'S4_correlations_selected_sensitivities.csv')
    def scatter(ax, x, y, xl, yl):
        z = base.dropna(subset=[x, y])
        ax.scatter(z[x], z[y], s=12, color=BLUE, alpha=0.7, edgecolors='white', linewidths=0.3, clip_on=False)
        r = corr[(corr.pair == x + '–' + y) & (corr.scope == 'commune') & (corr.analysis == 'core')].iloc[0]
        ax.text(0.02, 0.97, f'ρ = {num(r.rho, lang, 2)}; n = {int(r.n)}; {len(z)} ' + text('shown', 'visibles', lang), transform=ax.transAxes, va='top', fontsize=6.6)
        ax.set_xlabel(xl); ax.set_ylabel(yl); ax.set_xlim(left=0); ax.set_ylim(0, float(z[y].max()) * 1.2)
    a = fig.add_subplot(gs[0, 0]); clean(a, grid='both')
    scatter(a, 'GRD', 'P2', text('GRD: episodes per 100 000\nresident person-years', 'GRD: episodios por 100 000\npersonas-año residentes', lang), text('P2 (0–19 y): mean December stock\nper 100 000 residents', 'P2 (0–19 años): stock medio de diciembre\npor 100 000 residentes', lang))
    b = fig.add_subplot(gs[0, 1]); clean(b, grid='both')
    scatter(b, 'A05', 'P2', text('A05: entries per 100 000\nresident person-years', 'A05: ingresos por 100 000\npersonas-año residentes', lang), text('P2 (0–19 y): mean December stock\nper 100 000 residents', 'P2 (0–19 años): stock medio de diciembre\npor 100 000 residentes', lang))
    # (c) coefficients by analysis and scale
    c = fig.add_subplot(gs[1, 0]); clean(c, grid='x'); pos = c.get_position(); c.set_position([pos.x0 + 0.13, pos.y0, pos.width - 0.13, pos.height])
    analyses = [('core', 'Core (commune)', 'Base (comuna)'), ('stable_establishments', 'Stable establishments', 'Establecimientos estables'), ('exclude_metropolitan', 'Excl. Metropolitan Region', 'Sin Región Metropolitana'),
                ('all_three_complete', 'All three sources complete', 'Tres fuentes completas'), ('raw_sir', 'Raw standardised ratios', 'Razones estandarizadas crudas')]
    pairs = [('GRD–A05', BLUE, 'o'), ('GRD–P2', PINK, 's'), ('A05–P2', GREEN, '^')]
    ticks = []; labels = []
    for i, (an, en, es) in enumerate(analyses):
        for j, (pair, col, mk) in enumerate(pairs):
            z = corr[(corr.pair == pair) & (corr.scope == 'commune') & (corr.analysis == an)]
            if len(z): c.plot(z.rho.iloc[0], i + (j - 1) * 0.25, mk, color=col, ms=4, label=pair if i == 0 else None)
        ticks.append(i); labels.append(text(en, es, lang))
    reg = corr[(corr.scope == 'region') & (corr.analysis == 'core')]
    for j, (pair, col, mk) in enumerate(pairs):
        z = reg[reg.pair == pair]
        if len(z): c.plot(z.rho.iloc[0], len(analyses) + (j - 1) * 0.25, mk, color=col, ms=4, mfc='white')
    ticks.append(len(analyses)); labels.append(text('Core (region, open markers)', 'Base (región, marcadores vacíos)', lang))
    c.set_yticks(ticks); c.set_yticklabels(labels, fontsize=6.4); c.invert_yaxis(); c.axvline(0, color='#777', ls=':', lw=0.7); c.set_xlim(-0.15, 0.8)
    c.set_xlabel(text('Spearman ρ, 2021–2024 window\n(no spatial inference)', 'ρ de Spearman, ventana 2021–2024\n(sin inferencia espacial)', lang)); c.legend(loc='lower center', bbox_to_anchor=(0.5, 1.0), ncol=3, fontsize=6.4, handlelength=1, columnspacing=0.9, frameon=False, borderaxespad=0.1)
    # (d) sensitivity of GRD–A05 to the minimum count threshold
    d = fig.add_subplot(gs[1, 1]); clean(d)
    # Precomputed on the complete analytic file (manuscript values); see the module docstring.
    ts = pd.read_csv(DATA/'S7d_threshold_sensitivity.csv'); ks = ts.k.tolist(); rhos = ts.rho.tolist(); los = ts.rho_lo.tolist(); his = ts.rho_hi.tolist(); ns = ts.n_communes.tolist()
    d.fill_between(ks, los, his, color=BLUE, alpha=0.15, lw=0); d.plot(ks, rhos, color=BLUE, marker='o', ms=3, label=text('ρ (95% CI, Fisher z)', 'ρ (IC 95%, z de Fisher)', lang))
    d.axhline(0, color='#777', ls=':', lw=0.7); d.set_ylim(-0.2, 1); d.set_ylabel(text('Spearman ρ, GRD–A05', 'ρ de Spearman, GRD–A05', lang)); d.set_xlabel(text('Minimum count k\n(communes with GRD ≥ k and A05 ≥ k)', 'Recuento mínimo k\n(comunas con GRD ≥ k y A05 ≥ k)', lang), fontsize=6.8)
    d2 = d.twinx(); d2.grid(False); d2.spines['top'].set_visible(False); d2.plot(ks, ns, color=GREY, marker='s', ms=2.6, ls='--', lw=0.9, label=text('Communes included (right)', 'Comunas incluidas (derecha)', lang)); d2.set_ylim(0, 350); d2.set_ylabel(text('Communes (n)', 'Comunas (n)', lang), fontsize=7.2, color='#555555'); d2.tick_params(axis='y', colors='#555555')
    h1, l1 = d.get_legend_handles_labels(); h2, l2 = d2.get_legend_handles_labels(); d.legend(h1 + h2, l1 + l2, loc='upper right', fontsize=6.4, handlelength=1.4)
    for ax, ch in zip([a, b, c, d], 'abcd'): letter(fig, ax, ch, dx=(-0.19 if ch == 'c' else -0.085))
    save(fig, 'Figure_S7', lang)

# ------------------------------------------------------------------ S8 case definition and model diagnostics
def figS8(lang):
    style(); fig = plt.figure(figsize=(175/25.4, 95/25.4))
    gs = fig.add_gridspec(1, 2, left=0.10, right=0.975, top=0.93, bottom=0.17, wspace=0.45, width_ratios=[1, 1.35])
    a = fig.add_subplot(gs[0, 0]); clean(a); shade_pandemic(a)
    cr = pd.read_csv(DATA/'case_definition_variant_rates.csv').set_index('year')
    for col_, c_, mk, en, es in (('con_rett', GREY, 'D', 'Full F84 family (with F84.2)', 'Familia F84 completa (con F84.2)'), ('sin_rett', BLUE, 'o', 'Selected: F84 excluding F84.2', 'Seleccionada: F84 sin F84.2'), ('strict_autism_f840', ORANGE, 's', 'F84.0 only', 'Solo F84.0')):
        a.plot(cr.index, cr[col_], color=c_, marker=mk, ls='-' if col_ == 'sin_rett' else '--', label=text(en, es, lang)); end_label(a, 2024, cr[col_][2024], num(cr[col_][2024], lang, 1), c_, dx=3, dy={'con_rett': 7, 'sin_rett': -4, 'strict_autism_f840': 0}[col_], size=6.2)
    a.set_ylim(0, 950); year_ticks(a, YRS_GRD, short=True); a.set_xlim(2018.6, 2025.2); a.set_ylabel(text('Episodes per 100 000 GRD episodes', 'Episodios por 100 000 episodios GRD', lang)); a.legend(loc='upper left', fontsize=6.4, handlelength=1.4)
    b = fig.add_subplot(gs[0, 1]); clean(b, grid='x'); pos = b.get_position(); b.set_position([pos.x0 + 0.15, pos.y0, pos.width - 0.15, pos.height])
    m = pd.read_csv(DATA/'selected_models_scientific.csv')
    lab = {'grd_rate:sin_rett:observed:all:any:none:2019-2024': ('GRD any position, 2019–24', 'GRD cualquier posición, 2019–24'), 'grd_rate:sin_rett:fixed65:all:any:none:2019-2024': ('GRD stable panel, 2019–24', 'GRD panel estable, 2019–24'),
           'grd_rate:sin_rett:observed:all:any:depth:2019-2024': ('GRD any, coding-depth adjusted', 'GRD cualquier posición, ajustado profundidad'), 'grd_rate:sin_rett:observed:all:principal:none:2019-2024': ('GRD principal, 2019–24', 'GRD principal, 2019–24'),
           'grd_rate:sin_rett:observed:all:principal:depth_disruption:2019-2024': ('GRD principal, depth + 2020–21', 'GRD principal, profundidad + 2020–21'), 'grd_rate:sin_rett:observed:all:any:none:2021-2024': ('GRD any, 2021–24', 'GRD cualquier posición, 2021–24'),
           'grd_hospital:sin_rett:observed:any:none:2019-2024:cluster': ('GRD hospital fixed effects, clustered', 'GRD efectos fijos por hospital, agrupado'), 'a05_entry:strict_autism:estab:none:2021-2025': ('A05 entries per establishment', 'Ingresos A05 por establecimiento'),
           'a05_entry:strict_autism:stable_pop:none:2021-2025': ('A05 entries, stable panel per resident', 'Ingresos A05, panel estable por residente'), 'p2_dec:none:2021-2025': ('P2 December stock per resident', 'Stock P2 de diciembre por residente'),
           'p2_dec:estab:2021-2025': ('P2 December stock per establishment', 'Stock P2 de diciembre por establecimiento')}
    ys = []; names = []
    for i, r in m.reset_index().iterrows():
        en, es = lab.get(r.model_id, (r.model_id.split(':')[0] + ' ' + str(r.years), r.model_id.split(':')[0] + ' ' + str(r.years)))
        b.errorbar(r.apc, i, xerr=[[r.apc - r.apc_lo], [r.apc_hi - r.apc]], fmt='o', color=BLUE, ms=3.6, capsize=1.6, lw=0.9)
        b.text(max(r.apc_hi, 0) + 3, i, text(f'dispersion {num(r.dispersion, lang, 1)}; df {int(r.df_resid)}', f'dispersión {num(r.dispersion, lang, 1)}; gl {int(r.df_resid)}', lang), va='center', fontsize=6.0, color='#444444')
        ys.append(i); names.append(text(en, es, lang))
    b.set_yticks(ys); b.set_yticklabels(names, fontsize=6.2); b.invert_yaxis(); b.axvline(0, color='#555', ls=':', lw=0.7); b.set_xlim(-30, 165)
    b.set_xlabel(text('Annual percent change (95% CI)', 'Cambio porcentual anual (IC 95%)', lang))
    for ax, ch in zip([a, b], 'ab'): letter(fig, ax, ch, dx=(-0.30 if ch == 'b' else -0.085), dy=0.02)
    save(fig, 'Figure_S8', lang)

# ------------------------------------------------------------------ S9 clinical detail
def figS9(lang):
    style(); fig = plt.figure(figsize=(175/25.4, 95/25.4))
    gs = fig.add_gridspec(1, 2, left=0.10, right=0.975, top=0.93, bottom=0.17, wspace=0.45, width_ratios=[1.35, 1])
    a = fig.add_subplot(gs[0, 0]); clean(a, grid='x'); pos = a.get_position(); a.set_position([pos.x0 + 0.20, pos.y0, pos.width - 0.20, pos.height])
    ch = pd.read_csv(DATA/'clinical_chapters_selected.csv'); order = ch[ch.year == 2024].sort_values('pct_of_f84_episodes', ascending=False).group_label.tolist()
    for i, lab in enumerate(order):
        v0 = ch[(ch.group_label == lab) & (ch.year == 2019)].pct_of_f84_episodes; v1 = ch[(ch.group_label == lab) & (ch.year == 2024)].pct_of_f84_episodes
        v0 = float(v0.iloc[0]) if len(v0) else np.nan; v1 = float(v1.iloc[0]) if len(v1) else np.nan
        a.plot([v0, v1], [i, i], color=LIGHT, lw=1.2, zorder=1); a.scatter([v0], [i], s=18, facecolors='white', edgecolors=BLUE, linewidths=1.1, zorder=3); a.scatter([v1], [i], s=18, color=ORANGE, marker='s', zorder=3)
    n19 = int(ch[ch.year == 2019].n_f84_episodes_cell.iloc[0]); n24 = int(ch[ch.year == 2024].n_f84_episodes_cell.iloc[0])
    a.scatter([], [], s=18, facecolors='white', edgecolors=BLUE, linewidths=1.1, label=f'2019 (n={num(n19, lang)})'); a.scatter([], [], s=18, color=ORANGE, marker='s', label=f'2024 (n={num(n24, lang)})')
    a.set_yticks(range(len(order))); a.set_yticklabels([CHAP_EN.get(l, l) if lang == 'en' else l for l in order], fontsize=6.4); a.invert_yaxis(); a.set_xlim(0, 60)
    a.set_xlabel(text('Eligible episodes with a diagnosis in the chapter (%)', 'Episodios elegibles con un diagnóstico del capítulo (%)', lang), fontsize=7.2); a.legend(loc='lower right', fontsize=6.4, handlelength=1.2)
    b = fig.add_subplot(gs[0, 1]); clean(b); shade_pandemic(b)
    los = pd.read_csv(TIDY/'grd_length_of_stay.csv').query("variant=='sin_rett' and panel=='observed' and activity=='hospitalisation'")
    for posn, col, mk, en, es in (('principal', ORANGE, 'D', 'Eligible code as principal diagnosis', 'Código elegible principal'), ('secondary_only', BLUE, 'o', 'Eligible code only secondary', 'Código elegible solo secundario')):
        z = los[los.position == posn].set_index('year').reindex(YRS_GRD); b.plot(z.index, z.mean_days, color=col, marker=mk, label=text(en, es, lang)); b.plot(z.index, z.median_days, color=col, marker=mk, mfc='white', ls=':', lw=0.9, ms=2.8)
        end_label(b, 2024, z.mean_days[2024], num(z.mean_days[2024], lang, 1), col, dx=3, size=6.2)
    b.plot([], [], color='#444', ls='-', label=text('Mean', 'Media', lang)); b.plot([], [], color='#444', ls=':', label=text('Median', 'Mediana', lang))
    b.set_ylim(0, 40); year_ticks(b, YRS_GRD, short=True); b.set_xlim(2018.6, 2024.9); b.set_ylabel(text('Length of stay, hospitalisation\nepisodes (days)', 'Estancia, episodios de\nhospitalización (días)', lang)); b.legend(loc='upper right', fontsize=6.2, handlelength=1.4, ncol=1)
    for ax, ch_ in zip([a, b], 'ab'): letter(fig, ax, ch_, dx=(-0.34 if ch_ == 'a' else -0.085), dy=0.02)
    save(fig, 'Figure_S9', lang)

if __name__ == '__main__':
    which = sys.argv[1:] or ['S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8', 'S9']
    for lang in ('en', 'es'):
        for key in which:
            globals()['fig' + key](lang)
    write_qa('figuras_suplementarias_qa.json')
