from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_from_directory
import flask_login
from forms import *
import json
import os
import model
import flask

from bokeh.resources import INLINE

resources = INLINE
js_resources = resources.render_js()
css_resources = resources.render_css()


# config
SECRET_KEY = 'secret'
USERNAME = 'admin'
PASSWORD = 'default'

app = Flask(__name__)
app.config.from_object(__name__)
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

config = model.get_config_paths()

class User(flask_login.UserMixin):
    pass


@login_manager.user_loader
def load_user(user_id):
    users = model.get_from_users(user_id)
    if not users:
        return None
    user = User()
    user.id = users[0][0]
    user.name = users[0][1]
    flask_login.login_user(user) # , remember=True)
    return user


@app.route('/')
def home():
    if flask_login.current_user.is_authenticated:
        sedm_dict = model.get_homepage(flask_login.current_user.id,
                                       flask_login.current_user.name)

        return render_template('sedm.html', sedm_dict=sedm_dict)
    else:
        return redirect('login')


@app.route('/request', methods=['GET', 'POST'])
def requests():
    form = AddFixedRequest()

    # 1. If the request method is of type post then we expect this to be a
    #    submission.
    if request.method == 'POST':
        content = request.form
        req_dict, form = model.process_request_form(content, form,
                                                    flask_login.current_user.id)
        req_dict['message'] = req_dict['message'].replace("--", "<br>")

        return render_template('request.html', req_dict=req_dict, form=form)

    # 2. We should also be able to handle request that are of type json for
    #    automated ingestion.
    if request.is_json:
        content = json.loads(request.get_json())
    else:
        content = request.args.to_dict(flat=False)

    req_dict, form = model.get_request_page(flask_login.current_user.id,
                                            form,
                                            content=content)

    return render_template('request.html', req_dict=req_dict, form=form)


@app.route('/add_csv', methods=['GET', 'POST'])
def add_csv():
    form = AddCSVRequest()

    # 1. If the request method is of type post then we expect this to be a
    #    submission.
    if request.method == 'POST':
        content = request.form
        req_dict, form = model.process_add_csv(content, form,
                                               flask_login.current_user.id)

        req_dict['message'] = req_dict['message'].replace("--", "<br>")

        return render_template('add_csv.html', req_dict=req_dict, form=form)

    # 2. We should also be able to handle request that are of type json for
    #    automated ingestion.
    if request.is_json:
        content = json.loads(request.get_json())
    else:
        content = request.args.to_dict(flat=False)

    # 3. Generate the webpage dictionary if no POST or JSON request
    req_dict, form = model.get_add_csv(flask_login.current_user.id, form,
                                       content=content)

    return render_template('add_csv.html', req_dict=req_dict, form=form)


@app.route('/data_access/<path:instrument>', methods=['GET'])
@flask_login.login_required
def data_access(instrument):
    # 1. If the request method is of type post then we expect this to be a
    #    submission.
    if request.is_json:
        content = json.loads(request.get_json())
    else:
        content = request.args.to_dict(flat=False)

    content['user_id'] = flask_login.current_user.id
    content['camera_type'] = instrument.lower()
    out = model.get_science_products(**content)
    print(out)
    return render_template('view_data.html', sedm_dict=out)


@app.route('/data/<path:filename>')
@flask_login.login_required
def data_static(filename):
    '''
     Get files from the archive
    :param filename:
    :return:
    '''
    _p, _f = os.path.split(filename)

    if _f.startswith('finder') and 'ACQ' in _f:
        return send_from_directory(os.path.join(config['path']['path_phot'], _p, 'finders'), _f)
    elif _f.startswith('rc') or _f.startswith('finder') or 'ACQ' in _f:
        return send_from_directory(os.path.join(config['path']['path_phot'], _p), _f)
    else:
        return send_from_directory(os.path.join(config['path']['path_archive'], _p), _f)


@app.route('/weather_stats', methods=['GET', 'POST'])
def weather_stats():

    # 1. If the request method is of type post then we expect this to be a
    #    submission.
    if request.is_json:
        content = json.loads(request.get_json())
    else:
        content = request.args.to_dict(flat=True)

    out = model.get_weather_stats(**content)
    out['js_resources'] = INLINE.render_js()
    out['css_resources'] = INLINE.render_css()
    return render_template('weather_stats.html', sedm_dict=out)


@app.route('/objects', methods=['GET', 'POST'])
def objects():
    #form = AddFixedRequest()
    return render_template('sedm_base.html')


@app.route('/project_stats', methods=['GET', 'POST'])
def project_stats():
    #form = AddFixedRequest()
    return render_template('sedm_base.html')


@app.route('/scheduler', methods=['GET', 'POST'])
def scheduler():
    table = model.get_schedule()
    return render_template('scheduler.html', sedm_dict={'schedulerTable': table})


@app.route('/search/get_objects', methods=['GET', 'POST'])
def get_object():

    if request.is_json:
        content = json.loads(request.get_json())
    elif request.method == 'POST':
        content = request.form.to_dict(flat=False)
    else:
        content = request.args.to_dict(flat=False)

    out = model.get_object_info(**content)
    return jsonify(out)

