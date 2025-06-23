import requests
import datetime
import pandas as pd
import pytz # Для роботи з часовими поясами

# Функція для форматування дати в формат Mapon API (UTC)
def format_datetime_for_mapon(dt_object: datetime.datetime) -> str:
    # Mapon очікує ISO 8601 формат з UTC (Z)
    return dt_object.strftime('%Y-%m-%dT%H:%M:%S') + 'Z'

# Функція для отримання списку юнітів
def get_unit_list(api_key: str) -> list:
    url = f"https://mapon.com/api/v1/unit/list.json?key={api_key}"
    print(f"[Main] Спроба отримати список юнітів за URL: {url}")
    try:
        response = requests.get(url)
        response.raise_for_status() # Викликає виняток для HTTP помилок (4xx або 5xx)
        data = response.json()
        print(f"[Main] Відповідь від unit/list.json отримано.")

        if 'data' in data and 'units' in data['data'] and isinstance(data['data']['units'], list):
            all_units = data['data']['units']
            print(f"[Main] Успішно отримано {len(all_units)} юнітів з API.")
            
            filtered_units = []
            units_filtered_out = 0
            for unit in all_units:
                # Фільтруємо юніти, щоб переконатися, що unit_id є дійсним
                if unit.get('unit_id') is not None and isinstance(unit.get('unit_id'), int) and unit['unit_id'] > 0:
                    filtered_units.append(unit)
                else:
                    print(f"[Main] Юніт \"{unit.get('label') or unit.get('number') or 'ID:' + str(unit.get('unit_id'))}\" (ID: {unit.get('unit_id')}) пропущений: unit_id недійсний або відсутній.")
                    units_filtered_out += 1
            print(f"[Main] Всього юнітів пропущено (некоректний ID): {units_filtered_out}.")
            print(f"[Main] Для подальшої обробки вибрано {len(filtered_units)} юнітів.")
            
            if not filtered_units:
                print('Увага! Після фільтрації не знайдено жодного юніта з дійсним unit_id. Перевірте дані в Mapon.')
            
            return filtered_units
        else:
            print('Помилка! Неочікуваний формат відповіді від Mapon API для unit/list.json. JSON-структура не містить data.units.')
            print(f'Повна відповідь: {response.text}')
            return []
    except requests.exceptions.RequestException as e:
        print(f"Критична помилка при отриманні списку юнітів: {e}")
        return []

# Функція для отримання даних одометра CAN
def fetch_odometer(api_key: str, unit_id: str, datetime_obj: datetime.datetime):
    formatted_date = format_datetime_for_mapon(datetime_obj)
    url = f"https://mapon.com/api/v1/unit_data/can_point.json?key={api_key}&unit_id={unit_id}&datetime={formatted_date}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        if data.get('data') and data['data'].get('units') and \
           isinstance(data['data']['units'], list) and len(data['data']['units']) > 0 and \
           data['data']['units'][0].get('total_distance') and \
           isinstance(data['data']['units'][0]['total_distance'].get('value'), (int, float)):
            return data['data']['units'][0]['total_distance']['value']
        else:
            return None # Використовуємо None для відсутності даних
    except requests.exceptions.RequestException as e:
        print(f"[Odometer] Помилка при отриманні одометра CAN для Unit ID {unit_id} на {formatted_date}: {e}")
        return None

