"""
Streamlit UI for TenChat NeuroBooster
"""
import os
import streamlit as st
import requests
import json
import pandas as pd
from datetime import datetime
from typing import List, Dict

# API Configuration
# В Docker используется имя сервиса 'tenchat_api', локально - localhost
API_URL = os.getenv("API_URL", "http://localhost:8000")


def init_session_state():
    """Initialize session state"""
    if "refresh_counter" not in st.session_state:
        st.session_state.refresh_counter = 0
    if "selected_account_id" not in st.session_state:
        st.session_state.selected_account_id = None


def api_request(method: str, endpoint: str, **kwargs):
    """Make API request"""
    url = f"{API_URL}{endpoint}"
    try:
        response = requests.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        # Try to get detailed error message from response
        error_detail = ""
        try:
            error_data = e.response.json()
            if isinstance(error_data, dict):
                error_detail = error_data.get("detail", str(error_data))
        except:
            error_detail = e.response.text[:500] if e.response.text else ""
        
        st.error(f"Ошибка API: {e.response.status_code}")
        if error_detail:
            st.error(f"Детали: {error_detail}")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Ошибка подключения: {e}")
        return None


def render_sidebar():
    """Render sidebar with account selection"""
    with st.sidebar:
        st.header("⚙️ Настройки")

        # Get all accounts
        accounts = api_request("GET", "/accounts")
        
        # Ensure accounts is a list
        if accounts is None:
            accounts = []

        if len(accounts) > 0:
            st.subheader("Активный Аккаунт")

            # Build options: 0 = "Все аккаунты", then account IDs
            options_list = [0] + [acc["id"] for acc in accounts]
            options_labels = {0: "Все аккаунты"}
            for acc in accounts:
                options_labels[acc["id"]] = f"{acc['name']} ({acc['status']})"

            # Validate selected_account_id exists in options
            if st.session_state.selected_account_id not in options_list:
                st.session_state.selected_account_id = 0
            
            # Find current index safely
            try:
                current_index = options_list.index(st.session_state.selected_account_id)
            except ValueError:
                current_index = 0
                st.session_state.selected_account_id = 0

            selected_id = st.selectbox(
                "Выберите аккаунт:",
                options=options_list,
                format_func=lambda x: options_labels.get(x, f"Аккаунт {x}"),
                index=current_index,
                key="account_selector"
            )

            # Update session state (without rerun to avoid loops)
            st.session_state.selected_account_id = selected_id

            # Show selected account info
            if selected_id != 0:
                selected_acc = next((acc for acc in accounts if acc["id"] == selected_id), None)
                if selected_acc:
                    st.info(f"📊 **Статус:** {selected_acc['status']}")
                    st.info(f"🌐 **Прокси:** {selected_acc['proxy_display']}")
            else:
                st.info("📊 Выбраны все аккаунты")
        else:
            st.warning("⚠️ Нет добавленных аккаунтов")
            st.info("Перейдите во вкладку 'Аккаунты' для добавления")
            st.session_state.selected_account_id = None

        st.divider()

        # Quick stats
        st.subheader("📈 Быстрая статистика")

        if accounts and len(accounts) > 0:
            active_count = sum(1 for acc in accounts if acc["status"] == "active")
            st.metric("Активных аккаунтов", f"{active_count}/{len(accounts)}")

        # Recent actions count
        actions = api_request("GET", "/actions?limit=1000")
        if actions and len(actions) > 0:
            try:
                today_actions = sum(1 for a in actions
                                  if datetime.fromisoformat(a["created_at"].replace("Z", "")).date() == datetime.now().date())
                st.metric("Действий сегодня", today_actions)
            except Exception:
                st.metric("Действий сегодня", len(actions))


