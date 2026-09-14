# -*- coding: utf-8 -*-
"""labels.py — rótulos bilingües compartidos por tablas y láminas. Ampliar aquí, nunca con literales sueltos en los scripts.

Este archivo es la fuente única de tres cosas que TODO documento construido necesita:

  1. `L` / `t(clave, idioma)` — los rótulos cortos y bilingües que ya usaban tablas y láminas.
  2. `ICD10` / `icd_label(codigo, idioma)` — el diccionario ÚNICO de categorías CIE-10 de tres
     caracteres con su glosa en español y en inglés, más los capítulos y los bloques de salud mental.
     El documento en inglés jamás imprime la glosa española: si un código no tiene glosa inglesa se
     imprime el código solo (y la nota de la tabla lo dice).
  3. `language_leak(texto, idioma)` — el detector reutilizable de fuga de idioma con el que se prueba
     que ninguna celda, encabezado, título, nota o leyenda de los cuatro documentos construidos está
     escrita en el idioma equivocado (`tests/test_language_purity.py`). Junto a él, `marker_leak` y
     `PLACEHOLDER_MARKERS` cazan los marcadores de estado («ABSENT», «n/a», «Outcome», «no reportado»),
     demasiado cortos para el umbral de palabras funcionales y que ninguna declaración de transcripción
     exime, porque no son cita de nada.
  4. `provenance_text(valor, idioma)` — la glosa bilingüe de los campos descriptivos de
     `data_provenance.csv` (unidad, período, stock/flujo, quiebres, enlace, regla de uso) y de las notas
     de concordancia de manifiesto, que la Tabla S14 y la S15 imprimen.
  5. `GRD_SOURCE_CATEGORY` / `GRD_COUNTRY` — las categorías administrativas del episodio GRD que el
     registro escribe en español y que el documento en inglés lee en inglés; lo que queda literal
     (servicio de salud, especialidad, tramo previsional, pueblos originarios) lo declara
     `GRD_CATEGORY_NOTE`, la frase que comparten las Tablas S54 y S109.

Regla de estilo del estudio: una cadena que llega a un documento se escribe SIEMPRE como
`{"es": …, "en": …}`; el texto libre que viene de un archivo tidy o de un registro del pipeline se
traduce aquí o en el módulo que lo imprime, nunca se deja pasar tal cual al otro idioma.
"""
L = {
    "year": {"es": "Año", "en": "Year"},
    "episodes_f84_any": {"es": "Episodios GRD con F84 documentado (cualquier posición)", "en": "GRD episodes with documented F84 (any position)"},
    "episodes_f84_principal": {"es": "Episodios GRD con F84 principal", "en": "GRD episodes with F84 as principal diagnosis"},
    "per_100k_episodes": {"es": "por 100.000 episodios GRD", "en": "per 100,000 GRD episodes"},
    "per_100k_pop": {"es": "por 100.000 habitantes", "en": "per 100,000 population"},
    "observed_panel": {"es": "Panel anual observado", "en": "Observed annual panel"},
    "fixed_panel_65": {"es": "Panel fijo de 65 hospitales", "en": "Fixed panel of 65 hospitals"},
    "strict_hospitalisation": {"es": "Hospitalización estricta", "en": "Strict hospitalisation"},
    "cma": {"es": "Cirugía mayor ambulatoria", "en": "Major ambulatory surgery"},
    "coding_depth": {"es": "Profundidad diagnóstica (diagnósticos por episodio)", "en": "Coding depth (diagnoses per episode)"},
    "reporting_establishments": {"es": "Establecimientos reportantes", "en": "Reporting establishments"},
    "stable_panel": {"es": "Panel estable de establecimientos", "en": "Stable establishment panel"},
    "entries_autism": {"es": "Ingresos a salud mental por autismo (A05)", "en": "Mental-health programme entries for autism (A05)"},
    "stock_december": {"es": "Población bajo control en diciembre", "en": "Population under control in December"},
    "stock_june": {"es": "Población bajo control en junio (sensibilidad)", "en": "Population under control in June (sensitivity)"},
    "definition_era": {"es": "Era de definición", "en": "Definition era"},
    "pandemic": {"es": "Pandemia COVID-19", "en": "COVID-19 pandemic"},
    "law": {"es": "Ley 21.545 (marzo 2023)", "en": "Law 21.545 (March 2023)"},
    "ci95": {"es": "IC 95 %", "en": "95% CI"},
    "men": {"es": "Hombres", "en": "Males"},
    "women": {"es": "Mujeres", "en": "Females"},
    "both": {"es": "Ambos sexos", "en": "Both sexes"},
    "not_estimable": {"es": "no estimable", "en": "not estimable"},
}


def t(key: str, lang: str) -> str:
    return L[key][lang]


# ===========================================================================
# CIE-10 / ICD-10 — diccionario ÚNICO de glosas de tres caracteres
# ===========================================================================
#: Procedencia de cada columna del diccionario:
#:   * `es` — glosas abreviadas del diccionario CIE-10 en español que usa el pipeline chileno
#:     (MINSAL/DEIS; réplica de `scripts/report_helpers.ICD_LABELS`, la lista con la que se
#:     construyen las tablas tidy `grd_codiagnoses.csv`).
#:   * `en` — rúbrica inglesa de la categoría de tres caracteres de la CIE-10 de la OMS
#:     (World Health Organization. International Statistical Classification of Diseases and Related
#:     Health Problems, 10th revision, 2019 edition; https://icd.who.int/browse10/2019/en),
#:     abreviada con el mismo criterio que la columna española.
#: Un código sin entrada aquí se imprime SOLO (sin glosa) en los dos idiomas.
ICD10_SOURCE = {
    "es": ("Glosas CIE-10 en español: diccionario MINSAL/DEIS usado por el pipeline. Glosas en inglés: rúbrica de "
           "la categoría de tres caracteres de la CIE-10 de la OMS (10.ª revisión, edición 2019, "
           "icd.who.int/browse10/2019/en). Un código sin glosa en el idioma del documento se imprime solo, "
           "sin glosa: nunca se imprime la glosa del otro idioma."),
    "en": ("Spanish ICD-10 labels: the MINSAL/DEIS dictionary used by the pipeline. English labels: the WHO "
           "ICD-10 three-character category rubric (10th revision, 2019 edition, icd.who.int/browse10/2019/en), "
           "abbreviated with the same criterion as the Spanish column. A code without a label in the document's "
           "language is printed alone, with no label: the other language's label is never printed."),
}

ICD10: dict[str, dict[str, str]] = {
    "A08": {"es": "Infecciones intestinales virales", "en": "Viral and other specified intestinal infections"},
    "A09": {"es": "Diarrea y gastroenteritis de presunto origen infeccioso", "en": "Diarrhoea and gastroenteritis of presumed infectious origin"},
    "B34": {"es": "Infección viral de sitio no especificado", "en": "Viral infection of unspecified site"},
    "B95": {"es": "Estreptococos y estafilococos como causa", "en": "Streptococcus and staphylococcus as the cause of diseases classified elsewhere"},
    "B96": {"es": "Otros agentes bacterianos como causa", "en": "Other bacterial agents as the cause of diseases classified elsewhere"},
    "B97": {"es": "Agentes virales como causa de enfermedades", "en": "Viral agents as the cause of diseases classified elsewhere"},
    "C71": {"es": "Tumor maligno del encéfalo", "en": "Malignant neoplasm of brain"},
    "C91": {"es": "Leucemia linfoide", "en": "Lymphoid leukaemia"},
    "D33": {"es": "Tumor benigno del encéfalo y SNC", "en": "Benign neoplasm of brain and other parts of central nervous system"},
    "D50": {"es": "Anemia por deficiencia de hierro", "en": "Iron deficiency anaemia"},
    "D64": {"es": "Otras anemias", "en": "Other anaemias"},
    "D69": {"es": "Púrpura y otras afecciones hemorrágicas", "en": "Purpura and other haemorrhagic conditions"},
    "E03": {"es": "Otro hipotiroidismo", "en": "Other hypothyroidism"},
    "E10": {"es": "Diabetes mellitus tipo 1", "en": "Insulin-dependent diabetes mellitus"},
    "E11": {"es": "Diabetes mellitus tipo 2", "en": "Non-insulin-dependent diabetes mellitus"},
    "E22": {"es": "Hiperfunción de la hipófisis", "en": "Hyperfunction of pituitary gland"},
    "E30": {"es": "Trastornos de la pubertad", "en": "Disorders of puberty, not elsewhere classified"},
    "E34": {"es": "Otros trastornos endocrinos", "en": "Other endocrine disorders"},
    "E44": {"es": "Desnutrición proteicocalórica moderada", "en": "Protein-energy malnutrition of moderate and mild degree"},
    "E46": {"es": "Desnutrición proteicocalórica no especificada", "en": "Unspecified protein-energy malnutrition"},
    "E66": {"es": "Obesidad", "en": "Obesity"},
    "E78": {"es": "Trastornos del metabolismo de lipoproteínas", "en": "Disorders of lipoprotein metabolism and other lipidaemias"},
    "E86": {"es": "Depleción de volumen", "en": "Volume depletion"},
    "E87": {"es": "Otros trastornos hidroelectrolíticos", "en": "Other disorders of fluid, electrolyte and acid-base balance"},
    "F06": {"es": "Otros trastornos mentales por lesión cerebral", "en": "Other mental disorders due to brain damage and dysfunction and to physical disease"},
    "F07": {"es": "Trastornos de personalidad por enfermedad cerebral", "en": "Personality and behavioural disorders due to brain disease, damage and dysfunction"},
    "F09": {"es": "Trastorno mental orgánico no especificado", "en": "Unspecified organic or symptomatic mental disorder"},
    "F10": {"es": "Trastornos por uso de alcohol", "en": "Mental and behavioural disorders due to use of alcohol"},
    "F12": {"es": "Trastornos por uso de cannabinoides", "en": "Mental and behavioural disorders due to use of cannabinoids"},
    "F19": {"es": "Uso de múltiples drogas", "en": "Mental and behavioural disorders due to multiple drug use"},
    "F20": {"es": "Esquizofrenia", "en": "Schizophrenia"},
    "F23": {"es": "Trastornos psicóticos agudos", "en": "Acute and transient psychotic disorders"},
    "F25": {"es": "Trastornos esquizoafectivos", "en": "Schizoaffective disorders"},
    "F29": {"es": "Psicosis no orgánica no especificada", "en": "Unspecified nonorganic psychosis"},
    "F31": {"es": "Trastorno afectivo bipolar", "en": "Bipolar affective disorder"},
    "F32": {"es": "Episodio depresivo", "en": "Depressive episode"},
    "F33": {"es": "Trastorno depresivo recurrente", "en": "Recurrent depressive disorder"},
    "F41": {"es": "Otros trastornos de ansiedad", "en": "Other anxiety disorders"},
    "F43": {"es": "Reacción a estrés grave y adaptación", "en": "Reaction to severe stress, and adjustment disorders"},
    "F50": {"es": "Trastornos de la ingestión de alimentos", "en": "Eating disorders"},
    "F51": {"es": "Trastornos no orgánicos del sueño", "en": "Nonorganic sleep disorders"},
    "F60": {"es": "Trastornos específicos de la personalidad", "en": "Specific personality disorders"},
    "F63": {"es": "Trastornos de los hábitos e impulsos", "en": "Habit and impulse disorders"},
    "F70": {"es": "Retraso mental leve", "en": "Mild mental retardation"},
    "F71": {"es": "Retraso mental moderado", "en": "Moderate mental retardation"},
    "F72": {"es": "Retraso mental grave", "en": "Severe mental retardation"},
    "F73": {"es": "Retraso mental profundo", "en": "Profound mental retardation"},
    "F79": {"es": "Retraso mental no especificado", "en": "Unspecified mental retardation"},
    "F80": {"es": "Trastornos del desarrollo del habla y lenguaje", "en": "Specific developmental disorders of speech and language"},
    "F81": {"es": "Trastornos del aprendizaje escolar", "en": "Specific developmental disorders of scholastic skills"},
    "F82": {"es": "Trastorno del desarrollo de la función motriz", "en": "Specific developmental disorder of motor function"},
    "F83": {"es": "Trastornos mixtos del desarrollo", "en": "Mixed specific developmental disorders"},
    "F88": {"es": "Otros trastornos del desarrollo psicológico", "en": "Other disorders of psychological development"},
    "F89": {"es": "Trastorno del desarrollo psicológico no especificado", "en": "Unspecified disorder of psychological development"},
    "F90": {"es": "Trastornos hipercinéticos", "en": "Hyperkinetic disorders"},
    "F91": {"es": "Trastornos de la conducta", "en": "Conduct disorders"},
    "F92": {"es": "Trastornos mixtos de conducta y emociones", "en": "Mixed disorders of conduct and emotions"},
    "F93": {"es": "Trastornos emocionales de la infancia", "en": "Emotional disorders with onset specific to childhood"},
    "F94": {"es": "Trastornos del funcionamiento social infantil", "en": "Disorders of social functioning with onset specific to childhood"},
    "F95": {"es": "Trastornos por tics", "en": "Tic disorders"},
    "F98": {"es": "Otros trastornos emocionales y de conducta infantiles", "en": "Other behavioural and emotional disorders with onset in childhood"},
    "G12": {"es": "Atrofia muscular espinal", "en": "Spinal muscular atrophy and related syndromes"},
    "G24": {"es": "Distonía", "en": "Dystonia"},
    "G25": {"es": "Otros trastornos extrapiramidales y del movimiento", "en": "Other extrapyramidal and movement disorders"},
    "G40": {"es": "Epilepsia", "en": "Epilepsy"},
    "G41": {"es": "Estado epiléptico", "en": "Status epilepticus"},
    "G43": {"es": "Migraña", "en": "Migraine"},
    "G47": {"es": "Trastornos del sueño", "en": "Sleep disorders"},
    "G71": {"es": "Trastornos musculares primarios", "en": "Primary disorders of muscles"},
    "G80": {"es": "Parálisis cerebral", "en": "Cerebral palsy"},
    "G91": {"es": "Hidrocefalia", "en": "Hydrocephalus"},
    "G93": {"es": "Otros trastornos del encéfalo", "en": "Other disorders of brain"},
    "G96": {"es": "Otros trastornos del sistema nervioso central", "en": "Other disorders of central nervous system"},
    "H10": {"es": "Conjuntivitis", "en": "Conjunctivitis"},
    "H26": {"es": "Otras cataratas", "en": "Other cataract"},
    "H50": {"es": "Otros estrabismos", "en": "Other strabismus"},
    "H52": {"es": "Trastornos de la acomodación y refracción", "en": "Disorders of refraction and accommodation"},
    "H65": {"es": "Otitis media no supurativa", "en": "Nonsuppurative otitis media"},
    "H66": {"es": "Otitis media supurativa", "en": "Suppurative and unspecified otitis media"},
    "H90": {"es": "Hipoacusia conductiva y neurosensorial", "en": "Conductive and sensorineural hearing loss"},
    "H91": {"es": "Otras hipoacusias", "en": "Other hearing loss"},
    "I10": {"es": "Hipertensión esencial", "en": "Essential (primary) hypertension"},
    "I47": {"es": "Taquicardia paroxística", "en": "Paroxysmal tachycardia"},
    "J05": {"es": "Laringitis obstructiva aguda", "en": "Acute obstructive laryngitis [croup] and epiglottitis"},
    "J06": {"es": "Infección respiratoria superior aguda", "en": "Acute upper respiratory infections of multiple and unspecified sites"},
    "J12": {"es": "Neumonía viral", "en": "Viral pneumonia, not elsewhere classified"},
    "J15": {"es": "Neumonía bacteriana", "en": "Bacterial pneumonia, not elsewhere classified"},
    "J18": {"es": "Neumonía, organismo no especificado", "en": "Pneumonia, organism unspecified"},
    "J20": {"es": "Bronquitis aguda", "en": "Acute bronchitis"},
    "J21": {"es": "Bronquiolitis aguda", "en": "Acute bronchiolitis"},
    "J22": {"es": "Infección respiratoria inferior aguda", "en": "Unspecified acute lower respiratory infection"},
    "J30": {"es": "Rinitis alérgica y vasomotora", "en": "Vasomotor and allergic rhinitis"},
    "J35": {"es": "Enfermedades crónicas de amígdalas y adenoides", "en": "Chronic diseases of tonsils and adenoids"},
    "J45": {"es": "Asma", "en": "Asthma"},
    "J46": {"es": "Estado asmático", "en": "Status asthmaticus"},
    "J96": {"es": "Insuficiencia respiratoria", "en": "Respiratory failure, not elsewhere classified"},
    "J98": {"es": "Otros trastornos respiratorios", "en": "Other respiratory disorders"},
    "K00": {"es": "Trastornos del desarrollo dentario", "en": "Disorders of tooth development and eruption"},
    "K01": {"es": "Dientes incluidos e impactados", "en": "Embedded and impacted teeth"},
    "K02": {"es": "Caries dental", "en": "Dental caries"},
    "K04": {"es": "Enfermedades de la pulpa y periapicales", "en": "Diseases of pulp and periapical tissues"},
    "K08": {"es": "Otros trastornos de dientes y estructuras", "en": "Other disorders of teeth and supporting structures"},
    "K21": {"es": "Enfermedad por reflujo gastroesofágico", "en": "Gastro-oesophageal reflux disease"},
    "K29": {"es": "Gastritis y duodenitis", "en": "Gastritis and duodenitis"},
    "K35": {"es": "Apendicitis aguda", "en": "Acute appendicitis"},
    "K40": {"es": "Hernia inguinal", "en": "Inguinal hernia"},
    "K52": {"es": "Otras gastroenteritis y colitis", "en": "Other noninfective gastroenteritis and colitis"},
    "K56": {"es": "Íleo paralítico y obstrucción intestinal", "en": "Paralytic ileus and intestinal obstruction without hernia"},
    "K59": {"es": "Otros trastornos funcionales del intestino", "en": "Other functional intestinal disorders"},
    "K80": {"es": "Colelitiasis", "en": "Cholelithiasis"},
    "K92": {"es": "Otras enfermedades del sistema digestivo", "en": "Other diseases of digestive system"},
    "L02": {"es": "Absceso cutáneo, furúnculo y ántrax", "en": "Cutaneous abscess, furuncle and carbuncle"},
    "L03": {"es": "Celulitis", "en": "Cellulitis"},
    "L20": {"es": "Dermatitis atópica", "en": "Atopic dermatitis"},
    "M41": {"es": "Escoliosis", "en": "Scoliosis"},
    "M79": {"es": "Otros trastornos de tejidos blandos", "en": "Other soft tissue disorders, not elsewhere classified"},
    "N10": {"es": "Nefritis tubulointersticial aguda", "en": "Acute tubulo-interstitial nephritis"},
    "N39": {"es": "Otros trastornos del sistema urinario", "en": "Other disorders of urinary system"},
    "N43": {"es": "Hidrocele y espermatocele", "en": "Hydrocele and spermatocele"},
    "N45": {"es": "Orquitis y epididimitis", "en": "Orchitis and epididymitis"},
    "N47": {"es": "Prepucio redundante, fimosis y parafimosis", "en": "Redundant prepuce, phimosis and paraphimosis"},
    "O34": {"es": "Atención materna por anormalidad de órganos pélvicos", "en": "Maternal care for known or suspected abnormality of pelvic organs"},
    "O80": {"es": "Parto único espontáneo", "en": "Single spontaneous delivery"},
    "O82": {"es": "Parto único por cesárea", "en": "Single delivery by caesarean section"},
    "P07": {"es": "Trastornos relacionados con gestación corta y bajo peso", "en": "Disorders related to short gestation and low birth weight"},
    "Q38": {"es": "Malformaciones de lengua, boca y faringe", "en": "Other congenital malformations of tongue, mouth and pharynx"},
    "Q87": {"es": "Otros síndromes de malformaciones congénitas", "en": "Other specified congenital malformation syndromes affecting multiple systems"},
    "Q89": {"es": "Otras malformaciones congénitas", "en": "Other congenital malformations, not elsewhere classified"},
    "Q90": {"es": "Síndrome de Down", "en": "Down syndrome"},
    "Q99": {"es": "Otras anomalías cromosómicas", "en": "Other chromosome abnormalities, not elsewhere classified"},
    "R06": {"es": "Anormalidades de la respiración", "en": "Abnormalities of breathing"},
    "R09": {"es": "Otros síntomas respiratorios", "en": "Other symptoms and signs involving the circulatory and respiratory systems"},
    "R10": {"es": "Dolor abdominal", "en": "Abdominal and pelvic pain"},
    "R11": {"es": "Náusea y vómito", "en": "Nausea and vomiting"},
    "R41": {"es": "Síntomas cognitivos", "en": "Other symptoms and signs involving cognitive functions and awareness"},
    "R45": {"es": "Síntomas del estado emocional", "en": "Symptoms and signs involving emotional state"},
    "R46": {"es": "Síntomas de apariencia y comportamiento", "en": "Symptoms and signs involving appearance and behaviour"},
    "R47": {"es": "Trastornos del habla", "en": "Speech disturbances, not elsewhere classified"},
    "R48": {"es": "Dislexia y otras disfunciones simbólicas", "en": "Dyslexia and other symbolic dysfunctions, not elsewhere classified"},
    "R50": {"es": "Fiebre", "en": "Fever of other and unknown origin"},
    "R56": {"es": "Convulsiones", "en": "Convulsions, not elsewhere classified"},
    "R62": {"es": "Retardo del desarrollo esperado", "en": "Lack of expected normal physiological development"},
    "R63": {"es": "Síntomas de ingestión de alimentos y líquidos", "en": "Symptoms and signs concerning food and fluid intake"},
    "S00": {"es": "Traumatismo superficial de la cabeza", "en": "Superficial injury of head"},
    "S01": {"es": "Herida de la cabeza", "en": "Open wound of head"},
    "S02": {"es": "Fractura de huesos del cráneo y cara", "en": "Fracture of skull and facial bones"},
    "S06": {"es": "Traumatismo intracraneal", "en": "Intracranial injury"},
    "S32": {"es": "Fractura de columna lumbar y pelvis", "en": "Fracture of lumbar spine and pelvis"},
    "S42": {"es": "Fractura del hombro y brazo", "en": "Fracture of shoulder and upper arm"},
    "S52": {"es": "Fractura del antebrazo", "en": "Fracture of forearm"},
    "S61": {"es": "Herida de muñeca y mano", "en": "Open wound of wrist and hand"},
    "S62": {"es": "Fractura a nivel de la muñeca y mano", "en": "Fracture at wrist and hand level"},
    "S72": {"es": "Fractura del fémur", "en": "Fracture of femur"},
    "S82": {"es": "Fractura de pierna y tobillo", "en": "Fracture of lower leg, including ankle"},
    "T14": {"es": "Traumatismo de región no especificada", "en": "Injury of unspecified body region"},
    "T17": {"es": "Cuerpo extraño en vías respiratorias", "en": "Foreign body in respiratory tract"},
    "T18": {"es": "Cuerpo extraño en tubo digestivo", "en": "Foreign body in alimentary tract"},
    "T30": {"es": "Quemadura de región no especificada", "en": "Burn and corrosion, body region unspecified"},
    "T36": {"es": "Envenenamiento por antibióticos sistémicos", "en": "Poisoning by systemic antibiotics"},
    "T39": {"es": "Envenenamiento por analgésicos no opiáceos", "en": "Poisoning by nonopioid analgesics, antipyretics and antirheumatics"},
    "T42": {"es": "Envenenamiento por antiepilépticos, sedantes e hipnóticos", "en": "Poisoning by antiepileptic, sedative-hypnotic and antiparkinsonism drugs"},
    "T43": {"es": "Envenenamiento por psicotrópicos", "en": "Poisoning by psychotropic drugs, not elsewhere classified"},
    "T50": {"es": "Envenenamiento por otros medicamentos", "en": "Poisoning by diuretics and other and unspecified drugs and medicaments"},
    "T78": {"es": "Efectos adversos no clasificados", "en": "Adverse effects, not elsewhere classified"},
    "U07": {"es": "COVID-19", "en": "COVID-19"},
    "W01": {"es": "Caída en el mismo nivel", "en": "Fall on same level from slipping, tripping and stumbling"},
    "W10": {"es": "Caída en o desde escaleras", "en": "Fall on and from stairs and steps"},
    "W18": {"es": "Otras caídas en el mismo nivel", "en": "Other fall on same level"},
    "W19": {"es": "Caída no especificada", "en": "Unspecified fall"},
    "X60": {"es": "Envenenamiento autoinfligido por analgésicos", "en": "Intentional self-poisoning by nonopioid analgesics, antipyretics and antirheumatics"},
    "X61": {"es": "Envenenamiento autoinfligido por psicotrópicos", "en": "Intentional self-poisoning by antiepileptic, sedative-hypnotic and psychotropic drugs"},
    "X62": {"es": "Envenenamiento autoinfligido por narcóticos", "en": "Intentional self-poisoning by narcotics and psychodysleptics"},
    "X64": {"es": "Envenenamiento autoinfligido por otras drogas", "en": "Intentional self-poisoning by other and unspecified drugs and medicaments"},
    "X70": {"es": "Lesión autoinfligida por ahorcamiento", "en": "Intentional self-harm by hanging, strangulation and suffocation"},
    "X78": {"es": "Lesión autoinfligida por objeto cortante", "en": "Intentional self-harm by sharp object"},
    "X84": {"es": "Lesión autoinfligida por medios no especificados", "en": "Intentional self-harm by unspecified means"},
    "Y83": {"es": "Complicaciones de intervención quirúrgica", "en": "Surgical operation and other surgical procedures as the cause of abnormal reaction of the patient"},
    "Y84": {"es": "Complicaciones de otros procedimientos", "en": "Other medical procedures as the cause of abnormal reaction of the patient"},
    "Y92": {"es": "Lugar de ocurrencia", "en": "Place of occurrence of the external cause"},
    "Z00": {"es": "Examen general", "en": "General examination and investigation of persons without complaint or reported diagnosis"},
    "Z01": {"es": "Otros exámenes especiales", "en": "Other special examinations and investigations of persons without complaint or reported diagnosis"},
    "Z03": {"es": "Observación por sospecha", "en": "Medical observation and evaluation for suspected diseases and conditions"},
    "Z04": {"es": "Examen y observación por otras razones", "en": "Examination and observation for other reasons"},
    "Z51": {"es": "Otra atención médica", "en": "Other medical care"},
    "Z53": {"es": "Atención no realizada", "en": "Persons encountering health services for specific procedures, not carried out"},
    "Z61": {"es": "Problemas relacionados con hechos negativos en la niñez", "en": "Problems related to negative life events in childhood"},
    "Z62": {"es": "Problemas relacionados con la crianza", "en": "Other problems related to upbringing"},
    "Z63": {"es": "Problemas relacionados con el grupo de apoyo primario", "en": "Other problems related to primary support group, including family circumstances"},
    "Z65": {"es": "Problemas psicosociales", "en": "Problems related to other psychosocial circumstances"},
    "Z71": {"es": "Consulta y consejo", "en": "Persons encountering health services for other counselling and medical advice"},
    "Z73": {"es": "Problemas relacionados con dificultades de la vida", "en": "Problems related to life-management difficulty"},
    "Z74": {"es": "Problemas relacionados con dependencia del cuidador", "en": "Problems related to care-provider dependency"},
    "Z75": {"es": "Problemas relacionados con facilidades de atención", "en": "Problems related to medical facilities and other health care"},
    "Z76": {"es": "Contacto con servicios de salud en otras circunstancias", "en": "Persons encountering health services in other circumstances"},
    "Z80": {"es": "Historia familiar de neoplasia", "en": "Family history of malignant neoplasm"},
    "Z81": {"es": "Historia familiar de trastornos mentales", "en": "Family history of mental and behavioural disorders"},
    "Z82": {"es": "Historia familiar de discapacidades", "en": "Family history of certain disabilities and chronic diseases"},
    "Z86": {"es": "Historia personal de otras enfermedades", "en": "Personal history of certain other diseases"},
    "Z87": {"es": "Historia personal de otras enfermedades", "en": "Personal history of other diseases and conditions"},
    "Z88": {"es": "Historia personal de alergia", "en": "Personal history of allergy to drugs, medicaments and biological substances"},
    "Z91": {"es": "Historia personal de factores de riesgo", "en": "Personal history of risk-factors, not elsewhere classified"},
    "Z92": {"es": "Historia personal de tratamiento médico", "en": "Personal history of medical treatment"},
    "Z96": {"es": "Presencia de implantes funcionales", "en": "Presence of other functional implants"},
    "Z98": {"es": "Otros estados posquirúrgicos", "en": "Other postprocedural states"},
    "Z99": {"es": "Dependencia de máquinas y dispositivos", "en": "Dependence on enabling machines and devices, not elsewhere classified"},
}

