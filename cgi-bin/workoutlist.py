#!/usr/bin/python

import requests
import json
import urllib
import cgi
import re
import shutil
from shutil import copyfileobj
import sys
import Cookie
import os


def get_session(email=None, password=None):
        session = requests.Session()
        
        data = {
            "username": email,
            "password": password,
            "_eventId": "submit",
            "embed": "true",
        }
        params = {
            "service": "https://connect.garmin.com/post-auth/login",
            "clientId": "GarminConnect",
            "consumeServiceTicket": "false"
        }
        
        preResp = session.get("https://sso.garmin.com/sso/login", params=params)
        data["lt"] = re.search("name=\"lt\"\s+value=\"([^\"]+)\"", preResp.text).groups(1)[0]
        ssoResp = session.post("https://sso.garmin.com/sso/login", params=params, data=data, allow_redirects=False)
        ticket_match = re.search("ticket=([^']+)'", ssoResp.text)
        ticket = ticket_match.groups(1)[0]
        gcRedeemResp = session.get("https://connect.garmin.com/post-auth/login", params={"ticket": ticket}, allow_redirects=False)
        expected_redirect_count = 6
        current_redirect_count = 1
        while True:
            gcRedeemResp = session.get(gcRedeemResp.headers["location"], allow_redirects=False)
            if current_redirect_count >= expected_redirect_count and gcRedeemResp.status_code != 200:
                raise APIException("GC redeem %d/%d error %s %s" % (current_redirect_count, expected_redirect_count, gcRedeemResp.status_code, gcRedeemResp.text))
            if gcRedeemResp.status_code == 200 or gcRedeemResp.status_code == 404:
                break
            current_redirect_count += 1
            if current_redirect_count > expected_redirect_count:
                break
        return session

form = cgi.FieldStorage()

if "HTTP_COOKIE" in os.environ and os.environ.get('HTTP_COOKIE') != "":
    cookie_string=os.environ.get('HTTP_COOKIE')
    cookie=Cookie.SimpleCookie()
    cookie.load(cookie_string)
    username = cookie["username"].value
    password = cookie["password"].value

elif "username" in form and "password" in form:
    username = form["username"].value
    password = form["password"].value
    cookie=Cookie.SimpleCookie()
    cookie["username"] = username
    cookie["password"] = password
    print cookie
else:
    username = ""
    password = ""

session = get_session(email=username, password=password)   

if "action" in form:
    if form["action"].value == "View Workouts":
        print "Content-Type: text/html\n\n"
        
        result = session.get("https://connect.garmin.com/proxy/workout-service-1.0/json/workoutlist").text
        print "<textarea name='result' rows='20' cols='80'>"+result+"</textarea>"
        print "<br>"
        json_obj = json.loads(result)
        for i in json_obj['com.garmin.connect.workout.dto.BaseUserWorkoutListDto']['baseUserWorkouts']:
            print "<input type='button' onclick=\"location.href='workoutlist.py?action=Download&workoutId="+str(i['workoutId'])+"';\" value='Download' />"
            print "<input type='button' onclick=\"delete_button("+str(i['workoutId'])+");\" value='Delete' />"
            print i['workoutName']
            print "<br>"

        print "<br><br>"
        print "<a href='../garmin_workout_tools.html'>Back to Main</a>"
        print """
            <script type='text/javascript'>
            function delete_button(id) {
            var user_choice = window.confirm('Are you sure you want to delete this workout?');
            if(user_choice==true) {
            window.location="workoutlist.py?action=Delete&workoutId="+id;
            } else {
            return false;
            }
            }
            </script>
        """

    if form["action"].value == "Upload Workout":
        print "Content-Type: text/html\n\n"
        
        #json_str = open('test.json', 'r').read()
        json_str = form["result"].value
        json_str = json.dumps(json.loads(json_str), separators=(',', ':'))
        payload = {'data':json_str}
        post = session.post("https://connect.garmin.com/proxy/workout-service-1.0/json/createWorkout", headers={"content-type":"application/x-www-form-urlencoded"}, params=payload)
        print "URL: "
        print post.url
        print "<br>"
        print "URL (decoded): "
        print urllib.unquote(post.url)
        print "<br>"
        print "Result: "
        print "<br>"
        print "<textarea name='result' rows='20' cols='80'>"+post.text+"</textarea>"
        print "<br><br>"
        print "<a href='../garmin_workout_tools.html'>Back to Main</a>"

    if form["action"].value == "Download":
        print "Content-Type: application/octet-stream"
        print "Content-Disposition: attachment; filename=download.json"
        print ""
        #print form
        response = session.get("https://connect.garmin.com/proxy/workout-service-1.0/json/workout/"+form["workoutId"].value).text
        print response

    if form["action"].value == "Delete":
        print "Content-Type: text/html\n\n"
        response = session.delete("https://connect.garmin.com/proxy/workout-service-1.0/json/deleteWorkout/"+form["workoutId"].value).text
        print response
        print "<br><br>"
        print "<a href='../garmin_workout_tools.html'>Back to Main</a>"

