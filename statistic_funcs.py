import string
import os
import pymorphy2
import requests
from bs4 import BeautifulSoup

# Определение преобразователя слов
morph = pymorphy2.MorphAnalyzer(lang='ru')

# Обновление пунктуации: в русскоязычной литературе используются еще и эти символы
punctuation = string.punctuation + '«»—'

"""
---------------Функции для получения данных из разных источников---------------
"""


def get_text_from_file(file_path):
    # Функция для получения данных из txt файла
    # На вход получает название файла (должен быть расположен в той же папке, что и код)
    # На выход возвращает либо текст, либо ошибку распознавания текста

    # Если получается открыть текст и считать из него данные
    try:
        # Открытие файла
        with open(file_path, 'r', encoding='utf-8') as text_file:  # открываем файл txt с текстом
            text = text_file.read()  # считываем из него содержание

        # Фиксирование, что нет ошибки
        error = False

        # Возвращение кортежа (данные об ошибке, строка с текстом)
        return error, text

    # Если возникает ошибка кодировки
    except UnicodeDecodeError:

        # Фиксирование ошибки
        error = True

        # Возвращение кортежа (данные об ошибке, пустая строка)
        return error, ''


def check_link(url):
    # Функция проверяет, подходит ли ссылка условиям для работы программы
    # На вход получает строку со ссылкой
    # В результате возвращает True (норм) или False (не подходит)

    # Проверка того, что ссылка ведет на подходящий сайт и на раздел в нем
    if ('ru.wikipedia' in url and len(url) > len('https://ru.wikipedia.org/wiki/')) \
            or \
            ('ilibrary' in url and 'text' in url):

        # Проверка возможности подключиться к странице
        if requests.get(url).status_code == 200:
            return True

    else:
        return False


def generate_soup(url):
    # Функция для создания soup для получения данных с сайтов
    # На вход получает ссылку на страницу
    # В результате возращает soup

    page = requests.get(url)
    page_text = page.text
    soup = BeautifulSoup(page_text, features='html.parser')

    return soup


def get_text_from_wiki(url):
    # Функция для получения данных с Википедии
    # На вход получает ссылку на страницу в Википедии
    # На выходе возвращает кортеж
    # (True/False, текст/0 - в зависимости от успеха подключения к странице)

    # Генерация soup
    wiki_soup = generate_soup(url)

    # Получение содержимого того, что находится под тегом p в body
    wiki_paragraphs = wiki_soup.find('body').find_all('p')

    # Создание пустого спискка для сохранения текста
    wiki_page_text = list()

    # Перебор параграфов, их очистка и добавление в список
    for paragraph in wiki_paragraphs:
        paragraph_text = str(paragraph.text).replace('\xa0', ' ')
        wiki_page_text.append(paragraph_text)

    # Слияние данных из списка в строку для получения текста
    whole_wiki_page_text = ''.join(wiki_page_text)

    # Возвращение текста со страницы
    return whole_wiki_page_text


def get_text_from_illibrary(url):
    # Функция для получения текста со страницы ilibrary.ru
    # На вход получает ссылку на страницу с этого сайта
    # На выходе возвращает soup

    # Генерация soup
    ili_soup = generate_soup(url)

    # Получение текста из всех p в body
    ili_parapraphs = ili_soup.find('body').find_all('span', class_='p')

    # Создание пустого списка для сохранения текста
    ili_text = list()

    # Перебор параграфов и их добавление в список
    for paragraph in ili_parapraphs:
        paragraph_text = paragraph.text
        ili_text.append(paragraph_text)

    # Преобразование списка в строку
    whole_ili_text = ''.join(ili_text)

    # Возвращение строки с текстом со страницы
    return whole_ili_text


"""
---------------------Функции для анализа полученного текста---------------------
"""


