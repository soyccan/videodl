# TODO: scan for Ctrl-C (SIGTERM) signal

import m3u8
import requests
from Crypto.Cipher import AES

import time
import sys
import re
import json
import os
import subprocess
import logging
import operator
import threading
import tempfile
import queue
import urllib.parse


class HLSDownloader:
    MAX_ATTEMPTS = 10
    VERIFY_URL = True # set to False for debugging
    NUM_THREAD = 10

    def __init__(self, playlist_url, filename, get_idx, segment_dir=None, headers=None):
        if headers:
            self.headers = headers
        else:
            self.headers = {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:61.0) Gecko/20100101 Firefox/61.0'}
        self.key = b''
        self.segments = []
        self.failed_segments = []

        self.start_time = time.time()
        self.download_size = 0
        self.download_size_lock = threading.Lock()
        self.download_finished = False

        self.filename = filename
        self.get_idx = get_idx
        self.segment_dir = segment_dir
        if not self.segment_dir:
            self.segment_dir = tempfile.mkdtemp()

        self.playlist_url = playlist_url
        self._load_playlist()

    def _show_status(self):
        while not self.download_finished:
            time.sleep(2)
            sys.stdout.write(
                '\r'
                f'Size: { self.download_size / 1048576 : 4.2f} MB'
                '\t\t'
                f'Rate: { self.download_size / (time.time() - self.start_time) / 1024 : 4.2f} KB/s')
            # TODO: download time should not count in program time

    def download(self):
        logging.info('start downloading, filename: %s, total segments: %d, segment_dir: %s',
                     self.filename, len(self.segments), self.segment_dir)

        try:
            os.mkdir(self.segment_dir)
        except FileExistsError:
            pass

        segment_queue = queue.Queue()
        workers = []
        for item in self.segments:
            segment_queue.put(item)
        for _ in range(self.NUM_THREAD):
            thrd = threading.Thread(target=self._download_segment, args=(segment_queue,))
            thrd.start()
            workers.append(thrd)

        status_thrd = threading.Thread(target=self._show_status)
        status_thrd.start()

#          segment_queue.join() # TODO: necessary?
        for thrd in workers:
            thrd.join()

        self.download_finished = True
        status_thrd.join()

        logging.warning('Re-download failed segments')
        logging.debug(self.failed_segments)
        assert segment_queue.empty()
        for item in self.failed_segments:
            segment_queue.put(item)
        while not segment_queue.empty():
            self._download_segment(segment_queue)

        self._concat()

    def _download_segment(self, segment_queue):
        while not segment_queue.empty():
            seg = segment_queue.get()
            idx = self.get_idx(seg.uri)
            target_url = urllib.parse.urljoin(self.playlist_url, seg.uri)

            if os.path.exists(str(idx)+'.ts'):
                logging.info('ignoring %d.ts', idx)
                segment_queue.task_done()
                continue

            logging.debug('Downloading segment %d.ts', idx)

            attempts = 0
            while attempts < self.MAX_ATTEMPTS:
                try:
                    attempts += 1
                    logging.debug('urlopen %s', target_url)

                    ts_data = requests.get(target_url,
                                           headers=self.headers,
                                           verify=self.VERIFY_URL,
                                           timeout=10).content
                    self.download_size_lock.acquire()
                    self.download_size += len(ts_data)
                    self.download_size_lock.release()

                except BaseException as e:
                    logging.warning('failed on %s: %s, retrying', target_url, str(e))

                else:
                    break
            if attempts >= self.MAX_ATTEMPTS:
                logging.error('maximum attempts exceeded %s, skipping %d.ts', target_url, idx)
                self.failed_segments.append(seg)
                segment_queue.task_done()
                continue

            if self.key:
                cipher = AES.new(self.key, AES.MODE_CBC, IV=b'%016x' % idx)
                d_ts_data = cipher.decrypt(ts_data)
            else:
                d_ts_data = ts_data

            open(os.path.join(self.segment_dir, str(idx)+'.ts'), 'wb').write(d_ts_data)
            segment_queue.task_done()

    def _concat(self):
        cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-protocol_whitelist', 'file,pipe',
            '-i', '-',
            '-c', 'copy',
            self.filename]

        filelist = b''
        for seg in self.segments:
            seg_filename = os.path.join(self.segment_dir,
                                        str(self.get_idx(seg.uri))+'.ts')
            filelist += 'file {}\n'.format(seg_filename).encode()

        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        proc.communicate(input=filelist)
        proc.wait()

    def clean_segments(self):
        for seg in self.segments:
            os.remove(os.path.join(
                self.segment_dir, str(self.get_idx(seg.uri))+'.ts'))

    def _load_playlist(self):
        logging.info('Loading %s', self.playlist_url)

        m3u8obj = m3u8.loads(requests.get(self.playlist_url,
                                          headers=self.headers,
                                          verify=self.VERIFY_URL).text)
        self.segments = sorted(m3u8obj.segments,
                               key=lambda x: int(self.get_idx(x.uri)))

        if m3u8obj.playlists:
            # if there are multiple resolution, choose best
            m3u8obj.playlists.sort(key=operator.attrgetter('stream_info.resolution'),
                                   reverse=True)
            target_url = urllib.parse.urljoin(self.playlist_url,
                                              m3u8obj.playlists[0].uri)

            logging.info('Loading %s', target_url)
            logging.info('Resolution: %s', m3u8obj.playlists[0].stream_info.resolution)

            m3u8obj = m3u8.loads(requests.get(target_url,
                                              headers=self.headers,
                                              verify=self.VERIFY_URL).text)

            self.segments.clear()
            for seg in m3u8obj.segments:
                self.segments.append(seg)

        if m3u8obj.keys and m3u8obj.keys[0]:
            logging.info('key found')

            self.key = requests.get(m3u8obj.keys[0].uri,
                                    headers=self.headers,
                                    verify=self.VERIFY_URL).content

            logging.debug('key: %s', self.key)