#: Capítulos CIE-10 (rangos de tres caracteres, inclusive) en los dos idiomas.
ICD10_CHAPTERS: list[tuple[str, str, dict[str, str]]] = [
    ("A00", "B99", {"es": "Infecciosas y parasitarias", "en": "Certain infectious and parasitic diseases"}),
    ("C00", "D48", {"es": "Neoplasias", "en": "Neoplasms"}),
    ("D50", "D89", {"es": "Sangre e inmunidad", "en": "Blood, blood-forming organs and immune mechanism"}),
    ("E00", "E90", {"es": "Endocrinas, nutricionales y metabólicas", "en": "Endocrine, nutritional and metabolic diseases"}),
    ("F00", "F99", {"es": "Trastornos mentales y del comportamiento", "en": "Mental and behavioural disorders"}),
    ("G00", "G99", {"es": "Sistema nervioso", "en": "Nervous system"}),
    ("H00", "H59", {"es": "Ojo y anexos", "en": "Eye and adnexa"}),
    ("H60", "H95", {"es": "Oído y apófisis mastoides", "en": "Ear and mastoid process"}),
    ("I00", "I99", {"es": "Sistema circulatorio", "en": "Circulatory system"}),
    ("J00", "J99", {"es": "Sistema respiratorio", "en": "Respiratory system"}),
    ("K00", "K93", {"es": "Sistema digestivo", "en": "Digestive system"}),
    ("L00", "L99", {"es": "Piel y tejido subcutáneo", "en": "Skin and subcutaneous tissue"}),
    ("M00", "M99", {"es": "Osteomuscular y tejido conectivo", "en": "Musculoskeletal system and connective tissue"}),
    ("N00", "N99", {"es": "Sistema genitourinario", "en": "Genitourinary system"}),
    ("O00", "O99", {"es": "Embarazo, parto y puerperio", "en": "Pregnancy, childbirth and the puerperium"}),
    ("P00", "P96", {"es": "Afecciones del período perinatal", "en": "Certain conditions originating in the perinatal period"}),
    ("Q00", "Q99", {"es": "Malformaciones congénitas", "en": "Congenital malformations and chromosomal abnormalities"}),
    ("R00", "R99", {"es": "Síntomas y signos no clasificados", "en": "Symptoms, signs and abnormal findings not elsewhere classified"}),
    ("S00", "T98", {"es": "Traumatismos y envenenamientos", "en": "Injury, poisoning and other consequences of external causes"}),
    ("V01", "Y98", {"es": "Causas externas", "en": "External causes of morbidity and mortality"}),
    ("Z00", "Z99", {"es": "Factores que influyen en el estado de salud", "en": "Factors influencing health status and contact with health services"}),
]

#: Bloques de salud mental (F00–F99) en los dos idiomas.
ICD10_MENTAL_BLOCKS: list[tuple[str, str, dict[str, str]]] = [
    ("F00", "F09", {"es": "Trastornos mentales orgánicos", "en": "Organic mental disorders"}),
    ("F10", "F19", {"es": "Uso de sustancias psicoactivas", "en": "Psychoactive substance use"}),
    ("F20", "F29", {"es": "Esquizofrenia y psicosis", "en": "Schizophrenia and psychotic disorders"}),
    ("F30", "F39", {"es": "Trastornos del ánimo", "en": "Mood (affective) disorders"}),
    ("F40", "F48", {"es": "Ansiedad, estrés y somatomorfos", "en": "Anxiety, stress-related and somatoform disorders"}),
    ("F50", "F59", {"es": "Síndromes conductuales fisiológicos", "en": "Behavioural syndromes with physiological disturbances"}),
    ("F60", "F69", {"es": "Personalidad y comportamiento adulto", "en": "Adult personality and behaviour"}),
    ("F70", "F79", {"es": "Discapacidad intelectual", "en": "Intellectual disability"}),
    ("F80", "F83", {"es": "Desarrollo del habla, aprendizaje y motor", "en": "Speech, scholastic and motor development"}),
    ("F84", "F84", {"es": "Trastornos generalizados del desarrollo", "en": "Pervasive developmental disorders"}),
    ("F88", "F89", {"es": "Otros trastornos del desarrollo psicológico", "en": "Other disorders of psychological development"}),
    ("F90", "F90", {"es": "Trastornos hipercinéticos", "en": "Hyperkinetic disorders"}),
    ("F91", "F98", {"es": "Conducta y emociones de inicio en la infancia", "en": "Behavioural and emotional disorders with onset in childhood"}),
    ("F99", "F99", {"es": "Trastorno mental no especificado", "en": "Unspecified mental disorder"}),
]

#: Etiqueta que se imprime cuando el bloque de salud mental no aplica (código fuera de F).
NOT_F_BLOCK = {"es": "No F", "en": "Not F"}


def icd_label(code3, lang: str) -> str:
    """Glosa de la categoría CIE-10 de tres caracteres en `lang`, o «» si no la hay en ese idioma."""
    return ICD10.get(str(code3).strip().upper(), {}).get(lang, "")


def icd_code_label(code3, lang: str, sep: str = " — ") -> str:
    """«J45 — Asma» / «J45 — Asthma»; el código solo cuando no hay glosa en el idioma pedido."""
    code = str(code3).strip().upper()
    label = icd_label(code, lang)
    return f"{code}{sep}{label}" if label else code


def _in_range(code3: str, start: str, end: str) -> bool:
    return bool(code3) and start <= code3[:3] <= end


def icd_chapter(code3, lang: str) -> str:
    """Capítulo CIE-10 del código, en `lang`; «» si el código no cae en ningún capítulo."""
    code = str(code3).strip().upper()[:3]
    for start, end, label in ICD10_CHAPTERS:
        if _in_range(code, start, end):
            return label[lang]
    return ""


def icd_mental_block(code3, lang: str) -> str:
    """Bloque de salud mental del código, en `lang`; `NOT_F_BLOCK` si no es un código F."""
    code = str(code3).strip().upper()[:3]
    for start, end, label in ICD10_MENTAL_BLOCKS:
        if _in_range(code, start, end):
            return label[lang]
    return NOT_F_BLOCK[lang]


def icd_chapter_es_to(label_es: str, lang: str) -> str:
    """Traduce una glosa de capítulo o de bloque ya escrita en español (columna tidy) a `lang`."""
    s = str(label_es).strip()
    for _, _, label in ICD10_CHAPTERS + ICD10_MENTAL_BLOCKS:
        if s == label["es"]:
            return label[lang]
    if s == NOT_F_BLOCK["es"]:
        return NOT_F_BLOCK[lang]
    return tidy_text(s, lang)


# ===========================================================================
# Detector reutilizable de fuga de idioma
# ===========================================================================
"""Cómo funciona.

Una cadena que llega a un documento está «limpia» cuando no contiene palabras funcionales del OTRO
idioma. El detector no traduce ni adivina: cuenta palabras marcadoras —artículos, preposiciones,
conjuntivos y auxiliares que no existen en el otro idioma— después de retirar todo lo que no es prosa:

  * identificadores técnicos (`n_students`, `EXP_REG`, `D15_11`), rutas, nombres de archivo y URL;
  * nombres propios de varias palabras (regiones, comunas, instituciones, sedes de encuestas), que en
    los dos idiomas se escriben en español: «Magallanes y de la Antártica Chilena», «Junta Nacional de
    Auxilio Escolar y Becas»;
  * el texto que la propia tabla declara como transcripción literal de la fuente (columna rotulada
    «verbatim Spanish», nota que dice que un campo se transcribe sin traducir, o el fragmento de una
    celda que va después de «Original Spanish wording:»).

Se marca fuga cuando quedan `threshold` o más marcadores del idioma equivocado y son más que los del
idioma del documento. `language_leak` devuelve `None` cuando la cadena está limpia y un diccionario
con los marcadores encontrados cuando no lo está, de modo que el mensaje de la prueba diga por qué.
"""
import re as _re
import unicodedata as _ud

#: Palabras funcionales que solo existen en español.
LEAK_ES_MARKERS = frozenset("""
de la el los las un una unos unas del al y en con por para sin sobre entre que se su sus es son era
fue fueron ser estar está están hay ha han como cada todo toda todos todas mismo misma mismos mismas
solo sólo más menos año años según número nunca siempre donde cuando porque desde hasta también
tampoco pero aunque esta este estos estas esa ese esos esas cual cuales quien quienes lo le les tiene
tienen puede pueden debe deben ni ya muy otro otra otros otras sino ambos ambas cuyo cuya cuyas cuyos
sólo aquí allí ninguna ninguno alguna alguno algunas algunos dentro fuera además sino mediante
""".split())

#: Palabras funcionales que solo existen en inglés.
LEAK_EN_MARKERS = frozenset("""
the and with of for from are is was were not never by which that this these those each both only
between under within without per every its their when where because however also than then such been
being has have had does do did should would could may might must into onto upon about after before
during through across over above below against among while although though whether other another same
different they we our it as at on to an but all any more most less few fewer always still here there
what who whose how why so if none neither either each-of themselves itself
""".split())

#: Nombres propios y locuciones que se escriben igual en los dos idiomas (no son fuga).
LEAK_PROPER_NOUNS: tuple[str, ...] = (
    "Magallanes y de la Antártica Chilena", "Libertador General Bernardo O'Higgins",
    "Aysén del General Carlos Ibáñez del Campo", "Arica y Parinacota", "La Araucanía",
    "Región Metropolitana de Santiago", "Región Metropolitana", "Isla de Pascua", "Juan Fernández",
    "Cabo de Hornos", "Junta Nacional de Auxilio Escolar y Becas",
    "Ministerio de Salud", "Ministerio de Educación", "Ministerio de Desarrollo Social y Familia",
    "Instituto Nacional de Estadísticas", "Superintendencia de Salud",
    "Fondo Nacional de Salud", "Departamento de Estadísticas e Información de Salud",
    "Centro de Estudios MINEDUC", "Servicio de Salud", "Servicios de Salud",
    "Encuesta Nacional de Discapacidad y Dependencia", "Encuesta Nacional de Calidad de Vida",
    "Programa de Integración Escolar", "Ley 21.545", "Sin Código de Comuna", "Sin dato Comuna",
    "Trastorno del Espectro Autista", "Trastornos del Espectro Autista",
)

#: Frases con las que una columna, una nota o una celda declaran una transcripción literal.
_VERBATIM_PATTERNS = (
    r"verbatim\s+spanish", r"verbatim\s+english", r"\(verbatim\)", r"verbatim,",
    r"textual(?:es)?\s+en\s+(?:español|inglés)", r"literal(?:es)?\s+en\s+(?:español|inglés)",
    r"original\s+spanish\s+wording", r"redacci[óo]n\s+original\s+en\s+espa[ñn]ol",
    r"deliberately\s+not\s+translated", r"no\s+se\s+traducen",
    r"transcrib\w*\s+(?:en\s+ingl[ée]s|as\s+recorded|verbatim)",
    r"se\s+transcriben\s+en\s+ingl[ée]s",
)
_VERBATIM_RE = _re.compile("|".join(_VERBATIM_PATTERNS), _re.IGNORECASE)

_WORD_RE = _re.compile(r"[^\W\d_]+", _re.UNICODE)
_CAP_RE = _re.compile(r"[A-ZÁÉÍÓÚÜÑ]")


def declares_verbatim(text) -> bool:
    """True si el encabezado, la nota o la celda declaran que el texto es transcripción literal."""
    return bool(_VERBATIM_RE.search(str(text or "")))


def _strip_technical(text: str) -> str:
    """Quita identificadores, rutas, archivos, siglas y todo lo que lleve dígitos o guion bajo."""
    out = []
    for token in str(text).split():
        bare = token.strip("()[]{}«»\"'“”‘’,;:.¿?¡!—–-")
        if not bare:
            continue
        if "_" in bare or "/" in bare or "\\" in bare or "=" in bare:
            continue
        if any(ch.isdigit() for ch in bare):
            continue
        letters = [c for c in bare if c.isalpha()]
        if letters and all(c.isupper() for c in letters) and len(letters) > 1:
            continue
        out.append(token)
    return " ".join(out)


def _strip_proper_nouns(text: str) -> str:
    """Quita los nombres propios declarados y las secuencias de TRES o más palabras capitalizadas unidas
    por conectores («Magallanes y de la Antártica Chilena», «Hospital de Niños Roberto del Río»).

    El umbral de tres evita comerse el arranque de una frase —«No — No estimable: el cuestionario…»,
    donde dos mayúsculas seguidas son puntuación, no un nombre propio— sin dejar pasar los nombres de
    región, comuna o institución, que siempre llevan tres o más palabras capitalizadas."""
    s = str(text)
    for name in LEAK_PROPER_NOUNS:
        s = s.replace(name, " ")
    tokens = s.split()
    connectors = {"y", "e", "o", "u", "de", "del", "la", "las", "los", "el", "al",
                  "and", "of", "the", "for", "in", "on"}

    def capitalised(tok: str) -> bool:
        bare = tok.strip("()[]{}«»\"'“”‘’,;:.¿?¡!—–-")
        return bool(bare) and bool(_CAP_RE.match(bare))

    keep = [True] * len(tokens)
    i = 0
    while i < len(tokens):
        if not capitalised(tokens[i]):
            i += 1
            continue
        j, last_cap = i + 1, i
        while j < len(tokens):
            if capitalised(tokens[j]):
                last_cap, j = j, j + 1
            elif tokens[j].lower().strip(",;:.") in connectors:
                j += 1
            else:
                break
        capitals = sum(1 for k in range(i, last_cap + 1) if capitalised(tokens[k]))
        if capitals >= 3:                      # al menos tres palabras capitalizadas encadenadas
            for k in range(i, last_cap + 1):
                keep[k] = False
        i = max(j, i + 1)
    return " ".join(tok for tok, k in zip(tokens, keep) if k)


def _strip_declared_quote(text: str) -> str:
    """Corta la cadena en la declaración de transcripción literal que ella misma contenga."""
    m = _VERBATIM_RE.search(str(text))
    return str(text)[:m.start()] if m else str(text)


#: Marcadores de estado y de encabezado que el pipeline escribe en UN idioma y que, si aparecen en el
#: documento del otro, son fuga por sí solos: son demasiado cortos para llegar al umbral de tres palabras
#: funcionales («ABSENT», «n/a», «Outcome») y ninguno es una cita literal de la fuente, de modo que una
#: declaración de transcripción NO los exime. La revisión página a página los contó 596 veces en el
#: suplemento español (544 en la Tabla S14, 370 «n/a» en la S31, 137 «Outcome», 44 «ABSENT», 5 «MISSING»).
PLACEHOLDER_MARKERS: dict[str, tuple[str, ...]] = {
    # prohibidos dentro del documento en español
    "es": ("ABSENT", "MISSING", "Outcome", "n/a", "N/A", "not listed", "no date", "not applicable",
           "not reported", "not estimable", "not published", "no data", "not recorded", "not identified"),
    # prohibidos dentro del documento en inglés
    "en": ("ausente", "no informado", "no reportado", "no estimable", "no publicado", "no aplica",
           "sin dato", "sin fecha", "no listado", "desconocido", "vacío"),
}
#: Un marcador vale como fuga solo si va suelto: ni dentro de un identificador (`enrolled_tramo_missing`),
#: ni dentro de una ruta o de una lista de columnas separada por barras.
_MARKER_BOUNDARY = r"(?<![\w_./|\-])%s(?![\w_./|\-])"


def marker_leak(text, lang: str) -> list[str]:
    """Marcadores del idioma equivocado hallados sueltos en `text` (lista vacía si no hay ninguno)."""
    if lang not in PLACEHOLDER_MARKERS:
        raise ValueError(f"idioma desconocido: {lang!r}")
    s = str(text or "")
    return [m for m in PLACEHOLDER_MARKERS[lang]
            if _re.search(_MARKER_BOUNDARY % _re.escape(m), s)]


def language_markers(text, lang: str) -> tuple[list[str], list[str]]:
    """(marcadores del idioma equivocado, marcadores del idioma del documento) de una cadena."""
    prepared = _strip_technical(_strip_proper_nouns(_strip_declared_quote(text)))
    words = [w.lower() for w in _WORD_RE.findall(prepared)]
    es = [w for w in words if w in LEAK_ES_MARKERS]
    en = [w for w in words if w in LEAK_EN_MARKERS]
    return (es, en) if lang == "en" else (en, es)


def language_leak(text, lang: str, context: str = "", threshold: int = 3) -> dict | None:
    """Fuga de idioma de `text` en un documento escrito en `lang` (`'es'` o `'en'`).

    `context` es el encabezado de la columna y la nota de la tabla: si declaran transcripción literal
    («verbatim Spanish», «se transcriben en inglés»), la celda no es fuga. Devuelve `None` si está
    limpia, o `{'lang', 'wrong', 'right', 'text'}` con los marcadores hallados si no lo está.
    """
    if lang not in ("es", "en"):
        raise ValueError(f"idioma desconocido: {lang!r}")
    s = str(text or "").strip()
    if not s:
        return None
    markers = marker_leak(s, lang)
    if markers:                    # un marcador de estado nunca es cita literal: la declaración no exime
        return {"lang": lang, "wrong": markers, "right": [], "text": s}
    if declares_verbatim(context):
        return None
    wrong, right = language_markers(s, lang)
    if len(wrong) >= threshold and len(wrong) > len(right):
        return {"lang": lang, "wrong": wrong, "right": right, "text": s}
    return None


