# rattle-media
Python based web application to play music from Google Play via gstreamer.

Initially, this will support only All Access accounts, with support for other accounts coming later.

Work has only just begun.


Setting up
-------------------------------
In the root folder, run pip install -r requirements.pip

In /static, run bower install bower.json

Install into the system:
python-gst-1.0 gstreamer1.0-plugins-good gstreamer1.0-plugins-ugly


Config
-------------------------------
In the root folder, create config.py with the following contents:

    google_username="<your username>"
    google_password="<your password>"
    google_device_id="<your device id>" # See the unofficial google music api for details on where to get this
    secret_key="<some secret>"