def render_accounts_tab():
    """Render Accounts tab"""
    st.header("Управление Аккаунтами")

    # Add account form
    with st.expander("➕ Добавить Аккаунт", expanded=False):
        with st.form("add_account_form"):
            st.subheader("Новый Аккаунт")

            account_name = st.text_input(
                "Название аккаунта",
                placeholder="Мой TenChat"
            )

            cookies_file = st.file_uploader(
                "Загрузите cookies.json",
                type=["json"],
                help="Экспортируйте cookies из браузера (EditThisCookie или J2TEAM)"
            )

            proxy = st.text_input(
                "Прокси (ip:port:login:pass)",
                placeholder="123.45.67.89:8080:user:password"
            )

            submitted = st.form_submit_button("Добавить и Проверить")

            if submitted:
                if not account_name:
                    st.error("Введите название аккаунта")
                elif not cookies_file:
                    st.error("Загрузите файл с cookies")
                elif not proxy:
                    st.error("Введите прокси")
                else:
                    # Read cookies
                    try:
                        # Read raw bytes and handle BOM
                        raw_bytes = cookies_file.read()
                        
                        # Strip UTF-8 BOM if present
                        if raw_bytes.startswith(b'\xef\xbb\xbf'):
                            raw_bytes = raw_bytes[3:]
                        
                        # Decode to string
                        cookies_json = raw_bytes.decode("utf-8")
                        
                        # Strip Unicode BOM if present after decode
                        cookies_json = cookies_json.lstrip('\ufeff')
                        
                        # Validate JSON before sending
                        try:
                            parsed = json.loads(cookies_json)
                            if not isinstance(parsed, list):
                                st.warning("⚠️ Файл cookies должен содержать массив [...], не объект {...}")
                        except json.JSONDecodeError as je:
                            st.error(f"Некорректный JSON в файле cookies: {je}")
                            st.stop()

                        # Create account
                        response = api_request(
                            "POST",
                            "/accounts",
                            json={
                                "name": account_name,
                                "cookies_json": cookies_json,
                                "proxy": proxy
                            }
                        )

                        if response:
                            st.success(f"✅ Аккаунт '{account_name}' добавлен!")
                            st.session_state.refresh_counter += 1
                            st.rerun()

                    except UnicodeDecodeError as e:
                        st.error(f"Ошибка кодировки файла. Убедитесь, что файл в UTF-8: {e}")
                    except Exception as e:
                        st.error(f"Ошибка при чтении cookies: {e}")

    # List accounts
    st.subheader("Список Аккаунтов")

    accounts = api_request("GET", "/accounts")

    if accounts:
        # Create dataframe
        df_data = []
        for acc in accounts:
            df_data.append({
                "ID": acc["id"],
                "Название": acc["name"],
                "Прокси": acc["proxy_display"],
                "Статус": acc["status"],
                "Последняя проверка": datetime.fromisoformat(acc["last_check"]).strftime("%Y-%m-%d %H:%M")
            })

        df = pd.DataFrame(df_data)

        # Style status
        def color_status(val):
            if val == "active":
                return "background-color: #90EE90"
            elif val == "error":
                return "background-color: #FFB6C1"
            elif val == "cookies_expired":
                return "background-color: #FFD700"
            else:
                return ""

        styled_df = df.style.applymap(color_status, subset=["Статус"])

        st.dataframe(styled_df, use_container_width=True, hide_index=True)

        # Delete account
        st.subheader("Удалить Аккаунт")
        account_to_delete = st.selectbox(
            "Выберите аккаунт для удаления",
            options=[acc["id"] for acc in accounts],
            format_func=lambda x: next(acc["name"] for acc in accounts if acc["id"] == x)
        )

        if st.button("🗑️ Удалить аккаунт", type="secondary"):
            response = api_request("DELETE", f"/accounts/{account_to_delete}")
            if response:
                st.success("Аккаунт удален")
                st.rerun()

    else:
        st.info("Нет добавленных аккаунтов")


