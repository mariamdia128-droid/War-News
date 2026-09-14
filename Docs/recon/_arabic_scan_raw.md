# Raw Arabic scan (auto)

## app\sources\services\red_alert_collector.py (35 hits)

- L39: `    "علي الطاهر": 71115,`
- L40: `    "برج الشمالي": 62128,`
- L41: `    "لمنصوريى": 62296,`
- L42: `    "عين بعال": 62243,`
- L43: `    "وادي حيلو": 62218,`
- L44: `    "دى حيلو": 62218,`
- L68: `            "معم سر",`
- L69: `            "معمر سر",`
- L79: `            "كوترية",`
- L85: `        "لبنان",`
- L86: `        "تحليق",`
- L87: `        "تحديث",`
- L88: `        "مسير",`
- L89: `        "مسيره",`
- L90: `        "مقاتلات حربيه",`
- L91: `        "طيران حربي",`
- L92: `        "اقصى درجات الحذر",`
- L93: `        "الخريطه المباشره",`
- L99: `    "الخريطة",`
- L100: `    "تبرع الان",`
- L101: `    "عزز القناة",`
- L106: `    "احصاءات نهاية اليوم",`
- L107: `    "إحصاءات نهاية اليوم",`
- L108: `    "اجمالي التنبيهات",`
- L109: `    "إجمالي التنبيهات",`
- L110: `    "اكثر القرى رصدا",`
- L111: `    "أكثر القرى رصداً",`
- L112: `    "نرجو منكم ابلاغنا فورا",`
- L113: `    "عبر البوت الجديد",`
- L147: `    value = value.translate(str.maketrans("أإآٱىةؤئ", "اااايهوي"))`
- L229: `            normalize_arabic("حيطة") in normalized`
- L230: `            or normalize_arabic("خبطة") in normalized`
- L232: `        and normalize_arabic("حذر") in normalized`
- L558: `                # "مسيّرة") in white text in the dark top-right header. A`
- L684: `                action_ar="نشاط جوي بحاجة إلى التحقق",`

## app\api\rejected_news_router.py (33 hits)

- L54: `        (("general multi-area alert", "no single village applies"), "التنبيه عام ويشمل عدة مناطق، لذلك لا ينطبق على بلدة واحدة."),`
- L55: `        (("location could not be identified reliably from the alert image",), "تعذّر تحديد المنطقة بدقة من صورة التنبيه."),`
- L56: `        (("no locality was specified in the red alert notice",), "لم يحدّد تنبيه Red Alert بلدة بعينها."),`
- L57: `        (("no canonical village matched", "no village matched", "unmatched village"), "لم يتم العثور على بلدة معتمدة مطابقة للخبر."),`
- L58: `        (("no canonical condition matched", "no condition matched", "unmatched condition"), "لم يتم العثور على حالة أو نوع حدث معتمد مطابق للخبر."),`
- L59: `        (("not related to lebanon", "not relevant to lebanon", "outside lebanon"), "الخبر غير مرتبط بلبنان."),`
- L60: `        (("location is unclear", "unclear location"), "موقع الحدث غير واضح."),`
- L61: `        (("relevance was uncertain", "uncertain relevance"), "لم يتمكن النظام من التأكد من ارتباط الخبر، ويحتاج إلى مراجعة."),`
- L62: `        (("classified as not relevant", "not relevant", "irrelevant"), "صُنّف الخبر على أنه غير مرتبط بنطاق الأحداث المطلوبة."),`
- L68: `        return "الخبر مكرر ومطابق لخبر خام آخر."`
- L70: `        return "سبب الرفض غير مؤكد ويحتاج الخبر إلى مراجعة إدارية."`
- L72: `        return "صُنّف الخبر على أنه غير مرتبط بنطاق الأحداث المطلوبة."`
- L77: `    return "رُفض الخبر أثناء المعالجة الآلية ويحتاج إلى مراجعة إدارية."`
- L87: `    normalized = re.sub(r"[^\w\s\u0600-\u06ff.,،:؛!?؟-]", " ", normalized)`
- L88: `    normalized = re.sub(r"\s+", " ", normalized).strip(" .،,:؛-")`
- L95: `        or ("حيطة" in normalized and "حذر" in normalized)`
- L100: `    if ("آخر تحديث" in normalized or "اخر تحديث" in normalized) and ("المسير" in normalized or "مسيرة" in normalized):`
- L101: `        return "تحديث: نشاط طائرات مسيّرة معادية في أجواء لبنان. يُرجى الحيطة والحذر."`
- L102: `    if is_red_alert and any(keyword in normalized for keyword in ("مقاتلات حربية", "طيران حربي")):`
- L103: `        return "رُصد طيران حربي في الأجواء اللبنانية. يُرجى الحيطة والحذر."`
- L104: `    if is_red_alert and any(keyword in normalized for keyword in ("مروحية", "مروحيات", "هليكوبتر", "كوتريّة")):`
- L105: `        return "رُصدت مروحية في الأجواء اللبنانية. يُرجى الحيطة والحذر."`
- L107: `        return "رُصدت طائرة مسيّرة. تعذّر تحديد المنطقة بدقة من الصورة."`
- L109: `    if "مقاتلات حربية" in normalized and "لبنان" in normalized:`
- L110: `        return "رُصدت مقاتلات حربية متجهة نحو لبنان."`
- L111: `    if "مسيرة" in normalized or "مسيّرة" in normalized:`
- L112: `        return "رُصدت طائرة مسيّرة، لكن تعذّر تحديد البلدة من النص."`
- L113: `    if "غارة" in normalized:`
- L114: `        return "أُفيد عن غارة، لكن تعذّر تحديد موقع الحدث بدقة من النص."`
- L116: `        return "تعذّر استخراج ملخص واضح من الخبر الأصلي."`
- L122: `    if shortened[-1:] not in ".!?؟":`
- L131: `        arabic = f"الخبر مكرر ومطابق للخبر الخام{target}."`
- L145: `        if ("آخر تحديث" in text or "اخر تحديث" in text) and "لبنان" in text:`

