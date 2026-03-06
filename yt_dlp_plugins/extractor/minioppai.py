import itertools
import json
import re
from base64 import b64decode
from urllib.parse import quote

from yt_dlp.extractor.common import (
    InfoExtractor,
    SearchInfoExtractor,
)
from yt_dlp.networking.exceptions import HTTPError
from yt_dlp.utils import (
    ExtractorError,
    decode_packed_codes,
    int_or_none,
    js_to_json,
    random_user_agent,
    str_or_none,
    traverse_obj,
    unescapeHTML,
    urljoin,
)


class MiniOppaiIE(InfoExtractor):
    IE_NAME = 'minioppai'
    _VALID_URL = r'https://minioppai\.org/(?P<slug>[\w-]+)/?$'
    _WORKING = False

    def _real_extract(self, url):
        slug = self._match_valid_url(url).group('slug')
        webpage = self._download_webpage(url, slug)
        formats = []
        subtitles = {}
        for format_data in self._build_formats(webpage):
            format_subs = format_data.pop('subtitles', {})
            subtitles = self._merge_subtitles(subtitles, format_subs)
            formats.append(format_data)

        return {
            'id': slug,
            'title': self._og_search_title(webpage),
            'thumbnail': self._og_search_thumbnail(webpage),
            'formats': formats,
            'subtitles': subtitles,
            'age_limit': 18,
        }

    def _build_formats(self, webpage):
        for _json in self._process_url(webpage):
            referer = _json.pop('referer')
            yield traverse_obj(
                _json, {
                    'url': ('sources', 0, 'file', {lambda r: self._is_url(r, referer=referer)}),
                    'height': ('height', {int_or_none}),
                    'quality': ('height', {lambda q: f'{q}p'}, {str_or_none}),
                    'subtitles': ('subtitles'),
                })

    def _is_url(self, url, referer):  # TODO: ikut ikutan nulis TODO doang
        headers = {
            'User-Agent': random_user_agent(),
            'referer': referer,
            'Range': 'bytes=0-',
        }
        if url.startswith('https'):
            return url
        """NI MASIH ERROR GATAU KENAPA"""
        if url.startswith(('/', '/stream')):
            try:
                # url = b64decode(url.split('/', maxsplit=4)[3]).decode()
                # self.write_debug(f'url kontol: {url}')
                # url_page = self._download_webpage(unquote(url), 'b64', headers=headers, timeout=10)
                url = 'https://tv.streampai.my.id' + url
                url_page = self._download_webpage(url, 'b64', headers=headers, timeout=10)
                # response = self._request_webpage(url, 'b64', headers=headers, encoding='utf-8')
                # if response:
                # url_page = self._webpage_read_content(response, url, 'resp')
                url = self._html_search_regex(r'href="([^"]+)">here', url_page, 'stupid')
                self.write_debug(f'url stupid: {url}')
                if url.startswith(('/', '/personal')):
                    url = urljoin('https://studentundipacid-my.sharepoint.com/', unescapeHTML(url))
                    self.write_debug(f'url: {url}')
                    return url
            except TypeError as e:
                raise ExtractorError(f'Gagal mendapatkan url dari {url_page}', cause=e, expected=True)
            except ExtractorError as e:
                if isinstance(e.cause, HTTPError) and e.cause.code == 429:
                    raise ExtractorError('Server sibuk, coba lagi nanti', expected=True)
                raise

    def _get_streampai_urls(self, webpage):
        # r'value="(?P<b64>\w?[^"]+)"\s*data-index="\d+">\s*(?P<res>[\d\w]+)?p?[^<]',
        for match in re.finditer(
            r"""(?x)
                value="(?P<b64>\w?[^"]+)"
                \s*data-index="\d+">
                \s*(?P<res>[\d\w]+)?p?[^<]""",
                webpage, re.DOTALL | re.IGNORECASE):
            try:
                html = b64decode(match.group('b64')).decode()
                url = self._html_search_regex(r'src="([^"]+)"', html, 'iframe')
                self.write_debug(url)
                res = match.group('res')
                if url:
                    if url.startswith('//'):
                        url = 'https:' + url
                    if res.isnumeric():
                        yield url, res
                    yield url, None
            except Exception as e:
                self.report_warning(f'Gagal extract URL: {e}')
                continue

    def _process_url(self, webpage):
        headers = {
            'User-Agent': random_user_agent(),
            'Referer': 'https://minioppai.org/',
        }
        for url, res in self._get_streampai_urls(webpage):
            self.write_debug(url)
            js_page = self._download_webpage(url, 'js obfuscated', headers=headers)
            js_decoded = decode_packed_codes(js_page)
            raw_json = self._search_regex(
                r'jwplayer\s*\([^)]+\)\s*\.setup\s*\(\s*(\{.+?\})\s*\)\s*;',
                js_decoded, 'jspw')
            if raw_json:
                clean_json = js_to_json(raw_json.replace("\\'", '"').replace('\\', ''))
                data = json.loads(clean_json)
                subtitles = self._build_subtitle(data, url)
                yield {
                    **traverse_obj(data, ('playlist', 0)),
                    'subtitles': subtitles,
                    'height': res,
                    'referer': url,
                }

    def _build_subtitle(self, _json, url):
        sub = traverse_obj(_json, ('playlist', 0, 'tracks', 0, 'file'))
        if sub:
            self.write_debug(f'subtitle: {sub}')
            subtitle = urljoin('https://streampai.my.id', quote(sub))
            self.write_debug(f'full subtitle: {subtitle}')
            return {
                'id': [
                    {
                        'url': subtitle,
                        'ext': subtitle.rsplit('.', maxsplit=1)[1],
                        'http_headers': {
                            'User-Agent': random_user_agent(),
                            'Referer': url,
                        },
                    },
                ],
            }
        return {}


class MiniOppaiPlaylistIE(MiniOppaiIE):
    IE_NAME = 'minioppai:playlist'
    _VALID_URL = r'https://minioppai\.org/anime/(?P<slug>[\w-]+)/?$'

    def _real_extract(self, url):
        slug = self._match_valid_url(url).group('slug')
        webpage = self._download_webpage(url, slug)
        entries = []
        for ep_url in re.finditer(r'data-index="\d+">\s*<a\s*href="(?P<url>[^"]+)">', webpage):
            entries.append(self.url_result(ep_url.group('url'), ie=MiniOppaiIE.ie_key()))
        return self.playlist_result(
            entries=reversed(entries), playlist_id=slug, playlist_title=self._og_search_title(webpage))


class MiniOppaiSearchIE(SearchInfoExtractor):
    IE_NAME = 'minioppai:search'
    _SEARCH_KEY = 'minioppai'

    # https://minioppai.org/?s=amai+ijiwaru
    def _search_results(self, query):
        for _i in itertools.count(0):
            webpage = self._download_webpage('https://minioppai.org/', 'home page', query={'s': query})
            url = self._html_search_regex(r'Cari\s*.+?href="(?P<url>[^"]+)"\s*itemprop', webpage, 'uerel')
            if url:
                yield self.url_result(url, ie=MiniOppaiPlaylistIE.ie_key())
