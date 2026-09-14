# -*- coding: utf-8 -*-
"""equations_lancet.py — todas las fórmulas del estudio multisistema (Lancet Regional Health – Americas).

Fuente única de las ecuaciones de la metodología extendida que va, como material suplementario, dentro del
mismo archivo del manuscrito. Cada ecuación se define en LaTeX y se compone con el motor `mathtext` de
matplotlib con la familia STIX (compatible tipográficamente con Times New Roman) a 600 ppp, exactamente como
`paper/equations.py` del primer estudio; se prefieren imágenes a ecuaciones OMML porque el conversor
LaTeX→OMML disponible produce raíces y sumatorios defectuosos.

Contenido:
  EQUATIONS   lista ordenada de (clave, LaTeX) o (clave, [LaTeX por línea]); el orden es la numeración Y el orden
              en que la metodología extendida las imprime (`display_order`, `check_display_order`).
  EQUATION_LANG_VARIANTS  LaTeX alternativo por idioma (los códigos de sexo H/M del dato en español, M/F en inglés).
  NUMBER      {clave: número de ecuación} (1..N, secuencial).
  LABEL       {clave: {'es': rótulo, 'en': label}} nombre corto de la ecuación.
  ESTIMATORS  registro de estimadores: ecuaciones que lo definen, supuestos, implementación, script y salida.
              No lleva un campo «estado»: el estado («calculado» / «preespecificado») lo deriva
              `prose_methods_extended.output_exists` de la existencia real del archivo de salida declarado.
  render_all()      compone todos los PNG en outputs/equations/eq_NN_<clave>[_a|_b|_c].png (y en
                    outputs/equations/<idioma>/ los que cambian con el idioma) y devuelve {clave: [rutas base]}.
  ensure_rendered(lang) compone solo los que falten (lo usa `prose_methods_extended.methods_blocks`).
  paths_for(clave, eq_dir, lang)  rutas esperadas sin componer.
  check_display_order()  falla si alguna ecuación se imprime fuera de su número.

Notación común a todas las ecuaciones (se repite en el texto de la metodología extendida):
  d = eventos (recuento administrativo, nunca casos incidentes ni prevalentes); n = denominador declarado;
  i = área (comuna o región); h = establecimiento u hospital; t = año; a = grupo etario quinquenal (17 grupos
  de la población estándar mundial de la OMS); s = sexo registrado (H = hombres y M = mujeres, tal como lo
  codifican las fuentes chilenas; en los documentos en inglés la ecuación 2 se compone con M = male y F =
  female); α = 0,05; z = cuantil normal; φ = dispersión.
  «TEE» = tasa estandarizada por edad (direct standardisation), «CPA» = cambio porcentual anual (APC),
  «RIE» = razón indirectamente estandarizada (SIR/SMR), «IC» = intervalo de confianza, «EER» = error estándar
  relativo (RSE), «gl» = grados de libertad, como en el archivo compartido `paper/equations.py`.

Uso:  python3 lancet_americas/equations_lancet.py     (compone los PNG y lista las rutas)
"""
from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
EQ_DIR = HERE / "outputs" / "equations"

LANGS: tuple[str, ...] = ("es", "en")
BASE_LANG = "es"                 # el LaTeX de `EQUATIONS` es la versión en español (nombres de archivo históricos)

