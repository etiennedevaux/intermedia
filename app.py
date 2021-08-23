from datetime import datetime
import os
from flask import (
    Flask, flash, render_template,
    redirect, request, session, url_for)
from flask_pymongo import DESCENDING, PyMongo
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
if os.path.exists("env.py"):
    import env


app = Flask(__name__)

app.config["MONGO_DBNAME"] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.secret_key = os.environ.get("SECRET_KEY")

mongo = PyMongo(app)

def data_refresh(flter):
    global categories, recipes, categoriesinuse
    categories = mongo.db.categories.find().sort("sequence", 1)
    categoriesinuse = mongo.db.recipes.distinct('category_name')
    recipes = list(mongo.db.recipes.find(flter).sort("upload_date", -1))
   
    for recipe in recipes:
        try: 
            recipe['family_name'] = mongo.db.users.find_one({"username": recipe["created_by"]})["family_name"]
        except:
            recipe['family_name'] = "Unknown"
        try:
            recipe['given_name'] = mongo.db.users.find_one({"username": recipe["created_by"]})["given_name"]
        except:
            recipe['given_name'] = "User"
        try:
            recipe['profile_image'] = mongo.db.users.find_one({"username": recipe["created_by"]})["profile_image"]
        except:
            recipe['profile_image'] = "../static/images/avatar.jpg"
        try: 
            recipe['about_me'] = mongo.db.users.find_one({"username": recipe["created_by"]})["about_me"]
        except:
            recipe['about_me'] ="No Description"

 
# https://www.geeksforgeeks.org/python-404-error-handling-in-flask/
@app.errorhandler(404)
def not_found(e):
    flash(e)
    return render_template("404.html")


@app.route("/")
@app.route("/get_recipes/")
def get_recipes():
    data_refresh({"upload_date":{"$ne": None}})
    return render_template("recipes.html", recipes=recipes, categoriesinuse=categoriesinuse)

@app.route("/get_filtered_recipes", methods=["GET", "POST"])
def get_filtered_recipes():
    cat_fil = request.form.get("category_filter")
    if cat_fil == "All":
        dataqry={"upload_date":{"$ne": None}}
    else:
        dataqry={"$and": [{"upload_date":{"$ne": None}},{"category_name":str(cat_fil)}]}
    data_refresh(dataqry)
    return render_template("recipes.html", recipes=recipes, categoriesinuse=categoriesinuse)

@app.route("/search", methods=["GET", "POST"])
def search():
    query = request.form.get("query")
    return render_template("recipes.html", recipes=recipes)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # check if username already exists in db
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})

        if existing_user:
            flash("Username already exists")
            return redirect(url_for("register"))

        register = {
            "username": request.form.get("username").lower(),
            "password": generate_password_hash(request.form.get("password")),
            "family_name": request.form.get("family-name"),
            "given_name": request.form.get("given-name"),
            "about_me": request.form.get("about_me"),
            "profile_image": request.form.get("profile-image")
        }
        mongo.db.users.insert_one(register)

        # put the new user into 'session' cookie
        session["user"] = request.form.get("username").lower()
        flash("Registration Successful")
        return redirect(url_for("profile", username=session["user"]))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # check if username exists in db
        existing_user = mongo.db.users.find_one_or_404(
            {"username": request.form.get("username").lower()})

        if existing_user:
            # ensure hashed password matches user input
            if check_password_hash(
                    existing_user["password"], request.form.get("password")):
                        session["user"] = request.form.get("username").lower()
                        flash("Welcome " + existing_user['given_name'])
                        return redirect(url_for("profile", username=session["user"]))
            else:
                # invalid password match
                flash("Incorrect Username and/or Password")
                return redirect(url_for("login"))

        else:
            # username doesn't exist
            flash("Incorrect Username")
            return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/profile/", methods=["GET", "POST"])
def profile():
    # grab the session user's username from db
    
    if  "user" in session:
        userprofile = mongo.db.users.find_one_or_404({"username": session["user"]})
        return render_template("profile.html", userprofile=userprofile)

    return redirect(url_for("login"))


@app.route("/logout")
def logout():
    # remove user from session cookie
    flash("You have been logged out")
    session.pop("user")
    return redirect(url_for("login"))


@app.route("/add_recipe", methods=["GET", "POST"])
def add_recipe():
    data_refresh({"upload_date":{"$ne": None}})
    if request.method == "POST":
        
        recipe = {
            "category_name": request.form.get("category_name"),
            "recipe_name": request.form.get("recipe_name"),
            "recipe_description": request.form.get("recipe_description"),
            "recipe_ingredients": request.form.get("recipe_ingredients"),
            "recipe_equipment": request.form.get("recipe_equipment"),
            "recipe_image": request.form.get("recipe_image"),
            "upload_date": datetime.today().strftime("%Y-%m-%d"),
            "created_by": session["user"]
        }
        mongo.db.recipes.insert_one(recipe)
        data_refresh({"upload_date":{"$ne": None}})
        flash("Recipe Successfully Added")
        return redirect(url_for("get_recipes"))


    return render_template("add_recipe.html", categories=categories)


