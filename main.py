# Импорт встроенных библиотек
import asyncio
import os

# Импорт нужных модулей и классов из библиотеки модулей aiogram
from aiogram import Bot, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import Dispatcher, FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils import executor

# Импорт функций из второго программного файла для подсчета статистики
import statistic_funcs as sf

# Получение токена из стороннего файла
# Файл не приложен в целях безопасности
# Для проверки работы бота можете создать собственный файл
# и поместить в него токен без кавычек и любых других обозначений
with open('token.txt') as token_file:
    token = token_file.read()

# Определение бота для дальнейшей работы
bot = Bot(token)
# Определение временного хранилища
storage = MemoryStorage()
# Определение диспетчера, который обрабатывает события с сервера ТГ
dp = Dispatcher(bot, storage=storage)


# Дочерний класс от встроенного в aiogram
# Нужен, чтобы записывать состояние ожидания работы с источником
class SourceState(StatesGroup):
    source = State()
    link = State()
    file = State()
    time_to_quit = State()


# Дочерний класс от встроенного в aiogram
# Нужен, чтобы записывать состояние ожидания работы с результатами
class ResultsState(StatesGroup):
    num_to_show = State()
    save_state = State()
    user_filename = State()


# Класс для хранения словарей результатов
class Results:
    # Словарь с общей статистикой (изначально - пустой)
    general_stats = dict()
    # Словарь со статистикой значимых слов (изначально - пустой)
    sensed_stats = dict()


async def on_startup(_):
    # Служебная функция, которая сообщает, когда бот запущен
    print('Бот готов к работе -)')


# Словарь источников
# Удобен при работе с callback data, чтобы не опечататься
p_sources = {'Интернет': 'site_source', 'Файл': 'file_source'}

# Словарь вариантов сохранений
# Удобен при работе с callback data, чтобы не опечататься
s_possibilities = {True: 'save', False: 'no_save'}


# Хэндлер для команд start (начать) и help
# Один на две команды, т.к. их смысл особо не отличается
@dp.message_handler(commands=['start', 'help'])
async def start_help_message(message: types.Message):
    # Функция для реакции на команды start и help
    # На вход принимает сообщение от пользователя
    # В результате отправляет пользователю сообщение

    # Переменные для сокращения дальнейшего кода
    chat_id = message.chat.id

    # Id стикера
    hello_sticker = 'CAACAgIAAxkBAAEEIYViLMx5E8-k5QhWXWeSLeAvbwlvhw' \
                    'ACogYAAmMr4gnSxdCG4azufCME'
    await bot.send_sticker(chat_id=chat_id,
                           sticker=hello_sticker)

    # Строка, в которой хранится содержание сообщения
    help_text = 'Привет, я Эдвард, телеграм-бот, который может прочитать ' \
                'текст с русскоязычной Википедии, ilibrary.ru или ' \
                'из файла .txt и сказать, какие слова чаще всего ' \
                'в нем встречаются. \n\n' \
                'Чтобы начать, нажми на /stats'
    # Отправка сообщения пользователю
    await bot.send_message(chat_id=chat_id, text=help_text)


# Хэндлер для команды stats, с которой начинается процесс обработки текста
@dp.message_handler(commands=['stats'], state=None)
async def ask_for_source(message: types.Message):
    # Функция для реакции на команду stats
    # На вход принимает сообщение от пользователя с текстом из команды
    # В результате отправляет вопрос об источнике текста и устанавливает
    # положение ожидания ответа

    # Установка положения ожидания источника
    await SourceState.source.set()

    # Создание раскладки для инлайн-клавиатуры
    source_markup = InlineKeyboardMarkup(row_width=1)
    site_button = InlineKeyboardButton(text='Из Интернета',
                                       callback_data=p_sources['Интернет'])
    file_button = InlineKeyboardButton(text='Из файла',
                                       callback_data=p_sources['Файл'])
    source_markup.add(site_button, file_button)

    # Строка с текстом вопроса
    source_question = 'Откуда взять текст для анализа?'
    # Отправка вопроса пользователю
    await bot.send_message(chat_id=message.chat.id,
                           text=source_question,
                           reply_markup=source_markup)