# ---------------------------------------------------------------------------
# Ecuaciones (el orden fija la numeración del suplemento)
# ---------------------------------------------------------------------------
EQUATIONS: list[tuple[str, object]] = [
    # --- 1. Tasas ---------------------------------------------------------
    ("crude", [r"r = 10^{5}\,\frac{d}{n}, \qquad d_L = \frac{1}{2}\,\chi^{2}_{2d;\,\alpha/2}, \qquad "
               r"d_U = \frac{1}{2}\,\chi^{2}_{2d+2;\,1-\alpha/2}",
               r"(r_L,\ r_U) = \left(10^{5}\,\frac{d_L}{n},\ \ 10^{5}\,\frac{d_U}{n}\right), \qquad \alpha = 0.05"]),
    ("age_specific", r"r_{as} = 10^{5}\,\frac{d_{as}}{n_{as}}, \qquad a = 1,\dots,17 \ \ (0\!-\!4,\ 5\!-\!9,\ \dots,\ 80+), "
                     r"\qquad s \in \{\mathrm{H},\ \mathrm{M}\}"),
    ("dsr", r"\mathrm{TEE} = 10^{5}\sum_{a=1}^{17} w_a\,\frac{d_a}{n_a}, \qquad w_a = \frac{p_a}{\sum_{b=1}^{17} p_b}"),
    ("dsr_var", r"\mathrm{Var}(\mathrm{TEE}) = 10^{10}\sum_{a=1}^{17} w_a^{2}\,\frac{d_a}{n_a^{2}}, \qquad "
                r"w_M = 10^{5}\,\max_{a}\left(\frac{w_a}{n_a}\right)"),
    ("ff", [r"L = G^{-1}\!\left(\frac{\alpha}{2};\ \frac{\mathrm{TEE}^{2}}{\mathrm{Var}(\mathrm{TEE})},\ "
            r"\frac{\mathrm{Var}(\mathrm{TEE})}{\mathrm{TEE}}\right)",
            r"U = G^{-1}\!\left(1-\frac{\alpha}{2};\ \frac{(\mathrm{TEE}+w_M)^{2}}{\mathrm{Var}(\mathrm{TEE})+w_M^{2}},\ "
            r"\frac{\mathrm{Var}(\mathrm{TEE})+w_M^{2}}{\mathrm{TEE}+w_M}\right)"]),
    ("rr", r"\mathrm{RT} = \frac{\mathrm{TEE}_1}{\mathrm{TEE}_2}, \qquad "
           r"\mathrm{IC}_{95\%} = \exp\left\{\ln \mathrm{RT} \pm z_{0.975}\,\mathrm{se}\right\}, \qquad "
           r"\mathrm{se}^{2} = \frac{\mathrm{Var}_1}{\mathrm{TEE}_1^{2}} + \frac{\mathrm{Var}_2}{\mathrm{TEE}_2^{2}}"),
    ("count_ratio", [r"\hat{\theta} = \frac{d_1}{d_2}, \qquad \pi = \frac{d_1}{d_1+d_2}, \qquad "
                     r"\pi_L = \mathrm{B}^{-1}\!\left(\frac{\alpha}{2};\ d_1,\ d_2+1\right), \qquad "
                     r"\pi_U = \mathrm{B}^{-1}\!\left(1-\frac{\alpha}{2};\ d_1+1,\ d_2\right)",
                     r"(\theta_L,\ \theta_U) = \left(\frac{\pi_L}{1-\pi_L},\ \ \frac{\pi_U}{1-\pi_U}\right)"]),
    # --- 2. Estandarización indirecta y suavizamiento ----------------------
    ("expected", [r"E_i = \sum_{a}\sum_{s} n_{ias}\,\lambda_{as}, \qquad "
                  r"\lambda_{as} = \frac{\sum_i d_{ias}}{\sum_i n_{ias}}, \qquad \mathrm{RIE}_i = \frac{O_i}{E_i}",
                  r"(\mathrm{RIE}_{i,L},\ \mathrm{RIE}_{i,U}) = \left(\frac{d_L(O_i)}{E_i},\ \ \frac{d_U(O_i)}{E_i}\right)"]),
    ("byar", r"\mathrm{RIE}^{B}_{i,L} = \frac{O_i\left(1 - \frac{1}{9O_i} - \frac{z_{0.975}}{3\sqrt{O_i}}\right)^{3}}{E_i}, "
             r"\qquad \mathrm{RIE}^{B}_{i,U} = \frac{(O_i+1)\left(1 - \frac{1}{9(O_i+1)} + "
             r"\frac{z_{0.975}}{3\sqrt{O_i+1}}\right)^{3}}{E_i}"),
    ("eb", r"\tilde{\theta}_i = \omega_i\,\frac{O_i}{E_i} + (1-\omega_i)\,\hat{m}, \qquad "
           r"\omega_i = \frac{E_i}{E_i + \hat{m}/\hat{v}}"),
    ("eb_prior", r"\hat{m} = \frac{\sum_i O_i}{\sum_i E_i}, \qquad "
                 r"\hat{v} = \frac{\sum_i E_i\left(O_i/E_i - \hat{m}\right)^{2}}{\sum_i E_i} - \frac{\hat{m}}{\overline{E}}, "
                 r"\qquad \overline{E} = \frac{1}{N}\sum_i E_i"),
    # --- 3. Tendencias y modelos ------------------------------------------
    ("qpois", r"\log E[d_t] = \alpha + \beta\,t + \gamma_1 c_t + \gamma_2 D_t + \log n_t, \qquad "
              r"\mathrm{Var}(d_t) = \phi\,E[d_t], \qquad D_t = \mathbf{1}\{t \in \{2020,\ 2021\}\}"),
    ("apc", r"\mathrm{CPA} = 100\left(e^{\beta}-1\right), \qquad "
            r"\mathrm{IC}_{95\%} = 100\left(e^{\beta \pm z_{0.975}\,\mathrm{se}(\beta)}-1\right), \qquad "
            r"\hat{\phi} = \frac{1}{T-p}\sum_{t=1}^{T}\frac{\left(d_t-\hat{\mu}_t\right)^{2}}{\hat{\mu}_t}"),
    ("fe", [r"\log E[d_{ht}] = \alpha_h + \beta\,t + \gamma\,c_{ht} + \log n_{ht}, \qquad h = 1,\dots,H",
            r"\hat{V}_{\mathrm{cl}} = \left(X^{\top}WX\right)^{-1}\left(\sum_{h=1}^{H} X_h^{\top} u_h u_h^{\top} X_h\right)"
            r"\left(X^{\top}WX\right)^{-1}, \qquad u_h = y_h - \hat{\mu}_h"]),
    ("ri", [r"\log E[d_{ht}\mid b_h] = \alpha + \beta\,t + \log n_{ht} + b_h, \qquad b_h \sim N(0,\ \sigma^{2})",
            r"\hat{\phi}_{c} = \frac{1}{n-p-1}\sum_{h}\sum_{t}\frac{\left(d_{ht}-\hat{\mu}_{ht}\right)^{2}}{\hat{\mu}_{ht}}"]),
    ("dw", r"\mathrm{DW} = \frac{\sum_{t=2}^{T}\left(e_t-e_{t-1}\right)^{2}}{\sum_{t=1}^{T} e_t^{2}}, \qquad "
           r"e_t = \mathrm{sign}\left(d_t-\hat{\mu}_t\right)\sqrt{2\left[d_t\log\frac{d_t}{\hat{\mu}_t}-"
           r"\left(d_t-\hat{\mu}_t\right)\right]}"),
    # --- 4. Proporciones ---------------------------------------------------
    ("wilson", r"\hat{p}_{L,U} = \frac{\hat{p} + \frac{z^{2}}{2n} \pm z\sqrt{\frac{\hat{p}(1-\hat{p})}{n} + "
               r"\frac{z^{2}}{4n^{2}}}}{1 + \frac{z^{2}}{n}}, \qquad z = z_{1-\alpha/2}"),
    ("jeffreys", r"\mathrm{IC}_{95\%}(\pi) = \left[\mathrm{B}^{-1}\!\left(0.025;\ x+\frac{1}{2},\ n-x+\frac{1}{2}\right),\ "
                 r"\mathrm{B}^{-1}\!\left(0.975;\ x+\frac{1}{2},\ n-x+\frac{1}{2}\right)\right]"),
    # --- 5. Calendario y comparabilidad de series --------------------------
    ("season", r"S_{ym} = \frac{d_{ym}}{\overline{d}_y}, \qquad \overline{d}_y = \frac{1}{12}\sum_{m=1}^{12} d_{ym}, "
               r"\qquad S_m = \frac{1}{Y}\sum_{y=1}^{Y} S_{ym}"),
    ("index_number", r"I_t = 100\,\frac{x_t}{x_{t_0}}, \qquad t_0 \in \{2019,\ 2021\}, \qquad I_{t_0} = 100"),
    # --- 6. Asociación y concordancia --------------------------------------
    ("spearman", r"\rho = 1 - \frac{6\sum_{i=1}^{n} D_i^{2}}{n\left(n^{2}-1\right)}, \qquad "
                 r"\mathrm{IC}_{95\%}(\rho) = \tanh\left(\mathrm{artanh}\,\rho \pm \frac{z_{0.975}}{\sqrt{n-3}}\right)"),
    ("kappa", r"\kappa_w = \frac{\sum_{i,j} w_{ij}\,p_{ij} - \sum_{i,j} w_{ij}\,p_{i\cdot}\,p_{\cdot j}}"
              r"{1 - \sum_{i,j} w_{ij}\,p_{i\cdot}\,p_{\cdot j}}, \qquad w_{ij} = 1 - \frac{|i-j|}{k-1}"),
    # --- 7. Encuestas con diseño complejo ----------------------------------
    ("taylor", [r"\hat{p} = \frac{\sum_{h}\sum_{c}\sum_{k} w_{hck}\,\delta_{hck}\,y_{hck}}"
                r"{\sum_{h}\sum_{c}\sum_{k} w_{hck}\,\delta_{hck}}, \qquad "
                r"u_{hck} = \frac{w_{hck}\,\delta_{hck}\left(y_{hck}-\hat{p}\right)}{\sum_{h,c,k} w_{hck}\,\delta_{hck}}",
                r"\widehat{\mathrm{Var}}(\hat{p}) = \sum_{h}\frac{m_h}{m_h-1}\sum_{c=1}^{m_h}"
                r"\left(u_{hc}-\overline{u}_h\right)^{2}, \qquad u_{hc} = \sum_k u_{hck}, \qquad "
                r"\mathrm{gl} = \sum_h m_h - H",
                r"\mathrm{IC}_{95\%}(p) = \mathrm{logit}^{-1}\left(\mathrm{logit}(\hat{p}) \pm "
                r"t_{0.975;\,\mathrm{gl}}\,\frac{\widehat{\mathrm{se}}(\hat{p})}{\hat{p}\left(1-\hat{p}\right)}\right)"]),
    ("deff", r"\mathrm{DEFF} = \frac{\widehat{\mathrm{Var}}(\hat{p})}{\hat{p}\left(1-\hat{p}\right)/n}, \qquad "
             r"\mathrm{EER} = 100\,\frac{\widehat{\mathrm{se}}(\hat{p})}{\hat{p}}, \qquad "
             r"n_{\mathrm{ef}} = \frac{n}{\mathrm{DEFF}}"),
    # --- 8. Análisis espacial ----------------------------------------------
    ("moran", [r"I = \frac{N}{S_0}\,\frac{\sum_i\sum_j w_{ij}\left(x_i-\overline{x}\right)\left(x_j-\overline{x}\right)}"
               r"{\sum_i \left(x_i-\overline{x}\right)^{2}}, \qquad S_0 = \sum_i\sum_j w_{ij}",
               r"w_{ij} = \frac{c_{ij}}{\sum_j c_{ij}}, \qquad c_{ij} = \mathbf{1}\{i \sim j\}, \qquad c_{ii} = 0, "
               r"\qquad p_{\mathrm{perm}} = \frac{1 + \mathrm{n}\{I^{(k)} \geq I_{\mathrm{obs}}\}}{K+1}, \qquad K = 999"]),
    ("moran_biv", r"I_{B} = \frac{\sum_i z^{y}_i \sum_j w_{ij}\,z^{x}_j}{\sum_i \left(z^{y}_i\right)^{2}}, \qquad "
                  r"z^{x}_i = \frac{x_i-\overline{x}}{s_x}, \qquad z^{y}_i = \frac{y_i-\overline{y}}{s_y}"),
    ("lisa", r"I_i = \frac{x_i-\overline{x}}{m_2}\sum_j w_{ij}\left(x_j-\overline{x}\right), \qquad "
             r"m_2 = \frac{1}{N}\sum_i \left(x_i-\overline{x}\right)^{2}, \qquad "
             r"p_{i,\mathrm{perm}} = \frac{1 + \mathrm{n}\{I_i^{(k)} \geq I_{i,\mathrm{obs}}\}}{K+1}"),
    # El umbral de Benjamini–Hochberg va ANTES de Gi* porque los indicadores locales (LISA) son los primeros
    # que lo aplican: el orden de esta lista es la numeración y también el orden en que la metodología
    # extendida imprime las ecuaciones (véase `display_order`).
    ("bh", r"k^{*} = \max\left\{k:\ p_{(k)} \leq \frac{k}{m}\,q\right\}, \qquad q = 0.05, \qquad p^{*} = p_{(k^{*})}"),
    ("gistar", r"G^{*}_i = \frac{\sum_j w_{ij}x_j - \overline{x}\sum_j w_{ij}}"
               r"{s\sqrt{\dfrac{N\sum_j w_{ij}^{2} - \left(\sum_j w_{ij}\right)^{2}}{N-1}}}, \qquad "
               r"s = \sqrt{\frac{1}{N}\sum_j x_j^{2} - \overline{x}^{2}}"),
    # --- 9. Desigualdad territorial ----------------------------------------
    ("lorenz", r"F_k = \frac{\sum_{i \leq k} n_{(i)}}{\sum_{i=1}^{N} n_{(i)}}, \qquad "
               r"L_k = \frac{\sum_{i \leq k} d_{(i)}}{\sum_{i=1}^{N} d_{(i)}}, \qquad "
               r"\frac{d_{(1)}}{n_{(1)}} \leq \dots \leq \frac{d_{(N)}}{n_{(N)}}"),
    ("gini", r"G = 1 - \sum_{k=1}^{N}\left(F_k-F_{k-1}\right)\left(L_k+L_{k-1}\right), \qquad F_0 = L_0 = 0, "
             r"\qquad 0 \leq G \leq 1"),
    ("theil", [r"T = \frac{1}{N}\sum_{i=1}^{N}\frac{x_i}{\mu}\log\frac{x_i}{\mu}, \qquad \mu = \frac{1}{N}\sum_{i=1}^{N} x_i",
               r"T = \sum_{g=1}^{G} s_g\,T_g + \sum_{g=1}^{G} s_g\log\frac{\mu_g}{\mu}, \qquad "
               r"s_g = \frac{\sum_{i \in g} x_i}{\sum_i x_i}"]),
    # --- 10. Regla de supresión -------------------------------------------
    ("suppression", [r"S(d) = \mathbf{1}\{1 \leq d \leq 4\}, \qquad d^{\ast} = \left[1-S(d)\right]d + S(d)\,\lambda, "
                     r"\qquad d = 0 \Rightarrow d^{\ast} = 0",
                     r"\sum_{c\,\in\,\mathcal{R}} S(d_c) = 1 \ \Rightarrow \ S(d_{c'}) \leftarrow 1, \qquad "
                     r"c' = \mathrm{arg\,min}\{d_c:\ S(d_c) = 0,\ c \in \mathcal{R}\}"]),
]

