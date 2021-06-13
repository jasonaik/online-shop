from flask import Flask, render_template, redirect, url_for, flash, abort, request, jsonify
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from typing import Callable
from functools import wraps
from flask_gravatar import Gravatar
from werkzeug.utils import secure_filename
import smtplib
from forms import ReviewForm, RegisterForm, LoginForm, UpdateReviewForm
import os
import stripe
import pandas as pd

stripe.api_key = os.environ.get("STRIPE_API_KEY")

SEND_EMAIL = "automatedemailproject@gmail.com"
PASSWORD = "passwordlol"
UPLOAD_FOLDER = "static/images"
FILENAME = None
CURRENT_PRODUCT = None
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
ckeditor = CKEditor(app)
Bootstrap(app)
gravatar = Gravatar(
    app, size=100, rating='g', default='retro', force_default=False, force_lower=False, use_ssl=False, base_url=None)

# CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL1", "sqlite:///shop.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


class MySQLAlchemy(SQLAlchemy):
    Column: Callable
    Integer: Callable
    String: Callable
    ForeignKey: Callable
    Boolean: Callable
    Text: Callable
    Float: Callable


db = MySQLAlchemy(app)
Base = declarative_base()


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), unique=True)
    password = db.Column(db.String(200))
    name = db.Column(db.String(1000))

    # This will act like a List of BlogPost objects attached to each User.
    # The "author" refers to the author property in the BlogPost class.
    reviews = relationship("Review", back_populates="review_author")
    user_cart = relationship("CartItem", back_populates="user")


class Review(db.Model):
    __tablename__ = "reviews"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    stars = db.Column(db.String(200), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    review_author = relationship("User", back_populates="reviews")
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"))
    parent_product = relationship("Product", back_populates="reviews")


class CartItem(db.Model):
    __tablename__ = "cart"
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"))
    product = relationship("Product", back_populates="cart")
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    user = relationship("User", back_populates="user_cart")


class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(1000), unique=True)
    price = db.Column(db.Float, nullable=False)
    main_image = db.Column(db.String(1000), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=False)
    specification = db.Column(db.Text, nullable=False)
    side_images = relationship("ProductImages", back_populates="parent_product")
    reviews = relationship("Review", back_populates="parent_product")
    cart = relationship("CartItem", back_populates="product")


class ProductImages(db.Model):
    __tablename__ = "product_images"
    id = db.Column(db.Integer, primary_key=True)
    image = db.Column(db.String(1000), unique=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"))
    parent_product = relationship("Product", back_populates="side_images")


class NewsletterEmails(db.Model):
    __tablename__ = "newsletter_emails"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), unique=True)


db.create_all()


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.id != 1:
            return abort(403)
        return f(*args, **kwargs)

    return decorated_function


@app.route('/register', methods=["GET", "POST"])
def register():
    item_num = 0
    if current_user.is_authenticated:
        user_cart = current_user.user_cart
        item_num = len(user_cart)
    form = RegisterForm()
    if form.validate_on_submit():

        if User.query.filter_by(email=form.email.data).first():
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))

        if form.password.data != form.confirm_password.data:
            flash("Password don't match!")
            return redirect(url_for("register"))

        hash_and_salted_password = generate_password_hash(
            form.password.data,
            method='pbkdf2:sha256',
            salt_length=8
        )
        new_user = User(
            email=form.email.data,
            name=form.name.data,
            password=hash_and_salted_password,
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for("home"))

    return render_template("register.html", form=form, current_user=current_user, item_num=item_num)


@app.route('/login', methods=["GET", "POST"])
def login():
    item_num = 0
    if current_user.is_authenticated:
        user_cart = current_user.user_cart
        item_num = len(user_cart)
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        user = User.query.filter_by(email=email).first()
        # Email doesn't exist or password incorrect.
        if not user:
            flash("That email does not exist, please try again.")
            return redirect(url_for('login'))
        elif not check_password_hash(user.password, password):
            flash('Password incorrect, please try again.')
            return redirect(url_for('login'))
        else:
            login_user(user)
            return redirect(url_for('home'))
    return render_template("login.html", form=form, current_user=current_user, item_num=item_num)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route("/")
