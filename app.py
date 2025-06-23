import streamlit as st
import datetime
import pytz # Для роботи з часовими поясами
import pandas as pd # Для роботи з DataFrame
from io import BytesIO # Для збереження Excel в пам'ять

# Імпортуємо нашу логіку з файлу mapon_api_client.py
from mapon_api_client import get_fleet_odometer_and_fuel_data

# --- Налаштування Streamlit сторінки ---
# Ця команда МАЄ бути ПЕРШОЮ командою Streamlit у скрипті!
st.set_page_config(
    page_title="Звіт автопарку Mapon",
    page_icon="🚗",
    layout="wide" # Робимо сторінку широкою для кращого відображення таблиць, але головне - використовуємо st.sidebar
)

# Користувацькі CSS для стилізації (оновлено на зелено-чорну гаму з читабельністю)
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
        color: #333333 !important; /* Змінено на темний колір для тексту, додано !important */
        background-color: white !important; /* Забезпечуємо білий фон, додано !important */
        box-shadow: inset 0 1px 3px rgba(0,0,0,0.1); /* Внутрішня тінь для ефекту глибины */
    }

    /* Стиль для плейсхолдерів (тексту заповнювача) */
    .stTextInput div[data-baseweb="input"] input::placeholder,
    .stDateInput div[data-baseweb="input"] input::placeholder,
    .stTimeInput div[data-baseweb="input"] input::placeholder,
    .stMultiSelect div[data-baseweb="select"] input::placeholder {
        color: #666666 !important; /* Темніший колір для плейсхолдера, додано !important */
        opacity: 1; /* Для Firefox */
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
    /* Колір тексту всередині поля мультиселекта (коли вводиться для пошуку) */
    .stMultiSelect div[data-baseweb="select"] input {
        color: #333333 !important; /* Темний колір тексту для поля вводу в мультиселекті */
    }
    /* Колір фону для вибраних елементів (колонок) */
    .stMultiSelect span[data-baseweb="tag"] {
        background-color: #eafbe1 !important; /* Дуже світлий зелений */
        color: #388e3c !important; /* Темно-зелений текст - ПОКРАЩЕНО */
        border: 1px solid #7ab800 !important; /* Зелена рамка */
        border-radius: 4px !important;
        font-size: 0.75rem !important;
        padding: 4px 8px !important;
        margin: 2px !important;
    }
    /* Колір іконки закриття вибраного елемента */
    .stMultiSelect span[data-baseweb="tag"] svg {
        fill: #388e3c !important; /* Темно-зелена іконка - ПОКРАЩЕНО */
    }
    /* Колір фону при наведенні на опцію у випадаючому списку */
    div[role="option"]:hover {
        background-color: #f0f8ed !important; /* Світло-зелений при наведенні */
    }
    /* Колір тексту опції у випадаючому списку */
    div[role="option"] span {
        color: #333333 !important; /* Темний текст для опцій - ПОКРАЩЕНО */
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
    
    /* Стилізація бічної панелі */
    /* Ці класи можуть змінюватися в майбутніх версіях Streamlit, тому краще перевіряти їх при оновленні */
    .st-emotion-cache-vk33z2, .st-emotion-cache-1f190u8 { /* Оновлені селектори для бічної панелі */
        background-color: #212121; /* Дуже темний сірий/майже чорний, як на Mapon */
        color: #ffffff; /* Білий текст на бічній панелі */
    }
    .st-emotion-cache-vk33z2 h1, .st-emotion-cache-1f190u8 h1,
    .st-emotion-cache-vk33z2 h2, .st-emotion-cache-1f190u8 h2,
    .st-emotion-cache-vk33z2 h3, .st-emotion-cache-1f190u8 h3 {
        color: #8BC34A; /* Зелені заголовки сайдбару */
        border-bottom: 1px solid #333333; /* Легка розділяюча лінія */
        padding-bottom: 0.5rem;
        margin-bottom: 1rem;
    }
    /* Лейбли input полів на сайдбарі */
    .st-emotion-cache-vk33z2 .stTextInput label,
    .st-emotion-cache-1f190u8 .stTextInput label,
    .st-emotion-cache-vk33z2 .stDateInput label,
    .st-emotion-cache-1f190u8 .stDateInput label,
    .st-emotion-cache-vk33z2 .stTimeInput label,
    .st-emotion-cache-1f190u8 .stTimeInput label,
    .st-emotion-cache-vk33z2 .stMultiSelect label,
    .st-emotion-cache-1f190u8 .stMultiSelect label,
    .st-emotion-cache-vk33z2 .stSelectbox label,
    .st-emotion-cache-1f190u8 .stSelectbox label {
        color: #ADD8E6; /* Світло-блакитний для лейблів на сайдбарі */
    }

    /* Стилі для тексту всередині полів на сайдбарі */
    .st-emotion-cache-vk33z2 .stTextInput div[data-baseweb="input"] input,
    .st-emotion-cache-1f190u8 .stTextInput div[data-baseweb="input"] input,
    .st-emotion-cache-vk33z2 .stDateInput div[data-baseweb="input"] input,
    .st-emotion-cache-1f190u8 .stDateInput div[data-baseweb="input"] input,
    .st-emotion-cache-vk33z2 .stTimeInput div[data-baseweb="input"] input,
    .st-emotion-cache-1f190u8 .stTimeInput div[data-baseweb="input"] input,
    .st-emotion-cache-vk33z2 .stSelectbox div[data-baseweb="select"],
    .st-emotion-cache-1f190u8 .stSelectbox div[data-baseweb="select"] {
        color: #e0e0e0 !important; /* Світлий текст у полях на сайдбарі */
        background-color: #333333 !important; /* Темний фон полів на сайдбарі */
        border-color: #555555 !important; /* Трохи світліша рамка на сайдбарі */
    }
    /* Стилі для плейсхолдерів на сайдбарі */
    .st-emotion-cache-vk33z2 .stTextInput div[data-baseweb="input"] input::placeholder,
    .st-emotion-cache-1f190u8 .stTextInput div[data-baseweb="input"] input::placeholder {
        color: #b0b0b0 !important; /* Світліший плейсхолдер на темному фоні сайдбару */
    }
    /* Стиль для мультиселекта на сайдбарі (вибрані теги) */
    .st-emotion-cache-vk33z2 .stMultiSelect span[data-baseweb="tag"],
    .st-emotion-cache-1f190u8 .stMultiSelect span[data-baseweb="tag"] {
        background-color: #333333 !important; /* Темний фон для тегів на сайдбарі */
        color: #ADD8E6 !important; /* Світло-блакитний текст тегів на сайдбарі */
        border-color: #666666 !important; /* Світліша рамка */
    }
    /* Іконка закриття тега на сайдбарі */
    .st-emotion-cache-vk33z2 .stMultiSelect span[data-baseweb="tag"] svg,
    .st-emotion-cache-1f190u8 .stMultiSelect span[data-baseweb="tag"] svg {
        fill: #ADD8E6 !important; /* Колір іконки закриття на сайдбарі */
    }
    /* Опції мультиселекта у випадаючому списку на сайдбарі */
    .st-emotion-cache-vk33z2 div[role="option"] span,
    .st-emotion-cache-1f190u8 div[role="option"] span {
        color: #333333 !important; /* Темний текст опцій */
    }
    .st-emotion-cache-vk33z2 div[role="option"]:hover,
    .st-emotion-cache-1f190u8 div[role="option"]:hover {
        background-color: #e0e0e0 !important; /* Світлий фон при наведенні */
    }

    </style>
    """, unsafe_allow_html=True)

# Ініціалізація session_state
if 'df_report' not in st.session_state:
    st.session_state.df_report = pd.DataFrame()
if 'report_generated' not in st.session_state:
    st.session_state.report_generated = False
if 'start_date_display' not in st.session_state:
    st.session_state.start_date_display = None
if 'end_date_display' not in st.session_state:
    st.session_state.end_date_display = None

# --- Бокова панель для введення API ключа та вибору періоду ---
st.sidebar.header("Налаштування API Mapon")
api_key = st.sidebar.text_input("Введіть ваш API ключ Mapon", type="password")

if not api_key:
    st.sidebar.warning("Будь ласка, введіть ваш Mapon API Key для продовження.")
    st.stop() # Зупиняємо виконання, якщо API ключ не введено

st.sidebar.markdown("---")
st.sidebar.header("Вибір періоду")

# Отримуємо поточну дату та час в Києві (або ваш бажаний часовий пояс)
kyiv_tz = pytz.timezone('Europe/Kiev')
now_kyiv = datetime.datetime.now(kyiv_tz)

# ВИПРАВЛЕНО: Дати за замовчуванням - вчора і сьогодні
default_start_date = (now_kyiv - datetime.timedelta(days=1)).date()
default_start_time = datetime.time(0, 0, 0) # Початок дня

default_end_date = now_kyiv.date()
default_end_time = datetime.time(23, 59, 59) # Кінець дня

# Вибір дати та часу початку на бічній панелі
start_date = st.sidebar.date_input("Дата початку", value=default_start_date)
start_time = st.sidebar.time_input("Час початку", value=default_start_time)

# Вибір дати та часу закінчення на бічній панелі
end_date = st.sidebar.date_input("Дата закінчення", value=default_end_date)
end_time = st.sidebar.time_input("Час закінчення", value=default_end_time)

# Об'єднуємо дату і час в локальному часовому поясі
start_datetime_local = datetime.datetime.combine(start_date, start_time)
end_datetime_local = datetime.datetime.combine(end_date, end_time)

# Локалізуємо і конвертуємо в UTC
start_datetime_utc = kyiv_tz.localize(start_datetime_local).astimezone(pytz.utc)
end_datetime_utc = kyiv_tz.localize(end_datetime_local).astimezone(pytz.utc)

# Перевірка, що дата початку не пізніше дати закінчення
if start_datetime_utc > end_datetime_utc:
    st.sidebar.error("Помилка: Дата та час початку періоду не може бути пізніше дати та часу закінчення.")
    st.stop() # Зупиняємо виконання, якщо дати некоректні

st.sidebar.markdown("---")

# --- Основна частина сторінки ---
st.title("Звіт по автопарку Mapon")
st.write("Отримайте детальний звіт по пробігу та витраті палива вашого автопарку за обраний період.")

# Визначаємо всі можливі колонки
all_possible_columns = [
    'Номер Автомобіля',
    'Одометр CAN (початок)',
    'Одометр CAN (кінець)',
    'Пробіг (CAN, км)',
    'Паливо в баку (початок, л)',
    'Паливо в баку (кінець, л)',
    'Заправлено за період (л)',
    'Зливи за період (л)',
    'Витрата (датчик рівня, л)',
    'Середня витрата (датчик рівня, л/100км)',
    'Витрата (CAN Flow, л)',
    'Середня витрата (CAN Flow, л/100км)'
]

# Мультиселект для вибору колонок, на основній панелі (як і було в попередньому коді)
selected_columns = st.multiselect(
    "Оберіть колонки для відображення у звіті:",
    options=all_possible_columns,
    default=all_possible_columns # За замовчуванням обираємо всі
)

# Кнопка генерації звіту на бічній панелі
if st.sidebar.button("Згенерувати Звіт"):
    if not api_key:
        # Це вже обробляється вище через st.stop(), але залишимо для дублюючої перевірки
        st.sidebar.error("Будь ласка, введіть ваш API ключ Mapon.")
    elif not selected_columns:
        st.sidebar.warning("Будь ласка, оберіть хоча б одну колонку для відображення у звіті.")
    else:
        with st.spinner("Завантаження даних... Це може зайняти деякий час для великих автопарків."):
            try:
                df = get_fleet_odometer_and_fuel_data(api_key, start_datetime_utc, end_datetime_utc)
                
                if not df.empty:
                    st.session_state.df_report = df # Зберігаємо повний DataFrame у session_state
                    st.session_state.report_generated = True
                    st.session_state.start_date_display = start_date.strftime('%Y%m%d') # Зберігаємо для імені файлу
                    st.session_state.end_date_display = end_date.strftime('%Y%m%d')    # Зберігаємо для імені файлу
                    st.success("Звіт успішно згенеровано!")
                else:
                    st.session_state.df_report = pd.DataFrame() # Очищаємо, якщо немає даних
                    st.session_state.report_generated = False
                    st.warning("Звіт не містить даних для обраного періоду. Перевірте обраний період та/або активність юнітів у Mapon.")
            
            except Exception as e:
                st.session_state.df_report = pd.DataFrame() # Очищаємо при помилці
                st.session_state.report_generated = False
                st.error(f"Виникла помилка при завантаженні даних: {e}. Будь ласка, перевірте API Key.")

# Відображення звіту, якщо він був згенерований
if st.session_state.report_generated and not st.session_state.df_report.empty:
    st.subheader("Попередній перегляд звіту")
    
    # Перевіряємо, чи всі selected_columns дійсно є в df_report
    actual_selected_columns = [col for col in selected_columns if col in st.session_state.df_report.columns]
    
    if actual_selected_columns:
        df_display = st.session_state.df_report[actual_selected_columns]
        st.dataframe(df_display, use_container_width=True)

        # Функція для конвертації DataFrame в Excel (кешується)
        @st.cache_data
        def convert_df_to_excel(df_to_convert):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_to_convert.to_excel(writer, index=False, sheet_name='Звіт по автопарку')
                worksheet = writer.sheets['Звіт по автопарку']
                for i, col in enumerate(df_to_convert.columns):
                    # Розширюємо стовпці для кращої читабельності
                    max_len = max(df_to_convert[col].astype(str).map(len).max(), len(col)) + 2
                    worksheet.set_column(i, i, max_len)
            processed_data = output.getvalue()
            return processed_data

        excel_data = convert_df_to_excel(df_display) # Передаємо відфільтрований DataFrame
        st.download_button(
            label="📥 Завантажити звіт у Excel",
            data=excel_data,
            # Використовуємо збережені дати для імені файлу
            file_name=f"Mapon_Звіт_Автопарку_{st.session_state.start_date_display}_{st.session_state.end_date_display}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    else:
        st.warning("Вибрані колонки не знайдені в згенерованому звіті або звіт порожній. Будь ласка, перегенеруйте звіт.")
elif st.session_state.report_generated and st.session_state.df_report.empty:
    st.warning("Звіт згенеровано, але він не містить даних для відображення з обраними параметрами.")
elif not st.session_state.report_generated:
    st.info("Введіть API ключ, оберіть період та натисніть 'Згенерувати Звіт', щоб отримати дані.")