from flask import Flask, render_template, request, redirect
from flask_cors import CORS
from flask_mysqldb import MySQL
import numpy as np
import pandas as pd
import requests
import pickle

crop_recommendation_model_path = 'model/RandomForest.pkl'
crop_recommendation_model = pickle.load(
    open(crop_recommendation_model_path, 'rb'))


def rainfall_fetch(city):
    rainfallData = {
        'kabale': 60,
        'entebbe': 150,
        'gulu': 5,
        'lira': 5,
        'mbarara': 60,
        'bushenyi': 100,
        'masindi': 2,
        'jinja': 150,
        'serere': 60,
        'soroti': 50,
        'mubende': 30,
        'kampala': 60,
        'arua': 0,
        'tororo': 70,
        'kotido': 2,
        'kasese': 80,
        'kitgum': 19
    }
    return rainfallData[city]


def weather_fetch(city_name):
    """
    Fetch and returns the temperature and humidity of a city
    :params: city_name
    :return: temperature, humidity
    """
    api_key = "abfb8146fd98ef50e173ea3093df08d5"
    total_temperature = 0
    total_humidity = 0
    average_temperature = 0
    average_humidity = 0
    base_url = "https://pro.openweathermap.org/data/2.5/forecast/climate?"

    complete_url = base_url + "q=" + city_name + "&appid=" + api_key
    x = ""
    try:
        response = requests.get(complete_url)
        x = response.json()
        if x["code"] != "404":
            for i in x['list']:
                total_temperature += (i['temp']['max'])

            for h in x['list']:
                total_humidity += h['humidity']

            average_temperature = total_temperature / 30
            average_humidity = total_humidity / 30

            temperature = round((average_temperature - 273.15), 2)
            humidity = average_humidity
            return temperature, humidity
        else:
            return None
    except Exception as e:
        print("An error occured:")
        print(e)
        return None

app = Flask(__name__)
CORS(app)
app.jinja_env.add_extension('jinja2.ext.loopcontrols')
app.config.from_object(__name__)

# Db Config
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'nicholas'
app.config['MYSQL_PASSWORD'] = 'Dicky1000@'
app.config['MYSQL_DB'] = 'idealcrop'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)


############### Utilities ###############

# Function to fetch data from the db
def db_query(query):
    try:
        cursor = mysql.connection.cursor()
        cursor.execute(query)
        result = cursor.fetchall()
        cursor.close()
        return result
    except Exception as e:
        print("An error occured:")
        print(e)
        return {'db_error': True}


# Function to check if db result set is empty or has errors
def check_result(result_set, subject):
    if len(result_set) == 0:
        return "No " + subject + " found"
    elif len(result_set) == 1 and result_set['db_error']:
        return "Error"
    else:
        return "True"


# Recommendation Routes

# Normal Routes
@app.route('/')
def index():
    title = "IdealCrop"
    return redirect("/crop-recommend")


@app.route('/crop-recommend')
def crop_recommend():
    # Route info
    title = "Recommend Crop"
    activeTab = "crop_recommend"
    return render_template('crop-recommend.html', title=title, activeTab=activeTab)


@app.route('/crop-predict', methods=['POST'])
def crop_prediction():
    # Route info
    title = "Crop Prediction"
    activeTab = "crop_recommend"
    
    if request.method == 'POST':
        try:
            N = int(request.form['nitrogen'])
            P = int(request.form['phosphorus'])
            K = int(request.form['potassium'])
            ph = float(request.form['ph'])
            rainfall = rainfall_fetch(request.form.get('district'))
            city = request.form.get('district')

            if weather_fetch(city) is not None:
                temperature, humidity = weather_fetch(city)
                data = np.array([[N, P, K, temperature, humidity, ph, rainfall]])
                my_prediction = crop_recommendation_model.predict(data)
                final_prediction = my_prediction[0]
                return render_template('crop-recommend.html', title=title, activeTab=activeTab, prediction=final_prediction, N=N, P=P, K=K, ph=ph, city=city)
            else:
                error = "There was an error completing your request, please try again later."
                return render_template('crop-recommend.html', title=title, activeTab=activeTab, predictionError=error)
        except:
            error = "Please submit the correct input!"
            return render_template('crop-recommend.html', title=title, activeTab=activeTab, predictionError=error)