# Хэндлер для обработки callback data
# в состоянии ожидания ответа на вопрос об источнике текста
@dp.callback_query_handler(state=SourceState.source)
async def source_callback(call: types.CallbackQuery):
    # Функция обрабатывает callback data об источнике текста
    # На вход получает данные callback
    # В результате переправляет процесс, в зависимости от ответа

    # Переменные для сокращения дальнейшего кода
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    # Проверка нажатия какой-либо кнопки на инлайн-клавиатуре
    if call.message:

        # Если указан источник - Интернет
        if call.data == p_sources['Интернет']:
            # Установка положения ожидания ссылки
            await SourceState.link.set()

            # Текст со следующим вопросом
            link_question = 'Хорошо! Жду ссылку на страницу\n\n' \
                            'Обратите внимание, что я умею работать только ' \
                            'со статьями на ru.wikipedia.org или ilibrary.ru'

            # Отправка пользователю соообщения об ожидании
            await bot.edit_message_text(chat_id=chat_id,
                                        message_id=message_id,
                                        text=link_question,
                                        reply_markup=None)

        # Если указан источник - файл
        if call.data == p_sources['Файл']:
            # Установка положения ожидания файла
            await SourceState.file.set()

            # Текст со следующим вопросом
            file_question = 'Хорошо! Жду файл в формате .txt'

            # Отправка пользователю соообщения об ожидании
            await bot.edit_message_text(chat_id=chat_id,
                                        message_id=message_id,
                                        text=file_question,
                                        reply_markup=None)


async def get_link(message, state):
    # Функция возвращает ссылку из пользовательского сообщения
    # На вход получает сообщение и положение
    # На выход возвращает строку со ссылкой

    # Запись ссылки из сообщения в оперативную память
    async with state.proxy() as s:
        s['link'] = message.text.strip()

    # Получение данных в переменную из оперативной памяти
    async with state.proxy() as data:
        url = data['link']

    # Возвращение строки со ссылкой
    return url


# Хэндлер активен в состоянии ожидания ссылки
@dp.message_handler(state=SourceState.link)
async def analyze_link(message: types.Message, state: FSMContext):
    # Функция начинает процесс анализа текст из интернета
    # На вход получает сообщение со ссылкой
    # В результате переходит к стадии анализа, общей для статей и документов

    # Переменные для сокращения дальнейшего кода
    chat_id = message.chat.id

    # Получение ссылки из сообщения
    url = await get_link(message=message, state=state)
    # Завершение текущего статуса положения
    await state.finish()

    # Проверка правильности ссылки
    # Если ссылка подходит для работы (с нужного сайта, код ответа - 200)
    if sf.check_link(url):

        # Текст для сообщения пользователю
        connection_text = 'Отлично, начинаю работу!'

        # Отправка сообщения о начале работы пользователю
        await bot.send_message(chat_id=chat_id,
                               text=connection_text)

        # Получение текста со страницы
        # Если это ссылка на Википедию
        if 'wikipedia' in url:
            # то программа обращается к функции для Википедии
            raw_text = sf.get_text_from_wiki(url)

        # Если это ссылка на ilibrary
        if 'ilibrary' in url:
            # то программа обращается к функции для ilibrary
            raw_text = sf.get_text_from_illibrary(url)

        # Получив текст, запускает функцию, которая регулирует процесс анализа
        await analyze(message, raw_text)

    # Если ссылка не подоходит для работы (не тот сайт или код ответа не 200)
    else:
        # Текст для сообщения об ошибке
        wrong_link_warning = 'Ссылка кажется неверной, жду новую'

        # Отправка сообщения об ошибке
        await bot.send_message(chat_id=chat_id,
                               text=wrong_link_warning)

        # Установка статуса ожидания ссылки
        await SourceState.link.set()


def remove_file(file_class):
    # Функция удаляет файл после его чтения
    # На вход получает класс файла, как его возвращает aiogram
    # В результате уделяет файл

    # Определение пути к файлу
    file_path = os.path.join(file_class.name)
    # Удаление файла
    os.remove(file_path)


# Хэндлер активен в состоянии ожидания файла, реагирует на входящие файлы
@dp.message_handler(state=SourceState.file,
                    content_types=types.ContentTypes.DOCUMENT)
