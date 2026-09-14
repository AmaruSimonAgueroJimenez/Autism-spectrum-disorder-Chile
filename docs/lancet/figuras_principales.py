"""Main figures 1–4 of the manuscript (version 10), in English and Spanish, for docs/lancet.

Adapted copy of `technical/sources/build_v10_main_figures.py` of revision 10. It reads the public copies in
`docs/lancet/data/` (the commune comparison uses `communes_public.csv`, without identifiers and with cells
of 1 to 4 records masked) and writes `docs/lancet/figures/<language>/Figure_N.*`.
Case definition: GRD = F84 family without F84.2 (sin_rett); REM A05/P6 = strict autism code unless
labelled 'F84 family'. Usage: python3 figuras_principales.py [1 2 3 4]
"""
import sys, json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from figstyle import *

pd.set_option('mode.chained_assignment', None)
YRS_GRD = list(range(2019, 2025)); YRS_REM = list(range(2021, 2026))

# ----------------------------------------------------------------------------- data
def load_grd_summary():
    g = pd.read_csv(TIDY/'grd_year_summary.csv').query("variant=='sin_rett' and activity=='all'")
    return g

def load_forest():
    m = pd.read_csv(TIDY/'models_summary.csv', low_memory=False).query("variant=='sin_rett'")
    def pick(**kw):
        z = m.copy()
        for k, v in kw.items():
            z = z[z[k].isna()] if v is None else z[z[k] == v]
        assert len(z) == 1, (kw, len(z))
        r = z.iloc[0]; return float(r.apc), float(r.apc_lo), float(r.apc_hi), int(r.df_resid)
    rows = [  # (group, label_en, label_es, values, colour, marker)
     ('grd', 'Any position, observed panel, 2019–24', 'Cualquier posición, panel observado, 2019–24',
      pick(estimand='est_grd_rate', panel='panel_observed', activity='act_all', position='pos_any', covariates='cov_none', years='2019-2024'), BLUE, 'o'),
     ('grd', 'Any position, stable 65 hospitals, 2019–24', 'Cualquier posición, 65 hospitales estables, 2019–24',
      pick(estimand='est_grd_rate', panel='panel_fixed65', activity='act_all', position='pos_any', covariates='cov_none', years='2019-2024'), BLUE, 's'),
     ('grd', 'Any position, adjusted for coding depth, 2019–24', 'Cualquier posición, ajustado por profundidad de codificación, 2019–24',
      pick(estimand='est_grd_rate', panel='panel_observed', activity='act_all', position='pos_any', covariates='cov_depth', years='2019-2024'), BLUE, 'D'),
     ('grd', 'Any position, 2021–24 only', 'Cualquier posición, solo 2021–24',
      pick(estimand='est_grd_rate', panel='panel_observed', activity='act_all', position='pos_any', covariates='cov_none', years='2021-2024'), BLUE, '^'),
     ('grd', 'Strict hospitalisation only, 2019–24', 'Solo hospitalización estricta, 2019–24',
      pick(estimand='est_grd_rate', panel='panel_observed', activity='act_hospitalisation', position='pos_any', covariates='cov_none', years='2019-2024'), BLUE, 'v'),
     ('grd', 'Principal diagnosis, 2019–24', 'Diagnóstico principal, 2019–24',
      pick(estimand='est_grd_rate', panel='panel_observed', activity='act_all', position='pos_principal', covariates='cov_none', years='2019-2024'), ORANGE, 'o'),
     ('pop', 'GRD episodes per resident, both sexes, 2019–24', 'Episodios GRD por residente, ambos sexos, 2019–24',
      pick(estimand='est_grd_pop', sex='TOTAL', covariates='cov_age', years='2019-2024', position='pos_any') if False else None, BLUE, 'o'),
    ]
    # population models: locate by model_id pattern to avoid ambiguity
    def by_id(sub):
        z = m[m.model_id.str.contains(sub, regex=False)]
        assert len(z) == 1, (sub, z.model_id.tolist()); r = z.iloc[0]
        return float(r.apc), float(r.apc_lo), float(r.apc_hi), int(r.df_resid)
    rows = [r for r in rows if r[3] is not None]
    pop_ids = m[m.estimand == 'est_grd_pop'].model_id.tolist()
    def pop(sex):
        z = m[(m.estimand == 'est_grd_pop') & (m.sex == sex) & (m.covariates == 'cov_age') & (m.years == '2019-2024')]
        z = z[z.model_id.str.contains('any')] if len(z) > 1 else z
        assert len(z) == 1, (sex, z.model_id.tolist()); r = z.iloc[0]
        return float(r.apc), float(r.apc_lo), float(r.apc_hi), int(r.df_resid)
    rows += [
     ('pop', 'GRD episodes per resident, males, 2019–24', 'Episodios GRD por residente, hombres, 2019–24', pop('HOMBRE'), BLUE, 'o'),
     ('pop', 'GRD episodes per resident, females, 2019–24', 'Episodios GRD por residente, mujeres, 2019–24', pop('MUJER'), BLUE, 's'),
     ('pop', 'DEIS discharges, principal diagnosis, 2019–24', 'Egresos DEIS, diagnóstico principal, 2019–24', by_id('deis_principal:sin_rett:none:2019-2024'), GREY, 'o'),
     ('rem', 'A05 entries per resident, males, 2021–25', 'Ingresos A05 por residente, hombres, 2021–25', by_id('a05_entry:sin_rett:HOMBRE:age_adjusted:2021-2025'), GREEN, 'o'),
     ('rem', 'A05 entries per resident, females, 2021–25', 'Ingresos A05 por residente, mujeres, 2021–25', by_id('a05_entry:sin_rett:MUJER:age_adjusted:2021-2025'), GREEN, 's'),
     ('rem', 'A05 entries, stable 258 establishments, 2021–25', 'Ingresos A05, 258 establecimientos estables, 2021–25', by_id('a05_entry:sin_rett:stable_pop:none:2021-2025'), GREEN, 'D'),
     ('rem', 'P6 under control, primary care, 2021–25', 'P6 en control, atención primaria, 2021–25', by_id('p6_primary:sin_rett:none:2021-2025'), PINK, 'o'),
     ('rem', 'P6 under control, specialty care, 2021–25', 'P6 en control, especialidad, 2021–25', by_id('p6_specialty:sin_rett:none:2021-2025'), PINK, 's'),
    ]
    return rows

def load_age_rates(source, y0, y1):
    """Combine the verified sex-specific age tables of revision 09 into both-sex rates per 100 000 residents."""
    out = {}
    for y in (y0, y1):
        h = pd.read_csv(DATA/f'{source}_age_hombre_{y}.csv'); m = pd.read_csv(DATA/f'{source}_age_mujer_{y}.csv')
        z = h[['age_group', 'count', 'population']].merge(m[['age_group', 'count', 'population']], on='age_group', suffixes=('_h', '_m'))
        z['count'] = z.count_h + z.count_m; z['pop'] = z.population_h + z.population_m
        z['rate'] = z['count'] / z['pop'] * 1e5
        from scipy import stats
        z['lo'] = stats.chi2.ppf(0.025, 2 * z['count']) / 2 / z['pop'] * 1e5
        z['hi'] = stats.chi2.ppf(0.975, 2 * (z['count'] + 1)) / 2 / z['pop'] * 1e5
        out[y] = z.set_index('age_group')
    return out