# ===========================================================================
# Glosario de impresión — la forma que el LECTOR ve, escrita UNA sola vez
# ===========================================================================
"""Dos clases de defecto de vocabulario habían sobrevivido a tres lecturas porque cada módulo escribía
su propia forma: un anglicismo suelto en prosa española («crosswalk», 1 vez en el artículo y 45 en el
manuscrito combinado, medido sobre el DOCX del 2026-09-08) y un par de apellidos escrito con guion en
unas láminas y con raya corta en las demás («Getis-Ord» contra «Getis–Ord», 24 contra 32 en el corpus).

La regla se escribe aquí, una vez, y se aplica en el ÚNICO embudo por el que pasa todo lo que el lector
lee —los bloques del documento en `10_manuscript.build_pair`: párrafos, títulos, entradillas, leyendas,
notas, encabezados de columna y CELDAS de las 125 tablas—, de modo que ningún módulo tiene que declarar
su propia forma y ninguno puede quedarse atrás. `printed_text` es idempotente: aplicarla dos veces da lo
mismo que aplicarla una.

Qué NO toca, y por qué. El anglicismo se traduce sólo en la PROSA: los identificadores de máquina que el
papel imprime tal cual —`comuna_crosswalk.csv`, `ST4a_comuna_crosswalk_summary`,
`censo2024_comunas_not_in_crosswalk`, `cartography_comunas_vs_crosswalk`— se cruzan carácter a carácter
con `outputs/` y con los controles, y traducirlos rompería esa traza; por eso el patrón exige que la
palabra no lleve pegado `_`, `/` ni `-`. Y el término inglés se conserva ENTERO en los documentos
en inglés: la regla del anglicismo es de idioma («es»), la del par de apellidos es de ortografía y vale
en los dos.

El PUNTO no se trata como los otros tres separadores, y la distinción está medida. Prohibirlo entero
dejaba pasar la única aparición que sobrevivió a la fase 4k: el encabezado español «Geografía y
crosswalk.», donde el punto es el que cierra la frase y no el de un nombre de archivo —una por
documento largo español, cuatro en el corpus, invisibles para la guarda porque `printed_leak` usa el
mismo patrón que la sustitución—. En un identificador el punto SIEMPRE lleva detrás una letra o una
cifra (`comuna_crosswalk.csv`); al final de una frase lleva un blanco, un cierre de comillas o nada.
Por eso el patrón prohíbe el punto sólo cuando le sigue un carácter de palabra: los cuatro
identificadores siguen intactos y la prosa deja de esconder el anglicismo detrás de su propio punto.
"""
#: (patrón, {idioma: forma impresa}). Un idioma ausente deja el texto intacto en ese idioma.
PRINTED_TERMS: tuple[tuple[str, dict[str, str]], ...] = (
    # anglicismo suelto en prosa española; «cuadro» es masculino, de modo que la sustitución no toca
    # el artículo que la frase ya trae («el crosswalk comunal» → «el cuadro de equivalencias comunal»),
    # y no se dice «tabla» para no confundirlo con las Tablas numeradas del propio documento.
    (r"(?<![\w./-])[Cc]rosswalk(?![\w/-])(?!\.\w)", {"es": "cuadro de equivalencias"}),
    (r"(?<![\w./-])[Cc]rosswalks(?![\w/-])(?!\.\w)", {"es": "cuadros de equivalencias"}),
    # par de apellidos: raya corta, como Fay–Feuer, Clopper–Pearson o Durbin–Watson
    (r"Getis-Ord", {"es": "Getis–Ord", "en": "Getis–Ord"}),
    # el título de Wedderburn (1974) llega del `.bib` con la raya corta; si alguna copia vuelve con raya
    # larga, se corrige al imprimir. La atadura del renglón NO se escribe aquí: la pone
    # docx_builder.compound_indivisible a los dos lados de la raya, que es lo único que evita el corte.
    (r"Gauss[—-]Newton", {"es": "Gauss–Newton", "en": "Gauss–Newton"}),
)
_PRINTED_TERMS_COMPILED = tuple((_re.compile(p), t) for p, t in PRINTED_TERMS)


def printed_text(value, lang: str):
    """El texto tal como debe imprimirse en `lang`, con el glosario de impresión aplicado.

    Devuelve el valor intacto (y del mismo tipo) si no es texto o si nada cambia, de modo que se puede
    pasar por ella cualquier celda de tabla sin mirar antes de qué tipo es.
    """
    if not isinstance(value, str) or not value:
        return value
    out = value
    for rx, forms in _PRINTED_TERMS_COMPILED:
        forma = forms.get(lang)
        if forma is None:
            continue
        out = rx.sub(lambda m, f=forma: f if m.group(0)[:1].islower() or not f[:1].isalpha()
                     else f[:1].upper() + f[1:], out)
    return out


def printed_leak(value, lang: str) -> list[str]:
    """Lo que el glosario de impresión habría cambiado y sigue ahí: la guarda que detiene la construcción."""
    if not isinstance(value, str) or not value:
        return []
    fuera = []
    for rx, forms in _PRINTED_TERMS_COMPILED:
        if forms.get(lang) is None:
            continue
        fuera += [m.group(0) for m in rx.finditer(value)]
    return fuera


# ===========================================================================
# Indicadores REM — glosa bilingüe de la columna `indicator` de las tablas tidy
# ===========================================================================
"""La columna `indicator` de `outputs/tidy/rem_pathway_annual.csv` guarda el nombre del código REM tal
como lo dejó el módulo 02: unas filas en español (las que vienen del diccionario REM) y otras en inglés
(las que el módulo redactó). Ese texto llega a las tablas y láminas de los dos idiomas, de modo que aquí
se declara la glosa en ambos. `rem_indicator(valor, idioma)` devuelve la glosa; si un indicador nuevo no
está en el diccionario devuelve el valor tal cual, y la prueba de idioma lo detecta."""

REM_INDICATOR: dict[str, dict[str, str]] = {
    "A05 ingresos a salud mental: autismo estricto": {
        "es": "A05 ingresos a salud mental: autismo estricto",
        "en": "A05 mental-health entries: strict autism"},
    "A05 ingresos a salud mental: familia TGD (F84 completo (incluye síndrome de Rett))": {
        "es": "A05 ingresos a salud mental: familia TGD (F84 completo, incluye síndrome de Rett)",
        "en": "A05 mental-health entries: PDD family (complete F84, including Rett syndrome)"},
    "A05 ingresos a salud mental: familia TGD (F84 sin síndrome de Rett)": {
        "es": "A05 ingresos a salud mental: familia TGD (F84 sin síndrome de Rett)",
        "en": "A05 mental-health entries: PDD family (F84 excluding Rett syndrome)"},
    "A05 ingresos a salud mental: trastornos generalizados del desarrollo (TGD amplio, pre-2021)": {
        "es": "A05 ingresos a salud mental: trastornos generalizados del desarrollo (TGD amplio, pre-2021)",
        "en": "A05 mental-health entries: pervasive developmental disorders (broad PDD, pre-2021)"},
    "A05 egresos (altas clínicas) a salud mental: autismo estricto": {
        "es": "A05 egresos (altas clínicas) de salud mental: autismo estricto",
        "en": "A05 mental-health exits (clinical discharges): strict autism"},
    "A05 egresos (altas clínicas) a salud mental: familia TGD (F84 completo (incluye síndrome de Rett))": {
        "es": "A05 egresos (altas clínicas) de salud mental: familia TGD (F84 completo, incluye síndrome de Rett)",
        "en": "A05 mental-health exits (clinical discharges): PDD family (complete F84, including Rett syndrome)"},
    "A05 egresos (altas clínicas) a salud mental: familia TGD (F84 sin síndrome de Rett)": {
        "es": "A05 egresos (altas clínicas) de salud mental: familia TGD (F84 sin síndrome de Rett)",
        "en": "A05 mental-health exits (clinical discharges): PDD family (F84 excluding Rett syndrome)"},
    "A05 egresos (altas clínicas) a salud mental: trastornos generalizados del desarrollo (TGD amplio, pre-2021)": {
        "es": "A05 egresos (altas clínicas) de salud mental: trastornos generalizados del desarrollo (TGD amplio, pre-2021)",
        "en": "A05 mental-health exits (clinical discharges): pervasive developmental disorders (broad PDD, pre-2021)"},
    "P6 población bajo control en APS: TGD amplio (pre-2021)": {
        "es": "P6 población bajo control en APS: TGD amplio (pre-2021)",
        "en": "P6 population under control in primary care: broad PDD (pre-2021)"},
    "P6 población bajo control en APS: autismo estricto": {
        "es": "P6 población bajo control en APS: autismo estricto",
        "en": "P6 population under control in primary care: strict autism"},
    "P6 población bajo control en APS: familia TGD (F84 completo (incluye síndrome de Rett))": {
        "es": "P6 población bajo control en APS: familia TGD (F84 completo, incluye síndrome de Rett)",
        "en": "P6 population under control in primary care: PDD family (complete F84, including Rett syndrome)"},
    "P6 población bajo control en APS: familia TGD (F84 sin síndrome de Rett)": {
        "es": "P6 población bajo control en APS: familia TGD (F84 sin síndrome de Rett)",
        "en": "P6 population under control in primary care: PDD family (F84 excluding Rett syndrome)"},
    "P6 población bajo control en especialidad: TGD amplio (pre-2021)": {
        "es": "P6 población bajo control en especialidad: TGD amplio (pre-2021)",
        "en": "P6 population under control in specialty care: broad PDD (pre-2021)"},
    "P6 población bajo control en especialidad: autismo estricto": {
        "es": "P6 población bajo control en especialidad: autismo estricto",
        "en": "P6 population under control in specialty care: strict autism"},
    "P6 población bajo control en especialidad: familia TGD (F84 completo (incluye síndrome de Rett))": {
        "es": "P6 población bajo control en especialidad: familia TGD (F84 completo, incluye síndrome de Rett)",
        "en": "P6 population under control in specialty care: PDD family (complete F84, including Rett syndrome)"},
    "P6 población bajo control en especialidad: familia TGD (F84 sin síndrome de Rett)": {
        "es": "P6 población bajo control en especialidad: familia TGD (F84 sin síndrome de Rett)",
        "en": "P6 population under control in specialty care: PDD family (F84 excluding Rett syndrome)"},
    "Alteración de lenguaje y/o área social en control de 18 meses": {
        "es": "Alteración de lenguaje y/o área social en el control de 18 meses",
        "en": "Language and/or social-area alteration at the 18-month check"},
    "Niños/as con control a los 18 meses": {
        "es": "Niños y niñas con control de salud a los 18 meses",
        "en": "Children with an 18-month health check"},
    "M-CHAT performed among children with language/social alteration": {
        "es": "M-CHAT realizado en niños y niñas con alteración de lenguaje o área social",
        "en": "M-CHAT performed among children with language or social-area alteration"},
    "Altered M-CHAT among children with language/social alteration": {
        "es": "M-CHAT alterado en niños y niñas con alteración de lenguaje o área social",
        "en": "Altered M-CHAT among children with language or social-area alteration"},
    "Suspected autism in other controls or consultations": {
        "es": "Sospecha de autismo en otros controles o consultas",
        "en": "Suspected autism in other check-ups or consultations"},
    "Autism suspicion by alert-sign guide: yes": {
        "es": "Sospecha de autismo según pauta de señales de alerta: sí",
        "en": "Autism suspicion by alert-sign guide: yes"},
    "Autism suspicion by alert-sign guide: no": {
        "es": "Sospecha de autismo según pauta de señales de alerta: no",
        "en": "Autism suspicion by alert-sign guide: no"},
    "Referral after alert-sign evaluation: yes": {
        "es": "Derivación tras la evaluación por señales de alerta: sí",
        "en": "Referral after alert-sign evaluation: yes"},
    "Referral after alert-sign evaluation: no": {
        "es": "Derivación tras la evaluación por señales de alerta: no",
        "en": "Referral after alert-sign evaluation: no"},
    "M-CHAT motive: altered EEDP language/social area in ages 16–30 months": {
        "es": "Motivo del M-CHAT: área de lenguaje o social del EEDP alterada, 16–30 meses",
        "en": "M-CHAT reason: altered EEDP language or social area, ages 16–30 months"},
    "M-CHAT motive: autism risk factor or alert sign in ages 16–30 months": {
        "es": "Motivo del M-CHAT: factor de riesgo o señal de alerta de autismo, 16–30 meses",
        "en": "M-CHAT reason: autism risk factor or alert sign, ages 16–30 months"},
    "M-CHAT motive: both altered EEDP and autism risk/alert in ages 16–30 months": {
        "es": "Motivo del M-CHAT: EEDP alterado y factor de riesgo o señal de alerta, 16–30 meses",
        "en": "M-CHAT reason: both altered EEDP and autism risk factor or alert sign, ages 16–30 months"},
    "M-CHAT-R/F first part: low risk": {
        "es": "M-CHAT-R/F primera parte: riesgo bajo", "en": "M-CHAT-R/F first part: low risk"},
    "M-CHAT-R/F first part: medium risk": {
        "es": "M-CHAT-R/F primera parte: riesgo medio", "en": "M-CHAT-R/F first part: medium risk"},
    "M-CHAT-R/F first part: high risk": {
        "es": "M-CHAT-R/F primera parte: riesgo alto", "en": "M-CHAT-R/F first part: high risk"},
    "M-CHAT-R/F result: low risk": {
        "es": "M-CHAT-R/F resultado: riesgo bajo", "en": "M-CHAT-R/F result: low risk"},
    "M-CHAT-R/F second part: medium risk in first part": {
        "es": "M-CHAT-R/F segunda parte: riesgo medio en la primera parte",
        "en": "M-CHAT-R/F second part: medium risk in the first part"},
    "M-CHAT-R/F second part: referral required": {
        "es": "M-CHAT-R/F segunda parte: requiere derivación",
        "en": "M-CHAT-R/F second part: referral required"},
    "M-CHAT-R/F second part: no referral required": {
        "es": "M-CHAT-R/F segunda parte: no requiere derivación",
        "en": "M-CHAT-R/F second part: no referral required"},
    "M-CHAT-R/F medium risk: diagnostic referral required": {
        "es": "M-CHAT-R/F riesgo medio: requiere derivación a evaluación diagnóstica",
        "en": "M-CHAT-R/F medium risk: diagnostic referral required"},
    "M-CHAT-R/F medium risk: no diagnostic referral required": {
        "es": "M-CHAT-R/F riesgo medio: no requiere derivación a evaluación diagnóstica",
        "en": "M-CHAT-R/F medium risk: no diagnostic referral required"},
    "M-CHAT-R/F high risk: diagnostic referral required": {
        "es": "M-CHAT-R/F riesgo alto: requiere derivación a evaluación diagnóstica",
        "en": "M-CHAT-R/F high risk: diagnostic referral required"},
    "M-CHAT-R/F high risk with specialist referral": {
        "es": "M-CHAT-R/F riesgo alto con derivación a especialista",
        "en": "M-CHAT-R/F high risk with specialist referral"},
    "Children aged 31–59 months evaluated at integral health control": {
        "es": "Niños y niñas de 31–59 meses evaluados en el control de salud integral",
        "en": "Children aged 31–59 months evaluated at the integral health check"},
    "Children aged 31–59 months suspected elsewhere": {
        "es": "Niños y niñas de 31–59 meses con sospecha detectada en otra instancia",
        "en": "Children aged 31–59 months with suspicion detected elsewhere"},
    "Suspected autism ages 30–59 months: diagnostic referral required": {
        "es": "Sospecha de autismo a los 30–59 meses: requiere derivación a evaluación diagnóstica",
        "en": "Suspected autism at ages 30–59 months: diagnostic referral required"},
    "Suspected autism ages 30–59 months: no diagnostic referral required": {
        "es": "Sospecha de autismo a los 30–59 meses: no requiere derivación a evaluación diagnóstica",
        "en": "Suspected autism at ages 30–59 months: no diagnostic referral required"},
    "Counselling in screening context: number of M-CHAT-R/F": {
        "es": "Consejería en contexto de tamizaje: número de M-CHAT-R/F",
        "en": "Counselling in the screening context: number of M-CHAT-R/F"},
    "Assisted referral in screening context: number of M-CHAT-R/F": {
        "es": "Derivación asistida en contexto de tamizaje: número de M-CHAT-R/F",
        "en": "Assisted referral in the screening context: number of M-CHAT-R/F"},
    "Entry to primary-level rehabilitation by health condition: autism": {
        "es": "Ingreso a rehabilitación de nivel primario por condición de salud: autismo",
        "en": "Entry to primary-level rehabilitation by health condition: autism"},
    "Entry to hospital-level rehabilitation by health condition: autism": {
        "es": "Ingreso a rehabilitación de nivel hospitalario por condición de salud: autismo",
        "en": "Entry to hospital-level rehabilitation by health condition: autism"},
    "Entry to mental-health programme: pervasive developmental disorders": {
        "es": "Ingreso al programa de salud mental: trastornos generalizados del desarrollo",
        "en": "Entry to the mental-health programme: pervasive developmental disorders"},
    "Entry: autism": {"es": "Ingreso: autismo", "en": "Entry: autism"},
    "Entry: Asperger": {"es": "Ingreso: síndrome de Asperger", "en": "Entry: Asperger syndrome"},
    "Entry: Rett syndrome": {"es": "Ingreso: síndrome de Rett", "en": "Entry: Rett syndrome"},
    "Entry: childhood disintegrative disorder": {
        "es": "Ingreso: trastorno desintegrativo infantil", "en": "Entry: childhood disintegrative disorder"},
    "Entry: pervasive developmental disorder unspecified": {
        "es": "Ingreso: trastorno generalizado del desarrollo no especificado",
        "en": "Entry: pervasive developmental disorder, unspecified"},
    "Clinical discharge: autism": {"es": "Egreso clínico: autismo", "en": "Clinical discharge: autism"},
    "Clinical discharge: Asperger": {"es": "Egreso clínico: síndrome de Asperger", "en": "Clinical discharge: Asperger syndrome"},
    "Clinical discharge: Rett syndrome": {"es": "Egreso clínico: síndrome de Rett", "en": "Clinical discharge: Rett syndrome"},
    "Clinical discharge: childhood disintegrative disorder": {
        "es": "Egreso clínico: trastorno desintegrativo infantil",
        "en": "Clinical discharge: childhood disintegrative disorder"},
    "Clinical discharge: pervasive developmental disorder unspecified": {
        "es": "Egreso clínico: trastorno generalizado del desarrollo no especificado",
        "en": "Clinical discharge: pervasive developmental disorder, unspecified"},
    "Clinical discharge: pervasive developmental disorders": {
        "es": "Egreso clínico: trastornos generalizados del desarrollo",
        "en": "Clinical discharge: pervasive developmental disorders"},
    "Autism under control in primary care": {
        "es": "Autismo bajo control en APS", "en": "Autism under control in primary care"},
    "Autism under control in specialty care": {
        "es": "Autismo bajo control en especialidad", "en": "Autism under control in specialty care"},
    "Asperger under control in primary care": {
        "es": "Síndrome de Asperger bajo control en APS", "en": "Asperger syndrome under control in primary care"},
    "Asperger under control in specialty care": {
        "es": "Síndrome de Asperger bajo control en especialidad", "en": "Asperger syndrome under control in specialty care"},
    "Rett syndrome under control in primary care": {
        "es": "Síndrome de Rett bajo control en APS", "en": "Rett syndrome under control in primary care"},
    "Rett syndrome under control in specialty care": {
        "es": "Síndrome de Rett bajo control en especialidad", "en": "Rett syndrome under control in specialty care"},
    "Childhood disintegrative disorder under control in primary care": {
        "es": "Trastorno desintegrativo infantil bajo control en APS",
        "en": "Childhood disintegrative disorder under control in primary care"},
    "Childhood disintegrative disorder under control in specialty care": {
        "es": "Trastorno desintegrativo infantil bajo control en especialidad",
        "en": "Childhood disintegrative disorder under control in specialty care"},
    "Pervasive developmental disorder unspecified under control in primary care": {
        "es": "Trastorno generalizado del desarrollo no especificado bajo control en APS",
        "en": "Pervasive developmental disorder, unspecified, under control in primary care"},
    "Pervasive developmental disorder unspecified under control in specialty care": {
        "es": "Trastorno generalizado del desarrollo no especificado bajo control en especialidad",
        "en": "Pervasive developmental disorder, unspecified, under control in specialty care"},
    "Pervasive developmental disorders under control in primary care": {
        "es": "Trastornos generalizados del desarrollo bajo control en APS",
        "en": "Pervasive developmental disorders under control in primary care"},
    "Pervasive developmental disorders under control in specialty care": {
        "es": "Trastornos generalizados del desarrollo bajo control en especialidad",
        "en": "Pervasive developmental disorders under control in specialty care"},
    "Autism spectrum disorder population under control": {
        "es": "Población con trastorno del espectro autista bajo control",
        "en": "Autism spectrum disorder population under control"},
    "Total NANEAS population under control": {
        "es": "Población total NANEAS bajo control", "en": "Total NANEAS population under control"},
}


def rem_indicator(value, lang: str) -> str:
    """Glosa bilingüe del indicador REM; devuelve el valor tal cual si el indicador no está declarado."""
    s = str(value).strip()
    return REM_INDICATOR.get(s, {}).get(lang, s)


# ===========================================================================
# REM-20 — áreas funcionales de hospitalización (glosa bilingüe y glosario de abreviatura)
# ===========================================================================
"""La columna `area_funcional` de `outputs/tidy/rem20_establishment_area_year.csv` llega del REM-20 en
español y SÓLO en español: es el nombre de la sección del formulario. El panel (e) de la Figura E22
ordena las áreas por días-cama disponibles e imprime las diez primeras, de modo que hasta esta glosa el
documento inglés rotulaba diez barras en español («Méd.-Quir. Cuid. Medios», «Obstetricia») dentro de
una lámina por lo demás inglesa: la rutina de abreviatura acortaba la cadena ESPAÑOLA y el idioma del
documento no intervenía en ningún punto.

`rem20_area(valor, idioma)` devuelve el nombre completo en el idioma pedido y `rem20_area_words(idioma)`
el glosario de recorte de ESE idioma, para que la abreviatura se haga sobre la cadena del propio idioma
y nunca sobre la traducción de otra. El nombre completo vuelve siempre en la tabla acompañante: la
lámina abrevia, no oculta.

La escala de complejidad del REM-20 tiene cuatro peldaños —básicos, medios, intermedios, intensivos— y
la traducción los conserva distintos (`basic`, `medium`, `intermediate`, `intensive`): traducir
«cuidados medios» por «intermediate care» fundiría dos áreas funcionales que la fuente separa."""

REM20_AREA: dict[str, dict[str, str]] = {
    # -- las diez que imprime el panel (e) de la Figura E22, por días-cama disponibles ---------------
    "Área Médico-Quirúrgico Cuidados Medios": {
        "es": "Área Médico-Quirúrgico Cuidados Medios",
        "en": "Medical–surgical area, medium care"},
    "Área Médico-Quirúrgico Cuidados Básicos": {
        "es": "Área Médico-Quirúrgico Cuidados Básicos",
        "en": "Medical–surgical area, basic care"},
    "Área Médica Adulto Cuidados Medios": {
        "es": "Área Médica Adulto Cuidados Medios",
        "en": "Adult medical area, medium care"},
    "Área Obstetricia": {
        "es": "Área Obstetricia", "en": "Obstetrics area"},
    "Área Médica Adulto Cuidados Básicos": {
        "es": "Área Médica Adulto Cuidados Básicos",
        "en": "Adult medical area, basic care"},
    "Área Cuidados Intermedios Adultos": {
        "es": "Área Cuidados Intermedios Adultos",
        "en": "Adult intermediate care area"},
    "Área Médico-Quirúrgico Pediátrica Cuidados Medios": {
        "es": "Área Médico-Quirúrgico Pediátrica Cuidados Medios",
        "en": "Paediatric medical–surgical area, medium care"},
    "Área Cuidados Intensivos Adultos": {
        "es": "Área Cuidados Intensivos Adultos",
        "en": "Adult intensive care area"},
    "Área Psiquiatría Adulto Corta estadía": {
        "es": "Área Psiquiatría Adulto Corta estadía",
        "en": "Adult psychiatry area, short stay"},
    "Área Neonatología Cuidados Intermedios": {
        "es": "Área Neonatología Cuidados Intermedios",
        "en": "Neonatal intermediate care area"},
    # -- el resto del formulario, para que un cambio de orden entre años no reintroduzca la fuga -----
    "Área Médica Pediátrica Cuidados Medios": {
        "es": "Área Médica Pediátrica Cuidados Medios",
        "en": "Paediatric medical area, medium care"},
    "Área Médico-Quirúrgico Pediátrica Cuidados Básicos": {
        "es": "Área Médico-Quirúrgico Pediátrica Cuidados Básicos",
        "en": "Paediatric medical–surgical area, basic care"},
    "Área Neonatología Cuidados Básicos": {
        "es": "Área Neonatología Cuidados Básicos",
        "en": "Neonatal basic care area"},
    "Área Médica Pediátrica Cuidados Básicos": {
        "es": "Área Médica Pediátrica Cuidados Básicos",
        "en": "Paediatric medical area, basic care"},
    "Área Cuidados Intermedios Pediátricos": {
        "es": "Área Cuidados Intermedios Pediátricos",
        "en": "Paediatric intermediate care area"},
    "Área Neonatología Cuidados Intensivos": {
        "es": "Área Neonatología Cuidados Intensivos",
        "en": "Neonatal intensive care area"},
    "Área Pensionado": {
        "es": "Área Pensionado", "en": "Private paying ward area"},
    "Área Sociosanitaria Adulto": {
        "es": "Área Sociosanitaria Adulto", "en": "Adult social-health care area"},
    "Área Psiquiatría Infanto-adolescente corta estadía": {
        "es": "Área Psiquiatría Infanto-adolescente corta estadía",
        "en": "Child and adolescent psychiatry area, short stay"},
    "Área Cuidados Intensivos Pediátricos": {
        "es": "Área Cuidados Intensivos Pediátricos",
        "en": "Paediatric intensive care area"},
    "Área de Hospitalización de Cuidados Intensivos en Psiquiatría Adulto": {
        "es": "Área de Hospitalización de Cuidados Intensivos en Psiquiatría Adulto",
        "en": "Adult psychiatric intensive care area"},
    "Área Psiquiatría Adulto Mediana estadía": {
        "es": "Área Psiquiatría Adulto Mediana estadía",
        "en": "Adult psychiatry area, medium stay"},
    "Área Psiquiatría Forense Adulto tratamiento": {
        "es": "Área Psiquiatría Forense Adulto tratamiento",
        "en": "Adult forensic psychiatry area, treatment"},
    "Área Psiquiatría Adulto Larga estadía": {
        "es": "Área Psiquiatría Adulto Larga estadía",
        "en": "Adult psychiatry area, long stay"},
    "Área Psiquiatría Forense Adulto evaluación e inicio tto.": {
        "es": "Área Psiquiatría Forense Adulto evaluación e inicio tto.",
        "en": "Adult forensic psychiatry area, assessment and start of treatment"},
    "Área de Hospitalización de Cuidados Intensivos en Psiquiatría Infanto Adolescente": {
        "es": "Área de Hospitalización de Cuidados Intensivos en Psiquiatría Infanto Adolescente",
        "en": "Child and adolescent psychiatric intensive care area"},
    "Área Psiquiatría Forense Infanto Adolescente tratamiento": {
        "es": "Área Psiquiatría Forense Infanto Adolescente tratamiento",
        "en": "Child and adolescent forensic psychiatry area, treatment"},
    "Área Psiquiatría Infanto-adolescente mediana estadía": {
        "es": "Área Psiquiatría Infanto-adolescente mediana estadía",
        "en": "Child and adolescent psychiatry area, medium stay"},
}

