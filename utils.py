import os
import zipfile

def delete_files_in_directory(directory):
    if not os.path.exists(directory):
        return
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        try:
            if os.path.isfile(filepath):
                os.remove(filepath)
        except Exception as e:
            print(f"Error deleting {filename}: {e}")

def zip_directory(input_dir, output_dir):
    # Create a ZipFile object
    with zipfile.ZipFile(output_dir, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Iterate over all files and subdirectories in the input directory
        for root, dirs, files in os.walk(input_dir):
            for file in files:
                # Create the full filepath by joining the root and file
                file_path = os.path.join(root, file)
                # Add the file to the zip
                zipf.write(file_path, os.path.relpath(file_path, input_dir))
