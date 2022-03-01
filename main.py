import math
from _datetime import datetime

"""
Whakatāne bar forecasting algorithm v1
2nd March 2022
"""

forecast = open("Weather.csv", "r")
tides = open("Whakatāne 2022.csv", "r")
bar = open("BarForecast.csv", "w")

#Listing tides for the year. Format of date, tide 1 time, tide 1 height, tide 2 time etc.
tidelist = []
for line in tides:
    line = line.split(",")
    line[0] = datetime.date(datetime.strptime(line[0], "%d/%m/%Y"))
    line[-1] = line[-1].rstrip("\n")
    tidelist.append(line)

def BarForecast(tidelist):
    for line in forecast:
        line = line.split(",")

        date = datetime.date(datetime.strptime(line[0], "%d/%m/%Y"))
        time = datetime.time(datetime.strptime(line[1], "%H:%M"))
        windAvg = int(line[3])
        windDir = line[4]
        seaPer = int(line[5])
        swellHgt = float(line[6])
        swellDir = line[7][:-1]
        tide = TideFinder(date, time, tidelist)
        depth = 2

        #Calculating swell impact, taking into account height and period. May need to add direction - (NE worse than NW?)
        swellScore = 0.0044 * (swellHgt * seaPer)**3 - 0.0889 * (swellHgt * seaPer)**2 + 1.0833 * (swellHgt * seaPer) + 5*10**(-12)

        #Calculating wind impact, based on direction and average strength (in knots)
        if windDir[0].upper() == "N":
            windScore = 2 * windAvg

        elif windDir[0].upper() == "W":
            windScore = windAvg

        else:
            windScore = 0.5 * windAvg

        #Calculating effect of tide (height and direction) and taking into account depth of bar
        tideScore = 320.37 * math.e**(-1.371*(depth + tide[0]))
        if tide[1] == "out":
            tideScore = tideScore * 2

        barScore = swellScore + windScore + tideScore

        #Workabble
        if barScore <= 50:
            bar.write(date.strftime("%d/%m/%Y") +","+ time.strftime("%H:%M") + ",Bar is workable\n")

        #Workable with caution
        elif barScore <= 100:
            bar.write(date.strftime("%d/%m/%Y") + "," + time.strftime("%H:%M") + ",Bar is workable with caution\n")

        #Closed
        else:
            bar.write(date.strftime("%d/%m/%Y") + "," + time.strftime("%H:%M") + ",Bar is closed\n")

    bar.close()
    forecast.close()
    tides.close()

#This is pretty messy... needs work! Finding depth at any given time
def TideFinder(date, time, tidelist):
    for i in range(len(tidelist)):

        if tidelist[i][0] == date:
            daysTides = tidelist[i]

            if daysTides[-1] == "":
                daysTides[-2] = tidelist[i+1][1]
                daysTides[-1] = tidelist[i+1][2]

            if time == datetime.time(datetime.strptime(daysTides[1], "%H:%M")):
                if daysTides[2] < 1:
                    dir = "in"

                else:
                    dir = "out"

                return daysTides[2], dir

            elif time == datetime.time(datetime.strptime(daysTides[3], "%H:%M")):
                if daysTides[4] < 1:
                    dir = "in"
                else:
                    dir = "out"
                return daysTides[4], dir

            elif time == datetime.time(datetime.strptime(daysTides[5], "%H:%M")):
                if daysTides[6] < 1:
                    dir = "in"
                else:
                    dir = "out"
                return daysTides[6], dir

            elif time == datetime.time(datetime.strptime(daysTides[7], "%H:%M")):
                if daysTides[8] < 1:
                    dir = "in"
                else:
                    dir = "out"
                return daysTides[8], dir

            elif time < datetime.time(datetime.strptime(daysTides[1], "%H:%M")):
                prevTide = (tidelist[i-1][-2], float(tidelist[i-1][-1]))
                nextTide = (daysTides[1], float(daysTides[2]))

            elif datetime.time(datetime.strptime(daysTides[1], "%H:%M")) < time < datetime.time(datetime.strptime(daysTides[3], "%H:%M")):
                prevTide = (daysTides[1], float(daysTides[2]))
                nextTide = (daysTides[3], float(daysTides[4]))

            elif datetime.time(datetime.strptime(daysTides[3], "%H:%M")) < time < datetime.time(datetime.strptime(daysTides[5], "%H:%M")):
                prevTide = (daysTides[3], float(daysTides[4]))
                nextTide = (daysTides[5], float(daysTides[6]))

            elif datetime.time(datetime.strptime(daysTides[5], "%H:%M")) < time < datetime.time(datetime.strptime(daysTides[7], "%H:%M")):
                prevTide = (daysTides[5], float(daysTides[6]))
                nextTide = (daysTides[7], float(daysTides[8]))

            elif time > datetime.time(datetime.strptime(daysTides[7], "%H:%M")) > datetime.time(datetime.strptime(daysTides[5], "%H:%M")):
                prevTide = (daysTides[7], float(daysTides[8]))
                nextTide = (tidelist[i+1][1], float(tidelist[i+1][2]))

            else:
                prevTide = (daysTides[5], float(daysTides[6]))
                nextTide = (daysTides[7], float(daysTides[8]))

            break

    t = TimeToDecimal(time)
    t1 = TimeToDecimal(prevTide[0])
    t2 = TimeToDecimal(nextTide[0])

    A = math.pi * (((t - t1)/(t2 - t1))+1)

    tideHeight = prevTide[1] + (nextTide[1] - prevTide[1])* ((math.cos(A) + 1)/2)

    flow = nextTide[1] - prevTide[1]

    if flow < 0:
        flow = "out"
    else:
        flow = "in"

    return tideHeight, flow

#Function for used within TideFinder to convert minutes portion of time to decimal. Necessary for calculations
def TimeToDecimal(time):
    if not isinstance(time, str):
        time = time.strftime("%H.%M")
    minutes = int(time[-2:]) / 60
    time = int(time[:-3]) + minutes
    return time

#print(tidefinder(datetime.date(datetime.strptime("08/03/2022", "%d/%m/%Y")), datetime.time(datetime.strptime("22:00", "%H:%M")), tidelist))
BarForecast(tidelist)