async def analyze_file(message: types.Message, state: FSMContext):
    # Функция начинает процесс анализа текста из файла
    # На вход получает сообщение с файлом
    # В результате переходит к стадии анализа, общей для статей и докумнетов

    # Переменные для сокращения дальнейшего кода
    chat_id = message.chat.id
    message_id = message.message_id + 1

    # Текст уведомления о загрузке
    file_download_text = 'Проникаю в файл...'

    # Уведомление пользователя о загрузке
    await bot.send_message(chat_id=chat_id,
                           text=file_download_text)

    # Скачивание файла
    document = message.document
    file_class = await document.download(destination_dir=os.getcwd())

    # Завершение состояния положений
    await state.finish()

    # Текст уведомления о проверке
    file_check_text = 'Проверяю файл...'

    # Уведомление пользователя о проверке
    await bot.edit_message_text(chat_id=chat_id,
                                message_id=message_id,
                                text=file_check_text)

    # Проверка расширения текста
    # Если расширение - txt, то работа продолжается
    if file_class.name.endswith('.txt'):

        # Получить сообщение об ошибке и текст из файла
        error, text = sf.get_text_from_file(file_class.name)

        # Удалить файл после использования, чтобы они не копились
        remove_file(file_class)

        # Если возникла ошибка в кодировке файла
        if error:

            # Текст уведомления
            unreadable_text = 'К сожалению, не удалось прочитать ' \
                              'содержимое файла, ' \
                              'попробуйте файл в другой кодировке'

            # Отправка уведомления пользователю
            await bot.edit_message_text(chat_id=chat_id,
                                        message_id=message_id,
                                        text=unreadable_text)
        # Если ошибки не возникло
        else:
            # Анализ текста
            await analyze(message, text)

    # Если расширение - не txt, то бот просит новый файл
    else:

        # Удаление текущего файла
        remove_file(file_class)

        # Текст уведомления
        wrong_file_text = 'Расширение этого файла – не txt, ' \
                          'я не умею с таким работать. Жду новый файл'

        # Уведомление пользователя
        await bot.edit_message_text(chat_id=chat_id,
                                    message_id=message_id,
                                    text=wrong_file_text)

        # Установка состояния ожидания файла
        await SourceState.file.set()


async def analyze(message, text):
    # Регулирует весь процесс анализа
    # На вход получает сообщение из предыдущей функции для работы с чатом
    # и текст для анализа
    # В результате направляет процесс на вывод результатов пользователю

    # Переменные для сокращения дальнейшего кода
    chat_id = message.chat.id
    message_id = message.message_id + 1

    # Текст для сообщения
    text_download_text = 'Открываю текст...'
    # Редактирование предыдущего сообщения бота
    await bot.edit_message_text(chat_id=chat_id,
                                message_id=message_id,
                                text=text_download_text)

    # Получение "чистого" текста
    clean_text = sf.clean_text(text)

    # Текст для сообщения
    text_analyze_text = 'Анализирую текст...'
    # Редактирование предыдущего сообщения бота
    await bot.edit_message_text(chat_id=chat_id,
                                message_id=message_id,
                                text=text_analyze_text)

    # Создание необходимых списков слов
    words_list = sf.get_words_list(clean_text)  # Все слова
    infinitives_list = sf.get_infinitives(words_list)  # Все слова в инфинитиве
    unique_words_list = sf.get_unique_words(infinitives_list)  # Уникальные слова

    # Текст для сообщения
    result_collecting_text = 'Собираю результаты...'
    # Редактирование предыдущего сообщения бота
    await bot.edit_message_text(chat_id=chat_id,
                                message_id=message_id,
                                text=result_collecting_text)

    # Присвоение пустым словарям значений со статистикой
    # Общая статистика всех слов
    Results.general_stats = sf.sort_dict_by_value(
        sf.get_general_stat_dict(infinitives_list,
                                 unique_words_list))
    # Статистика слов - частей речи, несущих смысл
    Results.sensed_stats = sf.sort_dict_by_value(
        sf.get_sensed_vocabulary_dict(Results.general_stats))

    # Переход к выводу результатов
    await ready_results(message)


async def ready_results(message):
    # Функция отправляет сообщает пользователю о готовых результатах
    # и начинает процесс их демонстрации
    # На вход получает сообщение из предыдущей функции
    # В результате спрашивает пользователя, какие результаты вывести

    # Текст вопроса
    num_to_show_text = 'Результаты готовы! \n\n' \
                       'Сколько топовых слов показать?\n' \
                       '(не более 5; рекомендуется – 3)'
    # Редактирование предыдущего сообщения для выведения вопроса
    await bot.edit_message_text(chat_id=message.from_user.id,
                                message_id=message.message_id + 1,
                                text=num_to_show_text)

    # Устанавливает состояние ожидания ответа о количестве
    await ResultsState.num_to_show.set()


