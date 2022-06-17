#!/bin/bash

# Rename the zh_cn folder 
mv translations/zh_cn translations/zh

# Create a directory for api (locale)
mkdir locale

# Copy all subdirectories to locale
cp -r translations/ locale/

# Loop over each directory and create another directory LC_Messages
# Move django.po files to LC_Messages
cd locale/
for d in */ ; do
    dir=${d%*/}
    mkdir $dir/LC_MESSAGES
    mv $dir/django.po $dir/LC_MESSAGES/
done

cd ..

# locale will be dropped here
galaxy_ng_api_path="galaxy_ng/locale" 

# Overwrite files
rsync -av locale/ $galaxy_ng_api_path

# Cleanup
rm -rf translations/
rm -rf locale/