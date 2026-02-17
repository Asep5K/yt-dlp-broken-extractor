import itertools
import re
import sys
from pathlib import Path

from yt_dlp.extractor.common import InfoExtractor, SearchInfoExtractor

sys.path.insert(0, str(Path(__file__).parent))
from .myvidplay import MyVidPlayIE
from .streampoi import StreamPoiIE


# dosa di tanggung senidri!!
class NekoPoiIE(InfoExtractor):
    IE_NAME = 'nekopoi'
    _VALID_URL = r'https://nekopoi\.care/(?P<slug>[^/?]+)'
    _TESTS = [{
        'url': 'https://nekopoi.care/l2d-sepongan-columbina-bagai-vakum-penghisap-sperma-genshin-impact',
        'info_dict': {
            'id': 'l2d-sepongan-columbina-bagai-vakum-penghisap-sperma-genshin-impact',
            'title': 'Sepongan Columbina Bagai Vakum Penghisap Sperma! – Genshin Impact',
            'ext': 'mp4',
        },
        'params': {'skip_download': True},
    }]

    def __init__(self):

        self.extractor_map = {
            'myvidplay': lambda u, w: MyVidPlayIE(self._downloader)._extract_from_webpage(u, w),
            'streampoi': lambda u, w: StreamPoiIE(self._downloader)._extract_from_webpage(u, w),
            'vidnest': lambda u, w: self._extract_jwplayer_data(w, 'jwplayer', require_title=False)['formats'],
        }


    def _clean_title(self, webpage):
        """buat ngebersihin title doang"""
        title = self._html_extract_title(webpage)
        return self._html_search_regex(
            r'(?:[.*])?\s(.*)\s– NekoPoi',
                title, name='video title', default=title, fatal=False)


    @staticmethod
    def _get_urls(webpage, pattern=None):
        """Extract all video embed links from NekoPoi page"""
        if not pattern: # ini gw lupa bigshare dapat darimana, tapi ya biarin lah 😃
            pattern = r'<iframe\ssrc=(https://(?:vidnest|bigshare|myvidplay|streampoi)\.(?:io|com)[^\s]+)'

        urls = re.findall(pattern, webpage, re.DOTALL)
        return urls or []


    def _extract(self, url):
        """pake loop ajah biar ga kebanyakan if else"""
        self._sleep(10, url, #sleeeeeeeeeeeeeeeeeep
                msg_template='%(video_id)s: sleep %(timeout)s detik biar gak kena limit',
            )
        webpage = self._download_webpage(url, 'webpage URL')

        for site_name, extractor in self.extractor_map.items():
            if site_name in url:
                self.write_debug(f'Using extractor: {site_name}')
                return extractor(url, webpage)


    def _real_extract(self, url):
        self.to_screen('⚠️ DOSA DI TANGGUNG SENDIRI!!')

        mobj = self._match_valid_url(url)
        slug = mobj.group('slug')

        webpage = self._download_webpage(url, slug)
        video_title = self._clean_title(webpage)
        video_id = self._html_search_regex(r'<link\s*rel=shortlink\s*href=\'.*?(\d+)\'><link',
                                        webpage, name='video id', fatal=False, default=slug)
        urls = self._get_urls(webpage)

        formats = []
        if urls and isinstance(urls, list):
            for url in urls:

                results = self._extract(url)
                # jika list extend biar ga list in list
                if isinstance(results, list):
                    formats.extend(results)

                # jika dictionary append
                if isinstance(results, dict):
                    formats.append(results)
        self._remove_duplicate_formats(formats)
        return {
            'id': video_id,
            'title': video_title,
            'formats': formats,
        }


class NekoPoiEpisodeIE(NekoPoiIE):
    IE_NAME = 'nekopoi playlist'
    _VALID_URL = r'https://nekopoi\.care/(?P<genre>hentai|jav)/(?P<slug>[^/?]+)'

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        slug = mobj.group('slug')
        genre = mobj.group('genre')

        webpage = self._download_webpage(url, slug)

        # Extract title
        video_title = self._html_extract_title(webpage)

        # Extract video ID
        video_id = self._html_search_regex(
            r'<link\s*rel=shortlink\s*href=\'.*?(\d+)\'><link',
            webpage,
            name='video id',
            fatal=False,
            default=slug,
        )

        # Get URLs with pattern
        pattern = r'leftoff><a\s*href=(https://.*?(?:-episode-\d+)*[^/?])>Episode'
        urls = self._get_urls(webpage, pattern)

        self.write_debug(f'Found URLs: {urls}')


        entries = []
        for url in urls:
            entries.append(self.url_result(
                url=url,
                ie=NekoPoiIE,
                video_title=video_title,
                video_id=video_id,
                genre=genre,
            ))

        return self.playlist_result(
            entries=entries,
            playlist_id=video_id,
            playlist_title=video_title,
        )


class NekoPoiSearchIE(SearchInfoExtractor, NekoPoiIE):
    IE_NAME = 'nekopoi:search'
    _SEARCH_KEY = 'nekopoi'

    def _search_results(self, query):
        base_url = f'https://nekopoi.care/search/{query}'

        for page_num in itertools.count(0): #maximal 3 page, tapi ya biarin lah 😃
            url_page = f'{base_url}/page/{page_num}'

            webpage = self._download_webpage(url_page, f'Nekopoi page {page_num}',
                            errnote='mungkin salah judul, atau page nya udah habis!')

            pattern = r'</div><h2><a\shref=(https://nekopoi\.care[^>]+)'
            urls = self._get_urls(webpage, pattern)

            for url in urls:
                self.write_debug('Using Extractor NekoPoiIE!')
                yield self.url_result(url, ie=NekoPoiIE)