# Хэндлер активен только в состоянии, когда ожидается ответ о количестве
# показываемых результатов
@dp.message_handler(state=ResultsState.num_to_show)
async def show_results(message: types.Message, state: FSMContext):
    # Функция получает отправляет пользователю топовые результаты анализа
    # На вход получает сообщение
    # В результате отправляет результаты анализа и спрашивает,
    # нужно ли их сохранить в файлы

    # Переменные для сокращения дальнейшего кода
    chat_id = message.chat.id

    # Сохраняет число из входящего сообщения в оперативную память
    async with state.proxy() as s:
        s['num_to_show'] = message.text.strip()

    # Получает число из оперативной памяти
    async with state.proxy() as data:
        num_to_show = data['num_to_show']

    # Завершает состояние ожидания числа
    await state.finish()

    # Если полученный ответ можно превратить в integer
    try:
        # Превращение числа из строки в integer
        num_to_show = int(num_to_show)

        # Если пользователь попросил показать результаты
        if num_to_show > 0:
            # Генерация текста результатов
            general_stats_text = sf.generate_result_text(Results.general_stats,
                                                         num_to_show)
            sensed_stats_text = sf.generate_result_text(Results.sensed_stats,
                                                        num_to_show)

            # Определение заголовков
            general_title = 'Результаты подсчета всех слов'
            sensed_title = 'Результаты подсчета слов, несущих смысл\n' \
                           '(то есть всех частей речи, кроме предлогов, ' \
                           'междометий, союзов и местоимений)'

            # Склейка частей текста воедино
            whole_result_text = f'{general_title}\n\n{general_stats_text}\n' \
                                f'{sensed_title}\n\n{sensed_stats_text}'

            # Отправка результатов
            await bot.send_message(chat_id=chat_id,
                                   text=whole_result_text)

        # Переход к процессу сохранения результатов
        await save_or_not(message)

    # Если полученный ответ невозможно превратить в integer
    except ValueError:

        # Устанавка состояния ожидания числа
        await ResultsState.num_to_show.set()

        # Текст предупреждения для пользователя
        not_num_warning = 'Я ожидал получить число цифрами... Попробуйте снова'

        # Отправка предупреждения пользователю
        await bot.send_message(chat_id=chat_id,
                               text=not_num_warning)


async def save_or_not(message):
    # Функция спрашивает пользователя, нужно ли сохранить результаты
    # На вход получает сообщение из предыдущей функции
    # В результате отправляет сообщение

    # Генерация инлайн-клавиатуры
    save_or_not_markup = InlineKeyboardMarkup(row_width=1)
    save_button = InlineKeyboardButton(text='Сохранить статистику в csv',
                                       callback_data=s_possibilities[True])
    not_button = InlineKeyboardButton(text='Не сохранять',
                                      callback_data=s_possibilities[False])
    save_or_not_markup.add(save_button, not_button)

    save_question = 'Сохранить статистику в файл csv?\n\n' \
                    'Если не сохраните, то она будет утеряна'

    # Установка состояния ожидания ответа
    await ResultsState.save_state.set()
    # Отправка вопроса
    await bot.send_message(chat_id=message.from_user.id,
                           text=save_question,
                           reply_markup=save_or_not_markup)


# Хэндлер активен в положении ожидания ответа на вопрос, сохранять ли результаты
@dp.callback_query_handler(state=ResultsState.save_state)
async def save_file(call: types.CallbackQuery, state: FSMContext):
    # Функция реагирует на ответ пользователя
    # На вход получает данные callback
    # В результате направляет процесс в функции в зависимости
    # от пользовательского ответа

    # Переменные для сокращения дальнейшего кода
    chat_id = call.message.chat.id

    # Проверка, что кнопка нажата
    if call.message:

        # Убирание клавиатуры после ее использования
        await bot.edit_message_reply_markup(chat_id=chat_id,
                                            message_id=call.message.message_id,
                                            reply_markup=None)

        # Если решено сохранять результаты
        if call.data == s_possibilities[True]:
            # Установка положения ожидания названия файлов
            await ResultsState.user_filename.set()

            # Текст вопроса
            filename_question = 'Как назвать файл?'
            # Отправка вопроса пользователю
            await bot.send_message(chat_id=chat_id,
                                   text=filename_question)

        # Если решено не сохранять результаты
        if call.data == s_possibilities[False]:
            # Положение ожидания завершается
            await state.finish()

            # Id стикера
            throw_sticker = 'CAACAgIAAxkBAAEEIYdiLM0jigTJaj_' \
                            'E5CyB1XmRsJXZ_gACrQYAAmMr4glQA_NT5ANj9iME'
            # Отправка стикера
            await bot.send_sticker(chat_id=chat_id,
                                   sticker=throw_sticker)

            # Бот прощается с пользователем
            await goodbye(call.message)


