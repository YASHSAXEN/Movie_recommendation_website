from flask import Flask, render_template, request, redirect, url_for,flash,session,send_file
from flask_mail import Mail,Message
from flask_paginate import Pagination, get_page_args
from flask_sqlalchemy import SQLAlchemy
import pickle
import pandas as pd
import numpy as np
import requests
import re
import imdb
from bs4 import BeautifulSoup
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import json

with open("config.json",'r') as c:
    params = json.load(c)["params"]

UPLOAD_FOLDER = 'static'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = params["database"] 
app.config['SECRET_KEY'] = params["secret_key"]
app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = params["mail_id"]
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_PASSWORD'] = params["mail_pass"]
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
mail = Mail(app)
db = SQLAlchemy(app)

class Contactus(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    mobilenumber = db.Column(db.String(12), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    message = db.Column(db.String(1000), nullable=False)

class Moviedata(db.Model):
    movie_id = db.Column(db.Integer, primary_key=True)
    movie_name = db.Column(db.String(80), nullable=False)
    poste_path = db.Column(db.String(12), nullable=False)

class Userdetails(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(1000), nullable=False)
    filename = db.Column(db.String(50))

class Bookmark(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    movieid = db.Column(db.Integer, nullable=False)
    moviename = db.Column(db.String(80), nullable=False)
    posterpath = db.Column(db.String(12), nullable=False)
    username = db.Column(db.String(80), nullable=False)

class History(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    moviename = db.Column(db.String(80), nullable=False)
    posterpath = db.Column(db.String(12), nullable=False)
    username = db.Column(db.String(80), nullable=False)
    date = db.Column(db.String(80), nullable=False)
 
ia = imdb.IMDb()

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def fetch_poster(movieid):
    flag = False
    keys = params["api_key"]
    response = requests.get(
        f"https://api.themoviedb.org/3/find/{movieid}?api_key={keys}&language=en-US&external_source=imdb_id")
        # f"https://api.themoviedb.org/3/find/{movieid}?api_key=9ec4fcf6ee16570a83538ebb62923432&language=en-US&external_source=imdb_id")
    data = response.json()
    if len(data["movie_results"]) != 0 and flag == False:
        poster_path = data["movie_results"][0]["poster_path"]
        flag = True
    elif len(data["tv_results"]) != 0 and flag == False:
        poster_path = data["tv_results"][0]["poster_path"]
    return "https://image.tmdb.org/t/p/original/" + poster_path

def fetch_trailer_link(movieid):
    key = []
    status = True
    keys = params["api_key"]
    response = requests.get(f"http://api.themoviedb.org/3/movie/{movieid}/videos?api_key={keys}")
        # f"http://api.themoviedb.org/3/movie/{movieid}/videos?api_key=9ec4fcf6ee16570a83538ebb62923432")
    data = response.json()
    try:
        flag = True
        lst = data["results"]
        show = ""
        if len(lst)!=0:
            for i in range(len(lst)):
                if lst[i]["type"] == "Trailer":
                    key.append(lst[i]["key"])
                    flag = False
                    show +=  lst[i]["type"]
                    break
            if flag==True:
                y = 0
                for i in range(len(lst)):
                    if lst[i]["type"] == "Teaser":
                        key.append(lst[i]["key"])
                        flag = False
                        y=1
                        show +=  lst[i]["type"]
                        print("yess")
                        break
                if flag==True:
                    for i in range(len(lst)):
                        if lst[i]["type"] == "Clip":
                            key.append(lst[i]["key"])
                            flag = False
                            y=1
                            show +=  lst[i]["type"]
                            print("yesss")
                            break
                elif y==0:
                    key.append("")
                    status = False
                
        else:
            key.append("")
            status = False
    except:
        key.append("")
        status = False
    print(key)
    return "https://www.youtube.com/watch?v="+key[0],status,show

df = pickle.load(open("df.pkl", "rb"))
df = pd.DataFrame(df)

genres = df["Genre"].str.split(",")
genres_list = set()
for i in genres:
    lst = []
    for j in i:
        lst.append(j.strip())
    genres_list = genres_list.union(set(lst))
genres_lists = list(genres_list)
if len(genres_lists) == 21:
    genres_lists.remove("War")
    genres_lists.remove("Musical")
    genres_lists.remove("History")
    genres_lists.remove("Music")
    genres_lists.remove("Sport")
    genres_lists.remove("Family")

dic = {}
for genre in genres_lists:
    dic.update({genre: df[genre].value_counts().to_dict()})
genre_dataframe = pd.DataFrame(dic)

def popularitybasedrecommendation(selected_movie_genre):
    no_of_entries = genre_dataframe[selected_movie_genre][1]
    new_df = df[df[selected_movie_genre] == 1] 
    if no_of_entries<100:
        top_five_movies = new_df.head(no_of_entries)
    else:
        top_five_movies = new_df.head(100)
    titles = []
    recommended_movie_poster = []
    recommended_movie_id = []
    for title in top_five_movies["Name"]:
        w = 0
        search = ia.search_movie(title)
        search_id = search[0].movieID
        movieid = "tt"+search_id
        try:
            path = fetch_poster(movieid)
        except:
            w = 1
        if w ==0:
            recommended_movie_poster.append(path)
            titles.append(title)
            recommended_movie_id.append(search_id)
    return titles, recommended_movie_poster, recommended_movie_id

def fetch_selected_movie_detials(selected_movie_name):
    data = used_data[used_data["Name"] == selected_movie_name]
    overview = data["Overview"].values[0]
    title = data["Name"].values[0]
    genre = data["Genre"].values[0]
    runtime = str(data["Runtime"].values[0]) + " min"
    rating = "⭐ " + str(data["Rating"].values[0])
    director = data["Director"].values[0]
    actor = str(data["Actors"].values[0])[1:-1]
    overview = data["Overview"].values[0]
    return title, genre, runtime, rating, director, actor, overview

used_data = pickle.load(open("used_data.pkl", "rb"))
used_data = pd.DataFrame(used_data)

similarity = pickle.load(open("similarity3.pkl", "rb"))

def recommendations(moviename):
    movie_index = movies[movies["Name"] == moviename].index[0]
    similarities = list(enumerate(similarity[movie_index]))
    sorted_similarities = sorted(
        similarities, key=lambda x: x[1], reverse=True)[0:6]
    recommended_movie = []
    recommended_movie_poster = []
    recommended_movie_id = []
    for i in sorted_similarities:
        recomended_movies_tilte = movies.iloc[i[0]]["Name"]
        search = ia.search_movie(recomended_movies_tilte)
        movieid = "tt"+search[0].movieID
        recommended_movie_id.append(movieid)
        recommended_movie.append(recomended_movies_tilte)
        recommended_movie_poster.append(fetch_poster(movieid))
    return recommended_movie, recommended_movie_poster , recommended_movie_id

movie_data = pickle.load(open("movie_data4.pkl", "rb"))
movies = pd.DataFrame(movie_data)
movie_list = movies["Name"].values

@app.route("/")
@app.route("/login",methods=["POST","GET"])
def login():
    if request.method =="POST":
        username = request.form["username"]
        password = request.form["password"]
        page1 = request.form["page1"]
        login = Userdetails.query.filter_by(username=username,password=password).first()
        if login is not None:
            session['loggedin'] =True
            session["username"] = username
            session["password"] = password
            return redirect(url_for(page1))
        else:
            flash("😡 Please Enter valid username/password")
            return render_template("login.html")
    return render_template("login.html")

@app.route("/signup",methods=["POST","GET"])
def signup():
    statuses = True
    if request.method =="POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        cpassword = request.form["cpassword"]
        condition = "^[a-z]+[\._]?[a-z 0-9]+[@]\w+[.]\w{2,3}$"
        user = Userdetails.query.filter_by(username=username).all()
        if len(user)>0:
            statuses=False
            flash("😡 Username Already Exist!")
            return render_template("signup.html", statuses=statuses)
        elif re.search(condition,email) and len(username)>=4 and len(password)>4 and password==cpassword and len(user)==0:
            details = Userdetails(username=username, email=email, password=password)
            db.session.add(details)
            db.session.commit()
            flash("✅ Successfully Registered/Go on Login page")
            return render_template("signup.html",statuses=statuses)
        else:
            statuses=False
            flash("😡 Please Enter valid entries")
            return render_template("signup.html", statuses=statuses)
    return render_template("signup.html")

@app.route("/index", methods=["POST", "GET"])
def index():
    bollywood = []
    bollywoodid = []
    bollywoodposter = []
    hollywood = []
    hollywoodid = []
    hollywoodposter = []
    r1 = requests.get("https://www.gadgets360.com/entertainment/new-hindi-movies")
    webpage1 = r1.text
    soup1 = BeautifulSoup(webpage1,"lxml")
    for i in range(8):
        t = 0
        ia = imdb.IMDb()
        name = soup1.find_all("div",class_="_mvbx _flx")[i].find("div",class_="_mvinfo").find("a").text
        search = ia.search_movie(name)
        movieid = "tt"+search[0].movieID
        try:
            path = fetch_poster(movieid)
        except:
            t = 1
        if t ==0:
            bollywoodposter.append(path)
            bollywoodid.append(movieid)
            bollywood.append(name)
    r2 = requests.get("https://www.gadgets360.com/entertainment/new-english-movies")
    webpage2 = r2.text
    soup2 = BeautifulSoup(webpage2,"lxml")
    for i in range(8):
        q = 0
        ia = imdb.IMDb()
        name = soup2.find_all("div",class_="_mvbx _flx")[i].find("div",class_="_mvinfo").find("a").text
        search = ia.search_movie(name)
        movieid = "tt"+search[0].movieID
        try:
           path = fetch_poster(movieid)
        except:
            q=1
        if q==0: 
            hollywoodid.append(movieid)
            hollywood.append(name)
            hollywoodposter.append(path)
    if request.method == "POST":
        selected_movie = request.form["sn"]
        return redirect(url_for('single', movie=selected_movie))
    return render_template("index.html", movie_list=movie_list,bollywoodposter=bollywoodposter,hollywoodposter=hollywoodposter)

@app.route("/about", methods=["POST", "GET"])
def about():
    if request.method == "POST":
        selected_movie = request.form["sn"]
        return redirect(url_for('single', movie=selected_movie))
    return render_template("about.html", movie_list=movie_list)

@app.route("/review", methods=["GET", "POST"])
def review():
    page = request.args.get("page",1,type=int)
    data = Moviedata.query.paginate(page=page,per_page=4)
    if request.method == "POST" and "sn" in request.form:
        selected_movie = request.form["sn"]
        return redirect(url_for('single', movie=selected_movie))
    elif request.method == "POST" and "gn" in request.form:
        data = Moviedata.query.filter_by().all()
        if len(data)>0:
            for i in data:
                y = int(str(i)[10:-1])
                post =  Moviedata.query.filter_by(movie_id=y).first()
                db.session.delete(post)
                db.session.commit()
        genre = request.form["gn"]
        
        titles, posters, id = popularitybasedrecommendation(genre)
        data = Moviedata.query.filter_by().all()
        for i in range(len(titles)):
                entry = Moviedata(movie_id=id[i], movie_name=titles[i], poste_path=posters[i])
                db.session.add(entry)
                db.session.commit()
        page = request.args.get("page",1,type=int)
        data = Moviedata.query.paginate(page=page,per_page=4)
        return render_template("review.html", lists=genres_lists,  g=genre,data=data,titles=titles, posters=posters,movie_list=movie_list)
    elif request.method == "POST" and "selm" in request.form:
        moviename = request.form.get("selm")
        return redirect(url_for('single', movie=moviename))
    return render_template("review.html", lists=genres_lists,  movie_list=movie_list,data=data)

@app.route("/contact", methods=["POST", "GET"])
def contact():
    statuses = True
    if request.method == "POST" and "name" in request.form:
        username = request.form["name"]
        email = request.form["email"]
        mobilenumber = request.form["number"]
        message = request.form["message"]
        condition = "^[a-z]+[\._]?[a-z 0-9]+[@]\w+[.]\w{2,3}$"
        if re.search(condition,email) and len(mobilenumber)==10 and len(username)>=4 and len(message)>4:
            entry1 = Contactus(username=username, mobilenumber=mobilenumber, email=email,message=message)
            db.session.add(entry1)
            db.session.commit()
            msg = Message(f'From the Recommendation Site {username}', sender = email, recipients = ['ashusaxena210403@gmail.com'])
            msg.body = username + "\n" + message
            mail.send(msg)
            flash("✅ Successfully Submitted")
            return render_template("contact.html", movie_list=movie_list,statuses=statuses)
        else:
            statuses=False
            flash("😡 Please Enter valid entries")
            return render_template("contact.html", movie_list=movie_list,statuses=statuses)
    if request.method == "POST" and "sn" in request.form:
        selected_movie = request.form["sn"]
        return redirect(url_for('single', movie=selected_movie))
    return render_template("contact.html", movie_list=movie_list)

@app.route("/single/<string:movie>",methods=["POST","GET"])
def single(movie):
    statuses = True
    flag=0
    x = movie.split(" ")
    c = "%20".join(x)
    if request.method == "POST":
        bookmark = request.form["bkm"]
        username = session["username"]
        data1 = Bookmark.query.filter_by(username=username).all()
        bookmarked_movies = []
        for i in range(len(data1)):
            sno = int(str(data1[i])[10:-1])
            data2 =  Bookmark.query.get(sno)
            bookmarked_movies.append(data2.moviename)
        if bookmark not in bookmarked_movies:
            flag=1
            search = ia.search_movie(bookmark)
            movieid = "tt"+search[0].movieID
            posterpath = fetch_poster(movieid)
            details = Bookmark(username=username,movieid=search[0].movieID,posterpath=posterpath,moviename= bookmark)
            db.session.add(details)
            db.session.commit()
            flash(f"✅ {bookmark} is Bookmarked")
        else:
            statuses = False
            flag=2
            flash(f"😶‍🌫️ You already bookmarked {bookmark} ")
    title, genr, runtime, rating, director, actor, overview = fetch_selected_movie_detials(movie)
    recommended_movie, recommended_movie_poster, recommended_movie_id = recommendations(movie)
    print(recommended_movie_id[0])
    search_movie_link,status,show = fetch_trailer_link(recommended_movie_id[0])
    entry = History(username=session["username"], moviename=recommended_movie[0], posterpath=recommended_movie_poster[0],date=datetime.now())
    db.session.add(entry)
    db.session.commit()
    return render_template("single.html",search_movie_link = search_movie_link ,movie_list=movie_list, title=title, genre=genr, runtime=runtime, rating=rating, director=director, actor=actor, overview=overview, recommended_movie=recommended_movie, recommended_movie_poster=recommended_movie_poster,status=status,c=c,flag=flag,show=show)

@app.route("/logout")
def logout():
    session.pop("loggedin",None)
    session.pop("username",None)
    session.pop("password",None)
    return redirect(url_for("login"))

@app.route("/profile",methods=["POST","GET"])
def profile():
    if request.method=="POST" and "update" in request.form:
        user = Userdetails.query.filter_by(username=session["username"]).first()
        s_no = int(str(user)[13:-1])
        print(s_no)
        return redirect(url_for("update",s_no=s_no))
    elif request.method=="POST" and "bookmarks" in request.form:
        return redirect(url_for("bookmark"))
    elif request.method=="POST" and "History" in request.form:
        return redirect(url_for("history"))
    user = Userdetails.query.filter_by(username=session["username"]).all()
    return render_template("profile.html",user=user, movie_list=movie_list)

@app.route("/update/<int:s_no>",methods=["POST","GET"])
def update(s_no):
    user = Userdetails.query.get(s_no)
    if request.method=="POST":
        email = request.form["email"]
        password =request.form["password"]
        file = request.files["file"]
        condition = "^[a-z]+[\._]?[a-z 0-9]+[@]\w+[.]\w{2,3}$"
        if re.search(condition,email) and len(password)>4:
            user.password = password
            user.email = email
            user.filename = file.filename
            db.session.commit()
            user = Userdetails.query.get(s_no)
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for("profile",user = user))
        else:
            flash("😡 Please Enter valid entries")
            return render_template("update.html",movie_list=movie_list,user=user)
    return render_template("update.html",movie_list=movie_list,user=user)

@app.route("/bookmark",methods=["POST","GET"])
def bookmark():
    if request.method == "POST" and "selm" in request.form:
        moviename = request.form.get("selm")
        return redirect(url_for('single', movie=moviename))
    if request.method == "POST" and "remove" in request.form:
        moviename = request.form["remove"]
        value1 = Bookmark.query.filter_by(username=session["username"]).all()
        for i in range(len(value1)):
            valueno = int(str(value1[i])[10:-1])
            value2 =  Bookmark.query.get(valueno)
            if value2.moviename == moviename:
                movie =  Bookmark.query.filter_by(sno=valueno).first()
                db.session.delete(movie)
                db.session.commit()
                break
    username = session["username"]
    data1 = Bookmark.query.filter_by(username=username).all()
    bookmarked_movies_name = []
    bookmarked_movies_posterpath = []
    for i in range(len(data1)):
        sno = int(str(data1[i])[10:-1])
        data2 =  Bookmark.query.get(sno)
        bookmarked_movies_name.append(data2.moviename)
        bookmarked_movies_posterpath.append(data2.posterpath)
    y = len(bookmarked_movies_name)
    return render_template("bookmark.html",bookmarked_movies_name=bookmarked_movies_name,bookmarked_movies_posterpath=bookmarked_movies_posterpath,movie_list=movie_list,y=y)

@app.route("/forgot",methods=["POST","GET"])
def forgot():
    if request.method =="POST":
        username = request.form["username"]
        password = request.form["password"]
        confirmpassword = request.form["cpassword"]
        print(username)
        print(password)
        print(confirmpassword)
        if confirmpassword == password:
            data = Userdetails.query.filter_by(username=username).first()
            print(data)
            sno = int(str(data)[13:-1])
            user = Userdetails.query.get(sno)
            user.password = password
            db.session.commit()
            return redirect(url_for("login"))
        else:
            flash("😡 Confirm Password does not match with Password")
            return render_template("forgot.html")
    return render_template("forgot.html")

@app.route("/history",methods=["POST","GET"])
def history():
    if request.method == "POST" and "selm" in request.form:
        moviename = request.form.get("selm")
        return redirect(url_for('single', movie=moviename))
    if request.method == "POST" and "remove" in request.form:
        moviename = request.form["remove"]
        value1 = History.query.filter_by(username=session["username"]).all()
        for i in range(len(value1)):
            valueno = int(str(value1[i])[8:-1])
            value2 =  History.query.get(valueno)
            if value2.moviename == moviename:
                movie =  History.query.filter_by(sno=valueno).first()
                db.session.delete(movie)
                db.session.commit()
                break
    username = session["username"]
    data1 = History.query.filter_by(username=username).all()
    search_movies_name = []
    search_movies_posterpath = []
    search_date = []
    for i in range(len(data1)):
        print(str(data1[i]))
        sno = int(str(data1[i])[9:-1])
        data2 =  History.query.get(sno)
        search_movies_name.append(data2.moviename)
        search_movies_posterpath.append(data2.posterpath)
        search_date.append(data2.date)
    y = len(search_movies_name)
    return render_template("history.html",bookmarked_movies_name=search_movies_name,bookmarked_movies_posterpath=search_movies_posterpath,search_date=search_date,movie_list=movie_list,y=y)

app.run(debug=True)