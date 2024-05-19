import requests.cookies
from functools import wraps
from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import datetime as dt
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from flask_gravatar import Gravatar
from forms import CreatePostForm, RegisterUser, LogIn, Comment
from smtplib import SMTP
from os import environ

sender = "pythontest122@outlook.com"
sender_pass = "knsp2793"
receiver = "aadikeshu2305@gmail.com"

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)
login_manager = LoginManager()
login_manager.init_app(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(user_id)


gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("user_info.id"))
    author = relationship("Users", back_populates="posts")
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    comments = relationship("Comments", back_populates="parent_post")


class Users(UserMixin, db.Model):
    __tablename__ = "user_info"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250))
    email = db.Column(db.String(250), unique=True)
    password = db.Column(db.String(250))
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comments", back_populates="user")


class Comments(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user_info.id"))
    user = relationship("Users", back_populates="comments")
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    parent_post = relationship("BlogPost", back_populates="comments")
    text = db.Column(db.String(512))


with app.app_context():

    year = dt.now().year

    def admin_only(function):
        @wraps(function)
        def wrapper_fun(*args, **kwargs):
            if not current_user or Users.query.filter_by(id=current_user.id).first() != Users.query.filter_by(id=1).first():
                abort(403)
            else:
                return function(*args, **kwargs)
        return wrapper_fun

    @app.route('/')
    def get_all_posts():
        posts = BlogPost.query.all()
        return render_template("index.html", all_posts=posts, logged_in=current_user.is_authenticated, year=year)


    @app.route('/register', methods=['GET', 'POST'])
    def register():
        form = RegisterUser()
        if form.validate_on_submit():
            email = form.email.data
            password = generate_password_hash(password=form.password.data, method="pbkdf2:sha256", salt_length=8)
            name = form.name.data
            user = Users.query.filter_by(email=email).first()
            if user:
                flash("User already exists, Log In instead!")
                return redirect(url_for('login'))
            else:
                user = Users(
                    name=name,
                    email=email,
                    password=password
                )
                db.session.add(user)
                db.session.commit()
                login_user(user)
                return redirect(url_for('get_all_posts'))

        elif request.method == 'GET':
            return render_template("register.html", form=form, logged_in=current_user.is_authenticated, year=year)


    @app.route('/login', methods=['POST', 'GET'])
    def login():
        form = LogIn()
        if form.validate_on_submit():
            user = Users.query.filter_by(email=form.email.data).first()
            password = form.password.data
            if user and check_password_hash(pwhash=user.password, password=password):
                login_user(user)
                return redirect(url_for('get_all_posts'))
            elif not user:
                flash("There is no account with that email, Register with a new account.")
                return redirect(url_for('login'))
            else:
                flash("Incorrect Password. Try Again")
                return redirect(url_for('login'))
        elif request.method == 'GET':
            return render_template("login.html", form=form, logged_in=current_user.is_authenticated, year=year)


    @app.route('/logout')
    def logout():
        logout_user()
        return redirect(url_for('get_all_posts'))


    @app.route("/post/<int:post_id>", methods=["POST", "GET"])
    def show_post(post_id):
        form = Comment()
        requested_post = db.session.query(BlogPost).get(post_id)
        comments = Comments.query.all()
        if form.validate_on_submit():
            if current_user.is_authenticated:
                comment = form.comment.data
                comment_ = Comments(
                    text=comment,
                    user=current_user,
                    parent_post=requested_post
                )
                db.session.add(comment_)
                db.session.commit()
                return redirect(url_for('show_post', post_id=post_id))
            else:
                flash("You need to be logged in to comment")
                return redirect(url_for('show_post', post_id=post_id))
        return render_template("post.html", post=requested_post, logged_in=current_user.is_authenticated, form=form, comments=comments, year=year)


    @app.route("/about")
    def about():
        return render_template("about.html", logged_in=current_user.is_authenticated, year=year)


    @app.route("/contact", methods=["POST", "GET"])
    def contact():
        if request.method == "POST":
            print(True)
            name = request.form["name"]
            email = request.form["email"]
            phone = request.form['phone']
            message = request.form['message']
            with SMTP(host="smtp-mail.outlook.com", port=587) as connection:
                connection.starttls()
                connection.login(user=sender, password=sender_pass)
                connection.sendmail(
                    from_addr=sender,
                    to_addrs=receiver,
                    msg=f"Subject: New message from Blog! \n\nname: {name}\nemail: {email}\nphone: {phone}\nmessage: {message}"
                )
            flash("Message successfully sent")
            return redirect(url_for('contact'))
        elif request.method == "GET":
            print(True)
            return render_template("contact.html", logged_in=current_user.is_authenticated, year=year)


    @app.route("/new-post", methods=['GET', 'POST'])
    @admin_only
    def add_new_post():
        edit = False
        form = CreatePostForm()
        if form.validate_on_submit():
            new_post = BlogPost(
                title=form.title.data,
                subtitle=form.subtitle.data,
                body=form.body.data,
                author=current_user,
                date=dt.now().strftime("%B %d, %Y")
            )
            db.session.add(new_post)
            db.session.commit()
            return redirect(url_for("get_all_posts"))

        elif request.method == 'GET':
            return render_template("make-post.html", form=form, logged_in=current_user.is_authenticated, edit=edit, year=year)


    @app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
    @admin_only
    def edit_post(post_id):
        edit = True
        post = BlogPost.query.get(post_id)
        edit_form = CreatePostForm(
            title=post.title,
            subtitle=post.subtitle,
            author=post.author,
            body=post.body
        )
        if edit_form.validate_on_submit():
            post.title = edit_form.title.data
            post.subtitle = edit_form.subtitle.data
            post.author.name = edit_form.author.data
            post.body = edit_form.body.data
            db.session.commit()
            return redirect(url_for("show_post", post_id=post.id))

        elif request.method == 'GET':
            return render_template("make-post.html", form=edit_form, logged_in=current_user.is_authenticated, edit=edit, year=year)


    @app.route("/delete/<int:post_id>")
    @admin_only
    def delete_post(post_id):
        post_to_delete = BlogPost.query.get(post_id)
        db.session.delete(post_to_delete)
        db.session.commit()
        return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
