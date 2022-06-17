# Change Directory to clones
cd _clones

# Extract Strings from UI
./compose run --rm --user=0 \
-v _translations:/translations \
ui \
sh -c "npm run gettext:extract && cp /hub/app/locale/en.po translations/en.po"

# Extract Strings from API
 ./compose run --rm --user=0 \
-v _translations:/translations \
api \
bash -c "cd /app/galaxy_ng && django-admin makemessages -l en_us --keep-pot && cp /app/galaxy_ng/locale/django.pot translations/django.po"

# Terminate docker
