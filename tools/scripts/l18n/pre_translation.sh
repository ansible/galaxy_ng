#!/bin/bash

# Build Hub Development Environment
python3 -m venv venv
source venv/bin/activate
pip3 install -r dev_requirements.txt

# Extract Strings from API
cd galaxy_ng && django-admin makemessages -l en_us --keep-pot
 
cd ..

# Move files to Translations folder
mv galaxy_ng/locale/django.pot translations/django.po