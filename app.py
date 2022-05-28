# Making the necessary imports and importing our face recognition program
from flask import Flask, render_template, request, url_for, redirect, session
from PIL import Image
import base64
import io
from Face import *
import time
import cv2
import numpy as np
from datetime import datetime
import os
import sqlite3
from werkzeug.utils import secure_filename
import urllib.request


# Functions related to security and Transformation of data
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def convertToBinaryData(filename):
    with open(filename, 'rb') as file:
        blobData = file.read()
    return blobData


nm = ""
id_name = ""


# Creating a Flask app with static and template folders and setting up a key 
app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = "super secret key"
app.config['UPLOAD FOLDER'] = r"static"


# This the Home page
@app.route('/')
def hello_world(): 

    session["x1"] = True
    session["Rx1"] = True
    im = Image.open("face.jpg")
    data = io.BytesIO()
    im.save(data, "JPEG")
    encoded_img_data = base64.b64encode(data.getvalue())
    return render_template("index.html", img_data=encoded_img_data.decode('utf-8'))


# This is the attendance login page
@app.route('/hello', methods = ['GET','POST'])
def hello():

    if request.method == "POST":
        nm = request.form.get("name")
        id_name = request.form.get("id")
        session["name"] = nm
        session["id"] = id_name
        return redirect(url_for('wait'))
    
    else:
        return render_template("Form.html")


# This page checks if the user has left any field empty during login else we are redirected to the next page
@app.route('/Wait')
def wait():
    
    if session["name"] == "" or session["id"] == "":
        return render_template("ReForm.html")
    
    else:
        nm = ""
        id_name = ""
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        session["time"] = current_time
    
        if session["x1"]:
            session["x1"] = False
            return render_template("wait.html")
    
        else:
            time.sleep(5)
            session["x1"] = True
            return redirect(url_for('function_1'))


# This function captures the 21st instance of webcam image and saves it in the static folder for later use
@app.route('/function_1')
def function_1():
    
    img = capture_image()
    cv2.imwrite(r'static\Temp.jpg', img)
    return render_template("ImageCheck.html")


# This function calls the face_match and age_gender_detect functions, then if it is a first time login, 
# this page redirects to the first time form which confirms the user gender and age and stores it
@app.route('/function')
def function():
    
    name = session.get("name")
    id = session.get("id")
    time = session.get("time")
    image = Image.open(r'static\Temp.jpg')
    load_face()
    p = face_match(image,name,id, time)
    gender, age = age_gender_detect(image)
    name = name.lower()
    n = len(name)
    session["name"] = ""
    
    for i in range(0,n):
        if i==0:
            session["name"] += name[i].upper()
    
        elif name[i-1] == " ":
            session["name"] += name[i].upper()
    
        else:
            session["name"] += name[i]
    
    session["id"] = id
    session["time"] = time
    session["gender"] = gender
    session["age"] = age
    
    if p:
      con = sqlite3.connect("info.db")
      cur = con.cursor()
      row = cur.execute('''SELECT col3, col4 from DETAILS WHERE col1 = ?;''', (session["name"],))
      data = list(row)
      g = data[0][0]
      a = data[0][1]
      con.close()
    
      if g == None and a == None:
         return render_template("Confirmation.html", gender = session["gender"], age = session["age"])
    
      else:
         return render_template("IdCard.html", name = session["name"], 
                                 id = session["id"], time = session["time"], gender = g, age = a)
    
    else:
      return redirect(url_for('task'))


# This is the gender and age confirmation form for first time users
@app.route('/confirm', methods = ['GET','POST'])
def confirm():
    
    if request.method == "POST":
        gender = request.form.get("gender")
        print(gender, session["gender"])
    
        if gender == 'no' and session["gender"] == 'Male':
            session["gender"] = 'Female'
    
        elif gender == 'no' and session["gender"] == 'Female':
            session["gender"] = 'Male'
    
        age = request.form.get("age")
        con = sqlite3.connect("info.db")
        cur = con.cursor()
        cur.execute("UPDATE DETAILS SET (col3, col4) = (?, ?) WHERE col1 = ?;", (session["gender"], age, session["name"]))
        con.commit()
        con.close()
        return render_template("IdCard.html", name = session["name"], id = session["id"], 
                                time = session["time"], gender = session["gender"], age = age)
    
    else:
        return render_template("Confirmation.html", gender = session["gender"], age = session["age"])