@app.route('/search/get_object_values', methods=['GET', 'POST'])
def get_object_values():

    if request.is_json:
        content = json.loads(request.get_json())
    elif request.method == 'POST':
        content = request.form.to_dict(flat=False)
    else:
        content = request.args.to_dict(flat=False)

    out = model.get_object_values(content['id'])

    return jsonify(out)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        # Login and validate the user.index
        # user should be an instance of your `User` class
        username = form.username.data
        password = form.password.data

        ret = model.check_login(username, password)
        if ret[0]:
            user = User()
            user.id, username = [ret[1], username]
            flask_login.login_user(user)
            flash("Logged in as %s" % username)
            return redirect(url_for('home'))
        else:
            return render_template('login.html', message=ret[1], form=form)

    return render_template('login.html',  form=form)


@app.route("/logout")
@flask_login.login_required
def logout():
    flask_login.logout_user()
    return redirect(url_for('login'))


@app.route('/manage_user', methods=['GET', 'POST'])
@flask_login.login_required
def manage_user():

    if flask_login.current_user.name != 'SEDM_admin':
        return redirect(flask.url_for('index'))

    message = ""
    form1 = SearchUserForm()
    form2 = UsersForm()

    old_groups = []
    new_groups = []
    allocations =[]

    #Case with no user at all
    if len(flask.request.args) ==0:
        message = "Introduce the search criteria for your user. For exact search try \"."


        return (render_template('manage_users.html', form1=form1, from2=form2, message=message))

    #Case with when we want to search for a specific user
    if 'search_user' in flask.request.form:
        username = form1.search_string.data
    elif('user' in flask.request.args):    
        username = flask.request.args['user']
    elif (form2.username.data):
        username = form2.username.data
        #username.replace("'", "").replace('"', '')
        #username = '"{0}"'.format(username)
    else:
        username = ''

    u = model.get_info_user(username)
    message = u["message"]


    if username =="" or not "username" in u.keys():

        form2.old_groups.choices = []
        form2.new_groups.choices = []

        if 'add_user' in flask.request.form:

            name = form2.name.data
            email = form2.email.data
            new_password = form2.pass_new.data
            new_password_conf = form2.pass_conf.data


            if form2.pass_new.data and new_password ==new_password_conf:
                status, mes = db.add_user({"username":username, "name":name, "email":email, "password":new_password})
                if status ==0:
                    flash("User created")
                else:
                    message = mes
            else:
                message = "New user requires a password!"

            return (render_template('manage_users.html', form1=form1, form2=form2, allocations=[], message=message))

        else:
            return (render_template('manage_users.html', form1=form1, form2=form2, allocations=[], message=message))
    else:
        form2.old_groups.choices = [(g[0], g[0]) for g in u["old_groups"]]
        form2.new_groups.choices = [(g[0], g[0]) for g in u["new_groups"]]
        allocations = u["allocations"]


    if 'search_user' in flask.request.form and form1.validate_on_submit():
        form2.username.data = u["username"]
        form2.name.data = u["name"]
        form2.email.data = u["email"]

    elif 'add_group' in flask.request.form :
        username = form2.username.data
        #username.replace("'", "").replace('"', '')
        #u = model.get_info_user(username)#'"{0}"'.format(username))
        u = model.get_info_user('"{0}"'.format(username))
        message = u["message"]

        g = flask.request.form['new_groups']
        model.add_group(u["id"], g)
        message = "Added group for user %s"%(form2.username.data)

    elif 'remove_group' in flask.request.form:

        username = form2.username.data
        #username.replace("'", "").replace('"', '')
        #u = model.get_info_user(username)#'"{0}"'.format(username))
        u = model.get_info_user('"{0}"'.format(username))
        message = u["message"]
        g = flask.request.form['old_groups']
        model.remove_group(u["id"], g)
        message = "Deleted group for user %s"%form2.username.data

    elif 'modify_user' in flask.request.form and form2.validate_on_submit():
        username = form2.username.data
        u = model.get_info_user('"{0}"'.format(form2.username.data))
        #u = model.get_info_user(username) #'"{0}"'.format(form2.username.data))
        message = u["message"]

        name = form2.name.data
        email = form2.email.data
        new_password = form2.pass_new.data
        new_password_conf = form2.pass_conf.data

        status, mes = db.update_user({'id': u["id"], 'name':name, 'email':email})  
        flash("User with username %s updated with name %s, email %s. %s"%(username, name, email, mes))   

        #If there is any infoirmation in the password field, we update
        if form2.pass_new.data:
            db.update_user({'id': u["id"], 'password': new_password})
            flash("Password changed ")
    elif 'delete_user' in flask.request.form and form2.name.data:

        username = form2.username.data
        u = model.get_info_user(username)

        if 'username' in u.keys():
            status, mes = db.remove_user({'id': u["id"]})  
            flash("Deleted user with username %s. %s"%(username, mes))   
            return (render_template('manage_users.html', form1=form1, form2=None, allocations=[], message=message))

    else:
        print ("NOTHING TO BE DONE")
        pass

    u = model.get_info_user(username)
    form2.old_groups.choices = [(g[0], g[0]) for g in u["old_groups"]]
    form2.new_groups.choices = [(g[0], g[0]) for g in u["new_groups"]]
    allocations = u["allocations"]

    return (render_template('manage_users.html', form1=form1, form2=form2, allocations=allocations, message=message) )

if __name__ == '__main__':
    app.run()