## app\news\services\incident_details\category_mapper.py (29 hits)

- L104: `    {"مدرسة", "school", "ثانوية", "ابتدائية", "رياض"}`
- L107: `    {"جامعة", "university", "معهد", "كلية", "college"}`
- L110: `    {"كنيسة", "church", "chapel", "كاتدرائية"}`
- L112: `_MOSQUE_KEYWORDS: frozenset[str] = frozenset({"مسجد", "mosque", "جامع"})`
- L113: `_CEME_KEYWORDS: frozenset[str] = frozenset({"مقبرة", "cemetery", "مدفن"})`
- L115: `    {"أثري", "archeolog", "تراث", "heritage"}`
- L117: `_RELEG_KEYWORDS: frozenset[str] = frozenset({"ديني", "religious", "مزار", "shrine"})`
- L118: `_BRIDGE_KEYWORDS: frozenset[str] = frozenset({"جسر", "bridge"})`
- L119: `_ROAD_KEYWORDS: frozenset[str] = frozenset({"طريق", "road", "أوتوستراد", "autostrada"})`
- L121: `    {"قطع", "blocked", "تعذر", "مسدود", "blockage"}`
- L123: `_LITANI_KEYWORDS: frozenset[str] = frozenset({"litani", "ليتاني", "الليتاني"})`
- L124: `_ZAHRANI_KEYWORDS: frozenset[str] = frozenset({"zahrani", "زرقاني", "الزرقاني"})`
- L125: `_DRONE_KEYWORDS: frozenset[str] = frozenset({"drone", "محلقة", "مسيرة", "طائرة مسيرة"})`
- L126: `_WATER_KEYWORDS: frozenset[str] = frozenset({"water", "مياه", "آبار", "بئر", "سقاية"})`
- L127: `_ELECTRIC_KEYWORDS: frozenset[str] = frozenset({"electric", "كهرب", "محطة كهرب"})`
- L128: `_OLIVE_KEYWORDS: frozenset[str] = frozenset({"olive", "زيتون", "أشجار"})`
- L129: `_MJNOUB_KEYWORDS: frozenset[str] = frozenset({"mjnoub", "مجنوب"})`
- L132: `    "سيارة",`
- L133: `    "سيارات",`
- L134: `    "آلية إسعاف",`
- L135: `    "آليات إسعاف",`
- L137: `_ARABIC_DIGIT_MAP = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")`
- L139: `    r"(\d+)\s*(?:سيارة|سيارات)|(?:سيارة|سيارات)\s*(\d+)"`
- L327: `    """Best-effort count next to سيارة/سيارات; returns None when no numeral found."""`
- L477: `    if "no_warning" in name or "لا تحذير" in name:`
- L479: `    elif "warning" in name or "تحذير" in name:`
- L481: `    if "genocide" in name or "إبادة" in name:`
- L483: `    if "building" in name or "مبن" in name or "مبان" in name:`
- L485: `    if "apart" in name or "شقة" in name or "شقق" in name:`

