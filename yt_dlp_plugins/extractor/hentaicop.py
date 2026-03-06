import json
import re
from base64 import b64decode

from yt_dlp.extractor.common import (
    InfoExtractor,
    SearchInfoExtractor,
)
from yt_dlp.utils import (
    LazyList,
    js_to_json,
    traverse_obj,
    urljoin,
)


class HenTaiCopIE(InfoExtractor):
    IE_NAME = 'hentaicop'
    _VALID_URL = r'https://hentaicop\.com/(?P<slug>[\w-]+)/?$'

    def _real_extract(self, url):
        slug = self._match_valid_url(url).group('slug')
        webpage = self._download_webpage(url, slug)
        title = self._html_extract_title(webpage) or self._og_search_title(webpage)
        return {
            'id': slug,
            'title': title or slug,
            'formats': LazyList(self._gen_formats(webpage, title)),
            'age_limit': 18,
        }

    def _gen_formats(self, webpage, title_or_slug):
        for data_json in self._get_json(webpage):
            if not data_json:
                continue
            url = traverse_obj(data_json, ('sources', 0, 'file'))
            self.write_debug(f'm3u8 url: {url}')
            yield from self._extract_m3u8_formats(url, title_or_slug, fatal=False)

    def _search_b64(self, webpage):
        for b64 in re.finditer(r'value="(?P<b64>[^"]+)"\s*data-index=', webpage, re.S):
            b64_iframe = b64decode(b64.group('b64')).decode()
            if b64_iframe and 'dood' not in b64_iframe.lower():
                """
                DOOD [dood id="sezoxqknjhcb"]:
                [Piracy] Extracting URL: https://dood.wf/d/sezoxqknjhcb
                ERROR: [Piracy] This website is no longer supported since it has been determined to be primarily used for piracy.
                    DO NOT open issues for it
                """
                url = self._html_search_regex(r'src="([^"]+)', b64_iframe, 'play.php')
                self.write_debug(f'php url: {url}')
                if url and url.startswith(('/', '/play.php')):
                    url = urljoin('https://hentaicop.com', url)
                    self.write_debug(f'full php url: {url}')
                    yield url

    def _get_json(self, webpage):
        # var config = {"key":"G4m70uWOpSGvQRLA18vxtYWL6Pecz3SDxPH\/RxMXqtxypDZ5ERyjZl1HNpRVUJaw","title":"s2.9385b44eef82e4b1ce998.site master.m3u8","autostart":false,"repeat":false,"mute":false,"rewind":false,"image":"https:\/\/hepidrive.online\/poster\/?url=R0tET1dXam5Mdm9vSnQwdXh3QTVsVHl1aXlQZVN2cGlJR3NCb2xmdHdaQUpDRjMwL0ZTcDVKMDlSNmJJNWNsdTo67jAkPXy5lnIrLXQCIC9UHA%3D%3D","abouttext":"GunDeveloper.com","aboutlink":"https:\/\/gundeveloper.com","tracks":[],"sources":[{"label":"Original","type":"hls","file":"https:\/\/s2.9385b44eef82e4b1ce998.site\/hls\/anime\/folder1\/server5\/,Seifuku_wa_Kita_mama_de_01_360p,Seifuku_wa_Kita_mama_de_01_480p,Seifuku_wa_Kita_mama_de_01_720p,Seifuku_wa_Kita_mama_de_01_1080p,.mp4.urlset\/master.m3u8"}],"sharing":false,"controls":true,"hlshtml":true,"primary":"html5","preload":"auto","cast":{"appid":"00000000"},"androidhls":true,"stretching":"uniform","displaytitle":false,"displaydescription":false,"playbackRateControls":false,"captions":{"color":"#ffff00","backgroundOpacity":0},"aspectratio":"16:9","floating":false};
        for url in self._search_b64(webpage):
            jw_page = self._download_webpage(url, 'jw page')
            raw_json = self._html_search_regex(r'var\s*config\s*=\s*([^;]+)', jw_page, 'jwson', fatal=False)
            if raw_json:
                clean_json = json.loads(js_to_json(raw_json))
                yield clean_json


class HenTaiCopSeriesIE(HenTaiCopIE):
    IE_NAME = 'hentaicop:series'
    # 'https://hentaicop.com/series/android-wa-keiken-ninzuu-ni-hairimasu-ka-uncensored/'
    _VALID_URL = r'https://hentaicop.com/series/(?P<slug>[\w-]+)/?$'

    def _real_extract(self, url):
        slug = self._match_valid_url(url).group('slug')
        webpage = self._download_webpage(url, slug)
        title = self._og_search_title(webpage) or self._html_extract_title(webpage)
        entries = []
        for urls in re.finditer(r'data-index="\d+">\s*<a\s*href="(?P<url>[^"]+)">', webpage, re.S):
            url = urls.group('url')
            if url:
                entries.append(self.url_result(url=url, ie=HenTaiCopIE.ie_key()))
        return self.playlist_result(entries=reversed(entries), playlist_id=slug, playlist_title=title)


class HenTaiCopRandomSearchIE(SearchInfoExtractor):
    IE_NAME = 'hentaicop:search'
    _SEARCH_KEY = 'hentaicoprandom'

    def _search_results(self, query):
        ajax = 'https://hentaicop.com/wp-admin/admin-ajax.php'
        query = {
            'action': 'ts_ac_do_search',
            'ts_ac_query': query,
        }
        data_json = self._download_json(ajax, 'jesom', query=query)
        all_posts = traverse_obj(data_json, ('anime', ..., 'all', ...))
        for post in all_posts:
            url = post.get('post_link')
            title = post.get('post_title')
            video_id = post.get('ID')
            if url and title:
                yield self.url_result(
                    url=url, ie=HenTaiCopSeriesIE.ie_key(),
                    video_id=video_id, video_title=title)


class HenTaiCopSearchIE(SearchInfoExtractor):
    IE_NAME = 'hentaicop:search'
    _SEARCH_KEY = 'hentaicop'
    _WORKING = False
    _ENABLED = False

    def _search_results(self, query):  # PUSING MIKIR REGEX
        # 'https://hentaicop.com/?s=dou'
        webpage = self._download_webpage('https://hentaicop.com/', 'home page', query={'s': query})
        for _f in re.finditer(
            r'<a[^>]*href="(?P<url>[^"]+)"[^>]*itemprop="url"[^>]*title="(?P<title>[^"]+)"[^>]*>',
                webpage, re.S):
            pass