def home():
    products = Product.query.all()
    item_num = 0
    if current_user.is_authenticated:
        user_cart = current_user.user_cart
        item_num = len(user_cart)
    return render_template("index.html", products=products, current_user=current_user, item_num=item_num)


@app.route("/add", methods=["GET", "POST"])
@login_required
@admin_only
def add_product():
    item_num = 0
    if current_user.is_authenticated:
        user_cart = current_user.user_cart
        item_num = len(user_cart)
    global FILENAME, CURRENT_PRODUCT
    # form = CreateProductForm()
    # if form.validate_on_submit():
    if request.method == "POST":
        for index in range(6):
            current_file = f"file{index}"
            if current_file is not None:
                if current_file not in request.files:
                    flash('No file part')
                    return redirect(request.url)
                file = request.files[current_file]
                if file.filename == '':
                    if current_file != 0:
                        break
                    else:
                        flash('No image selected for uploading')
                        return redirect(request.url)
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    if index == 0:
                        FILENAME = filename
                        new_product = Product(
                            name=request.form["name"],
                            price=request.form["price"],
                            description=request.form["desc"],
                            specification=request.form["specs"],
                            main_image=f"{FILENAME}"
                        )

                        CURRENT_PRODUCT = new_product

                        db.session.add(new_product)
                        db.session.commit()
                    else:
                        product_image = ProductImages(
                            image=filename,
                            parent_product=Product.query.get(CURRENT_PRODUCT.id)
                        )

                        db.session.add(product_image)
                        db.session.commit()

                else:
                    flash('Allowed image types are - png, jpg, jpeg')
                    return redirect(request.url)
            else:
                break

        return redirect(url_for("home"))

    return render_template("add.html", current_user=current_user, item_num=item_num)


@app.route("/edit/<int:product_id>", methods=["GET", "POST"])
@login_required
@admin_only
def edit_product(product_id):
    item_num = 0
    if current_user.is_authenticated:
        user_cart = current_user.user_cart
        item_num = len(user_cart)
    product_to_edit = Product.query.get(product_id)
    main_image = product_to_edit.main_image
    name = product_to_edit.name
    price = product_to_edit.price
    desc = product_to_edit.description
    specs = product_to_edit.specification
    supp_images = [image.image for image in product_to_edit.side_images]
    global FILENAME, CURRENT_PRODUCT
    if request.method == "POST":
        for index in range(6):
            current_file = f"file{index}"
            if current_file not in request.files:
                flash('No file part')
                return redirect(request.url)
            file = request.files[current_file]
            if file.filename == '':
                product_to_edit.name = request.form["name"]
                product_to_edit.price = request.form["price"]
                product_to_edit.description = request.form["desc"]
                product_to_edit.specification = request.form["specs"]

                db.session.commit()

            if file:
                if allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    if index == 0:
                        os.remove(f"static/images/{product_to_edit.main_image}")
                        product_to_edit.name = request.form["name"]
                        product_to_edit.description = request.form.get("ckeditor")
                        product_to_edit.main_image = filename

                        db.session.commit()
                    else:
                        product_images = product_to_edit.side_images
                        try:
                            os.remove(f"static/images/{product_images[index - 1].image}")
                            product_images[index - 1].image = filename

                            db.session.commit()
                        except IndexError:
                            product_image = ProductImages(
                                image=filename,
                                parent_product=product_to_edit
                            )

                            db.session.add(product_image)
                            db.session.commit()

                else:
                    flash('Allowed image types are - png, jpg, jpeg')
                    return redirect(request.url)

        return redirect(url_for("edit_product", product_id=product_id))

    return render_template(
        "edit.html",
        current_user=current_user,
        main_image=main_image,
        name=name,
        price=price,
        desc=desc,
        specs=specs,
        supp_images=supp_images,
        product_id=product_id, item_num=item_num)


@app.route("/delete/<int:product_id>")
@login_required
@admin_only
def delete_product(product_id):
    product_to_delete = Product.query.get(product_id)
    os.remove(f"static/images/{product_to_delete.main_image}")
    db.session.delete(product_to_delete)
    db.session.commit()

    for image in product_to_delete.side_images:
        os.remove(f"static/images/{image.image}")
        db.session.delete(image)
        db.session.commit()

    return redirect(url_for("home"))


