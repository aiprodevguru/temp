import datetime
from peewee import *
import os
from const import runtime_tmp_dir

db = SqliteDatabase(os.path.join(runtime_tmp_dir, 'local.db'))

class BaseModel(Model):
    class Meta:
        database = db

class Zipfile(BaseModel):
    zip_file_path = TextField()
    upload_file_path = TextField()
    request_payload = TextField()
    size = FloatField(null=True)
    created_at = DateTimeField(default=datetime.datetime.now)

# Connect to our database.
db.connect()

# Create the tables.
db.create_tables([Zipfile, ])

def dbCreateZip(data):
    zip = Zipfile.create(**data)

def dbGetZip(limit=10):
    if limit:
        query = Zipfile.select().order_by(Zipfile.created_at.desc()).limit(limit)
    else:
        query = Zipfile.select().order_by(Zipfile.created_at.desc())

    res = []

    for zip in query:
        res.append({
            "id": zip.id,
            "zip_file_path": zip.zip_file_path,
            "upload_file_path": zip.upload_file_path,
            "request_payload": zip.request_payload,
            "size": zip.size,
            "created_at": zip.created_at
        })

    return res

def dbRemoveZip(id):
    try:
        zip = Zipfile.get(Zipfile.id == id)
        zip.delete_instance()
    except Exception as e:
        print(e)

if __name__ == '__main__':
    dbCreateZip({
        "zip_file_path": 'test/res.zip_file_path',
        "upload_file_path": 'test/res.upload_file_path',
        "request_payload": '{"data": "test"}',
        "size": 1000
    })

    print(dbGetZip())
