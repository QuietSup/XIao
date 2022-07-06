import glob
import os
import random
import shutil
import sqlite3
from datetime import datetime
from os.path import exists

import matplotlib.dates as mdates
from PIL import Image
from flask import Flask, render_template, request
from matplotlib import pyplot as plt, ticker
from py7zr import unpack_7zarchive
import pandas as pd
import numpy as np
from windrose import WindroseAxes

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
    # print(city)
    sqlite_connection = sqlite3.connect('meteodata.db')
    cursor = sqlite_connection.cursor()
    # print('**************************' + city)

    cursor.execute('SELECT id FROM cities WHERE city=?', (city,))
    sqlite_connection.commit()
    city_id = cursor.fetchone()[0]

    # print(city)
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



@app.route('/<city>/temperature')
def temperature(city):
    img_path = f'static/img/{city}/temperature.png'
    if exists('/' + img_path):
        os.remove('/' + img_path)
    sqlite_connection = sqlite3.connect('meteodata.db')
    cursor = sqlite_connection.cursor()

    cursor.execute('SELECT id FROM cities WHERE city=?', (city,))
    sqlite_connection.commit()
    city_id = cursor.fetchone()[0]

    insert = "SELECT time FROM meteo " \
             "WHERE city=? " \
             # "limit 100"
    cursor.execute(insert, (city_id,))
    sqlite_connection.commit()
    time = cursor.fetchall()
    for i in range(len(time)):
        time[i] = time[i][0]
    x = pd.Series(time)
    x = x.interpolate().tolist()
    for i in range(len(x)):
        x[i] = datetime.strptime(x[i], '%Y-%m-%d-%H-%M')
    # x = matplotlib.dates.date2num(x)
    x = sorted(x)
    # print(x)

    insert = "SELECT temperature FROM meteo " \
             "WHERE city=? " \
             # "limit 100"
    cursor.execute(insert, (city_id,))
    sqlite_connection.commit()
    temperature = cursor.fetchall()
    for i in range(len(temperature)):
        temperature[i] = temperature[i][0]
    y = pd.Series(temperature)
    y = y.interpolate().tolist()
    # print(y)

    plt.plot(x, y, color='green')

    # naming the x axis
    plt.xlabel('Час', fontsize=18)
    # naming the y axis
    plt.ylabel('Температура', fontsize=18)

    # giving a title to my graph
    plt.title('Температурні умови регіону', fontsize=20)
    fig = plt.gcf()
    fig.set_size_inches(18.5, 10.5)
    # plt.xticks(rotation=-20)
    ax = plt.gca()
    from matplotlib.dates import MO, TU, WE, TH, FR, SA, SU
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    ax.xaxis.set_minor_locator(mdates.WeekdayLocator(byweekday=MO, interval=1))
    ax.yaxis.set_major_locator(ticker.MultipleLocator(5))

    plt.margins(x=0)
    plt.grid()
    ax.xaxis.grid(which='minor', linewidth=0.5)
    ax.xaxis.grid(which='major', linewidth=1, color='orange')

    plt.figtext(.75, .89, "жовтий --> Понеділок", fontsize=16, style='italic')


    sqlite_connection.close()
    plt.savefig(img_path, bbox_inches='tight')
    plt.close()
    return render_template('stat.html', plt=plt, city=city, img_path='../'+img_path)


@app.route('/<city>/windrose')
def windrose(city):
    img_path = f'static/img/{city}/windrose.png'
    if exists('/' + img_path):
        os.remove('/' + img_path)
    sqlite_connection = sqlite3.connect('meteodata.db')
    cursor = sqlite_connection.cursor()

    cursor.execute('SELECT id FROM cities WHERE city=?', (city,))
    sqlite_connection.commit()
    city_id = cursor.fetchone()[0]

    insert = "SELECT wind_direction FROM meteo " \
             "WHERE city=? " \
             # "limit 100"
    cursor.execute(insert, (city_id,))
    sqlite_connection.commit()
    wind_direction = cursor.fetchall()
    for i in range(len(wind_direction)):
        wind_direction[i] = wind_direction[i][0]
    wind_direction = pd.Series(wind_direction)
    wind_direction = wind_direction.interpolate().tolist()
    wind_direction = [int(x) for x in wind_direction]
    i = 1
    wdir = {}
    d = 0
    while i <= 9 and d <= 360:
        wdir[i] = d
        i += 1
        d += 45
    print(wdir)
    for i in range(len(wind_direction)):
        if i == 9:
            wind_direction[i] = random.randint(1, 360)
        else:
            wind_direction[i] = wdir[wind_direction[i]]



    insert = "SELECT wind_speed FROM meteo " \
             "WHERE city=? " \
             # "limit 100"
    cursor.execute(insert, (city_id,))
    sqlite_connection.commit()
    wind_speed = cursor.fetchall()
    for i in range(len(wind_speed)):
        wind_speed[i] = wind_speed[i][0]
    wind_speed = pd.Series(wind_speed)
    wind_speed = wind_speed.interpolate().tolist()
    wind_speed = [int(x) for x in wind_speed]

    ax = WindroseAxes.from_ax()
    print(wind_direction[:30])
    ax.bar(wind_direction, wind_speed, edgecolor='k')
    ax.set_xticklabels(['Пн', 'Пн-Сх',  'Сх', 'Пд-Сх', 'Пд', 'Пд-Зх', 'Зх', 'Пн-ЗХ'])
    ax.set_theta_zero_location('N')
    ax.legend()
    plt.title('Троянда вітрів', fontsize=20)


    plt.savefig(img_path)
    plt.close()
    # plt.table(cellText=)

    sqlite_connection.close()
    return render_template('stat.html', city=city, img_path='../'+img_path)


