import asyncio
import base64
import json
import re
from typing import Any

from openai import OpenAI

from .config import settings


DEFAULT_WORKOUT = {
    "name": "Тренировка A",
    "exercises": [
        {"name": "Отжимания", "sets": 3, "reps": "8-12", "rest": "60 сек"},
        {"name": "Приседания", "sets": 3, "reps": "12-15", "rest": "60 сек"},
        {"name": "Выпады", "sets": 3, "reps": "10 на каждую ногу", "rest": "60 сек"},
        {"name": "Узкие отжимания", "sets": 3, "reps": "6-10", "rest": "60 сек"},
        {"name": "Планка", "sets": 3, "reps": "30-45 сек", "rest": "45 сек"},
    ],
}


class AIService:
    def __init__(self) -> None:
        self.client = None
        if settings.deepseek_api_key:
            self.client = OpenAI(api_key=settings.deepseek_api_key, base_url="https://api.deepseek.com")

    async def _chat(self, messages: list[dict[str, Any]]) -> str:
        if not self.client:
            return ""

        def call() -> str:
            result = self.client.chat.completions.create(
                model=settings.deepseek_model,
                messages=messages,
                temperature=0.3,
                stream=False,
            )
            return result.choices[0].message.content or ""

        return await asyncio.to_thread(call)

    @staticmethod
    def _json_from_text(text: str) -> dict[str, Any] | None:
        if not text:
            return None
        cleaned = text.strip().replace("```json", "").replace("```", "").strip()
        try:
            value = json.loads(cleaned)
            return value if isinstance(value, dict) else None
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if not match:
                return None
            try:
                value = json.loads(match.group(0))
                return value if isinstance(value, dict) else None
            except json.JSONDecodeError:
                return None

    async def generate_plan(self, profile: dict[str, Any]) -> dict[str, Any]:
        fallback = {
            "nutrition": "Ориентируйтесь на регулярные приёмы пищи, источник белка в каждом основном приёме, овощи и достаточное питьё. Калории являются ориентиром, а не медицинской нормой.",
            "meal_schedule": ["Завтрак", "Обед", "Ужин", "1-2 небольших перекуса по голоду"],
            "sleep": "Старайтесь придерживаться стабильного времени сна и получать достаточно часов для вашего возраста.",
            "recovery": "Оставляйте дни лёгкой активности, разминайтесь и прекращайте упражнение при резкой боли.",
            "daily_tasks": ["Выпить воду", "Сделать запланированную активность", "Записать питание", "Лечь спать вовремя"],
            "workouts": [DEFAULT_WORKOUT, {**DEFAULT_WORKOUT, "name": "Тренировка B"}],
        }
        if not self.client:
            return fallback

        prompt = f"""Ты создаёшь безопасный wellness-план, не медицинское назначение.
Профиль: {json.dumps(profile, ensure_ascii=False)}
Верни только JSON с ключами:
 nutrition, meal_schedule (массив строк), sleep, recovery, daily_tasks (массив строк), workouts (массив из 2 объектов name и exercises).
Для несовершеннолетних не задавай жёсткие ограничения по калориям. Не ставь диагнозы и не назначай лекарства.
Нагрузка должна увеличиваться постепенно."""
        try:
            data = self._json_from_text(await self._chat([{"role": "system", "content": "Ты осторожный AI-фитнес помощник."}, {"role": "user", "content": prompt}]))
            if data:
                return {**fallback, **data}
        except Exception:
            pass
        return fallback

    async def analyze_food_text(self, text: str) -> dict[str, Any]:
        fallback = {"description": text, "calories": 500, "protein": 25, "fat": 18, "carbs": 60}
        if not self.client:
            return fallback
        prompt = f"""Оцени блюдо приблизительно, не выдавай это за точное измерение.
Текст пользователя: {text}
Верни только JSON: description, calories, protein, fat, carbs.
Числа должны быть примерными и относиться ко всей указанной порции."""
        try:
            data = self._json_from_text(await self._chat([{"role": "system", "content": "Ты помощник по приблизительной оценке питания."}, {"role": "user", "content": prompt}]))
            if data:
                return self._normalize_food(data, text)
        except Exception:
            pass
        return fallback

    async def analyze_food_image(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> dict[str, Any]:
        fallback = {"description": "Еда на фотографии", "calories": 500, "protein": 25, "fat": 18, "carbs": 60}
        if not self.client:
            return fallback
        image_data = base64.b64encode(image_bytes).decode("ascii")
        data_url = f"data:{mime_type};base64,{image_data}"
        prompt = "Определи предположительный состав еды, размер порции и примерные калории и БЖУ. Верни только JSON с ключами description, calories, protein, fat, carbs. Обязательно учитывай, что оценка по фото приблизительная."

        def call() -> str:
            response = self.client.responses.create(
                model=settings.deepseek_vision_model,
                input=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": prompt},
                            {"type": "input_image", "image_url": data_url, "detail": "low"},
                        ],
                    }
                ],
            )
            return getattr(response, "output_text", "") or ""

        try:
            result = await asyncio.to_thread(call)
            data = self._json_from_text(result)
            if data:
                return self._normalize_food(data, "Еда на фотографии")
        except Exception:
            pass
        return fallback

    @staticmethod
    def _normalize_food(data: dict[str, Any], default_description: str) -> dict[str, Any]:
        def number(key: str) -> float:
            try:
                return float(data.get(key, 0))
            except (TypeError, ValueError):
                return 0.0

        return {
            "description": str(data.get("description") or default_description),
            "calories": round(number("calories")),
            "protein": round(number("protein"), 1),
            "fat": round(number("fat"), 1),
            "carbs": round(number("carbs"), 1),
        }

    async def trainer_answer(self, profile: dict[str, Any], context: str, question: str) -> str:
        if not self.client:
            return "AI пока не подключён: добавьте DEEPSEEK_API_KEY в переменные окружения. Пока можно пользоваться разделами профиля, тренировок, питания, воды и сна."
        prompt = f"""Профиль пользователя: {json.dumps(profile, ensure_ascii=False)}
Контекст последних записей: {context}
Вопрос: {question}
Ответь по-русски кратко и практично. Не ставь медицинские диагнозы, не назначай лекарства. При резкой боли, травме, обмороке, боли в груди или других тревожных симптомах рекомендуй обратиться к врачу или в экстренную помощь. Не предлагай резкого увеличения нагрузки."""
        try:
            return await self._chat([{"role": "system", "content": "Ты внимательный AI-фитнес и wellness-помощник."}, {"role": "user", "content": prompt}])
        except Exception:
            return "Не удалось получить ответ AI. Проверьте ключ DeepSeek и повторите попытку."