# Функція для отримання рівня палива
def fetch_fuel_level(api_key: str, unit_id: str, target_datetime: datetime.datetime, fuel_type: str):
    # Встановлюємо часовий пояс на UTC для коректного порівняння
    target_datetime_utc = target_datetime.astimezone(pytz.utc)

    # Запит даних за весь день для пошуку найближчої точки
    start_of_day = target_datetime_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = target_datetime_utc.replace(hour=23, minute=59, second=59, microsecond=999999)

    formatted_from = format_datetime_for_mapon(start_of_day)
    formatted_till = format_datetime_for_mapon(end_of_day)

    # Спочатку спробуємо отримати дані від сенсора
    data_source_sensor = 'sensor'
    url_sensor = f"https://mapon.com/api/v1/fuel/data.json?key={api_key}&unit_id={unit_id}&from={formatted_from}&till={formatted_till}&data_source={data_source_sensor}"

    try:
        response_sensor = requests.get(url_sensor)
        response_sensor.raise_for_status()
        data_sensor = response_sensor.json()

        raw_values_sensor = data_sensor.get('data', {}).get('sensor', {}).get('tanks', [{}])[0].get('values')
        if raw_values_sensor and isinstance(raw_values_sensor, list) and len(raw_values_sensor) > 0:
            points = sorted([
                {'datetime': datetime.datetime.fromisoformat(point['gmt'].replace('Z', '+00:00')), 'value': point['value']}
                for point in raw_values_sensor if isinstance(point.get('value'), (int, float)) and point['value'] >= 0
            ], key=lambda x: x['datetime'])

            if points:
                found_point = None
                if fuel_type == 'start':
                    # Шукаємо першу точку, яка >= target_datetime
                    found_point = next((p for p in points if p['datetime'] >= target_datetime_utc), None)
                    if not found_point: # Якщо таких немає, беремо найпершу точку дня
                        found_point = points[0]
                elif fuel_type == 'end':
                    # Шукаємо останню точку, яка <= target_datetime
                    for p in reversed(points):
                        if p['datetime'] <= target_datetime_utc:
                            found_point = p
                            break
                    if not found_point: # Якщо таких немає, беремо найостаннішу точку дня
                        found_point = points[-1]
                
                if found_point:
                    return round(found_point['value'], 2)

        # Якщо в 'sensor' нічого не знайшлося, спробуємо отримати дані від CAN (рівень палива)
        data_source_can = 'can'
        url_can = f"https://mapon.com/api/v1/fuel/data.json?key={api_key}&unit_id={unit_id}&from={formatted_from}&till={formatted_till}&data_source={data_source_can}"
        
        response_can = requests.get(url_can)
        response_can.raise_for_status()
        data_can = response_can.json()

        raw_values_can = data_can.get('data', {}).get('can', {}).get('tanks', [{}])[0].get('values')
        if raw_values_can and isinstance(raw_values_can, list) and len(raw_values_can) > 0:
            points = sorted([
                {'datetime': datetime.datetime.fromisoformat(point['gmt'].replace('Z', '+00:00')), 'value': point['value']}
                for point in raw_values_can if isinstance(point.get('value'), (int, float)) and point['value'] >= 0
            ], key=lambda x: x['datetime'])

            if points:
                found_point = None
                if fuel_type == 'start':
                    found_point = next((p for p in points if p['datetime'] >= target_datetime_utc), None)
                    if not found_point:
                        found_point = points[0]
                elif fuel_type == 'end':
                    for p in reversed(points):
                        if p['datetime'] <= target_datetime_utc:
                            found_point = p
                            break
                    if not found_point:
                        found_point = points[-1]
                
                if found_point:
                    return round(found_point['value'], 2)
    
    except requests.exceptions.RequestException as e:
        print(f"[FuelLevel] Критична помилка при отриманні рівня палива для Unit ID {unit_id} (тип: {fuel_type}) на {format_datetime_for_mapon(target_datetime)} : {e}")
    
    return None