#: Palabras que se repiten en los nombres de área funcional y que sólo gastan ancho en el eje de la
#: lámina. Hay un glosario POR IDIOMA porque la abreviatura se aplica a la cadena del propio idioma:
#: el glosario español no recorta nada de «Paediatric medical–surgical area, medium care», y aplicarlo
#: a la cadena inglesa era exactamente lo que dejaba el rótulo español en la lámina inglesa.
REM20_AREA_WORDS: dict[str, dict[str, str]] = {
    "es": {
        "Médico-Quirúrgico": "Méd.-Quir.", "Cuidados Intermedios": "Cuid. Intermedios",
        "Cuidados Intensivos": "Cuid. Intensivos", "Cuidados Medios": "Cuid. Medios",
        "Cuidados Básicos": "Cuid. Básicos", "Pediátrica": "Ped.", "Pediátrico": "Ped.",
        "Pediátricos": "Ped.", "Psiquiatría": "Psiq.", "Neonatología": "Neonat.",
        "Corta estadía": "corta est.", "Mediana estadía": "mediana est.",
        "Larga estadía": "larga est.", "Infanto-adolescente": "infanto-adol.",
        "Infanto Adolescente": "infanto-adol.", "Hospitalización de ": "",
    },
    "en": {
        "Medical–surgical": "Med.–surg.", "medical–surgical": "med.–surg.",
        "Child and adolescent": "Child & adol.", "Paediatric": "Paed.",
        "psychiatric intensive care": "psych. intensive care",
        "forensic psychiatry": "forensic psych.", "psychiatry": "psych.",
        "Neonatal": "Neonat.",
        "assessment and start of treatment": "assessment/start of tx",
    },
}

#: Palabra que encabeza todos los nombres y que, por común, no distingue ninguno: se quita antes de
#: abreviar. En español es el prefijo «Área », en inglés el sufijo « area».
REM20_AREA_STEM = {"es": ("Área ", ""), "en": ("", " area")}


def rem20_area(value, lang: str) -> str:
    """Nombre completo del área funcional REM-20 en el idioma pedido.

    Devuelve el valor tal cual si el área no está declarada, y entonces la prueba de pureza de idioma
    la señala como fuga y obliga a declararla aquí."""
    s = str(value).strip()
    return REM20_AREA.get(s, {}).get(lang, s)


def rem20_area_short(value, lang: str) -> str:
    """Nombre del área funcional SIN la palabra común y con el glosario de recorte de SU idioma.

    No trunca: el recorte al ancho del eje —y la comprobación de que dos áreas no queden con el mismo
    rótulo— lo hace la lámina, que es la única que conoce el ancho del panel."""
    t = rem20_area(value, lang)
    head, tail = REM20_AREA_STEM.get(lang, ("", ""))
    if head and t.startswith(head):
        t = t[len(head):]
    if tail and t.endswith(tail):
        t = t[: -len(tail)]
    elif tail and tail + "," in t:
        t = t.replace(tail + ",", ",", 1)
    for long_, short in REM20_AREA_WORDS.get(lang, {}).items():
        t = t.replace(long_, short)
    return t.strip()


# ===========================================================================
# Comunas — ortografía del nombre que se IMPRIME
# ===========================================================================
"""El nombre de comuna es un NOMBRE PROPIO: se escribe igual en los dos idiomas y no se traduce. Lo que
sí cambia entre fuentes es su ortografía. `outputs/tidy/comuna_crosswalk.csv` conserva el nombre tal como
lo publica la fuente que lo enlazó, y esa fuente escribe dos comunas sin su tilde: «Los Angeles» (Biobío)
y «Pitrufquen» (La Araucanía). El resultado se veía en el panel (f) de las Figuras E40 y E41 y en las
tablas territoriales: «Los Angeles» impreso sin tilde en la misma columna que «Valparaíso», «Maipú»,
«Copiapó», «Chillán» y «Concepción», que sí la llevan.

`comuna_name(valor)` normaliza la ortografía ANTES de imprimir, y no lo hace con una lista de parches:
`COMUNA_ACCENTED` declara las 81 comunas del país cuyo nombre oficial lleva tilde, diéresis o eñe, y la
normalización busca por la forma PLEGADA (sin diacríticos, en mayúscula), de modo que cualquier fuente
que deje caer la tilde de cualquiera de las 81 —no sólo de estas dos— se corrige sola. Los 346 nombres
tienen forma plegada única, así que la búsqueda no puede confundir dos comunas.

Sólo se toca el nombre que se IMPRIME. Las columnas de enlace (`comuna_norm`, `aliases_norm`, el código
DEIS y el CUT) siguen siendo las de la fuente: la normalización ortográfica no interviene en ningún
cruce."""

#: Las 81 comunas cuyo nombre oficial lleva diacrítico (tilde, diéresis o eñe), en la ortografía del INE.
COMUNA_ACCENTED: tuple[str, ...] = (
    "Alhué", "Alto Biobío", "Antártica", "Aysén", "Camiña", "Cañete", "Chaitén", "Chañaral", "Chillán",
    "Chillán Viejo", "Chépica", "Cochamó", "Colbún", "Combarbalá", "Concepción", "Conchalí", "Concón",
    "Constitución", "Copiapó", "Curacautín", "Curacaví", "Curaco de Vélez", "Curicó", "Doñihue",
    "Estación Central", "Futaleufú", "Hualaihué", "Hualañé", "Hualpén", "Juan Fernández", "La Unión",
    "Licantén", "Longaví", "Los Álamos", "Los Ángeles", "Machalí", "Maipú", "María Elena", "María Pinto",
    "Maullín", "Mulchén", "Máfil", "Ollagüe", "Olmué", "Peñaflor", "Peñalolén", "Pitrufquén",
    "Puchuncaví", "Pucón", "Puqueldón", "Purén", "Queilén", "Quellón", "Quillón", "Quilpué", "Requínoa",
    "Ránquil", "Río Bueno", "Río Claro", "Río Hurtado", "Río Ibáñez", "Río Negro", "Río Verde",
    "San Fabián", "San Joaquín", "San José de Maipo", "San Nicolás", "San Ramón", "Santa Bárbara",
    "Santa María", "Tirúa", "Toltén", "Tomé", "Traiguén", "Valparaíso", "Vichuquén", "Vicuña", "Vilcún",
    "Viña del Mar", "Ñiquén", "Ñuñoa",
)


def comuna_fold(value) -> str:
    """Forma PLEGADA de un nombre de comuna: sin diacríticos, en mayúscula y sin espacios de sobra."""
    s = " ".join(str(value).split())
    return "".join(c for c in _ud.normalize("NFKD", s) if not _ud.combining(c)).upper()


_COMUNA_BY_FOLD: dict[str, str] = {comuna_fold(n): n for n in COMUNA_ACCENTED}


def comuna_name(value) -> str:
    """Nombre de comuna con su ortografía oficial; devuelve el valor tal cual si no lleva diacrítico."""
    s = " ".join(str(value).split())
    return _COMUNA_BY_FOLD.get(comuna_fold(s), s)


# ===========================================================================
# Texto libre de los archivos tidy y del pipeline — glosa bilingüe
# ===========================================================================
"""Los archivos de `outputs/tidy/` guardan, además de las cifras, texto libre que los documentos
imprimen: la unidad y la geografía declaradas por cada archivo, las reglas de armonización de las capas
de cobertura, los dominios de encuesta, las definiciones de las series educativas, las notas de diseño
de JUNAEB y las categorías agrupadas del episodio GRD. Ese texto lo escribió el módulo productor en UN
idioma. `tidy_text(valor, idioma)` devuelve la versión del idioma pedido: primero busca el valor exacto
en `TIDY_TEXT`, después prueba los patrones de `TIDY_TEXT_RULES` (para el texto que lleva números,
años o listas de variables dentro) y, si nada casa, devuelve el valor tal cual —caso en el que la
prueba `tests/test_language_purity.py` lo señala como fuga y obliga a declararlo aquí—.

Las categorías administrativas que vienen literalmente de la fuente (nombres de país, servicios de
salud, especialidades, tramos FONASA: todas en MAYÚSCULAS en el GRD) NO se traducen: son el valor
codificado del registro y se imprimen igual en los dos idiomas."""

