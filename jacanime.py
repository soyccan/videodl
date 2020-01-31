from urllib.request import urlopen, Request
from urllib.error import URLError
from http.cookiejar import CookieJar
import re, os.path, time, sys, math, shutil, logging

def human_size(size, decimals = 2):
    if size <= 0:
        return '0'
    unit = ('Bytes', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB')
    factor = int(math.log2(size) // 10)
    if factor > 8:
        factor = 8
    return "{0:.{2}f}{1}".format(size / (1 << (10 * factor)), unit[factor], decimals)

def try_other_filename(filename):
    base, ext = os.path.splitext(filename)
    for i in range(1, sys.maxsize):
        newname = base + ' ' + str(i) + ext
        if not os.path.exists(newname):
            return newname

def get_jac_video(index_page):
    # return list of (google drive id, filename) pairs
    res = []
    try:
        logging.debug('Connecting ' + index_page)
        html = urlopen(index_page, timeout=30).read()
    except URLError:
        logging.error('Error on connection!\n')
        logging.info(sys.exc_info())
        return res

    pattern = br'https://(drive|docs)\.google\.com/(open\?id=|file/d/)([^/"]+)'
    for i, match in enumerate(re.finditer(pattern, html)):
        res.append((
            match.group(3).decode(),
            '{:02}.mp4'.format(i+1) ))
    return res

def get_jac_video_passwd(index_page):
    # return list of (google drive id, filename) pairs
    res = []
    try:
        logging.debug('Connecting', index_page)
        html = urlopen(index_page, timeout=30).read()
    except URLError:
        logging.error('Error on connection!\n')
        logging.info(sys.exc_info())
        return res

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3486.0 Safari/537.36',
        'Cookie': 'j-p=7837e0571acbecef3c23baaaf5c7ce4c'}

    pattern = br'https://sgod.ga/[^"]*'
    for i, match in enumerate(re.finditer(pattern, html)):
        rq = Request(
            match.group(0).decode().replace('https://sgod.ga/', 'https://sgod.ga/?id='),
            headers=headers)
        try:
            logging.debug('connecting ' + rq.full_url)
            rp = urlopen(rq)
        except URLError:
            logging.error('Error on connection\n')
            logging.info(sys.exc_info())
            continue

        vid = re.search(r'https://drive.google.com/file/d/([^/]*)', rp.geturl())
        if not vid:
            vid = re.search(r'id=([^&]*)', rp.geturl())
        res.append((vid.group(1), '{:02}.mp4'.format(i+1) ))
    return res

def get_jac_video_dailymotion(index_page):
    # return list of (dailymotion id, filename) pairs
    res = []
    try:
        logging.debug('Connecting', index_page)
        html = urlopen(index_page, timeout=30).read()
    except URLError:
        logging.error('Error on connection!\n')
        return res

    pattern = br'<span data-lang="([^"]*)">'
    for i, match in enumerate(re.finditer(pattern, html)):
        res.append((
            match.group(1).decode(),
            '{:02}.mp4'.format(i+1) ))
    return res

def dl_googledrive_video(url_filename_list):
    total_start_tm = time.clock()
    total_sz = 0

    for videoid, filename in url_filename_list:
        if not videoid: continue
        if os.path.exists(filename):
            logging.warning(f'Ignoring exisiting file "{filename}"')
            # filename = try_other_filename(filename)
            # logging.info('changing filename to "{}"'.format(filename))
            continue

        ck = CookieJar()
        rq = Request("https://drive.google.com/uc?export=download&id=" + videoid)
        try:
            logging.debug('Connecting ' + rq.full_url)
            rp = urlopen(rq, timeout=10)
        except URLError:
            logging.error(f'connection to {rq.full_url} failed!')
            logging.error(f'videoid: {videoid}')
            logging.error(f'filename: {filename}')
            continue

        ck.extract_cookies(rp, rq)

        try:
            dllink = re.search(
                rb'uc-download-link[^>]*href="([^>"]*)"',
                rp.read()).group(1).decode().replace('&amp;', '&')
        except:
            logging.debug('failed on finding download address')
            logging.debug(rp.read().decode())
            continue

        rq1 = Request('https://drive.google.com' + dllink)
        ck.add_cookie_header(rq1)
        with urlopen(rq1) as rp1, \
              open(filename, 'wb') as f1:
            logging.info('Downloading video ID "{}" as file "{}"'.format(videoid, filename))
            if rp1.getheader('Content-Type') not in ('video/mp4', 'video/x-matroska'):
                logging.warning(f"Ignoring file {filename}, videoid {videoid}")
                logging.warning(f"target file isn't of type .mp4 or .mkv")
                continue

            blksz = 1024 * 1024 * 16
            dlsz = 0
            # totalsz = rp1.getheader('Content-Length')
            tm = time.clock()
            while not rp1.closed:
                chunk = rp1.read(blksz)
                if len(chunk) == 0: break
                dlsz += len(chunk)
                sys.stdout.write('\r' + ' ' * (shutil.get_terminal_size()[0]-2))
                sys.stdout.write('\rDownloaded {}% at {}/s'.format('?',
                    human_size(dlsz / (time.clock() - tm))))
                f1.write(chunk)
                time.sleep(0.05)

            total_sz += dlsz
            sys.stdout.write(
                '\nSpent: {:.2f}s\nSize: {}\n\n'.format(
                    time.clock() - tm,
                    human_size(dlsz)))

    total_spend = time.clock() - total_start_tm
    sys.stdout.write(
        '\n\nTotal Spent: {:.2f}\n'
        'Total Size: {}\n'
        'Average Download Speed: {}/s\n'.format(
        total_spend, human_size(total_sz), human_size(total_sz / total_spend)))

if __name__ == '__main__':
    logging.basicConfig(
        level = logging.DEBUG,
        format = '[%(levelname)s] %(message)s')
    logging.info('Jac Animation Downloader')
    if len(sys.argv) >= 3 and sys.argv[1] == '-u':
        l = get_jac_video(sys.argv[2])
        dl_googledrive_video(l)
    elif len(sys.argv) >= 3 and sys.argv[1] == '-uu':
        l = get_jac_video_passwd(sys.argv[2])
        dl_googledrive_video(l)
    elif len(sys.argv) >= 3 and sys.argv[1] == '-f':
        l = []
        for line in open(sys.argv[2]):
            (videoid, filename) = line.split()
            l.append((videoid, filename))
        dl_googledrive_video(l)
    else:
        logging.info('Usage: {} [options]'.format(sys.argv[0]))
        logging.info('Options:')
        logging.info('    -f [file containing urls and filenames]')
        logging.info('    -u [index page URL]')
        logging.info('    -uu [index page URL] (new password-protected version)')

    # dl_googledrive_video([('0B1H-WTo5XmcrdDlPYm1YSXZMMTQ', 'xx.mp4')])
    # https://www.googleapis.com/drive/v3/files/0B62NacqK6vZnRVMtSDFLbkVEUGs
