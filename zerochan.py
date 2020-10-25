# cat imgurls.txt | parallel 'a={/}; b=$(printf %b ${a//\%/\\x}); [ ! -e "$b" ] && wget -c {}'
#
import re
import logging
import urllib.parse
import urllib.request
import threading
import queue
import os
import shutil
import sys

import requests

if os.environ.get('DEBUG'):
    logging.basicConfig(level="DEBUG")
else:
    logging.basicConfig(level="INFO")

COOKIES = "cookienotice=1; __utmz=7894585.1601227796.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none); z_id=1564805; z_hash=874ada7e51aeefd8bd05d098e065d01e; PHPSESSID=sr4fj4ebe3ntbt4tvmee9rvsou; v3=0; z_theme=1; __gads=ID=146ac7565203ef60-22f9fad85dc40028:T=1603613058:RT=1603613058:S=ALNI_MbhwZV2M1F6xZqclCPLF3SPa-0mYA; __utmc=7894585; __utmt=1; __utma=7894585.1127421201.1601227796.1602437286.1603613056.4; __utmb=7894585.2.10.1603613058"
NUM_THREAD = 24


def get_imgurls(keyword, keyword_url, keyword_file):
    def worker(tasks, imgurls, keyword, keyword_url, keyword_file):
        while True:
            i = tasks.get()
            if i <= 0:
                break
            logging.info(f"i: {i}")

            url = "https://www.zerochan.net/{}?p={}".format(
                keyword_url.replace(".", "+"), i)
            html = requests.get(url, headers={"cookie": COOKIES}).text
            res = list(
                re.finditer(
                    r"https://static\.zerochan\.net/.*?full\.[0-9]+\.(png|jpg|jpeg|gif)",
                    html,
                ))
            for match in res:
                if not match:
                    continue
                imgurl = match.group(0)
                logging.debug("imgurl: %s", imgurl)
                if keyword_file not in imgurl:
                    continue
                imgurls.put(imgurl)
            tasks.task_done()

    pages = int(
        re.search(
            r"page 1 of ([0-9]+)",
            requests.get(
                "https://www.zerochan.net/" + keyword_url,
                headers={
                    "cookie": COOKIES
                },
            ).text,
        ).group(1))

    logging.info(
        "total {} pages\nkeyword: {}\nkeyword_url: {}\nkeyword_file: {}".
        format(pages, keyword, keyword_url, keyword_file))

    imgurls = queue.Queue()
    tasks = queue.Queue()
    pool = []
    for i in range(1, pages + 1):
        tasks.put(i)
    for _ in range(NUM_THREAD):
        pool.append(
            threading.Thread(
                target=worker,
                args=(tasks, imgurls, keyword, keyword_url, keyword_file),
            ))
        pool[-1].start()

    try:
        tasks.join()
        for _ in range(NUM_THREAD):
            tasks.put(-1)
        for e in pool:
            e.join()
    except KeyboardInterrupt:
        raise

    res = []
    while not imgurls.empty():
        res.append(imgurls.get())
    return list(set(res))


def main():
    def download_worker(url, dest_path):
        with urllib.request.urlopen(url) as sk, \
                open(dest_path, 'wb') as of:
            shutil.copyfileobj(sk, of)

    keyword = urllib.parse.unquote(sys.argv[1].replace("+", " "))
    keyword_url = urllib.parse.quote(keyword.replace(" ", "+"), safe="+")
    keyword_file = urllib.parse.quote(
        keyword.replace(" ", ".").replace("/", "."))

    imgurls = get_imgurls(keyword, keyword_url, keyword_file)

    dirname = keyword.replace(':', ';')  # colon is invalid in Win32
    if not os.path.exists(dirname):
        os.mkdir(dirname)

    pool = []
    for url in imgurls:
        filename = urllib.parse.unquote(
            urllib.parse.urlparse(url).path.split('/')[-1]).replace(':', ';')
        if not filename:
            logging.error('Filename cannot be obtained from url: %s', url)
            continue
        dest_path = os.path.join(dirname, filename)

        if not os.path.exists(dest_path):
            logging.info('Writing to ' + dest_path)
            pool.append(
                threading.Thread(target=download_worker,
                                 args=(url, dest_path)))
            pool[-1].start()
    try:
        for t in pool:
            t.join()
    except KeyboardInterrupt:
        raise


main()