TIDY_TEXT: dict[str, dict[str, str]] = {
    # -- categorías agrupadas del episodio GRD (redactadas por el pipeline, no por la fuente) --------
    "no informado": {"es": "no informado", "en": "not reported"},
    "unknown": {"es": "desconocido", "en": "unknown"},
    "sin hospital de procedencia": {"es": "sin hospital de procedencia", "en": "no referring hospital"},
    "con hospital de procedencia": {"es": "con hospital de procedencia", "en": "with a referring hospital"},
    "otra especialidad (fuera de las 20 principales)": {
        "es": "otra especialidad (fuera de las 20 principales)",
        "en": "other specialty (outside the 20 most frequent)"},
    "otros grupos GRD y no informado": {
        "es": "otros grupos GRD y no informado", "en": "other GRD groups and not reported"},
    "Ninguno/otro": {"es": "Ninguno/otro", "en": "None/other"},
    "Otros o no válidos": {"es": "Otros o no válidos", "en": "Other or invalid"},
    "Pueblo originario declarado": {"es": "Pueblo originario declarado", "en": "Declared indigenous people"},
    "Otro país": {"es": "Otro país", "en": "Other country"},
    "Chile": {"es": "Chile", "en": "Chile"},
    "Desconocida": {"es": "Desconocida", "en": "Unknown"},
    "Desconocido": {"es": "Desconocido", "en": "Unknown"},
    "No identificada": {"es": "No identificada", "en": "Not identified"},
    # Los nombres de convenio previsional son iguales en los dos idiomas: se declaran igualmente para que
    # la prueba de idioma sepa que es una decisión y no un olvido.
    "FONASA MAI A": {"es": "FONASA MAI A", "en": "FONASA MAI A"},
    "FONASA MAI B": {"es": "FONASA MAI B", "en": "FONASA MAI B"},
    "FONASA MAI C": {"es": "FONASA MAI C", "en": "FONASA MAI C"},
    "FONASA MAI D": {"es": "FONASA MAI D", "en": "FONASA MAI D"},
    "ISAPRE": {"es": "ISAPRE", "en": "ISAPRE"},
    "FFAA y de Orden": {"es": "FFAA y de Orden", "en": "Armed forces and police"},
    "FONASA libre elección": {"es": "FONASA libre elección", "en": "FONASA free choice"},
    "Particular": {"es": "Particular", "en": "Out-of-pocket"},
    "Otra": {"es": "Otra", "en": "Other"},
    "Otro": {"es": "Otro", "en": "Other"},
    # -- marcadores que escribe el pipeline, no la fuente ------------------------------------------
    "ABSENT": {"es": "ausente", "en": "absent"},
    "ABSENT: el ítem de enfermedad/condición crónica no incluye una categoría de trastorno del espectro autista": {
        "es": "ausente: el ítem de enfermedad o condición crónica no incluye una categoría de trastorno del espectro autista",
        "en": "absent: the item on a diagnosed illness or chronic condition has no autism spectrum disorder category"},
    "(missing)": {"es": "(vacío)", "en": "(missing)"},
    "MISSING": {"es": "VACÍO", "en": "MISSING"},
    # -- reglas de armonización de las capas de cobertura (FONASA, APS, ISAPRE) ---------------------
    "rows are additive within a year (exact duplicates kept); geography mixes APS-enrolment comuna (inscritos) and domicile (no inscritos)": {
        "es": "las filas son aditivas dentro de un año (los duplicados exactos se conservan); la geografía mezcla la comuna de inscripción en APS (inscritos) y el domicilio (no inscritos)",
        "en": "rows are additive within a year (exact duplicates kept); geography mixes the APS-enrolment comuna (persons enrolled in primary care) and domicile (persons not enrolled)"},
    "enrolled persons (December stock); centres = distinct centre codes; retention = panel enrolled / total enrolled": {
        "es": "personas inscritas (stock de diciembre); centros = códigos de centro distintos; retención = inscritos del panel / inscritos totales",
        "en": "enrolled persons (December stock); centres = distinct centre codes; retention = panel enrolled / total enrolled"},
    "enrolled persons (December stock); n_centres = distinct centre codes, not additive across rows": {
        "es": "personas inscritas (stock de diciembre); n_centres = códigos de centro distintos, no aditivos entre filas",
        "en": "enrolled persons (December stock); n_centres = distinct centre codes, not additive across rows"},
    "enrolled persons (December stock, comuna of the centre)": {
        "es": "personas inscritas (stock de diciembre, comuna del centro)",
        "en": "enrolled persons (December stock, comuna of the centre)"},
    "sheet 'Beneficiarios' (age columns collapsed to 5-year bands) + sheet 'Nonatos o sin Clasificar'": {
        "es": "hoja «Beneficiarios» (columnas de edad colapsadas a tramos quinquenales) + hoja «Nonatos o sin Clasificar»",
        "en": "sheet 'Beneficiarios' (age columns collapsed to 5-year bands) + sheet 'Nonatos o sin Clasificar'"},
    "Total Cotizantes + Total Cargas (derived per cell; sex views derived likewise from the sex sheets)": {
        "es": "Total Cotizantes + Total Cargas (derivado celda a celda; las vistas por sexo se derivan igual desde las hojas por sexo)",
        "en": "Total Cotizantes + Total Cargas (derived per cell; sex views derived likewise from the sex sheets)"},
    "2019-2020 single-year columns 'Edad 1'..'Edad 100' collapsed to 5-year bands; 'Edad 1' inferred to hold ages 0-1; 'Edad 100' open-ended": {
        "es": "columnas de edad simple «Edad 1»…«Edad 100» de 2019-2020 colapsadas a tramos quinquenales; se infiere que «Edad 1» contiene las edades 0-1 y que «Edad 100» es un tramo abierto",
        "en": "2019-2020 single-year columns 'Edad 1'..'Edad 100' collapsed to 5-year bands; 'Edad 1' inferred to hold ages 0-1; 'Edad 100' open-ended"},
    "5-year bands as published (0-4 … 95-99, >=100 -> 80+); S/I -> not_informed": {
        "es": "tramos quinquenales tal como se publican (0-4 … 95-99, >=100 -> 80+); S/I -> not_informed",
        "en": "5-year bands as published (0-4 … 95-99, >=100 -> 80+); S/I -> not_informed"},
    "comuna file: sum ONLY within year+sex; the TOTAL sex view duplicates MUJER+HOMBRE(+SIN_INFORMACION); beneficiarios = cotizantes + cargas (+ nonatos in 2019-2020); all-zero cells of the complete source grid are omitted (absent = 0)": {
        "es": "archivo comunal: sumar SOLO dentro de año + sexo; la vista de sexo TOTAL duplica MUJER+HOMBRE(+SIN_INFORMACION); beneficiarios = cotizantes + cargas (+ nonatos en 2019-2020); las celdas todas en cero de la rejilla fuente completa se omiten (ausente = 0)",
        "en": "comuna file: sum ONLY within year+sex; the TOTAL sex view duplicates MUJER+HOMBRE(+SIN_INFORMACION); beneficiarios = cotizantes + cargas (+ nonatos in 2019-2020); all-zero cells of the complete source grid are omitted (absent = 0)"},
    # -- dominios y campos de las encuestas ---------------------------------------------------------
    "ENDIDE adultos 18+: autismo reportado": {
        "es": "ENDIDE adultos 18+: autismo reportado", "en": "ENDIDE adults 18+: reported autism"},
    "ENDIDE NNA 2-17: autismo reportado": {
        "es": "ENDIDE NNA 2-17: autismo reportado",
        "en": "ENDIDE children and adolescents 2-17: reported autism"},
    "ENDIDE NNA 2-17: autismo reportado y confirmado por un médico": {
        "es": "ENDIDE NNA 2-17: autismo reportado y confirmado por un médico",
        "en": "ENDIDE children and adolescents 2-17: autism reported and confirmed by a physician"},
    "ENDIDE NNA con autismo reportado: confirmado por un médico": {
        "es": "ENDIDE NNA con autismo reportado: confirmado por un médico",
        "en": "ENDIDE children and adolescents with reported autism: confirmed by a physician"},
    "ENDIDE NNA con autismo reportado: confirmado por un médico (sensibilidad: No responde = no confirmado)": {
        "es": "ENDIDE NNA con autismo reportado: confirmado por un médico (sensibilidad: No responde = no confirmado)",
        "en": "ENDIDE children and adolescents with reported autism: confirmed by a physician (sensitivity: No answer = not confirmed)"},
    "ENDIDE NNA con autismo reportado: ha recibido medicamento": {
        "es": "ENDIDE NNA con autismo reportado: ha recibido medicamento",
        "en": "ENDIDE children and adolescents with reported autism: has received medication"},
    "ENDIDE NNA con autismo reportado: ha recibido otro tratamiento": {
        "es": "ENDIDE NNA con autismo reportado: ha recibido otro tratamiento",
        "en": "ENDIDE children and adolescents with reported autism: has received other treatment"},
    "ENCAVI 15+: diagnóstico de trastorno del espectro autista": {
        "es": "ENCAVI 15+: diagnóstico de trastorno del espectro autista",
        "en": "ENCAVI 15+: autism spectrum disorder diagnosis"},
    "ENCAVI 15+: diagnóstico de trastorno del espectro autista (sensibilidad: No sabe/No responde = no diagnosticado)": {
        "es": "ENCAVI 15+: diagnóstico de trastorno del espectro autista (sensibilidad: No sabe/No responde = no diagnosticado)",
        "en": "ENCAVI 15+: autism spectrum disorder diagnosis (sensitivity: Do not know / No answer = not diagnosed)"},
    "ENCAVI 15+ con diagnóstico de TEA: ha recibido o está en tratamiento médico": {
        "es": "ENCAVI 15+ con diagnóstico de TEA: ha recibido o está en tratamiento médico",
        "en": "ENCAVI 15+ with an ASD diagnosis: has received or is under medical treatment"},
    "age_group": {"es": "grupo etario", "en": "age group"},
    "sex": {"es": "sexo", "en": "sex"},
    "total": {"es": "total", "en": "total"},
    "Hombre": {"es": "Hombre", "en": "Male"},
    "Mujer": {"es": "Mujer", "en": "Female"},
    "primary": {"es": "principal", "en": "primary"},
    "secondary": {"es": "secundaria", "en": "secondary"},
    "sensitivity": {"es": "sensibilidad", "en": "sensitivity"},
    "adequate": {"es": "adecuada", "en": "adequate"},
    "imprecise": {"es": "imprecisa", "en": "imprecise"},
    # -- definiciones de las series educativas ------------------------------------------------------
    "Estudiantes autistas en PIE (TEA + TEA-Asperger, según Centro de Estudios MINEDUC)": {
        "es": "Estudiantes autistas en PIE (TEA + TEA-Asperger, según Centro de Estudios MINEDUC)",
        "en": "Autistic students in PIE (ASD + ASD-Asperger, per Centro de Estudios MINEDUC)"},
    "Estudiantes autistas en PIE (SINACES Tabla 1; TEA + TEA-Asperger)": {
        "es": "Estudiantes autistas en PIE (SINACES Tabla 1; TEA + TEA-Asperger)",
        "en": "Autistic students in PIE (SINACES Table 1; ASD + ASD-Asperger)"},
    "Estudiantes matriculados en PIE con NEE permanente 'Trastorno del Espectro Autista (P)' (establecimientos funcionando)": {
        "es": "Estudiantes matriculados en PIE con NEE permanente «Trastorno del Espectro Autista (P)» (establecimientos funcionando)",
        "en": "Students enrolled in PIE with the permanent special educational need 'Trastorno del Espectro Autista (P)' (operating establishments)"},
    "Estudiantes matriculados en PIE con NEE permanente 'Trastorno del Espectro Autista - Asperger (P)'": {
        "es": "Estudiantes matriculados en PIE con NEE permanente «Trastorno del Espectro Autista - Asperger (P)»",
        "en": "Students enrolled in PIE with the permanent special educational need 'Trastorno del Espectro Autista - Asperger (P)'"},
    "Porcentaje publicado de 'Trastorno del Espectro Autista (P)' sobre el total PIE": {
        "es": "Porcentaje publicado de «Trastorno del Espectro Autista (P)» sobre el total PIE",
        "en": "Published percentage of 'Trastorno del Espectro Autista (P)' over the PIE total"},
    "Porcentaje publicado de 'Trastorno del Espectro Autista - Asperger (P)' sobre el total PIE": {
        "es": "Porcentaje publicado de «Trastorno del Espectro Autista - Asperger (P)» sobre el total PIE",
        "en": "Published percentage of 'Trastorno del Espectro Autista - Asperger (P)' over the PIE total"},
    "Estudiantes matriculados en Escuelas Especiales de Autismo": {
        "es": "Estudiantes matriculados en Escuelas Especiales de Autismo",
        "en": "Students enrolled in special autism schools (Escuelas Especiales de Autismo)"},
    "Total = Escuela Especial de Autismo + PIE": {
        "es": "Total = Escuela Especial de Autismo + PIE",
        "en": "Total = special autism school + PIE"},
    "Total − Escuela Especial de Autismo (derivado)": {
        "es": "Total − Escuela Especial de Autismo (derivado)",
        "en": "Total − special autism school (derived)"},
    "Total de estudiantes integrados/as en el PIE (todas las NEE)": {
        "es": "Total de estudiantes integrados/as en el PIE (todas las NEE)",
        "en": "Total students integrated in PIE (all special educational needs)"},
    "Total de postulantes al PIE (todas las NEE)": {
        "es": "Total de postulantes al PIE (todas las NEE)",
        "en": "Total PIE applicants (all special educational needs)"},
    "Postulantes autistas al PIE": {"es": "Postulantes autistas al PIE", "en": "Autistic PIE applicants"},
    "Postulantes autistas por ingreso regular (cupos Decreto 170)": {
        "es": "Postulantes autistas por ingreso regular (cupos Decreto 170)",
        "en": "Autistic applicants through regular entry (Decreto 170 places)"},
    "Postulantes autistas por ingreso excepcional (autorización Seremi)": {
        "es": "Postulantes autistas por ingreso excepcional (autorización Seremi)",
        "en": "Autistic applicants through exceptional entry (Seremi authorisation)"},
    "% publicado: postulantes autistas / total postulantes": {
        "es": "% publicado: postulantes autistas / total postulantes",
        "en": "published %: autistic applicants / total applicants"},
    "100 × (TEA + TEA-Asperger) / total PIE": {
        "es": "100 × (TEA + TEA-Asperger) / total PIE", "en": "100 × (ASD + ASD-Asperger) / PIE total"},
    "100 × TEA (P) / total PIE": {"es": "100 × TEA (P) / total PIE", "en": "100 × ASD (P) / PIE total"},
    "100 × femenino / (femenino + masculino)": {
        "es": "100 × femenino / (femenino + masculino)", "en": "100 × female / (female + male)"},
    "100 × postulantes autistas / total postulantes (calculado)": {
        "es": "100 × postulantes autistas / total postulantes (calculado)",
        "en": "100 × autistic applicants / total applicants (computed)"},
    "Porcentaje publicado: total PIE / matrícula total en establecimientos con aporte estatal": {
        "es": "Porcentaje publicado: total PIE / matrícula total en establecimientos con aporte estatal",
        "en": "Published percentage: PIE total / total enrolment in state-funded establishments"},
    "Suma TEA (P) + TEA-Asperger (P) calculada a partir de Tabla 6": {
        "es": "Suma TEA (P) + TEA-Asperger (P) calculada a partir de la Tabla 6",
        "en": "Sum of ASD (P) + ASD-Asperger (P) computed from Table 6"},
    "TEA (P) + TEA-Asperger (P), Apuntes 60 Tabla 6": {
        "es": "TEA (P) + TEA-Asperger (P), Apuntes 60 Tabla 6",
        "en": "ASD (P) + ASD-Asperger (P), Apuntes 60 Table 6"},
    # -- notas de diseño de JUNAEB -----------------------------------------------------------------
    "Sin ponderador publicado: proporciones no ponderadas con IC de Wilson; no son estimaciones nacionales": {
        "es": "Sin ponderador publicado: proporciones no ponderadas con IC de Wilson; no son estimaciones nacionales",
        "en": "No published weight: unweighted proportions with Wilson CI; these are not national estimates"},
    # -- unidad declarada por los archivos tidy -----------------------------------------------------
    "A05 autism entries (05990022), count": {
        "es": "ingresos A05 de autismo (05990022), recuento", "en": "A05 autism entries (05990022), count"},
    "DEIS discharges with F84 principal per 100,000 discharges": {
        "es": "egresos DEIS con F84 principal por 100.000 egresos",
        "en": "DEIS discharges with F84 principal per 100,000 discharges"},
    "GRD episodes (rows) by normalised COMUNA of residence; F84 any position / principal per variant": {
        "es": "episodios GRD (filas) por COMUNA de residencia normalizada; F84 en cualquier posición / principal según la variante",
        "en": "GRD episodes (rows) by normalised COMUNA of residence; F84 any position / principal per variant"},
    "GRD episodes with documented F84 (observed panel, all activity) per 100,000 INE resident population (base 2017, 30 June); crude with exact Poisson limits, WHO-standardised with Fay-Feuer limits": {
        "es": "episodios GRD con F84 documentado (panel observado, toda modalidad) por 100.000 habitantes residentes INE (base 2017, 30 de junio); bruta con límites exactos de Poisson y estandarizada OMS con límites de Fay-Feuer",
        "en": "GRD episodes with documented F84 (observed panel, all activity) per 100,000 INE resident population (base 2017, 30 June); crude with exact Poisson limits, WHO-standardised with Fay-Feuer limits"},
    "REM A05 autism entries (sum of age x sex cells, in-era rows) per 100,000 INE resident population (base 2017); crude with exact Poisson limits; WHO-standardised with Fay-Feuer limits; place of care vs residence": {
        "es": "ingresos A05 de autismo del REM (suma de las celdas edad × sexo, filas dentro de la era) por 100.000 habitantes residentes INE (base 2017); bruta con límites exactos de Poisson; estandarizada OMS con límites de Fay-Feuer; lugar de atención frente a residencia",
        "en": "REM A05 autism entries (sum of age × sex cells, in-era rows) per 100,000 INE resident population (base 2017); crude with exact Poisson limits; WHO-standardised with Fay-Feuer limits; place of care vs residence"},
    "P2 ASD under control in December, people": {
        "es": "P2 personas con TEA bajo control en diciembre", "en": "P2 ASD under control in December, people"},
    "P6 primary-care autism under control in December (P6241010), people": {
        "es": "P6 autismo bajo control en APS en diciembre (P6241010), personas",
        "en": "P6 primary-care autism under control in December (P6241010), people"},
    "PIE ASD + ASD-Asperger students (harmonised), annual stock": {
        "es": "estudiantes PIE con TEA + TEA-Asperger (armonizado), stock anual",
        "en": "PIE ASD + ASD-Asperger students (harmonised), annual stock"},
    "beneficiaries (December stock)": {
        "es": "beneficiarios (stock de diciembre)", "en": "beneficiaries (December stock)"},
    "children reported": {"es": "niños y niñas informados", "en": "children reported"},
    "comuna × context indicator: percentage with its own interval": {
        "es": "comuna × indicador de contexto: porcentaje con su propio intervalo",
        "en": "comuna × context indicator: percentage with its own interval"},
    "comuna × indicator × period: observed, expected, ratios": {
        "es": "comuna × indicador × período: observado, esperado, razones",
        "en": "comuna × indicator × period: observed, expected, ratios"},
    "comuna × indicator: LISA quadrant, Gi* class and their p-values": {
        "es": "comuna × indicador: cuadrante LISA, clase Gi* y sus valores p",
        "en": "comuna × indicator: LISA quadrant, Gi* class and their p-values"},
    "comuna × pair: local bivariate class": {
        "es": "comuna × par: clase bivariada local", "en": "comuna × pair: local bivariate class"},
    "comuna × year × indicator: count, population, rate per 100,000": {
        "es": "comuna × año × indicador: recuento, población, tasa por 100.000",
        "en": "comuna × year × indicator: count, population, rate per 100,000"},
    "comuna: 2024 standardisation under two population bases": {
        "es": "comuna: estandarización de 2024 bajo dos bases poblacionales",
        "en": "comuna: 2024 standardisation under two population bases"},
    "discharges (episodes) and bed-days per functional area; activity/capacity, NOT covered population": {
        "es": "egresos (episodios) y días cama por área funcional; actividad/capacidad, NO población cubierta",
        "en": "discharges (episodes) and bed-days per functional area; activity/capacity, NOT covered population"},
    "discharges (episodes) and bed-days; activity/capacity, NOT covered population": {
        "es": "egresos (episodios) y días cama; actividad/capacidad, NO población cubierta",
        "en": "discharges (episodes) and bed-days; activity/capacity, NOT covered population"},
    "discharges (episodes); bed-days available": {
        "es": "egresos (episodios); días cama disponibles", "en": "discharges (episodes); bed-days available"},
    "días de estadía por episodio": {"es": "días de estadía por episodio", "en": "days of stay per episode"},
    "egresos (registros DEIS)": {"es": "egresos (registros DEIS)", "en": "discharges (DEIS records)"},
    "egresos GRD (índice) y reingresos": {
        "es": "egresos GRD (índice) y reingresos", "en": "GRD index discharges and readmissions"},
    "egresos con el subcódigo en DIAG1 (registros DEIS)": {
        "es": "egresos con el subcódigo en DIAG1 (registros DEIS)",
        "en": "discharges carrying the subcode in DIAG1 (DEIS records)"},
    "entries reported": {"es": "ingresos informados", "en": "entries reported"},
    "exits reported": {"es": "egresos informados", "en": "exits reported"},
    "episodes with F84 (any position) per 100,000 GRD episodes": {
        "es": "episodios con F84 (cualquier posición) por 100.000 episodios GRD",
        "en": "episodes with F84 (any position) per 100,000 GRD episodes"},
    "episodes with F84 principal per 100,000 GRD episodes": {
        "es": "episodios con F84 principal por 100.000 episodios GRD",
        "en": "episodes with F84 principal per 100,000 GRD episodes"},
    "episodios GRD": {"es": "episodios GRD", "en": "GRD episodes"},
    "episodios GRD (mes de ingreso)": {"es": "episodios GRD (mes de ingreso)", "en": "GRD episodes (month of admission)"},
    "episodios GRD con el co-diagnóstico": {
        "es": "episodios GRD con el co-diagnóstico", "en": "GRD episodes carrying the co-diagnosis"},
    "episodios GRD y personas dentro del año": {
        "es": "episodios GRD y personas dentro del año", "en": "GRD episodes and persons within the year"},
    "identificadores y episodios GRD": {
        "es": "identificadores y episodios GRD", "en": "GRD identifiers and episodes"},
    "indicator pair × scale: Spearman rho with Fisher-z interval": {
        "es": "par de indicadores × escala: rho de Spearman con intervalo de Fisher-z",
        "en": "indicator pair × scale: Spearman rho with Fisher-z interval"},
    "indicator pair: bivariate Moran's I": {
        "es": "par de indicadores: I de Moran bivariada", "en": "indicator pair: bivariate Moran's I"},
    "indicator × comparison: Spearman rho with Fisher-z interval": {
        "es": "indicador × comparación: rho de Spearman con intervalo de Fisher-z",
        "en": "indicator × comparison: Spearman rho with Fisher-z interval"},
    "indicator × year: Gini, Theil (between/within) and decile ratio": {
        "es": "indicador × año: Gini, Theil (entre/dentro) y razón de deciles",
        "en": "indicator × year: Gini, Theil (between/within) and decile ratio"},
    "interventions": {"es": "intervenciones", "en": "interventions"},
    "one row per scale × indicator × value type × weights × period × subset": {
        "es": "una fila por escala × indicador × tipo de valor × pesos × período × subconjunto",
        "en": "one row per scale × indicator × value type × weights × period × subset"},
    "people in stock": {"es": "personas en el stock", "en": "people in the stock"},
    "percent": {"es": "porcentaje", "en": "percent"},
    "percent of PIE applicants": {"es": "porcentaje de los postulantes al PIE", "en": "percent of PIE applicants"},
    "percent of PIE students": {"es": "porcentaje de los estudiantes PIE", "en": "percent of PIE students"},
    "percent of enrolment in state-funded establishments": {
        "es": "porcentaje de la matrícula en establecimientos con aporte estatal",
        "en": "percent of enrolment in state-funded establishments"},
    "percentage of the comuna population; SAE 2024 small-area estimates carry their own lower and upper limit, which is reported and never propagated into the correlations": {
        "es": "porcentaje de la población comunal; las estimaciones de área pequeña SAE 2024 traen su propio límite inferior y superior, que se informa y nunca se propaga a las correlaciones",
        "en": "percentage of the comuna population; SAE 2024 small-area estimates carry their own lower and upper limit, which is reported and never propagated into the correlations"},
    "persons": {"es": "personas", "en": "persons"},
    "persons (INE projection, 30 June)": {
        "es": "personas (proyección INE, 30 de junio)", "en": "persons (INE projection, 30 June)"},
    "persons with valid benefits (December stock); sum only within year+sex (TOTAL duplicates the sex views)": {
        "es": "personas con beneficios vigentes (stock de diciembre); sumar solo dentro de año + sexo (TOTAL duplica las vistas por sexo)",
        "en": "persons with valid benefits (December stock); sum only within year+sex (TOTAL duplicates the sex views)"},
    "persons with valid benefits (December stock; administrative comuna of the beneficiary)": {
        "es": "personas con beneficios vigentes (stock de diciembre; comuna administrativa del beneficiario)",
        "en": "persons with valid benefits (December stock; administrative comuna of the beneficiary)"},
    "peso relativo IR-29301 / episodios por grupo GRD": {
        "es": "peso relativo IR-29301 / episodios por grupo GRD",
        "en": "IR-29301 relative weight / episodes per GRD group"},
    "referral records": {"es": "registros de derivación", "en": "referral records"},
    "region × indicator: observed, expected, rate and ratios": {
        "es": "región × indicador: observado, esperado, tasa y razones",
        "en": "region × indicator: observed, expected, rate and ratios"},
    "screening records": {"es": "registros de tamizaje", "en": "screening records"},
    "screening results": {"es": "resultados de tamizaje", "en": "screening results"},
    "students": {"es": "estudiantes", "en": "students"},
    # -- denominador declarado ---------------------------------------------------------------------
    "INE base 2017 (30 June) comuna population": {
        "es": "población comunal INE base 2017 (30 de junio)", "en": "INE base 2017 (30 June) comuna population"},
    "INE base 2017 person-years": {"es": "persona-años INE base 2017", "en": "INE base 2017 person-years"},
    "INE base 2017 population": {"es": "población INE base 2017", "en": "INE base 2017 population"},
    "INE base 2017 versus Census 2024": {
        "es": "INE base 2017 frente al Censo 2024", "en": "INE base 2017 versus Census 2024"},
    "person-years of the period": {"es": "persona-años del período", "en": "person-years of the period"},
    "población INE (no incluida)": {"es": "población INE (no incluida)", "en": "INE population (not included)"},
    "see unit": {"es": "véase la unidad", "en": "see unit"},
    # -- geografía declarada -----------------------------------------------------------------------
    "Administrative comuna of the beneficiary (as published by the Superintendencia)": {
        "es": "Comuna administrativa del beneficiario (tal como la publica la Superintendencia)",
        "en": "Administrative comuna of the beneficiary (as published by the Superintendencia)"},
    "Comuna (cod_comuna) / region (codregion)": {
        "es": "Comuna (cod_comuna) / región (codregion)", "en": "Comuna (cod_comuna) / region (codregion)"},
    "Comuna (cut_comuna, 4-digit INE code) and region": {
        "es": "Comuna (cut_comuna, código INE de 4 dígitos) y región",
        "en": "Comuna (cut_comuna, 4-digit INE code) and region"},
    "Comuna (residence)": {"es": "Comuna (residencia)", "en": "Comuna (residence)"},
    "Comuna and coordinates of the establishment (ComunaCodigo, Latitud, Longitud)": {
        "es": "Comuna y coordenadas del establecimiento (ComunaCodigo, Latitud, Longitud)",
        "en": "Comuna and coordinates of the establishment (ComunaCodigo, Latitud, Longitud)"},
    "Comuna of enumeration (census geography)": {
        "es": "Comuna de empadronamiento (geografía censal)", "en": "Comuna of enumeration (census geography)"},
    "Comuna of the APS centre (COD_CENTRO), never residence": {
        "es": "Comuna del centro APS (COD_CENTRO), nunca la residencia",
        "en": "Comuna of the APS centre (COD_CENTRO), never residence"},
    "Establishment (CODIGO_ESTABLECIMIENTO, COD_SSS), never residence": {
        "es": "Establecimiento (CODIGO_ESTABLECIMIENTO, COD_SSS), nunca la residencia",
        "en": "Establishment (CODIGO_ESTABLECIMIENTO, COD_SSS), never residence"},
    "Establishment and comuna of the school (JUNAEB_4_Q1_COMUNA etc.), not residence": {
        "es": "Establecimiento y comuna del colegio (JUNAEB_4_Q1_COMUNA y equivalentes), no la residencia",
        "en": "Establishment and comuna of the school (JUNAEB_4_Q1_COMUNA and equivalents), not residence"},
    "Establishment of care (IdEstablecimiento, IdServicio, IdRegion, IdComuna of the establishment); never residence": {
        "es": "Establecimiento de atención (IdEstablecimiento, IdServicio, IdRegion, IdComuna del establecimiento); nunca la residencia",
        "en": "Establishment of care (IdEstablecimiento, IdServicio, IdRegion, IdComuna of the establishment); never residence"},
    "Hospital of care (COD_HOSPITAL, SERVICIO_SALUD); patient's reported COMUNA/PROVINCIA of residence (place of care and residence must not be mixed)": {
        "es": "Hospital de atención (COD_HOSPITAL, SERVICIO_SALUD); COMUNA/PROVINCIA de residencia informada del paciente (lugar de atención y residencia no se mezclan)",
        "en": "Hospital of care (COD_HOSPITAL, SERVICIO_SALUD); patient's reported COMUNA/PROVINCIA of residence (place of care and residence must not be mixed)"},
    "Mixed: comuna of the APS enrolment centre for enrolled persons and domicile for non-enrolled; the variable INSCRITO_APS that separates the mixture disappears from 2023; never treat as homogeneous residence": {
        "es": "Mixta: comuna del centro de inscripción APS para los inscritos y domicilio para los no inscritos; la variable INSCRITO_APS que separa la mezcla desaparece desde 2023; nunca se trata como residencia homogénea",
        "en": "Mixed: comuna of the APS enrolment centre for enrolled persons and domicile for non-enrolled; the variable INSCRITO_APS that separates the mixture disappears from 2023; never treat as homogeneous residence"},
    "National": {"es": "Nacional", "en": "National"},
    "National (and sector where published)": {
        "es": "Nacional (y sector donde se publica)", "en": "National (and sector where published)"},
    "National and regional; never comuna": {
        "es": "Nacional y regional; nunca comunal", "en": "National and regional; never comuna"},
    "National and regional; never disaggregate to comuna": {
        "es": "Nacional y regional; nunca se desagrega a comuna",
        "en": "National and regional; never disaggregate to comuna"},
    "National/regional; the provincia/comuna complement does not confer comuna representativeness": {
        "es": "Nacional/regional; el complemento de provincia/comuna no confiere representatividad comunal",
        "en": "National/regional; the provincia/comuna complement does not confer comuna representativeness"},
    "Residence comuna (4-digit INE code without leading zero; DEIS uses 5 digits with leading zero); name aliases Aisén/Aysén, Coihaique/Coyhaique, Cabo de Hornos (Ex-Navarino)/Cabo de Hornos": {
        "es": "Comuna de residencia (código INE de 4 dígitos sin cero inicial; DEIS usa 5 dígitos con cero inicial); alias de nombre Aisén/Aysén, Coihaique/Coyhaique, Cabo de Hornos (Ex-Navarino)/Cabo de Hornos",
        "en": "Residence comuna (4-digit INE code without leading zero; DEIS uses 5 digits with leading zero); name aliases Aisén/Aysén, Coihaique/Coyhaique, Cabo de Hornos (Ex-Navarino)/Cabo de Hornos"},
    "Residence comuna/region of the patient (COMUNA_RESIDENCIA, 5-digit DEIS code with leading zero) and establishment sector (PERTENENCIA_ESTABLECIMIENTO_SALUD)": {
        "es": "Comuna/región de residencia del paciente (COMUNA_RESIDENCIA, código DEIS de 5 dígitos con cero inicial) y dependencia del establecimiento (PERTENENCIA_ESTABLECIMIENTO_SALUD)",
        "en": "Residence comuna/region of the patient (COMUNA_RESIDENCIA, 5-digit DEIS code with leading zero) and establishment sector (PERTENENCIA_ESTABLECIMIENTO_SALUD)"},
    "administrative comuna of the beneficiary as recorded by the ISAPRE (not verified residence)": {
        "es": "comuna administrativa del beneficiario según la registra la ISAPRE (no es residencia verificada)",
        "en": "administrative comuna of the beneficiary as recorded by the ISAPRE (not verified residence)"},
    "as above": {"es": "igual que arriba", "en": "as above"},
    "comuna": {"es": "comuna", "en": "comuna"},
    "comuna and region": {"es": "comuna y región", "en": "comuna and region"},
    "comuna of domicile as registered by FONASA": {
        "es": "comuna de domicilio según la registra FONASA", "en": "comuna of domicile as registered by FONASA"},
    "comuna of residence as recorded in GRD (matched to INE names via comuna_crosswalk; unmatched kept as unknown)": {
        "es": "comuna de residencia según el GRD (enlazada a los nombres INE por comuna_crosswalk; las no enlazadas quedan como desconocidas)",
        "en": "comuna of residence as recorded in GRD (matched to INE names via comuna_crosswalk; unmatched kept as unknown)"},
    "comuna of the APS centre (place of enrolment, not residence)": {
        "es": "comuna del centro APS (lugar de inscripción, no residencia)",
        "en": "comuna of the APS centre (place of enrolment, not residence)"},
    "comuna of the APS enrolment centre (place of enrolment, not residence)": {
        "es": "comuna del centro de inscripción APS (lugar de inscripción, no residencia)",
        "en": "comuna of the APS enrolment centre (place of enrolment, not residence)"},
    "establishment (place of care), not residence": {
        "es": "establecimiento (lugar de atención), no residencia",
        "en": "establishment (place of care), not residence"},
    "mixed: comuna of the APS enrolment centre for inscritos and comuna of domicile for non-inscritos (NOT homogeneous residence); the split is available only in fonasa_beneficiaries_comuna_tramo_year for 2018-2022": {
        "es": "mixta: comuna del centro de inscripción APS para los inscritos y comuna de domicilio para los no inscritos (NO es residencia homogénea); la separación solo está disponible en fonasa_beneficiaries_comuna_tramo_year para 2018-2022",
        "en": "mixed: comuna of the APS enrolment centre for inscritos and comuna of domicile for non-inscritos (NOT homogeneous residence); the split is available only in fonasa_beneficiaries_comuna_tramo_year for 2018-2022"},
    "mixed: residence for GRD, establishment for REM/REM-20/APS (column geography_numerator)": {
        "es": "mixta: residencia en el GRD y establecimiento en REM/REM-20/APS (columna geography_numerator)",
        "en": "mixed: residence for GRD, establishment for REM/REM-20/APS (column geography_numerator)"},
    "not applicable": {"es": "no aplica", "en": "not applicable"},
    "region": {"es": "región", "en": "region"},
    "residence (SAE and INE) or mixed (FONASA share)": {
        "es": "residencia (SAE e INE) o mixta (proporción FONASA)",
        "en": "residence (SAE and INE) or mixed (FONASA share)"},
    "residence (territorial population; comuna of residence)": {
        "es": "residencia (población territorial; comuna de residencia)",
        "en": "residence (territorial population; comuna of residence)"},
}

