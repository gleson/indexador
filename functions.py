
import os
import re
import chardet
import hashlib
import time
import datetime
import nbformat
# from flask_executor import Executor
from nbconvert import PythonExporter
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, render_template, request, redirect, jsonify



def formatdate(date):
    return datetime.datetime.fromtimestamp(date).strftime('%Y/%m/%d %H:%M:%S')

def adjust_content(text):
    ## 01
    # remove_characters = ['\\', '/', '[', ']', '(', ')', '{', '}', '=', '#', ';', ':', '+', '-', ',', '|', '!', "'", '"', '*', '<', '>', '?', '.', '–', '‘', '’', '”', '“', '`', '~', '^', '\n', '\t']
    # for character in remove_characters:
    #     text = text.replace(character, ' ')
    ## 03
    text = re.sub(r'\b[\W_]+', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()

def delete_by_hash_list(hash_list):
    try:
        for file_hash in hash_list:
            delete_file = Files.query.filter_by(fl_hash=file_hash).first()
            db.session.delete(delete_file)        
        db.session.commit()
        return True
    except:
        return False

def delete_by_extension(extension):
    try:
        files = Files.query.filter(Files.fl_name.endswith(extension)).all()
        for file in files:
            db.session.delete(file)
        db.session.commit()
        return True
    except:
        return False

def delete_by_filename(filename):
    try:
        files = Files.query.filter_by(fl_name=filename).all()
        for file in files:
            db.session.delete(file)
        db.session.commit()
        return True
    except:
        return False


def detect_encoding(path):
    with open(path, 'rb') as file:
        data = file.read()
        result = chardet.detect(data)
        encoding = result['encoding']
    return encoding


def read_file_by_type(file_content, extension):
    if extension == '.ipynb':
        nb = nbformat.read(file_content, as_version=4)
        exporter = PythonExporter()
        codigo_py, _ = exporter.from_notebook_node(nb)


def index_and_update_folders(folder, extensions, exclude_folders, exclude_files, to_index):
    print(f'Iniciando: {folder.fld_path}')
    try:
        current_hash_list = folder.fld_hashes.split(',')
    except:
        current_hash_list = []

    new_hash_list = []
    for root, directories, files in os.walk(folder.fld_path, topdown=True):
        if set(root.split('\\')).intersection(exclude_folders):
            continue
        for name in files:
            hash = None
            if (name in exclude_files) or (name[:2]=='.~'):
                continue 
            path = f'{root}\\{name}' 
            if os.path.splitext(path)[1] in extensions:
                with open(path, 'r', encoding='utf-8') as file:
                    try:
                        text = file.read()
                        hash = hashlib.md5((path+text).encode()).hexdigest()
                    except UnicodeDecodeError:
                        encode = detect_encoding(path)
                        try:
                            with open(path, 'r', encoding=encode) as file:
                                text = file.read()
                                hash = hashlib.md5((path+text).encode()).hexdigest()
                        except:
                            text = 'empty'
                            hash = hashlib.md5(path.encode()).hexdigest()
                new_hash_list.append(hash)
                if hash in current_hash_list:
                    continue
                if to_index:
                    text = adjust_content(text)
                    all_words = set(text.split())
                    words = " ".join(all_words)
                    fl_size = os.path.getsize(path)//1024
                    fl_modificated = formatdate(os.path.getmtime(path))
                    this_file = Files.query.filter_by(fl_name=name, fl_path=root).first()
                    if this_file:
                        this_file.fl_words = words
                        this_file.fl_size = fl_size
                        this_file.fl_modificated = fl_modificated
                    else:
                        fl_created = formatdate(os.path.getctime(path))
                        this_file = Files(fl_name=name, fl_path=root, fl_words=words, fl_size=fl_size, fl_created=fl_created, fl_modificated=fl_modificated, fl_hash=hash)
                        db.session.add(this_file)
                    db.session.commit()
    # Atualizando informações da pasta
    folder.fld_last_check_date = datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')
    if new_hash_list == current_hash_list:
        folder.fld_last_status = 'Atualizado'
    else:
        folder.fld_last_status = 'Desatualizado'
        if to_index:
            folder.fld_hashes = ','.join(new_hash_list)
            folder.fld_last_status = 'Atualizado'
            hashes_to_delete = [item for item in current_hash_list if item not in new_hash_list]
            delete_by_hash_list(hashes_to_delete)
    db.session.add(folder)
    db.session.commit()
    print(f'Concluindo: {folder.fld_path}')
    return redirect("./index_all")