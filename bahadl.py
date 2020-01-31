# TODO: open socket for authentication (gamers.com.tw), auto retrieve cookies
# TODO: integrate with dl-hls.py is misc.git
# TODO: ffmpeg-python module for concat

from urllib.parse import urlsplit
import time
import random
import math
import re
import json
import datetime
import logging
import pprint
import subprocess
import io
import os

from bs4 import BeautifulSoup
import requests

from hlsdl import HLSDownloader


class Anime:
    # TODO
    # set to False for debugging (burp)
    verify = False

    # when SSL certificate validating is disabled for debugging, ignore the warnings
    if not verify:
        requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

    def __init__(self, anime_sn):
        self.headers = {
            'Connection': 'close',
            'Accept': '*/*',
            'DNT': '1',
            'X-Requested-With': 'XMLHttpRequest',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3679.0 Safari/537.36',
            'Referer': f'https://ani.gamer.com.tw/animeVideo.php?sn={anime_sn}',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7,es;q=0.6',
            'Origin': 'https://ani.gamer.com.tw',
            'Cookie': '__cfduid=d193af2b80c798c57be2500abe51bcb581573446600; BAHAID=chengkongtw; BAHANICK=soytw; BAHAENUR=7f43875ed6b6f6c61ed8d0ad3432bf79; BAHARUNE=bdd93a4c64e6eec4449475d77297135e209fe58120a0c78216f2642d7525fad586a323091a13df9370bc; BAHALV=5; BAHAFLT=1488545856; MB_BAHAID=chengkongtw; MB_BAHANICK=soytw; MB_BAHARUNE=bdd93a4c64e6eec4449475d77297135e209fe58120a0c78216f2642d7525fad586a323091a13df9370bc; avtrv=1580439208019; ckM=626696263; ckBH_lastBoard=[[%2226742%22%2C%22Fate/Grand%20Order%22]%2C[%229009%22%2C%22TYPE-MOON%20%E7%B3%BB%E5%88%97%22]%2C[%2246270%22%2C%22%E9%87%91%E7%94%B0%E9%99%BD%E4%BB%8B%20%E4%BD%9C%E5%93%81%E9%9B%86%EF%BC%88%E5%AF%84%E5%AE%BF%E5%AD%B8%E6%A0%A1%E7%9A%84%E8%8C%B1%E9%BA%97%E8%91%89%EF%BC%89%20%22]%2C[%2260076%22%2C%22%E5%A0%B4%E5%A4%96%E4%BC%91%E6%86%A9%E5%8D%80%22]%2C[%2242388%22%2C%22%E5%B7%9D%E5%8E%9F%E7%A4%AB%20%E4%BD%9C%E5%93%81%E9%9B%86%22]%2C[%2242265%22%2C%22FLIPFLOPs%20%E4%BD%9C%E5%93%81%E9%9B%86%EF%BC%88%E9%81%94%E7%88%BE%E6%96%87%E9%81%8A%E6%88%B2%EF%BC%89%20%22]%2C[%2245499%22%2C%22%E5%9C%A8%E5%9C%B0%E4%B8%8B%E5%9F%8E%E5%B0%8B%E6%B1%82%E9%82%82%E9%80%85%E6%98%AF%E5%90%A6%E6%90%9E%E9%8C%AF%E4%BA%86%E4%BB%80%E9%BA%BC%22]%2C[%2243641%22%2C%22%E9%B4%A8%E5%BF%97%E7%94%B0%E4%B8%80%20%E4%BD%9C%E5%93%81%E9%9B%86%EF%BC%88%E9%9D%92%E6%98%A5%E8%B1%AC%E9%A0%AD%E5%B0%91%E5%B9%B4%20%E7%B3%BB%E5%88%97%EF%BC%89%20%22]%2C[%2247551%22%2C%22%E4%BA%94%E7%AD%89%E5%88%86%E7%9A%84%E6%96%B0%E5%A8%98%20%22]%2C[%2242214%22%2C%22%E7%AD%92%E4%BA%95%E5%A4%A7%E5%BF%97%20%E4%BD%9C%E5%93%81%E9%9B%86%EF%BC%88%E6%88%91%E5%80%91%E7%9C%9F%E7%9A%84%E5%AD%B8%E4%B8%8D%E4%BE%86%EF%BC%81%EF%BC%89%20%22]]; buap_modr=p001; buap_puoo=p101; _ga=GA1.1.941738174.1576603948; __gads=ID=ac98a7d8d6299198:T=1576603948:S=ALNI_MZzMaZSzkSK4VEhggZzvOK0UIyAiA; _ga_MT7EZECMKQ=GS1.1.1580438704.61.1.1580439241.0; _gid=GA1.3.811410919.1580142268; ckBahaAd=-----0-12----9-----------; hahamut_topBar_notify=false; _gat=1',
        }

        b = BeautifulSoup(
            requests.get(f'https://ani.gamer.com.tw/animeVideo.php?sn={anime_sn}',
                         verify=self.verify).text, 'html.parser')

        self.title = b.find(class_='anime_name').find('h1').text
        self.title = re.sub(r'\[[0-9]+\]$', '', self.title)
        logging.debug(self.title)

        self.episodes = []
        ul = b.find('section', class_='season').find('ul')
        if ul:
            for li in ul:
                self.episodes.append({
                    'title': self.title,
                    'index': li.find('a').text,
                    'anime_sn': li.find('a')['href'][4:],
                    'stream_url': '' # get when used
                })
        else:
            # if there's only one episode (movie)
            self.episodes.append({
                'title': self.title,
                'index': '1',
                'anime_sn': anime_sn,
                'stream_url': '' # get when used
            })

        logging.debug('\n' + pprint.pformat(self.episodes))

    def __str__(self):
        return f'<Anime title="{self.title}" len(episodes)="{len(self.episodes)}">'

    def __getitem__(self, index):
        # WARNING: index may contain floating number (i.e. 10.5) or string (i.e. 1a)
        return [ep for ep in self.episodes if ep['index'] == str(index)][0]

    def __iter__(self):
        return iter(self.episodes)

    def get_stream_url(self, anime_sn):
        logging.info(f'getting stream_url for {self.title} sn={anime_sn}')
        logging.info(f'URL: https://ani.gamer.com.tw/animeVideo.php?sn={anime_sn}')
        s = requests.Session()

        # adlist
        r = s.get(
            f'https://i2.bahamut.com.tw/JS/ad/animeVideo2.js?v={datetime.datetime.today().strftime("%Y%m%d%H")}',
            verify=self.verify, headers=self.headers)
        adlist = json.loads(re.search(r'adlist = (.*);', r.text).group(1))
        # e, t = map(int, re.search(r'iK = getAdIndex\(([0-9]+), ([0-9]+)\);', r.text).group(1, 2))
        # ad = adlist[getAdIndex(e, t)]
        # logging.debug(adlist, e, t, ad)


        # device id
        r = s.get('https://ani.gamer.com.tw/ajax/getdeviceid.php?id=', verify=self.verify, headers=self.headers)
        s.cookies['ckBahaAd'] = '----------------'
        devid = r.json()['deviceid']

        # try watch AD and fetch streaming URL
        attempt = 0
        while attempt < 10:
            attempt += 1

            ad = random.choice(adlist)

            # token
            r = s.get(f'https://ani.gamer.com.tw/ajax/token.php?adID={ad[0]}&sn={anime_sn}&device={devid}&hash={self.Hash()}', verify=self.verify, headers=self.headers)
            # logging.debug(r, r.request.url, r.text)


            # unlock & checklock
            r = s.get(f'https://ani.gamer.com.tw/ajax/unlock.php?sn={anime_sn}&ttl=0', verify=self.verify, headers=self.headers)
            r = s.get(f'https://ani.gamer.com.tw/ajax/checklock.php?device={devid}&sn={anime_sn}', verify=self.verify, headers=self.headers)


            # ad start & end
            r = s.get(f'https://ani.gamer.com.tw/ajax/videoCastcishu.php?s={ad[2]}&sn={anime_sn}', verify=self.verify, headers=self.headers)
            r = s.get(f'https://ani.gamer.com.tw/ajax/videoCastcishu.php?s={ad[2]}&sn={anime_sn}&ad=end', verify=self.verify, headers=self.headers)


            # video start
            r = s.get(f'https://ani.gamer.com.tw/ajax/videoStart.php?sn={anime_sn}', verify=self.verify, headers=self.headers)


            # playlist URL (M3U8)
            r = s.get(f'https://ani.gamer.com.tw/ajax/m3u8.php?sn={anime_sn}&device={devid}', verify=self.verify, headers=self.headers)
            logging.debug('m3u8 response: ' + r.text)
            playlist = json.loads(r.text).get('src')
            if playlist:
                playlist = 'https:' + playlist
                break


        # load playlist
        # -- !ORIGIN IS IMPORTANT! --
        # r = s.get(playlist, verify=verify, headers={'Origin': 'https://ani.gamer.com.tw', **headers})
        # logging.debug(r.text)

        return playlist

    def download(self, episode_indices=[], filenames=[], keep_segments=True):
        """episode_indices: list of str or int
           filenames: list of str
        """
        episode_indices = list(map(str, episode_indices))
        if not episode_indices:
            episode_indices = [ep['index'] for ep in self.episodes]

        if not filenames:
            for idx in episode_indices:
                if len(idx) < 2: # 01 02 ... 10 11 ...
                    idx = '0' + idx
                filenames.append(idx + '.mp4')

        if len(filenames) != len(episode_indices):
            raise ValueError('filenames are not sufficiently given')

        d = dict(zip(episode_indices, filenames))
        for ep in self.episodes:
            if ep['index'] in d:
                ep['stream_url'] = self.get_stream_url(ep['anime_sn'])
                get_idx = lambda x: int(re.search(r'([0-9]+).ts', x).group(1))

                h = HLSDownloader(
                    ep['stream_url'],
                    d[ep['index']],
                    get_idx,
                    segment_dir=None,
                    headers=self.headers)
                h.download()

                if not keep_segments:
                    h.clean_segments()


    @staticmethod
    def getAdIndex(e, t):
        if 1 > t or 0 > e or e > 64:
            return 0

        # n = getCookie("ckBahaAd")
        n = ''
        o = 0

        if not n:
            o = int(random.random() * (t - 1))
        # else:
        #     o = fromCode62(n.charAt(e))

        if 0 > o:
            o = int(random.random() * (t - 1))
        else:
            o = (o + 1) % t
        # document.cookie = "ckBahaAd=" + generateCkGamerAdString(n, e, o) + ";expires=" + (new Date).toDateString() + " 23:59:59 UTC+0800;domain=.gamer.com.tw"

        return o

    @staticmethod
    def Hash():
        # JS code:
        # var t = (new Date).getTime();
        # window.performance && "function" == typeof window.performance.now && (t += performance.now());
        # var e = "xxxxxxxxxxxx".replace(/[x]/g, function(e) {
        #     var n = (t + 16 * Math.random()) % 16 | 0;
        #     return t = Math.floor(t / 16),
        #     ("x" == e ? n : 3 & n | 8).toString(16)
        # });
        # return e
        r = ''
        t = time.time() * 1000
        for _ in range(12):
            n = int(t + 16 * random.random()) % 16
            t = math.floor(t / 16)
            r += '%x' % n
        return r




# logging.basicConfig(level='DEBUG')
logging.basicConfig(level='INFO')
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)






a = Anime(90)
a.download(list(range(9,23)), keep_segments=False)
#  a = Anime(14521)
#  a.download([4])