NUMBER: dict[str, int] = {key: i + 1 for i, (key, _) in enumerate(EQUATIONS)}
KEYS: list[str] = [key for key, _ in EQUATIONS]

# ---------------------------------------------------------------------------
# Variantes de idioma del LaTeX
# ---------------------------------------------------------------------------
# Los códigos de sexo son literales de las fuentes chilenas (H = hombres, M = mujeres) y no se traducen en los
# datos, pero una ecuación impresa en un documento en inglés que declare «s ∈ {H, M}» es ilegible: en inglés la
# ecuación se compone con el conjunto {M, F} y la línea de definición del texto dice qué códigos usa cada idioma.
# La versión base (español) conserva el nombre de archivo histórico `eq_NN_<clave>.png`; cada idioma con variante
# propia se compone en `outputs/equations/<idioma>/` con el mismo nombre, de modo que ningún consumidor que
# enumere `outputs/equations/*.png` (por ejemplo el inventario de activos del módulo 16) cambia de recuento.
EQUATION_LANG_VARIANTS: dict[str, dict[str, object]] = {
    "age_specific": {
        "en": r"r_{as} = 10^{5}\,\frac{d_{as}}{n_{as}}, \qquad a = 1,\dots,17 \ \ (0\!-\!4,\ 5\!-\!9,\ \dots,\ 80+), "
              r"\qquad s \in \{\mathrm{M},\ \mathrm{F}\}",
    },
}


def tex_for(key: str, lang: str = BASE_LANG) -> object:
    """LaTeX de una ecuación en el idioma pedido (str o lista de líneas); cae en la versión base si no hay variante."""
    variant = EQUATION_LANG_VARIANTS.get(key, {}).get(lang)
    return dict(EQUATIONS)[key] if variant is None else variant