def test():
    logging.basicConfig(level='DEBUG')
    cookie='__cfduid=d193af2b80c798c57be2500abe51bcb581573446600; BAHAID=chengkongtw; BAHANICK=soytw; BAHAENUR=da5e55df5c8f98fd232c6b6a9f6d1455; BAHARUNE=fc7fbdb9c37f02884a0fa0ae7b55d3cb161386f1161468f21ad3856678fe73961513090885e12070ce17; BAHALV=5; BAHAFLT=1488545856; MB_BAHAID=chengkongtw; MB_BAHANICK=soytw; MB_BAHARUNE=fc7fbdb9c37f02884a0fa0ae7b55d3cb161386f1161468f21ad3856678fe73961513090885e12070ce17; avtrv=1579871792030; ckM=626696263; ckBH_lastBoard=[[%229009%22%2C%22TYPE-MOON%20%E7%B3%BB%E5%88%97%22]%2C[%2260076%22%2C%22%E5%A0%B4%E5%A4%96%E4%BC%91%E6%86%A9%E5%8D%80%22]%2C[%2226742%22%2C%22Fate/Grand%20Order%22]%2C[%2242214%22%2C%22%E7%AD%92%E4%BA%95%E5%A4%A7%E5%BF%97%20%E4%BD%9C%E5%93%81%E9%9B%86%EF%BC%88%E6%88%91%E5%80%91%E7%9C%9F%E7%9A%84%E5%AD%B8%E4%B8%8D%E4%BE%86%EF%BC%81%EF%BC%89%20%22]%2C[%2246270%22%2C%22%E9%87%91%E7%94%B0%E9%99%BD%E4%BB%8B%20%E4%BD%9C%E5%93%81%E9%9B%86%EF%BC%88%E5%AF%84%E5%AE%BF%E5%AD%B8%E6%A0%A1%E7%9A%84%E8%8C%B1%E9%BA%97%E8%91%89%EF%BC%89%20%22]%2C[%2247333%22%2C%22Princess%20Principal%22]%2C[%2244991%22%2C%22%E6%9E%9C%E7%84%B6%E6%88%91%E7%9A%84%E9%9D%92%E6%98%A5%E6%88%80%E6%84%9B%E5%96%9C%E5%8A%87%E6%90%9E%E9%8C%AF%E4%BA%86%22]]; buap_modr=p001; buap_puoo=p101; _ga=GA1.1.941738174.1576603948; __gads=ID=ac98a7d8d6299198:T=1576603948:S=ALNI_MZzMaZSzkSK4VEhggZzvOK0UIyAiA; _ga_MT7EZECMKQ=GS1.1.1579873159.37.1.1579876603.0; hahamut_topBar_notify=null; _gid=GA1.3.174118962.1579790911; ckBahaAd=-------07----------------; _gat=1'
    headers={
        'Host': 'gamer-cds.cdn.hinet.net',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:72.0) Gecko/20100101 Firefox/72.0',
        'Accept': '*/*',
        'Accept-Language': 'zh-TW,en-US;q=0.7,en;q=0.3',
        'Accept-Encoding': 'gzip, deflate, br',
        'Origin': 'https://ani.gamer.com.tw',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Referer': 'https://ani.gamer.com.tw/animeVideo.php?sn=14452',
        'TE': 'Trailers',
        'Cookie': cookie
    }
    url='https://gamer-cds.cdn.hinet.net/vod_gamer/_definst_/smil:gamer2/100033d5fb0dde1b587e298d40591d936f5042a0/hls-ae-2s.smil/playlist.m3u8?token=fVhGsQqwkdGxQDRLeEo80g&expires=1579883277&bahaData=chengkongtw:14452:1:PC:1f953'
    get_idx = lambda x: int(re.search(r'([0-9]+).ts', x).group(1))
    h = HLSDownloader(url, 'a.mp4', get_idx, 'tmp', headers)
    h.download()

def main():
    try:
        url = sys.argv[1]
        destfile = sys.argv[2]
    except IndexError:
        print(f'Usage: {sys.argv[0]} url destfile')
        exit(1)

    get_idx = lambda x: int(re.search(r'([0-9]+).ts', x).group(1))
    h = HLSDownloader(url, destfile, get_idx)
    h.download()

if __name__ == '__main__':
    if '--debug' in sys.argv:
        logging.basicConfig(level='DEBUG')
        logging.debug('enter debug mode')
    else:
        logging.basicConfig(level='INFO')

    main()

###
# iv=$(printf '%016x' $index)
# openssl aes-128-cbc -d -in media_0.ts -out media_decryptd_0.ts -nosalt -iv $iv -K $strkey