# This is the page that appears if the recognized name or stored Id is different from the entered name and Id 
@app.route('/task')
def task():
    
    print(session["name"])
    return render_template("Task.html")


# This is the attendance list which shows the first entry instance of a particular person and does not repeat the same person
@app.route('/Alist')
def Alist():
    
    com = sqlite3.connect("info.db")
    cur = com.cursor()
    row = cur.execute("SELECT * from ATTENDANCE")
    data = list(row)
    length = len(data)
    com.close()
    return render_template('Alist.html', length=length, data=data)


# This is page that appears when we click Clear attendance on home page
@app.route('/erase_message')
def erase_message():
    
    return render_template('Erase_message.html')


# This function clears the attendance records
@app.route('/erase')
def erase():
    
    com = sqlite3.connect("info.db")
    cur = com.cursor()
    cur.execute('''DELETE FROM ATTENDANCE''')
    com.commit()
    com.close()
    return redirect(url_for('hello_world'))


# This is page that appears when we click Clear details on home page
@app.route('/erase_message2')
def erase_message2():
    
    return render_template('Erase_message2.html')


# This function clears the person detail records
@app.route('/erase2')
def erase2():
    
    com = sqlite3.connect("info.db")
    cur = com.cursor()
    cur.execute('''DELETE FROM DETAILS;''')
    cur.execute('''DELETE FROM IMAGES;''')
    com.commit()
    com.close()
    return redirect(url_for('hello_world'))


# This form is for storing the details of a new user by the admin, i.e., name of the user and the Id provided by the admin 
@app.route('/Rhello', methods = ['GET','POST'])
def Rhello():
    
    if request.method == "POST":
        nm = request.form.get("Rname")
        id_name = request.form.get("Rid")
        img = request.files["img"]
        print(img.filename == "")
        print(type(nm), type(id_name), type(img))
        
        if img.filename == "":
            session["image"] = ""
        
        else:
         filename = secure_filename(img.filename)
         session["image"] = filename
         print(session["image"])
         img.save(os.path.join(app.config['UPLOAD FOLDER'], filename))
         session["Rname"] = nm
         session["Rid"] = id_name
         print(session["Rname"])
        return redirect(url_for('Rwait'))

    else:
        return render_template("RForm.html")


# This is check for empty fields and storing in the database
@app.route('/RWait')
def Rwait():

    if session["Rname"] == "" or session["Rid"] == "" or session["image"] == "":
        print(1)
        return render_template("ReRForm.html")

    else:
       con = sqlite3.connect("info.db")
       cur = con.cursor()
       session["Rname"] = session["Rname"].lower()
       n = len(session["Rname"])
       nm = ""
       for i in range(0,n):
           if i==0:
               nm += session["Rname"][i].upper()
           elif session["Rname"][i-1] == " ":
               nm += session["Rname"][i].upper()
           else:
               nm += session["Rname"][i]
       cur.execute('''INSERT INTO DETAILS (col1, col2) VALUES (?, ?);''', (nm, session["Rid"]))
       empphoto = convertToBinaryData(os.path.join(app.config['UPLOAD FOLDER'], session["image"]))
       os.remove(os.path.join(app.config['UPLOAD FOLDER'], session["image"]))
       cur.execute('''INSERT INTO IMAGES (col1, col2) VALUES (?, ?);''', (nm, empphoto))
       con.commit()
       con.close()
       return redirect(url_for('hello_world'))


# This the list consisting of the details of every registered user in the database, 
# the gender and age may be None if the user has never log in to give attendance
@app.route('/Dlist')
def Dlist():

    com = sqlite3.connect("info.db")
    cur = com.cursor()
    row = cur.execute("SELECT * from DETAILS")
    data = list(row)
    length = len(data)
    com.close()
    return render_template('Dlist.html', length=length, data=data)



if __name__ == '__main__':
    app.run(debug=True)

