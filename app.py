import glob
import os
import shutil
import sqlite3

from flask import Flask, render_template, request
from py7zr import unpack_7zarchive
import pandas as pd
import numpy as np

from city import City

app = Flask(__name__)


@app.route('/')
def choose_city():  # put application's code here
    sqlite_connection = sqlite3.connect('meteodata.db')
    cursor = sqlite_connection.cursor()
    insert = "SELECT city FROM cities"
    cursor.execute(insert)
    sqlite_connection.commit()
    cities = cursor.fetchall()
    print(cities)
    sqlite_connection.close()
    return render_template('index.html', cities=cities)


@app.route('/<city>')
def city_table(city):  # put application's code here
    sqlite_connection = sqlite3.connect('meteodata.db')
    cursor = sqlite_connection.cursor()

    cursor.execute('SELECT id FROM cities WHERE city=?', (city,))
    sqlite_connection.commit()
    city_id = cursor.fetchone()[0]

    print(city)
    insert = "SELECT * FROM meteo " \
             "INNER JOIN wind ON wind.id = meteo.wind_direction " \
             "WHERE city=? " \
             "limit 100"
    cursor.execute(insert, (city_id,))
    sqlite_connection.commit()
    data = cursor.fetchall()
    # print(cities)
    sqlite_connection.close()
    return render_template('city.html', data=data, city=city)


@app.route('/add')
def add():  # put application's code here
    return render_template('add.html', )


@app.route('/upload', methods=['GET', 'POST'])
def upload():  # put application's code here
    uploaded_file = request.files['file']
    if uploaded_file.filename != '':
        uploaded_file.save(uploaded_file.filename)
        print(uploaded_file)
    cwd = os.getcwd()
    try:
        shutil.register_unpack_format('7zip', ['.7z'], unpack_7zarchive)
        shutil.unpack_archive(uploaded_file.filename, f'{cwd}\\unpacked')
    except:  # if file exists
        return 'Error'

    list_of_files = glob.glob(f'{cwd}\\unpacked\\*')
    # if list_of_files:
    latest_file = max(list_of_files, key=os.path.getctime)
    print('latest_file=', latest_file)
    city = City(latest_file)
    print(city.open_openpyxl())
    city.importdata()
    print(f'{city.progress_now} / {city.progress_max}')
    return 'Success'


@app.route('/<city>/interpolate')
def intarpolated(city):  # put application's code here
    sqlite_connection = sqlite3.connect('meteodata.db')
    cursor = sqlite_connection.cursor()

    cursor.execute('SELECT id FROM cities WHERE city=?', (city,))
    sqlite_connection.commit()
    city_id = cursor.fetchone()[0]

    print(city)
    insert = "SELECT * FROM meteo " \
             "INNER JOIN wind ON wind.id = meteo.wind_direction " \
             "WHERE city=? " \
             "limit 100"
    cursor.execute(insert, (city_id,))
    sqlite_connection.commit()
    data = cursor.fetchall()

    insert = "SELECT cloud_num FROM meteo " \
             "INNER JOIN wind ON wind.id = meteo.wind_direction " \
             "WHERE city=? " \
             "limit 100"
    cursor.execute(insert, (city_id,))
    sqlite_connection.commit()
    cloud_num = cursor.fetchall()
    for x in range(len(cloud_num)):
        cloud_num[x] = cloud_num[x][0]
    a = pd.Series(cloud_num)
    a = a.interpolate().tolist()
    for i in range(len(data)):
        data[i] = list(data[i])
        data[i][6] = round(a[i], 2)



    insert = "SELECT bottom_line FROM meteo " \
             "INNER JOIN wind ON wind.id = meteo.wind_direction " \
             "WHERE city=? " \
             "limit 100"
    cursor.execute(insert, (city_id,))
    sqlite_connection.commit()
    bottom_line = cursor.fetchall()
    for x in range(len(bottom_line)):
        bottom_line[x] = bottom_line[x][0]
    a = pd.Series(bottom_line)
    a = a.interpolate().tolist()
    for i in range(len(data)):
        data[i][9] = round(a[i], 2)


    sqlite_connection.close()
    return render_template('city.html', data=data, city=city)












if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=80)