def clean_text(text):
    # Функция для очистки текста от того, что может помешать анализу
    # На вход получает строку с текстом
    # На выходе возвращает строку с очищенным текстом

    # Удаление переносов строк (деление на абзацы)
    half_clean_text = text.replace('\n', '')

    # Удаление дефисов, которые используются как тире
    half_clean_text = half_clean_text.replace(' - ', '')

    # Создание пустой строки для сохранения "чистого" текста
    fully_clean_text = ''

    # Удаление дефиса из строки с пунктуацией, чтобы не удалять их
    # из слов типа "как-то"
    cleaning_punctuation = punctuation.replace('-',
                                               '')

    # Перебор знаки из строки с полуочищенным текстом
    for letter in half_clean_text:

        # Если буква не совпадает со знаком пунктуации
        if letter not in cleaning_punctuation:
            # добавление буквы к строке с "чистым" текстом
            fully_clean_text += letter.lower()

    # Возврат строки с "чистым" текстом
    return fully_clean_text


def get_words_list(text):
    # Функция для преобразования строки чистого текста в список слов
    # На вход получает строку с очищенным текстом
    # На выходе возвращает список слов

    # Деление строки текста на список слов
    all_words_list = text.split()

    # Создание списка, в котором будут только слова из букв
    words_list = list()

    # Перебор слов из первого списка
    for word in all_words_list:

        # Если слово состоит только из букв
        if word.isalpha():
            # оно добавляется во второй список
            words_list.append(word)

    # Возврат списка слов, состоящих только из букв
    return words_list


def get_infinitives(words_list):
    # Функция для преобразования списка слов из текста
    # в список тех же слов, но в их начальной форме
    # На вход получает список слов
    # На выходе возвращает список тех же слов в начальной форме

    # Создание списка слов для хранения инфинитивов
    infinitives = list()

    # Перебор слов из входящего списка
    for curr_word in words_list:
        try:
            # Преобразование, нужное для причастий (иначе становятся глаголами)
            infinitive = morph.parse(curr_word)[0].inflect({'sing', 'nomn'}).word
        except AttributeError:
            # На случай ошибки, которая возникла однажды, грубое преобразование
            infinitive = morph.parse(curr_word)[0].normal_form

        # Добавление инфинитива в список инфинитивов
        infinitives.append(infinitive)

    # Вовзрат списка инфинитивов
    return infinitives


def get_unique_words(infinitives_list):
    # Функция возвращает список уникальных слов из заданного списка
    # из списках всех слов в начальной форме
    # На вход получает список слов в начальной форме
    # На выходе возвращает список уникальных слов

    # Преобразования списка слов во множество и затем снова в список
    unique_words = list(set(infinitives_list))

    # Возврат списка уникальных слов
    return unique_words


def sort_dict_by_value(dictionary_to_sort, reverse_mode=True):
    # Функция для сортировки словаря по значениям
    # На вход получает словарь для сортировки и параметр для reverse
    # На выходе возвращает отсортированный словарь

    # Создание пустого словаря для хранения сортированных данных
    sorted_dict = dict()

    # Сортировка ключей из входящего словаря по значениям в обратном порядке
    sorted_keys = sorted(dictionary_to_sort.keys(),
                         key=dictionary_to_sort.get,
                         reverse=reverse_mode)

    # Перебор ключей из отсортированного списка для добавления к ним значений
    # и сохранения их в отсортированный словарь
    for key in sorted_keys:
        sorted_dict[key] = dictionary_to_sort[key]

    # Возврат отсортированного по значениям словаря
    return sorted_dict


def get_general_stat_dict(infinitives_list, unique_words_list):
    # Функция для получения словаря с общей статистикой
    # На вход получает всех список инфитивов из текста и список уникальных слов
    # На выходе возвращает словарь
    # {str(слово): int(количество употреблений в тексте)}

    # Создание пустого словаря для хранения статистики
    general_stat = dict()

    # Перебор слов из списка уникальных слов
    for word in unique_words_list:
        # Добавление к ним значений
        general_stat[word] = infinitives_list.count(word)

    # Возврат словаря с общей статистикой
    return general_stat


