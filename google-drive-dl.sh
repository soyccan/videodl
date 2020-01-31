#!/bin/sh
echo "Google Drive Video Downloader"
if [ "$#" -lt 1 ]; then
    echo "Usage: $0 [input file]"
    echo "input file: space-separated ID and filename for each line"
    exit 1
fi

while read -r id filename; do
    echo "Downloading video id '$id' to file '$filename'"
    path=$(curl -c /tmp/cookies "https://drive.google.com/uc?export=download&id=$id" 2> /dev/null \
       | grep -Po 'uc-download-link[^>]*href="\K[^>"]*' | sed 's/\&amp;/\&/g')
    curl -L -b /tmp/cookies "https://drive.google.com$path" > "$filename"
done < "$1"
