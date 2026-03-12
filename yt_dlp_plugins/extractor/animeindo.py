import re

from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import (
    get_element_html_by_class,
    js_to_json,
    traverse_obj,
    urljoin,
)


# gak bisa bahsa enggres
class AnimeIndoIE(InfoExtractor):
    # https://anime-indo.lol/himesama-goumon-no-jikan-desu-2nd-season-episode-9/
    IE_NAME = 'animeindo'
    _VALID_URL = r'https://anime-indo\.lol/(?P<slug>[\w-]+)/?$'

    def _real_extract(self, url):
        slug = self._match_valid_url(url).group('slug')
        webpage = self._download_webpage(url, slug)
        servers = get_element_html_by_class('servers', webpage)
        url = self._html_search_regex(r'data-video="(.+xtwap[^"]+)"', servers, 'url')
        jwplayer_page = self._download_webpage(url, slug)
        json_data = self._search_json(r'"player\.setup"\(', js_to_json(jwplayer_page),
                                      'JSON data', slug, end_pattern=r'}')

        return {
            'id': slug,
            'title': self._og_search_title(webpage),
            **traverse_obj(json_data, {
                'formats': ('sources', 0, 'file',
                            {lambda p: self._extract_m3u8_formats(
                                urljoin('https://xtwap.top/', p),
                                video_id=slug)})},
                           )}


class AnimeIndoAnimeIE(AnimeIndoIE):
    # https://anime-indo.lol/anime/black-clover/
    IE_NAME = 'animeindo:anime'
    _VALID_URL = r'https://anime-indo\.lol/anime/(?P<slug>[\w-]+)/?$'

    def _real_extract(self, url):
        slug = self._match_valid_url(url).group('slug')
        webpage = self._download_webpage(url, slug)
        urls = get_element_html_by_class('ep', webpage)
        regex = r'href="[^<](?P<url>[^"]+)[^>]'
        if urls is None:
            self.raise_no_formats(f'No videos found in playlist: {url!r}', expected=True)
        entries = []
        for match in re.finditer(regex, urls):
            if not match:
                continue
            entries.append(self.url_result(url=urljoin('https://anime-indo.lol/',
                                                       match.group('url')), ie=AnimeIndoIE.ie_key()))
        return self.playlist_result(entries=entries, playlist_id=slug,
                                    playlist_title=self._og_search_title(webpage))