# ----------------------------------------------------------------------------- figure 1
F8X_LABELS = {'F80': ('F80 speech/language', 'F80 habla/lenguaje'), 'F81': ('F81 scholastic', 'F81 aprendizaje'),
              'F82': ('F82 motor', 'F82 motriz'), 'F83': ('F83 mixed', 'F83 mixtos'),
              'F84': ('F84 eligible codes', 'F84 códigos elegibles'), 'F88': ('F88 other', 'F88 otros'),
              'F89': ('F89 unspecified', 'F89 inespecífico')}
SHORT = {  # short forest labels (group, en, es)
 'Any position, observed panel, 2019–24': ('Any position, observed panel', 'Cualquier posición, panel observado'),
 'Any position, stable 65 hospitals, 2019–24': ('Stable panel, 65 hospitals', 'Panel estable, 65 hospitales'),
 'Any position, adjusted for coding depth, 2019–24': ('Adjusted for coding depth', 'Ajustado por profundidad'),
 'Any position, 2021–24 only': ('2021–24 only', 'Solo 2021–24'),
 'Strict hospitalisation only, 2019–24': ('Strict hospitalisation only', 'Solo hospitalización estricta'),
 'Principal diagnosis, 2019–24': ('Principal diagnosis', 'Diagnóstico principal'),
 'GRD episodes per resident, males, 2019–24': ('GRD episodes, males', 'Episodios GRD, hombres'),
 'GRD episodes per resident, females, 2019–24': ('GRD episodes, females', 'Episodios GRD, mujeres'),
 'DEIS discharges, principal diagnosis, 2019–24': ('DEIS discharges, principal', 'Egresos DEIS, principal'),
 'A05 entries per resident, males, 2021–25': ('A05 entries, males', 'Ingresos A05, hombres'),
 'A05 entries per resident, females, 2021–25': ('A05 entries, females', 'Ingresos A05, mujeres'),
 'A05 entries, stable 258 establishments, 2021–25': ('A05 entries, stable panel (258)', 'Ingresos A05, panel estable (258)'),
 'P6 under control, primary care, 2021–25': ('P6 under control, primary care', 'P6 en control, atención primaria'),
 'P6 under control, specialty care, 2021–25': ('P6 under control, specialty care', 'P6 en control, especialidad')}

