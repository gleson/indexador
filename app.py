import os
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy

from flask_executor import Executor
from functions import *


project_dir = os.path.dirname(os.path.abspath(__file__))
database_file = "sqlite:///{}".format(os.path.join(project_dir, "database.db"))

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = database_file

db = SQLAlchemy(app)
executor = Executor(app)

class Folders(db.Model):
    fld_path = db.Column(db.String(250), unique=True, primary_key=True)
    fld_hashes = db.Column(db.Text)
    fld_last_check_date = db.Column(db.String(50))
    fld_last_status = db.Column(db.String(15))
    fld_files = db.relationship('Files', cascade='delete')
    def __repr__(self):
        return f'<Path: {self.fld_path!r}>'


class Extensions(db.Model):
    ext_name = db.Column(db.String(50), unique=True, primary_key=True)
    def __repr__(self):
        return f'<Name: {self.ext_name!r}>'


class Exclude(db.Model):
    exc_name = db.Column(db.String(50), primary_key=True)
    exc_type = db.Column(db.String(50), primary_key=True)
    def __repr__(self):
        return f'<Name: {self.exc_name!r}>'


class Files(db.Model):
    fl_id = db.Column(db.Integer, primary_key=True)
    fl_name = db.Column(db.String(150))
    fl_path = db.Column(db.String(255))
    fl_words = db.Column(db.Text)
    fl_size = db.Column(db.Float)
    fl_created = db.Column(db.String(50))
    fl_modificated = db.Column(db.String(50))
    fl_hash = db.Column(db.String(50))
    fl_folder_path = db.Column(db.Integer, db.ForeignKey('folders.fld_path'))
    def __repr__(self):
        return f'<ID: {self.fl_id!r}>'






##############################################################################################################################
##############################################################################################################################
##############################################################################################################################






@app.route('/', methods=["GET", "POST"])
def home():
    folders, extensions, excludes = None, None, None

    if request.form:
        try:
            if request.form.get("fld_path") and os.path.exists(request.form.get("fld_path")):
                add_it = Folders(fld_path=request.form.get("fld_path"))
            elif request.form.get("ext_name"):
                add_it = Extensions(ext_name=request.form.get("ext_name"))
            elif request.form.get("exc_name"):
                add_it = Exclude(exc_name=request.form.get("exc_name"), exc_type=request.form.get("exc_type"))

            db.session.add(add_it)
            db.session.commit()
        except:
            db.session.rollback()

    folders = Folders.query.all()
    extensions = Extensions.query.all()
    excludes = Exclude.query.all()
    files = Files.query.all()
    n_range=max(len(folders), len(extensions), len(excludes))
    return render_template("home.html", folders=folders, extensions=extensions, excludes=excludes, files=files, n_range=n_range)


@app.route("/delete", methods=["POST"])
def delete():
    if request.form.get("fld_path"):
        delete_it = Folders.query.filter_by(fld_path=request.form.get("fld_path")).first()
        if delete_it.fld_hashes:
            delete_by_hash_list(delete_it.fld_hashes.split(','))

    elif request.form.get("ext_name"):
        delete_it = Extensions.query.filter_by(ext_name=request.form.get("ext_name")).first()
        delete_by_extension(request.form.get("ext_name"))

    elif request.form.get("exc_name"):
        delete_it = Exclude.query.filter_by(exc_name=request.form.get("exc_name"), exc_type=request.form.get("exc_type")).first()

    db.session.delete(delete_it)
    db.session.commit()
    return redirect("./config")


@app.route("/index_all", methods=["GET", "POST"])
def index_all():

    folders = Folders.query.all()
    return render_template("index_all.html", folders=folders)


@app.route("/update", methods=["GET", "POST"])
def update():
    if request.form.get("fld_update"):
        folders = Folders.query.filter_by(fld_path=request.form.get("fld_update"))
        to_index = True
    elif request.form.get("fld_status"):
        folders = Folders.query.filter_by(fld_path=request.form.get("fld_status"))
        to_index = False
    elif value := request.form.get("make_to_all"):
        folders = Folders.query.all()
        if value == 'update':
            to_index = True
        elif value == 'status':
            to_index = False
    else:
        return redirect("./index_all")

    extensions      = [x[0] for x in Extensions.query.with_entities(Extensions.ext_name).all()]
    exclude_folders = [y[0] for y in Exclude.query.with_entities(Exclude.exc_name).filter_by(exc_type='folder').all()]
    exclude_files   = [z[0] for z in Exclude.query.with_entities(Exclude.exc_name).filter_by(exc_type='file').all()]

    for folder in folders:
        result = executor.submit(index_and_update_folders, folder, extensions, exclude_folders, exclude_files, to_index)
 
    return redirect("./index_all")

##############################################################################################################################
##############################################################################################################################
##############################################################################################################################


@app.route("/config", methods=["GET", "POST"])
def config():
    folders, extensions, excludes = None, None, None

    if request.form:
        try:
            if request.form.get("fld_path") and os.path.exists(request.form.get("fld_path")):
                add_it = Folders(fld_path=request.form.get("fld_path"), fld_last_check_date='Nunca', fld_last_status='Desatualizado')
            elif request.form.get("ext_name"):
                add_it = Extensions(ext_name=request.form.get("ext_name"))
            elif request.form.get("exc_name"):
                add_it = Exclude(exc_name=request.form.get("exc_name"), exc_type=request.form.get("exc_type"))
                if request.form.get("exc_type") == 'file':
                    delete_by_filename(request.form.get("exc_name"))

            db.session.add(add_it)
            db.session.commit()
        except:
            db.session.rollback()

    folders = Folders.query.all()
    extensions = Extensions.query.all()
    excludes = Exclude.query.all()
    files = Files.query.all()
    n_range=max(len(folders), len(extensions), len(excludes))
    return render_template("config.html", folders=folders, extensions=extensions, excludes=excludes, files=files, n_range=n_range)


##############################################################################################################################
##############################################################################################################################
##############################################################################################################################


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000,)

