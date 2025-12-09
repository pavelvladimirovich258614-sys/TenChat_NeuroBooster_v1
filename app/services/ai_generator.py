"""
AI Content Generator (OpenAI-compatible API)
"""
from typing import List, Dict, Optional
from openai import AsyncOpenAI
from loguru import logger


class AIGenerator:
    """AI content generator using OpenAI-compatible API"""

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

    async def generate_comment(self, post_content: str) -> Optional[str]:
        """
        Generate a comment for a post

        Args:
            post_content: Post content to comment on

        Returns:
            Generated comment or None if error
        """
        try:
            system_prompt = """Ты - эксперт в деловых коммуникациях в социальных сетях.
Твоя задача - написать короткий, релевантный и ценный комментарий к посту.

Требования:
- Комментарий должен быть на русском языке
- Длина: 1-3 предложения
- Стиль: профессиональный, но дружелюбный
- Избегай банальностей типа "Отличный пост!"
- Добавляй ценность: задавай вопрос, делись опытом или инсайтом
"""

            user_prompt = f"Напиши комментарий к этому посту:\n\n{post_content}"

            response = await self.client.chat.completions.create(
                model=self.model_comments,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.8,
                max_tokens=150
            )

            comment = response.choices[0].message.content.strip()
            logger.info(f"Generated comment: {comment[:50]}...")
            return comment

        except Exception as e:
            logger.error(f"Generate comment failed: {e}")
            return None

    async def generate_article(
        self,
        topic: str,
        style: str = "professional"
    ) -> Optional[Dict[str, any]]:
        """
        Generate a full article with title, text, and hashtags

        Args:
            topic: Article topic
            style: Writing style (professional, casual, expert)

        Returns:
            Dictionary with title, text, and hashtags or None if error
        """
        try:
            system_prompt = f"""Ты - эксперт в создании качественного контента для бизнес-соцсети TenChat.
Твоя задача - написать полноценную статью на заданную тему.

Требования:
- Язык: русский
- Стиль: {style}
- Структура: заголовок, вступление, 2-3 основных блока, заключение
- Длина: 800-1200 слов
- Формат: используй markdown для оформления (заголовки, списки, выделения)
- Тон: экспертный, но доступный
- Избегай воды и банальностей

Формат ответа:
TITLE: [заголовок статьи]

TEXT:
[текст статьи с markdown разметкой]

HASHTAGS:
#хештег1 #хештег2 #хештег3
"""

            user_prompt = f"Напиши статью на тему: {topic}"

            response = await self.client.chat.completions.create(
                model=self.model_articles,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=2500
            )

            content = response.choices[0].message.content.strip()

            # Parse response
            article = self._parse_article_response(content)
            logger.info(f"Generated article: {article['title']}")
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