def fig1(lang):
    style(); fig = plt.figure(figsize=(175/25.4, 215/25.4))
    top = fig.add_gridspec(1, 2, left=0.115, right=0.985, top=0.97, bottom=0.735, wspace=0.42)
    mid = fig.add_gridspec(1, 2, left=0.30, right=0.985, top=0.645, bottom=0.40, wspace=0.40, width_ratios=[1, 1.12])
    bot = fig.add_gridspec(1, 2, left=0.115, right=0.985, top=0.315, bottom=0.085, wspace=0.42)
    g = load_grd_summary()
    obs = g.query("panel=='observed' and position=='any'").set_index('year').reindex(YRS_GRD)
    fix = g.query("panel=='fixed65' and position=='any'").set_index('year').reindex(YRS_GRD)
    pri = g.query("panel=='observed' and position=='principal'").set_index('year').reindex(YRS_GRD)
    # (a) primary indicator per 100 000 GRD episodes
    a = fig.add_subplot(top[0, 0]); clean(a); shade_pandemic(a)
    for z, col, mk, ls, lab in [(obs, BLUE, 'o', '-', text('Any position, observed panel', 'Cualquier posición, observados', lang)),
                                (fix, BLACK, 's', '--', text('Any position, stable 65 hospitals', 'Cualquier posición, 65 estables', lang)),
                                (pri, ORANGE, 'D', '-', text('Principal diagnosis', 'Diagnóstico principal', lang))]:
        a.fill_between(z.index, z.rate_lo, z.rate_hi, color=col, alpha=0.15, lw=0)
        a.plot(z.index, z.rate_per_100k_episodes, color=col, marker=mk, ls=ls, label=lab, mfc='white' if mk == 's' else col, ms=3.2)
    log_axis(a, 'y', lang); a.set_ylim(10, 2500); year_ticks(a, YRS_GRD, short=True)
    a.set_ylabel(text('Eligible episodes per 100 000\nGRD episodes (log scale)', 'Episodios elegibles por 100 000\nepisodios GRD (escala log)', lang))
    a.legend(loc='upper left', handlelength=1.6, borderaxespad=0.2)
    end_label(a, 2024, obs.rate_per_100k_episodes[2024], num(obs.rate_per_100k_episodes[2024], lang, 1), BLUE, dy=-8)
    end_label(a, 2024, pri.rate_per_100k_episodes[2024], num(pri.rate_per_100k_episodes[2024], lang, 1), ORANGE, dy=-6)
    a.set_xlim(2018.6, 2024.9)
    # (b) age-standardised indicators per 100 000 residents by source
    b = fig.add_subplot(top[0, 1]); clean(b); shade_pandemic(b)
    pr = pd.read_csv(TIDY/'models_population_rates.csv').query("variant=='sin_rett' and position=='any' and sex=='TOTAL'").set_index('year').reindex(YRS_GRD)
    a05 = pd.read_csv(DATA/'models_a05_standardised_rates.csv').query("variant=='strict_autism' and sex=='TOTAL'").set_index('year').reindex(YRS_REM)
    b.fill_between(pr.index, pr.asr_lo, pr.asr_hi, color=BLUE, alpha=0.15, lw=0)
    b.plot(pr.index, pr.asr, color=BLUE, marker='o', label=text('GRD eligible episodes, any position', 'Episodios GRD elegibles, cualquier posición', lang))
    b.fill_between(a05.index, a05.asr_lo, a05.asr_hi, color=GREEN, alpha=0.15, lw=0)
    b.plot(a05.index, a05.asr, color=GREEN, marker='^', label=text('A05 strict-autism programme entries', 'Ingresos A05 por autismo estricto', lang))
    law_line(b, lang, y=0.22)
    b.set_ylim(0, 120); b.set_xlim(2018.6, 2025.6); year_ticks(b, range(2019, 2026), short=True)
    b.set_ylabel(text('Records per 100 000 residents,\nWHO age-standardised', 'Registros por 100 000 residentes,\nestandarizados por edad (OMS)', lang))
    b.legend(loc='upper left', handlelength=1.6, borderaxespad=0.2)
    end_label(b, 2024, pr.asr[2024], num(pr.asr[2024], lang, 1), BLUE, dy=-7)
    end_label(b, 2025, a05.asr[2025], num(a05.asr[2025], lang, 1), GREEN, dy=6, ha='right', dx=-2)
    # (c) annual percent change forest (half width, short labels)
    c = fig.add_subplot(mid[0, 0]); clean(c, grid='x')
    rows = load_forest(); groups = {'grd': text('Per 100 000 GRD episodes', 'Por 100 000 episodios GRD', lang),
                                    'pop': text('Per 100 000 residents, age-adjusted', 'Por 100 000 residentes, ajustado por edad', lang),
                                    'rem': text('REM programmes, 2021–25', 'Programas REM, 2021–25', lang)}
    y = 0.0; ticks = []; labels = []; last = None
    for grp, en, es, (apc, lo, hi, df), col, mk in rows:
        if grp != last:
            y += 0.6; c.text(-0.98, y, groups[grp], transform=c.get_yaxis_transform(), fontsize=6.9, fontweight='bold', va='center', ha='left', color='#333333', clip_on=False); y += 1.0; last = grp
        c.errorbar(apc, y, xerr=[[apc - lo], [hi - apc]], fmt=mk, color=col, ms=3.6, capsize=1.6, lw=0.85, mfc=col if mk in 'oD^v' else 'white')
        ticks.append(y); labels.append(text(*SHORT[en], lang)); y += 1.0
    c.set_yticks(ticks); c.set_yticklabels(labels, fontsize=6.8); c.set_ylim(y - 0.4, -0.2); c.invert_yaxis() if False else None
    c.axvline(0, color='#555555', lw=0.7, ls=':'); c.set_xlim(-5, 70); c.set_xticks([0, 20, 40, 60])
    c.set_xlabel(text('Annual percent change (95% CI)', 'Cambio porcentual anual (IC 95%)', lang))
    c.tick_params(axis='y', length=0)
    # (d) F80–F89 block comparator, per 100 000 GRD episodes
    d = fig.add_subplot(mid[0, 1]); clean(d); shade_pandemic(d)
    f8 = pd.read_csv(DATA/'f80_f89_episode_rates.csv')
    panel = 'observed' if (f8.panel == 'observed').any() else 'fixed65'; f8 = f8[f8.panel == panel]
    # The block tabulation counts the whole F84 family (with F84.2); the eligible F84 line is drawn
    # from the sin_rett series of grd_year_summary on the same observed panel and denominator.
    tot = f8.query("category=='F84' and year==2024").n_episodes_total.iloc[0]
    assert panel == 'observed' and int(tot) == int(obs.n_episodes_total_same_panel_activity[2024]), (panel, tot)
    order = ['F84', 'F80', 'F83', 'F82', 'F81', 'F89', 'F88']
    cols = {'F84': BLUE, 'F80': GREEN, 'F83': SKY, 'F82': GOLD, 'F81': PINK, 'F89': GREY, 'F88': '#8c6d31'}
    mks = {'F84': 'o', 'F80': 's', 'F83': 'D', 'F82': 'v', 'F81': '^', 'F89': 'x', 'F88': 'P'}
    for cat in order:
        z = f8[f8.category == cat].set_index('year').reindex(YRS_GRD)
        if cat == 'F84': z = obs
        d.plot(z.index, z.rate_per_100k_episodes, color=cols[cat], marker=mks[cat], ls='-' if cat == 'F84' else '--', lw=1.4 if cat == 'F84' else 1.0, ms=3.2, label=text(*F8X_LABELS[cat], lang))
    log_axis(d, 'y', lang); d.set_ylim(1, 2000); d.set_xlim(2018.6, 2024.6); year_ticks(d, YRS_GRD, short=True)
    d.set_ylabel(text('Episodes per 100 000 GRD\nepisodes (log scale)', 'Episodios por 100 000\nepisodios GRD (escala log)', lang)); d.set_ylim(1, 5000)
    d.legend(loc='upper left', ncol=2, handlelength=1.4, columnspacing=0.7, handletextpad=0.4, borderaxespad=0.15, fontsize=6.4)
    # (e) male:female ratio
    e = fig.add_subplot(bot[0, 0]); clean(e)
    sr = pd.read_csv(DATA/'fig3d_sex_ratios.csv')
    for src, col, mk, lab in [('GRD', BLUE, 'o', text('GRD eligible episodes', 'Episodios GRD elegibles', lang)), ('A05', GREEN, '^', text('A05 strict-autism entries', 'Ingresos A05 autismo estricto', lang))]:
        z = sr[sr.source == src].sort_values('year')
        e.fill_between(z.year, z.ratio_lo, z.ratio_hi, color=col, alpha=0.15, lw=0)
        e.plot(z.year, z.male_female_count_ratio, color=col, marker=mk, label=lab)
        end_label(e, z.year.iloc[-1], z.male_female_count_ratio.iloc[-1], num(z.male_female_count_ratio.iloc[-1], lang, 2), col, dy=(-8 if src == 'GRD' else -7))
        end_label(e, z.year.iloc[0], z.male_female_count_ratio.iloc[0], num(z.male_female_count_ratio.iloc[0], lang, 2), col, dx=(4 if src == 'GRD' else 0), dy=(8 if src == 'GRD' else 9), ha=('left' if src == 'GRD' else 'center'))
    shade_pandemic(e); law_line(e, lang, y=0.20)
    e.set_ylim(1, 4.3); e.set_xlim(2018.6, 2025.5); year_ticks(e, range(2019, 2026), short=True)
    e.set_ylabel(text('Male:female ratio of records\n(95% CI)', 'Razón hombre:mujer de los\nregistros (IC 95%)', lang))
    e.legend(loc='lower left', handlelength=1.6, borderaxespad=0.2)
    # (f) age-specific GRD rates, 2019 vs 2024, both sexes
    f = fig.add_subplot(bot[0, 1]); clean(f, grid='x')
    ar = load_age_rates('grd', 2019, 2024); groups_age = list(ar[2019].index); ypos = np.arange(len(groups_age))
    for i, gname in enumerate(groups_age):
        r0, r1 = ar[2019].loc[gname], ar[2024].loc[gname]
        f.plot([r0.rate, r1.rate], [i, i], color=LIGHT, lw=1.2, zorder=1)
        pct = (r1.rate / r0.rate - 1) * 100
        f.text(max(r0.rate, r1.rate) * 1.4, i, ('+' if pct >= 0 else '−') + num(abs(pct), lang, 0) + ' %', va='center', fontsize=6.6, color=ORANGE if pct >= 0 else BLUE)
    f.scatter(ar[2019].rate, ypos, s=18, facecolors='white', edgecolors=BLUE, linewidths=1.1, zorder=3, label='2019')
    f.scatter(ar[2024].rate, ypos, s=18, color=ORANGE, marker='s', zorder=3, label='2024')
    log_axis(f, 'x', lang); f.set_xlim(0.3, 4000); f.set_yticks(ypos); f.set_yticklabels([s.replace('-', '–') for s in groups_age]); f.invert_yaxis()
    f.set_xlabel(text('Eligible episodes per\n100 000 residents (log scale)', 'Episodios elegibles por\n100 000 residentes (escala log)', lang))
    f.set_ylabel(text('Age group (years)', 'Grupo de edad (años)', lang))
    f.legend(loc='lower right', handlelength=1.2, borderaxespad=0.2)
    for ax, ch in zip([a, b, c, d, e, f], 'abcdef'): letter(fig, ax, ch, dx=(-0.27 if ch == 'c' else -0.075))
    save(fig, 'Figure_1', lang)


