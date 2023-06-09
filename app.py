# Интеграция со streamlit
import streamlit as st
bot_url = "https://t.me/official_studobot"
ipynb_url = "https://github.com/rtccreator/data_hse_project2023/blob/main/main.ipynb"
st.title("Итоговый проект / Наука о данных / Волобуев Владислав")
st.header("В чем заключается проект?")
st.subheader("\nЭто универсальный бот-помощник для студента, который умеет:\n\
1) Отправлять расписание на завтра и давать рекомендации,\n\
2) Узнавать актуальный курс юаня к рублю, отправлять график и рекомендовать, что делать для заработка,\n\
3) Принимать большие списки с контактными данными и отправлять список юзеру обратно только с валидными e-mail адресами и телефонами,\n\
4) Узнавать температуру на какую-либо дату в 2022 году в городе Базель основываясь на предсказаниях ML-модели,\n\
5) Решать СЛАУ методом Крамера\n\n")

st.markdown(f'''<a href={bot_url}><button style="background-color:Red;color:White;border-radius:5px;padding:10px;margin:15px 0;border-color:Red;">Перейти в бота</button></a>''',
unsafe_allow_html=True)
st.header("\n\nВесь код:\n")
st.markdown(f'''<a href={ipynb_url}><button style="background-color:Green;color:White;border-radius:5px;padding:10px;margin:15px 0;border-color:Green;">Посмотреть исходный код ноутбука (Github)</button></a>''',
unsafe_allow_html=True)
#Далее код и его работа
####################################

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from PIL import Image
from io import BytesIO
import io
import requests

bot_inst = Bot(st.secrets.tg.TG_TOKEN)
dp_inst = Dispatcher(bot_inst)

@dp_inst.message_handler(commands=['start'])
async def init_command(message: types.Message):
    reply_kb = InlineKeyboardMarkup()
    functions = [("📆 Получить расписание", 'schedule'), ("🇨🇳🇷🇺 Узнать курс юаня и получить совет", 'yuan'),
                 ("🗃️ Проверить CSV-файл с контактными данными", 'contacts'), ("⛅ Узнать предсказание погоды в Базеле", 'weather'), ("🧮 Решить СЛАУ по Крамеру", 'solve')]
    for item_text, item_callback in functions:
        reply_kb.add(InlineKeyboardButton(item_text, callback_data=item_callback))
    await message.answer("Добро пожаловать! Я многофункциональный бот. Выберите действие:", reply_markup=reply_kb)

@dp_inst.callback_query_handler(lambda query: True)
async def process_query(callback_query: types.CallbackQuery):
    callback_id = callback_query.from_user.id
    callback_data = callback_query.data
    error_txt = "Произошла ошибка, попробуйте позже."

    if callback_data == 'schedule':
        await bot_inst.send_message(callback_id, "Введите группу:")
    elif callback_data == 'yuan':
        await bot_inst.send_message(callback_id, "Пожалуйста, ожидайте...")
        try:
            yuan_val, yuan_img = get_yuan()
            await bot_inst.send_message(callback_id, yuan_val)
            img_io = io.BytesIO()
            img_io.name = 'yuan.png'
            image.save(img_io, 'PNG')
            img_io.seek(0)
            await bot_inst.send_photo(callback_id, photo=img_io)
        except Exception:
            await bot_inst.send_message(callback_id, error_txt)
    elif callback_data == 'contacts':
        await bot_inst.send_message(callback_id, "Загрузите файл CSV с номерами телефонов и e-mail'ами:")
    elif callback_data == 'weather':
        await bot_inst.send_message(callback_id, 'Введите дату в формате "Номер дня <пробел> Месяц" для получения предсказания погоды:')
    elif callback_data == 'solve':
        await bot_inst.send_message(callback_id, "Введите СЛАУ в формате: [[2,5,-1,10], [1,-1,3,5], [3,2,4,4]]:")

@dp_inst.message_handler()
async def process_message(message: types.Message):
    message_text = message.text
    try:
        if message_text.isdigit():
            group_id = get_groups(message_text)
            schedule, advice = get_schedule(group_id)
            await message.answer(f"Расписание: {schedule}\nСоветы: {advice}")
        elif ".csv" in message_text:
            file_info = await bot_inst.get_file(message.document.file_id)
            downloaded_file = await bot_inst.download_file(file_info.file_path)
            processed_data = check_data(downloaded_file)
            await bot_inst.send_document(message.from_user.id, ("contacts.csv", processed_data))
        elif len(message_text.split(" ")) == 2:
            weather_report = forecast_weather(message_text)
            await message.answer(f"Температура в Базеле: {weather_report}")
        else:
            slau = eval(message_text)
            result = solve_cramer(slau)
            await message.answer(f"Результат: {result}")
    except Exception:
        await message.answer("Произошла ошибка, попробуйте позже.")

