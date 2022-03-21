import math
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from _datetime import datetime
from requests import post

"""
Whakatāne bar forecasting algorithm v2
15th March 2022
"""
scope = ['https://spreadsheets.google.com/feeds']
creds = ServiceAccountCredentials.from_json_keyfile_name('sheetsAPI.json', scope)
client = gspread.authorize(creds)
sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1orTLfEY34Vl2Rn_ijwYCZ8b44dx2Adhutom7_bYKWg4/edit#gid=0")

worksheet = sheet.add_worksheet(title=datetime.now().strftime("%d/%m/%Y %H:%M"), rows=50, cols=5)
tides = open("Whakatāne 2022.csv", "r")
bar = open("BarForecast.csv", "w")
weather = open(datetime.now().strftime("%d%m%Y%H%M") + ".csv", "w")

# Listing tides for the year. Format of date, tide 1 time, tide 1 height, tide 2 time etc.
tidelist = []
for line in tides:
    line = line.split(",")
    line[0] = datetime.date(datetime.strptime(line[0], "%d/%m/%Y"))
    line[-1] = line[-1].rstrip("\n")
    tidelist.append(line)

resp = post('https://forecast-v2.metoceanapi.com/point/time',
            headers={'x-api-key': '3bWnxNuWTo8WfQnjpu7Dk1'},
            json={
                "points": [{
                    "lon": 177.0095,
                    "lat": -37.9391
                }],
                "variables": [
                    "wind.speed.at-10m",
                    "wind.direction.at-10m",
                    "wave.height",
                    "wave.period.peak",
                    "wave.height.above-8s",
                    "air.visibility",
                    "wave.direction.mean",
                    "wave.direction.above-8s.peak"
                ],
                "time": {
                    "from": "{:%Y-%m-%dT00:00:00Z}".format(datetime.now()),
                    "interval": "3h",
                    "repeat": 56 #28 for every 6 hours - skip i % 4 == 0
                }
            }
            )

def BarForecast(tidelist, resp):
    j = 0
    for i in range(56):
        if i % 8 == 0:
            j+=1
            continue
        elif i % 8 == 1 or i % 8 == 7:
            continue

        date = datetime.date(datetime.strptime(resp.json()['dimensions']['time']['data'][i][:10], "%Y-%m-%d"))
        time = datetime.time(datetime.strptime(resp.json()['dimensions']['time']['data'][i][11:-1], "%H:%M:%S"))

        if resp.json()['variables']['wind.speed.at-10m']['data'][i] is None:
            wind_speed = 0
        else:
            wind_speed = resp.json()['variables']['wind.speed.at-10m']['data'][i] * 1.9384

        if resp.json()['variables']['wind.direction.at-10m']['data'][i] is None:
            wind_dir = 180
        else:
            wind_dir = resp.json()['variables']['wind.direction.at-10m']['data'][i]
        period = resp.json()['variables']['wave.period.peak']['data'][i]
        swell_height = resp.json()['variables']['wave.height']['data'][i]
        swell_height2 = resp.json()['variables']['wave.height.above-8s']['data'][i]
#        swell_direction = line[7][:-1]
        tide = TideFinder(date, time, tidelist)
        depth = 2.2        # flood river flow

        # Calculating swell impact, taking into account height and period. May need to add direction - (NE worse than NW?)
        swell_score = 0.0112 * (swell_height * period) ** 3 - 0.1667 * (swell_height * period) ** 2 + 3.7639 * (
                swell_height * period) +1
        swell_score2 = 0.0112 * (swell_height2 * period) ** 3 - 0.1667 * (swell_height2 * period) ** 2 + 3.7639 * (
                swell_height2 * period) + 1

        # Calculating wind impact, based on direction and average strength (in knots)
        if wind_dir <= 78.75 or wind_dir >= 303.75:
            wind_score = 2 * wind_speed

        elif 236.25 <= wind_dir < 303.75:
            wind_score = wind_speed

        else:
            wind_score = 0.5 * wind_speed

        # Calculating effect of tide (height and direction) and taking into account depth of bar
        tide_score = 200.83 * math.e ** (-0.92 * (depth + tide[0]))
        if tide[1] == "out":
            tide_score = tide_score * 1.5

        barScore = swell_score + wind_score + tide_score
        barScore2 = swell_score2 + wind_score + tide_score
        barScore3 = swell_score + tide_score

        updaterange = "A"+ str(j) + ":E" + str(j)
        # Workabble
        if barScore <= 50:
            worksheet.update(updaterange, [[date.strftime("%d/%m/%Y"), time.strftime("%H:%M"), "Workable", barScore2, barScore3]])
            j+=1
            weather.write(date.strftime("%d/%m/%Y")+","+time.strftime("%H:%M")+","+str(wind_speed)+","+str(wind_dir)+","+str(period)+","+str(swell_height)+","+str(swell_height2)+"\n")
            print(date, time, barScore, barScore2, barScore3)

        # Workable with caution
        elif barScore <= 100:
            worksheet.update(updaterange, [[date.strftime("%d/%m/%Y"), time.strftime("%H:%M"), "Workable with Caution", barScore2, barScore3]])
            j += 1
            weather.write(date.strftime("%d/%m/%Y")+","+time.strftime("%H:%M")+","+str(wind_speed)+","+str(wind_dir)+","+str(period)+","+str(swell_height)+","+str(swell_height2)+"\n")
            print(date, time, barScore, barScore2, barScore3)

        # Closed
        else:
            worksheet.update(updaterange, [[date.strftime("%d/%m/%Y"), time.strftime("%H:%M"), "Closed", barScore2, barScore3]])
            j += 1
            weather.write(date.strftime("%d/%m/%Y")+","+time.strftime("%H:%M")+","+str(wind_speed)+","+str(wind_dir)+","+str(period)+","+str(swell_height)+","+str(swell_height2)+"\n")
            print(date, time, barScore, barScore2, barScore3)
    bar.close()
    tides.close()
    weather.close()