# ----------------------------------------------------------------------------- figure 2
ICD_EN = {'G40': 'Epilepsy (G40)', 'Z51': 'Other medical care (Z51)', 'N47': 'Phimosis, redundant prepuce (N47)', 'K35': 'Acute appendicitis (K35)',
          'J35': 'Tonsil and adenoid disease (J35)', 'J12': 'Viral pneumonia (J12)', 'T43': 'Psychotropic drug poisoning (T43)',
          'F32': 'Depressive episode (F32)', 'J46': 'Status asthmaticus (J46)', 'F60': 'Personality disorders (F60)'}
ICD_ES = {'G40': 'Epilepsia (G40)', 'Z51': 'Otra atención médica (Z51)', 'N47': 'Fimosis, prepucio redundante (N47)', 'K35': 'Apendicitis aguda (K35)',
          'J35': 'Enf. amígdalas y adenoides (J35)', 'J12': 'Neumonía viral (J12)', 'T43': 'Intoxicación psicotrópicos (T43)',
          'F32': 'Episodio depresivo (F32)', 'J46': 'Estado asmático (J46)', 'F60': 'Trastornos de la personalidad (F60)'}
SUB_LABELS = {'F840': ('F84.0 childhood autism', 'F84.0 autismo infantil'), 'F841': ('F84.1 atypical autism', 'F84.1 autismo atípico'),
              'F845': ('F84.5 Asperger', 'F84.5 Asperger'), 'F848': ('F84.8 other', 'F84.8 otros'),
              'F849': ('F84.9 unspecified', 'F84.9 inespecífico'), 'Other': ('F84.3, F84.4', 'F84.3, F84.4')}

