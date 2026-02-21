import re

from yt_dlp.extractor.common import InfoExtractor, SearchInfoExtractor
from yt_dlp.utils import (
    int_or_none,
    parse_resolution,
    random_user_agent,
    str_or_none,
    traverse_obj,
    try_call,
    urlencode_postdata,
)


class SameHadaKuIE(InfoExtractor):
    """situs kok banyak iklan nya  kocak"""
    IE_NAME = 'samehadaku'
    _VALID_URL = r'https://v1\.samehadaku\.how/(?P<slug>[^/?]+)(?:-episode-\d+/)'
    _HEADERS = {
        'User-Agent': random_user_agent(),
        'X-Requested-With': 'XMLHttpRequest',
        'Origin': 'https://v1.samehadaku.how',
        'Referer': 'https://v1.samehadaku.how/',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'iframe',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'cross-site',
    }

    def _clean_title(self, title):
        return self._search_regex(
            r'(.*?)\s*(?:Sub\s*Indo|subtitle\s*indonesia)?\s*-?\s*Samehadaku',
            title, name='title cleaner', fatal=False,
            default=title, flags=(re.IGNORECASE | re.DOTALL))

    def _get_page_url(self, nume, video_id):
        ajax_url = 'https://v1.samehadaku.how/wp-admin/admin-ajax.php'
        data_post = {
            'action': 'player_ajax',
            'post': video_id,
            'nume': nume,
            'type': 'schtml',
        }
        response = self._request_webpage(ajax_url, 'URLs page',
                                         headers=self._HEADERS,
                                         data=urlencode_postdata(data_post))
        if response:
            return self._webpage_read_content(response, ajax_url, data_post, note='read ajax page')
        return None

    @staticmethod
    def _parse_resolution(url):
        if not url:
            return None
        resolution = parse_resolution(url)
        if resolution and isinstance(resolution, dict):
            return resolution.get('height')
        res_map = {'FULLHD': 1080, 'SD': 480, 'HD': 720}
        for f, r in res_map.items():
            if f in url:
                return r
        return None

    def _parse_wibufile(self, url):
        if not url.endswith('.mp4'):
            wibufile_page = self._download_webpage(url, 'wibufile api',
                                                   fatal=False, tries=10, headers=self._HEADERS, timeout=5)
            pattern = r'\$\.ajax\(\{\s*url:\s*"(.*?)",'
            ajax_url = self._search_regex(pattern, wibufile_page, 'ajax request')
            data_str = self._download_webpage(ajax_url, 'ajax sendiri')
            data_dict = self._parse_json(data_str, 'wibufile url')
            if data_dict:
                url = traverse_obj(data_dict, ('sources', ..., 'file'))[0]
        if url:
            return self._build_format(url)
        return None

    def _parse_filedon(self, url):
        webpage = self._download_webpage(url, 'fildeon webpage')
        jeson_str = self._html_search_regex(r'data-page\s*=\s*"([^"]+)"',
                                            webpage, 'json str', flags=re.DOTALL)
        jeson_dict = self._parse_json(jeson_str, 'filedon json')
        if jeson_dict:
            url = traverse_obj(jeson_dict, ('props', 'url'))
            return self._build_format(url)
        return None

    def _build_format(self, url):
        fmt_map = {360: '18', 480: '35', 720: '22', 1080: '37'}
        res = try_call(lambda: self._parse_resolution(url))
        return {
            'url': url,
            'quality': str_or_none(f'{res}p'),
            'format_id': fmt_map[res],
            'resolution': int_or_none(res),
            'height': res,
            'width': int_or_none((res * 16) / 9),
        }

    def _get_urls(self, webpage):
        patterns = r'data-post="(?P<id>\d+)"\s*data-nume="(?P<nume>\d+)"'
        url_pattern = r'<iframe\s*src="(.*?[^"]+)'
        urls = []
        for data in re.finditer(patterns, webpage, re.DOTALL):
            iframe_page = self._get_page_url(nume=data.group('nume'), video_id=data.group('id'))
            url = self._html_search_regex(url_pattern, iframe_page, 'grep url', flags=(re.DOTALL | re.IGNORECASE))
            if url:
                urls.append(url)
        return urls, data.group('id')

    def _extract_url(self, url):
        parser_map = {
            'wibufile': self._parse_wibufile,
            'filedon': self._parse_filedon,
            # 'blogger': lambda u: self.url_result
        }
        for site_name, parser in parser_map.items():
            if site_name in url:
                result = parser(url)
                if result:
                    return result

    def _real_extract(self, url):
        slug = self._match_valid_url(url).group('slug')
        webpage = self._download_webpage(url, slug)
        urls, video_id = self._get_urls(webpage)
        video_title = try_call(lambda: self._html_extract_title(webpage),
                               self._og_search_title(webpage))
        formats = []
        for url in urls:
            data_dict = self._extract_url(url)
            if data_dict and isinstance(data_dict, dict):
                formats.append(data_dict)
        return {
            'id': video_id,
            'title': self._clean_title(video_title),
            'formats': formats,
        }


class SameHadaKuPlaylistIE(SameHadaKuIE):
    IE_NAME = 'samehadaku playlist'
    _VALID_URL = r'https://v1\.samehadaku\.how/anime/(?P<slug>[^/?]+)'

    @staticmethod
    def _get_valid_urls(webpage, pattern=r'href="(https://v1\.samehadaku\.how/[^"]+-episode-\d+/?)"'):
        matches = re.findall(pattern, webpage)
        if matches:
            return matches
        return None

    def _real_extract(self, url):
        slug = self._match_valid_url(url).group('slug')
        webpage = self._download_webpage(url, slug)
        playlist_id = self._html_search_regex(r'id="post-(\d+)"', webpage, 'playlist id', default=slug)
        urls = self._get_valid_urls(webpage)
        dups = set()
        entries = []
        for url in urls:
            if url and url not in dups:
                dups.add(url)
                entries.append(self.url_result(url, ie=SameHadaKuIE, video_id=slug))
        return self.playlist_result(
            reversed(entries),
            playlist_id=playlist_id,
            playlist_title=self._clean_title(self._og_search_title(webpage)),
        )


class SameHadaKuSearchIE(SearchInfoExtractor, SameHadaKuPlaylistIE):
    IE_NAME = 'samehadaku:search'
    _SEARCH_KEY = 'samehadaku'

    # https://v1.samehadaku.how/?s=oshi+no+ko
    def _search_results(self, query):
        data = urlencode_postdata({'s': query})
        webpage = self._download_webpage(
            'https://v1.samehadaku.how',
            video_id='search page', data=data,
            headers=self._HEADERS)
        query = query.replace(' ', '-')
        valid_url = self._get_valid_urls(webpage,
                                         rf'href="(https://v1\.samehadaku\.how/anime/{query}(?:-season-\d)?[^"?]+)')
        for url in valid_url:
            yield self.url_result(url, ie=SameHadaKuPlaylistIE, video_id=query)