# If I knew how to make it so that only customers who bought the product can review it, this would not be here.
@app.route("/delete/<int:product_id>/<int:review_id>")
@login_required
@admin_only
def delete_review(product_id, review_id):
    review_to_delete = Review.query.get(review_id)
    db.session.delete(review_to_delete)
    db.session.commit()

    return redirect(url_for("single", product_id=product_id))


@app.route("/product")
def product():
    item_num = 0
    if current_user.is_authenticated:
        user_cart = current_user.user_cart
        item_num = len(user_cart)
    products = Product.query.all()
    return render_template("product.html", products=products, current_user=current_user, item_num=item_num)


@app.route("/single/<product_id>", methods=["GET", "POST"], defaults={'increment': 0, 'current_num': 1})
@app.route("/single/<product_id>/<current_num>/<increment>", methods=["GET", "POST"])
def single(product_id, current_num, increment):
    item_num = 0
    if current_user.is_authenticated:
        user_cart = current_user.user_cart
        item_num = len(user_cart)
    requested_product = Product.query.get(product_id)

    total_stars = 0
    for review in requested_product.reviews:
        total_stars += len(review.stars)
    try:
        avg_stars = total_stars / len(requested_product.reviews)
    except ZeroDivisionError:
        avg_stars = -1

    for review in requested_product.reviews:
        if review.review_author == current_user:
            review_form = UpdateReviewForm(
                review_text=review.text,
                product_rating=review.stars
            )

            if review_form.validate_on_submit():
                if not current_user.is_authenticated:
                    flash("You need to login or register to write a review.")
                    return redirect(url_for("login"))

                review.text = review_form.review_text.data
                review.stars = review_form.product_rating.data

                db.session.commit()

                return redirect(url_for("single", product_id=product_id))

            return render_template(
                "single.html",
                product=requested_product,
                current_user=current_user,
                form=review_form,
                is_update=True,
                text=review.text,
                stars=review.stars,
                rating=avg_stars, item_num=item_num, increment=increment, current_num=current_num)

    review_form = ReviewForm()

    if review_form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to login or register to write a review.")
            return redirect(url_for("login"))

        new_review = Review(
            text=review_form.review_text.data,
            stars=review_form.product_rating.data,
            review_author=current_user,
            parent_product=requested_product
        )
        db.session.add(new_review)
        db.session.commit()

        return redirect(url_for("single", product_id=product_id))

    return render_template(
        "single.html",
        product=requested_product,
        current_user=current_user,
        form=review_form, rating=avg_stars, item_num=item_num, increment=0, current_num=current_num)


@app.route("/contact", methods=["GET", "POST"])
def contact():
    item_num = 0
    if current_user.is_authenticated:
        user_cart = current_user.user_cart
        item_num = len(user_cart)
    if request.method == "POST":

        if not current_user.is_authenticated:
            flash("You need to login or register to write a message or subscribe to the newsletter.")
            return redirect(url_for("login"))

        try:
            new_email = NewsletterEmails(
                email=request.form["news_email"]
            )
            db.session.add(new_email)
            db.session.commit()
            return redirect(url_for("contact"))

        except KeyError:
            subject = request.form['subject']
            fname = request.form['fname']
            lname = request.form['lname']
            email = request.form['email']
            message = request.form['message']
            with smtplib.SMTP("smtp.gmail.com") as connection:
                connection.starttls()
                connection.login(user=SEND_EMAIL, password=PASSWORD)
                connection.sendmail(
                    from_addr=SEND_EMAIL,
                    to_addrs=SEND_EMAIL,
                    msg=f"Subject: Sticks & Stones | {subject}\n\nThis is"
                        f" a Sticks & Stones customer message\n\n"
                        f"Name: {fname} {lname}\nEmail Address: {email}\n\n{message}")

            return redirect(url_for("contact"))

    return render_template("contact.html", current_user=current_user, item_num=item_num)


