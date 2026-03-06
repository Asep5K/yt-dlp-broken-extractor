import itertools
import re

from yt_dlp.extractor.common import InfoExtractor, SearchInfoExtractor
from yt_dlp.utils import (
    ExtractorError,
    ISO639Utils,
    LazyList,
    decode_packed_codes,
    int_or_none,
    parse_duration,
)


class AnimePahePlayIE(InfoExtractor):
    IE_NAME = 'animepahe:play'
    _VALID_URL = r'https://animepahe\.si/play/[\w-]+/(?P<id>[\w-]+)$'
    # https://animepahe.si/play/e00e2abb-09cd-673b-06da-18a477686101/650a22c4bef783b2207085eb8155778c4c347ad16dd3421a4f32dde36871d6f8

    def _real_extract(self, url):
        video_id = self._match_id(url)
        episode_page = self._download_webpage(url, video_id)
        thumbnail = self._html_search_regex(r'data-src="(?P<url>[^"]+.jpg)"', episode_page, name='thumbnail', fatal=False, group='url')
        return {
            'id': video_id,
            'title': self._clean_title(episode_page),
            'formats': LazyList(self._formats(episode_page)),
            'thumbnail': thumbnail,
        }

    def _clean_title(self, episode_page):
        # <title>Shiboyugi: Playing Death Games to Put Food on the Table Ep. 9 :: animepahe</title>
        raw_title = self._html_extract_title(episode_page)
        clean = raw_title.replace(':: animepahe', '').strip()
        if ':' in clean:
            return clean.replace(':', '')
        return clean or raw_title.strip()

    def _formats(self, episode_page):
        patterns = (r'data-src="(?P<url>https://kwik\.cx[^"]+)".*?data-resolution="(?P<res>\d+)"\s*data-audio="(?P<aud>\w+)"')
        for hateemel in re.finditer(patterns, episode_page, re.S | re.I):
            url = hateemel.group('url')
            m3u8_url, video_id = self._get_m3u8_url(url)
            height = hateemel.group('res')
            formats = self._extract_m3u8_formats(m3u8_url, video_id, quality=f'{height}p', ext='mp4', headers={'referer': url}, fatal=False)
            yield from self._fix_formats(url, hateemel.group('aud'), height, formats)

    def _fix_formats(self, url, language, height, formats):
        """biar kode nya tambah baris aja sih"""
        language = ISO639Utils.long2short(language)
        height_num = int_or_none(height)
        for fmt in formats:
            fmt.update({
                'height': height_num,
                'format_id': f'{height_num}p-{language}',
                'language': language,
                'http_headers': {
                    'referer': url,
                }})
            yield fmt

    def _get_m3u8_url(self, url):
        """mencoba belajar error handling"""
        video_id = url.rsplit('/', 1)[1]
        encoded_page = self.cache.load('animepahe', video_id)
        if not encoded_page:
            encoded_page = self._download_webpage(url, video_id)
            self.cache.store('animepahe', video_id, encoded_page)
        try:
            # ('const source=\'https://vault-99.owocdn.top/stream/99/02/b17bd218d453e4f1796bdec639ced8599cee1741ef31805f86b6c07789cd24d8/uwu.m3u8\';
            decoded_page = decode_packed_codes(encoded_page)
            pattern = r'const\s*source\s*?=\\\'(?P<url>[^\\]+)\\'
            m3u8_url = self._search_regex(pattern, decoded_page, name='m3u8 url', group='url')
            if not m3u8_url:
                raise ExtractorError('Tidak menemukan m3u8 url', video_id=video_id, expected=True)
            return m3u8_url, video_id
        except Exception as e:
            raise ExtractorError(f'Gagal proses halaman: {e}', cause=e, video_id=video_id, expected=True)


class AnimePaheAnimeIE(AnimePahePlayIE):
    IE_NAME = 'animepahe:anime'
    _VALID_URL = r'https://animepahe\.si/anime/(?P<id>[\w-]+)$'
    # https://animepahe.si/anime/d908a05a-631a-9bda-9f38-0433252e6d97

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        playlist_page = self._download_webpage(url, playlist_id, headers={'referer': 'https://animepahe.si/anime'})
        return self.playlist_result(
            entries=LazyList(self._entries(url, playlist_id)),
            playlist_id=playlist_id, playlist_title=self._og_search_title(playlist_page),
            playlist_description=self._og_search_description(playlist_page))

    def _entries(self, playlist_url, playlist_id):
        base_url = playlist_url.replace('/anime/', '/play/')
        for data_json in self._dapatkan_data_json(playlist_id):
            for anime in data_json.get('data'):
                yield self.url_result(
                    url_transparent=True, url=f'{base_url}/{anime.get("session")}',
                    ie=AnimePahePlayIE.ie_key(), video_id=anime.get('id'),
                    episode_number=anime.get('episode'),
                    duration=parse_duration(anime.get('duration')),
                    thumbnail=anime.get('snapshot'),
                    language=ISO639Utils.long2short(anime.get('audio')))

    def _dapatkan_data_json(self, playlist_id):
        for page_num in itertools.count(1):
            query = {
                'm': 'release',
                'id': playlist_id,
                'sort': 'episode_asc',
                'page': page_num,
            }
            cache_file = f'{playlist_id}_{page_num}'
            json_data = self.cache.load('animepahe', cache_file)
            if not json_data:
                json_data = self._download_json('https://animepahe.si/api', video_id=playlist_id, query=query)
                self.cache.store('animepahe', cache_file, json_data)
            if json_data.get('data'):
                yield json_data
            if not json_data.get('next_page_url'):
                break


class AnimePaheSearchIE(SearchInfoExtractor):
    IE_NAME = 'animepahe:search'
    _SEARCH_KEY = 'animepahe'
    # https://animepahe.si/api?m=search&q=jujjutsu%20kaisen

    def _search_results(self, query):
        json_data = self._download_json('https://animepahe.si/api', query, query={'m': 'search', 'q': query})
        for data_json in json_data.get('data'):
            yield self.url_result(url=f'https://animepahe.si/anime/{data_json.get("session")}', ie=AnimePaheAnimeIE.ie_key(), video_id=data_json.get('id'), video_title=data_json.get('title'))