###функции

####основные функции бота
async def main():
    st.title("STODOBOT Telegram бот запущен!")
    st.write("Бот выполняет указанные выше функции. По всем остальным модулям - см. Jupyter Notebook!")

async def start_polling():
    await dp_inst.start_polling()
####конец

def get_an_advice(prompt_subj):
    openai.api_key = st.secrets.main.GPT_TOKEN
    #важный момент - для работы данного кода необходим api, где лимит
    #не превышен. вполне возможно, что может быть достигнут максимум по этому ключу

    subj_tokens = int(len(prompt_subj.split(",")) * 50)

    #рассчитываем кол-во токенов по длине кол-ва предметов в какой-то день
    preprompt = f"Предложи максимально кратко, как \
    лучше подготовиться студенту к следующим дисциплинам: \
    В общей сумме должно получиться максимум {subj_tokens} символов! Очень кратко!"
    #print(preprompt)

    max_tokens = subj_tokens + 100
    #дадим модели больше, чем просим, чтобы не обрывать ответ

    response = openai.ChatCompletion.create(
      model='gpt-3.5-turbo', #выбираем самую быструю общедоступную модель 3.5 turbo
      messages=[
            {'role': 'system', 'content': preprompt},
            {'role': 'user', 'content': prompt_subj},
      ],
        max_tokens = max_tokens
    )
    
    return response['choices'][0]['message']['content']

def get_groups(query):
    url = f"https://ruz.fa.ru/api/search?term={query}&type=group"
    response = requests.get(url)
    grps_raw = response.json()
    #здесь генератором проходимся по json-ответу и берем значения id и label,
    #отсекая ненужное, в нашем случае ненужное - это ситуация, когда в label
    #перечислены сразу несколько групп, что нерелевантно
    res = [[grps_raw[i]['id'], 
            grps_raw[i]['label'].split(";")] for i in range(len(grps_raw)) if len(grps_raw) > 0 and len(grps_raw[i]['label'].split(";")) == 1]
    
    return res

def get_schedule(group_id, date):
    #обращаемся по id и дате, даты конца и начала равны
    url = f"https://ruz.fa.ru/api/schedule/group/{group_id}?start={date}&finish={date}&lng=1"
    response = requests.get(url)
    rasp_raw = response.json()
    #берем только название дисциплины, начало и конец по времени
    res = [[rasp_raw[i]['discipline'],
            rasp_raw[i]['beginLesson'],
            rasp_raw[i]['endLesson']] for i in range(len(rasp_raw)) if len(rasp_raw) > 0]
    
    res_final = []
    for i in res:
        if i not in res_final:
            res_final.append(i) #избавляемся от дубликатов
            
    all_subj_prompt = ""
    for i in tmrw_schedule:
        if i[0] not in all_subj_prompt:
            all_subj_prompt += f"{i[0]}, "
        
    return res_final, get_an_advice(all_subj_prompt)

####