# Функція для отримання зведених даних по паливу (заправки, зливи, витрата)
def fetch_fuel_summary_data(api_key: str, unit_id: str, start_date: datetime.datetime, end_date: datetime.datetime):
    formatted_from = format_datetime_for_mapon(start_date)
    formatted_till = format_datetime_for_mapon(end_date)
    url = f"https://mapon.com/api/v1/fuel/summary.json?key={api_key}&unit_id={unit_id}&from={formatted_from}&till={formatted_till}"

    fuel_summary = {
        'refuelled_sensor': None, 'drained_sensor': None, 'consumed_sensor': None, 'avg_consumption_sensor': None,
        'refuelled_can_level': None, 'drained_can_level': None, 'consumed_can_level': None, 'avg_consumption_can_level': None,
        'refuelled_flow': None, 'drained_flow': None, 'consumed_flow': None, 'avg_consumption_flow': None 
    }

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        if isinstance(data.get('data'), list) and len(data['data']) > 0:
            unit_summary = data['data'][0]

            # Дані Sensor
            if 'sensor' in unit_summary:
                if isinstance(unit_summary['sensor'].get('fueled'), (int, float)):
                    fuel_summary['refuelled_sensor'] = round(unit_summary['sensor']['fueled'], 2)
                if isinstance(unit_summary['sensor'].get('drained'), (int, float)):
                    fuel_summary['drained_sensor'] = round(unit_summary['sensor']['drained'], 2)
                if isinstance(unit_summary['sensor'].get('total_consumed'), (int, float)):
                    fuel_summary['consumed_sensor'] = round(unit_summary['sensor']['total_consumed'], 2)
                if isinstance(unit_summary['sensor'].get('avg_consumption'), (int, float)):
                    fuel_summary['avg_consumption_sensor'] = round(unit_summary['sensor']['avg_consumption'], 2)
            
            # Дані CAN (рівень палива або інші зведені дані CAN)
            if 'can' in unit_summary:
                if isinstance(unit_summary['can'].get('fueled'), (int, float)):
                    fuel_summary['refuelled_can_level'] = round(unit_summary['can']['fueled'], 2)
                if isinstance(unit_summary['can'].get('drained'), (int, float)):
                    fuel_summary['drained_can_level'] = round(unit_summary['can']['drained'], 2)
                if isinstance(unit_summary['can'].get('total_consumed'), (int, float)):
                    fuel_summary['consumed_can_level'] = round(unit_summary['can']['total_consumed'], 2)
                if isinstance(unit_summary['can'].get('avg_consumption'), (int, float)):
                    fuel_summary['avg_consumption_can_level'] = round(unit_summary['can']['avg_consumption'], 2)

            # Дані FLOW (проточний датчик)
            if 'flow' in unit_summary:
                if isinstance(unit_summary['flow'].get('fueled'), (int, float)):
                    fuel_summary['refuelled_flow'] = round(unit_summary['flow']['fueled'], 2)
                if isinstance(unit_summary['flow'].get('drained'), (int, float)):
                    fuel_summary['drained_flow'] = round(unit_summary['flow']['drained'], 2)
                if isinstance(unit_summary['flow'].get('total_consumed'), (int, float)):
                    fuel_summary['consumed_flow'] = round(unit_summary['flow']['total_consumed'], 2)
                if isinstance(unit_summary['flow'].get('avg_consumption'), (int, float)):
                    fuel_summary['avg_consumption_flow'] = round(unit_summary['flow']['avg_consumption'], 2)
            
            if not ('sensor' in unit_summary or 'can' in unit_summary or 'flow' in unit_summary):
                print(f"[FuelSummary] Для Unit ID {unit_id} відсутні дані 'sensor', 'can' і 'flow' у відповіді fuel/summary.json.")

            return fuel_summary
        else:
            return fuel_summary # Повертаємо ініціалізований словник з None значеннями
    except requests.exceptions.RequestException as e:
        print(f"Критична помилка при отриманні зведених даних палива для Unit ID {unit_id}: {e}")
        return fuel_summary # Повертаємо ініціалізований словник з None значеннями

# Допоміжна функція для перетворення timestamp в datetime в UTC (можливо, не потрібна, якщо використовуємо datetime об'єкти з pytz.utc)
def datetime_from_utc_timestamp(ts: float) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(ts, tz=pytz.utc)


