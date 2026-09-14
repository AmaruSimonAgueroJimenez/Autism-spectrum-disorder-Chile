"""Supplementary figures S2–S9 of the manuscript (version 10), in English and Spanish, for docs/study.

Adapted copy of `technical/sources/build_v10_supp_figures.py` of revision 10. S1 (data flow) and S6
(territorial maps) are static plates inherited from revision 09, stored in `docs/study/figures/<language>/`;
the sensitivity to the count threshold (S7d) is read precomputed from `S7d_threshold_sensitivity.csv`
because the complete commune file is not published.
Usage: python3 figuras_suplementarias.py [S2 S3 S4 S5 S7 S8 S9 copy]
"""
import sys, shutil
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
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

def copy_reused():
    """S1 (data flow) and S6 (territorial maps) are static assets inherited from revision 09 (its Figure_S1 and
    Figure_S3); this only checks that they are present next to the generated plates."""
    for lang in ('en', 'es'):
        for name in ('Figure_S1', 'Figure_S6'):
            for ext in ('png', 'pdf'):
                assert (BASE/'figures'/lang/f'{name}.{ext}').exists(), (lang, name, ext)
    print('  S1 and S6: static plates inherited from revision 09 are present')

if __name__ == '__main__':
    which = sys.argv[1:] or ['S2', 'S3', 'S4', 'S5', 'S7', 'S8', 'S9', 'copy']
    for lang in ('en', 'es'):
        for key in which:
            if key == 'copy': continue
            globals()['fig' + key](lang)
    if 'copy' in which: copy_reused()
    write_qa('figuras_suplementarias_qa.json')
