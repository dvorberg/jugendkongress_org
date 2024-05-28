import sys, os, os.path as op, fnmatch, shutil, types, functools, inspect
import subprocess, threading, tempfile

from t4 import sql

from flask import request

from PIL import Image

from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage

from . import config
from . import db

class Upload(db.dbobject):
    __relation__ = "uploads"
        
class UploadManager(object):
    def __init__(self, relation_name, subdir, ids_for_dbobject=None):
        """
        `relation_name` The SQL relation’s name for which we store files.
        `ids_for_dbobject` Function object returning a pair as
            ( foreign_id:int, fsid:str, ). The foreign_id identified the
            object throughout the database. `fsid`, i.e. ‘filesystem id’
        refers to the uniqe directory name used for a dbobject. All
        methods accepting a dbobject will also accept the fsid (as string)
        or any type of suitable primary key, which will be turned into
        a string using str().
        """
        self.relation_name = relation_name

        parts = subdir.split("/")
        parts = [ secure_filename(p) for p in parts]
        subdir = "/".join(parts)        
        self.subdir = subdir

        def default_ids_for_dbobject(o):
            if type(o) == int:
                return o, str(o),            
            elif hasattr(o, "fsid"):
                return o.id, o.fsid,
            else:
                return o.id, str(o.id),
        
        if ids_for_dbobject is None:
            self.ids_for_dbobject = default_ids_for_dbobject
        else:
            self.ids_for_dbobject = ids_for_dbobject
        
            
    def dirpath(self, dbobject):
        """
        Return the path to the directory for `dbobject` where its files
        reside.
        """
        id, fsid = self.ids_for_dbobject(dbobject)
            
        if ".." in fsid :
            raise OSError("No relative paths allowed in fsid: %s" % fsid)
        
        dirpath = op.join(config["UPLOADS_PATH"],
                          self.relation_name, fsid, self.subdir)
        os.makedirs(dirpath, exist_ok=True)

        return dirpath

    def abspath(self, dbobject, filename):
        """
        Return the absolute path to `filename` within out `dirpath`.
        """
        if (os.path.altsep and os.path.altsep in filename):
            raise OSError("No paths allowed in filename: %s" % filename)
        
        filename = secure_filename(filename)
        return op.join(self.dirpath(dbobject), filename)

    def url(self, dbobject, filename):
        """
        Return the absoulte url for `dbobject`’s `filename`.        
        """
        id, fsid = self.ids_for_dbobject(dbobject)
        return "%s/%s/%s/%s/%s" % ( config["UPLOADS_URL"],
                                    self.relation_name,
                                    fsid,
                                    self.subdir,
                                    filename, )
            
    def open(self, dbobject, filename, mode="r", info=None):
        """
        Return a file object for `dbobject`’s `filename`.  If `mode`
        instructs to open the file for writing, register it with the
        database and store `info` with it.
        """        
        if "w" in mode:
            self.register_with_db(dbobject, filename, info)
            
        path = self.abspath(dbobject, filename)
        return open(path, mode)

    def exists(self, dbobject, filename):
        """
        Does `dbobject`’s `filename` exist?
        This is a filesystem operation, not a database query.
        """
        return op.exists(self.abspath(dbobject, filename))

    def read(self, dbobject, filename, mode="r"):
        """
        Open `dbobject`’s `filename` and read the whole thing, returning
        it as a string. Use `mode` 'rb' for bytes.
        Does not access the database.
        """
        return self.open(dbobject, filename, mode).read()

    def write(self, dbobject, filename, data):
        """
        Open `dbobject`’s `filename` and write data to it. If data is a
        bytes object, the file will be opened in 'wb' mode.
        Does not modify the database.
        """
        if type(data) == bytes:
            with self.open(dbobject, filename, mode="wb") as fp:
                fp.write(data)
        elif type(data) == str:
            with self.open(dbobject, filename, mode="w") as fp:
                fp.write(data)
        else:
            raise TypeError("data must be bytes or string.")
        
    def unlink(self, dbobject, filename, ignore=True):
        """
        Delete `dbobject`’s `filename`, maybe `ignore` any error raised.
        Also removes and entry for this file from the database.
        """
        self.delete_from_db(dbobject, filename)
        
        abspath = self.abspath(dbobject, filename)
        try:
            os.unlink(abspath)
        except OSError:
            if not ignore:
                raise

    def rename(self, dbobject, filename, to):
        """
        Rename `dbobject`’s `filename` and update the database.
        """
        self.unlink(dbobject, to)
        os.rename(self.abspath(dbobject, filename),
                  self.abspath(dbobject, to))
        update = sql.update("uploads", self.where(dbobject, filename),
                            { "filename": to })
        db.execute(update)
            
    def clear(self, dbobject):
        """
        Delete all our files for a given dbobject.  This will also remove
        the storage directory, but it will quickly be re-created,
        should files be stored through the manager. Removes any of our
        entries from the database concerning `dbobject`. 
        """
        self.delete_from_db(dbobject)
        shutil.rmtree(self.dirpath(dbobject))
        
    drop = clear # Is this used at all?
        
    def glob(self, dbobject, pattern):
        """
        Returns a list of filenames (not paths!) stored for `dbobject`
        that match `pattern` in a unix-shell style (using Python’s
        fnmatch()).
        """
        return fnmatch.filter(os.listdir(self.dirpath(dbobject)), pattern)

    def firstfile(self, dbobject, suffix=None):
        """
        Returns the absolute path to the first file found in the managed
        directory or None, if no file found.
        """
        dirpath = self.dirpath(dbobject)
        for fn in os.listdir(dirpath):
            filepath = op.join(dirpath, fn)
            if op.isfile(filepath) and \
               ( suffix is None or filepath.endswith(suffix) ):
                return filepath

        return None

    def link(self, dbobject, filename, to, info=None):
        """
        Link `dbobject`’s `filename` to `to` creating a new entry in the
        database, possibly storing `info` with it.
        """
        os.link(self.abspath(dbobject, filename),
                self.abspath(dbobject, to))

        self.register_with_db(dbobject, to, info)
        
    def register_with_db(self, dbobject, filename, info=None):
        """
        Register a file with the database, possibly storing `info` with it.
        This will delete any previous entry for the same file from the
        database.
        """
        self.delete_from_db(dbobject, filename)

        name, suffix = op.splitext(filename)
        id, fsid = self.ids_for_dbobject(dbobject)
        
        if info is not None:
            info = sql.json_literal(info)

        db.insert_from_dict("uploads", { "relation_name": self.relation_name,
                                         "subdir": self.subdir,
                                         "foreign_id": id,
                                         "filename": filename,
                                         "suffix": suffix,
                                         "info": info },
                            retrieve_id=False)

    def where(self, dbobject, filename=None):
        """
        Return a t4.sql.where() object for `dbobject`’s files or the one
        referred to by `filename`.
        """
        id, fsid = self.ids_for_dbobject(dbobject)
        
        where = sql.where("foreign_id = ", sql.find_literal_maybe(id),
                          " AND subdir = ", sql.string_literal(self.subdir))
        if filename is not None:
            where = where.and_(sql.where("filename = ",
                                         sql.string_literal(filename)))
        
        return where
    
    def delete_from_db(self, dbobject, filename=None):
        """
        Delete one or all entries concerning `dbobject` from our database
        table.
        """
        delete = sql.delete("uploads", self.where(dbobject, filename))
        with db.cursor() as cc:
            command, params = db.rollup_sql(delete)
            cc.execute(command, params)

    def info_on(self, dbobject, filename):
        """
        Return the info stored in the database for `dbobject`’s `filename`.
        This is the result of a database query.
        """
        select = sql.select(("info",), "uploads",
                            self.where(dbobject, filename))
        tpl = query_one(select)
        if tpl is None:
            return None
        else:
            return json.dumps(tpl[0])

    def files_for(self, dbobject, where=None):
        """
        Return a result of Upload objects for `dbobject` from the database,
        possibly adding `where` to the query.
        """
        return Upload.select(self.where(dbobject).and_(where))    
                
    class for_dbobject_wrapper:
        """
        This is a wrapper for objects of this very class. It saves you
        from providing the `dbobject` parameter for all those function
        that take it as first argument and provides the files() and
        files_like() extra methods.
        """
        def __init__(self, upload_manager, dbobject):
            self.upload_manager = upload_manager
            self.dbobject = dbobject

        def __getattr__(self, name):
            method = getattr(self.upload_manager, name)
            if type(method) == types.MethodType:
                return functools.partial(method, self.dbobject)
            else:
                raise AttributeError(name)

        @property
        def files(self):
            return self.upload_manager.files_for(self.dbobject)

        def files_like(self, where):
            return self.upload_manager.files_for(self.dbobject, where)

    def for_(self, dbobject):
        """
        Return a wrapper-object that has all the methods of this Upload
        Manager with the first parameter set to `dbobject`.
        """
        return self.for_dbobject_wrapper(self, dbobject)

    @classmethod
    def upload_handler_from_request(self, request_field):
        return UploadHandler(request_field)

    @classmethod
    def handle_uploads(self, handle_upload_f, *request_fields):
        return UploadHandler.handle_uploads(handle_upload_f, *request_fields)
    