# Основна функція, яка буде запускатися (потім інтегруємо в Streamlit)
def get_fleet_odometer_and_fuel_data(api_key: str, start_datetime: datetime.datetime, end_datetime: datetime.datetime) -> pd.DataFrame:
    
    # Переконаємося, що дати в UTC
    if start_datetime.tzinfo is None:
        start_datetime = pytz.utc.localize(start_datetime)
    else:
        start_datetime = start_datetime.astimezone(pytz.utc)
    
    if end_datetime.tzinfo is None:
        end_datetime = pytz.utc.localize(end_datetime)
    else:
        end_datetime = end_datetime.astimezone(pytz.utc)


    if start_datetime > end_datetime:
        print("Помилка: Дата і час початку періоду не може бути пізніше дати і часу закінчення.")
        return pd.DataFrame()

    filtered_units = get_unit_list(api_key)
    if not filtered_units:
        return pd.DataFrame()

    results = []

    for current_unit in filtered_units:
        current_unit_id = current_unit['unit_id']
        unit_name = current_unit.get('number') or current_unit.get('label') or f"Unit {current_unit_id}"

        print(f"--- Починаємо обробку юніта: {unit_name} (ID: {current_unit_id}) ---")

        odometer_start = fetch_odometer(api_key, current_unit_id, start_datetime)
        odometer_end = fetch_odometer(api_key, current_unit_id, end_datetime)

        distance = None
        current_numeric_distance = 0.0

        if isinstance(odometer_start, (int, float)) and isinstance(odometer_end, (int, float)):
            numeric_distance_calc = odometer_end - odometer_start
            if numeric_distance_calc < 0:
                distance = f"Скидання ({round(numeric_distance_calc, 2)} км)" # Вказуємо, що це скидання
                current_numeric_distance = 0.0 # Для розрахунків вважаємо пробіг 0
            else:
                distance = round(numeric_distance_calc, 2)
                current_numeric_distance = distance
        else:
            distance = "Немає даних для розрахунку"
            current_numeric_distance = 0.0


        fuel_level_start = fetch_fuel_level(api_key, current_unit_id, start_datetime, 'start')
        fuel_level_end = fetch_fuel_level(api_key, current_unit_id, end_datetime, 'end')
        
        fuel_summary_data = fetch_fuel_summary_data(api_key, current_unit_id, start_datetime, end_datetime)

        # Обробка даних Sensor
        consumed_sensor_numeric = fuel_summary_data.get('consumed_sensor')
        average_consumption_sensor = None
        
        # Спочатку перевіряємо, чи Mapon API вже надав avg_consumption для сенсора
        if fuel_summary_data.get('avg_consumption_sensor') is not None:
            average_consumption_sensor = fuel_summary_data.get('avg_consumption_sensor')
        # Якщо ні, і є витрата та пробіг, обчислюємо вручну
        elif isinstance(consumed_sensor_numeric, (int, float)) and consumed_sensor_numeric >= 0:
           if current_numeric_distance > 0:
               average_consumption_sensor = round((consumed_sensor_numeric / current_numeric_distance) * 100, 2)
           elif consumed_sensor_numeric > 0 and current_numeric_distance == 0:
               average_consumption_sensor = 'Немає пробігу' # Якщо є витрата, але немає пробігу
           else:
               average_consumption_sensor = 0.0 if consumed_sensor_numeric is not None else None # Якщо витрата 0 або None

        # Обробка даних CAN Flow
        total_consumed_flow = fuel_summary_data.get('consumed_flow')
        average_consumption_flow = fuel_summary_data.get('avg_consumption_flow') # Беремо готове значення з API

        # Визначаємо загальні заправки/зливи, надаючи пріоритет sensor, потім flow, потім can_level
        # Цей порядок можна налаштувати за потребою
        refuelled_overall = None
        if fuel_summary_data.get('refuelled_sensor') is not None:
            refuelled_overall = fuel_summary_data.get('refuelled_sensor')
        elif fuel_summary_data.get('refuelled_flow') is not None:
            refuelled_overall = fuel_summary_data.get('refuelled_flow')
        elif fuel_summary_data.get('refuelled_can_level') is not None:
            refuelled_overall = fuel_summary_data.get('refuelled_can_level')
        
        drained_overall = None
        if fuel_summary_data.get('drained_sensor') is not None:
            drained_overall = fuel_summary_data.get('drained_sensor')
        elif fuel_summary_data.get('drained_flow') is not None:
            drained_overall = fuel_summary_data.get('drained_flow')
        elif fuel_summary_data.get('drained_can_level') is not None:
            drained_overall = fuel_summary_data.get('drained_can_level')


        results.append({
            'Номер Автомобіля': unit_name,
            'Одометр CAN (початок)': odometer_start,
            'Одометр CAN (кінець)': odometer_end,
            'Пробіг (CAN, км)': distance,
            'Паливо в баку (початок, л)': fuel_level_start,
            'Паливо в баку (кінець, л)': fuel_level_end,   
            'Заправлено за період (л)': refuelled_overall, 
            'Зливи за період (л)': drained_overall,         
            'Витрата (датчик рівня, л)': consumed_sensor_numeric, 
            'Середня витрата (датчик рівня, л/100км)': average_consumption_sensor, 
            'Витрата (CAN Flow, л)': total_consumed_flow, 
            'Середня витрата (CAN Flow, л/100км)': average_consumption_flow 
        })
    
    df = pd.DataFrame(results)
    return df

# Приклад використання (пізніше це буде частина Streamlit)
if __name__ == '__main__':
    API_KEY = "23795daca9a629820c618d27c7aa7319b01656e7" # Замініть на ваш реальний API ключ для тестування
    
    # Дати та час у UTC для прикладу
    # 31 травня 21:00:00 UTC = 1 червня 00:00:00 Київ
    start_date_example = datetime.datetime(2025, 5, 31, 21, 0, 0, tzinfo=pytz.utc) 
    # 2 червня 20:59:59 UTC = 2 червня 23:59:59 Київ
    end_date_example = datetime.datetime(2025, 6, 2, 20, 59, 59, tzinfo=pytz.utc) 

    print(f"Запускаємо отримання даних з {start_date_example} по {end_date_example}")
    
    final_df = get_fleet_odometer_and_fuel_data(API_KEY, start_date_example, end_date_example)
    print("\n--- Результати ---")
    print(final_df)
    
    # Збереження в Excel (приклад)
    # final_df.to_excel("fleet_report.xlsx", index=False)
    # print("Звіт збережено до fleet_report.xlsx")