def has_lang_variant(key: str, lang: str) -> bool:
    """True si la ecuación se compone distinta en ese idioma (y por tanto vive en `outputs/equations/<idioma>/`)."""
    return lang in EQUATION_LANG_VARIANTS.get(key, {})

LABEL: dict[str, dict[str, str]] = {
    "crude": {"es": "Tasa bruta y límites exactos de Poisson", "en": "Crude rate and exact Poisson limits"},
    "age_specific": {"es": "Tasas específicas por edad y sexo", "en": "Age- and sex-specific rates"},
    "dsr": {"es": "Estandarización directa (población estándar OMS)", "en": "Direct standardisation (WHO standard population)"},
    "dsr_var": {"es": "Varianza de la tasa estandarizada y corrección w_M", "en": "Variance of the standardised rate and the w_M correction"},
    "ff": {"es": "Límites gamma de Fay–Feuer", "en": "Fay–Feuer gamma limits"},
    "rr": {"es": "Razón de tasas estandarizadas con límites log-normales", "en": "Ratio of standardised rates with log-normal limits"},
    "count_ratio": {"es": "Razón de recuentos con límites binomiales exactos", "en": "Count ratio with exact binomial limits"},
    "expected": {"es": "Estandarización indirecta: casos esperados y RIE", "en": "Indirect standardisation: expected counts and SIR"},
    "byar": {"es": "Límites de Byar para la razón indirectamente estandarizada", "en": "Byar limits for the standardised ratio"},
    "eb": {"es": "Contracción bayesiana empírica global (Marshall)", "en": "Global empirical-Bayes shrinkage (Marshall)"},
    "eb_prior": {"es": "Priori por momentos del suavizamiento bayesiano empírico", "en": "Method-of-moments prior of the empirical-Bayes smoother"},
    "qpois": {"es": "Modelo log-lineal cuasi-Poisson con desplazamiento y covariables", "en": "Quasi-Poisson log-linear model with offset and covariates"},
    "apc": {"es": "Cambio porcentual anual, IC de Wald y dispersión de Pearson", "en": "Annual percent change, Wald interval and Pearson dispersion"},
    "fe": {"es": "Efectos fijos de hospital y varianza robusta por conglomerado", "en": "Hospital fixed effects and cluster-robust variance"},
    "ri": {"es": "Intercepto aleatorio Poisson y dispersión condicional", "en": "Poisson random intercept and conditional dispersion"},
    "dw": {"es": "Durbin–Watson sobre residuos de devianza", "en": "Durbin–Watson on deviance residuals"},
    "wilson": {"es": "Intervalo de Wilson para una proporción", "en": "Wilson interval for a proportion"},
    "jeffreys": {"es": "Intervalo de Jeffreys para una proporción", "en": "Jeffreys interval for a proportion"},
    "season": {"es": "Índice estacional mensual", "en": "Monthly seasonal index"},
    "index_number": {"es": "Números índice con año base declarado", "en": "Index numbers with a stated base year"},
    "spearman": {"es": "ρ de Spearman e intervalo de Fisher", "en": "Spearman's rho and the Fisher z interval"},
    "kappa": {"es": "Kappa con ponderación lineal", "en": "Linearly weighted kappa"},
    "taylor": {"es": "Razón de encuesta por linealización de Taylor", "en": "Survey ratio by Taylor linearisation"},
    "deff": {"es": "Efecto de diseño, error estándar relativo y n efectivo", "en": "Design effect, relative standard error and effective n"},
    "moran": {"es": "I de Moran global con contigüidad reina y p por permutaciones", "en": "Global Moran's I with queen contiguity and permutation p"},
    "moran_biv": {"es": "I de Moran bivariada", "en": "Bivariate Moran's I"},
    "lisa": {"es": "Indicadores locales de asociación espacial (LISA)", "en": "Local indicators of spatial association (LISA)"},
    "gistar": {"es": "Estadístico Gi* de Getis–Ord", "en": "Getis–Ord Gi* statistic"},
    "bh": {"es": "Umbral de Benjamini–Hochberg", "en": "Benjamini–Hochberg threshold"},
    "lorenz": {"es": "Curva de Lorenz territorial", "en": "Territorial Lorenz curve"},
    "gini": {"es": "Coeficiente de Gini", "en": "Gini coefficient"},
    "theil": {"es": "Índice de Theil y descomposición intra/entre", "en": "Theil index and within/between decomposition"},
    "suppression": {"es": "Regla de supresión de celdas pequeñas", "en": "Small-cell suppression rule"},
}

