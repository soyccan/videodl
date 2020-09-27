# cat imgurls.txt | parallel 'a={/}; b=$(printf %b ${a//\%/\\x}); [ ! -e "$b" ] && wget -c {}'
#
import re
import logging
import urllib.parse
import threading
import queue
import os
import sys

import requests


if os.environ.get('DEBUG'):
    logging.basicConfig(level="DEBUG")
else:
    logging.basicConfig(level="INFO")

COOKIES = "cookienotice=1; v3=0; z_hash=cf41b40e756c6d451ea66fe7a0377ee8; z_id=1523173; PHPSESSID=cov9v98iig22t6f4pcnlgrsflc; z_theme=1"
NUM_THREAD = 24


def worker(tasks, imgurls, keyword, keyword_url, keyword_file):
    while True:
        i = tasks.get()
        if i <= 0:
            break
        logging.info(f"i: {i}")

        url = "https://www.zerochan.net/{}?p={}".format(
            keyword_url.replace(".", "+"), i
        )
        html = requests.get(url, headers={"cookie": COOKIES}).text
        res = list(
            re.finditer(
                r"https://static\.zerochan\.net/.*?full\.[0-9]+\.(png|jpg|jpeg|gif)",
                html,
            )
        )
        for match in res:
            if not match:
                continue
            imgurl = match.group(0)
            logging.debug("imgurl: %s", imgurl)
            if keyword_file not in imgurl:
                continue
            imgurls.put(imgurl)
        tasks.task_done()


def main():
    keyword = urllib.parse.unquote(sys.argv[1].replace("+", " "))
    keyword_url = urllib.parse.quote(keyword.replace(" ", "+"), safe="+")
    keyword_file = urllib.parse.quote(
        keyword.replace(" ", ".").replace("/", ".")
    )

    pages = int(
        re.search(
            r"page 1 of ([0-9]+)",
            requests.get(
                "https://www.zerochan.net/{}".format(
                    keyword.replace(".", "+")
                ),
                headers={"cookie": COOKIES},
            ).text,
        ).group(1)
    )

    logging.info(
        "total {} pages\nkeyword: {}\nkeyword_url: {}\nkeyword_file: {}".format(
            pages, keyword, keyword_url, keyword_file
        )
    )

    imgurls = queue.Queue()
    tasks = queue.Queue()
    pool = []
    for i in range(1, pages+1):
        tasks.put(i)
    for _ in range(NUM_THREAD):
        pool.append(
            threading.Thread(
                target=worker,
                args=(tasks, imgurls, keyword, keyword_url, keyword_file),
            )
        )
        pool[-1].start()

    tasks.join()
    for _ in range(NUM_THREAD):
        tasks.put(-1)
    for e in pool:
        e.join()

    res = []
    while not imgurls.empty():
        res.append(imgurls.get())
    print('\n'.join(set(res)))

#      with open("imgurls.txt", "w") as f:
#          while not imgurls.empty():
#              f.write(imgurls.get() + "\n")


main()