## app\news\services\incident_details\casualty_transition_backstop.py (19 hits)

- L21: `        "استشهاد أحد جريحي/الجرحى",`
- L22: `        re.compile(r"استشهاد احد (?:جريحي|الجرحى)"),`
- L25: `        "وفاة أحد المصابين متأثراً بجراحه",`
- L26: `        re.compile(r"وفاه احد المصابين.{0,40}متاثر.{0,10}بجراح"),`
- L29: `        "فارق أحد الجرحى الحياة",`
- L30: `        re.compile(r"فارق احد الجرحى الحياه"),`
- L33: `        "توفي أحد الجرحى/المصابين",`
- L34: `        re.compile(r"توف[ىي] احد (?:الجرحى|المصابين)"),`
- L37: `        "توفي واحد من الجرحى",`
- L39: `            r"(?:بقي.{0,30}(?:جريح|جرحي).{0,40}توف[ىي] واحد(?:ا)?"`
- L40: `            r"|توف[ىي] واحد(?:ا)? من (?:الجرحى|الجرحي|جرحى|جرحي|المصابين))"`
- L44: `        "أحد الجرحى استشهد",`
- L45: `        re.compile(r"احد (?:جريحي|الجرحى|المصابين).{0,40}(?:استشهد|توف[ىي]|فارق)"),`
- L48: `        "وفاة/توفي جريح متأثراً بإصابته أو بجراحه",`
- L49: `        re.compile(r"(?:وفاه|توف[ىي]).{0,20}جريح.{0,40}متاثر.{0,10}(?:باصابت|بجراح)"),`
- L52: `        "استشهاد/وفاة متأثراً بجراحه التي أصيب بها",`
- L53: `        re.compile(r"(?:استشهاد|استشهد|وفاه|توف[ىي]).{0,60}متاثر.{0,10}بجراح.{0,40}اصيب بها"),`
- L56: `        "فارق الحياة بعد إصابة سابقة",`
- L57: `        re.compile(r"فارق الحياه.{0,60}(?:جرح|اصيب|اصابته|بجراح)"),`

## app\news\services\incident_details\story_revision_backstop.py (13 hits)

- L22: `    ("حصيلة أولية", re.compile(r"حصيله اوليه")),`
- L23: `    ("حصيلة مؤقتة", re.compile(r"حصيله مؤقته")),`
- L24: `    ("تحديث الحصيلة", re.compile(r"تحديث الحصيله")),`
- L25: `    ("ارتفاع عدد الشهداء/الجرحى", re.compile(r"ارتفاع عدد.{0,20}(?:الشهداء|الجرحى|الشهيد|الجريح)")),`
- L26: `    ("ارتفع عدد", re.compile(r"ارتفع عدد.{0,20}(?:الشهداء|الجرحى|الشهيد|الجريح)")),`
- L27: `    ("المعلومات الأولية", re.compile(r"المعلومات الاوليه")),`
- L28: `    ("معلومات أولية", re.compile(r"معلومات اوليه")),`
- L32: `    ("تنعى", re.compile(r"تنعي")),`
- L33: `    ("الموظفة/الموظف named martyr", re.compile(r"الموظف(?:ه)?.{0,40}(?:ارتقت|ارتقى|استشهد|شهيد)")),`
- L34: `    ("الشهيدة + given name", re.compile(r"الشهيده\s+\S{2,}\s+\S{2,}")),`
- L35: `    ("زهراء-style full name + martyrdom", re.compile(r"[\u0600-\u06ff]{3,}\s+[\u0600-\u06ff]{3,}.{0,40}(?:ارتقت|استشهدت|شهيده)")),`
- L38: `_NUMERIC_TOLL = re.compile(r"[0-9٠-٩]+")`
- L39: `_NAMED_IN_CANDIDATE = re.compile(r"تنعي|الشهيده\s+\S{2,}\s+\S{2,}")`

## app\news\services\clustering\raw_message_embedding_service.py (9 hits)