# ---------------------------------------------------------------------------
# Registro de estimadores: ecuación(es), supuestos, implementación, script y salida
# ---------------------------------------------------------------------------
# `output` son rutas relativas a la raíz del repositorio, separadas por «;»; una ruta sin directorio hereda el
# de la anterior y `<variante>`/`<idioma>` se resuelven por comodín. El módulo 12 comprueba su existencia y
# escribe el resultado en outputs/controls/12_methods_extended_controls.csv.
# Los marcadores se escriben SIEMPRE en su forma canónica española (`<variante>`, `<idioma>`, `<clave>`,
# `<indicador>`): `prose_methods_extended._paths` los traduce al imprimirlos, de modo que el documento en
# inglés muestre `outputs/<variant>/<language>/…` y no una ruta en español. Nunca escribas aquí la forma
# inglesa: `output_exists` y los comodines de disco esperan la forma canónica.
# NO hay campo «estado»: `prose_methods_extended._t_estimator_map` lo deriva de `output_exists(output)`, de modo
# que la tabla del mapa de estimadores no puede afirmar «preespecificado» sobre algo que ya está en el disco ni
# «calculado» sobre algo que falta. El único estimador sin archivo de salida en esta corrida es la kappa
# ponderada, cuya concordancia territorial se informa en su lugar con ρ de Spearman sobre rangos comunales.
ESTIMATORS: list[dict] = [
    dict(key="crude_rate", eq=["crude"],
         name={"es": "Tasa bruta con límites exactos de Poisson",
               "en": "Crude rate with exact Poisson limits"},
         assumption={"es": "Numerador Poisson y denominador fijo y conocido; el denominador debe pertenecer a la misma capa de cobertura que el numerador.",
                     "en": "Poisson numerator with a fixed, known denominator; the denominator must belong to the same coverage layer as the numerator."},
         impl="scripts/epi_helpers.py::crude_rate / poisson_limits; lancet_americas/common.py::rate_per",
         script="lancet_americas/pipeline/01_grd_core.py, 01b_deis_egresos.py, 02_rem_pathway.py, 11_grd_episode_detail.py",
         output="lancet_americas/outputs/tidy/grd_year_summary.csv"),
    dict(key="age_specific", eq=["age_specific"],
         name={"es": "Tasas específicas por edad y sexo", "en": "Age- and sex-specific rates"},
         assumption={"es": "Numerador y denominador clasificados con los mismos 17 grupos etarios y el mismo sexo registrado; edad desconocida se informa aparte y nunca se imputa.",
                     "en": "Numerator and denominator classified with the same 17 age groups and the same recorded sex; unknown age is reported separately and never imputed."},
         impl="scripts/epi_helpers.py::age_group_from_age, attach_population",
         script="lancet_americas/pipeline/03_denominators.py, 06_models.py",
         output="lancet_americas/outputs/tidy/models_population_rates.csv"),
    dict(key="direct_standardisation", eq=["dsr", "dsr_var", "ff"],
         name={"es": "Estandarización directa por edad con límites de Fay–Feuer",
               "en": "Direct age standardisation with Fay–Feuer limits"},
         assumption={"es": "Recuentos por grupo etario independientes y Poisson; los grupos sin denominador se excluyen y los pesos restantes se renormalizan (se informa cuántos faltan).",
                     "en": "Independent Poisson counts by age group; groups without a denominator are dropped and the remaining weights renormalised (the number missing is reported)."},
         impl="scripts/epi_helpers.py::direct_standardization (WHO_STANDARD; scipy.stats.gamma)",
         script="lancet_americas/pipeline/06_models.py::_standardise, population_rates",
         output="lancet_americas/outputs/tidy/models_population_rates.csv"),
    dict(key="rate_ratio", eq=["rr"],
         name={"es": "Razón de tasas estandarizadas (hombres/mujeres)",
               "en": "Ratio of standardised rates (males/females)"},
         assumption={"es": "Las dos tasas son independientes y su logaritmo es aproximadamente normal; no se aplica a numeradores de fuentes distintas ni no enlazables.",
                     "en": "The two rates are independent and their logarithm is approximately normal; never applied to numerators from different, unlinkable sources."},
         impl="scripts/epi_helpers.py::rate_ratio",
         script="lancet_americas/pipeline/06_models.py::population_rates",
         output="lancet_americas/outputs/tidy/models_population_rates.csv"),
    dict(key="count_ratio", eq=["count_ratio"],
         name={"es": "Razón de recuentos con límites binomiales exactos",
               "en": "Count ratio with exact binomial limits"},
         assumption={"es": "Los dos recuentos son Poisson independientes sobre la misma base poblacional; condicionando en el total, la razón se obtiene de la binomial exacta. No se usa entre fuentes no enlazables.",
                     "en": "The two counts are independent Poisson on the same population basis; conditioning on the total gives the exact binomial ratio. Never used between unlinkable sources."},
         impl="scripts/epi_helpers.py::count_ratio (scipy.stats.beta.ppf)",
         script={"es": "lancet_americas/pipeline/14_extra_figures_rem.py::prep_e14 (razón hombres:mujeres por grupo etario, A05)",
                 "en": "lancet_americas/pipeline/14_extra_figures_rem.py::prep_e14 (male:female ratio by age group, A05)"},
         output="lancet_americas/outputs/<variante>/<idioma>/extra/tables/E14_rem_a05_age_sex_numeric.csv"),
    dict(key="indirect_standardisation", eq=["expected", "byar"],
         name={"es": "Estandarización indirecta: esperados y RIE",
               "en": "Indirect standardisation: expected counts and SIR"},
         assumption={"es": "Las tasas específicas nacionales son aplicables a la estructura de cada área; el esperado exige la población por edad y sexo del área. Los límites exactos se sustituyen por los de Byar cuando O > 100.",
                     "en": "National stratum-specific rates apply to each area's structure; the expected count requires the area's age-by-sex population. Exact limits are replaced by Byar's when O > 100."},
         impl="lancet_americas/pipeline/15b_spatial_correlation.py::indirect_standardise, national_age_sex_schedule; "
              "scripts/epi_helpers.py::expected_counts, standardized_ratio",
         script="lancet_americas/pipeline/15b_spatial_correlation.py::indirect_standardise",
         output="lancet_americas/outputs/tidy/spatial_comuna_standardised.csv; spatial_region_summary.csv; "
                "spatial_denominator_sensitivity.csv"),
    dict(key="empirical_bayes", eq=["eb", "eb_prior"],
         name={"es": "Contracción bayesiana empírica global de las RIE",
               "en": "Global empirical-Bayes shrinkage of the SIR"},
         assumption={"es": "Modelo Poisson–gamma con una única distribución previa común a todas las áreas (sin estructura espacial); la varianza previa se estima por momentos y se trunca en cero.",
                     "en": "Poisson–gamma model with a single prior common to all areas (no spatial structure); the prior variance is estimated by moments and truncated at zero."},
         impl="lancet_americas/pipeline/15b_spatial_correlation.py::indirect_standardise (Marshall 1991: sir_eb, "
              "eb_weight, prior_mean, prior_variance); scripts/epi_helpers.py::empirical_bayes_ratio",
         script="lancet_americas/pipeline/15b_spatial_correlation.py::indirect_standardise",
         output="lancet_americas/outputs/tidy/spatial_comuna_standardised.csv; spatial_region_summary.csv"),
    dict(key="quasi_poisson", eq=["qpois", "apc"],
         name={"es": "Tendencia log-lineal cuasi-Poisson y CPA",
               "en": "Quasi-Poisson log-linear trend and APC"},
         assumption={"es": "Log-linealidad de la tendencia en el período modelado, varianza proporcional a la media (escala de Pearson) y desplazamiento log(denominador) con coeficiente uno; la serie de 4–7 puntos no identifica efectos causales.",
                     "en": "Log-linear trend over the modelled period, variance proportional to the mean (Pearson scale) and a log(denominator) offset with unit coefficient; a 4–7-point series identifies no causal effect."},
         impl="lancet_americas/common.py::quasi_poisson_trend; scripts/epi_helpers.py::annual_percent_change",
         script="lancet_americas/pipeline/06_models.py::fit_glm, Store.add_trend",
         output="lancet_americas/outputs/tidy/models_summary.csv"),
    dict(key="hospital_fixed_effects", eq=["fe"],
         name={"es": "Efectos fijos de hospital con varianza robusta por conglomerado",
               "en": "Hospital fixed effects with cluster-robust variance"},
         assumption={"es": "Tendencia común a los hospitales y nivel propio de cada uno; los errores se agrupan por hospital (H = 65–72 conglomerados, suficiente para el sándwich).",
                     "en": "A trend common to hospitals with a hospital-specific level; errors are clustered by hospital (H = 65–72 clusters, enough for the sandwich estimator)."},
         impl="statsmodels GLM(family=Poisson, scale='X2', cov_type='cluster')",
         script="lancet_americas/pipeline/06_models.py::hospital_models",
         output="lancet_americas/outputs/tidy/hospital_effects.csv"),
    dict(key="random_intercept", eq=["ri"],
         name={"es": "Intercepto aleatorio Poisson con diagnóstico de dispersión condicional",
               "en": "Poisson random intercept with conditional dispersion diagnostic"},
         assumption={"es": "Interceptos normales e independientes del predictor y equidispersión condicional; la dispersión condicional observada (≈3) muestra que el IC del modelo es anticonservador y se mantiene solo como sensibilidad.",
                     "en": "Normal intercepts independent of the predictor and conditional equidispersion; the observed conditional dispersion (≈3) shows the model's CI is anticonservative, so it is kept only as a sensitivity."},
         impl="statsmodels PoissonBayesMixedGLM (Laplace/MAP, offset)",
         script="lancet_americas/pipeline/06_models.py::fit_random_intercept",
         output="lancet_americas/outputs/tidy/hospital_effects.csv"),
    dict(key="durbin_watson", eq=["dw"],
         name={"es": "Durbin–Watson sobre residuos de devianza",
               "en": "Durbin–Watson on deviance residuals"},
         assumption={"es": "Residuos ordenados cronológicamente y equidistantes; con menos de ocho puntos la prueba es débil y se informa solo como orientación.",
                     "en": "Residuals ordered chronologically and equally spaced; with fewer than eight points the test is weak and is reported only as an indication."},
         impl="lancet_americas/pipeline/06_models.py::durbin_watson",
         script="lancet_americas/pipeline/06_models.py",
         output="lancet_americas/outputs/tidy/models_summary.csv"),
    dict(key="wilson", eq=["wilson"],
         name={"es": "Intervalo de Wilson para proporciones", "en": "Wilson interval for proportions"},
         assumption={"es": "Numerador binomial dentro de un denominador cerrado y observado (por ejemplo, egresos elegibles con horizonte completo dentro de la era del identificador).",
                     "en": "Binomial numerator within a closed, observed denominator (for example, discharges eligible with a complete horizon inside the identifier era)."},
         impl="lancet_americas/common.py::wilson",
         script="lancet_americas/pipeline/11_grd_episode_detail.py",
         output="lancet_americas/outputs/tidy/grd_readmission.csv"),
    dict(key="jeffreys", eq=["jeffreys"],
         name={"es": "Intervalo de Jeffreys para proporciones pequeñas",
               "en": "Jeffreys interval for small proportions"},
         assumption={"es": "Alternativa bayesiana con previa Beta(1/2, 1/2) para proporciones cercanas a cero o a uno, donde Wilson pierde cobertura nominal.",
                     "en": "Bayesian alternative with a Beta(1/2, 1/2) prior for proportions near zero or one, where Wilson loses nominal coverage."},
         impl="lancet_americas/pipeline/13_extra_figures_hospital.py::jeffreys (scipy.stats.beta.ppf)",
         script={"es": "lancet_americas/pipeline/13_extra_figures_hospital.py::ef4 (letalidad hospitalaria por año y posición)",
                 "en": "lancet_americas/pipeline/13_extra_figures_hospital.py::ef4 (in-hospital lethality by year and position)"},
         output="lancet_americas/outputs/<variante>/<idioma>/extra/tables/EF4_severity_weight_numeric.csv"),
    dict(key="seasonal_index", eq=["season"],
         name={"es": "Índice estacional mensual", "en": "Monthly seasonal index"},
         assumption={"es": "Doce meses observados por año y denominador estable dentro del año; los episodios sin fecha analizable van a la fila «mes desconocido» y quedan fuera del índice.",
                     "en": "Twelve observed months per year and a stable within-year denominator; episodes without a parsable date go to the 'unknown month' row and stay out of the index."},
         impl="scripts/epi_helpers.py::seasonal_index; lancet_americas/pipeline/11_grd_episode_detail.py",
         script="lancet_americas/pipeline/11_grd_episode_detail.py, 08b_figures_rem.py",
         output="lancet_americas/outputs/tidy/grd_monthly.csv"),
    dict(key="index_numbers", eq=["index_number"],
         name={"es": "Números índice con año base declarado", "en": "Index numbers with a stated base year"},
         assumption={"es": "Solo comparan la forma de series con unidades, denominadores y coberturas distintas; nunca sustituyen niveles ni permiten cocientes entre fuentes.",
                     "en": "They compare only the shape of series with different units, denominators and coverage; they never replace levels nor licence ratios between sources."},
         impl="lancet_americas/pipeline/06_models.py::convergence_index",
         script="lancet_americas/pipeline/06_models.py",
         output="lancet_americas/outputs/tidy/models_convergence_index.csv"),
    dict(key="spearman", eq=["spearman"],
         name={"es": "ρ de Spearman con intervalo de Fisher", "en": "Spearman's rho with the Fisher z interval"},
         assumption={"es": "Asociación monótona entre dos variables ecológicas; la transformación de Fisher supone independencia entre unidades, supuesto que la autocorrelación espacial vulnera (se declara al informarlo).",
                     "en": "Monotone association between two ecological variables; the Fisher transformation assumes independent units, an assumption that spatial autocorrelation violates (stated when reported)."},
         impl="scipy.stats.spearmanr; np.arctanh; lancet_americas/pipeline/15b_spatial_correlation.py::spearman_ci",
         script="lancet_americas/pipeline/06_models.py::figure_hospital; 15b_spatial_correlation.py::spearman_ci",
         output="lancet_americas/outputs/tidy/hospital_effects.csv; spatial_correlations.csv; spatial_stability.csv"),
    dict(key="weighted_kappa", eq=["kappa"],
         name={"es": "Kappa con ponderación lineal", "en": "Linearly weighted kappa"},
         assumption={"es": "Dos clasificaciones ordinales del mismo conjunto de áreas (por ejemplo, quintiles de dos fuentes); las áreas son las unidades y no hay enlace individual.",
                     "en": "Two ordinal classifications of the same set of areas (for example, quintiles from two sources); areas are the units and there is no individual linkage."},
         impl="cálculo directo de la matriz de acuerdo con pesos lineales (equivalente a "
              "sklearn.metrics.cohen_kappa_score(weights='linear'))",
         script={"es": "sin implementación en esta corrida: la concordancia territorial entre sistemas se informa con "
                       "ρ de Spearman sobre los rangos comunales y regionales (15b_spatial_correlation.py::spearman_ci)",
                 "en": "no implementation in this run: territorial agreement between systems is reported with Spearman's "
                       "rho on the comuna and region ranks (15b_spatial_correlation.py::spearman_ci)"},
         output="—"),
    dict(key="survey_taylor", eq=["taylor"],
         name={"es": "Proporción de encuesta con linealización de Taylor",
               "en": "Survey proportion with Taylor linearisation"},
         assumption={"es": "Muestreo estratificado por conglomerados con ponderadores de expansión; el dominio se estima como razón conservando todas las unidades y anulando la contribución fuera del dominio.",
                     "en": "Stratified cluster sampling with expansion weights; the domain is estimated as a ratio, keeping all units and zeroing the contribution outside the domain."},
         impl="lancet_americas/common.py::survey_proportion",
         script="lancet_americas/pipeline/04_surveys.py::estimate",
         output="lancet_americas/outputs/tidy/survey_estimates.csv"),
    dict(key="design_effect", eq=["deff"],
         name={"es": "Efecto de diseño y error estándar relativo",
               "en": "Design effect and relative standard error"},
         assumption={"es": "El comparador es un muestreo aleatorio simple con el mismo n no ponderado del dominio; los dominios con menos de 30 casos o EER > 30 % se marcan y no se presentan como estimaciones fiables.",
                     "en": "The comparator is simple random sampling with the same unweighted domain n; domains with fewer than 30 cases or RSE > 30% are flagged and not presented as reliable."},
         impl="lancet_americas/pipeline/04_surveys.py::estimate",
         script="lancet_americas/pipeline/04_surveys.py",
         output="lancet_americas/outputs/tidy/survey_estimates.csv"),
    dict(key="moran_global", eq=["moran"],
         name={"es": "I de Moran global con contigüidad reina estandarizada por filas",
               "en": "Global Moran's I with row-standardised queen contiguity"},
         assumption={"es": "Matriz de contigüidad reina estandarizada por filas sobre las comunas continentales (las no continentales se conservan en las tablas y quedan fuera de la matriz); las comunas sin vecino reina se informan y se enlazan con su vecino más próximo (KNN-1), y k = 4, k = 8 y la distancia inversa son sensibilidades declaradas; p por 999 permutaciones con semilla fija.",
                     "en": "Row-standardised queen contiguity over the continental comunas (non-continental ones stay in the tables and out of the matrix); comunas with no queen neighbour are reported and attached to their nearest neighbour (KNN-1), and k = 4, k = 8 and inverse distance are declared sensitivities; p from 999 permutations with a fixed seed."},
         impl="libpysal.weights.Queen / KNN / DistanceBand (transform='r', attach_islands); "
              "esda.moran.Moran(permutations=999)",
         script="lancet_americas/pipeline/15b_spatial_correlation.py::load_geography, moran_global",
         output="lancet_americas/outputs/tidy/spatial_moran.csv"),
    dict(key="moran_bivariate", eq=["moran_biv"],
         name={"es": "I de Moran bivariada entre fuentes", "en": "Bivariate Moran's I between sources"},
         assumption={"es": "Asociación entre el valor de una fuente en un área y el promedio ponderado de otra fuente en las áreas vecinas; es ecológica y mezcla lugar de atención con residencia si las fuentes difieren (se declara).",
                     "en": "Association between one source's value in an area and the weighted average of another source in neighbouring areas; ecological and mixing place of care with residence when sources differ (stated)."},
         impl="esda.moran.Moran_BV(permutations=999); esda.moran.Moran_Local_BV(seed=SEED)",
         script="lancet_americas/pipeline/15b_spatial_correlation.py::moran_bivariate",
         output="lancet_americas/outputs/tidy/spatial_bivariate_moran.csv; spatial_bivariate_local.csv"),
    dict(key="lisa", eq=["lisa", "bh"],
         name={"es": "Indicadores locales de asociación espacial", "en": "Local indicators of spatial association"},
         assumption={"es": "Inferencia condicional por permutaciones con la misma matriz de pesos; la multiplicidad de N pruebas locales se controla con el umbral de Benjamini–Hochberg (q = 0,05).",
                     "en": "Conditional permutation inference with the same weights matrix; the multiplicity of N local tests is controlled with the Benjamini–Hochberg threshold (q = 0.05)."},
         impl="esda.moran.Moran_Local(permutations=999, seed=SEED); "
              "statsmodels.stats.multitest.multipletests(method='fdr_bh', alpha=0.05)",
         script="lancet_americas/pipeline/15b_spatial_correlation.py::lisa_local, bh_threshold",
         output="lancet_americas/outputs/tidy/spatial_lisa.csv"),
    dict(key="getis_ord", eq=["gistar", "bh"],
         name={"es": "Estadístico Gi* de Getis–Ord", "en": "Getis–Ord Gi* statistic"},
         assumption={"es": "La misma matriz reina estandarizada por filas de los indicadores locales, incluyendo la propia área (star=True); exige valores no negativos, de modo que una serie con valores negativos se desplaza antes de calcularla; identifica conglomerados de valores altos o bajos, no significación causal, y usa la misma corrección de multiplicidad.",
                     "en": "The same row-standardised queen matrix as the local indicators, including the area itself (star=True); it requires non-negative values, so a series with negative values is shifted before it is computed; it identifies clusters of high or low values, not causal significance, and uses the same multiplicity correction."},
         impl="esda.getisord.G_Local(star=True, permutations=999, seed=SEED); "
              "statsmodels.stats.multitest.multipletests(method='fdr_bh', alpha=0.05)",
         script="lancet_americas/pipeline/15b_spatial_correlation.py::gistar_local, bh_threshold",
         output="lancet_americas/outputs/tidy/spatial_lisa.csv"),
    dict(key="lorenz_gini", eq=["lorenz", "gini"],
         name={"es": "Curva de Lorenz y coeficiente de Gini territoriales",
               "en": "Territorial Lorenz curve and Gini coefficient"},
         assumption={"es": "Áreas ordenadas por su tasa; el eje de población usa el mismo denominador que la tasa. Mide concentración del registro administrativo entre territorios, no desigualdad en el acceso.",
                     "en": "Areas ordered by their rate; the population axis uses the same denominator as the rate. It measures concentration of administrative recording across territories, not inequality of access."},
         impl="lancet_americas/pipeline/15b_spatial_correlation.py::lorenz_gini (trapecios sobre la curva acumulada)",
         script="lancet_americas/pipeline/15b_spatial_correlation.py::lorenz_gini, decile_ratio",
         output="lancet_americas/outputs/tidy/spatial_inequality.csv"),
    dict(key="theil", eq=["theil"],
         name={"es": "Índice de Theil con descomposición intra/entre regiones",
               "en": "Theil index with within/between-region decomposition"},
         assumption={"es": "Requiere valores estrictamente positivos; las áreas con cero eventos se informan aparte y no entran en el logaritmo. La descomposición usa la región como grupo.",
                     "en": "Requires strictly positive values; areas with zero events are reported separately and excluded from the logarithm. The decomposition uses the region as the group."},
         impl="lancet_americas/pipeline/15b_spatial_correlation.py::theil_decomposition (descomposición intra/entre regiones)",
         script="lancet_americas/pipeline/15b_spatial_correlation.py::theil_decomposition",
         output="lancet_americas/outputs/tidy/spatial_inequality.csv"),
    dict(key="suppression", eq=["suppression"],
         name={"es": "Regla de supresión de celdas pequeñas", "en": "Small-cell suppression rule"},
         assumption={"es": "Cero, ausente y «no reportado» son estados distintos: el cero se publica como cero y solo se suprimen los recuentos de 1 a 4; si una fila queda con una sola celda suprimida se suprime también la siguiente menor para evitar la recuperación por diferencia.",
                     "en": "Zero, missing and 'not reported' are distinct states: zero is published as zero and only counts of 1–4 are suppressed; if a row is left with a single suppressed cell, the next smallest is also suppressed to prevent recovery by subtraction."},
         impl="lancet_americas/pipeline/11_grd_episode_detail.py (suppression_flag, n_episodes_display); "
              "15b_spatial_correlation.py (columna suppressed de las tablas comunales)",
         script="lancet_americas/pipeline/11_grd_episode_detail.py, 01b_deis_egresos.py, 15b_spatial_correlation.py",
         output="lancet_americas/outputs/tidy/grd_territory.csv; spatial_comuna_indicators.csv"),
]