class UploadHandler(object):
    """
    This class is meant to be instantiated when feedback is gathered.
    This is done through its from_request() or handle_uploads() class
    methods. The constructor is basically useless. 
    """
    def __init__(self, request_field):
        """
        `uploaded_file` comes from request.files[...]
        """
        self._processed = None
        
        if not request_field in request.files:
            uploaded_file = None
        
        uploaded_file = request.files[request_field]
        if uploaded_file.filename == "":
            uploaded_file = None
            
        self.uploaded_file = uploaded_file

        if uploaded_file is None:
            self.tmpdir = None
        else:
            # Create temporary directory
            self.tmpdir = tempfile.TemporaryDirectory(
                dir=config["UPLOADS_PATH"])
            # tempfile.TemorarayDirecoty will cleanup() the directory and its
            # contents on __del__().
            
            self.filename = secure_filename(uploaded_file.filename)

            # Save the file to the tmpdir.
            self.abspath = op.join(self.tmpdir.name, self.filename)
            uploaded_file.save(self.abspath)


    @classmethod
    def handle_uploads(UploadHandler, handle_upload_f, *request_fields):
        """
        For each of the `request_fields` create call `upload_handler()`
        above and call `handle_upload_f(upload_handler)` for it, if it
        is present in the request.

        You `handle_upload_f()` must call the upload handler’s save()
        or discard() function explicitly.
        """
        for request_field in request_fields:
            with UploadHandler(request_field) as uh:
                if uh is not None:
                    handle_upload_f(uh)
        
    def __enter__(self):
        if self.uploaded_file is None:
            return None
        else:
            self._processed = False        
            return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if self.tmpdir:
            self.tmpdir.cleanup()

    def __del__(self):
        if self.uploaded_file is not None and not self._processed:
            raise ValueError("You must save() or discard() "
                             "the uploaded file.")

    def discard(self):
        self.tmpdir.cleanup()
        self._processed = True

    def save(self,
             upload_manager,
             local_filename=None, info=None,
             overwrite=True, clear=False):
        """
        Save the uploaded file. The `upload_manager` must be wrappered
        for_() a dbobject (see above).  Rename the file to
        `local_filename`, if so instructed, store `info` with it in
        the database, if provided, `overwrite` a file with the same
        name, otherwise raise IOError if it is in the ay. Maybe
        `clear()` the target directory before writing.
        """
        if clear:
            upload_manager.clear()

        if local_filename:
            filename = secure_filename(local_filename)
        else:                 
            filename = secure_filename(self.uploaded_file.filename)

        abspath = upload_manager.abspath(filename)

        if op.exists(abspath):
            if overwrite:
                upload_manager.unlink(abspath)
            else:
                raise IOError("%s already exists." % filename)

        os.link(self.abspath, abspath)
        upload_manager.register_with_db(filename, info)

        self._processed = True

        return abspath

    @property
    def mimetype(self):
        """
        Werkzeug...FileStorage.mimetype
        Like content_type, but without parameters (eg, without charset,
        type etc.) and always lowercase. For example if the content
        type is text/HTML; charset=utf-8 the mimetype would be
        'text/html'.
        """
        return self.uploaded_file.mimetype

    @property
    def content_type(self):
        """
        Werkzeug...FileStorage.content_type
        The content-type sent in the header. Usually not available.
        """
        return self.uploaded_file.content_type

    def open(self, mode="r"):
        return open(self.abspath, mode)

    def read(self, mode="r"):
        return open(self.abspath, mode).read()
    
    def image(self):
        return Image.open(self.abspath)

    def __bool__(self):
        return ( self.uploaded_file is not None )
    
        