@app.route("/edit_recipe/<recipe_id>", methods=["GET", "POST"])
def edit_recipe(recipe_id):
    if "user" not in session:
        return redirect(url_for("login"))

    recipe = mongo.db.recipes.find_one_or_404({"_id": ObjectId(recipe_id)})
    data_refresh({"upload_date":{"$ne": None}})
    if request.method == "POST":
        submit = {
            "category_name": request.form.get("category_name"),
            "recipe_name": request.form.get("recipe_name"),
            "recipe_description": request.form.get("recipe_description"),
            "recipe_ingredients": request.form.get("recipe_ingredients"),
            "recipe_equipment": request.form.get("recipe_equipment"),
            "recipe_instructions": request.form.get("recipe_instructions"),
            "recipe_image": request.form.get("recipe_image"),
            "upload_date": datetime.today().strftime("%Y-%m-%d"),
            "created_by": session["user"]
        }
        mongo.db.recipes.update({"_id": ObjectId(recipe_id)}, submit)
        flash("Recipe Successfully Updated")
        data_refresh({"upload_date":{"$ne": None}})
        return render_template("recipes.html", recipes=recipes, categoriesinuse=categoriesinuse)
        
    
    
    return render_template("edit_recipe.html", recipe=recipe, categories=categories)

@app.route("/user_admin/<user_id>", methods=["GET", "POST"])
def user_admin(user_id):
    data_refresh({"upload_date":{"$ne": None}})
    useradmin=mongo.db.users.find_one({"_id": ObjectId(user_id)}) 
    if request.method == "POST":
        submit = {
            "username": request.form.get("username").lower(),
            "family_name": request.form.get("family_name"),
            "given_name": request.form.get("given_name"),
            "about_me": request.form.get("about_me"),
            "profile_image": request.form.get("profile_image"),
            "password": useradmin["password"]
        }
        mongo.db.users.update({"_id": ObjectId(user_id)}, submit)
        flash("User Successfully Updated")
        data_refresh({"upload_date":{"$ne": None}})
        users=mongo.db.users.find().sort("username", 1)
        return render_template("users.html", users=users)

    useradmin=mongo.db.users.find_one({"_id": ObjectId(user_id)})      
    return render_template("user_admin.html", useradmin=useradmin)

@app.route("/edit_user/",  methods=["GET", "POST"])
def edit_user():

    # grab the session user's username from db
    userprofile = mongo.db.users.find_one({"username": session["user"]})
    data_refresh({"upload_date":{"$ne": None}})
    if request.method == "POST":
        submit = {"$set":{
            "given_name": request.form.get("given_name"),
            "family_name": request.form.get("family_name"),
            "about_me": request.form.get("about_me"),
            "password": userprofile["password"],
            "profile_image": request.form.get("profile_image"),
            "username": session["user"]
        }}
        mongo.db.users.update_one({"username": session["user"]}, submit)
        flash("Profile Successfully Updated")
        userprofile = mongo.db.users.find_one({"username": session["user"]})
        data_refresh({"upload_date":{"$ne": None}})
        return render_template("profile.html", userprofile=userprofile)
        
    return render_template("edit_user.html",userprofile=userprofile)
        
 
@app.route("/delete_recipe/<recipe_id>")
def delete_recipe(recipe_id):
    mongo.db.recipes.delete_one({"_id": ObjectId(recipe_id)})
    flash("Recipe Successfully Deleted")
    return redirect(url_for("get_recipes"))

@app.route("/delete_user/<user_id>")
def delete_user(user_id):
    mongo.db.users.delete_one({"_id": ObjectId(user_id)})
    flash("User Successfully Deleted")
    return redirect(url_for("get_users"))


@app.route("/get_categories")
def get_categories():
    categories = list(mongo.db.categories.find().sort("category_name", 1))
    return render_template("categories.html", categories=categories)

@app.route("/get_users")
def get_users():
    users = list(mongo.db.users.find().sort("username", 1))
    return render_template("users.html", users=users)


@app.route("/add_category", methods=["GET", "POST"])
def add_category():
    if request.method == "POST":
        category = {
            "category_name": request.form.get("category_name")
        }
        mongo.db.categories.insert_one(category)
        flash("New Category Added")
        return redirect(url_for("get_categories"))

    return render_template("add_category.html")


@app.route("/edit_category/<category_id>", methods=["GET", "POST"])
def edit_category(category_id):
    data_refresh({"upload_date":{"$ne": None}})
    if request.method == "POST":
        submit = {
            "category_name": request.form.get("category_name")
        }
        mongo.db.categories.update({"_id": ObjectId(category_id)}, submit)
        flash("Category Successfully Updated")
        return redirect(url_for("get_categories"))

    category = mongo.db.categories.find_one({"_id": ObjectId(category_id)})
    return render_template("edit_category.html", category=category)


@app.route("/delete_category/<category_id>")
def delete_category(category_id):
    mongo.db.categories.remove({"_id": ObjectId(category_id)})
    flash("Category Successfully Deleted")
    return redirect(url_for("get_categories"))


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=True)