def render_tasks_tab():
    """Render Tasks tab"""
    st.header("Запуск Задач")

    # Get accounts
    accounts = api_request("GET", "/accounts")

    if not accounts:
        st.warning("⚠️ Сначала добавьте аккаунты во вкладке 'Аккаунты'")
        return

    # Filter active accounts
    active_accounts = [acc for acc in accounts if acc["status"] == "active"]

    if not active_accounts:
        st.warning("⚠️ Нет активных аккаунтов")
        return

    # Task creation form
    st.subheader("Создать Задачу")

    # Select accounts based on sidebar selection
    if st.session_state.selected_account_id and st.session_state.selected_account_id != 0:
        # Single account selected in sidebar
        selected_acc = next((acc for acc in active_accounts
                           if acc["id"] == st.session_state.selected_account_id), None)
        if selected_acc:
            st.info(f"🎯 Задача будет выполнена для аккаунта: **{selected_acc['name']}**")
            selected_accounts = [selected_acc["id"]]
        else:
            st.warning("⚠️ Выбранный аккаунт не активен. Выберите другой аккаунт в боковой панели.")
            return
    else:
        # Multiple account selection
        selected_accounts = st.multiselect(
            "Выберите аккаунты",
            options=[acc["id"] for acc in active_accounts],
            format_func=lambda x: next(acc["name"] for acc in active_accounts if acc["id"] == x)
        )

    # Task type
    task_types = {
        "warmup": "🔥 Прогрев (Лайкинг ленты)",
        "ai_post": "✍️ AI Постинг",
        "mass_follow": "➕ Масс-фолловинг",
        "ai_comments": "💬 AI Комментарии",
        "connections": "🤝 Деловые связи",
        "dm_followers": "📩 Рассылка подписчикам",
        "dm_cold": "📨 Холодная рассылка",
        "alliance_invites": "🛡 Приглашение в Альянс",
        "parse_users": "🔍 Парсинг пользователей",
        "auto_reply": "🤖 Автоответчик"
    }

    task_type = st.selectbox(
        "Тип задачи",
        options=list(task_types.keys()),
        format_func=lambda x: task_types[x]
    )

    # Task parameters
    if task_type == "warmup":
        st.markdown("### Параметры Прогрева")

        with st.expander("💡 Как использовать эту функцию"):
            st.markdown("""
            **🔥 Прогрев аккаунта (Лайкинг ленты)**

            ℹ️ **Для чего нужно:**
            - Имитация активности живого пользователя
            - Повышение видимости вашего профиля в ленте
            - Подготовка аккаунта перед массовыми действиями

            ⚠️ **Рекомендации:**
            - Ставьте не более 50-100 лайков в сутки
            - Используйте задержку 60-180 секунд между действиями
            - Начинайте с 10-20 лайков, постепенно увеличивая
            - Лучше запускать прогрев утром (9-11 часов)

            ✅ **Безопасность:** Низкий риск, базовая функция
            """)

        num_likes = st.slider(
            "Количество лайков",
            min_value=5,
            max_value=50,
            value=10
        )

        feed_type = st.selectbox(
            "Тип ленты",
            options=["all", "business", "it", "marketing"],
            format_func=lambda x: {
                "all": "Все",
                "business": "Бизнес",
                "it": "IT",
                "marketing": "Маркетинг"
            }[x]
        )

        parameters = {
            "num_likes": num_likes,
            "feed_type": feed_type
        }

    elif task_type == "ai_post":
        st.markdown("### Параметры AI Постинга")

        with st.expander("💡 Как использовать эту функцию"):
            st.markdown("""
            **✍️ AI Постинг статей**

            ℹ️ **Для чего нужно:**
            - Автоматическая публикация экспертного контента
            - Поддержание активности профиля
            - Привлечение целевой аудитории

            ⚠️ **Рекомендации:**
            - Публикуйте 1-3 статьи в день (не больше!)
            - Задавайте конкретные темы: "Как AI помогает в маркетинге 2025"
            - Выбирайте стиль под вашу аудиторию
            - Проверяйте сгенерированный текст перед публикацией

            📝 **Совет:** Используйте "Экспертный" стиль для B2B, "Неформальный" для широкой аудитории

            📁 **Массовая загрузка:**
            - Загрузите .txt файл (каждая строка = тема)
            - Или .csv/.xlsx файл (столбец "topic")
            - Система создаст отдельную задачу для каждой темы

            ✅ **Безопасность:** Средний риск, следите за качеством контента
            """)

        # Topic input mode
        input_mode = st.radio(
            "Режим ввода темы:",
            options=["single", "file"],
            format_func=lambda x: {
                "single": "✍️ Одна тема (вручную)",
                "file": "📁 Массовая загрузка из файла"
            }[x],
            horizontal=True
        )

        topics_list = []

        if input_mode == "single":
            topic = st.text_area(
                "Тема статьи",
                placeholder="Напишите тему для статьи, например:\n'Как использовать AI для автоматизации маркетинга'",
                height=100
            )
            if topic:
                topics_list = [topic]
        else:
            # File upload
            uploaded_file = st.file_uploader(
                "Загрузите файл с темами",
                type=["txt", "csv", "xlsx"],
                help="Формат .txt: каждая строка = тема\nФормат .csv/.xlsx: столбец 'topic'"
            )

            if uploaded_file:
                try:
                    file_extension = uploaded_file.name.split(".")[-1].lower()

                    if file_extension == "txt":
                        # Read text file
                        content = uploaded_file.read().decode("utf-8")
                        topics_list = [line.strip() for line in content.split("\n") if line.strip()]

                    elif file_extension == "csv":
                        # Read CSV file
                        import io
                        content = uploaded_file.read().decode("utf-8")
                        df = pd.read_csv(io.StringIO(content))

                        if "topic" in df.columns:
                            topics_list = df["topic"].dropna().tolist()
                        else:
                            st.error("CSV файл должен содержать столбец 'topic'")

                    elif file_extension == "xlsx":
                        # Read Excel file
                        df = pd.read_excel(uploaded_file)

                        if "topic" in df.columns:
                            topics_list = df["topic"].dropna().tolist()
                        else:
                            st.error("Excel файл должен содержать столбец 'topic'")

                    if topics_list:
                        st.success(f"✅ Загружено тем: {len(topics_list)}")
                        with st.expander("📋 Предпросмотр тем"):
                            for i, t in enumerate(topics_list[:10], 1):
                                st.write(f"{i}. {t}")
                            if len(topics_list) > 10:
                                st.write(f"... и еще {len(topics_list) - 10} тем")

                except Exception as e:
                    st.error(f"Ошибка при чтении файла: {e}")

        # Style selector
        style = st.selectbox(
            "Стиль написания",
            options=["professional", "casual", "expert"],
            format_func=lambda x: {
                "professional": "Профессиональный",
                "casual": "Неформальный",
                "expert": "Экспертный"
            }[x]
        )

        # Mood selector (новое!)
        mood = st.selectbox(
            "Настроение (Mood)",
            options=["expert", "provocative", "friendly", "personal"],
            format_func=lambda x: {
                "expert": "🎓 Экспертное (факты, аналитика)",
                "provocative": "🔥 Провокационное (острые вопросы)",
                "friendly": "🤝 Дружелюбное (легкая беседа)",
                "personal": "💬 Личное (опыт, истории)"
            }[x]
        )

        parameters = {
            "topics": topics_list,  # Массив тем вместо одной темы
            "style": style,
            "mood": mood
        }

    elif task_type == "mass_follow":
        st.markdown("### Параметры Масс-фолловинга")

        with st.expander("💡 Как использовать эту функцию"):
            st.markdown("""
            **➕ Масс-фолловинг по целевой аудитории**

            ℹ️ **Для чего нужно:**
            - Быстрое расширение сети контактов
            - Привлечение внимания целевой аудитории
            - Рост числа подписчиков (взаимные подписки)

            ⚠️ **Рекомендации:**
            - НЕ БОЛЕЕ 20-30 подписок в день!
            - Используйте точные запросы: "CEO стартапа", "маркетолог Москва"
            - Задержка между подписками: минимум 60-120 секунд
            - Периодически отписывайтесь от неактивных

            🎯 **Примеры запросов:**
            - "директор по маркетингу"
            - "основатель IT компании"
            - "бизнес-консультант"

            ✅ **Безопасность:** Высокий риск при превышении лимитов!
            """)

        search_query = st.text_input(
            "Поисковый запрос",
            placeholder="Например: 'маркетолог' или 'CEO IT компании'"
        )

        num_follows = st.slider(
            "Количество подписок",
            min_value=5,
            max_value=20,
            value=10
        )

        parameters = {
            "search_query": search_query,
            "num_follows": num_follows
        }

    elif task_type == "ai_comments":
        st.markdown("### Параметры AI Комментариев")

        with st.expander("💡 Как использовать эту функцию"):
            st.markdown("""
            **💬 AI Комментарии к постам**

            ℹ️ **Для чего нужно:**
            - Привлечение внимания к вашему профилю
            - Демонстрация экспертности в теме
            - Налаживание диалога с целевой аудиторией

            ⚠️ **Рекомендации:**
            - Оставляйте 5-15 комментариев в день
            - Нейросеть читает пост и пишет ОСМЫСЛЕННЫЙ комментарий
            - Избегайте однотипных фраз
            - Комментируйте посты из вашей ниши

            🤖 **Как работает:**
            1. Система находит популярные посты в ленте
            2. AI анализирует содержание поста
            3. Генерирует релевантный комментарий
            4. Публикует с задержкой 60-180 сек

            ✅ **Безопасность:** Средний риск, следите за качеством комментариев
            """)

        num_comments = st.slider(
            "Количество комментариев",
            min_value=3,
            max_value=20,
            value=5
        )

        feed_type = st.selectbox(
            "Тип ленты",
            options=["all", "business", "it", "marketing"],
            format_func=lambda x: {
                "all": "Все",
                "business": "Бизнес",
                "it": "IT",
                "marketing": "Маркетинг"
            }[x]
        )

        parameters = {
            "num_comments": num_comments,
            "feed_type": feed_type
        }

    elif task_type == "connections":
        st.markdown("### Параметры Деловых Связей")

        with st.expander("💡 Как использовать эту функцию"):
            st.markdown("""
            **🤝 Запросы на деловые связи**

            ℹ️ **Для чего нужно:**
            - Построение профессиональной сети
            - Установление деловых контактов
            - Доступ к закрытым постам и сообщениям

            ⚠️ **Рекомендации:**
            - Отправляйте 10-20 запросов в день
            - Целевой поиск: "инвестор", "партнер для бизнеса"
            - Добавляйте персонализированное сообщение
            - Отслеживайте % принятых запросов

            💼 **Отличие от подписок:**
            - Деловые связи = LinkedIn connections
            - Взаимный доступ к профилю и контактам
            - Более высокий уровень доверия

            ✅ **Безопасность:** Средний риск, лимит строже чем у подписок
            """)

        search_query = st.text_input(
            "Поисковый запрос",
            placeholder="Например: 'директор по маркетингу'"
        )

        num_requests = st.slider(
            "Количество запросов",
            min_value=5,
            max_value=20,
            value=10
        )

        parameters = {
            "search_query": search_query,
            "num_requests": num_requests
        }

    elif task_type == "dm_followers":
        st.markdown("### Параметры Рассылки Подписчикам")

        with st.expander("💡 Как использовать эту функцию"):
            st.markdown("""
            **📩 Приветственная рассылка подписчикам**

            ℹ️ **Для чего нужно:**
            - Приветствие новых подписчиков
            - Прогрев холодной аудитории
            - Конвертация подписчиков в клиентов

            ⚠️ **Рекомендации:**
            - Отправляйте 10-20 сообщений в день
            - Используйте AI для персонализации
            - Указывайте цель: "поблагодарить", "пригласить на вебинар"
            - Избегайте прямых продаж в первом сообщении

            📝 **Примеры целей:**
            - "поблагодарить за подписку"
            - "предложить бесплатную консультацию"
            - "пригласить в сообщество"

            ✅ **Безопасность:** Низкий риск (подписчики уже проявили интерес)
            """)

        message_purpose = st.text_input(
            "Цель сообщения",
            placeholder="Например: 'поблагодарить за подписку'",
            value="networking"
        )

        num_messages = st.slider(
            "Количество сообщений",
            min_value=5,
            max_value=20,
            value=10
        )

        parameters = {
            "message_purpose": message_purpose,
            "num_messages": num_messages
        }

    elif task_type == "dm_cold":
        st.markdown("### Параметры Холодной Рассылки")

        with st.expander("💡 Как использовать эту функцию"):
            st.markdown("""
            **📨 Холодные сообщения (Cold DM)**

            ℹ️ **Для чего нужно:**
            - Прямой охват целевой аудитории
            - Поиск клиентов, партнеров, инвесторов
            - B2B продажи и networking

            ⚠️ **ВАЖНО - НЕ СПАМЬТЕ!**
            - МАКСИМУМ 5-10 сообщений в день
            - Пишите ТОЛЬКО релевантной аудитории
            - Персонализируйте каждое сообщение (AI сделает это)
            - Предлагайте ценность, а не "холодную продажу"

            🎯 **Как использовать:**
            1. Точный поиск: "CEO SaaS стартапа"
            2. Цель: "предложить партнерство в маркетинге"
            3. AI создаст персональное сообщение
            4. Задержка 180-300 сек между сообщениями

            ❌ **Не делайте:**
            - Массовую рассылку одинаковых текстов
            - Спам с продажами
            - Превышение лимита 10 сообщений/день

            ✅ **Безопасность:** ВЫСОКИЙ РИСК! Используйте осторожно
            """)

        search_query = st.text_input(
            "Поисковый запрос (целевая аудитория)",
            placeholder="Например: 'предприниматель'"
        )

        message_purpose = st.text_input(
            "Цель сообщения",
            placeholder="Например: 'предложить сотрудничество'",
            value="networking"
        )

        num_messages = st.slider(
            "Количество сообщений",
            min_value=3,
            max_value=10,
            value=5
        )

        st.warning("⚠️ Рекомендуется не более 5-10 холодных сообщений в день")

        parameters = {
            "search_query": search_query,
            "message_purpose": message_purpose,
            "num_messages": num_messages
        }

    elif task_type == "alliance_invites":
        st.markdown("### Параметры Приглашения в Альянс")

        with st.expander("💡 Как использовать эту функцию"):
            st.markdown("""
            **🛡 Приглашение в Альянс (Community)**

            ℹ️ **Для чего нужно:**
            - Набор участников в ваше сообщество
            - Формирование закрытого клуба экспертов
            - Увеличение охвата через альянс

            ⚠️ **Рекомендации:**
            - Приглашайте 10-20 человек в день
            - Ищите релевантных: "разработчик Python", "дизайнер UX"
            - Убедитесь, что альянс открыт для приглашений
            - Следите за % принятых инвайтов

            🔍 **Где взять ID альянса:**
            1. Откройте ваш альянс в TenChat
            2. Скопируйте ID из URL
            3. Пример: tenchat.ru/alliances/12345 → ID = 12345

            💡 **Совет:** Комбинируйте с персональными DM после принятия приглашения

            ✅ **Безопасность:** Средний риск, следите за лимитами
            """)

        alliance_id = st.text_input(
            "ID Альянса",
            placeholder="Введите ID вашего альянса"
        )

        search_query = st.text_input(
            "Поисковый запрос",
            placeholder="Например: 'разработчик Python'"
        )

        num_invites = st.slider(
            "Количество приглашений",
            min_value=5,
            max_value=20,
            value=10
        )

        parameters = {
            "alliance_id": alliance_id,
            "search_query": search_query,
            "num_invites": num_invites
        }

    elif task_type == "parse_users":
        st.markdown("### Параметры Парсинга Пользователей")

        with st.expander("💡 Как использовать эту функцию"):
            st.markdown("""
            **🔍 Парсинг базы контактов**

            ℹ️ **Для чего нужно:**
            - Сбор целевой аудитории для дальнейшей работы
            - Аналитика конкурентов и ниши
            - Подготовка списка для рассылок

            ⚠️ **Рекомендации:**
            - Парсите 50-100 пользователей за раз
            - Используйте точные запросы
            - Результаты сохраняются в логах задачи
            - Экспортируйте данные для CRM

            📊 **Что сохраняется:**
            - ID пользователя
            - Имя и должность
            - Ссылка на профиль
            - Количество подписчиков

            💡 **Применение:**
            1. Парсинг → Анализ → Сегментация
            2. Выбор самых активных/релевантных
            3. Таргетированная рассылка/подписка

            ✅ **Безопасность:** Низкий риск (только чтение данных)
            """)

        search_query = st.text_input(
            "Поисковый запрос",
            placeholder="Например: 'маркетинг директор'"
        )

        num_users = st.slider(
            "Количество пользователей для парсинга",
            min_value=10,
            max_value=100,
            value=50
        )

        st.info("💡 Результаты будут сохранены в логах задачи")

        parameters = {
            "search_query": search_query,
            "num_users": num_users
        }

    elif task_type == "auto_reply":
        st.markdown("### Параметры Автоответчика")

        with st.expander("💡 Как использовать эту функцию"):
            st.markdown("""
            **🤖 Автоответчик на входящие сообщения**

            ℹ️ **Для чего нужно:**
            - Мгновенный ответ на входящие сообщения
            - Обработка запросов в нерабочее время
            - Квалификация лидов (первичный контакт)

            ⚠️ **Рекомендации:**
            - Интервал проверки: 5-10 минут (300-600 сек)
            - AI генерирует контекстные ответы
            - Работает в фоновом режиме
            - Проверяйте качество ответов в логах

            🤖 **Как работает:**
            1. Каждые N секунд проверяет входящие
            2. Читает непрочитанные сообщения
            3. AI анализирует контекст
            4. Отправляет умный ответ
            5. Логирует все действия

            💡 **Совет:**
            - Запускайте на ночь или выходные
            - Комбинируйте с ручной обработкой днем
            - Отключайте при активной переписке

            ✅ **Безопасность:** Низкий риск, но следите за качеством ответов!
            """)

        check_interval = st.slider(
            "Интервал проверки (секунды)",
            min_value=60,
            max_value=600,
            value=300
        )

        st.info("💡 Автоответчик проверит входящие сообщения и автоматически ответит на непрочитанные")

        parameters = {
            "check_interval": check_interval
        }

    else:
        st.error(f"Неизвестный тип задачи: {task_type}")
        parameters = {}

    # Submit button
    if st.button("🚀 Запустить Задачи", type="primary"):
        if not selected_accounts:
            st.error("Выберите хотя бы один аккаунт")
        elif task_type == "ai_post" and not topics_list:
            st.error("Введите тему для статьи или загрузите файл с темами")
        else:
            # Create tasks
            response = api_request(
                "POST",
                "/tasks",
                json={
                    "account_ids": selected_accounts,
                    "task_type": task_type,
                    "parameters": parameters
                }
            )

            if response:
                st.success(f"✅ Создано задач: {len(response)}")
                st.balloons()

    # Recent tasks
    st.subheader("Последние Задачи")

    tasks = api_request("GET", "/tasks?limit=20")

    if tasks:
        df_data = []
        for task in tasks:
            # Get account name
            acc_name = next(
                (acc["name"] for acc in accounts if acc["id"] == task["account_id"]),
                f"Account {task['account_id']}"
            )

            # Map task type to display name
            task_type_display = task_types.get(task["task_type"], task["task_type"])

            df_data.append({
                "ID": task["id"],
                "Аккаунт": acc_name,
                "Тип": task_type_display,
                "Статус": task["status"],
                "Прогресс": f"{task['progress']}%",
                "Результат": task["result"] or "-",
                "Создано": datetime.fromisoformat(task["created_at"]).strftime("%Y-%m-%d %H:%M")
            })

        df = pd.DataFrame(df_data)

        # Color status
        def color_task_status(val):
            if val == "completed":
                return "background-color: #90EE90"
            elif val == "failed":
                return "background-color: #FFB6C1"
            elif val == "running":
                return "background-color: #87CEEB"
            else:
                return ""

        styled_df = df.style.applymap(color_task_status, subset=["Статус"])

        st.dataframe(styled_df, use_container_width=True, hide_index=True)

        # Show refresh button for running tasks instead of auto-refresh (avoids React loop)
        if any(task["status"] == "running" for task in tasks):
            st.info("⏳ Задачи выполняются...")
            if st.button("🔄 Обновить статус задач"):
                st.rerun()

    else:
        st.info("Нет задач")