ESTIMATOR_KEYS = [e["key"] for e in ESTIMATORS]


def numbers_for(estimator_key: str) -> list[int]:
    """Números de ecuación de un estimador, en el orden en que se definen."""
    for e in ESTIMATORS:
        if e["key"] == estimator_key:
            return [NUMBER[k] for k in e["eq"]]
    raise KeyError(estimator_key)


def orphan_equations() -> list[str]:
    """Ecuaciones que ningún estimador cita (deben ser cero)."""
    cited = {k for e in ESTIMATORS for k in e["eq"]}
    return [k for k in KEYS if k not in cited]


def orphan_estimators() -> list[str]:
    """Estimadores sin ecuación o con una clave de ecuación inexistente (deben ser cero)."""
    bad = []
    for e in ESTIMATORS:
        if not e["eq"] or any(k not in NUMBER for k in e["eq"]):
            bad.append(e["key"])
    return bad


# ---------------------------------------------------------------------------
# Orden de impresión: la metodología extendida emite cada ecuación la primera vez que un estimador la cita,
# de modo que el orden de `ESTIMATORS` (y, dentro de cada uno, el de su lista `eq`) debe reproducir la
# numeración 1, 2, …, N. Si no lo hace, el documento imprime «Ecuación 29» antes que «Ecuación 28».
# ---------------------------------------------------------------------------
def display_order() -> list[tuple[str, int]]:
    """(clave, número) en el orden en que la metodología extendida imprime las ecuaciones."""
    seen: set[str] = set()
    order: list[tuple[str, int]] = []
    for e in ESTIMATORS:
        for key in e["eq"]:
            if key in seen or key not in NUMBER:
                continue
            seen.add(key)
            order.append((key, NUMBER[key]))
    return order


