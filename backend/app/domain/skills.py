"""Skill vocabulary shared by résumé parsing, employer needs and matching.

Pure data plus pure functions. No DB, no FastAPI: the API layer passes raw
strings in and gets canonical skill codes back, so the same normalization is
applied to a parsed résumé, to a typed need and to a search filter.
"""
from __future__ import annotations

import re

# Canonical code -> human label. The label is what both cabinets display.
SKILLS: dict[str, str] = {
    "python": "Python",
    "go": "Go",
    "java": "Java",
    "kotlin": "Kotlin",
    "swift": "Swift",
    "csharp": "C#",
    "cpp": "C++",
    "php": "PHP",
    "ruby": "Ruby",
    "rust": "Rust",
    "typescript": "TypeScript",
    "javascript": "JavaScript",
    "react": "React",
    "vue": "Vue",
    "angular": "Angular",
    "nextjs": "Next.js",
    "nodejs": "Node.js",
    "django": "Django",
    "fastapi": "FastAPI",
    "spring": "Spring",
    "dotnet": ".NET",
    "flutter": "Flutter",
    "react-native": "React Native",
    "android": "Android",
    "ios": "iOS",
    "postgresql": "PostgreSQL",
    "mysql": "MySQL",
    "mongodb": "MongoDB",
    "clickhouse": "ClickHouse",
    "redis": "Redis",
    "kafka": "Kafka",
    "rabbitmq": "RabbitMQ",
    "elasticsearch": "Elasticsearch",
    "sql": "SQL",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "linux": "Linux",
    "nginx": "Nginx",
    "terraform": "Terraform",
    "ansible": "Ansible",
    "ci-cd": "CI/CD",
    "prometheus": "Prometheus",
    "grafana": "Grafana",
    "aws": "AWS",
    "git": "Git",
    "api-design": "Проектирование API",
    "microservices": "Микросервисы",
    "highload": "Highload",
    "statistics": "Статистика",
    "pytorch": "PyTorch",
    "tensorflow": "TensorFlow",
    "pandas": "Pandas",
    "spark": "Spark",
    "airflow": "Airflow",
    "nlp": "NLP",
    "cv": "Computer Vision",
    "mlops": "MLOps",
    "pytest": "Pytest",
    "selenium": "Selenium",
    "playwright": "Playwright",
    "postman": "Postman",
    "test-design": "Тест-дизайн",
    "autotests": "Автотесты",
    "jmeter": "JMeter",
}

# Everything a human might actually write, mapped onto a canonical code.
ALIASES: dict[str, str] = {
    "golang": "go",
    "питон": "python",
    "пайтон": "python",
    "джава": "java",
    "ts": "typescript",
    "тайпскрипт": "typescript",
    "js": "javascript",
    "джаваскрипт": "javascript",
    "node": "nodejs",
    "node.js": "nodejs",
    "nest": "nodejs",
    "nestjs": "nodejs",
    "reactjs": "react",
    "react.js": "react",
    "реакт": "react",
    "vuejs": "vue",
    "vue.js": "vue",
    "next": "nextjs",
    "next.js": "nextjs",
    "c#": "csharp",
    "c sharp": "csharp",
    "шарп": "csharp",
    "c++": "cpp",
    "си++": "cpp",
    "плюсы": "cpp",
    ".net": "dotnet",
    "asp.net": "dotnet",
    "дотнет": "dotnet",
    "postgres": "postgresql",
    "pg": "postgresql",
    "постгрес": "postgresql",
    "постгресql": "postgresql",
    "мускул": "mysql",
    "mongo": "mongodb",
    "монго": "mongodb",
    "редис": "redis",
    "кафка": "kafka",
    "рэббит": "rabbitmq",
    "rabbit": "rabbitmq",
    "elastic": "elasticsearch",
    "эластик": "elasticsearch",
    "ch": "clickhouse",
    "кликхаус": "clickhouse",
    "докер": "docker",
    "k8s": "kubernetes",
    "к8с": "kubernetes",
    "кубер": "kubernetes",
    "кубернетес": "kubernetes",
    "линукс": "linux",
    "нжинкс": "nginx",
    "ci/cd": "ci-cd",
    "cicd": "ci-cd",
    "сicd": "ci-cd",
    "gitlab ci": "ci-cd",
    "github actions": "ci-cd",
    "jenkins": "ci-cd",
    "гит": "git",
    "терраформ": "terraform",
    "ансибл": "ansible",
    "графана": "grafana",
    "прометей": "prometheus",
    "прометеус": "prometheus",
    "амазон": "aws",
    "rest": "api-design",
    "rest api": "api-design",
    "restful": "api-design",
    "grpc": "api-design",
    "graphql": "api-design",
    "апи": "api-design",
    "микросервис": "microservices",
    "микросервисы": "microservices",
    "хайлоад": "highload",
    "высокие нагрузки": "highload",
    "высоконагруженные": "highload",
    "матстат": "statistics",
    "статистика": "statistics",
    "мат. статистика": "statistics",
    "торч": "pytorch",
    "torch": "pytorch",
    "tf": "tensorflow",
    "пандас": "pandas",
    "спарк": "spark",
    "эирфлоу": "airflow",
    "ml": "mlops",
    "ml-ops": "mlops",
    "машинное обучение": "mlops",
    "нлп": "nlp",
    "компьютерное зрение": "cv",
    "opencv": "cv",
    "пайтест": "pytest",
    "селениум": "selenium",
    "плейрайт": "playwright",
    "постман": "postman",
    "тест дизайн": "test-design",
    "тест-дизайн": "test-design",
    "автотесты": "autotests",
    "автотестирование": "autotests",
    "джиметр": "jmeter",
    "флаттер": "flutter",
    "rn": "react-native",
    "андроид": "android",
    "айос": "ios",
    "котлин": "kotlin",
    "свифт": "swift",
    "джанго": "django",
    "фастапи": "fastapi",
    "спринг": "spring",
    "спринг бут": "spring",
    "spring boot": "spring",
}

