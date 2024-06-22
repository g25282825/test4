from flask import url_for
from markupsafe import escape
from flask import Flask, render_template, request, url_for, redirect, flash
from flask_sqlalchemy import SQLAlchemy
import click
import os
import sys
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from waitress import serve

WIN = sys.platform.startswith('win')
if WIN:  # 如果是 Windows 系统，使用三个斜线
    prefix = 'sqlite:///'
else:  # 否则使用四个斜线
    prefix = 'sqlite:////'

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev'
app.config['SQLALCHEMY_DATABASE_URI'] = prefix + os.path.join(app.root_path, 'data.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # 关闭对模型修改的监控

db = SQLAlchemy(app)
login_manager = LoginManager(app)
app.app_context().push()

@login_manager.user_loader
def load_user(user_id):
    user = User.query.get(int(user_id))
    return user



class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20))
    username = db.Column(db.String(20))
    password_hash = db.Column(db.String(128))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def validate_password(self, password):
        return check_password_hash(self.password_hash, password)

class Movie(db.Model):  # 表名将会是 movie
    id = db.Column(db.Integer, primary_key=True)  # 主键
    username = db.Column(db.String(20))
    title = db.Column(db.String(60))  # 电影标题
    year = db.Column(db.String(4))  # 电影年份

@app.cli.command()  # 注册为命令，可以传入 name 参数来自定义命令
@click.option('--drop', is_flag=True, help='Create after drop.')  # 设置选项
def initdb(drop):
    """Initialize the database."""
    if drop:  # 判断是否输入了选项
        db.drop_all()
    db.create_all()
    click.echo('Initialized database.')  # 输出提示信息

'''
@app.cli.command()
@click.option('--username', prompt=True, help='The username used to login.')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='The password used to login.')
def createuser(username, password):
    """Create user."""
    db.create_all()
    
    click.echo('Creating user...')
    user = User(username=username, name='Admin')
    user.set_password(password)
    db.session.add(user)

    db.session.commit()
    click.echo('Done.')
'''

@app.cli.command()
def forge():
    """Generate fake data."""
    db.create_all()

    # 全局的两个变量移动到这个函数内
    name = 'Grey Li'
    movies = [
        {'username': 'a', 'title': 'My Neighbor Totoro', 'year': '1988'},
        {'username': 'a', 'title': 'Dead Poets Society', 'year': '1989'},
        {'username': 'a', 'title': 'A Perfect World', 'year': '1993'},
        {'username': 'a', 'title': 'Leon', 'year': '1994'},
        {'username': 'a', 'title': 'Mahjong', 'year': '1996'},
        {'username': 'b', 'title': 'Swallowtail Butterfly', 'year': '1996'},
        {'username': 'b', 'title': 'King of Comedy', 'year': '1999'},
        {'username': 'b', 'title': 'Devils on the Doorstep', 'year': '1999'},
        {'username': 'b', 'title': 'WALL-E', 'year': '2008'},
        {'username': 'b', 'title': 'The Pork of Music', 'year': '2012'},
    ]

    gen_pass = generate_password_hash('a')

    user = User(name=name, username= 'a', password_hash = gen_pass)
    db.session.add(user)
    for m in movies:
        movie = Movie(username= m['username'], title=m['title'], year=m['year'])
        db.session.add(movie)

    db.session.commit()
    click.echo('Done.')

@app.route('/debug')
def usershow():
    user_id = current_user.id
    #return f"当前用户的ID是：{user_id}"
    #movie = Movie.query.filter_by(year = '1988').first()
    movie = Movie.query.first()
    movietitle = movie.title
    movietitle = movie.username
    return f"movie title是：{movietitle}"

@app.route('/user/<name>')
def user_page(name):
    return f'User: {escape(name)}'

@app.context_processor
def inject_user():
    user = User.query.first()
    return dict(user=user)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.route('/', methods=['GET', 'POST'])
def index():
    
    if request.method == 'POST':
        if not current_user.is_authenticated:
            return redirect(url_for('index'))
        

        title = request.form['title']
        year = request.form['year']

        if not title or not year or len(year) > 4 or len(title) > 60:
            flash('Invalid input.')
            return redirect(url_for('index'))

        movie = Movie(username=current_user.username, title=title, year=year)
        db.session.add(movie)
        db.session.commit()
        flash('Item created.')
        return redirect(url_for('index'))
    
    if not current_user.is_authenticated:
        movies = Movie.query.all()
    else:
        user_name = current_user.username
        movies = Movie.query.filter_by(username = user_name).all()
    
    return render_template('index.html', movies=movies)

@app.route('/movie/edit/<int:movie_id>', methods=['GET', 'POST'])
@login_required
def edit(movie_id):
    movie = Movie.query.get_or_404(movie_id)

    if request.method == 'POST':
        title = request.form['title']
        year = request.form['year']

        if not title or not year or len(year) > 4 or len(title) > 60:
            flash('Invalid input.')
            return redirect(url_for('edit', movie_id=movie_id))

        movie.username = current_user.username
        movie.title = title
        movie.year = year
        db.session.commit()
        flash('Item updated.')
        return redirect(url_for('index'))

    return render_template('edit.html', movie=movie)


@app.route('/movie/delete/<int:movie_id>', methods=['POST'])
@login_required
def delete(movie_id):
    movie = Movie.query.get_or_404(movie_id)
    db.session.delete(movie)
    db.session.commit()
    flash('Item deleted.')
    return redirect(url_for('index'))


@app.route('/base')
def gofor_base():
    return render_template('base.html')

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        name = request.form['name']

        if not name or len(name) > 20:
            flash('Invalid input.')
            return redirect(url_for('settings'))

        user = User.query.first()
        user.name = name
        db.session.commit()
        flash('Settings updated.')
        return redirect(url_for('index'))

    return render_template('settings.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not username or not password:
            flash('Invalid input.')
            return redirect(url_for('login'))

        user = User.query.filter_by(username=username).first()

        if username == user.username and user.validate_password(password):
            login_user(user)
            flash('Login success.')
            return redirect(url_for('index'))

        flash('Invalid username or password.')
        return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not username or not password:
            flash('Invalid input.')
            return redirect(url_for('register'))

        user = User.query.filter_by(username=username).first()

        if not user:
            flash('Register success.')
            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            return redirect(url_for('login'))
        else:
            flash('Repeat usename.')
            return redirect(url_for('register'))

    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Goodbye.')
    return redirect(url_for('index'))

'''
if __name__ == '__main__':
    app.run()
'''


if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=8080)    