- L13: `            r"(?:🏴\s*)?ملخص\s+ال[اإ]عتداءات\s+"`
- L14: `            r"(?:لهذا اليوم|من منتصف الليل حتى الساعة)\s*:?\s*"`
- L20: `            r"^\s*🌟?\s*صفحة الإعلامي الشهيد علي شعيب\s*[:：]\s*[●•]?\s*"`
- L25: `        re.compile(r"^\s*(?:🚨+|🔴+)\s*(?:عاجل\s*[|:،\-–—]?\s*)?"),`
- L34: `            r"\s*─{5,}.*📲\s*قناة بنت جبيل على واتساب.*$",`
- L43: `            r"^\s*[«“\"']?\s*الوكالة الوطنية(?:\s+للإعلام)?"`
- L50: `            r"^\s*(?:لبنان\s*[:：]\s*)?مراسل(?:ة)?\s+الميادين"`
- L51: `            r"(?:\s+في\s+[^:：\n]{1,80})?\s*[:：]\s*"`
- L57: `            r"^\s*[«“\"']?\s*لبنان\s*24\s*[»”\"']?\s*[:：]\s*"`

## app\news\services\incident_details\casualty_gender_evidence.py (8 hits)

- L21: `    """Match *word* as a standalone token, allowing optional و / ال prefixes.`
- L23: `    The definite article ``ال`` is explicitly permitted so forms like`
- L24: `    ``الشهيدة`` match. Any other preceding Arabic letter still rejects the`
- L28: `        rf"(?<![{_ARABIC_LETTER}])(?:و)?(?:ال)?(?:{word})(?![{_ARABIC_LETTER}])"`
- L74: `    return str(value).translate(str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩"))`
- L146: `    rf"(?:شهيد|استشهاد)\s+(?:ال)?(?:{_role_alternation(_MALE_ROLE_NOUNS)})"`
- L150: `    rf"(?:شهيده|استشهاد)\s+(?:ال)?(?:{_role_alternation(_FEMALE_ROLE_NOUNS)})"`
- L161: `    ``شهيد مسعف`` / ``استشهاد مسعف`` increment ``male_deaths`` even when the`

## app\core\text_normalization.py (6 hits)

- L9: `ARABIC_EDGE_PUNCTUATION = "،.؛!؟\"'"`
- L10: `ENGLISH_EDGE_PUNCTUATION = string.punctuation + "،؛؟"`
- L11: `ARABIC_ALEF_VARIANTS = "أإآٱة"`
- L12: `ARABIC_NORMALIZED_VARIANTS = "ااااه"`
- L26: `    normalized = normalized.replace("ى", "ي")`
- L56: `    normalized_letters = func.replace(normalized_letters, "ى", "ي")`

## app\news\repositories\air_violation_repository.py (6 hits)

- L53: `        return f"{condition.action_ar} - الموقع بحاجة إلى التحقق"`
- L62: `        f"{condition.action_ar} فوق {village_name} في قضاء {caza_name}"`
- L64: `        else f"{condition.action_ar} في قضاء {caza_name}"`
- L67: `    if "حيطة" in raw_text and "حذر" in raw_text:`
- L68: `        summary += " - حيطة وحذر"`
- L97: `        return "Multiple regions", "مناطق متعددة"`

## app\news\services\matching\village_aliases.py (6 hits)

- L63: `    "وادي السلوقي / السلوقي: fuzzy hits Ouadi Es-Sitt (Chouf) or Slouqi (Baalbek); "`
- L65: `    "وادي الحجير / الحجير: no ACS village entry; fuzzy hits unrelated Ouadi Ed-Deir.",`
- L66: `    "الفوقا (bare): three-way tie Houmine / Nabatiyeh El-Faouka / Temnine — too ambiguous.",`
- L67: `    "بسطرة: unmatched; no ACS row found.",`
- L68: `    "بين الحنية و المنصوري (and similar between-X-and-Y): multi-location, not a single parent.",`
- L69: `    "Generic descriptor strip (محيط/أطراف/حرش/وادي) remains a separate pending task; "`

## app\llm\services\ollama_presence_gate_service.py (6 hits)

- L401: `            if any(term in evidence_span for term in ("الطريق", "الجسر", "الأوتوستراد")) and not any(`
- L403: `                for term in ("استهدف الطريق", "استهدفت الطريق", "قطع", "تعذر مرور")`
- L408: `            if "مواكبة" in text or "بمواكبة" in text:`
- L411: `                    for term in ("استهدف الجيش", "استهدفت الجيش", "أصيب عسكري", "قتل عسكري")`
- L415: `            if "قسم الطوارئ" in text and not any(`
- L434: `            if "إلى المستشفى" in text or "الى المستشفى" in text:`

