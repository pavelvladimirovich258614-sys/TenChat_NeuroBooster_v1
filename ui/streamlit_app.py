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

    # Select accounts
    selected_accounts = st.multiselect(
        "Выберите аккаунты",
        options=[acc["id"] for acc in active_accounts],
        format_func=lambda x: next(acc["name"] for acc in active_accounts if acc["id"] == x)
    )

    # Task type
    task_type = st.radio(
        "Тип задачи",
        options=["warmup", "ai_post"],
        format_func=lambda x: "🔥 Прогрев (Лайкинг ленты)" if x == "warmup" else "✍️ AI Постинг"
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

    else:  # ai_post
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

            df_data.append({
                "ID": task["id"],
                "Аккаунт": acc_name,
                "Тип": "Прогрев" if task["task_type"] == "warmup" else "AI Пост",
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