def display_order_problems() -> list[str]:
    """Descripción de cada ecuación cuyo lugar de impresión no coincide con su número (debe ser lista vacía)."""
    order = display_order()
    problems = [f"{key} (ecuación {number}) se imprime en la posición {position}"
                for position, (key, number) in enumerate(order, start=1) if number != position]
    missing = [key for key in KEYS if key not in {k for k, _ in order}]
    if missing:
        problems.append(f"ecuaciones que ningún estimador imprime: {missing}")
    return problems


def check_display_order() -> list[tuple[str, int]]:
    """Falla ruidosamente si el orden de impresión difiere de la numeración; devuelve el orden verificado."""
    problems = display_order_problems()
    if problems:
        raise RuntimeError("el orden de impresión de las ecuaciones no es ascendente: " + "; ".join(problems))
    return display_order()


# ---------------------------------------------------------------------------
# Composición de los PNG
# ---------------------------------------------------------------------------
def _parts(tex) -> list[str]:
    return tex if isinstance(tex, list) else [tex]


def paths_for(key: str, eq_dir: Path | None = None, lang: str = BASE_LANG) -> list[Path]:
    """Rutas esperadas de los PNG de una ecuación (sin componerlos).

    El idioma base conserva `outputs/equations/eq_NN_<clave>[_a].png`; un idioma con variante propia de LaTeX
    escribe el mismo nombre dentro de `outputs/equations/<idioma>/`.
    """
    eq_dir = Path(eq_dir or EQ_DIR)
    if has_lang_variant(key, lang):
        eq_dir = eq_dir / lang
    parts = _parts(tex_for(key, lang))
    out = []
    for k in range(len(parts)):
        suffix = "" if len(parts) == 1 else f"_{'abcdef'[k]}"
        out.append(eq_dir / f"eq_{NUMBER[key]:02d}_{key}{suffix}.png")
    return out