def fig2(lang):
    style(); fig = plt.figure(figsize=(175/25.4, 215/25.4))
    gs = fig.add_gridspec(3, 2, left=0.10, right=0.975, top=0.965, bottom=0.06, hspace=0.55, wspace=0.55, height_ratios=[1, 1, 0.9])
    top_a = fig.add_gridspec(1, 1, left=0.10, right=0.395, top=0.965, bottom=0.715)
    top_b = fig.add_gridspec(1, 1, left=0.735, right=0.975, top=0.965, bottom=0.715)
    g = load_grd_summary()
    obs = g.query("panel=='observed' and position=='any'").set_index('year').reindex(YRS_GRD)
    pri = g.query("panel=='observed' and position=='principal'").set_index('year').reindex(YRS_GRD)
    sec = g.query("panel=='observed' and position=='secondary_only'").set_index('year').reindex(YRS_GRD)
    # (a) diagnostic position of the eligible code
    a = fig.add_subplot(top_a[0, 0]); clean(a); shade_pandemic(a)
    a.bar(YRS_GRD, sec.n_episodes_f84, color=BLUE, width=0.7, label=text('Eligible code only in a secondary position', 'Código elegible solo en posición secundaria', lang), zorder=2)
    a.bar(YRS_GRD, pri.n_episodes_f84, bottom=sec.n_episodes_f84, color=ORANGE, width=0.7, label=text('Eligible code as principal diagnosis', 'Código elegible como diagnóstico principal', lang), zorder=2)
    a.yaxis.set_major_formatter(thousands(lang)); a.set_ylim(0, 14000); year_ticks(a, YRS_GRD, short=True)
    a.set_ylabel(text('Eligible episodes (n)', 'Episodios elegibles (n)', lang))
    a2 = a.twinx(); a2.grid(False); a2.spines['top'].set_visible(False)
    pct = sec.n_episodes_f84 / obs.n_episodes_f84 * 100
    a2.plot(YRS_GRD, pct, color=BLACK, marker='o', ms=3, lw=1.1, zorder=3, label=text('% secondary only (right axis)', '% solo secundaria (eje derecho)', lang))
    for yv, pv in zip(YRS_GRD, pct):
        a2.annotate(num(pv, lang, 1), (yv, pv), xytext=(0, 5), textcoords='offset points', ha='center', fontsize=6.4, color=BLACK)
    a2.set_ylim(60, 100); a2.set_yticks([60, 70, 80, 90, 100]); a2.set_ylabel(text('Secondary position only (%)', 'Solo posición secundaria (%)', lang), fontsize=7.2, labelpad=2)
    h1, l1 = a.get_legend_handles_labels(); h2, l2 = a2.get_legend_handles_labels()
    a.legend(h1 + h2, l1 + l2, loc='upper center', bbox_to_anchor=(0.5, -0.16), fontsize=6.5, handlelength=1.4, borderaxespad=0.0)
    for yv in [2019, 2024]:
        a.annotate(num(obs.n_episodes_f84[yv], lang, 0), (yv, obs.n_episodes_f84[yv]), xytext=(0, 3), textcoords='offset points', ha='center', fontsize=6.6, color=BLUE, fontweight='bold')
    # (b) principal diagnosis when the eligible code is secondary only, 2019 vs 2024
    b = fig.add_subplot(top_b[0, 0]); clean(b, grid='x')
    cp = pd.read_csv(DATA/'clinical_principal_selected.csv')
    order = cp[cp.year == 2024].sort_values('pct_of_f84_episodes', ascending=False).code3.tolist()
    ypos = np.arange(len(order))
    for i, code in enumerate(order):
        v0 = cp[(cp.code3 == code) & (cp.year == 2019)].pct_of_f84_episodes; v1 = cp[(cp.code3 == code) & (cp.year == 2024)].pct_of_f84_episodes
        v0 = float(v0.iloc[0]) if len(v0) else np.nan; v1 = float(v1.iloc[0]) if len(v1) else np.nan
        b.plot([v0, v1], [i, i], color=LIGHT, lw=1.2, zorder=1)
        b.scatter([v0], [i], s=18, facecolors='white', edgecolors=BLUE, linewidths=1.1, zorder=3)
        b.scatter([v1], [i], s=18, color=ORANGE, marker='s', zorder=3)
    n19 = int(cp[cp.year == 2019].n_f84_episodes_cell.iloc[0]); n24 = int(cp[cp.year == 2024].n_f84_episodes_cell.iloc[0])
    b.scatter([], [], s=18, facecolors='white', edgecolors=BLUE, linewidths=1.1, label=f'2019 (n={num(n19, lang)})')
    b.scatter([], [], s=18, color=ORANGE, marker='s', label=f'2024 (n={num(n24, lang)})')
    b.set_yticks(ypos); b.set_yticklabels([(ICD_EN if lang == 'en' else ICD_ES)[c] for c in order], fontsize=6.6); b.invert_yaxis()
    b.set_xlim(0, 8.5); b.set_xlabel(text('Secondary-only episodes (%)', 'Episodios solo secundarios (%)', lang))
    b.legend(loc='lower right', fontsize=6.6, handlelength=1.2, borderaxespad=0.2)
    # (c) length of stay and case-mix weight
    c = fig.add_subplot(gs[1, 0]); clean(c); shade_pandemic(c)
    st = pd.read_csv(DATA/'burden_length_of_stay.csv')
    c.plot(st.year, st.eligible_mean_days, color=ORANGE, marker='s', label=text('Eligible episodes', 'Episodios elegibles', lang))
    c.plot(st.year, st.all_mean_days, color=GREY, marker='o', ls='--', label=text('All hospitalisation episodes', 'Todos los episodios de hospitalización', lang))
    for j in (0, len(st) - 1):
        c.annotate(num(st.eligible_mean_days.iloc[j], lang, 1), (st.year.iloc[j], st.eligible_mean_days.iloc[j]), xytext=(0, 13) if j == 0 else (0, 6), textcoords='offset points', ha='center', va='center' if j == 0 else 'baseline', fontsize=6.8, color=ORANGE, fontweight='bold')
    c.set_ylim(0, 15); year_ticks(c, YRS_GRD, short=True); c.set_ylabel(text('Mean length of stay (days)', 'Estancia media (días)', lang))
    c2 = c.twinx(); c2.grid(False); c2.spines['top'].set_visible(False)
    c2.plot(st.year, st.eligible_mean_grd_weight, color=GREEN, marker='^', ls=':', lw=1.1, ms=3.2, label=text('Mean GRD weight (right axis)', 'Peso GRD medio (eje derecho)', lang))
    c2.set_ylim(0.6, 1.05); c2.set_ylabel(text('Mean GRD relative weight', 'Peso relativo GRD medio', lang), color=GREEN, fontsize=7.5); c2.tick_params(axis='y', colors=GREEN)
    h1, l1 = c.get_legend_handles_labels(); h2, l2 = c2.get_legend_handles_labels()
    c.legend(h1 + h2, l1 + l2, loc='lower left', fontsize=6.5, handlelength=1.4, borderaxespad=0.2)
    # (d) readmission and repeat contact
    d = fig.add_subplot(gs[1, 1]); clean(d)
    rd = pd.read_csv(TIDY/'grd_readmission.csv').query("variant=='sin_rett' and position=='any' and panel=='observed'")
    r30 = rd[rd.horizon_days == 30].set_index('year').reindex(YRS_GRD); r90 = rd[rd.horizon_days == 90].set_index('year').reindex(YRS_GRD)
    d.fill_between(r30.index, r30.pct_any_cause_lo, r30.pct_any_cause_hi, color=BLUE, alpha=0.15, lw=0)
    d.plot(r30.index, r30.pct_any_cause, color=BLUE, marker='o', label=text('30 d, any cause', '30 d, cualquier causa', lang))
    d.plot(r30.index, r30.pct_f84, color=SKY, marker='D', ls='--', ms=3, label=text('30 d, eligible code', '30 d, código elegible', lang))
    d.fill_between(r90.index, r90.pct_any_cause_lo, r90.pct_any_cause_hi, color=PINK, alpha=0.15, lw=0)
    d.plot(r90.index, r90.pct_any_cause, color=PINK, marker='^', label=text('90 d, any cause', '90 d, cualquier causa', lang))
    d.axvline(2020.5, color=GREY, ls=':', lw=0.8)
    d.set_ylim(0, 56); year_ticks(d, YRS_GRD, short=True); d.set_ylabel(text('Readmitted after an eligible\ndischarge (%)', 'Reingreso tras un egreso\nelegible (%)', lang))
    d.set_xlabel(text('Year of index discharge', 'Año del egreso índice', lang))
    d.legend(loc='upper left', fontsize=6.0, handlelength=1.3, borderaxespad=0.2, ncol=1)
    ins = d.inset_axes([0.60, 0.585, 0.33, 0.40]); ins.grid(False); ins.yaxis.tick_right(); ins.yaxis.set_label_position('right')
    mu = pd.read_csv(DATA/'burden_multiplicity.csv'); x = np.arange(len(mu))
    ins.bar(x - 0.2, mu.pct_persons, width=0.38, color='#b9b9b9', label=text('People', 'Personas', lang))
    ins.bar(x + 0.2, mu.pct_episodes, width=0.38, color=BLUE, label=text('Episodes', 'Episodios', lang))
    ins.set_xticks(x); ins.set_xticklabels([str(v).replace('-', '–') for v in mu.episodes_per_identifier], fontsize=5.6)
    ins.set_yticks([0, 40, 80]); ins.tick_params(axis='y', labelsize=6.2); ins.set_ylim(0, 92)
    ins.set_xlabel(text('Episodes per person\n2021–24', 'Episodios por persona\n2021–24', lang), fontsize=6.2, labelpad=1)
    ins.set_ylabel('%', fontsize=6.2, labelpad=1); ins.legend(fontsize=5.8, loc='upper right', handlelength=1, borderpad=0.1, handletextpad=0.4)
    for sp in ('top', 'left'): ins.spines[sp].set_visible(False)
    # (e) composition of the eligible F84 subcodes
    e = fig.add_subplot(gs[2, :]); clean(e, grid=None)
    sc = pd.read_csv(DATA/'case_definition_subcodes.csv').set_index('year').reindex(YRS_GRD)
    keys = ['F840', 'F849', 'F845', 'F848', 'F841', 'Other']; cols = [BLUE, GREY, ORANGE, GOLD, SKY, PINK]
    bottom = np.zeros(len(YRS_GRD))
    for k, col in zip(keys, cols):
        vals = sc['pct_' + k].values
        e.bar(YRS_GRD, vals, bottom=bottom, color=col, width=0.72, label=text(*SUB_LABELS[k], lang), zorder=2)
        for xi, (v, b0) in enumerate(zip(vals, bottom)):
            if v >= 4.5: e.text(YRS_GRD[xi], b0 + v / 2, num(v, lang, 1) + ' %', ha='center', va='center', fontsize=6.4, color='white' if col in (BLUE, GREY, ORANGE) else '#222222').set_gid('inbar')
        bottom += vals
    e.set_ylim(0, 100); e.set_ylabel(text('Coded eligible\nsubcodes (%)', 'Subcódigos elegibles\ncodificados (%)', lang)); year_ticks(e, YRS_GRD)
    tot = (sc[['F840', 'F841', 'F845', 'F848', 'F849', 'Other']].sum(axis=1)).astype(int)
    for xi, yv in enumerate(YRS_GRD): e.text(yv, 101, 'n=' + num(int(tot[yv]), lang), ha='center', va='bottom', fontsize=6.4, color='#333333')
    e.legend(loc='center left', bbox_to_anchor=(1.005, 0.5), fontsize=6.8, handlelength=1.2, borderaxespad=0.0)
    e.set_xlim(2018.4, 2024.6)
    pos = e.get_position(); e.set_position([pos.x0, pos.y0, pos.width * 0.78, pos.height])
    for ax, ch in zip([a, b, c, d, e], 'abcde'): letter(fig, ax, ch, dx=(-0.245 if ch == 'b' else -0.075))
    save(fig, 'Figure_2', lang)