## app\news\services\incident_details\casualty_count_backstop.py (5 hits)

- L24: `_WESTERN_TO_ARABIC_INDIC = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")`
- L31: `        return tuple(term for term in words if term.endswith(("ان", "ين")))`
- L32: `    return tuple(term for term in words if not term.endswith(("ان", "ين")))`
- L63: `        rf"(?<![0-9٠-٩])(?:{re.escape(western)}|{re.escape(arabic_indic)})"`
- L64: `        rf"(?![0-9٠-٩])"`

## app\news\services\matching\condition_evidence_override.py (5 hits)

- L7: `    re.compile(r"قصف.{0,40}(?:دباب[ةه]|ميركافا)"),`
- L8: `    re.compile(r"(?:دباب[ةه]|ميركافا).{0,100}(?:تستهدف|تقصف|تطلق)"),`
- L10: `_WARNING_RAID = re.compile(r"غار[ةه].{0,15}تحذيري|تحذيري.{0,15}غار[ةه]")`
- L11: `_FEIGNED_RAID = re.compile(r"غارات?.{0,15}وهمي|وهمي.{0,15}غارات?")`
- L12: `_AIRSTRIKE = re.compile(r"(?:غار[ةه]|غارات|أغار|اغار)")`

## app\news\services\air_violations\import_source_enrichment.py (4 hits)

- L104: `    remainder, count = re.subn(r'^(?:مسير[ةه]?|طيران استطلاعي|طيران حربي|طيران مروحي)\s+(?:(?:فوق|في)\s+)?', '', text.strip())`
- L116: `    } and normalize_arabic(import_location_text(text)) == 'المنزله':`
- L136: `    aliases = {'كفره': 72257, 'شعث': 53274, 'النبطيه': 71111}`
- L148: `        if name and name.removeprefix('ال') == key.removeprefix('ال'):`

## app\news\services\dedup\story_relationship_service.py (4 hits)

- L23: `_HOUSE_RE = re.compile(r"منزل|بيت|مبنى|بنايه|شقه")`
- L24: `_CAR_RE = re.compile(r"سيار|دراج")`
- L25: `_SPARSE_RE = re.compile(r"اصابات|ضحايا|وقوع")`
- L26: `_DIGIT_RE = re.compile(r"[0-9٠-٩]")`

## app\news\services\matching\matching_service.py (4 hits)

- L40: `# confident match. Recon showed five * النبطية villages tied at ~0.615 with`
- L41: `# margin 0.0 (lowest id won). Unambiguous hits like النبطية الفوقا had`
- L57: `    2: _distinguishing_tokens("Warning Raid") or ("تحذيريه",),`
- L58: `    39: _distinguishing_tokens("Feigned Attacks") or ("وهميه",),`

## app\llm\services\ollama_category_detail_service.py (4 hits)

- L30: `    if term in {"دراج", "موتور"}`
- L31: `) or ("دراج", "موتور")`
- L191: `                        f"النص:\n{post_text}"`
- L222: `                        f"النص:\n{post_text}"`

## app\llm\services\ollama_extraction_service.py (3 hits)

- L45: `    r"طريق(?:\s+عام)?\s+"`
- L49: `    r"(?=$|[\n،؛.!؟])"`
- L51: `_ROUTE_AREA_PREFIXES = ("مرج ",)`

## app\llm\services\cnrs_extraction_fallback.py (2 hits)

- L26: `_MOTORCYCLE_TEXT_MARKERS = ("دراج", "موتور")`
- L38: `        return "Tank Fire" if "دبابة" in post_text else "Bombs"`

## app\news\models\emergency_organization.py (1 hits)

- L26: `    # Alias phrasings (e.g. "سيارة إسعاف") scored via word_similarity() alongside`

## app\news\models\village_location_alias.py (1 hits)

- L13: `    themselves (e.g. مدينة النبطية, حي المسلخ) so fuzzy matching does not`

## app\news\services\air_violations\red_alert_air_violation_service.py (1 hits)

- L63: `        if ("آخر تحديث" in text or "اخر تحديث" in text) and "لبنان" in text:`

## app\news\services\incident_details\casualty_scope_backstop.py (1 hits)

- L23: `            rf"(?<![\w])(?:و)?{re.escape(phrase)}(?![\w])",`