def make_image_versions(upload_manager, image_upload_name, minsizes=()):

    if not image_upload_name in request.files:
        return
    
    uploaded_file = request.files[image_upload_name]
    if uploaded_file.filename == "":
        return
    
    tmp_name = "tmp.jpg"
    
    # Write the original file to disk with a temporary name.
    uploaded_file.save(upload_manager.abspath(tmp_name))

    try:
        image = Image.open(upload_manager.abspath(tmp_name))
    except IOError:
        upload_manager.unlink(tmp_name)
        raise
    else:
        # Remove the previous upload and all the versions.
        for fn in upload_manager.glob("*"):
            if fn != tmp_name:
                upload_manager.unlink(fn)

        # Give the original file its rightfull name.
        upload_manager.link(tmp_name, uploaded_file.filename)
        
        # And also provide it under a standardized name.
        if image.format == "JPEG":
            upload_manager.link(tmp_name, "profile.jpg")
        else:
            if image.mode != "RGB":
                i = image.convert("RGB")
            else:
                i = image

            i.save(upload_manager.abspath("profile.jpg"), quality=95)

        # Now we unlink the tmp_name and be done with it.
        upload_manager.unlink(tmp_name)

        # Create the desired versions of the file.
        smaller = min(image.size)
        larger = max(image.size)

        convert_executable = shutil.which("convert")
        if not convert_executable:
            raise OSError("convert executable not found.")

        def convert(size):
            outfile_name = "profile-%i.jpg" % size
            
            cmd = [ convert_executable,
                    "-thumbnail",  "%ix%i" % ( size, size, ),
                    upload_manager.abspath("profile.jpg"),
                    upload_manager.abspath(outfile_name), ]
            subprocess.run( cmd, check = True, timeout = 15 )
            upload_manager.register_with_db(outfile_name)
        
        threads = []
        for size in minsizes:
            if smaller > size:
                # We need to create a thumbnail.
                # The size of the thumbnail is chosen so the image covers a
                # square of SIZE without upscaling.
                target_size = int(float(larger) / float(smaller) * float(size))
                convert(target_size)

        