# ----------------------------------------------------------------------------- figure 3
A03_ROWS = [  # (code, en, es) in cascade order, M-CHAT-R/F era 2023–2024
 ('09600212', 'Suspected autism in other controls', 'Sospecha en otros controles'),
 ('09600213', 'M-CHAT-R/F first part: low risk', 'M-CHAT-R/F primera parte: riesgo bajo'),
 ('09600214', 'M-CHAT-R/F first part: medium risk', 'M-CHAT-R/F primera parte: riesgo medio'),
 ('09600215', 'M-CHAT-R/F first part: high risk', 'M-CHAT-R/F primera parte: riesgo alto'),
 ('09600216', 'High risk with specialist referral', 'Riesgo alto con derivación a especialista'),
 ('09600218', 'Second part: no referral required', 'Segunda parte: sin derivación'),
 ('09600219', 'Second part: referral required', 'Segunda parte: con derivación')]

def rem_series(code, variant='single_code', measure=None, module=None):
    r = pd.read_csv(TIDY/'rem_pathway_annual.csv', low_memory=False)
    z = r[(r.code.astype(str) == code) & (r.variant == variant)]
    if measure: z = z[z.measure == measure]
    if module: z = z[z.module == module]
    assert len(z) >= 1, (code, variant, measure)
    return z.sort_values('year').set_index('year')

def fig3(lang):
    style(); fig = plt.figure(figsize=(175/25.4, 172/25.4))
    gs = fig.add_gridspec(2, 2, left=0.10, right=0.925, top=0.965, bottom=0.075, hspace=0.42, wspace=0.55, width_ratios=[1.05, 1])
    # (a) screening cascade, M-CHAT-R/F era (axes shifted right to make room for the category labels)
    a = fig.add_subplot(gs[0, 0]); clean(a, grid='x')
    pos = a.get_position(); a.set_position([pos.x0 + 0.20, pos.y0, pos.width - 0.20, pos.height])
    r = pd.read_csv(TIDY/'rem_pathway_annual.csv', low_memory=False); r['code'] = r.code.astype(str)
    ypos = np.arange(len(A03_ROWS))
    for i, (code, en, es) in enumerate(A03_ROWS):
        z = r[(r.code == code) & (r.variant == 'single_code')].set_index('year')
        v23 = float(z.total.get(2023, np.nan)); v24 = float(z.total.get(2024, np.nan))
        a.plot([v23, v24], [i, i], color=LIGHT, lw=1.2, zorder=1)
        a.scatter([v23], [i], s=18, facecolors='white', edgecolors=BLUE, linewidths=1.1, zorder=3)
        a.scatter([v24], [i], s=18, color=BLUE, marker='s', zorder=3)
        a.text(max(v23, v24) * 1.35, i, num(v24, lang), va='center', fontsize=6.4, color=BLUE)
    a.scatter([], [], s=18, facecolors='white', edgecolors=BLUE, linewidths=1.1, label='2023'); a.scatter([], [], s=18, color=BLUE, marker='s', label='2024')
    a.set_yticks(ypos); a.set_yticklabels([text(en, es, lang) for _, en, es in A03_ROWS], fontsize=6.6); a.invert_yaxis()
    log_axis(a, 'x', lang); a.set_xlim(400, 60000); a.set_xticks([1000, 10000]); a.xaxis.set_major_formatter(thousands(lang))
    a.set_xlabel(text('Screening records, annual flow (log scale)', 'Registros de tamizaje, flujo anual (escala log)', lang), fontsize=7.4)
    a.legend(loc='upper left', fontsize=6.6, handlelength=1.2, borderaxespad=0.2)
    # (b) A05 programme entries and clinical discharges, with reporting establishments
    b = fig.add_subplot(gs[0, 1]); clean(b); shade_pandemic(b)
    ent = rem_series('05990022'); dis = rem_series('05990027'); bent = rem_series('06902600'); bdis = rem_series('05225000')
    assert int(ent.total[2021]) == 2085 and int(ent.total[2025]) == 13155, ent.total.tolist()
    b2 = b.twinx(); b2.grid(False); b2.spines['top'].set_visible(False)
    for p_ in b2.bar(ent.index, ent.n_reporting_establishments, color='#dddddd', width=0.6, zorder=0): p_.set_gid('bg')
    b2.set_ylim(0, 3200); b2.set_ylabel(text('Reporting establishments (bars, n)', 'Establecimientos informantes (barras, n)', lang), fontsize=7.5, color='#555555'); b2.tick_params(axis='y', colors='#555555')
    b.set_zorder(b2.get_zorder() + 1); b.patch.set_visible(False)
    b.plot(bent.index, bent.total, color=GREY, marker='o', ls='-', ms=3, label=text('Broad PDD entries, 2019–20', 'Ingresos TGD amplio, 2019–20', lang))
    b.plot(bdis.index, bdis.total, color=GREY, marker='s', ls='--', ms=3, label=text('Broad PDD discharges, 2019–20', 'Egresos TGD amplio, 2019–20', lang))
    b.plot(ent.index, ent.total, color=GREEN, marker='^', label=text('Strict-autism entries', 'Ingresos por autismo estricto', lang))
    b.plot(dis.index, dis.total, color=GREEN, marker='v', ls='--', mfc='white', label=text('Strict-autism clinical discharges', 'Altas clínicas por autismo estricto', lang))
    end_label(b, 2025, ent.total[2025], num(ent.total[2025], lang), GREEN, dx=-2, dy=9, ha='right')
    end_label(b, 2025, dis.total[2025], num(dis.total[2025], lang), GREEN, dx=-2, dy=-7, ha='right')
    law_line(b, lang, y=0.42)
    b.set_ylim(0, 18000); b.yaxis.set_major_formatter(thousands(lang)); b.set_xlim(2018.6, 2025.5); year_ticks(b, range(2019, 2026), short=True)
    b.set_ylabel(text('Records, annual flow (n)', 'Registros, flujo anual (n)', lang))
    h1, l1 = b.get_legend_handles_labels(); h2, l2 = b2.get_legend_handles_labels()
    b.legend(h1 + h2, l1 + l2, loc='upper left', fontsize=6.2, handlelength=1.3, borderaxespad=0.2, labelspacing=0.3)
    # (c) people under control in December, P6, by level of care
    c = fig.add_subplot(gs[1, 0]); clean(c); shade_pandemic(c)
    pp = rem_series('P6241010', measure='december_stock'); ps = rem_series('P6241060', measure='december_stock')
    fp = rem_series('P6241010+P6241020+P6241040+P6241050', variant='sin_rett', measure='december_stock'); fs = rem_series('P6241060+P6241070+P6241090+P6241100', variant='sin_rett', measure='december_stock')
    bp = rem_series('P6223000', measure='december_stock'); bs = rem_series('P6223380', measure='december_stock')
    c.plot(bp.index, bp.total, color=GREY, marker='o', ms=3, label=text('Primary care, broad PDD, 2019–20', 'APS, TGD amplio, 2019–20', lang))
    c.plot(bs.index, bs.total, color=GREY, marker='s', ms=3, ls='--', label=text('Specialty care, broad PDD, 2019–20', 'Especialidad, TGD amplio, 2019–20', lang))
    c.plot(fp.index, fp.total, color=GOLD, marker='D', ms=2.8, ls=':', lw=1.0, label=text('Primary care, F84 family', 'APS, familia F84', lang))
    c.plot(fs.index, fs.total, color=SKY, marker='D', ms=2.8, ls=':', lw=1.0, label=text('Specialty care, F84 family', 'Especialidad, familia F84', lang))
    c.plot(pp.index, pp.total, color=ORANGE, marker='o', label=text('Primary care, strict autism', 'APS, autismo estricto', lang))
    c.plot(ps.index, ps.total, color=BLUE, marker='s', label=text('Specialty care, strict autism', 'Especialidad, autismo estricto', lang))
    end_label(c, 2025, pp.total[2025], num(pp.total[2025], lang), ORANGE, dx=4)
    end_label(c, 2025, ps.total[2025], num(ps.total[2025], lang), BLUE, dx=4)
    law_line(c, lang, y=0.16)
    c.set_ylim(0, 32000); c.yaxis.set_major_formatter(thousands(lang)); c.set_xlim(2018.6, 2025.5); year_ticks(c, range(2019, 2026), short=True)
    c.set_ylabel(text('People under control in December (n)', 'Personas en control en diciembre (n)', lang))
    c.legend(loc='upper left', fontsize=6.2, handlelength=1.3, borderaxespad=0.2, labelspacing=0.3)
    # (d) counselling, assisted referral and rehabilitation entries, 2023–2025
    d = fig.add_subplot(gs[1, 1]); clean(d)
    items = [('29101566', 'Counselling (M-CHAT-R/F context)', 'Consejería (contexto M-CHAT-R/F)', SKY),
             ('29101574', 'Assisted referral', 'Derivación asistida', BLUE),
             ('29101629', 'Rehabilitation entry, primary level', 'Ingreso a rehabilitación, nivel primario', GREEN),
             ('29101651', 'Rehabilitation entry, hospital level', 'Ingreso a rehabilitación, nivel hospitalario', PINK)]
    yrs = [2023, 2024, 2025]; w = 0.2
    for j, (code, en, es, col) in enumerate(items):
        z = rem_series(code).reindex(yrs)
        xs = np.array(yrs) + (j - 1.5) * w
        d.bar(xs, z.total, width=w, color=col, label=text(en, es, lang), zorder=2)
        for x, v, n in zip(xs, z.total, z.n_reporting_establishments):
            d.text(x, v + 250, num(v, lang), ha='center', va='bottom', fontsize=5.8, color='#222222', rotation=90)
    d.set_xticks(yrs); d.set_ylim(0, 26000); d.yaxis.set_major_formatter(thousands(lang))
    d.set_ylabel(text('Records, annual flow (n)', 'Registros, flujo anual (n)', lang))
    d.legend(loc='upper left', fontsize=6.2, handlelength=1.2, borderaxespad=0.2, labelspacing=0.3)
    for ax, ch in zip([a, b, c, d], 'abcd'): letter(fig, ax, ch, dx=(-0.275 if ch == 'a' else -0.075))
    save(fig, 'Figure_3', lang)

