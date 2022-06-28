import datetime
import glob
import os
import sqlite3

import lagrange as lagrange
import openpyxl
from re import sub
from googletrans import Translator
from pandas.io.excel._openpyxl import OpenpyxlReader


class City:
    def __init__(self, file_name):
        self.__name = file_name
        self.__file_name = file_name
        self.__list_of_files = glob.glob(f'{file_name}\\*')
        self.data = []
        self.header = []
        city_name = os.path.basename(self.file_name)
        self.city_name = sub("([a-zA-Zа-яА-ЯёЁіІїЇєЄ']+).*", "\\1", city_name).capitalize()
        self.progress_max = 0
        self.progress_now = 0

    def open_openpyxl(self, **kw):
        for path in self.list_of_files:
            filename = os.path.basename(path)
            year = sub(".*(\\d{4}).*", "\\1", filename)
            month = sub(".*\\D(\\d{1,2}).*", "\\1", filename)
            default_kw = {'read_only': True, 'data_only': True, 'keep_links': False}
            for k, v in default_kw.items():
                if k not in kw:
                    kw[k] = v
            wb = openpyxl.load_workbook(path, **kw)
            sheet = wb.worksheets[0]
            convert_cell = OpenpyxlReader(path)._convert_cell
            data = []
            for row in sheet.rows:
                data.append([convert_cell(cell, False) for cell in row])

            self.header = data[0]
            data.pop(0)
            self.progress_max += len(data)
            newdata = []
            for row in data:
                time = row[self.header.index('UTC')]
                hours = sub("(\\d{1,2}).*", "\\1", f'{time}')
                minutes = sub(".*\\D(\\d{2})\\D.*", "\\1", f'{time}')
                print(minutes)
                newdata.append({
                    'time': f'{year}-{month}-{int(row[self.header.index("Число месяца")])}-{hours}-{minutes}',
                    'temperature': f'{row[self.header.index("T")]}',
                    'wind_direction': f'{row[self.header.index("dd")]}',
                    'wind_speed': f'{row[self.header.index("FF")]}',
                    'cloud_num': f'{row[self.header.index("N")]}',
                    'visibility': f'{row[self.header.index("vv")]}',
                    'pressure': f'{row[self.header.index("PPP")]}',
                    'bottom_line': f'{row[self.header.index("hhh")]}',
                    'weather': f'{row[self.header.index("ww")]}'
                })

            self.data.append(newdata)

    def importdata(self):
        winds = {'Северный': 1,
                 'С-В': 2,
                 'Восточный': 3,
                 'Ю-В': 4,
                 'Южный': 5,
                 'Ю-З': 6,
                 'Западный': 7,
                 'С-З': 8,
                 'Переменный': 9}

        weathercode = {
            'CL': 1,
            'BR': 2,
            'FG': 3,
            'RA': 4,
            'SHRA': 5,
            'SNRA': 6,
            'SN': 7,
            'SHSN': 8,
            'TS': 9,
            'DZ': 10,
            'FZ': 11,
            'HL': 12
        }

        try:
            sqlite_connection = sqlite3.connect('C:\\Users\\38098\PycharmProjects\\flaskProject\\meteodata.db')
            cursor = sqlite_connection.cursor()

            cursor.execute("SELECT * FROM cities WHERE city=?", [self.city_name])
            sqlite_connection.commit()
            if not cursor.fetchone():
                cursor.execute("INSERT INTO cities (city) VALUES (?)", [self.city_name])
                sqlite_connection.commit()

            cursor.execute("SELECT id FROM cities WHERE city=?", [self.city_name])
            sqlite_connection.commit()
            city_id = cursor.fetchone()[0]




            insert1 = "INSERT INTO meteo " \
                      "(city, time, temperature, wind_direction, wind_speed, cloud_num, " \
                      "visibility, pressure, bottom_line) " \
                      "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);"

            for one in self.data:
                for row in one:
                    time = None if row.get('time') == '' else row.get('time')
                    temperature = None if row.get('temperature') == '' else int(float(row.get('temperature')))
                    wind_direction = None if row.get('wind_direction') == '' else winds[row.get('wind_direction')]
                    wind_speed = None if row.get('wind_speed') == '' else int(float(row.get('wind_speed')))
                    cloud_num = None if row.get('cloud_num') == '' else int(float(row.get('cloud_num')))
                    visibility = None if row.get('visibility') == '' else row.get('visibility')
                    pressure = None if row.get('pressure') == '' else int(float(row.get('pressure')))
                    bottom_line = None if row.get('bottom_line') == '' else int(float(row.get('bottom_line')))
                    values1 = [city_id,
                               time,
                               temperature,
                               wind_direction,
                               wind_speed,
                               cloud_num,
                               visibility,
                               pressure,
                               bottom_line]
                    cursor.execute(insert1, values1)
                    sqlite_connection.commit()
                    ww = row.get('weather').split('+')

                    insert3 = "SELECT id FROM meteo WHERE city=? AND time=?;"
                    cursor.execute(insert3, [city_id, row["time"]])
                    sqlite_connection.commit()
                    meteo = cursor.fetchone()[0]
                    for each in ww:
                        if each != '':
                            insert2 = "INSERT INTO meteo_weather (meteo, weather) VALUES (?, ?);"
                            values2 = [meteo, weathercode.get(each)]
                            cursor.execute(insert2, values2)
                            sqlite_connection.commit()
                    self.progress_now += 1
                    print(f'{self.progress_now} / {self.progress_max}')

        except sqlite3.Error as error:
            print("Ошибка при работе с SQLite\n", error)

        # finally:
            # if sqlite_connection:
            #     sqlite_connection.close()
            #     print("Соединение с SQLite закрыто")

    @property
    def name(self):
        return self.__name

    @property
    def file_name(self):
        return self.__file_name

    @property
    def list_of_files(self):
        return self.__list_of_files

    @name.setter
    def name(self, value):
        self.__name = value

    @file_name.setter
    def file_name(self, value):
        self.__file_name = value

    @list_of_files.setter
    def list_of_files(self, value):
        self.__list_of_files = value


def translate(word):
    # specify source language
    translator = Translator()
    translation = translator.translate(word, src="ru", dest='uk')
    return translation.text


# connection = sqlite3.connect('meteodata.db')
# cursor = connection.cursor()
# query = "SELECT * from meteo"
# cursor.execute(query)
# results = cursor.fetchall()
#
# time_range = datetime.timedelta(hours=0, minutes=30)
# last = datetime.datetime(2000, 1, 1, 1, 1)
# missing = []
# for row in results:
#     date_and_time = row[2].split('-')
#     current = datetime.datetime(int(date_and_time[0]), int(date_and_time[1]), int(date_and_time[2]),
#                                 int(date_and_time[3]), int(date_and_time[4]))
#     if not (current - last) == time_range:
#         missing.append(row[0])
#     last = current
# print(missing)
# for index in missing:
#     query = f"SELECT * from meteo WHERE id = {index} OR id = {index - 1} OR id = {index + 1}"
#     cursor.execute(query)
#     results = cursor.fetchall()
#     missing_dates = []
#     for row in results:
#         date_and_time = row[2].split('-')
#         current = datetime.datetime(int(date_and_time[0]), int(date_and_time[1]), int(date_and_time[2]),
#                                 int(date_and_time[3]), int(date_and_time[4]))
#         missing_dates.append(current)
#     if not missing_dates[1] - missing_dates[0] == time_range:
#         # while missing_dates[1] >= missing_dates[0]:
#         #     missing_dates
#         print("first")
#     else:
#         print("second")
# connection.close()
