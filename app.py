from flask import Flask, request, redirect, url_for, render_template, send_file, flash, jsonify
import os
import shutil
import zipfile
import mimetypes
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'
BASE_DIR = os.path.expanduser("~")
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_file_icon(filename, is_dir):
    if is_dir:
        return 'fas fa-folder'
    ext = os.path.splitext(filename)[1].lower()
    icons = {
        '.txt': 'fas fa-file-alt',
        '.py': 'fab fa-python',
        '.js': 'fab fa-js-square',
        '.html': 'fab fa-html5',
        '.css': 'fab fa-css3-alt',
        '.json': 'fas fa-code',
        '.xml': 'fas fa-code',
        '.jpg': 'fas fa-image',
        '.jpeg': 'fas fa-image',
        '.png': 'fas fa-image',
        '.gif': 'fas fa-image',
        '.pdf': 'fas fa-file-pdf',
        '.doc': 'fas fa-file-word',
        '.docx': 'fas fa-file-word',
        '.zip': 'fas fa-file-archive',
        '.rar': 'fas fa-file-archive'
    }
    return icons.get(ext, 'fas fa-file')

def get_file_size(filepath):
    try:
        size = os.path.getsize(filepath)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    except:
        return "0 B"
def safe_path(path):
    full = os.path.abspath(os.path.join(BASE_DIR, path.strip("/")))
    if not full.startswith(BASE_DIR):
        return BASE_DIR
    return full

@app.route('/', defaults={'path': ''})
@app.route('/browse/<path:path>')
def browse(path):
    full_path = safe_path(path)
    try:
        items = []
        for f in os.listdir(full_path):
            item_path = os.path.join(full_path, f)
            is_dir = os.path.isdir(item_path)
            items.append({
                'name': f,
                'path': os.path.join(path, f),
                'is_dir': is_dir,
                'icon': get_file_icon(f, is_dir),
                'size': get_file_size(item_path) if not is_dir else '',
                'modified': os.path.getmtime(item_path)
            })
        # Sort: directories first, then files
        items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
    except:
        items = []
    
    # Create breadcrumb
    breadcrumb = []
    if path:
        parts = path.split('/')
        for i, part in enumerate(parts):
            breadcrumb.append({
                'name': part,
                'path': '/'.join(parts[:i+1])
            })
    
    parent = os.path.dirname(path)
    return render_template('index.html', 
                         items=items, 
                         path=path, 
                         parent=parent,
                         breadcrumb=breadcrumb)

@app.route('/upload/<path:path>', methods=['POST'])
def upload_file(path):
    full_path = safe_path(path)
    if 'files' not in request.files:
        flash('No files selected', 'error')
        return redirect(url_for('browse', path=path))
    
    files = request.files.getlist('files')
    uploaded_count = 0
    
    for file in files:
        if file and file.filename:
            filename = secure_filename(file.filename)
            file_path = os.path.join(full_path, filename)
            file.save(file_path)
            uploaded_count += 1
    
    flash(f'Successfully uploaded {uploaded_count} file(s)', 'success')
    return redirect(url_for('browse', path=path))

@app.route('/download/<path:path>')
def download_file(path):
    full_path = safe_path(path)
    if os.path.isfile(full_path):
        return send_file(full_path, as_attachment=True)
    elif os.path.isdir(full_path):
        # Create zip file for directory
        zip_path = full_path + '.zip'
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(full_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, os.path.dirname(full_path))
                    zipf.write(file_path, arcname)
        
        def remove_file(response):
            try:
                os.remove(zip_path)
            except:
                pass
            return response
        
        return send_file(zip_path, as_attachment=True, 
                        download_name=f"{os.path.basename(path)}.zip",
                        mimetype='application/zip')
    
    flash('File not found', 'error')
    return redirect(url_for('browse', path=os.path.dirname(path)))
@app.route('/edit/<path:path>', methods=['GET', 'POST'])
def edit_file(path):
    full_path = safe_path(path)
    parent = os.path.dirname(path)
    
    # Check if file is text-based
    try:
        mime_type, _ = mimetypes.guess_type(full_path)
        if mime_type and not mime_type.startswith('text/'):
            flash('This file type cannot be edited', 'error')
            return redirect(url_for('browse', path=parent))
    except:
        pass
    
    if request.method == 'POST':
        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(request.form['content'])
            flash('File saved successfully', 'success')
            return redirect(url_for('browse', path=parent))
        except Exception as e:
            flash(f'Error saving file: {str(e)}', 'error')
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        file_ext = os.path.splitext(path)[1].lower()
    except Exception as e:
        flash(f'Error reading file: {str(e)}', 'error')
        content = ''
        file_ext = ''
    
    return render_template('edit.html', 
                         path=path, 
                         content=content, 
                         parent=parent,
                         file_ext=file_ext)

@app.route('/delete/<path:path>')
def delete_file(path):
    full_path = safe_path(path)
    try:
        if os.path.isdir(full_path):
            shutil.rmtree(full_path)
            flash('Folder deleted successfully', 'success')
        elif os.path.isfile(full_path):
            os.remove(full_path)
            flash('File deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting: {str(e)}', 'error')
    
    return redirect(url_for('browse', path=os.path.dirname(path)))

@app.route('/new/<path:path>', methods=['POST'])
def new_file(path):
    full_path = safe_path(path)
    name = request.form['filename']
    if not name:
        flash('Please enter a name', 'error')
        return redirect(url_for('browse', path=path))
    
    target = os.path.join(full_path, name)
    try:
        if request.form['type'] == 'file':
            open(target, 'w').close()
            flash(f'File "{name}" created successfully', 'success')
        else:
            os.makedirs(target, exist_ok=True)
            flash(f'Folder "{name}" created successfully', 'success')
    except Exception as e:
        flash(f'Error creating: {str(e)}', 'error')
    
    return redirect(url_for('browse', path=path))

@app.route('/rename/<path:path>', methods=['GET', 'POST'])
def rename_file(path):
    full_path = safe_path(path)
    parent = os.path.dirname(path)
    
    if request.method == 'POST':
        new_name = request.form['new_name']
        if not new_name:
            flash('Please enter a new name', 'error')
            return render_template('rename.html', 
                                 path=path, 
                                 current_name=os.path.basename(path), 
                                 parent=parent)
        
        try:
            new_path = os.path.join(os.path.dirname(full_path), new_name)
            os.rename(full_path, new_path)
            flash(f'Renamed successfully to "{new_name}"', 'success')
            return redirect(url_for('browse', path=parent))
        except Exception as e:
            flash(f'Error renaming: {str(e)}', 'error')
    
    return render_template('rename.html', 
                         path=path, 
                         current_name=os.path.basename(path), 
                         parent=parent)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)