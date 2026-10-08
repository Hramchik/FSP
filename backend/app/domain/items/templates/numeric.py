"""Deterministic, server-graded task families for all six MVP specializations.

An item instance is reconstructed from (template_code, seed). The expected
answer is deliberately never part of ItemInstance and is never serialized by
an API response.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import random
import re


@dataclass(frozen=True)
class ItemInstance:
    template_code: str
    seed: int
    prompt: str
    answer_type: str = "integer"
    options: tuple[str, ...] = ()


def _rng(seed: int, salt: str) -> random.Random:
    digest = hashlib.sha256(f"{salt}:{seed}".encode()).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def _parts(template_code: str) -> tuple[str, str]:
    match = re.fullmatch(r"([a-z]+)_([a-z_]+)_v(\d{2})_(junior|middle|senior|lead)", template_code)
    if not match:
        # Backward-compatible parser for old templates while they are being
        # retired by the seed script.
        spec = template_code.split("_", 1)[0]
        return spec, "legacy"
    return match.group(1), match.group(2)


def _task(template_code: str, seed: int) -> tuple[str, int]:
    rng = _rng(seed, template_code)
    spec, family = _parts(template_code)
    case_id = hashlib.sha256(f"case:{template_code}:{seed}".encode()).hexdigest()[:8]

    if family == "algorithms":
        n = rng.randint(40, 260)
        answer = n * (n - 1) // 2
        prompt = f"Бэкенд / алгоритмы [{case_id}]: полный перебор сравнивает каждую пару из {n} элементов ровно один раз. Сколько сравнений выполнится?"
    elif family == "sql":
        rows = rng.randint(5000, 50000)
        selectivity = rng.randint(5, 45)
        answer = rows * selectivity // 100
        prompt = f"Бэкенд / SQL [{case_id}]: запрос возвращает {selectivity}% из {rows} строк. Сколько строк вернёт запрос при целочисленном расчёте?"
    elif family == "api":
        requests = rng.randint(120, 5000)
        batch = rng.randint(8, 64)
        answer = math.ceil(requests / batch)
        prompt = f"Бэкенд / API [{case_id}]: нужно обработать {requests} запросов батчами по {batch}. Сколько батчей потребуется в худшем случае?"
    elif family == "concurrency":
        jobs = rng.randint(40, 500)
        workers = rng.randint(4, 32)
        duration = rng.randint(20, 180)
        answer = math.ceil(jobs / workers) * duration
        prompt = f"Бэкенд / конкурентность [{case_id}]: {jobs} независимых задач выполняются {workers} воркерами, каждая занимает {duration} мс. Сколько мс займёт выполнение при равномерном распределении?"
    elif family == "cache":
        requests = rng.randint(1000, 20000)
        hit_rate = rng.randint(70, 98)
        hit_cost = rng.randint(1, 5)
        miss_cost = rng.randint(20, 120)
        hits = requests * hit_rate // 100
        misses = requests - hits
        answer = hits * hit_cost + misses * miss_cost
        prompt = f"Бэкенд / кэш [{case_id}]: {requests} запросов, hit-rate {hit_rate}%, hit стоит {hit_cost} мс, miss — {miss_cost} мс. Какова суммарная задержка всех запросов в мс?"

    elif family == "js_ts":
        items = rng.randint(40, 300)
        keep = rng.randint(20, 80)
        answer = items * keep // 100
        prompt = f"Фронтенд / JS/TS [{case_id}]: массив содержит {items} элементов. Фильтр оставляет {keep}% элементов. Сколько элементов останется?"
    elif family == "browser":
        viewport = rng.randint(900, 2200)
        left = rng.randint(12, 80)
        right = rng.randint(12, 80)
        scrollbar = rng.choice([0, 15, 17])
        answer = viewport - left - right - scrollbar
        prompt = f"Фронтенд / браузер [{case_id}]: viewport {viewport}px, внешние отступы {left}px и {right}px, scrollbar {scrollbar}px. Какова доступная ширина контента?"
    elif family == "layout":
        items = rng.randint(20, 240)
        columns = rng.randint(2, 12)
        answer = math.ceil(items / columns)
        prompt = f"Фронтенд / вёрстка [{case_id}]: {items} карточек раскладываются в CSS Grid по {columns} колонок. Сколько строк нужно?"
    elif family == "state":
        initial = rng.randint(0, 20)
        increments = rng.randint(20, 200)
        decrements = rng.randint(5, 80)
        answer = initial + increments - decrements
        prompt = f"Фронтенд / состояние [{case_id}]: счётчик начинается с {initial}, получает {increments} инкрементов и {decrements} декрементов. Какое итоговое значение?"
    elif family == "http":
        assets = rng.randint(4, 40)
        size_kb = rng.randint(20, 500)
        compression = rng.randint(40, 80)
        answer = assets * size_kb * compression // 100
        prompt = f"Фронтенд / HTTP [{case_id}]: {assets} ресурсов по {size_kb} КБ каждый передаются после сжатия до {compression}% исходного размера. Сколько КБ передастся?"

    elif family == "lifecycle":
        launches = rng.randint(10, 80)
        callbacks = rng.randint(2, 8)
        answer = launches * callbacks
        prompt = f"Мобильная разработка / жизненный цикл [{case_id}]: приложение проходит {callbacks} обязательных lifecycle-callbacks при каждом из {launches} запусков. Сколько вызовов всего?"
    elif family == "async":
        tasks = rng.randint(30, 400)
        workers = rng.randint(2, 16)
        duration = rng.randint(20, 150)
        answer = math.ceil(tasks / workers) * duration
        prompt = f"Мобильная разработка / асинхронность [{case_id}]: {tasks} задач выполняются параллельно максимум по {workers}, каждая занимает {duration} мс. Сколько мс нужно?"
    elif family == "storage":
        records = rng.randint(500, 12000)
        bytes_per = rng.randint(100, 900)
        answer = records * bytes_per // 1024
        prompt = f"Мобильная разработка / хранение [{case_id}]: {records} записей занимают по {bytes_per} байт. Сколько полных КБ нужно без учёта метаданных?"
    elif family == "battery":
        capacity = rng.randint(2500, 6000)
        drain = rng.randint(3, 20)
        hours = rng.randint(1, 8)
        answer = capacity - drain * hours
        prompt = f"Мобильная разработка / батарея [{case_id}]: ёмкость {capacity} мА·ч, расход {drain} мА в течение {hours} часов. Сколько мА·ч останется?"
    elif family == "mobile_networking":
        payload = rng.randint(100, 5000)
        chunks = rng.randint(2, 12)
        answer = math.ceil(payload / chunks)
        prompt = f"Мобильная разработка / сеть [{case_id}]: payload {payload} КБ разбивается максимум на {chunks} равных частей. Каков размер крупнейшей части в КБ при целочисленном округлении вверх?"

    elif family == "sql_analytics":
        rows = rng.randint(10000, 100000)
        groups = rng.randint(10, 500)
        answer = rows // groups
        prompt = f"Данные и ML / SQL [{case_id}]: {rows} строк равномерно распределены по {groups} группам. Сколько строк приходится на одну полную группу?"
    elif family == "statistics":
        base = rng.randint(10, 100)
        spread = rng.randint(2, 20)
        values = [base + spread * i for i in range(5)]
        answer = sum(values) // len(values)
        prompt = f"Данные и ML / статистика [{case_id}]: пять наблюдений образуют арифметическую последовательность, первое {base}, шаг {spread}. Чему равно среднее?"
    elif family == "classification":
        tp = rng.randint(50, 900)
        fp = rng.randint(10, 150)
        fn = rng.randint(10, 150)
        p = tp * 10000 // (tp + fp)
        r = tp * 10000 // (tp + fn)
        answer = (2 * p * r) // max(p + r, 1)
        prompt = f"Данные и ML / метрики [{case_id}]: TP={tp}, FP={fp}, FN={fn}. Вычислите F1 в базисных пунктах (10000 = 1.0), округляя вниз."
    elif family == "pipeline":
        records = rng.randint(1000, 50000)
        per_minute = rng.randint(200, 3000)
        answer = math.ceil(records / per_minute)
        prompt = f"Данные и ML / pipeline [{case_id}]: нужно обработать {records} записей со скоростью {per_minute} записей/мин. Сколько полных минут потребуется?"
    elif family == "quality":
        total = rng.randint(500, 5000)
        error_rate = rng.randint(1, 15)
        answer = total * (100 - error_rate) // 100
        prompt = f"Данные и ML / качество модели [{case_id}]: из {total} прогнозов ошибка возникает в {error_rate}% случаев. Сколько прогнозов корректны?"

    elif family == "linux":
        read = rng.randint(1, 9)
        write = rng.randint(1, 9)
        execute = rng.randint(1, 9)
        answer = read * 4 + write * 2 + execute
        prompt = f"DevOps / Linux [{case_id}]: для одного класса пользователей заданы права r={read}, w={write}, x={execute}. Вычислите числовую маску rwx по правилу 4/2/1 для каждой группы права."
    elif family == "devops_networking":
        prefix = rng.randint(24, 29)
        answer = 2 ** (32 - prefix) - 2
        prompt = f"DevOps / сети [{case_id}]: сколько usable IPv4-адресов содержит подсеть /{prefix} без network и broadcast адресов?"
    elif family == "cicd":
        stages = rng.randint(4, 40)
        duration = rng.randint(2, 30)
        parallel = rng.randint(1, 8)
        answer = math.ceil(stages / parallel) * duration
        prompt = f"DevOps / CI/CD [{case_id}]: {stages} одинаковых стадий по {duration} минут выполняются параллельно максимум по {parallel}. Сколько минут займёт один прогон?"
    elif family == "containers":
        replicas = rng.randint(2, 80)
        cpu = rng.randint(100, 1000)
        answer = replicas * cpu
        prompt = f"DevOps / контейнеры [{case_id}]: каждый из {replicas} pod'ов запрашивает {cpu} millicores CPU. Какой общий CPU request в millicores?"
    elif family == "observability":
        total = rng.randint(10000, 200000)
        errors = rng.randint(10, max(20, total // 20))
        answer = errors * 10000 // total
        prompt = f"DevOps / наблюдаемость [{case_id}]: из {total} запросов {errors} завершились ошибкой. Найдите error rate в базисных пунктах (10000 = 100%)."

    elif family == "boundaries":
        fields = rng.randint(2, 150)
        minimum = rng.randint(1, 50)
        maximum = minimum + rng.randint(20, 200)
        answer = fields * 6
        prompt = f"QA / тест-дизайн [{case_id}]: для {fields} независимых целочисленных полей с диапазонами, включая поле [{minimum}; {maximum}], берём по шесть граничных точек на поле (min−1, min, min+1, max−1, max, max+1). Сколько проверок получится?"
    elif family == "pairwise":
        a = rng.randint(2, 6)
        b = rng.randint(2, 6)
        c = rng.randint(2, 5)
        answer = a * b + a * c + b * c
        prompt = f"QA / pairwise [{case_id}]: три параметра имеют {a}, {b} и {c} значений. Сколько пар значений существует между всеми парами параметров?"
    elif family == "api_assertions":
        endpoints = rng.randint(3, 12)
        checks = rng.randint(2, 7)
        answer = endpoints * checks
        prompt = f"QA / API [{case_id}]: в тестовом наборе {endpoints} эндпоинтов и для каждого проверяется {checks} независимых условий. Сколько проверок выполняется?"
    elif family == "requirements":
        requirements = rng.randint(5, 30)
        cases = rng.randint(2, 8)
        answer = requirements * cases
        prompt = f"QA / анализ требований [{case_id}]: {requirements} требований проходят по {cases} независимым сценариям проверки. Сколько проверок нужно выполнить?"
    elif family == "automation":
        tests = rng.randint(50, 500)
        workers = rng.randint(2, 20)
        seconds = rng.randint(5, 60)
        answer = math.ceil(tests / workers) * seconds
        prompt = f"QA / автотесты [{case_id}]: {tests} тестов выполняются на {workers} параллельных воркерах, каждый тест занимает {seconds} секунд. Какова длительность полного прогона в секундах?"
    else:
        raise ValueError(f"Unknown task family in template {template_code}")

    return prompt + " Ответьте целым числом.", answer


def generate(template_code: str, seed: int) -> ItemInstance:
    prompt, _ = _task(template_code, seed)
    return ItemInstance(template_code, seed, prompt)


def grade(template_code: str, seed: int, answer: str) -> bool:
    try:
        expected = _task(template_code, seed)[1]
        return int(answer.strip()) == expected
    except (ValueError, AttributeError):
        return False


def parameter_fingerprint(template_code: str, seed: int) -> str:
    return hashlib.sha256(f"{template_code}:{seed}".encode()).hexdigest()
