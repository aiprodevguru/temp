from datetime import datetime
import zipfile
import os
import shutil
import PyInstaller.__main__
from utils import delete_files_in_directory, zip_directory
from pathlib import Path

current_datetime = datetime.now()
formatted_datetime = current_datetime.strftime("%Y-%m-%d_%H-%M")

APP_PATH = os.path.dirname(__file__)
DIST_PATH = os.path.join(APP_PATH, 'dist')

def delete_zip_file_in_directory(folder_path):
    files = os.listdir(folder_path)
    # Iterate over each file and delete zip files
    for file_name in files:
        file_path = os.path.join(folder_path, file_name)
        if os.path.isfile(file_path) and file_name.endswith('.zip'):
            os.remove(file_path)
            print(f"Deleted zip file: {file_path}")

delete_files_in_directory(DIST_PATH)

installer_file = ''
zip_file = ''
runtime_tmp_dir = ''
if os.name == 'nt':
    installer_file = os.path.join(APP_PATH, 'installers/windows/install.bat')
    zip_file = os.path.join(APP_PATH, 'installers/windows/windows-setup_'+formatted_datetime+'.zip')
    runtime_tmp_dir = os.path.join('C:\\', 'Recorder')
    delete_zip_file_in_directory(os.path.join(APP_PATH, 'installers/windows'))
if os.name == 'posix' and os.uname().sysname == 'Linux':
    installer_file = os.path.join(APP_PATH, 'installers/ubuntu/install.sh')
    zip_file = os.path.join(APP_PATH, 'installers/ubuntu/ubuntu-setup_'+formatted_datetime+'.zip')
    delete_zip_file_in_directory(os.path.join(APP_PATH, 'installers/ubuntu'))
    runtime_tmp_dir = os.path.join('/var', '.Recorder')
if os.name == 'posix' and os.uname().sysname == 'Darwin':
    installer_file = os.path.join(APP_PATH, 'installers/mac/install.sh')
    zip_file = os.path.join(APP_PATH, 'installers/mac/mac-setup_'+formatted_datetime+'.zip')
    delete_zip_file_in_directory(os.path.join(APP_PATH, 'installers/mac'))
    runtime_tmp_dir = os.path.join(Path.home(), '.Recorder')

PyInstaller.__main__.run([
    os.path.join(APP_PATH, 'code1.py'),
    '--onefile',   # Generate a single executable file
    '--clean',     # Clean temporary files before building
    '--noconfirm', # Do not ask for confirmation during build
    '--runtime-tmpdir',
    runtime_tmp_dir
])

shutil.copy(installer_file, DIST_PATH)

if os.name == 'nt':
    shutil.copy(os.path.join(APP_PATH, 'ffmpeg.exe'), DIST_PATH)

zip_directory(DIST_PATH, zip_file)

print ('Build Completed!', zip_file)