@app.route('/npk-recommend')
def npk_recommend():
    # Route info
    title = "Recommend NPK"
    activeTab = "npk_recommend"
    return render_template('npk-recommend.html', title=title, activeTab=activeTab)


@app.route('/npk-predict', methods=['POST'])
def npk_predict():
    # Route info
    title = "Recommend NPK"
    activeTab = "npk_recommend"
    try:
        crop_name = str(request.form['cropname'])
        df = pd.read_csv('data/fertilizer.csv')
        N = df[df['Crop'] == crop_name]['N'].iloc[0]
        P = df[df['Crop'] == crop_name]['P'].iloc[0]
        K = df[df['Crop'] == crop_name]['K'].iloc[0]
        pH = df[df['Crop'] == crop_name]['pH'].iloc[0]

        return render_template('npk-recommend.html', title=title, activeTab=activeTab, crop_name=crop_name, N=N, P=P, K=K, pH=pH)
    except:
        error = "Please submit the correct input!"
        return render_template('npk-recommend.html', title=title, activeTab=activeTab, error=error)

@app.route('/crop-varieties')
def crop_varieties():
    # Getting crops with varieties
    query = "SELECT DISTINCT(variety.species), species.crop, crop.id, crop.crop_name, crop.image FROM variety "
    query += "LEFT JOIN species ON variety.species = species.id "
    query += "LEFT JOIN crop ON species.crop = crop.id;"

    crops = db_query(query)

    # Route info
    title = "Crop Varieties"
    activeTab = "varieties"
    return render_template('crop-varieties.html', title=title, activeTab=activeTab, crops=crops)


@app.route('/crop-varieties/<int:id>')
def show_varieties(id):
    # Getting varities for selected crop
    query = "SELECT variety.variety_name, variety.maturity_duration, variety.yield, variety.special_attributes, crop.crop_name FROM variety "
    query += "LEFT JOIN species ON variety.species = species.id "
    query += "LEFT JOIN crop ON species.crop = crop.id WHERE species.crop = '" + str(id) + "'"

    varieties = db_query(query)

    # Check for errors or empty result set before determining crop name
    if check_result(varieties, 'varieties') == "True":
        cropName = varieties[0]['crop_name'].capitalize()
    else:
        cropName = check_result(varieties, 'varieties')

    # Route info
    title = "Crop Varieties"
    activeTab = "varieties"

    return render_template('crop-varieties-list.html', title=title, activeTab=activeTab, varieties=varieties,
                           cropName=cropName)


@app.route('/practices')
def ideal_practices():
    # Getting crops with varieties
    query = "SELECT DISTINCT(crop_practice.crop), crop.id, crop.crop_name, crop.image FROM crop_practice "
    query += "LEFT JOIN crop ON crop_practice.crop = crop.id;"

    crops = db_query(query)

    # Route info
    title = "Cultivation Practices"
    activeTab = "practices"
    return render_template('practices.html', title=title, activeTab=activeTab, crops=crops)


@app.route('/practices/<int:id>')
def show_practices(id):
    # Getting varities for selected crop
    query = "SELECT crop_practice.id, stage.stage_name, stage.stage_description, practice.practice_name, crop_practice.practice_description, crop.crop_name "
    query += "FROM crop_practice LEFT JOIN practice ON crop_practice.practice = practice.id "
    query += "LEFT JOIN stage ON crop_practice.stage = stage.id LEFT JOIN crop ON crop_practice.crop = crop.id "
    query += "WHERE crop_practice.crop = '" + str(id) + "'"

    practices = db_query(query)

    # Check for errors or empty result set determing crop name
    if check_result(practices, 'practices') == "True":
        cropName = practices[0]['crop_name'].capitalize()
    else:
        cropName = check_result(practices, 'practices')

    # Route info
    title = "Cultivation Practices"
    activeTab = "practices"
    return render_template('practices-list.html', title=title, activeTab=activeTab, practices=practices,
                           cropName=cropName)


