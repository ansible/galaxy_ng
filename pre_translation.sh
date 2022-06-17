# Change Directory to clones
cd _clones/galaxy_ng/

# Build Hub Development Environment
cp .compose.env.example .compose.env
echo $"ANSIBLE_HUB_UI_PATH='#'" >> .compose.env
./compose build

# Extract Strings from API
./compose run --rm --user=0 \
 -v $(pwd)/translations:/translations \
 api \
 bash -c "cd app/galaxy_ng && django-admin makemessages -l en_us --keep-pot && cp /app/galaxy_ng/locale/django.pot /translations/django.po"
 
# cd ..

# Move files to Translations folder
# mv galaxy_ng/locale/django.pot translations/
