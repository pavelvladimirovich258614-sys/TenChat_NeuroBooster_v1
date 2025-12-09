"""
AI Content Generator (OpenAI-compatible API) with Human-like Output
"""
import random
import re
from typing import List, Dict, Optional, Any
from openai import AsyncOpenAI
from loguru import logger


class AIGenerator:
    """AI content generator with anti-detection and human-like output"""

    # Фразы-маркеры AI, которые нужно избегать
    AI_MARKERS = [
        "безусловно", "несомненно", "в современном мире", "в наше время",
        "стоит отметить", "важно понимать", "необходимо отметить",
        "в связи с этим", "таким образом", "в целом", "в первую очередь",
        "с учетом вышесказанного", "в контексте", "резюмируя",
        "комплексный подход", "синергия", "оптимизация", "трансформация",
        "в заключение хочется сказать", "подводя итоги",
    ]
    
    # Варианты начала комментариев для разнообразия
    COMMENT_STARTERS = [
        "", "О, ", "Хм, ", "Кстати, ", "Интересно, ", "А ", "Вот это да! ",
        "Слушай, ", "Знаешь, ", "Да, ", "Согласен, ", "Не согласен, но ",
    ]
    
    # Варианты окончаний для разнообразия
    COMMENT_ENDERS = [
        "", " Как думаете?", " Что скажете?", " Интересно ваше мнение.",
        " Сталкивались с таким?", " У кого какой опыт?",
    ]

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model_comments: str = "openai/gpt-4o-mini",
        model_articles: str = "anthropic/claude-3.5-haiku",
        model_analytics: str = "deepseek/deepseek-chat"
    ):
        """
        Initialize AI generator

        Args:
            base_url: API base URL
            api_key: API key
            model_comments: Model for comments and quick replies
            model_articles: Model for article generation
            model_analytics: Model for analytics
        """
        self.client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key
        )
        self.model_comments = model_comments
        self.model_articles = model_articles
        self.model_analytics = model_analytics

    def _humanize_text(self, text: str) -> str:
        """
        Post-process text to make it more human-like
        
        Args:
            text: Generated text
            
        Returns:
            Humanized text
        """
        # Убираем типичные AI-маркеры
        result = text
        for marker in self.AI_MARKERS:
            # Case-insensitive замена
            pattern = re.compile(re.escape(marker), re.IGNORECASE)
            result = pattern.sub("", result)
        
        # Убираем двойные пробелы
        result = re.sub(r'\s+', ' ', result)
        
        # Убираем пробелы перед знаками препинания
        result = re.sub(r'\s+([.,!?:;])', r'\1', result)
        
        # Иногда добавляем опечатку (5% шанс) - делает текст более человечным
        # if random.random() < 0.05:
        #     words = result.split()
        #     if len(words) > 3:
        #         idx = random.randint(1, len(words) - 2)
        #         word = words[idx]
        #         if len(word) > 3:
        #             # Перестановка букв
        #             char_idx = random.randint(1, len(word) - 2)
        #             word = word[:char_idx] + word[char_idx+1] + word[char_idx] + word[char_idx+2:]
        #             words[idx] = word
        #             result = ' '.join(words)
        
        return result.strip()

    async def generate_comment(self, post_content: str) -> Optional[str]:
        """
        Generate a human-like comment for a post

        Args:
            post_content: Post content to comment on

        Returns:
            Generated comment or None if error
        """
        try:
            # Вариативность в промптах
            comment_types = [
                "задай уточняющий вопрос по теме",
                "поделись коротким личным опытом",
                "вырази согласие и добавь мысль",
                "вежливо поспорь с автором",
                "дай практический совет",
            ]
            comment_type = random.choice(comment_types)
            
            system_prompt = f"""Ты пишешь комментарий в деловой соцсети как обычный пользователь.

ЗАДАЧА: {comment_type}

КРИТИЧЕСКИ ВАЖНО - как НЕ писать:
❌ НЕ начинай с "Отличный пост!", "Спасибо за статью!", "Очень интересно!"
❌ НЕ используй канцеляризмы: "стоит отметить", "важно понимать", "в современном мире"
❌ НЕ пиши длинно - максимум 2-3 коротких предложения
❌ НЕ используй эмодзи в каждом предложении
❌ НЕ пиши "я согласен" или "полностью поддерживаю"

КАК писать:
✅ Пиши как в мессенджере - коротко и по делу
✅ Можно начать с "О,", "Хм,", "Кстати,", "А вот"
✅ Один конкретный вопрос или мысль
✅ Разговорный стиль, можно сленг
✅ Максимум 1 эмодзи (или без них)

Примеры хороших комментариев:
- "У нас похожая ситуация была, только мы пошли другим путём - через холодные звонки. Сработало лучше"
- "А как вы решаете проблему с масштабированием? У нас это боль"  
- "Хм, спорно. В B2B это работает, а вот в рознице - сомневаюсь"
- "О, как раз недавно тестили такой подход. Конверсия выросла на 15%"
"""

            user_prompt = f"Напиши комментарий к посту (помни - коротко и без банальностей!):\n\n{post_content[:500]}"

            response = await self.client.chat.completions.create(
                model=self.model_comments,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.9,  # Выше для разнообразия
                max_tokens=100,   # Короче = человечнее
                presence_penalty=0.6,  # Меньше повторений
                frequency_penalty=0.5
            )

            comment = response.choices[0].message.content.strip()
            
            # Постобработка
            comment = self._humanize_text(comment)
            
            # Убираем кавычки если AI обернул ответ в них
            comment = comment.strip('"\'')
            
            # Иногда добавляем вариативное начало/конец
            if random.random() < 0.2:
                starter = random.choice(self.COMMENT_STARTERS)
                if not comment.startswith(tuple("ОАХКВСНДИЗ")):  # Если не начинается с заглавной
                    comment = starter + comment[0].lower() + comment[1:]
            
            logger.info(f"Generated comment: {comment[:50]}...")
            return comment

        except Exception as e:
            logger.error(f"Generate comment failed: {e}")
            return None

    async def generate_article(
        self,
        topic: str,
        style: str = "professional",
        mood: str = "expert"
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a full article with title, text, and hashtags

        Args:
            topic: Article topic
            style: Writing style (professional, casual, expert)
            mood: Article mood (expert, provocative, friendly, personal)

        Returns:
            Dictionary with title, text, and hashtags or None if error
        """
        try:
            # Mood-based prompt variations with anti-AI-detection focus
            mood_instructions = {
                "expert": """
**Настроение: Экспертное 🎓**
- Пиши как практик с 10+ лет опыта, который реально делал это руками
- Делись КОНКРЕТНЫМИ цифрами: "за 3 месяца подняли конверсию с 2% до 7%"
- Используй профессиональный сленг, но НЕ канцеляризмы
- Структура: провокационный тезис → реальный кейс → выводы
- Абзацы по 2-4 предложения (мобилки!)
- 1-2 эмодзи на всю статью, не больше
""",
                "provocative": """
**Настроение: Провокационное 🔥**
- Начни с утверждения, которое заставит остановиться: "90% маркетологов сливают бюджет"
- Критикуй общепринятые подходы с аргументами
- Пиши резко, как в споре с другом
- Риторические вопросы: "Серьезно? В 2024 году?"
- Ударные абзацы по 1-3 предложения
- Можно матернуться (мягко) или использовать сарказм
""",
                "friendly": """
**Настроение: Дружелюбное 🤝**
- Пиши как рассказываешь историю коллеге в курилке
- Много "я", "мы", "у нас было так..."
- Реальные примеры: имена (можно выдуманные), даты, суммы
- Обращайся на "вы" но без официоза
- Короткие абзацы, разговорный стиль
- Фразы типа: "Короче говоря", "А потом случилось вот что"
""",
                "personal": """
**Настроение: Личное 💬**
- Рассказывай СВОЮ историю: "Три года назад я был в полной ж..."
- Показывай эмоции: страх, сомнения, радость победы
- Структура: проблема → путь → инсайт
- Пиши как думаешь, с паузами: "И тут я понял. Просто понял."
- Мини-абзацы в 1-2 предложения
- Эмодзи редко, для эмоции 😅
"""
            }

            mood_instruction = mood_instructions.get(mood, mood_instructions["expert"])
            
            # Рандомизируем структуру для уникальности
            structures = [
                "Начни с провокационного вопроса",
                "Начни с шокирующего факта или статистики",
                "Начни с короткой личной истории",
                "Начни с проблемы, которая бесит читателя",
            ]
            structure_hint = random.choice(structures)

            system_prompt = f"""Ты автор в TenChat - деловой соцсети. Пишешь как ЖИВОЙ человек, не как бот.

{mood_instruction}

**{structure_hint}**

**ЗАПРЕЩЕНО (это выдаёт AI):**
❌ "В современном мире", "стоит отметить", "важно понимать"
❌ "Безусловно", "несомненно", "в целом"
❌ "Комплексный подход", "синергия", "оптимизация процессов"
❌ "В заключение хочется отметить", "подводя итоги"
❌ Идеально структурированный текст с нумерацией везде
❌ Слишком много эмодзи (макс 2-3 на статью)

**ОБЯЗАТЕЛЬНО (так пишут люди):**
✅ Конкретные цифры и факты (выдумай правдоподобные)
✅ Разговорные фразы: "Короче", "Вот смотрите", "А теперь внимание"
✅ Неидеальная структура - люди не пишут по шаблону
✅ Личный опыт (можешь придумать)
✅ Один-два абзаца длиннее остальных (так естественнее)
✅ Вопросы к читателю

**Длина:** 500-800 слов. Люди читают с телефонов!

**Формат ответа СТРОГО:**
TITLE: [заголовок БЕЗ кавычек, цепляющий]

TEXT:
[текст с markdown: ## для подзаголовков, **жирный** для акцентов]

HASHTAGS:
#тег1 #тег2 #тег3 #тег4 #тег5
"""

            user_prompt = f"Тема: {topic}\n\nСтиль: {style}, настроение: {mood}.\n\nНапиши уникальную статью. Помни - ты человек, не AI!"

            response = await self.client.chat.completions.create(
                model=self.model_articles,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.92,  # Высокая для уникальности
                max_tokens=2500,
                presence_penalty=0.7,  # Избегаем повторений
                frequency_penalty=0.5
            )

            content = response.choices[0].message.content.strip()

            # Parse response
            article = self._parse_article_response(content)
            
            # Post-process для удаления AI-маркеров
            article["text"] = self._humanize_text(article["text"])
            article["title"] = self._humanize_text(article["title"])
            
            logger.info(f"Generated article ({mood} mood): {article['title'][:50]}...")
            return article

        except Exception as e:
            logger.error(f"Generate article failed: {e}")
            return None

    def _parse_article_response(self, content: str) -> Dict[str, any]:
        """
        Parse AI response into structured article

        Args:
            content: Raw AI response

        Returns:
            Dictionary with title, text, and hashtags
        """
        lines = content.split("\n")
        title = ""
        text_lines = []
        hashtags = []

        current_section = None

        for line in lines:
            line = line.strip()

            if line.startswith("TITLE:"):
                title = line.replace("TITLE:", "").strip()
                current_section = "title"
            elif line.startswith("TEXT:"):
                current_section = "text"
            elif line.startswith("HASHTAGS:"):
                current_section = "hashtags"
            elif current_section == "text" and line:
                text_lines.append(line)
            elif current_section == "hashtags" and line:
                # Extract hashtags
                tags = [tag.strip() for tag in line.split() if tag.startswith("#")]
                hashtags.extend(tags)

        # If parsing failed, use simple approach
        if not title:
            # First non-empty line as title
            for line in lines:
                if line.strip():
                    title = line.strip().replace("TITLE:", "").replace("#", "").strip()
                    break

        if not text_lines:
            text_lines = [line for line in lines if line.strip() and not line.startswith("TITLE:") and not line.startswith("HASHTAGS:")]

        text = "\n".join(text_lines).strip()

        return {
            "title": title or "Без заголовка",
            "text": text,
            "hashtags": hashtags[:5]  # Limit to 5 hashtags
        }

    async def analyze_topic(self, topic: str) -> Optional[Dict[str, any]]:
        """
        Analyze topic and suggest structure

        Args:
            topic: Topic to analyze

        Returns:
            Analysis with suggested structure
        """
        try:
            system_prompt = """Ты - аналитик контента. Проанализируй тему и предложи структуру статьи."""

            user_prompt = f"""Проанализируй эту тему для статьи в TenChat: {topic}

Предоставь:
1. Целевую аудиторию
2. Ключевые моменты для раскрытия
3. Рекомендуемую структуру
4. Предложенные хештеги"""

            response = await self.client.chat.completions.create(
                model=self.model_analytics,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.5,
                max_tokens=800
            )

            analysis = response.choices[0].message.content.strip()
            logger.info(f"Topic analyzed: {topic}")

            return {
                "topic": topic,
                "analysis": analysis
            }

        except Exception as e:
            logger.error(f"Analyze topic failed: {e}")
            return None

    async def generate_auto_reply(
        self,
        incoming_message: str,
        context: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate automatic reply to incoming message

        Args:
            incoming_message: Incoming message text
            context: Optional context (user profile, previous messages)

        Returns:
            Generated reply or None if error
        """
        try:
            system_prompt = """Ты - виртуальный помощник в деловой социальной сети TenChat.
Твоя задача - отвечать на входящие сообщения вежливо, профессионально и по существу.

Требования:
- Язык: русский
- Стиль: деловой, но дружелюбный
- Длина: 2-4 предложения
- Если сообщение содержит вопрос - дай полезный ответ
- Если это приветствие - поприветствуй в ответ
- Если это коммерческое предложение - вежливо укажи на способ связи или отклони
"""

            user_prompt = f"Входящее сообщение: {incoming_message}"
            if context:
                user_prompt += f"\n\nКонтекст: {context}"

            response = await self.client.chat.completions.create(
                model=self.model_comments,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )

            reply = response.choices[0].message.content.strip()
            logger.info(f"Generated auto-reply: {reply[:50]}...")
            return reply

        except Exception as e:
            logger.error(f"Generate auto-reply failed: {e}")
            return None

    async def generate_welcome_message(
        self,
        recipient_name: Optional[str] = None,
        recipient_position: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate welcome message for new follower

        Args:
            recipient_name: Recipient's name
            recipient_position: Recipient's position/role

        Returns:
            Generated welcome message or None if error
        """
        try:
            # Варианты приветствий для разнообразия
            greeting_styles = [
                "краткое и дружелюбное",
                "с вопросом о сфере деятельности",
                "с предложением обмена опытом",
                "с упоминанием общих интересов",
            ]
            style = random.choice(greeting_styles)
            
            system_prompt = f"""Напиши приветственное сообщение новому подписчику в TenChat.

Стиль: {style}

**НЕЛЬЗЯ:**
❌ "Спасибо за подписку!" - банально
❌ "Рад видеть вас в своей сети!" - шаблон
❌ "Буду рад сотрудничеству" - слишком формально
❌ Длинные представления

**НУЖНО:**
✅ Короткое, 2-3 предложения максимум
✅ Как будто пишешь знакомому в мессенджере
✅ Конкретный вопрос или предложение
✅ Без эмодзи или 1 максимум

Примеры хороших сообщений:
- "Привет! Заметил, что вы в маркетинге - я тоже. Чем сейчас занимаетесь?"
- "О, вы из IT! Я тут про AI пишу. Если интересно - велком в комменты 🙂"
- "Привет! Спасибо что зашли. Вы в продажах? У меня есть пара мыслей по теме"
"""

            user_prompt = "Напиши приветствие (помни - коротко, без шаблонов!)"
            if recipient_name:
                user_prompt += f"\nИмя: {recipient_name}"
            if recipient_position:
                user_prompt += f"\nДолжность: {recipient_position}"

            response = await self.client.chat.completions.create(
                model=self.model_comments,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.9,
                max_tokens=100,
                presence_penalty=0.5
            )

            message = response.choices[0].message.content.strip()
            message = self._humanize_text(message)
            message = message.strip('"\'')
            
            logger.info(f"Generated welcome message: {message[:50]}...")
            return message

        except Exception as e:
            logger.error(f"Generate welcome message failed: {e}")
            return None

    async def generate_dm_message(
        self,
        purpose: str,
        recipient_name: Optional[str] = None,
        recipient_position: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate direct message for outreach

        Args:
            purpose: Purpose of the message (e.g., "networking", "job offer", "partnership")
            recipient_name: Recipient's name
            recipient_position: Recipient's position/role

        Returns:
            Generated message or None if error
        """
        try:
            # Рандомизируем подход
            approaches = [
                "через общую боль/проблему",
                "через комплимент работе человека",
                "через прямое предложение",
                "через вопрос",
            ]
            approach = random.choice(approaches)
            
            system_prompt = f"""Напиши холодное сообщение в TenChat для установления контакта.

**Цель:** {purpose}
**Подход:** {approach}

**ЗАПРЕЩЕНО - это СПАМ:**
❌ "Здравствуйте! Меня зовут... Я представляю компанию..."
❌ "Хочу предложить вам уникальную возможность..."
❌ "Наша компания специализируется на..."
❌ Длинные письма на 5+ предложений
❌ Формальный деловой стиль

**КАК ПИСАТЬ - это работает:**
✅ 2-4 предложения МАКСИМУМ
✅ Сразу к делу, без долгих представлений
✅ Один конкретный вопрос или предложение
✅ Как будто пишешь знакомому коллеге
✅ Можно неформально

Примеры работающих сообщений:
- "Привет! Видел ваш пост про [тема] - у нас похожая история. Есть идея, как это решить. Интересно пообщаться?"
- "Здравствуйте! Вы в [сфера], я тоже. Ищу партнёра для проекта по [тема]. 15 минут на созвон найдётся?"
- "Привет! Нужен человек с вашим опытом для консультации. Оплачиваю. Актуально?"
"""

            user_prompt = f"Цель сообщения: {purpose}\nНапиши короткое, человечное сообщение."
            if recipient_name:
                user_prompt += f"\nИмя: {recipient_name}"
            if recipient_position:
                user_prompt += f"\nДолжность: {recipient_position}"

            response = await self.client.chat.completions.create(
                model=self.model_comments,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.85,
                max_tokens=150,
                presence_penalty=0.6
            )

            message = response.choices[0].message.content.strip()
            message = self._humanize_text(message)
            message = message.strip('"\'')
            
            logger.info(f"Generated DM: {message[:50]}...")
            return message

        except Exception as e:
            logger.error(f"Generate DM failed: {e}")
            return None