def get_sensed_vocabulary_dict(general_stat_dictionary):
    # Функция для получения статистики слов, несущих смысл
    # На вход получает словарь с общей статистикой
    # В результате возвращает словарь с "осмысленной" статистикой

    # Создание пустого словаря для хранения данных
    sensed_vocabulary_dict = dict()

    # Определение списка частей речи, которые не несут смысл
    notsensed_POSes = ['CONJ', 'PREP', 'NPRO', 'ADJF', 'PRCL']

    # Перебор ключей из словаря с общей статистикой
    for curr_word in general_stat_dictionary.keys():

        # Определение части речи текущего слова
        curr_word_tag = morph.parse(curr_word)[0].tag.POS

        # Если эта часть речи не в списке бессмысленных
        if curr_word_tag not in notsensed_POSes:
            # добавление статистики в словарь
            sensed_vocabulary_dict[curr_word] = \
                general_stat_dictionary[curr_word]

    # Возвращение словаря со статистикой слов, несущих смысл
    return sensed_vocabulary_dict


"""
---------------------------Функции для вывода данных---------------------------
"""


def generate_result_text(result_dict, num_to_show):
    # Функция генерирует текст с результатами для отправки пользователю
    # На вход получает словарь с данными и количество значений для вывода
    # В результате возвращает строку с текстом

    # Создание списка ключей из полученного словаря
    keys = list(result_dict.keys())

    # Определение переменной, куда будет сохраняться итоговый текст
    result_text = ''

    # Проверка, что требуемое количество не превышает имеющиеся данные
    if num_to_show > len(keys):
        num_to_show = len(keys)

    # Проверка, что требуемое количество точно поместится в одно сообщение
    if num_to_show > 5:
        num_to_show = 5

    # Перебор нужного количества ключей из списка
    for key in keys[:num_to_show]:

        # Определение формы слова "раз" для красивого и грамотного текста
        if 4 >= result_dict[key] % 10 >= 2:
            times = 'раза'
        else:
            times = 'раз'

        # Прибавление строки к общему тексту
        result_text += f'Слово "{key}" встречается {result_dict[key]} {times}\n'

    # Возрат итогового текста
    return result_text


def generate_filename(user_filename, adding):
    # Функция для генерации названия файла
    # На вход получает пользовательское название файла
    # и прибавление от программы
    # На выходе возвращает отформатированное название в формате .csv

    # Создание пустой строки с итоговым названием файла
    filename = ''

    # Исключение последних пробелов или точек из пользовательского названия
    while filename.endswith('.') or filename.endswith(' '):
        filename = filename[:-1]

    # Перебор букв в пользовательском названии без последних пробелов и точек
    for letter in user_filename:
        # Замена пробелов на нижние подчеркивания
        if letter == ' ':
            filename += '_'
        # Удаление непозволительных знаков
        elif letter in ['?', '!', '<', '>', '*', '""', '@', '/', '\\', '|']:
            filename += ''
        # Замена двоеточия на "- "
        elif letter == ':':
            filename += '- '
        else:
            filename += letter.lower()

    # Прибавление к названию добавки и формата
    filename += adding + '.csv'

    # Возврат отформатированного названия
    return filename


def write_to_file(line_to_write, filename):
    # Функция записывает данные из словаря в файл
    # На вход получает данные для записи и название (путь) к файлу
    # В результате записывает данные в файл и возвращает путь к нему

    # Генерация полного пути к файлу
    path = os.path.join(os.path.abspath('results'), filename)

    # Запись данных в файл
    with open(path, 'w') as doc:
        print(line_to_write, file=doc)

    # Возврат пути
    return path


def generate_line(dictionary_to_write):
    # Функция генерирует текст для записи в файл
    # На вход получает словарь, данные которого нужно записать
    # В результате возвращает строку с текстом для записи в csv

    # Создание пустой строки для записи туда текста
    line_to_write = ''

    # Перебор ключей полученного словаря
    for key in dictionary_to_write.keys():
        # Прибавление отформатированных данных ключ-значение к тексту
        line_to_write += key + ';' + str(dictionary_to_write[key]) + '\n'

    # Исключение последнего переноса строки
    line_to_write = line_to_write[:-1]

    # Возврат строки текста, готового для записи
    return line_to_write