def get_yuan():
    driver = webdriver.Chrome()
    driver.get('https://www.investing.com/currencies/cny-rub-technical')
    time.sleep(2)
    cookie_button = driver.find_elements(By.ID, 'onetrust-accept-btn-handler')
    if len(cookie_button) > 0:
        cookie_button[0].click() #это мы нажимаем "продолжить" на куки-баннер, если он существует
    data_time_list_inv = [300, 1800, 86400, 'week', 'month']
    data_inv = []
    for i in data_time_list_inv:
        time.sleep(1)
        #немного ждем и нажимаем на ссылки, которые находятся внутри li с атрибутом data-period
        driver.find_element(By.CSS_SELECTOR, f"li[data-period=\"{i}\"] > a").click()
        time.sleep(1)
        #искомое находится в div с этим id:
        target_div_inv = driver.find_element(By.ID, 'techStudiesInnerWrap')
        data_inv.append(list(map(lambda element: element.text, target_div_inv.find_elements(By.TAG_NAME, 'div'))))
        #парсим текст каждого внутреннего divа для 5 минут, получаса, дня, недели, месяца
    
    driver.get('https://www.tradingview.com/symbols/CNYRUB/technicals/')
    data_time_list_tdv = ['5m', '30m', '1D', '1W', '1M']
    time.sleep(2)
    data_tdv = []
    for i in data_time_list_tdv:
        time.sleep(1)
        #аналогично с Инвестингом, только здесь ищем кнопку с определенным атрибутом
        #в id и после парсим с контейнера, добавляя в общий массив
        driver.find_element(By.CSS_SELECTOR, f"button[id=\"{i}\"]").click()
        time.sleep(1)
        data_tdv.append(driver.find_element(By.CLASS_NAME, 'countersWrapper-kg4MJrFB').text)
        #аналогично\

    driver.quit()
    
    #причесываем, убирая ненужные отступы
    investing_data_clean = []
    for i in data_inv:
        for j in i:
            j = j.replace("\n", "").split(":")
            investing_data_clean.append(j)

    tradingview_data_clean = [s.split('\n') for s in data_tdv]
    time_periods = ['5 min', '30 min', 'day', 'week', 'month']
    inv_data_pd = [investing_data_clean[i:i + 3] for i in range(0, len(investing_data_clean), 3)] 
    inv_for_pd_final = list(map(list, zip(*inv_data_pd))) #поворачиваем получившийся список
    df = pd.DataFrame(inv_for_pd_final, columns=time_periods)
    #преобразовываем в dataframe со столбцами наших временных интервалов
    final_yuan_dict = df.to_dict()

    c = 0
    for k, v in final_yuan_dict.items():
        final_yuan_dict[time_periods[c]][3] = tradingview_data_clean[c]
        c += 1
        
    driver = webdriver.Chrome()
    driver.get('https://www.profinance.ru/charts/cnyrub/lc11')
    time.sleep(2)
    driver.find_element(By.ID, 'chart_button_plus').click() #немного увеличим масштаб
    time.sleep(2)
    img_elem = driver.find_element(By.ID, 'chart_img')
    img_elem_src = img_elem.get_attribute('src')
    response = requests.get(img_elem_src) #обрабатываем ссылку на изображение
    img = Image.open(BytesIO(response.content)) #получаем наше изображение

    driver.quit()
    
    return final_yuan_dict, img

####

def check_data(file):
    df = pd.read_csv(file)
    df
    #обращаясь к регулярным выражениям, сделаем маски
    phone_mask = re.compile(r'^\+7\d{10}$') #формат +7XXXXXXXXXX
    email_mask = re.compile(r'^[\w\.-]+@[\w\.-]+\.\w+$') #базовый формат имейла

    def check_phone(phone):
        if phone_mask.match(phone):
            return True
        else:
            return False

    def check_email(email):
        if email_mask.match(email):
            return True
        else:
            return False
    #эти базовые функции мы применим на интересующие нас столбцы и сделаем два новых датафрейма
    #типы всех значений нужно также рассмотреть как строки, иначе регулярные выражения не сработают
    df['valid_phone'] = df['phone'].astype(str).apply(check_phone)
    df['valid_email'] = df['email'].astype(str).apply(check_email)

    valid_df = df[df['valid_phone'] & df['valid_email']] #объединяем строки, где нет ошибок

    return valid_df

####

def forecast_weather(date):
    if len(date.split(" ")) == 2:
        date += " 2022"
        #добавляем 2022, т.к. предсказываем именно по этому году
        #и конвертируем в datetime
        date = pd.to_datetime(date, format="%d %B %Y", dayfirst=True)
        date_sql = date.strftime('%Y-%m-%d')
        
        with sqlite3.connect('db_ml_res.db') as sql_conn:
            print(date_sql)
            res = pd.read_sql_query(f"SELECT * FROM weather_data WHERE date = '{date_sql} 00:00:00'", sql_conn)
        return [date_sql, f"{round(res['prediction'][0], 1)} C", f"{round(res['actual'][0], 1)} C"]
    else:
        return "Введите действительную дату в формате: день месяц"

def solve_cramer(slau):
    M = sp.Matrix(slau)
    M_coeff = M[:, :-1]
    M_const = M[:, -1]
    res = []
    
    if M_coeff.cols != M_coeff.rows:
        return 'Матрица не является квадратной, по Крамеру ее не решить, \
испольуйте, например, метод Гаусса'
    elif M_coeff.det() == 0:
        return 'Определитель основной матрицы равен 0, а это значит, \
что нет единственного решения!'
    else:
        for i in range(M_coeff.cols):
            M_temp = M_coeff.copy()
            M_temp[:, i] = M_const 
            #последовательно меняем столбцы матрицы на значения констант
            res.append(M_temp.det()/M_coeff.det())
            #добавляем к списку найденное значение переменной
            #после деления детерминанта на детерминант констант
            
    return res

###конец
    
if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(asyncio.gather(main(), start_polling()))


#END################################
