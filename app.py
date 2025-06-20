import streamlit as st
import datetime
import pytz # Для роботи з часовими поясами
import pandas as pd # Для роботи з DataFrame
from io import BytesIO # Для збереження Excel в пам'ять

# Імпортуємо нашу логіку з файлу mapon_api_client.py
from mapon_api_client import get_fleet_odometer_and_fuel_data

# --- Налаштування Streamlit сторінки ---
st.set_page_config(
    page_title="Звіт автопарку Mapon",
    page_icon="🚗",
    layout="wide" # Робимо сторінку широкою для кращого відображення таблиць
)

# Користувацькі CSS для стилізації
st.markdown("""
    <style>
    /* Основний контейнер для відступів та фону */
    .main .block-container {
        padding-top: 2rem;
        padding-right: 2rem;
        padding-left: 2rem;
        padding-bottom: 2rem;
        background-color: #f8f8f8; /* Дуже світло-сірий фон для основного контенту, як на Mapon */
    }

    /* Стиль для заголовків H1 */
    h1 {
        color: #333333; /* Темно-сірий/майже чорний */
        font-family: 'Arial', sans-serif;
        border-bottom: none; /* Приберемо нижню лінію для H1 */
        margin-bottom: 1.5rem; /* Збільшимо відступ після H1 */
    }
    /* Стиль для всіх інших заголовків (H2, H3, H4, H5, H6) */
    h2, h3, h4, h5, h6 {
        color: #333333; /* Темно-сірий/майже чорний, як на Mapon */
        font-family: 'Arial', sans-serif;
        border-bottom: 1px solid #e0e0e0; /* Легка лінія під заголовками */
        padding-bottom: 0.5rem;
        margin-bottom: 1rem;
    }

    /* Стиль для кнопок */
    .stButton>button {
        background-color: #7ab800; /* Колір Mapon */
        color: white;
        border-radius: 4px;
        border: none;
        padding: 10px 20px;
        font-size: 16px;
        font-weight: bold;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        transition: background-color 0.2s ease, box-shadow 0.2s ease; /* Плавний перехід */
    }
    .stButton>button:hover {
        background-color: #6aaa00; /* Темніший зелений при наведенні */
        color: white;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }

    /* Стиль для текстових полів (API Key) та інших input-ів */
    .stTextInput label, .stDateInput label, .stTimeInput label, .stMultiSelect label, .stSelectbox label {
        color: #555555; /* Темніший колір для назви поля */
        font-size: 1rem;
        font-weight: bold;
        margin-bottom: 0.25rem; /* Зменшимо відступ між лейблом та полем */
        display: block; /* Забезпечимо, щоб лейбл займав свій рядок */
    }
    .stTextInput div[data-baseweb="input"] input,
    .stDateInput div[data-baseweb="input"] input,
    .stTimeInput div[data-baseweb="input"] input,
    .stSelectbox div[data-baseweb="select"] { /* Добавлено для Selectbox */
        border: 1px solid #b0b0b0; /* Трохи темніша рамка для кращого контрасту */
        border-radius: 4px;
        padding: 0.5rem 1rem;
        font-size: 1rem;
        color: #333333;
        box-shadow: inset 0 1px 3px rgba(0,0,0,0.1); /* Внутрішня тінь для ефекту глибины */
    }
    .stTextInput div[data-baseweb="input"]:focus-within,
    .stDateInput div[data-baseweb="input"]:focus-within,
    .stTimeInput div[data-baseweb="input"]:focus-within,
    .stSelectbox div[data-baseweb="select"]:focus-within { /* Добавлено для Selectbox */
        border-color: #7ab800; /* Зелена рамка при фокусі */
        box-shadow: 0 0 0 0.1rem rgba(122, 184, 0, 0.25); /* Легка зелена тінь при фокусі */
    }

    /* Стилізація мультиселекта */
    /* Основний контейнер мультиселекта */
    .stMultiSelect div[data-baseweb="select"] {
        border: 1px solid #b0b0b0; /* Рамка для всього віджета */
        border-radius: 4px;
        box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);
    }
    /* Колір фону для вибраних елементів (колонок) */
    .stMultiSelect span[data-baseweb="tag"] {
        background-color: #eafbe1 !important; /* Дуже світлий зелений */
        color: #388e3c !important; /* Темно-зелений текст */
        border: 1px solid #7ab800 !important; /* Зелена рамка */
        border-radius: 4px !important;
        font-size: 0.75rem !important;
        padding: 4px 8px !important;
        margin: 2px !important;
    }
    /* Колір іконки закриття вибраного елемента */
    .stMultiSelect span[data-baseweb="tag"] svg {
        fill: #388e3c !important;
    }
    /* Колір фону при наведенні на опцію у випадаючому списку */
    div[role="option"]:hover {
        background-color: #f0f8ed !important; /* Світло-зелений при наведенні */
    }
    /* Колір тексту опції у випадаючому списку */
    div[role="option"] span {
        color: #333333 !important;
    }
    /* Зменшуємо шрифт для вибраних елементів в полі мультиселекта (дублюємо, бо специфічність) */
    div[data-baseweb="select"] span.css-1n74gkj {
        font-size: 0.75rem !important;
    }
    /* Зменшуємо шрифт для елементів у випадаючому списку мультиселекта (дублюємо) */
    div[data-baseweb="select"] div.css-1n74gkj {
        font-size: 0.75rem !important;
    }
    /* Кнопка розкриття мультиселекта (стрілочка) */
    div[data-testid="stMultiSelect"] div[role="button"] {
        border-color: #7ab800 !important; /* Зелена рамка навколо кнопки розкриття */
    }

    /* Стилізація тексту в попередженнях та інформації (збільшений контраст) */
    .stAlert {
        font-size: 14px;
        border-radius: 4px;
        padding: 10px 15px; /* Більші відступи */
        margin-top: 1rem;
        margin-bottom: 1rem;
    }
    .stAlert.st-ee { /* Для info */
        background-color: #e6f7ff;
        color: #0056b3;
        border-left: 5px solid #2196f3;
    }
    .stAlert.st-eb { /* Для success */
        background-color: #eafbe1;
        color: #388e3c;
        border-left: 5px solid #4caf50;
    }
    .stAlert.st-dd { /* Для warning */
        background-color: #fff9e6;
        color: #e65100;
        border-left: 5px solid #ff9800;
    }
    .stAlert.st-cc { /* Для error */
        background-color: #ffe6e6;
        color: #d32f2f;
        border-left: 5px solid #f44336;
    }

    /* Зменшення шрифту в таблиці DataFrame та покращення контрасту */
    .stDataFrame {
        font-size: 0.75rem !important;
        border: 1px solid #e0e0e0;
        border-radius: 4px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        margin-top: 1.5rem; /* Відступ від попередніх елементів */
    }
    .stDataFrame table {
        font-size: 0.75rem !important;
        width: 100%;
        border-collapse: collapse; /* Приберемо подвійні межі */
    }
    .stDataFrame th, .stDataFrame td {
        font-size: 0.75rem !important;
        padding: 8px 12px;
        border-bottom: 1px solid #eeeeee; /* Легка межа між рядками */
        text-align: left;
    }
    .stDataFrame th {
        background-color: #f0f0f0;
        color: #555555;
        font-weight: bold;
        border-bottom: 2px solid #e0e0e0;
    }
    .stDataFrame tr:nth-child(even) {
        background-color: #f9f9f9;
    }
    .stDataFrame tr:hover {
        background-color: #e8f5e9;
    }
    
    /* Стилізація бічної панелі (якщо використовується) */
    .st-emotion-cache-vk33z2 { /* Цей клас може змінюватися в майбутніх версіях Streamlit */
        background-color: #212121; /* Дуже темний сірий/майже чорний, як на Mapon */
        color: #ffffff; /* Білий текст на бічній панелі */
    }
    .st-emotion-cache-vk33z2 .st-emotion-cache-1pxe4x4 {
        color: #dddddd; /* Світло-сірий для звичайних посилань */
    }
    .st-emotion-cache-vk33z2 .st-emotion-cache-1pxe4x4:hover {
        color: #7ab800; /* Зелений при наведенні */
    }
    .st-emotion-cache-vk33z2 .st-emotion-cache-1pxe4x4.active {
        color: #7ab800; /* Активний пункт зеленим */
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)


st.title("🌱 Звіт автопарку Mapon")
st.markdown("Тут ви можете отримати детальний звіт щодо одометра та витрат пального вашого автопарку за обраний період.")

# --- Введення API ключа ---
api_key = st.text_input("Введіть ваш Mapon API Key", type="password")

# Перевіряємо, чи введено API ключ
if not api_key:
    st.warning("Будь ласка, введіть ваш Mapon API Key для продовження.")
    st.stop()

# --- Вибір діапазону дат та часу ---
st.header("Оберіть період для звіту")

# Функции для обновления session_state для времени
def update_start_time():
    st.session_state['start_time_value'] = st.session_state['start_time_input_key']

def update_end_time():
    st.session_state['end_time_value'] = st.session_state['end_time_input_key']

# Инициализация session_state для хранения выбранного времени и часового пояса
if 'start_time_value' not in st.session_state:
    st.session_state['start_time_value'] = datetime.time(0, 0, 0)
if 'end_time_value' not in st.session_state:
    st.session_state['end_time_value'] = datetime.time(23, 59, 59)

# Получаем список всех часовых поясов из pytz
all_timezones = sorted(pytz.all_timezones)

# Определяем часовой пояс по умолчанию. Попробуем угадать местный, или установим Киев.
default_timezone = "Europe/Kiev" # Начальное значение по умолчанию
try:
    # Попытка получить локальный часовой пояс пользователя
    import tzlocal
    local_tz = tzlocal.get_localzone().zone
    if local_tz in all_timezones:
        default_timezone = local_tz
except Exception:
    pass # Если tzlocal не сработал или не установлен, оставим default_timezone

if 'selected_timezone' not in st.session_state:
    st.session_state['selected_timezone'] = default_timezone

# Виджет выбора часового пояса
selected_timezone_str = st.selectbox(
    "Оберіть ваш часовий пояс:",
    options=all_timezones,
    index=all_timezones.index(st.session_state['selected_timezone']), # Устанавливаем выбранный по умолчанию
    key="timezone_select_key",
    help="Всі дати та час нижче будуть інтерпретуватися у вибраному часовому поясі, а потім конвертовані в UTC для Mapon API."
)
# Обновляем session_state после выбора часового пояса
st.session_state['selected_timezone'] = selected_timezone_str

# Создаем объект часового пояса из выбранной строки
try:
    local_tz_object = pytz.timezone(selected_timezone_str)
except pytz.UnknownTimeZoneError:
    st.error(f"Помилка: Невідомий часовий пояс '{selected_timezone_str}'. Будь ласка, оберіть інший.")
    st.stop()

# Текущая дата в местном часовом поясе
now_local_datetime = datetime.datetime.now(local_tz_object)
default_start_date = (now_local_datetime - datetime.timedelta(days=1)).date()
default_end_date = now_local_datetime.date()


col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Дата початку (обраний часовий пояс)", value=default_start_date)
    start_time_selected = st.time_input(
        "Час початку (обраний часовий пояс)",
        value=st.session_state['start_time_value'],
        step=300, # Шаг в секундах (300 секунд = 5 минут)
        key="start_time_input_key", # Уникальный ключ для виджета
        on_change=update_start_time # Вызываем функцию при изменении
    )

with col2:
    end_date = st.date_input("Дата закінчення (обраний часовий пояс)", value=default_end_date)
    end_time_selected = st.time_input(
        "Час закінчення (обраний часовий пояс)",
        value=st.session_state['end_time_value'],
        step=300, # Шаг в секундах (300 секунд = 5 минут)
        key="end_time_input_key", # Уникальный ключ для виджета
        on_change=update_end_time # Вызываем функцию при изменении
    )

# --- КОНВЕРТАЦИЯ ЛОКАЛЬНОГО ВРЕМЕНИ В UTC ---
# 1. Объединяем дату и время без часового пояса (naive datetime)
start_datetime_naive = datetime.datetime.combine(start_date, start_time_selected)
end_datetime_naive = datetime.datetime.combine(end_date, end_time_selected)

# 2. Делаем naive datetime "aware" о выбранном часовом поясе
start_datetime_local = local_tz_object.localize(start_datetime_naive, is_dst=None)
end_datetime_local = local_tz_object.localize(end_datetime_naive, is_dst=None)

# 3. Конвертируем локализованные datetime в UTC
start_datetime_full = start_datetime_local.astimezone(pytz.utc)
end_datetime_full = end_datetime_local.astimezone(pytz.utc)

# Проверка, что дата начала не позднее даты окончания
if start_datetime_full > end_datetime_full:
    st.error("Помилка: Дата та час початку періоду не може бути пізніше дати та часу закінчення.")
    st.stop()

# --- Раздел для настройки отчета (выбор колонок) ---
st.header("Налаштування звіту")

# Названия колонок должны точно совпадать с тем, что возвращает get_fleet_odometer_and_fuel_data в mapon_api_client.py
all_possible_columns = [
    'Номер Автомобіля',
    'Одометр CAN (початок)',
    'Одометр CAN (кінець)',
    'Пробіг (CAN, км)',
    'Паливо в баку (початок, л)',
    'Паливо в баку (кінець, л)',
    'Заправлено за період (л)',
    'Зливи за період (л)',
    'Витрата (датчик, л)',
    'Середня витрата (л/100км)'
]

# Инициализация session_state для хранения выбранных колонок
if 'selected_columns_value' not in st.session_state:
    st.session_state['selected_columns_value'] = all_possible_columns # По умолчанию все колонки

# Функция для обновления session_state для колонок
def update_selected_columns():
    st.session_state['selected_columns_value'] = st.session_state['multiselect_columns_key']

selected_columns = st.multiselect(
    "Оберіть колонки для відображення у звіті:",
    options=all_possible_columns,
    default=st.session_state['selected_columns_value'],
    key="multiselect_columns_key", # Уникальный ключ
    on_change=update_selected_columns # Вызываем функцию при изменении
)

if not selected_columns:
    st.warning("Будь ласка, оберіть хоча б одну колонку для відображення.")
    st.stop()


# --- Кнопка для запуска отчета ---
st.write("")
if st.button("Згенерувати звіт", help="Натисніть, щоб отримати дані з Mapon"):
    st.info(f"Завантаження даних для періоду з {start_datetime_local.strftime('%Y-%m-%d %H:%M:%S %Z%z')} по {end_datetime_local.strftime('%Y-%m-%d %H:%M:%S %Z%z')}... (Це {start_datetime_full.strftime('%Y-%m-%d %H:%M:%S UTC')} по {end_datetime_full.strftime('%Y-%m-%d %H:%M:%S UTC')} у UTC).")

    # Запускаем нашу основную функцию из mapon_api_client.py
    with st.spinner('Отримання даних з Mapon API...'):
        try:
            df = get_fleet_odometer_and_fuel_data(api_key, start_datetime_full, end_datetime_full)
            
            if not df.empty:
                st.success("Дані успішно завантажено!")
                st.write("")
                
                # Фильтруем DataFrame по выбранным колонкам
                columns_to_show = [col for col in selected_columns if col in df.columns]
                
                if not columns_to_show:
                    st.warning("Обрані колонки не знайдено в отриманих даних. Відображаю всі доступні колонки.")
                    st.dataframe(df.style.highlight_null(), use_container_width=True)
                else:
                    st.subheader("Результати звіту")
                    df_display = df[columns_to_show]
                    st.dataframe(df_display.style.highlight_null(), use_container_width=True)

                # --- Кнопка для загрузки Excel ---
                st.write("")
                st.subheader("Завантажити звіт")
                
                @st.cache_data
                def convert_df_to_excel(df_to_convert):
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        df_to_convert.to_excel(writer, index=False, sheet_name='Звіт по автопарку')
                        worksheet = writer.sheets['Звіт по автопарку']
                        for i, col in enumerate(df_to_convert.columns):
                            max_len = max(df_to_convert[col].astype(str).map(len).max(), len(col)) + 2
                            worksheet.set_column(i, i, max_len)
                    processed_data = output.getvalue()
                    return processed_data

                excel_data = convert_df_to_excel(df_display)
                st.download_button(
                    label="📥 Завантажити звіт у Excel",
                    data=excel_data,
                    file_name=f"Mapon_Звіт_Автопарку_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
            else:
                st.warning("Звіт не містить даних. Перевірте обраний період або переконайтесь, що Mapon API повернув дані для активних юнітів.")
        
        except Exception as e:
            st.error(f"Виникла помилка при завантаженні даних: {e}. Будь ласка, перевірте API Key та спробуйте ще раз.")
            st.exception(e)