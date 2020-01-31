SECONDS=0
totalsz=0
while read -r i f; do
    f="$(printf $f | tr -d '\r')"

    if [ "$i" -lt 10 ]; then
        i="0$i"
    fi

    if [ -e "$i.mp4" ]; then
        echo file $i.mp4 exists
        continue
    fi

    echo
    echo Downloading $i.mp4
    tm=$SECONDS
    '/c/Program Files/VideoLAN/VLC/vlc.exe' "$f" --sout file/ts:$i.mp4 --sout-keep --play-and-exit -I dummy &> /dev/null

    echo DONE!
    filesz=$(du -m "$i.mp4" | cut -f1)
    totalsz=$(( $totalsz + $filesz ))
    echo used: $(($SECONDS - $tm))s
    echo average rate: $(( $filesz / ($SECONDS - $tm) ))MB/s
done <<< "$(nl urls.txt)" # nl: line number
echo ALL FINISHED
echo Total Used: "$SECONDS"s
echo Overall Download Rate: $(( $totalsz / $SECONDS ))MB/s