async def get_user_filename(state, message):
    # Функция получает пользовательское название файла из сообщения
    # На вход получает состояние и сообщение
    # В результате возвращает строку с пользовательским названием файла

    async with state.proxy() as s:
        s['filename'] = message.text.strip()

    # Получение данных в переменную из оперативной памяти
    async with state.proxy() as data:
        user_filename = data['filename']

    return user_filename


# Хэндлер активен в положении ожидания пользовательского названия файла
@dp.message_handler(state=ResultsState.user_filename)
async def save_files(message: types.Message, state: FSMContext):
    # Функция генерирует файлы и отправляет их пользователю
    # На вход получает сообщение с пользовательским название файла
    # В результате отправляет файлы и прощается с пользователем

    # Переменные для сокращения дальнейшего кода
    chat_id = message.chat.id

    # Получение данных в переменную из оперативной памяти
    user_filename = await get_user_filename(state, message)

    # Завершение положения
    await state.finish()

    # Генерация названий файлов
    general_filename = sf.generate_filename(user_filename, '_general')
    sensed_filename = sf.generate_filename(user_filename, '_sensed')

    # Генерация содержаний файлов
    general_line = sf.generate_line(Results.general_stats)
    sensed_line = sf.generate_line(Results.sensed_stats)

    # Создание файлов и сохранение путей к ним
    general_path = sf.write_to_file(general_line, general_filename)
    sensed_path = sf.write_to_file(sensed_line, sensed_filename)

    # Создание файлов
    general_file = types.input_file.InputFile(path_or_bytesio=general_path,
                                              filename=general_filename)
    sensed_file = types.input_file.InputFile(path_or_bytesio=sensed_path,
                                             filename=sensed_filename)

    # Определение описаний файлов для сообщений
    general_caption = 'Файл со статистикой всех слов'
    sensed_caption = 'Файл со статистикой слов, несущих смысл'

    # Отправка файлов пользователю
    await bot.send_document(chat_id=chat_id,
                            document=general_file,
                            caption=general_caption)
    await bot.send_document(chat_id=chat_id,
                            document=sensed_file,
                            caption=sensed_caption)

    # Удаление файлов с диска
    os.remove(general_path)
    os.remove(sensed_path)

    # Прощание с пользователем
    await goodbye(message)


async def goodbye(message):
    # Функция прощается с пользователем
    # На вход получает сообщение из предыдущей функции
    # В результате отправляет сообщение

    # Переменные для сокращения дальнейшего кода
    chat_id = message.chat.id

    # Пауза перед отправкой сообщения
    await asyncio.sleep(1)

    # Текст сообщения
    goodbye_text = 'На этом все, с вами приятно работать!\n\n' \
                   'P.S. Вы всегда можете обратиться за помощью...\n' \
                   '/stats'
    # Отправка сообщения
    await bot.send_message(chat_id=chat_id,
                           text=goodbye_text)

    # Пауза перед отправкой стикера
    await asyncio.sleep(1)

    # Id стикера
    goodbye_sticker = 'CAACAgIAAxkBAAEEIYNiLMwIbnpUPum9iwKCYimwDiqaQ' \
                      'wACmQYAAmMr4gm97kxaEFRiRyME'
    # Отправка стикера
    await bot.send_sticker(chat_id=chat_id,
                           sticker=goodbye_sticker)


# Хэндлер принимает любые сообщения, которые не прошли предыдущие
@dp.message_handler()
async def any_other_message(message: types.Message):
    # Функция отправляет пользователю сообщение о том, что ничего непонятно
    # На вход принимает сообщение от пользователя
    # В результате отправляет сообщение

    # Текст сообщения
    idk_text = 'К сожалению, я не понимаю, что вы от меня хотите\n\n' \
               'Чтобы получить информацию обо мне, нажмите /help'
    # Отправка сообщения
    await message.reply(text=idk_text)


# Запуск бота
executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