@app.route('/zoning')
def crop_zoning():
    # Route info
    title = "Crop Zoning"
    activeTab = "zoning"

    # Get crops and regions to display
    queryZone = "SELECT crop_zone.crop, crop_zone.region, crop.crop_name, region.region_name FROM crop_zone "
    queryZone += "LEFT JOIN crop ON crop_zone.crop = crop.id LEFT JOIN region ON crop_zone.region = region.id"
    crop_zone = db_query(queryZone)

    # Check for errors or empty result set
    crops = {}
    regions = {}
    if check_result(crop_zone, 'crop zones') == "True":

        # Populate regions and crops list 
        for row in crop_zone:
            if row['region_name'] in regions:
                continue
            else:
                regions.update({row['region']: row['region_name']})

            if row['crop_name'] in crops:
                continue
            else:
                crops.update({row['crop']: row['crop_name']})

    return render_template('zoning.html', title=title, activeTab=activeTab, crops=crops, regions=regions)


@app.route('/zoning-details', methods=['POST'])
def crop_zone_details():
    # Route info
    title = "Crop Zoning"
    activeTab = "zoning"

    # Handle submissions
    if request.method == 'POST':
        regionId = ""
        cropId = ""
        zone_for = ""
        name = ""

        # Begin query for zoning
        queryZone = "SELECT crop_zone.region, region.region_name, crop.crop_name, crop_zone.crop_extras, crop_zone.yield FROM crop_zone "
        queryZone += "LEFT JOIN region ON crop_zone.region = region.id "
        queryZone += "LEFT JOIN crop ON crop_zone.crop = crop.id "

        # Differentiate crop and region
        if request.form.get('regionSelect') != None:
            regionId = request.form.get('regionSelect')
            queryZone += "WHERE crop_zone.region = '" + str(regionId) + "' ORDER BY crop_zone.yield DESC"
            zone_for = "Crops"
        if request.form.get('cropSelect') != None:
            cropId = request.form.get('cropSelect')
            queryZone += "WHERE crop_zone.crop = '" + str(cropId) + "' ORDER BY crop_zone.yield DESC"
            zone_for = "Regions"

        zone_result = db_query(queryZone)

        # Check for errors or empty result set determing crop name
        if check_result(zone_result, 'crop zone') == "True":
            if zone_for == "Crops":
                name = zone_result[0]['region_name']
            elif zone_for == "Regions":
                name = zone_result[0]['crop_name'].capitalize()
        else:
            name = check_result(zone_result, 'crop zone')

        return render_template('zoning-list.html', title=title, activeTab=activeTab, zone_result=zone_result, name=name,
                               zone_for=zone_for)


@app.route('/show-districts/<int:id>')
def show_districts(id):
    # Route info
    title = 'Region Districts'

    # Get districts
    queryDistrict = "SELECT district.district_name, region.region_name, region.id FROM district "
    queryDistrict += "LEFT JOIN region ON district.region = region.id WHERE district.region = '" + str(id) + "'"

    districts = db_query(queryDistrict)

    if check_result(districts, 'districts') == "True":
        regionName = districts[0]['region_name']
    else:
        regionName = check_result(districts, 'districts')

    return render_template('show-districts.html', title=title, districts=districts, regionName=regionName)


# Error Routes

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html")


@app.errorhandler(405)
def method_not_allowed(e):
    return render_template("405.html")


if __name__ == "__main__":
    app.run(debug=True)