#: Texto que lleva números, años o listas de variables dentro y por eso se declara como patrón.
#: Cada regla es (patrón, {"es": plantilla, "en": plantilla}) con los grupos escritos \1, \2, …
#: Categorías del episodio GRD que la fuente escribe en español y que NO son nombres propios: tipo de
#: ingreso, de actividad, de procedencia, de alta, etnia declarada, sexo y los estados del dato. Se
#: traducen al inglés porque son prosa administrativa, no la razón social de una institución. Lo que
#: queda literal (y la nota de la tabla lo declara) son el servicio de salud, la especialidad médica y
#: el tramo previsional: son los rótulos que el maestro del GRD asigna a cada institución o convenio.
GRD_SOURCE_CATEGORY: dict[str, str] = {
    # estados del dato (aparecen en varias variables)
    "DESCONOCIDO": "UNKNOWN", "DESCONOCIDA": "UNKNOWN", "IGNORADO": "NOT RECORDED",
    "NO IDENTIFICADA": "NOT IDENTIFIED", "NO IDENTIFICADO": "NOT IDENTIFIED",
    "NO CONSIGNADO": "NOT RECORDED", "NO APLICA": "NOT APPLICABLE", "NO RESPONDE": "NO ANSWER",
    "NINGUNA": "NONE", "NINGUNO": "NONE", "OTRO": "OTHER", "OTRA": "OTHER",
    # TIPO_INGRESO
    "URGENCIA": "EMERGENCY", "PROGRAMADA": "SCHEDULED", "NO PROGRAMADA": "UNSCHEDULED",
    "OBSTETRICA": "OBSTETRIC",
    # TIPO_ACTIVIDAD
    "HOSPITALIZACIÓN": "HOSPITALISATION",
    "CIRUGÍA MAYOR AMBULATORIA (CMA)": "MAJOR AMBULATORY SURGERY (CMA)",
    "HOSPITALIZACIÓN DIURNA": "DAY HOSPITALISATION",
    "HOSPITALIZACIÓN EN URGENCIA": "HOSPITALISATION IN THE EMERGENCY UNIT",
    # TIPO_PROCEDENCIA
    "SERVICIO EMERGENCIA (DOMICILIO)": "EMERGENCY DEPARTMENT (FROM HOME)",
    "CENTRO ESPECIALIDADES (CDT, CRS, CONSULTORIO ADOS. ESP)":
        "SPECIALTY CENTRE (CDT, CRS, ATTACHED SPECIALTY CLINIC)",
    "OTROS HOSPITALES DE LA RED": "OTHER HOSPITALS OF THE HEALTH SERVICE NETWORK",
    "OTROS HOSPITALES RED NACIONAL": "OTHER HOSPITALS OF THE NATIONAL NETWORK",
    "APS URGENCIA (SAPU, SUR, SUC)": "PRIMARY-CARE EMERGENCY UNIT (SAPU, SUR, SUC)",
    "APS CONSULTORIO (CESFAM)": "PRIMARY-CARE CLINIC (CESFAM)",
    "OTRAS INSTITUCIONES SALUD (CLÍNICAS PRIVADAS, DE REHABILITAC":
        "OTHER HEALTH INSTITUTIONS (PRIVATE CLINICS, REHABILITATIO",
    "OTRAS INSTITUCIONES (CÁRCEL, HOGARES DE ANCIANOS, SENAME, EC":
        "OTHER INSTITUTIONS (PRISON, CARE HOMES, SENAME, ET",
    "CONSULTA PRIVADA": "PRIVATE PRACTICE",
    "ESTRATEGIA CRR": "REFERRAL AND COUNTER-REFERRAL STRATEGY (CRR)",
    "PLAN DE RESOLUCIÓN LE": "WAITING-LIST RESOLUTION PLAN",
    "HOSPITALIZACIÓN DOMICILIARIA": "HOME HOSPITALISATION",
    "POSTA RURAL": "RURAL HEALTH POST",
    "CARDIOCIRUGÍA PAGO GRD": "CARDIAC SURGERY, GRD PAYMENT",
    "LISTA DE ESPERA": "WAITING LIST",
    "UGCC": "UGCC (NATIONAL COMPLEX-CASE MANAGEMENT UNIT)",
    # TIPOALTA
    "DOMICILIO": "HOME",
    "DERIVACIÓN OTRO HOSPITAL DEL SERVICIO": "TRANSFER TO ANOTHER HOSPITAL OF THE SAME HEALTH SERVICE",
    "DERIVACIÓN OTRO HOSPITAL DE LA RED NACIONAL": "TRANSFER TO ANOTHER HOSPITAL OF THE NATIONAL NETWORK",
    "DERIVACIÓN A OTROS CENTROS (CÁRCEL, HOGAR DE": "TRANSFER TO OTHER CENTRES (PRISON, CARE HOM",
    "DERIVACIÓN INST. PRIVADA (COMPRA DE SERVICIOS": "TRANSFER TO A PRIVATE INSTITUTION (PURCHASED SERVICE",
    "DERIVACIÓN INST. PRIVADA (VOLUNTARIO)": "TRANSFER TO A PRIVATE INSTITUTION (AT THE PATIENT'S REQUEST)",
    "ALTA VOLUNTARIA": "DISCHARGE AGAINST MEDICAL ADVICE",
    "FALLECIDO": "DIED",
    "FUGA DEL PACIENTE": "PATIENT ABSCONDED",
    # sexo
    "HOMBRE": "MALE", "MUJER": "FEMALE",
}

#: Frase que declara, en la nota de toda tabla de características del episodio, qué categorías se
#: transcriben literalmente y cuáles llevan glosa. La usan el módulo 11 (Tabla S54) y el 16 (Tabla S109),
#: de modo que las dos digan lo mismo.
GRD_CATEGORY_NOTE = {
    "es": ("Las categorías del episodio se traducen al idioma del documento, salvo el servicio de salud, "
           "la especialidad médica, el tramo previsional y los pueblos originarios declarados, que son los "
           "rótulos que el maestro del GRD asigna y se transcriben literalmente, en español y en mayúsculas, "
           "en los dos idiomas. El registro escribe algunas categorías con más de una grafía (MEXICO y "
           "MÉXICO, HAITI y HAITÍ, REPUBLICA y REPÚBLICA DOMINICANA, NINGUNA y NINGUNO): las filas se "
           "mantienen separadas tal como las reporta la fuente y por eso la traducción puede repetirse."),
    "en": ("Episode categories are translated into the language of the document, except for the health "
           "service, the medical specialty, the insurance bracket and the declared indigenous people, which "
           "are the labels assigned by the GRD master tables and are transcribed verbatim, in Spanish and in "
           "capitals, in both languages. The register writes some categories with more than one spelling "
           "(MEXICO and MÉXICO, HAITI and HAITÍ, REPUBLICA and REPÚBLICA DOMINICANA, NINGUNA and NINGUNO): "
           "the rows are kept separate exactly as the source reports them, so the same translation can "
           "appear twice."),
}

#: Nacionalidades del GRD: el registro las escribe en español y tienen exónimo inglés establecido, de
#: modo que el documento en inglés las imprime en inglés (el español conserva la forma de la fuente).
GRD_COUNTRY: dict[str, str] = {
    "AFGANISTÁN": "AFGHANISTAN", "AFRICA ORIENTAL": "EASTERN AFRICA", "ALBANIA": "ALBANIA",
    "ALEMANIA": "GERMANY", "AMÉRICA": "AMERICAS", "AMÉRICA CENTRAL": "CENTRAL AMERICA",
    "AMÉRICA DEL NORTE": "NORTHERN AMERICA", "AMÉRICA DEL SUR": "SOUTH AMERICA",
    "AMÉRICA SEPTENTRIONAL": "NORTHERN AMERICA", "ANGOLA": "ANGOLA", "ANGUILA": "ANGUILLA",
    "ANTIGUA Y BARBUDA": "ANTIGUA AND BARBUDA", "ANTILLAS HOLANDESAS": "NETHERLANDS ANTILLES",
    "ANTÁRTIDA": "ANTARCTICA", "ARABIA SAUDITA": "SAUDI ARABIA", "ARGELIA": "ALGERIA",
    "ARGENTINA": "ARGENTINA", "ARMENIA": "ARMENIA", "ARUBA": "ARUBA", "ASIA": "ASIA",
    "ASIA SUDORIENTAL": "SOUTH-EASTERN ASIA", "AUSTRALIA": "AUSTRALIA", "AUSTRIA": "AUSTRIA",
    "AZERBAIYÁN": "AZERBAIJAN", "BAHAMAS": "BAHAMAS", "BANGLADESH": "BANGLADESH",
    "BARBADOS": "BARBADOS", "BELARÚS": "BELARUS", "BELICE": "BELIZE", "BENIN": "BENIN",
    "BERMUDAS": "BERMUDA", "BOLIVIA": "BOLIVIA",
    "BOLIVIA (ESTADO PLURINACIONAL DE)": "BOLIVIA (PLURINATIONAL STATE OF)",
    "BOSNIA Y HERZEGOVINA": "BOSNIA AND HERZEGOVINA", "BOTSWANA": "BOTSWANA", "BRASIL": "BRAZIL",
    "BULGARIA": "BULGARIA", "BURKINA FASO": "BURKINA FASO", "BURUNDI": "BURUNDI",
    "BÉLGICA": "BELGIUM", "CABO VERDE": "CABO VERDE", "CAMBOYA": "CAMBODIA",
    "CAMERÚN": "CAMEROON", "CANADÁ": "CANADA", "CHAD": "CHAD", "CHECOSLOVAQUIA": "CZECHOSLOVAKIA",
    "CHILE": "CHILE", "CHINA": "CHINA", "CHIPRE": "CYPRUS", "COLOMBIA": "COLOMBIA",
    "COMORAS": "COMOROS", "CONGO": "CONGO",
    "CONGO (REPÚBLICA DEMOCRÁTICA DEL)": "CONGO (DEMOCRATIC REPUBLIC OF THE)",
    "COREA DEL NORTE (REPÚBLICA POPULAR DEMOCRÁTICA DE)":
        "NORTH KOREA (DEMOCRATIC PEOPLE'S REPUBLIC OF)",
    "COREA DEL SUR (REPÚBLICA DE)": "SOUTH KOREA (REPUBLIC OF)",
    "COSTA DE MARFIL": "CÔTE D'IVOIRE", "COSTA RICA": "COSTA RICA", "CROACIA": "CROATIA",
    "CUBA": "CUBA", "DINAMARCA": "DENMARK", "DJIBOUTI": "DJIBOUTI", "DOMINICA": "DOMINICA",
    "ECUADOR": "ECUADOR", "EGIPTO": "EGYPT", "EL SALVADOR": "EL SALVADOR",
    "EMIRATOS ÁRABES UNIDOS": "UNITED ARAB EMIRATES", "ERITREA": "ERITREA",
    "ESLOVAQUIA": "SLOVAKIA", "ESLOVENIA": "SLOVENIA", "ESPAÑA": "SPAIN",
    "ESTADOS UNIDOS DE AMÉRICA": "UNITED STATES OF AMERICA", "ETIOPÍA": "ETHIOPIA",
    "EUROPA": "EUROPE", "EUROPA OCCIDENTAL": "WESTERN EUROPE", "EUROPA ORIENTAL": "EASTERN EUROPE",
    "EUROPA SEPTENTRIONAL": "NORTHERN EUROPE", "FIJI": "FIJI", "FILIPINAS": "PHILIPPINES",
    "FINLANDIA": "FINLAND", "FRANCIA": "FRANCE", "GABÓN": "GABON",
    "GEORGIA DEL SUR Y LAS ISLAS SANDWICH DEL SUR": "SOUTH GEORGIA AND THE SOUTH SANDWICH ISLANDS",
    "GHANA": "GHANA", "GRANADA": "GRENADA", "GRECIA": "GREECE", "GROENLANDIA": "GREENLAND",
    "GUADELOUPE": "GUADELOUPE", "GUAM": "GUAM", "GUATEMALA": "GUATEMALA",
    "GUAYANA FRANCESA": "FRENCH GUIANA", "GUINEA": "GUINEA", "GUINEA BISSAU": "GUINEA-BISSAU",
    "GUINEA ECUATORIAL": "EQUATORIAL GUINEA", "GUINEA FRANCESA": "FRENCH GUINEA",
    "GUYANA": "GUYANA", "HAITI": "HAITI", "HAITÍ": "HAITI", "HONDURAS": "HONDURAS",
    "HUNGRÍA": "HUNGARY", "INDIA": "INDIA", "INDONESIA": "INDONESIA", "IRAQ": "IRAQ",
    "IRLANDA": "IRELAND", "IRÁN (REPÚBLICA ISLÁMICA DE)": "IRAN (ISLAMIC REPUBLIC OF)",
    "ISLA DE NAVIDAD": "CHRISTMAS ISLAND", "ISLANDIA": "ICELAND", "ISLAS CAIMÁN": "CAYMAN ISLANDS",
    "ISLAS COCOS": "COCOS (KEELING) ISLANDS", "ISLAS COOK": "COOK ISLANDS",
    "ISLAS FEROE": "FAROE ISLANDS", "ISLAS MALVINAS": "FALKLAND ISLANDS (MALVINAS)",
    "ISLAS VÍRGENES BRITÁNICAS": "BRITISH VIRGIN ISLANDS", "ISLAS ÅLAND": "ÅLAND ISLANDS",
    "ISRAEL": "ISRAEL", "ITALIA": "ITALY", "JAMAICA": "JAMAICA", "JAPÓN": "JAPAN",
    "JORDANIA": "JORDAN", "KAZAJSTÁN": "KAZAKHSTAN", "KENYA": "KENYA",
    "KIRGUISTÁN": "KYRGYZSTAN", "KUWAIT": "KUWAIT",
    "LAO (REPÚBLICA DEMOCRÁTICA POPULAR)": "LAO PEOPLE'S DEMOCRATIC REPUBLIC",
    "LESOTHO": "LESOTHO", "LETONIA": "LATVIA", "LUXEMBURGO": "LUXEMBOURG", "LÍBANO": "LEBANON",
    "MACAO": "MACAO", "MACEDONIA": "NORTH MACEDONIA", "MADAGASCAR": "MADAGASCAR",
    "MALASIA": "MALAYSIA", "MALDIVAS": "MALDIVES", "MALTA": "MALTA", "MARRUECOS": "MOROCCO",
    "MARTINIQUE": "MARTINIQUE", "MAURICIO": "MAURITIUS", "MAURITANIA": "MAURITANIA",
    "MAYOTTE": "MAYOTTE", "MEXICO": "MEXICO", "MÉXICO": "MEXICO",
    "MOLDOVA (REPÚBLICA DE)": "MOLDOVA (REPUBLIC OF)", "MONTENEGRO": "MONTENEGRO",
    "MONTSERRAT": "MONTSERRAT", "MOZAMBIQUE": "MOZAMBIQUE", "MYANMAR": "MYANMAR",
    "MÓNACO": "MONACO", "NAMIBIA": "NAMIBIA", "NAURU": "NAURU", "NEPAL": "NEPAL",
    "NICARAGUA": "NICARAGUA", "NIGERIA": "NIGERIA", "NORUEGA": "NORWAY",
    "NUEVA ZELANDIA": "NEW ZEALAND", "NÍGER": "NIGER", "OCEANÍA": "OCEANIA", "OMÁN": "OMAN",
    "PAKISTÁN": "PAKISTAN", "PALAU": "PALAU", "PALESTINA (ESTADO DE)": "PALESTINE (STATE OF)",
    "PANAMÁ": "PANAMA", "PARAGUAY": "PARAGUAY", "PAÍSES BAJOS": "NETHERLANDS", "PERÚ": "PERU",
    "POLINESIA": "POLYNESIA", "POLINESIA FRANCESA": "FRENCH POLYNESIA", "POLONIA": "POLAND",
    "PORTUGAL": "PORTUGAL", "PUERTO RICO": "PUERTO RICO",
    "REINO UNIDO DE GRAN BRETAÑA E IRLANDA DEL NORTE":
        "UNITED KINGDOM OF GREAT BRITAIN AND NORTHERN IRELAND",
    "REPUBLICA DOMINICANA": "DOMINICAN REPUBLIC", "REPÚBLICA DOMINICANA": "DOMINICAN REPUBLIC",
    "REPÚBLICA CENTROAFRICANA": "CENTRAL AFRICAN REPUBLIC", "REPÚBLICA CHECA": "CZECHIA",
    "REPÚBLICA ÁRABE SIRIA": "SYRIAN ARAB REPUBLIC", "REUNIÓN": "RÉUNION", "RUMANIA": "ROMANIA",
    "RUSIA (FEDERACIÓN DE)": "RUSSIAN FEDERATION", "RWANDA": "RWANDA",
    "SAMOA AMERICANA": "AMERICAN SAMOA", "SAN CRISTOBAL Y NEVIS": "SAINT KITTS AND NEVIS",
    "SANTA LUCÍA": "SAINT LUCIA", "SANTA SEDE": "HOLY SEE",
    "SANTO TOMÉ Y PRÍNCIPE": "SAO TOME AND PRINCIPE", "SENEGAL": "SENEGAL", "SERBIA": "SERBIA",
    "SEYCHELLES": "SEYCHELLES", "SIERRA LEONA": "SIERRA LEONE", "SINGAPUR": "SINGAPORE",
    "SRI LANKA": "SRI LANKA", "SUDÁFRICA": "SOUTH AFRICA", "SUDÁN": "SUDAN", "SUECIA": "SWEDEN",
    "SUIZA": "SWITZERLAND", "SWAZILANDIA": "ESWATINI", "TAILANDIA": "THAILAND",
    "TAIWÁN (PROVINCIA DE CHINA)": "TAIWAN (PROVINCE OF CHINA)",
    "TANZANIA (REPÚBLICA UNIDA DE)": "TANZANIA (UNITED REPUBLIC OF)", "TAYIKISTÁN": "TAJIKISTAN",
    "TERRITORIO BRITÁNICO DEL OCÉANO ÍNDICO": "BRITISH INDIAN OCEAN TERRITORY", "TOGO": "TOGO",
    "TRINIDAD Y TOBAGO": "TRINIDAD AND TOBAGO", "TURKMENISTÁN": "TURKMENISTAN",
    "TURQUÍA": "TÜRKIYE", "TÚNEZ": "TUNISIA", "UCRANIA": "UKRAINE", "UGANDA": "UGANDA",
    "URUGUAY": "URUGUAY", "VANUATU": "VANUATU", "VENEZUELA": "VENEZUELA",
    "VENEZUELA (REPÚBLICA BOLIVARIANA DE)": "VENEZUELA (BOLIVARIAN REPUBLIC OF)",
    "VIETNAM": "VIET NAM", "YEMEN": "YEMEN", "YUGOSLAVIA": "YUGOSLAVIA", "ZIMBABWE": "ZIMBABWE",
    "ÁFRICA": "AFRICA", "ÁFRICA SEPTENTRIONAL": "NORTHERN AFRICA",
}


#: Reglas con comodines: (patrón, plantilla). La plantilla lleva la expansión de cada idioma y, cuando la
#: frase contiene un RECUENTO escrito por el módulo productor, la clave `num` con los grupos que hay que
#: reescribir con el separador de miles del idioma («184,963» → «184.963»).
TIDY_TEXT_RULES: list[tuple[str, dict[str, object]]] = [
    (r"^A05 PDD family entries \((con_rett|sin_rett)\), count$",
     {"es": r"ingresos A05 de la familia TGD (\1), recuento", "en": r"A05 PDD family entries (\1), count"}),
    (r"^(\d+) labels: (.+)$",
     {"es": r"\1 rótulos: \2", "en": r"\1 labels: \2"}),
    (r"^No estimable: el cuestionario (\d{4}) no incluye categoría TEA \(categorías: (.+?)\)\. "
     r"Se informa el filtro de diagnóstico prolongado solo como contexto\.$",
     {"es": r"No estimable: el cuestionario \1 no incluye categoría TEA (categorías: \2). "
            r"Se informa el filtro de diagnóstico prolongado solo como contexto.",
      "en": r"Not estimable: the \1 questionnaire has no ASD category (categories: \2). "
            r"The prolonged-diagnosis filter is reported as context only."}),
    (r"^No estimable: la variable (\S+) está completamente vacía en el archivo publicado \((.+?) filas\), "
     r"aunque (.+?) cuidadores respondieron Sí al filtro\. No debe leerse como cero\. "
     r"Ponderador (\S+) ausente en (.+?) filas\.$",
     {"es": r"No estimable: la variable \1 está completamente vacía en el archivo publicado (\2 filas), "
            r"aunque \3 cuidadores respondieron Sí al filtro. No debe leerse como cero. "
            r"Ponderador \4 ausente en \5 filas.",
      "en": r"Not estimable: variable \1 is entirely empty in the published file (\2 rows), even though "
            r"\3 carers answered Yes to the filter. It must not be read as zero. "
            r"Weight \4 is missing in \5 rows.",
      "num": (2, 3, 5)}),
    (r"^Ítem TEA disponible pero sin factor de expansión publicado para (\d{4}): solo conteos y proporción "
     r"no ponderada \(IC Wilson\); no es estimación nacional ni comparable directamente con (\S+)\.(.*)$",
     {"es": r"Ítem TEA disponible pero sin factor de expansión publicado para \1: solo conteos y proporción "
            r"no ponderada (IC de Wilson); no es estimación nacional ni comparable directamente con \2.\3",
      "en": r"ASD item available but with no published expansion factor for \1: counts and unweighted "
            r"proportion only (Wilson CI); not a national estimate and not directly comparable with \2.\3"}),
    (r"^Proporción ponderada de estudiantes cuyo cuidador reporta diagnóstico médico prolongado de TEA sobre "
     r"todos los estudiantes con ponderador \(No/No sabe/sin respuesta al filtro = no reportado\)\. "
     r"Sensibilidad \*_answered: denominador restringido a filtro Sí/No\. Cohorte escolar seleccionada y "
     r"reporte de cuidadores; no prevalencia nacional\.(.*)$",
     {"es": r"Proporción ponderada de estudiantes cuyo cuidador reporta diagnóstico médico prolongado de TEA "
            r"sobre todos los estudiantes con ponderador (No/No sabe/sin respuesta al filtro = no reportado). "
            r"Sensibilidad *_answered: denominador restringido al filtro Sí/No. Cohorte escolar seleccionada y "
            r"reporte de cuidadores; no es prevalencia nacional.\1",
      "en": r"Weighted proportion of students whose carer reports a prolonged medical ASD diagnosis over all "
            r"students carrying a weight (No / Do not know / no answer to the filter = not reported). "
            r"Sensitivity *_answered: denominator restricted to a Yes/No filter answer. Selected school cohort "
            r"and carer report; not national prevalence.\1"}),
    (r"^EE por linealización de Taylor con estudiantes como unidades independientes \(sin estratos/PSU en el "
     r"diccionario; ignora el conglomerado escolar\); IC 95 % logit; ponderador (\S+)$",
     {"es": r"EE por linealización de Taylor con estudiantes como unidades independientes (sin estratos ni UPM "
            r"en el diccionario; ignora el conglomerado escolar); IC 95 % logit; ponderador \1",
      "en": r"SE by Taylor linearisation with students as independent units (no strata or PSU in the "
            r"dictionary; the school cluster is ignored); logit-scale 95% CI; weight \1"}),
    (r"^Sexo: male\.$", {"es": "Sexo: hombres.", "en": "Sex: males."}),
    (r"^Sexo: female\.$", {"es": "Sexo: mujeres.", "en": "Sex: females."}),
    (r"^Categorías de sexo con n<5 \('other', n=(\d+)\) suprimidas\.$",
     {"es": r"Categorías de sexo con n < 5 («other», n = \1) suprimidas.",
      "en": r"Sex categories with n < 5 ('other', n = \1) suppressed."}),
    (r"^(pie_\w+) (\d{4}), género femenino$",
     {"es": r"\1 \2, género femenino", "en": r"\1 \2, female students"}),
    (r"^(pie_\w+) (\d{4}), género masculino$",
     {"es": r"\1 \2, género masculino", "en": r"\1 \2, male students"}),
]

_TIDY_RULES_COMPILED = [(_re.compile(p), t) for p, t in TIDY_TEXT_RULES]

#: Fragmentos que se traducen por separado dentro de una nota compuesta (se prueban por sufijo).
_TIDY_SUFFIXES = (" Sexo: male.", " Sexo: female.", " Categorías de sexo con n<5 ('other', n=1) suprimidas.")


def _expand_rule(m, template: dict, lang: str) -> str:
    """Expande una plantilla de `TIDY_TEXT_RULES` reescribiendo los miles de los grupos declarados.

    El módulo productor deja el número tal como lo escribió («184,963 filas»); la clave opcional
    `"num"` enumera los grupos que son un RECUENTO, de modo que el documento español lea «184.963» y el
    inglés «184,963» sin tocar los decimales de la misma frase."""
    out = m.expand(template[lang])
    for index in template.get("num", ()):
        raw = m.group(index)
        if raw:
            localised = _group_separators(raw, lang)
            if localised != raw:
                out = out.replace(raw, localised)
    return out