# This is pretty messy... needs work! Finding depth at any given time
def TideFinder(date, time, tidelist):
    for i in range(len(tidelist)):

        if tidelist[i][0] == date:
            daysTides = tidelist[i]

            if daysTides[-1] == "":
                daysTides[-2] = tidelist[i + 1][1]
                daysTides[-1] = tidelist[i + 1][2]

            if time == datetime.time(datetime.strptime(daysTides[1], "%H:%M")):
                if float(daysTides[2]) < 1:
                    dir = "in"

                else:
                    dir = "out"

                return float(daysTides[2]), dir

            elif time == datetime.time(datetime.strptime(daysTides[3], "%H:%M")):
                if float(daysTides[4]) < 1:
                    dir = "in"
                else:
                    dir = "out"
                return float(daysTides[4]), dir

            elif time == datetime.time(datetime.strptime(daysTides[5], "%H:%M")):
                if float(daysTides[6]) < 1:
                    dir = "in"
                else:
                    dir = "out"
                return float(daysTides[6]), dir

            elif time == datetime.time(datetime.strptime(daysTides[7], "%H:%M")):
                if float(daysTides[8]) < 1:
                    dir = "in"
                else:
                    dir = "out"
                return float(daysTides[8]), dir

            elif time < datetime.time(datetime.strptime(daysTides[1], "%H:%M")):
                prevTide = (tidelist[i - 1][-2], float(tidelist[i - 1][-1]))
                nextTide = (daysTides[1], float(daysTides[2]))

            elif datetime.time(datetime.strptime(daysTides[1], "%H:%M")) < time < datetime.time(
                    datetime.strptime(daysTides[3], "%H:%M")):
                prevTide = (daysTides[1], float(daysTides[2]))
                nextTide = (daysTides[3], float(daysTides[4]))

            elif datetime.time(datetime.strptime(daysTides[3], "%H:%M")) < time < datetime.time(
                    datetime.strptime(daysTides[5], "%H:%M")):
                prevTide = (daysTides[3], float(daysTides[4]))
                nextTide = (daysTides[5], float(daysTides[6]))

            elif datetime.time(datetime.strptime(daysTides[5], "%H:%M")) < time < datetime.time(
                    datetime.strptime(daysTides[7], "%H:%M")):
                prevTide = (daysTides[5], float(daysTides[6]))
                nextTide = (daysTides[7], float(daysTides[8]))

            elif time > datetime.time(datetime.strptime(daysTides[7], "%H:%M")) > datetime.time(
                    datetime.strptime(daysTides[5], "%H:%M")):
                prevTide = (daysTides[7], float(daysTides[8]))
                nextTide = (tidelist[i + 1][1], float(tidelist[i + 1][2]))

            else:
                prevTide = (daysTides[5], float(daysTides[6]))
                nextTide = (daysTides[7], float(daysTides[8]))

            break

    t = TimeToDecimal(time)
    t1 = TimeToDecimal(prevTide[0])
    t2 = TimeToDecimal(nextTide[0])

    A = math.pi * (((t - t1) / (t2 - t1)) + 1)

    tideHeight = prevTide[1] + (nextTide[1] - prevTide[1]) * ((math.cos(A) + 1) / 2)

    flow = nextTide[1] - prevTide[1]

    if flow < 0:
        flow = "out"
    else:
        flow = "in"

    return tideHeight, flow


# Function  used within TideFinder to convert minutes portion of time to decimal. Necessary for calculations
def TimeToDecimal(time):
    if not isinstance(time, str):
        time = time.strftime("%H.%M")
    minutes = int(time[-2:]) / 60
    time = int(time[:-3]) + minutes
    return time


# print(tidefinder(datetime.date(datetime.strptime("08/03/2022", "%d/%m/%Y")), datetime.time(datetime.strptime("22:00", "%H:%M")), tidelist))
BarForecast(tidelist, resp)


#print(resp.status_code)
# print(resp.json())
# # print just values of wave height:
# print(resp.json()['variables']['wave.direction.mean']['data'])
# print(resp.json()['variables']['wave.direction.above-8s.peak']['data'])
# print(resp.json()['variables']['wave.height']['data'])
# print(resp.json()['dimensions']['time']['data'])
# print(resp.json()['variables']['wind.speed.at-10m']['data'], resp.json()['variables']['wind.speed.at-10m']['noData'])
# print(resp.json()['variables']['wind.direction.at-10m']['data'], resp.json()['variables']['wind.direction.at-10m']['noData'])
# print(resp.json()['variables']['air.visibility']['data'])