@app.route('/<city>/temperature-time')
def temperature_time(city):
    img_path = f'static/img/{city}/temperature-time.png'
    if exists('/' + img_path):
        os.remove('/' + img_path)
    sqlite_connection = sqlite3.connect('meteodata.db')
    cursor = sqlite_connection.cursor()

    cursor.execute('SELECT id FROM cities WHERE city=?', (city,))
    sqlite_connection.commit()
    city_id = cursor.fetchone()[0]

    insert = "SELECT temperature FROM meteo " \
             "WHERE city=? " \
             # "limit 100"
    cursor.execute(insert, (city_id,))
    sqlite_connection.commit()
    temperature = cursor.fetchall()
    for i in range(len(temperature)):
        temperature[i] = temperature[i][0]
    t = pd.Series(temperature)
    t = t.interpolate().tolist()
    # print(y)

    # x = range(min(t), max(t))
    # y = []
    # for value in x:
    #     y.append(t.count(value) * 0.5)
    # plt.hist(t, color='green')
    n, bins, patches = plt.hist(t, bins=int(max(t)-min(t)), facecolor='#2ab0ff', edgecolor='#e0e0e0', linewidth=0.5, alpha=0.7)

    n = n.astype('int')  # it MUST be integer
    # Good old loop. Choose colormap of your taste
    for i in range(len(patches)):
        patches[i].set_facecolor(plt.cm.jet(n[i] / max(n)))
    # Make one bin stand out
    # patches[47].set_fc('red')  # Set color
    # patches[47].set_alpha(1)  # Set opacity
    # Add annotation
    # plt.annotate('Important Bar!', xy=(0.57, 175), xytext=(2, 130), fontsize=15,
    #              arrowprops={'width': 0.4, 'headwidth': 7, 'color': '#333333'})


    #
    #
    #
    ax = plt.gca()
    ax.xaxis.set_major_locator(ticker.MultipleLocator(2))
    ax.xaxis.set_minor_locator(ticker.MultipleLocator(1))
    ax.yaxis.set_major_locator(ticker.MultipleLocator(50))
    ax.yaxis.set_minor_locator(ticker.MultipleLocator(25))
    fig = plt.gcf()
    fig.set_size_inches(27, 10.5)
    plt.xlabel('Т, °С', fontsize=18)
    plt.ylabel('t, 30хв', fontsize=18)
    # plt.xticks(rotation=-80)
    # plt.grid()
    ax.yaxis.grid(True, linewidth=1.5)
    ax.yaxis.grid(which='minor', linewidth=0.5)
    # plt.grid(which='minor')
    plt.margins(0)
    plt.title('Тривалість температурних режимів', fontsize=20)









    sqlite_connection.close()
    plt.savefig(img_path, bbox_inches='tight')
    plt.close()
    return render_template('stat.html', plt=plt, city=city, img_path='../'+img_path)


@app.route('/<city>/report', methods=['GET', 'POST'])
def report(city):
    from fpdf import FPDF
    report = city + '-звіт.pdf'
    if exists(report):
        os.remove(report)
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    cwd = os.getcwd()
    imagelist = glob.glob(f'{cwd}\\static\\img\\{city}\\*')
    print(imagelist)
    # imagelist is the list with all image filenames
    # for image in imagelist:
    #     pdf.add_page()
    #     pdf.image(image, 0, 0, 280, 210)
    for imageFile in imagelist:
        cover = Image.open(imageFile)
        width, height = cover.size

        # convert pixel in mm with 1px=0.264583 mm
        width, height = float(width * 0.264583), float(height * 0.264583)

        # given we are working with A4 format size
        pdf_size = {'P': {'w': 210, 'h': 297}, 'L': {'w': 297, 'h': 210}}

        # get page orientation from image size
        orientation = 'P' if width < height else 'L'

        #  make sure image size is not greater than the pdf format size
        width = width if width < pdf_size[orientation]['w'] else pdf_size[orientation]['w']
        height = height if height < pdf_size[orientation]['h'] else pdf_size[orientation]['h']

        pdf.add_page(orientation=orientation)

        pdf.image(imageFile, 0, 0, width, height)



    pdf.output(report, "F")
    return "NICEEE"





if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=80)
