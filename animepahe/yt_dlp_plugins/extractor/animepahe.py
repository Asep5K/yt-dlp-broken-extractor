import itertools
import re

from yt_dlp.extractor.common import InfoExtractor, SearchInfoExtractor
from yt_dlp.utils import (
    ISO639Utils,
    decode_packed_codes,
    int_or_none,
    random_user_agent,
)


class AnimePaheIE(InfoExtractor, ISO639Utils):
    IE_NAME = 'animepahe'
    _VALID_URL = r'https://animepahe\.si/play/.*/(?P<id>.*)'

    def _real_extract(self, url):
        webpage = self._download_webpage(url, 'web', headers={'user-agent': random_user_agent()})
        video_id = self._html_search_regex(
            r'<meta\s*name="id"\s*content="(\d+)">',
            webpage, name='video id', fatal=False,
            default=self._match_id(url))
        video_title = self._html_extract_title(webpage)
        thumbnail = self._html_search_regex(r'data-src="(.*?[(?:.jpg")?])"', webpage, name='thumbnail', fatal=False)
        return {
            'id': video_id,
            'title': video_title,
            'thumbnail': thumbnail,
            'formats': self._build_formats(webpage),

        }

    def _get_m3u8_url(self, url):
        webpage = self._download_webpage(url, url.rsplit('/', maxsplit=1)[1])
        js_decoded = decode_packed_codes(webpage)
        if js_decoded:
            # 'const source =\'https://vault-99.owocdn.top/stream/99/01/6dfb35bed1df8646977c5a610768b2c75ac5a0d27a9f1aaeaf0f7e47654dcd3a/uwu.m3u8\'
            regexxnx = r'const\s*source\s*=\\\'(.*?)\\'  # regex pepek
            url = self._search_regex(regexxnx, js_decoded, name='m3u8 url')
            if url:
                return url
        return False

    def _build_formats(self, webpage):
        paterns = r'data-src="(?P<url>https://kwik\.cx[^"]+)".*?data-resolution="(?P<res>\d+)"\s*data-audio="(?P<aud>\w+)"'
        formats = []
        for u in re.finditer(paterns, webpage, re.DOTALL | re.IGNORECASE):
            url = u.group('url')
            height = int_or_none(u.group('res'))
            lang = u.group('aud')
            m3u8_url = self._get_m3u8_url(url)
            formats.append({
                'url': m3u8_url,
                'manifest_url': url,
                'language': self.long2short(lang),
                'quality': f'{height}p',
                'ext': 'mp4',
                'height': height,
                'http_headers': {
                    'Referer': url,
                    'User-Agent': random_user_agent(),
                },
            })
        return formats


#  TODO: ?
class AnimePahePlaylistIE(AnimePaheIE):
    IE_NAME = 'animepahe playlist'
    # https://animepahe.si/anime/d908a05a-631a-9bda-9f38-0433252e6d97
    _VALID_URL = r'https://animepahe\.si/anime/(?P<id>.*)'

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        webpage = self._download_webpage(url, playlist_id)
        base_url = url.replace('/anime/', '/play/')
        entries = []
        for page_num in itertools.count(1):
            query = {
                'm': 'release',
                'id': playlist_id,
                'sort': 'episode_asc',
                'page': page_num,
            }
            data_json = self._download_json('https://animepahe.si/api', video_id=playlist_id, query=query)

            for f in data_json['data']:
                entries.append(self.url_result(url=f'{base_url}/{f["session"]}',
                                               ie=AnimePaheIE.ie_key(), video_id=f['session'],
                                               episode_number=f['episode']))
            if not data_json['next_page_url']:
                break

        return self.playlist_result(
            entries=entries,
            playlist_id=playlist_id,
            playlist_title=self._og_search_title(webpage),
            playlist_description=self._og_search_description(webpage),
        )


class AnimePaheSearchIE(SearchInfoExtractor):
    IE_NAME = 'animepahe:search'
    _SEARCH_KEY = 'animepahe'
    # https://animepahe.si/api?m=search&q=jujjutsu%20kaisen

    def _search_results(self, query):
        results = self._download_json('https://animepahe.si/api',
                                      query, query={'m': 'search', 'q': query})
        for f in results['data']:
            yield self.url_result(url=f'https://animepahe.si/anime/{f["session"]}',
                                  ie=AnimePahePlaylistIE.ie_key(), video_id=f['id'],
                                  video_title=f['title'])