def tidy_text(value, lang: str) -> str:
    """Texto libre de un archivo tidy, escrito en `lang`; el valor tal cual si no está declarado."""
    s = str(value).strip()
    if not s:
        return s
    if s in TIDY_TEXT:
        return TIDY_TEXT[s][lang]
    if s in GRD_SOURCE_CATEGORY:
        return GRD_SOURCE_CATEGORY[s] if lang == "en" else s
    if s in GRD_COUNTRY:
        return GRD_COUNTRY[s] if lang == "en" else s
    for suffix in _TIDY_SUFFIXES:
        if s.endswith(suffix) and s[:-len(suffix)].strip():
            return f"{tidy_text(s[: -len(suffix)], lang)} {tidy_text(suffix, lang)}"
    for pattern, template in _TIDY_RULES_COMPILED:
        m = pattern.match(s)
        if m:
            return _expand_rule(m, template, lang)
    return s


# ===========================================================================
# Procedencia de los artefactos fuente — glosa bilingüe de data_provenance.csv
# ===========================================================================
"""`data_provenance.csv` y `provenance_manifest_checks.csv` (módulo 00) describen los 182 artefactos
fuente en inglés: unidad de observación, período, quiebres de definición, restricciones de enlace, regla
de uso y la nota de concordancia con el manifiesto. Ese texto NO es una transcripción de un diccionario
chileno: lo redactó este estudio a partir de `DATA_REVIEW.md` y `source_registry.csv`, de modo que es
prosa descriptiva y el documento en español tiene que leerla en español.

Hasta la tarea LG la Tabla S14 declaraba «se transcriben en inglés tal como constan» y con esa
declaración se saltaba el detector: 544 frases inglesas en 38 páginas del suplemento español. Aquí se
declara la traducción de cada valor distinto; `provenance_text(valor, idioma)` la devuelve, y
`tests/test_language_purity.py` falla si aparece un valor nuevo sin traducir.

Los identificadores que SÍ son la fuente —nombres de archivo, columnas (`CUENTA_BENEFICIARIOS`,
`DIAGNOSTICO1..35`), códigos REM, rutas y URL— se conservan literales dentro de la frase traducida."""

