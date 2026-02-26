import re
import sys
from pathlib import Path

from yt_dlp.extractor.common import InfoExtractor

sys.path.insert(0, str(Path(__file__).parent))
from .myvidplay import MyVidPlayIE
from .streampoi import StreamPoiIE


# jangan protes kalo kualitas kode nya jelek
# gw bukan programmer / yang ngerti banget python
# gw cuma iseng belajar aja
class NekoPoiIE(InfoExtractor): # dosa di tanggung senidri!!
    IE_NAME = 'nekopoi'
    _VALID_URL = r'https://nekopoi\.care/(?P<slug>[\w-]+)/?$'
    _EMBED_REGEX =[
        r'https://nekopoi\.care/[\w-]+-episode-\d+-subtitle-indonesia/'
    ]
    _TESTS = [{
        'url': 'https://nekopoi.care/l2d-sepongan-columbina-bagai-vakum-penghisap-sperma-genshin-impact',
        'info_dict': {
            'id': 'l2d-sepongan-columbina-bagai-vakum-penghisap-sperma-genshin-impact',
            'title': 'Sepongan Columbina Bagai Vakum Penghisap Sperma! – Genshin Impact',
            'ext': 'mp4',
        },
        'params': {'skip_download': True},
    }]

    def __init__(self, downloader=None):
        super().__init__(downloader)
        if downloader:
            self.set_downloader(downloader)

        self.extractor_map = {
            'myvidplay': self._extract_myvidplay,
            'streampoi': self._extract_streampoi,
            'vidnest': self._extract_vidnest,
        }

    def _real_initialize(self):
        if not self.get_param('cookiesfrombrowser'):
            self.report_warning('pake --cookies-from-browser woy!!')
        if not self._get_cookies('https://nekopoi.care').get('cf_clearance'):
            raise self.StopExtraction('No cf_clearance! Mungkin kena proteksi, coba refresh page Nekopoi!')

    def _extract_myvidplay(self, url, webpage):
        ie = MyVidPlayIE(self._downloader)
        return ie._extract_from_webpage(url, webpage)

    def _extract_streampoi(self, url, webpage):
        ie = StreamPoiIE(self._downloader)
        return ie._extract_from_webpage(url, webpage)

    def _extract_vidnest(self, url, webpage):
        return self._extract_jwplayer_data(webpage, 'jwplayer', require_title=False)['formats']

    @staticmethod
    def _get_urls(webpage,
                  pattern=r'<iframe\s*src="(https://(?:vidnest|bigshare|myvidplay|streampoi)\.(?:io|com|live)[^"]+)'):
        urls = re.findall(pattern, webpage, re.DOTALL)
        return urls or []

    def _extract(self, url):
        """pake loop ajah biar ga kebanyakan if else"""
        webpage = self._download_webpage(url, 'webpage URL')

        for site_name, extractor in self.extractor_map.items():
            if site_name in url:
                self.write_debug(f'Using extractor: {site_name}')
                return extractor(url, webpage)

    def _real_extract(self, url):
        self.to_screen('⚠️ DOSA DI TANGGUNG SENDIRI!!')
        slug = self._match_valid_url(url).group('slug')
        webpage = self._download_webpage(url, slug)
        video_title = self._og_search_title(webpage)
        video_id = self._html_search_regex(r'<link\s*rel=shortlink\s*href=\'.*?(\d+)\'><link',
                                           webpage, name='video id', fatal=False, default=slug)
        urls = self._get_urls(webpage)
        formats = []
        if urls and isinstance(urls, list):
            for url in urls:
                results = self._extract(url)
                if isinstance(results, list): # jika list extend biar ga list in list
                    formats.extend(results)
                if isinstance(results, dict): # jika dictionary append
                    formats.append(results)
        return {
            'id': video_id,
            'title': video_title,
            'formats': formats,
        }


class NekoPoiPlaylistIE(NekoPoiIE): # ERROR: url nya mirip kaya diatas, susah bedain
    IE_NAME = 'nekopoi playlist'
    _VALID_URL = r'https://nekopoi\.care/(?P<genre>hentai|jav)/(?P<slug>[^/?]+)'  # TODO: benerin regex
    _WORKING = False
    _ENABLED = False

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        slug = mobj.group('slug')
        genre = mobj.group('genre')
        webpage = self._download_webpage(url, slug)
        video_title = self._og_search_title(webpage)
        # Extract video ID
        video_id = self._html_search_regex(
            r'<link\s*rel=shortlink\s*href=\'.*?(\d+)\'><link', webpage,
            name='video id', fatal=False, default=slug)
        # Get URLs with pattern
        pattern = rf'<a\s*href="(https://nekopoi\.care/{slug}(?:-episode-\d(?:-subtitle-indonesia)))/"\s*class="nk-episode-card">'
        urls = self._get_urls(webpage, pattern)
        self.write_debug(f'Found URLs: {urls}')

        entries = []
        for url in urls:
            entries.append(self.url_result(
                url=url, ie=NekoPoiIE.ie_key(),
                video_title=video_title,
                video_id=video_id,
                tags=genre,
            ))

        return self.playlist_result(
            entries=entries,
            playlist_id=video_id,
            playlist_title=video_title,
        )
