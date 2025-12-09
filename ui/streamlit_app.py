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
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {e}")
        return None


def render_sidebar():
    """Render sidebar with account selection"""
    with st.sidebar:
        st.header("⚙️ Настройки")

        # Get all accounts
        accounts = api_request("GET", "/accounts")

        if accounts and len(accounts) > 0:
            st.subheader("Активный Аккаунт")

            # Account selector
            account_options = {acc["id"]: f"{acc['name']} ({acc['status']})" for acc in accounts}

            # Add "All accounts" option
            account_options[0] = "Все аккаунты"

            # Default to first account if nothing selected
            if st.session_state.selected_account_id is None:
                st.session_state.selected_account_id = 0

            selected_id = st.selectbox(
                "Выберите аккаунт:",
                options=list(account_options.keys()),
                format_func=lambda x: account_options[x],
                index=0 if st.session_state.selected_account_id == 0 else
                      list(account_options.keys()).index(st.session_state.selected_account_id),
                key="account_selector"
            )

            # Update session state
            if selected_id != st.session_state.selected_account_id:
                st.session_state.selected_account_id = selected_id
                st.rerun()

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

        st.divider()

        # Quick stats
        st.subheader("📈 Быстрая статистика")

        if accounts:
            active_count = sum(1 for acc in accounts if acc["status"] == "active")
            st.metric("Активных аккаунтов", f"{active_count}/{len(accounts)}")

        # Recent actions count
        actions = api_request("GET", "/actions?limit=1000")
        if actions:
            today_actions = sum(1 for a in actions
                              if datetime.fromisoformat(a["created_at"]).date() == datetime.now().date())
            st.metric("Действий сегодня", today_actions)


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
                        cookies_json = cookies_file.read().decode("utf-8")

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

        topic = st.text_area(
            "Тема статьи",
            placeholder="Напишите тему для статьи, например:\n'Как использовать AI для автоматизации маркетинга'",
            height=100
        )

        style = st.selectbox(
            "Стиль написания",
            options=["professional", "casual", "expert"],
            format_func=lambda x: {
                "professional": "Профессиональный",
                "casual": "Неформальный",
                "expert": "Экспертный"
            }[x]
        )

        parameters = {
            "topic": topic,
            "style": style
        }

    elif task_type == "mass_follow":
        st.markdown("### Параметры Масс-фолловинга")

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
        elif task_type == "ai_post" and not topic:
            st.error("Введите тему для статьи")
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

        # Auto-refresh for running tasks
        if any(task["status"] == "running" for task in tasks):
            st.info("⏳ Задачи выполняются... Страница обновится автоматически")
            import time
            time.sleep(5)
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

            df_data.append({
                "Аккаунт": acc_name,
                "Действие": action_type_map.get(action["action_type"], action["action_type"]),
                "Цель": action["target_id"] or "-",
                "Успех": "✅" if action["success"] else "❌",
                "Ошибка": action["error_message"] or "-",
                "Время": datetime.fromisoformat(action["created_at"]).strftime("%Y-%m-%d %H:%M:%S")
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
        "TenChat NeuroBooster v1.0 | Self-Hosted Automation"
        "</div>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