# ----------------------------------------------------------------------------- figure 4
def fig4(lang):
    style(); fig = plt.figure(figsize=(175/25.4, 172/25.4))
    gs = fig.add_gridspec(2, 2, left=0.105, right=0.975, top=0.965, bottom=0.095, hspace=0.45, wspace=0.42)
    # (a) educational registrations
    a = fig.add_subplot(gs[0, 0]); clean(a); shade_pandemic(a)
    pie = pd.read_csv(TIDY/'education_summary_year.csv').set_index('year')   # same series as fig3a_pie.csv, plus special schools
    a.plot(pie.index, pie.pie_tea_strict_n, color=BLUE, marker='s', ls='--', ms=3, label=text('PIE, autism category (Apuntes 60)', 'PIE, categoría autismo (Apuntes 60)', lang))
    a.plot(pie.index, pie.pie_tea_asperger_n, color=ORANGE, marker='^', ls='--', ms=3, label=text('PIE, Asperger category (Apuntes 60)', 'PIE, categoría Asperger (Apuntes 60)', lang))
    a.plot(pie.index, pie.pie_harmonised_n, color=SKY, marker='o', lw=1.6, label=text('Harmonised autism registrations', 'Registros armonizados de autismo', lang))
    sin = pie.pie_harmonised_sinaces_n.dropna()
    a.plot(sin.index, sin.values, color=BLACK, marker='x', ls='none', ms=5, mew=1.2, label=text('As printed by SINACES', 'Según SINACES', lang))
    a.plot(pie.index, pie.special_schools_autism_n, color=PINK, marker='v', ms=3, label=text('Special schools, autism', 'Escuelas especiales, autismo', lang))
    for yv in [2019, 2021, 2023, 2025]:
        v = pie.pie_harmonised_n[yv]; a.annotate(num(v, lang), (yv, v), xytext=((4, 7) if yv == 2019 else ((0, 6) if yv == 2025 else (-2, 5))), textcoords='offset points', ha=('left' if yv == 2019 else ('center' if yv == 2025 else 'right')), fontsize=6.4, color=SKY, fontweight='bold')
    law_line(a, lang, y=0.30)
    a.set_ylim(0, 125000); a.yaxis.set_major_formatter(thousands(lang)); a.set_xlim(2018.6, 2025.5); year_ticks(a, range(2019, 2026), short=True)
    a.set_ylabel(text('Students (annual school stock)', 'Estudiantes (stock escolar anual)', lang))
    a.legend(loc='upper left', fontsize=6.2, handlelength=1.4, borderaxespad=0.2, labelspacing=0.3)
    # (b) relative change across systems, 2021 = 100
    b = fig.add_subplot(gs[0, 1]); clean(b); shade_pandemic(b)
    ci = pd.read_csv(TIDY/'models_convergence_index.csv').query("variant=='sin_rett' and index_base_year==2021")
    series = [('grd_any_rate', 'GRD episode indicator', 'Indicador de episodios GRD', BLUE, 'o', '-'),
              ('deis_principal_rate', 'DEIS principal-diagnosis rate', 'Tasa DEIS diagnóstico principal', GREY, 'D', '-'),
              ('a05_strict_entries', 'A05 strict-autism entries', 'Ingresos A05 autismo estricto', GREEN, '^', '-'),
              ('p2_december_stock', 'P2 December stock', 'Stock P2 de diciembre', PINK, 's', '-'),
              ('p6_primary_strict_stock', 'P6 primary care, December stock', 'P6 APS, stock de diciembre', GOLD, 'v', '-'),
              ('pie_harmonised', 'PIE harmonised registrations', 'Registros PIE armonizados', SKY, 'o', '-')]
    for key, en, es, col, mk, ls in series:
        z = ci[ci.series == key].set_index('year').sort_index()
        pre = z[z.index <= 2021]; post = z[z.index >= 2021]
        if len(pre) > 1: b.plot(pre.index, pre['index'], color=col, marker=mk, ls=':', ms=3, lw=1)
        b.plot(post.index, post['index'], color=col, marker=mk, ls=ls, ms=3.2, label=text(en, es, lang))
        end_label(b, post.index[-1], post['index'].iloc[-1], num(post['index'].iloc[-1], lang), col, dx=3, dy=(-4 if key == 'grd_any_rate' else 0), size=6.2)
    b.axhline(100, color='#8c8c8c', lw=0.6, ls=':'); law_line(b, lang, y=0.12)
    log_axis(b, 'y', lang); b.set_ylim(40, 6000); b.set_xlim(2018.6, 2026.2); year_ticks(b, range(2019, 2026), short=True)
    b.set_ylabel(text('Index, 2021 = 100 (log scale)', 'Índice, 2021 = 100 (escala log)', lang))
    b.legend(loc='upper left', fontsize=6.2, handlelength=1.4, borderaxespad=0.2, labelspacing=0.3)
    # (c) population surveys
    c = fig.add_subplot(gs[1, 0]); clean(c, grid='x')
    pos = c.get_position(); c.set_position([pos.x0 + 0.10, pos.y0, pos.width - 0.10, pos.height])
    sv = pd.read_csv(TIDY/'survey_estimates.csv').query("estimate_type=='primary' and subgroup_type in ('total','sex')")
    blocks = [('ENDIDE adultos 18+: autismo reportado', 'ENDIDE 2022, adults 18+, reported', 'ENDIDE 2022, adultos 18+, reportado', BLUE),
              ('ENDIDE NNA 2-17: autismo reportado', 'ENDIDE 2022, ages 2–17, reported', 'ENDIDE 2022, 2–17 años, reportado', GREEN),
              ('ENDIDE NNA 2-17: autismo reportado y confirmado por un médico', 'ENDIDE 2022, ages 2–17, confirmed', 'ENDIDE 2022, 2–17 años, confirmado', PINK),
              ('ENCAVI 15+: diagnóstico de trastorno del espectro autista', 'ENCAVI 2023–24, ages 15+, diagnosed', 'ENCAVI 2023–24, 15+ años, diagnóstico', ORANGE)]
    sub_lab = {'total': text('Total', 'Total', lang), 'Hombre': text('Males', 'Hombres', lang), 'Mujer': text('Females', 'Mujeres', lang)}
    y = 0; ticks = []; labels = []
    for dom, en, es, col in blocks:
        c.text(0.04, y, text(en, es, lang), fontsize=6.6, fontweight='bold', color=col, va='center', ha='left', transform=c.get_yaxis_transform()); y += 1
        for sub in ['total', 'Hombre', 'Mujer']:
            r = sv[(sv.domain == dom) & (sv.subgroup == sub)].iloc[0]
            est, lo, hi = r.proportion * 100, r.lo * 100, r.hi * 100
            imp = str(r.precision_flag) != 'adequate'
            c.errorbar(est, y, xerr=[[est - lo], [hi - est]], fmt='o', color=LIGHT if imp else col, ms=3.4, capsize=1.6, lw=0.9)
            c.text(hi * 1.15, y, f'{num(est, lang, 2)} ({num(lo, lang, 2)}–{num(hi, lang, 2)})', va='center', fontsize=6.2, color='#555555' if imp else '#222222')
            ticks.append(y); labels.append(f'{sub_lab[sub]} · {int(r.cases)}/{num(int(r.n), lang)}'); y += 1
        y += 0.4
    c.set_yticks(ticks); c.set_yticklabels(labels, fontsize=6.4); c.set_ylim(y - 0.4, -0.7); c.tick_params(axis='y', length=0)
    log_axis(c, 'x', lang); c.set_xlim(0.07, 40); c.set_xticks([0.1, 0.3, 1, 3, 10]); c.xaxis.set_major_formatter(FuncFormatter(lambda v, p: num(v, lang, 1) if v < 1 else num(v, lang, 0)))
    c.set_xlabel(text('Weighted % with 95% CI (log scale); labels: cases/unweighted n\ngrey: imprecise (RSE > 30% or < 30 cases)', '% ponderado con IC 95% (escala log); etiquetas: casos/n sin ponderar\ngris: impreciso (RSE > 30% o < 30 casos)', lang), fontsize=6.8)
    # (d) commune-level comparison between hospital and programme indicators, 2021–2024
    d = fig.add_subplot(gs[1, 1]); clean(d, grid='both')
    # Public extract: rates of communes whose GRD and A05 counts are 0 or >= 5 (cells 1-4 masked); no identifiers.
    base = pd.read_csv(DATA/'communes_public.csv'); corr = pd.read_csv(DATA/'S4_correlations_selected_sensitivities.csv')
    z = base.dropna(subset=['GRD', 'A05'])
    rm = z.metropolitan.astype(bool)
    d.scatter(z.GRD[~rm], z.A05[~rm], s=12, color=BLUE, alpha=0.7, edgecolors='white', linewidths=0.3, label=text('Other regions', 'Otras regiones', lang), clip_on=False)
    d.scatter(z.GRD[rm], z.A05[rm], s=14, facecolors='white', edgecolors=ORANGE, linewidths=0.9, label=text('Metropolitan Region', 'Región Metropolitana', lang), clip_on=False)
    r = corr[(corr.pair == 'GRD–A05') & (corr.scope == 'commune') & (corr.analysis == 'core')].iloc[0]
    rx = corr[(corr.pair == 'GRD–A05') & (corr.scope == 'commune') & (corr.analysis == 'exclude_metropolitan')].iloc[0]
    d.text(0.02, 0.97, text(f'Spearman ρ = {num(r.rho, lang, 2)}; n = {int(r.n)}\nexcluding Metropolitan Region: ρ = {num(rx.rho, lang, 2)}; n = {int(rx.n)}\n{len(z)} communes shown; counts 1–4 suppressed',
                            f'ρ de Spearman = {num(r.rho, lang, 2)}; n = {int(r.n)}\nsin Región Metropolitana: ρ = {num(rx.rho, lang, 2)}; n = {int(rx.n)}\n{len(z)} comunas visibles; recuentos 1–4 suprimidos', lang),
           transform=d.transAxes, va='top', ha='left', fontsize=6.4, linespacing=1.15)
    d.set_xlabel(text('GRD: eligible episodes per 100 000\nresident person-years, 2021–24', 'GRD: episodios elegibles por 100 000\npersonas-año residentes, 2021–24', lang))
    d.set_ylabel(text('A05: strict-autism entries per 100 000\nresident person-years, 2021–24', 'A05: ingresos autismo estricto por 100 000\npersonas-año residentes, 2021–24', lang))
    d.set_xlim(left=0); d.set_ylim(0, float(z.A05.max()) * 1.25)
    d.legend(loc='upper right', bbox_to_anchor=(1.0, 0.84), fontsize=6.4, handlelength=1.2, borderaxespad=0.2)
    for ax, ch in zip([a, b, c, d], 'abcd'): letter(fig, ax, ch, dx=(-0.19 if ch == 'c' else -0.09))
    save(fig, 'Figure_4', lang)

if __name__ == '__main__':
    which = [int(x) for x in sys.argv[1:]] or [1, 2, 3, 4]
    for lang in ('en', 'es'):
        if 1 in which: fig1(lang)
        if 2 in which: fig2(lang)
        if 3 in which: fig3(lang)
        if 4 in which: fig4(lang)
    write_qa('figuras_principales_qa.json')