def _compose(part: str, path: Path, plt, dpi: int, fontsize: int) -> None:
    """Compone una línea de LaTeX en su PNG con el motor mathtext y la familia STIX."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(0.1, 0.1))
    text = fig.text(0, 0, f"${part}$", fontsize=fontsize)
    fig.canvas.draw()
    bbox = text.get_window_extent()
    width, height = bbox.width / fig.dpi + 0.15, bbox.height / fig.dpi + 0.15
    plt.close(fig)
    fig = plt.figure(figsize=(width, height))
    fig.text(0.5, 0.5, f"${part}$", fontsize=fontsize, ha="center", va="center")
    fig.savefig(path, dpi=dpi, facecolor="white", bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)


def render_all(dpi: int = 600, fontsize: int = 15, eq_dir: Path | None = None, only_missing: bool = False,
               langs: tuple[str, ...] = LANGS) -> dict:
    """Compone las ecuaciones en todos los idiomas y devuelve {clave: [rutas PNG del idioma base]}."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"mathtext.fontset": "stix", "font.family": "STIXGeneral", "text.usetex": False})
    eq_dir = Path(eq_dir or EQ_DIR)
    eq_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, list[Path]] = {}
    for key, _ in EQUATIONS:
        done: set[Path] = set()
        for lang in langs:
            targets = paths_for(key, eq_dir, lang)
            if lang == BASE_LANG:
                paths[key] = targets
            for part, path in zip(_parts(tex_for(key, lang)), targets):
                if path in done or (only_missing and path.is_file()):
                    done.add(path)
                    continue
                _compose(part, path, plt, dpi, fontsize)
                done.add(path)
        paths.setdefault(key, paths_for(key, eq_dir, BASE_LANG))
    return paths


def ensure_rendered(eq_dir: Path | None = None, lang: str = BASE_LANG) -> dict:
    """Compone solo los PNG que falten; devuelve {clave: [rutas del idioma pedido]}."""
    eq_dir = Path(eq_dir or EQ_DIR)
    missing = any(not p.is_file() for lg in LANGS for key in KEYS for p in paths_for(key, eq_dir, lg))
    if missing:
        render_all(eq_dir=eq_dir, only_missing=True)
    return {key: paths_for(key, eq_dir, lang) for key in KEYS}


if __name__ == "__main__":
    order = check_display_order()          # falla ruidosamente si la impresión no sigue la numeración
    rendered = render_all()
    total = sum(len(paths_for(k, lang=lg)) for lg in LANGS for k in KEYS)
    print(f"{len(EQUATIONS)} ecuaciones, {total} PNG en {EQ_DIR} ({', '.join(LANGS)})")
    for key, ps in rendered.items():
        extra = [f"{lg}/{p.name}" for lg in LANGS if lg != BASE_LANG and has_lang_variant(key, lg)
                 for p in paths_for(key, lang=lg)]
        print(f"  ({NUMBER[key]:2d}) {key:<16} {[p.name for p in ps]}" + (f" + {extra}" if extra else ""))
    print("Orden de impresión:", ", ".join(str(n) for _, n in order))
    print("Ecuaciones fuera de orden:", display_order_problems() or "ninguna")
    print("Ecuaciones sin estimador:", orphan_equations() or "ninguna")
    print("Estimadores sin ecuación:", orphan_estimators() or "ninguno")