# Skills that a specialization is normally built from. Used to weight a skill
# that the employer did not name explicitly but that still signals fit.
CORE_SKILLS: dict[str, set[str]] = {
    "backend": {"python", "go", "java", "csharp", "php", "ruby", "rust", "cpp", "postgresql",
                "mysql", "mongodb", "redis", "kafka", "rabbitmq", "sql", "api-design",
                "microservices", "highload", "django", "fastapi", "spring", "dotnet", "nodejs"},
    "frontend": {"typescript", "javascript", "react", "vue", "angular", "nextjs", "nodejs"},
    "mobile": {"kotlin", "swift", "java", "flutter", "react-native", "android", "ios"},
    "data": {"python", "sql", "statistics", "pytorch", "tensorflow", "pandas", "spark",
             "airflow", "nlp", "cv", "mlops", "clickhouse"},
    "devops": {"docker", "kubernetes", "linux", "nginx", "terraform", "ansible", "ci-cd",
               "prometheus", "grafana", "aws", "git"},
    "qa": {"pytest", "selenium", "playwright", "postman", "test-design", "autotests",
           "jmeter", "sql", "python"},
}

# Russian case/number endings a skill name realistically takes, plus the
# "-ист" profession family. Matching an explicit list instead of "any letters"
# keeps "гитара" from resolving to git and "торчать" from resolving to torch.
_ENDINGS = (
    "а ам ами ах е ев ей ем ю я ям ями ях и ии ий им ими их ов ого ой ом ому "
    "у ы ых ую ые ый ист иста исте истом исту исты истов истам истами истах"
).split()
_ENDING_RE = "(?:" + "|".join(sorted(_ENDINGS, key=len, reverse=True)) + ")?"
_VOWELS = "аеиоуыэюя"


def _russian_stem(term: str) -> str:
    """Drop one trailing vowel so that "кафка" also matches "кафкой"."""
    return term[:-1] if len(term) > 4 and term[-1] in _VOWELS else term


_LOOKUP: dict[str, str] = {}
for _code, _label in SKILLS.items():
    _LOOKUP[_code] = _code
    _LOOKUP[_label.lower()] = _code
_LOOKUP.update(ALIASES)

# Longest alias first so that "react native" never degrades into "react".
_SORTED_TERMS = sorted(_LOOKUP, key=len, reverse=True)


def normalize(raw: str) -> str | None:
    """Map one written skill onto its canonical code, or None if unknown."""
    key = raw.strip().lower().replace("ё", "е")
    return _LOOKUP.get(key)


def normalize_many(values) -> list[str]:
    """Normalize a list, drop unknown values, keep the order, de-duplicate."""
    out: list[str] = []
    for value in values or []:
        code = normalize(str(value))
        if code and code not in out:
            out.append(code)
    return out


def extract(text: str) -> list[str]:
    """Pull canonical skills out of free-form Russian or English prose.

    The employer describes a need in their own words; this is what turns that
    paragraph into the structured requirement the matcher works with.
    """
    if not text:
        return []
    haystack = " " + re.sub(r"[^0-9a-zа-я+#./\- ]+", " ", text.lower().replace("ё", "е")) + " "
    found: list[str] = []
    for term in _SORTED_TERMS:
        code = _LOOKUP[term]
        if code in found:
            continue
        # Alphanumeric terms need word boundaries; terms with punctuation such
        # as "c++" or "ci/cd" are matched as padded substrings instead.
        if re.fullmatch(r"[0-9a-zа-я ]+", term):
            # Russian terms are matched through their inflection, because the
            # employer writes "ищу питониста с кафкой", not a list of lemmas.
            # Short terms are excluded so that "гит" does not match "гитара".
            if len(term) >= 4 and re.search(r"[а-я]", term):
                body = re.escape(_russian_stem(term)) + _ENDING_RE
            else:
                body = re.escape(term)
            pattern = r"(?<![0-9a-zа-я])" + body + r"(?![0-9a-zа-я])"
        else:
            pattern = re.escape(term)
        if re.search(pattern, haystack):
            found.append(code)
    return found


def label(code: str) -> str:
    return SKILLS.get(code, code)


def labels(codes) -> list[str]:
    return [label(code) for code in codes or []]