#: Texto descriptivo de la procedencia: inglés (forma canónica del CSV) → español.
PROVENANCE_TEXT: dict[str, str] = {
    # -- unidad de observación ----------------------------------------------------------------------
    "GRD episode (one row per financed/coded hospital episode: hospitalisation or major ambulatory surgery)":
        "episodio GRD (una fila por episodio hospitalario financiado/codificado: hospitalización o cirugía mayor ambulatoria)",
    "Code dictionary / master table (ICD-10, ICD-9-CM procedures, GRD master tables)":
        "diccionario de códigos / tabla maestra (CIE-10, procedimientos CIE-9-MC, tablas maestras GRD)",
    "Establishment x month x REM code row (Col01..Col50 cells of Serie A monthly statistical register)":
        "fila establecimiento × mes × código REM (celdas Col01..Col50 del registro estadístico mensual de la Serie A)",
    "Annual Serie A code dictionary (one sheet per REM section: A03, A05, A27, A28, ...)":
        "diccionario anual de códigos de la Serie A (una hoja por sección REM: A03, A05, A27, A28, …)",
    "Establishment x semester (Mes=06 or 12) x REM code row (Serie P population under control)":
        "fila establecimiento × semestre (Mes=06 o 12) × código REM (población bajo control de la Serie P)",
    "Annual Serie P code dictionary (sheets P2, P6, ...)":
        "diccionario anual de códigos de la Serie P (hojas P2, P6, …)",
    "Hospital discharge (egreso) reported to DEIS, one row per discharge":
        "egreso hospitalario informado al DEIS, una fila por egreso",
    "Variable dictionary of the DEIS discharge database":
        "diccionario de variables de la base de egresos del DEIS",
    "Aggregated cell of FONASA beneficiaries at December (dimension combination x count)":
        "celda agregada de beneficiarios FONASA a diciembre (combinación de dimensiones × recuento)",
    "Variable dictionary of FONASA beneficiary publications":
        "diccionario de variables de las publicaciones de beneficiarios FONASA",
    "Aggregated cell: APS centre x FONASA tramo x age group x sex x TOTAL_INSCRITOS at 31 December":
        "celda agregada: centro APS × tramo FONASA × grupo de edad × sexo × TOTAL_INSCRITOS al 31 de diciembre",
    "Aggregated ISAPRE beneficiaries (cotizantes and cargas) by comuna, age and sex at December":
        "beneficiarios ISAPRE agregados (cotizantes y cargas) por comuna, edad y sexo a diciembre",
    "Population estimate/projection cell: comuna x sex x single age (or x urban/rural area x age group) x year":
        "celda de estimación/proyección de población: comuna × sexo × edad simple (o × área urbana/rural × grupo de edad) × año",
    "Census tabulation: comuna x sex x five-year age group (D1) or disability tabulation (P1)":
        "tabulado censal: comuna × sexo × grupo quinquenal de edad (D1) o tabulado de discapacidad (P1)",
    "National population estimate/projection by sex and age, 1992-2070, base Censo 2024":
        "estimación/proyección nacional de población por sexo y edad, 1992-2070, base Censo 2024",
    "Establishment x functional area x month (REM-20 hospitalisation process indicators; 167,405 rows, 2014-July 2026, 208 establishments, 29 functional areas)":
        "establecimiento × área funcional × mes (indicadores de proceso de hospitalización del REM-20; 167.405 filas, 2014-julio de 2026, 208 establecimientos, 29 áreas funcionales)",
    "Health establishment (current catalogue; 5,717 records including closed establishments)":
        "establecimiento de salud (catálogo vigente; 5.717 registros, incluidos los establecimientos cerrados)",
    "Surveyed person (adults, caregivers and children/adolescents), complex sample design":
        "persona encuestada (adultos, cuidadores y niños, niñas y adolescentes), diseño muestral complejo",
    "Surveyed person aged 15 years or more (16,590 respondents), complex sample design":
        "persona encuestada de 15 años o más (16.590 respondientes), diseño muestral complejo",
    "Surveyed person/household (CASEN 2024), complex sample design":
        "persona u hogar encuestado (CASEN 2024), diseño muestral complejo",
    "Documentation and territorial complement of CASEN 2024 (codebooks, questionnaire, sampling design, usage note, provincia/comuna .dta)":
        "documentación y complemento territorial de CASEN 2024 (libros de códigos, cuestionario, diseño muestral, nota de uso, .dta de provincia/comuna)",
    "Published aggregate tables of students in Programas de Integración Escolar (PIE) by diagnosis":
        "tablas agregadas publicadas de estudiantes en Programas de Integración Escolar (PIE) por diagnóstico",
    "De-identified student record of the Encuesta de Vulnerabilidad Estudiantil (EVE), one file per level (parvularia, 1º básico, 5º básico, 1º medio) and year":
        "registro desidentificado de estudiante de la Encuesta de Vulnerabilidad Estudiantil (EVE), un archivo por nivel (parvularia, 1º básico, 5º básico, 1º medio) y año",
    "EVE questionnaire (PDF) or code dictionary (xlsx) per level and year":
        "cuestionario EVE (PDF) o diccionario de códigos (xlsx) por nivel y año",
    "Small-area estimate (SAE) of income and multidimensional poverty per comuna with confidence interval":
        "estimación de áreas pequeñas (SAE) de pobreza por ingresos y multidimensional por comuna, con intervalo de confianza",
    "Long-format population cell: cut_comuna x edad x género x año (1,905,768 rows)":
        "celda de población en formato largo: cut_comuna × edad × género × año (1.905.768 filas)",
    "Polygon feature: comuna (346 features) or region (17 features), EPSG:3857; shapefile components (.shp geometry, .dbf attributes, .shx index, .prj CRS, .cpg encoding)":
        "entidad poligonal: comuna (346 entidades) o región (17 entidades), EPSG:3857; componentes del shapefile (.shp geometría, .dbf atributos, .shx índice, .prj SRC, .cpg codificación)",
    "Code map row: module x year range x code x domain x unit x aggregation rule x comparability warning (57 rows)":
        "fila del mapa de códigos: módulo × rango de años × código × dominio × unidad × regla de agregación × advertencia de comparabilidad (57 filas)",
    # -- período -------------------------------------------------------------------------------------
    "1992-2070 (base Censo 2024)": "1992-2070 (base Censo 2024)",
    "2001-2024": "2001-2024",
    "2002-2035": "2002-2035",
    "2002-2035 (base Censo 2017)": "2002-2035 (base Censo 2017)",
    "2014-07/2026 (continuous update)": "2014-07/2026 (actualización continua)",
    "2019-2023 (PIE trend)": "2019-2023 (tendencia PIE)",
    "2019-2025": "2019-2025",
    "2022-2025 (SINACES report)": "2022-2025 (informe SINACES)",
    "2023 (PIE by sex)": "2023 (PIE por sexo)",
    "2023-2024": "2023-2024",
    "31 December 2019": "31 de diciembre de 2019",
    "31 December 2020": "31 de diciembre de 2020",
    "31 December 2021": "31 de diciembre de 2021",
    "31 December 2022": "31 de diciembre de 2022",
    "31 December 2023": "31 de diciembre de 2023",
    "31 December 2024": "31 de diciembre de 2024",
    "31 December 2025": "31 de diciembre de 2025",
    "Censo 2024": "Censo 2024",
    "December 2018": "diciembre de 2018",
    "December 2019": "diciembre de 2019",
    "December 2020": "diciembre de 2020",
    "December 2021": "diciembre de 2021",
    "December 2022": "diciembre de 2022",
    "December 2023": "diciembre de 2023",
    "December 2024": "diciembre de 2024",
    "December 2025": "diciembre de 2025",
    "current": "vigente",
    "current catalogue (portal file establecimientos_20260901.csv)":
        "catálogo vigente (archivo del portal establecimientos_20260901.csv)",
    "current layer": "capa vigente",
    "local codebook used by scripts/grd_epidemiology.py":
        "libro de códigos local que usa scripts/grd_epidemiology.py",
    "versions published with GRD 2019-2024": "versiones publicadas junto con el GRD 2019-2024",
    # -- stock o flujo --------------------------------------------------------------------------------
    "flow (episodes discharged in the year)": "flujo (episodios egresados en el año)",
    "flow (discharges in the year)": "flujo (egresos del año)",
    "flow (monthly activity: screenings, interventions, programme entries/exits)":
        "flujo (actividad mensual: tamizajes, intervenciones, ingresos/egresos de programa)",
    "stock": "stock",
    "stock (December snapshot)": "stock (corte de diciembre)",
    "stock (semiannual population under control)": "stock (población bajo control semestral)",
    "stock (school-year registration)": "stock (registro del año escolar)",
    "stock (mid-year population)": "stock (población a mitad de año)",
    "stock (census night 2024)": "stock (noche censal 2024)",
    "stock (2024 estimate)": "stock (estimación 2024)",
    "activity/capacity (monthly discharges and bed-days; beds are capacity)":
        "actividad/capacidad (egresos y días-cama mensuales; las camas son capacidad)",
    "cross-sectional survey (context)": "encuesta transversal (contexto)",
    "cross-sectional survey (population benchmark)": "encuesta transversal (referencia poblacional)",
    "cross-sectional school survey (caregiver report)":
        "encuesta escolar transversal (reporte de cuidadores)",
    "not applicable": "no aplica",
    "not applicable (catalogue)": "no aplica (catálogo)",
    "not applicable (dictionary)": "no aplica (diccionario)",
    "not applicable (documentation)": "no aplica (documentación)",
    "not applicable (metadata)": "no aplica (metadatos)",
    # -- quiebres de definición -----------------------------------------------------------------------
    "Encrypted identifier changes format between 2020 and 2021 (zero overlap); hospital panel 65/65/65/65/68/72; mean coding depth rises from 4.39 (2019) to 5.78 (2024) diagnoses per episode; 2019 contains day-hospital and emergency activity categories absent from 2020; GRD_PUBLICO_2022.csv omits one malformed source row (932,839 vs 932,840 records; see GRD/metadata/SOURCES_MANIFEST.md)":
        "el identificador encriptado cambia de formato entre 2020 y 2021 (solapamiento nulo); panel hospitalario 65/65/65/65/68/72; la profundidad diagnóstica media sube de 4,39 (2019) a 5,78 (2024) diagnósticos por episodio; 2019 contiene categorías de actividad de hospital de día y de urgencia ausentes en 2020; GRD_PUBLICO_2022.csv omite una fila fuente malformada (932.839 frente a 932.840 registros; véase GRD/metadata/SOURCES_MANIFEST.md)",
    "Verify the version applicable to each GRD year (source_registry.csv)":
        "verificar la versión aplicable a cada año GRD (source_registry.csv)",
    "A03: legacy subgroup codes 2019-2022 (children with language/social alteration), new M-CHAT-R/F family 2023, 31-59-month codes added 2024, full redesign 2025; A05: broad PDD only in 2019-2020, strict autism and disaggregated categories from 2021; A27 TEA-specific codes only from 2023 (earlier assisted-referral codes concern alcohol/drugs); A28 autism rehabilitation from 2023; 2020 reporting disruption (pandemic); SerieA_2025.csv keeps one incomplete trailing row from the source publication":
        "A03: códigos de subgrupo del esquema antiguo 2019-2022 (niños y niñas con alteración de lenguaje o del área social), nueva familia M-CHAT-R/F en 2023, códigos de 31-59 meses añadidos en 2024, rediseño completo en 2025; A05: TGD amplio solo en 2019-2020, autismo estricto y categorías desagregadas desde 2021; los códigos A27 específicos de TEA existen solo desde 2023 (los códigos de derivación asistida anteriores corresponden a alcohol y drogas); rehabilitación de autismo A28 desde 2023; disrupción del reporte en 2020 (pandemia); SerieA_2025.csv conserva una última fila incompleta de la publicación fuente",
    "File naming changes in 2023 (DICCIONARIO CODIGOS SA_yy); code families change as listed for rem_serie_a":
        "el nombre de archivo cambia en 2023 (DICCIONARIO CODIGOS SA_yy); las familias de códigos cambian según lo indicado para rem_serie_a",
    "P6 changes from broad PDD (2019-2020) to autism and disaggregated categories (2021); P2501878 exists only from December 2023; June 2020 P2 records only 172 persons in 28 establishments (pandemic reporting collapse); files extracted from the official SERIE_REM_{year}.zip (member names vary by year)":
        "P6 pasa de TGD amplio (2019-2020) a autismo y categorías desagregadas (2021); P2501878 existe solo desde diciembre de 2023; en junio de 2020 P2 registra apenas 172 personas en 28 establecimientos (colapso del reporte por la pandemia); los archivos se extraen del SERIE_REM_{year}.zip oficial (los nombres de los miembros varían por año)",
    "Taxonomic break of P6 in 2021; P2501878 added in 2023":
        "quiebre taxonómico de P6 en 2021; P2501878 se añade en 2023",
    "Confirm version applicable to each year": "confirmar la versión aplicable a cada año",
    "Only two diagnosis fields (cannot reproduce 'F84 in any of 35 positions'); column set changes across years (2019 header PERTENENCIA_ESTABLECIMIENTO_SALU with ETNIA, INTERV_Q, PROCED; 2024 header PERTENENCIA_ESTABLECIMIENTO_SALUD without them); 2012 and 2021 have an official 15-column variant kept apart":
        "solo dos campos de diagnóstico (no permite reproducir «F84 en cualquiera de 35 posiciones»); el conjunto de columnas cambia entre años (encabezado de 2019 PERTENENCIA_ESTABLECIMIENTO_SALU con ETNIA, INTERV_Q, PROCED; encabezado de 2024 PERTENENCIA_ESTABLECIMIENTO_SALUD sin ellas); 2012 y 2021 tienen una variante oficial de 15 columnas que se mantiene aparte",
    "Check variant schemas (2012, 2021, 2024)": "revisar los esquemas de las variantes (2012, 2021, 2024)",
    "Schema changes in 2021, 2023, 2024 and 2025; count column renamed CUENTA_BENEFICIARIOS -> BENEFICIARIOS in 2024; 2018-2020 contain repeated rows that are additive fragments of an unexposed dimension; encoding Latin-1 in 2018-2024 members and UTF-8 in the 2025 member; age groups change (e.g. 30 a 39 in 2023)":
        "el esquema cambia en 2021, 2023, 2024 y 2025; la columna de recuento pasa de CUENTA_BENEFICIARIOS a BENEFICIARIOS en 2024; 2018-2020 contienen filas repetidas que son fragmentos aditivos de una dimensión no expuesta; codificación Latin-1 en los miembros de 2018-2024 y UTF-8 en el de 2025; los grupos de edad cambian (por ejemplo, 30 a 39 en 2023)",
    "2024: variable names change (NOMBRE_DEPENDENCIA -> DEPENDENCIA_ADMINISTRATIVA, TRAMO -> TRAMO_FONASA) and age groups change; encoding Latin-1 in 2019-2023 and UTF-8 in 2024-2025; centre code 200261 appears reused and 200474 corrected geographically; tramo X and missing tramos must not be mixed without definition":
        "2024: cambian los nombres de variables (NOMBRE_DEPENDENCIA → DEPENDENCIA_ADMINISTRATIVA, TRAMO → TRAMO_FONASA) y cambian los grupos de edad; codificación Latin-1 en 2019-2023 y UTF-8 en 2024-2025; el código de centro 200261 aparece reutilizado y el 200474 corregido geográficamente; el tramo X y los tramos ausentes no deben mezclarse sin definirlos",
    "Format changes .xls -> .xlsx and single ages -> five-year groups in 2021; separate sheet for unborn/unclassified in 2019-2020; sheets by sex and 'Total' are duplicated views":
        "el formato cambia de .xls a .xlsx y de edades simples a grupos quinquenales en 2021; hoja separada de nonatos o sin clasificar en 2019-2020; las hojas por sexo y la hoja «Total» son vistas duplicadas",
    "Base Censo 2017; not to be combined with Censo 2024 / base-2024 figures without an explicit flag":
        "base Censo 2017; no debe combinarse con cifras del Censo 2024 ni de la base 2024 sin declararlo explícitamente",
    "Different base from the 2017 projections; P1 is disability context, not autism-specific":
        "base distinta de la de las proyecciones 2017; P1 es contexto de discapacidad, no específico de autismo",
    "No comuna disaggregation equivalent to the base-2017 series":
        "no tiene una desagregación comunal equivalente a la de la serie base 2017",
    "Continuously updated mutable dataset (download dated 2026-09-04); no diagnoses or persons":
        "conjunto de datos mutable de actualización continua (descarga fechada el 2026-09-04); no contiene diagnósticos ni personas",
    "Links all REM-20 codes; historical reporting panel must be derived from observed REM/GRD reporting, not from this file":
        "enlaza todos los códigos del REM-20; el panel histórico de reporte debe derivarse del reporte REM/GRD observado, no de este archivo",
    "Mutable current catalogue (portal version establecimientos_20260901.csv), not an annual series; many historical dates missing":
        "catálogo vigente mutable (versión del portal establecimientos_20260901.csv), no es una serie anual; faltan muchas fechas históricas",
    "Self/caregiver report; not equivalent to an administrative F84 code":
        "autorreporte o reporte del cuidador; no equivale a un código administrativo F84",
    "Reported diagnosis; not clinically equivalent to administrative F84":
        "diagnóstico declarado; no es clínicamente equivalente al F84 administrativo",
    "Not an autism source; 2024 only": "no es una fuente de autismo; solo 2024",
    "TEA strict vs TEA-Asperger vs harmonised TEA + TEA-Asperger require separate rules; 2022 discrepancy: SINACES report writes 42,945 while 45,014 minus 2,074 special-school students gives 42,940 (Apuntes 60); rule must be explicit":
        "TEA estricto, TEA-Asperger y la armonización TEA + TEA-Asperger exigen reglas separadas; discrepancia de 2022: el informe SINACES escribe 42.945 mientras que 45.014 menos 2.074 estudiantes de escuelas especiales da 42.940 (Apuntes 60); la regla debe declararse de forma explícita",
    "Question wording and codes change by year (dictionaries only for 2019, 2021, 2024, 2025); 2022 files are ANSI/Windows-1252 encoded; 2024 1º medio TEA variable is completely empty (report 'not estimable', never zero)":
        "la redacción de las preguntas y los códigos cambian por año (solo hay diccionarios para 2019, 2021, 2024 y 2025); los archivos de 2022 están codificados en ANSI/Windows-1252; en 2024 la variable TEA de 1º medio está completamente vacía (se informa «no estimable», nunca cero)",
    "Questionnaires exist for 2019-2025; dictionaries only for 2019, 2021, 2024 and 2025":
        "hay cuestionarios para 2019-2025; diccionarios solo para 2019, 2021, 2024 y 2025",
    "Estimation uncertainty; 2024 only": "incertidumbre de estimación; solo 2024",
    "Vintage of the layer must be confirmed against the comuna crosswalk (346 comunas)":
        "la versión de la capa debe confirmarse contra el cuadro de equivalencias comunal (346 comunas)",
    "Derived file: must be verified against Poblacion/INE/proyecciones_comuna_edad_sexo_2002_2035_base_2017.csv before use":
        "archivo derivado: debe verificarse contra Poblacion/INE/proyecciones_comuna_edad_sexo_2002_2035_base_2017.csv antes de usarlo",
    "Encodes the A03/A05/A27/A28/P2/P6 definition breaks listed in DATA_REVIEW.md":
        "codifica los quiebres de definición de A03/A05/A27/A28/P2/P6 que enumera DATA_REVIEW.md",
    # -- restricciones de enlace ----------------------------------------------------------------------
    "Unique persons only within each year; never deduplicate across 2020/2021; no person-level linkage to REM, DEIS, FONASA, surveys or education":
        "personas únicas solo dentro de cada año; nunca se desduplica entre 2020 y 2021; no hay enlace a nivel de persona con REM, DEIS, FONASA, encuestas ni educación",
    "Aggregate rows without persons; A27 counts interventions not children; no linkage between A03, A27, A05, A28, P2/P6 or GRD":
        "filas agregadas sin personas; A27 cuenta intervenciones, no niños y niñas; no hay enlace entre A03, A27, A05, A28, P2/P6 ni GRD",
    "Aggregate stocks without persons; not linkable to A05 entries, GRD or education":
        "stocks agregados sin personas; no enlazables con los ingresos A05, con el GRD ni con educación",
    "No identifier; no linkage to GRD episodes or persons":
        "sin identificador; no hay enlace con los episodios GRD ni con personas",
    "Aggregate; no persons": "agregado; sin personas",
    "Aggregate; no persons; not linkable to REM or GRD":
        "agregado; sin personas; no enlazable con REM ni con GRD",
    "Aggregates, no microdata; not linkable to health registers":
        "agregados, sin microdatos; no enlazables con los registros de salud",
    "Territorial": "territorial",
    "Territorial; not users of a specific provider":
        "territorial; no son usuarios de un prestador determinado",
    "Establishment codes link to DEIS catalogue; no persons; compatibility with GRD hospital codes must be verified":
        "los códigos de establecimiento enlazan con el catálogo del DEIS; sin personas; la compatibilidad con los códigos de hospital del GRD debe verificarse",
    "No linkage to registers": "sin enlace con registros",
    "No linkage to registers; benchmark of order of magnitude only":
        "sin enlace con registros; solo sirve como referencia de orden de magnitud",
    "No linkage to registers; comuna identifier does not give comuna representativeness":
        "sin enlace con registros; el identificador de comuna no otorga representatividad comunal",
    "Comuna complement must be linked per codebook; no comuna representativeness":
        "el complemento comunal debe enlazarse según el libro de códigos; no hay representatividad comunal",
    "No linkage to PIE, health registers or other years":
        "sin enlace con el PIE, con los registros de salud ni con otros años",
    "Ecological covariate; ecological fallacy": "covariable ecológica; falacia ecológica",
    "Join by code only; no fuzzy name matching":
        "unión solo por código; nunca por coincidencia difusa de nombres",
    # -- regla de uso ---------------------------------------------------------------------------------
    "Primary hospital estimand: GRD episodes with documented F84 in any diagnosis position per 100,000 GRD episodes; F84 principal, strict hospitalisation vs major ambulatory surgery, fixed panel of 65 hospitals and coding-depth stratification are mandatory sensitivities; never label as 'hospitalisations for autism', prevalence or incidence; reproduce config.CONTROLS['grd_*'] before modelling":
        "estimando hospitalario primario: episodios GRD con F84 documentado en cualquier posición diagnóstica por 100.000 episodios GRD; F84 principal, hospitalización estricta frente a cirugía mayor ambulatoria, panel fijo de 65 hospitales y estratificación por profundidad de codificación son sensibilidades obligatorias; nunca se rotula como «hospitalizaciones por autismo», prevalencia ni incidencia; reproducir config.CONTROLS['grd_*'] antes de modelar",
    "Interpretation of GRD codes and categories only; never a data input":
        "solo para interpretar los códigos y categorías del GRD; nunca es un insumo de datos",
    "Build tidy establishment x month x code tables keeping zero, empty and 'no row reported' as distinct states; facet by definition era; report reporting establishments; confirm every code against the annual Serie A dictionary; treat 2020 as a reporting-disruption year without interpolation; reproduce config.CONTROLS a05/a27/a28/a03 totals":
        "construir tablas tidy de establecimiento × mes × código manteniendo cero, celda vacía y «sin fila reportada» como estados distintos; separar por era de definición; informar los establecimientos reportantes; confirmar cada código contra el diccionario anual de la Serie A; tratar 2020 como año de disrupción del reporte, sin interpolar; reproducir los totales a05/a27/a28/a03 de config.CONTROLS",
    "Confirm every code and column position of scripts/downloads/rem_pathway_codes.csv for the given year before extraction (scripts/audit_rem.py pattern)":
        "confirmar cada código y cada posición de columna de scripts/downloads/rem_pathway_codes.csv para el año correspondiente antes de extraer (patrón de scripts/audit_rem.py)",
    "December (Mes=12) is the primary series and June the sensitivity; never sum semesters nor average them; always report reporting establishments; reproduce config.CONTROLS p2_*/p6_* December totals":
        "diciembre (Mes=12) es la serie primaria y junio la sensibilidad; nunca se suman los semestres ni se promedian; siempre se informan los establecimientos reportantes; reproducir los totales de diciembre p2_*/p6_* de config.CONTROLS",
    "Confirm P2/P6 codes and column meaning for each year before extraction":
        "confirmar los códigos P2/P6 y el significado de las columnas de cada año antes de extraer",
    "External check of the F84-principal/DIAG1-DIAG2 series and of national discharge volumes only; not a substitute for GRD; never combine numerators from GRD with denominators from DEIS":
        "solo como comprobación externa de la serie F84 principal/DIAG1-DIAG2 y de los volúmenes nacionales de egresos; no sustituye al GRD; nunca se combinan numeradores del GRD con denominadores del DEIS",
    "Interpretation only": "solo para interpretación",
    "Never apply drop_duplicates(): sum all rows; harmonise schema explicitly keeping original columns; use as insurance-coverage layer only; reproduce config.CONTROLS fonasa_beneficiaries_december":
        "nunca se aplica drop_duplicates(): se suman todas las filas; el esquema se armoniza de forma explícita conservando las columnas originales; se usa solo como capa de cobertura previsional; reproducir config.CONTROLS fonasa_beneficiaries_december",
    "Use as operational-coverage layer; restrict to tramos A-D when comparing with FONASA 'enrolled' totals (difference < 0.2% in 2019-2022); keep original columns; reproduce config.CONTROLS aps_enrolled_december and aps_centres":
        "se usa como capa de cobertura operativa; se restringe a los tramos A-D al compararla con los totales de «inscritos» de FONASA (diferencia < 0,2 % en 2019-2022); se conservan las columnas originales; reproducir config.CONTROLS aps_enrolled_december y aps_centres",
    "Total = cotizantes + cargas (from 2021); never add sex sheets to the Total sheet; reproduce config.CONTROLS isapre_beneficiaries_december":
        "total = cotizantes + cargas (desde 2021); nunca se suman las hojas por sexo a la hoja Total; reproducir config.CONTROLS isapre_beneficiaries_december",
    "Primary population denominator for 2019-2024/25 series; build an auditable comuna crosswalk by code (no silent fuzzy matching); reproduce config.CONTROLS ine_population_national":
        "denominador poblacional primario de las series 2019-2024/25; se construye un cuadro de equivalencias comunal auditable por código (sin coincidencia difusa silenciosa); reproducir config.CONTROLS ine_population_national",
    "National sensitivity and census-base bridge only; flag explicitly when used":
        "solo como sensibilidad nacional y puente entre bases censales; se declara explícitamente cuando se usa",
    "Sensitivity/bridge only; never mix with base-2017 projections without an explicit flag":
        "solo como sensibilidad o puente; nunca se mezcla con las proyecciones base 2017 sin declararlo explícitamente",
    "Capacity/activity layer and continuous-panel sensitivity only; never use as covered population; reproduce config.CONTROLS rem20_panel_188_retention":
        "solo capa de capacidad/actividad y sensibilidad de panel continuo; nunca se usa como población cubierta; reproducir config.CONTROLS rem20_panel_188_retention",
    "Geography and type of supply for establishment codes only; never reconstruct an annual catalogue from it":
        "solo para la geografía y el tipo de oferta de los códigos de establecimiento; nunca se reconstruye con él un catálogo anual",
    "Estimate proportion, weighted total, SE and 95% CI with weights, strata and clusters (Taylor linearisation); avoid domains with insufficient effective size; preliminary 0.29%/2.86% must be recomputed":
        "se estiman proporción, total ponderado, EE e IC 95 % con ponderadores, estratos y conglomerados (linealización de Taylor); se evitan los dominios con tamaño efectivo insuficiente; las cifras preliminares de 0,29 % y 2,86 % deben recalcularse",
    "Complex-design estimation with 95% CI; preliminary 0.71% (about 114,817 persons) must be recomputed before use":
        "estimación con diseño complejo e IC 95 %; la cifra preliminar de 0,71 % (unas 114.817 personas) debe recalcularse antes de usarla",
    "Context on public insurance use and poverty only; never comuna-level estimates":
        "solo como contexto sobre uso del seguro público y pobreza; nunca se producen estimaciones a nivel de comuna",
    "Interpretation and design declaration only": "solo para interpretación y declaración del diseño",
    "Keep TEA strict, TEA-Asperger, harmonised and SINACES series separate; record the five-case discrepancy; interpret as school recognition/demand, never prevalence":
        "las series TEA estricto, TEA-Asperger, armonizada y SINACES se mantienen separadas; se registra la discrepancia de cinco casos; se interpretan como reconocimiento o demanda escolar, nunca como prevalencia",
    "Use annual wording and weight EXP; report weighted proportions with CI; never national prevalence nor a series directly comparable with PIE; reproduce config.CONTROLS junaeb_unweighted_2024/2025":
        "se usan la redacción anual y el ponderador EXP; se informan proporciones ponderadas con IC; nunca es prevalencia nacional ni una serie directamente comparable con el PIE; reproducir config.CONTROLS junaeb_unweighted_2024/2025",
    "Cite the exact annual wording before using any EVE variable":
        "citar la redacción anual exacta antes de usar cualquier variable de la EVE",
    "Prespecified territorial deprivation covariate with its uncertainty; no ecological searches with many covariates":
        "covariable territorial de privación preespecificada, con su incertidumbre; no se hacen búsquedas ecológicas con muchas covariables",
    "Use only after reconciliation with the INE source file; git-ignored local file (date = mtime)":
        "se usa solo tras conciliarlo con el archivo fuente del INE; archivo local ignorado por git (la fecha es el mtime)",
    "Maps in supplement only; join by cod_comuna after crosswalk; git-ignored local files (date = mtime)":
        "mapas solo en el suplemento; unión por cod_comuna después del cuadro de equivalencias; archivos locales ignorados por git (la fecha es el mtime)",
    "Initial map; each code must be re-confirmed against the annual dictionary in every run":
        "mapa inicial; cada código debe reconfirmarse contra el diccionario anual en cada corrida",
    # -- población cubierta ---------------------------------------------------------------------------
    "Episodes of public hospitals reporting to the FONASA GRD dataset; observed panel of 65 hospitals in 2019-2022, 68 in 2023 and 72 in 2024 (not a fixed panel of 72)":
        "episodios de hospitales públicos que reportan al conjunto GRD de FONASA; panel observado de 65 hospitales en 2019-2022, 68 en 2023 y 72 en 2024 (no es un panel fijo de 72)",
    "Activity reported by public-network establishments (primary care and specialty) to DEIS; the reporting panel varies by year and code and must be reported alongside counts":
        "actividad que los establecimientos de la red pública (atención primaria y especialidad) reportan al DEIS; el panel reportante varía por año y por código y debe informarse junto con los recuentos",
    "People under control in public-network establishments reporting P2 (NANEAS) and P6 (mental health) at June and December; reporting establishments vary (P2 December: 460, 400, 640, 897, 1,012, 1,218, 1,325 in 2019-2025)":
        "personas bajo control en establecimientos de la red pública que reportan P2 (NANEAS) y P6 (salud mental) en junio y diciembre; los establecimientos reportantes varían (P2 en diciembre: 460, 400, 640, 897, 1.012, 1.218, 1.325 en 2019-2025)",
    "All discharges from public and private establishments reported to DEIS (broader than the GRD public panel)":
        "todos los egresos de establecimientos públicos y privados informados al DEIS (universo más amplio que el panel público del GRD)",
    "FONASA beneficiaries at 31 December (national totals 14,841,577 in 2019 to 17,132,611 in 2025)":
        "beneficiarios FONASA al 31 de diciembre (totales nacionales de 14.841.577 en 2019 a 17.132.611 en 2025)",
    "Persons enrolled in primary-care centres (13,777,051 in 2019 to 15,791,862 in 2025; centres 1,890 to 2,091)":
        "personas inscritas en centros de atención primaria (13.777.051 en 2019 a 15.791.862 en 2025; centros de 1.890 a 2.091)",
    "ISAPRE beneficiaries (3,431,126 in 2019 to 2,517,305 in 2025)":
        "beneficiarios ISAPRE (3.431.126 en 2019 a 2.517.305 en 2025)",
    "Resident population of Chile, 346 comunas, 2002-2035 (national 19,107,216 in 2019 to 20,206,953 in 2025)":
        "población residente de Chile, 346 comunas, 2002-2035 (nacional de 19.107.216 en 2019 a 20.206.953 en 2025)",
    "Resident population 2002-2035 (INE base 2017), reshaped by the repository":
        "población residente 2002-2035 (INE base 2017), reordenada por el repositorio",
    "Resident population of Chile (national level only)": "población residente de Chile (solo a nivel nacional)",
    "Population enumerated in Censo 2024": "población empadronada en el Censo 2024",
    "Public hospitals reporting REM-20 bed-day and discharge indicators":
        "hospitales públicos que reportan los indicadores de días-cama y egresos del REM-20",
    "Household population of Chile, 2022 (national and regional representativeness); unweighted autism reports: 72 adults, 163 children/adolescents, 139 with professional confirmation":
        "población en hogares de Chile, 2022 (representatividad nacional y regional); reportes de autismo sin ponderar: 72 adultos, 163 niños, niñas y adolescentes, 139 con confirmación profesional",
    "Household population of Chile, 2024 (national and regional representativeness)":
        "población en hogares de Chile, 2024 (representatividad nacional y regional)",
    "Population aged 15+ of Chile, 2023-2024; 80 unweighted positive autism-diagnosis responses":
        "población de 15 años y más de Chile, 2023-2024; 80 respuestas positivas de diagnóstico de autismo sin ponderar",
    "Students registered in PIE (registration for subsidy/quotas; MINEDUC warns it does not include all autistic students); PIE TEA strict 2019-2023: 11,877; 13,613; 18,801; 28,845; 47,551. TEA-Asperger: 9,135; 9,977; 12,081; 14,095; 16,091. SINACES harmonised 2024-2025: 86,475; 106,786 (special schools 2,505; 2,626)":
        "estudiantes registrados en el PIE (registro para subvención y cupos; el MINEDUC advierte que no incluye a todos los estudiantes autistas); PIE TEA estricto 2019-2023: 11.877; 13.613; 18.801; 28.845; 47.551. TEA-Asperger: 9.135; 9.977; 12.081; 14.095; 16.091. Armonizado SINACES 2024-2025: 86.475; 106.786 (escuelas especiales 2.505; 2.626)",
    "Students in selected school cohorts answering the caregiver questionnaire (coverage is selective, not all Chilean students); unweighted TEA 2024: 17,641 / 10,245 / 7,468 (parvularia / 1º básico / 5º básico); 2025: 18,785 / 12,536 / 9,887 / 9,164 (incl. 1º medio)":
        "estudiantes de cohortes escolares seleccionadas que responden el cuestionario del cuidador (la cobertura es selectiva, no son todos los estudiantes de Chile); TEA sin ponderar 2024: 17.641 / 10.245 / 7.468 (parvularia / 1º básico / 5º básico); 2025: 18.785 / 12.536 / 9.887 / 9.164 (incluye 1º medio)",
    "345 comunas, 2024": "345 comunas, 2024",
    "not applicable (cartography)": "no aplica (cartografía)",
    "not applicable (code map)": "no aplica (mapa de códigos)",
    "not applicable (supply catalogue)": "no aplica (catálogo de oferta)",
    # -- geografía ------------------------------------------------------------------------------------
    "Hospital of care (COD_HOSPITAL, SERVICIO_SALUD); patient's reported COMUNA/PROVINCIA of residence (place of care and residence must not be mixed)":
        "hospital de atención (COD_HOSPITAL, SERVICIO_SALUD); COMUNA/PROVINCIA de residencia declarada del paciente (el lugar de atención y la residencia no deben mezclarse)",
    "Establishment of care (IdEstablecimiento, IdServicio, IdRegion, IdComuna of the establishment); never residence":
        "establecimiento de atención (IdEstablecimiento, IdServicio, IdRegion, IdComuna del establecimiento); nunca la residencia",
    "Residence comuna/region of the patient (COMUNA_RESIDENCIA, 5-digit DEIS code with leading zero) and establishment sector (PERTENENCIA_ESTABLECIMIENTO_SALUD)":
        "comuna o región de residencia del paciente (COMUNA_RESIDENCIA, código DEIS de 5 dígitos con cero inicial) y sector del establecimiento (PERTENENCIA_ESTABLECIMIENTO_SALUD)",
    "Mixed: comuna of the APS enrolment centre for enrolled persons and domicile for non-enrolled; the variable INSCRITO_APS that separates the mixture disappears from 2023; never treat as homogeneous residence":
        "mixta: comuna del centro de inscripción APS para las personas inscritas y domicilio para las no inscritas; la variable INSCRITO_APS que separa la mezcla desaparece desde 2023; nunca se trata como residencia homogénea",
    "Comuna of the APS centre (COD_CENTRO), never residence":
        "comuna del centro APS (COD_CENTRO), nunca la residencia",
    "Administrative comuna of the beneficiary (as published by the Superintendencia)":
        "comuna administrativa del beneficiario (tal como la publica la Superintendencia)",
    "Comuna (residence)": "comuna (residencia)",
    "Comuna of enumeration (census geography)": "comuna de empadronamiento (geografía censal)",
    "Comuna (cut_comuna, 4-digit INE code) and region":
        "comuna (cut_comuna, código INE de 4 dígitos) y región",
    "Comuna (cod_comuna) / region (codregion)": "comuna (cod_comuna) / región (codregion)",
    "Comuna and coordinates of the establishment (ComunaCodigo, Latitud, Longitud)":
        "comuna y coordenadas del establecimiento (ComunaCodigo, Latitud, Longitud)",
    "Establishment (CODIGO_ESTABLECIMIENTO, COD_SSS), never residence":
        "establecimiento (CODIGO_ESTABLECIMIENTO, COD_SSS), nunca la residencia",
    "Establishment and comuna of the school (JUNAEB_4_Q1_COMUNA etc.), not residence":
        "establecimiento y comuna del colegio (JUNAEB_4_Q1_COMUNA, etc.), no la residencia",
    "Residence comuna (4-digit INE code without leading zero; DEIS uses 5 digits with leading zero); name aliases Aisén/Aysén, Coihaique/Coyhaique, Cabo de Hornos (Ex-Navarino)/Cabo de Hornos":
        "comuna de residencia (código INE de 4 dígitos sin cero inicial; el DEIS usa 5 dígitos con cero inicial); alias de nombre Aisén/Aysén, Coihaique/Coyhaique, Cabo de Hornos (Ex-Navarino)/Cabo de Hornos",
    "National": "nacional",
    "National (and sector where published)": "nacional (y por sector cuando se publica)",
    "National and regional; never comuna": "nacional y regional; nunca comunal",
    "National and regional; never disaggregate to comuna":
        "nacional y regional; nunca se desagrega a comuna",
    "National/regional; the provincia/comuna complement does not confer comuna representativeness":
        "nacional o regional; el complemento de provincia y comuna no otorga representatividad comunal",
    # -- denominador posible --------------------------------------------------------------------------
    "All GRD episodes of the same year and hospital panel (per 100,000 episodes); INE base-2017 population by age and sex for complementary population rates":
        "todos los episodios GRD del mismo año y panel hospitalario (por 100.000 episodios); población INE base 2017 por edad y sexo para las tasas poblacionales complementarias",
    "INE base-2017 population by age/sex (A05); number of reporting establishments and stable panel; APS enrolment as operational coverage; no ratios between stages of non-linkable sources":
        "población INE base 2017 por edad y sexo (A05); número de establecimientos reportantes y panel estable; inscritos APS como cobertura operativa; no se calculan cocientes entre etapas de fuentes no enlazables",
    "P2501878 total NANEAS under control only from December 2023; number of reporting establishments; INE population as territorial context":
        "P2501878, total de NANEAS bajo control, solo desde diciembre de 2023; número de establecimientos reportantes; población INE como contexto territorial",
    "All DEIS discharges of the same year; INE population":
        "todos los egresos DEIS del mismo año; población INE",
    "Public insurance coverage denominator by comuna, age group and sex (insurance layer, distinct from INE, APS and REM-20)":
        "denominador de cobertura del seguro público por comuna, grupo de edad y sexo (capa previsional, distinta de INE, APS y REM-20)",
    "Operational coverage per centre (offset for REM primary-care indicators); continuous panel of 1,871 centre codes retains 99.87% of 2019 and 97.54% of 2025 totals":
        "cobertura operativa por centro (offset de los indicadores REM de atención primaria); el panel continuo de 1.871 códigos de centro retiene el 99,87 % de los totales de 2019 y el 97,54 % de los de 2025",
    "Private insurance coverage layer; FONASA + ISAPRE equals 95.63% (2019) and 97.24% (2025) of INE projection (not a non-insurance rate)":
        "capa de cobertura del seguro privado; FONASA + ISAPRE equivale al 95,63 % (2019) y al 97,24 % (2025) de la proyección INE (no es una tasa de no aseguramiento)",
    "Territorial population denominator for rates per 100,000 inhabitants and WHO direct standardisation":
        "denominador poblacional territorial para las tasas por 100.000 habitantes y la estandarización directa OMS",
    "Population denominator (same as INE base 2017)": "denominador poblacional (el mismo del INE base 2017)",
    "National sensitivity denominator": "denominador de sensibilidad nacional",
    "Observed 2024 denominator and bridge between census bases (sensitivity)":
        "denominador observado de 2024 y puente entre bases censales (sensibilidad)",
    "Hospital activity/capacity intensity; not a covered population. Panel of 188 establishments with 12 months in every year 2019-2025 retains 99.76% of 2019 and 98.16% of 2025 discharges":
        "intensidad de actividad y capacidad hospitalaria; no es población cubierta. El panel de 188 establecimientos con 12 meses en todos los años 2019-2025 retiene el 99,76 % de los egresos de 2019 y el 98,16 % de los de 2025",
    "Weighted survey population of each domain (adults; children/adolescents)":
        "población ponderada de la encuesta en cada dominio (adultos; niños, niñas y adolescentes)",
    "Weighted population aged 15+": "población ponderada de 15 años y más",
    "Weighted population by insurance scheme (context for public/private coverage)":
        "población ponderada por sistema previsional (contexto de cobertura pública y privada)",
    "Total enrolment in the same PIE/school universe when published":
        "matrícula total del mismo universo PIE o escolar cuando se publica",
    "Weighted students of the same level and year": "estudiantes ponderados del mismo nivel y año",
    "not applicable (covariate)": "no aplica (covariable)",
    # -- notas de concordancia con el manifiesto (provenance_manifest_checks.csv) ----------------------
    "not listed in any manifest": "no listado en ningún manifiesto",
    "no date in manifest": "sin fecha en el manifiesto",
    "no date in manifest (consolidated 2026-09-02 per data-root README)":
        "sin fecha en el manifiesto (consolidado el 2026-09-02 según el README de la raíz de datos)",
    "date = normalisation date in REM/SerieA/.rem_manifest.json":
        "fecha = fecha de normalización en REM/SerieA/.rem_manifest.json",
}

#: Notas del manifiesto que llevan una cifra dentro: (patrón inglés, plantilla española).
PROVENANCE_RULES: tuple[tuple[str, str], ...] = (
    (r"^canonical records=([\d,]+); date = consolidation date of the manifest$",
     r"registros canónicos=\1; fecha = fecha de consolidación del manifiesto"),
)
_PROVENANCE_RULES = [(_re.compile(p), t) for p, t in PROVENANCE_RULES]

#: Nota que solo lleva identificadores técnicos (estado, URL de origen, miembro del zip): no es prosa.
_PROVENANCE_TECHNICAL = _re.compile(r"^(status|source_url|source_zip|member)=")


def _group_separators(text: str, lang: str) -> str:
    """Reescribe los miles de un texto al separador del idioma pedido («167,405» ↔ «167.405»).

    Solo toca los grupos de tres dígitos completos que no van pegados a un decimal, de modo que
    «4.39», «0,29 %» o «2026-09-04» quedan intactos."""
    if lang == "es":
        return _re.sub(r"(?<![\d.,])(\d{1,3}(?:,\d{3})+)(?![\d,.])",
                       lambda m: m.group(1).replace(",", "."), str(text))
    return _re.sub(r"(?<![\d.,])(\d{1,3}(?:\.\d{3})+)(?![\d.,])",
                   lambda m: m.group(1).replace(".", ","), str(text))


def provenance_text(value, lang: str) -> str:
    """Campo descriptivo de la procedencia escrito en `lang`; el valor tal cual si no está declarado.

    La forma canónica es la inglesa (la que guarda `data_provenance.csv`). Un valor nuevo sin traducir
    vuelve tal cual y `tests/test_language_purity.py` lo denuncia."""
    if lang not in ("es", "en"):
        raise ValueError(f"idioma desconocido: {lang!r}")
    s = str(value or "").strip()
    if not s or lang == "en":
        return s
    if s in PROVENANCE_TEXT:
        return PROVENANCE_TEXT[s]
    if _PROVENANCE_TECHNICAL.match(s):
        return s
    for pattern, template in _PROVENANCE_RULES:
        m = pattern.match(s)
        if m:
            return _group_separators(m.expand(template), lang)
    return s