def render_logs_tab():
    """Render Logs tab"""
    st.header("Логи Активности")

    # Get actions
    actions = api_request("GET", "/actions?limit=100")

    if actions:
        # Get accounts for mapping
        accounts = api_request("GET", "/accounts") or []

        # Filter by selected account if not "All accounts"
        if st.session_state.selected_account_id and st.session_state.selected_account_id != 0:
            actions = [a for a in actions if a["account_id"] == st.session_state.selected_account_id]
            if actions:
                selected_acc = next((acc for acc in accounts
                                   if acc["id"] == st.session_state.selected_account_id), None)
                if selected_acc:
                    st.info(f"📊 Показаны логи для аккаунта: **{selected_acc['name']}**")

        df_data = []
        for action in actions:
            # Get account name
            acc_name = next(
                (acc["name"] for acc in accounts if acc["id"] == action["account_id"]),
                f"Account {action['account_id']}"
            )

            # Format action type
            action_type_map = {
                "like": "👍 Лайк",
                "follow": "➕ Подписка",
                "post": "📝 Пост",
                "comment": "💬 Комментарий"
            }

            # Parse datetime safely
            try:
                created_at = action["created_at"].replace("Z", "").replace("T", " ")[:19]
                time_str = created_at
            except Exception:
                time_str = str(action.get("created_at", "-"))
            
            df_data.append({
                "Аккаунт": acc_name,
                "Действие": action_type_map.get(action["action_type"], action["action_type"]),
                "Цель": action["target_id"] or "-",
                "Успех": "✅" if action["success"] else "❌",
                "Ошибка": action["error_message"] or "-",
                "Время": time_str
            })

        df = pd.DataFrame(df_data)

        # Filter
        col1, col2 = st.columns(2)

        with col1:
            filter_account = st.multiselect(
                "Фильтр по аккаунту",
                options=df["Аккаунт"].unique()
            )

        with col2:
            filter_action = st.multiselect(
                "Фильтр по действию",
                options=df["Действие"].unique()
            )

        # Apply filters
        filtered_df = df
        if filter_account:
            filtered_df = filtered_df[filtered_df["Аккаунт"].isin(filter_account)]
        if filter_action:
            filtered_df = filtered_df[filtered_df["Действие"].isin(filter_action)]

        st.dataframe(filtered_df, use_container_width=True, hide_index=True)

        # Statistics
        st.subheader("Статистика")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            total_actions = len(actions)
            st.metric("Всего действий", total_actions)

        with col2:
            successful = sum(1 for a in actions if a["success"])
            st.metric("Успешных", successful)

        with col3:
            failed = total_actions - successful
            st.metric("Ошибок", failed)

        with col4:
            success_rate = (successful / total_actions * 100) if total_actions > 0 else 0
            st.metric("Success Rate", f"{success_rate:.1f}%")

    else:
        st.info("Нет логов активности")


def main():
    """Main Streamlit app"""
    st.set_page_config(
        page_title="TenChat NeuroBooster",
        page_icon="🚀",
        layout="wide"
    )

    # Initialize session state
    init_session_state()

    # Header
    st.title("🚀 TenChat NeuroBooster")
    st.markdown("**Self-Hosted сервис для автоматизации продвижения в TenChat**")

    # Check API connection
    health = api_request("GET", "/")
    if not health:
        st.error("⚠️ Не удается подключиться к API. Убедитесь, что FastAPI сервер запущен на http://localhost:8000")
        st.stop()

    # Render sidebar
    render_sidebar()

    # Tabs
    tab1, tab2, tab3 = st.tabs(["👤 Аккаунты", "⚙️ Задачи", "📊 Логи"])

    with tab1:
        render_accounts_tab()

    with tab2:
        render_tasks_tab()

    with tab3:
        render_logs_tab()

    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray;'>"
        "TenChat NeuroBooster v1.2.0 | Self-Hosted Automation"
        "</div>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