@app.route("/search", methods=["GET", "POST"])
def search():
    item_num = 0
    if current_user.is_authenticated:
        user_cart = current_user.user_cart
        item_num = len(user_cart)
    if request.method == "POST":
        search_text = request.form["search_text"]
        products = Product.query.all()
        searched_products = []
        for product_ in products:
            if search_text.lower() in product_.name.lower():
                searched_products.append(product_)
        return render_template(
            "search.html",
            current_user=current_user, products=searched_products, search_text=search_text, item_num=item_num)


@app.route("/services")
def services():
    item_num = 0
    if current_user.is_authenticated:
        user_cart = current_user.user_cart
        item_num = len(user_cart)
    return render_template("services.html", current_user=current_user, item_num=item_num)


@app.route("/about")
def about():
    item_num = 0
    if current_user.is_authenticated:
        user_cart = current_user.user_cart
        item_num = len(user_cart)
    return render_template("about.html", current_user=current_user, item_num=item_num)


@app.route("/cart-add/<product_id>/<location>/<num>")
def add_to_cart(product_id, location, num):
    if not current_user.is_authenticated:
        flash("You need to login or register to perform this action.")
        return redirect(url_for("login"))
    requested_product = Product.query.get(product_id)

    for _ in range(int(num)):
        cart_item = CartItem(
            product=requested_product,
            user=current_user,
        )

        db.session.add(cart_item)
        db.session.commit()

    return redirect(url_for(f"{location}", product_id=product_id))


@app.route("/cart-delete-all/<cart_item_name>/")
def delete_all_from_cart(cart_item_name):
    if not current_user.is_authenticated:
        flash("You need to login or register to perform this action.")
        return redirect(url_for("login"))
    for item in current_user.user_cart:
        if item.product.name == cart_item_name:
            cart_item = item
            db.session.delete(cart_item)
            db.session.commit()

    return redirect(url_for("cart"))


@app.route("/cart-delete/<cart_item_name>")
def delete_from_cart(cart_item_name):
    if not current_user.is_authenticated:
        flash("You need to login or register to perform this action.")
        return redirect(url_for("login"))
    for item in current_user.user_cart:
        if item.product.name == cart_item_name:
            cart_item = item
            db.session.delete(cart_item)
            db.session.commit()
            break

    return redirect(url_for("cart"))


@app.route("/cart")
def cart():
    item_num = 0
    if current_user.is_authenticated:
        user_cart = current_user.user_cart
        item_num = len(user_cart)

        item_names = [item.product.name for item in user_cart if item.product is not None]
        df = pd.Series(item_names).value_counts()

        item_dict = df.to_dict()

        for item in item_dict:
            item_product = Product.query.filter_by(name=item).first()
            item_dict[item] = {
                "num": int(item_dict[item]),
                "image": item_product.main_image,
                "name": item_product.name,
                "price": item_product.price * int(item_dict[item]),
            }
        return render_template("checkout.html", item_num=item_num, items=item_dict, Product=Product)

    else:
        return render_template("checkout.html", item_num=item_num)


@app.route("/success")
@login_required
def success():
    return render_template("success.html")


@app.route("/cancel")
@login_required
def cancel():
    return render_template("cancel.html")


@app.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    user_cart = current_user.user_cart

    item_names = [item.product.name for item in user_cart if item.product is not None]
    df = pd.Series(item_names).value_counts()

    item_dict = df.to_dict()

    for item in item_dict:
        item_product = Product.query.filter_by(name=item).first()
        item_dict[item] = {
            "num": int(item_dict[item]),
            "name": item_product.name,
            "price": int(item_product.price * 100),
        }

    json_payload = []
    for item in item_dict:
        json_element = {
                    'price_data': {
                        'currency': 'usd',
                        'unit_amount': item_dict[item]["price"],
                        'product_data': {
                            'name': item_dict[item]["name"],
                            'images': [],
                        },
                    },
                    'quantity': item_dict[item]["num"],
                }
        json_payload.append(json_element)

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=json_payload,
            mode='payment',
            success_url='https://sticks-and-stones-shop.herokuapp.com/success',
            cancel_url='https://sticks-and-stones-shop.herokuapp.com/cancel',
        )
        return jsonify({'id': checkout_session.id})
    except Exception as e:
        return jsonify(error=str(e)), 403


if __name__ == "__main__":
    app.run(host="localhost", port=5000)
