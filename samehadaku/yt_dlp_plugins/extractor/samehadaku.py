import re

from yt_dlp.extractor.common import InfoExtractor, SearchInfoExtractor
from yt_dlp.utils import urlencode_postdata


class SameHadaKuIE(InfoExtractor):
    IE_NAME = 'samehadaku'
    _VALID_URL = r'https://v1\.samehadaku\.how/(?P<slug>[^/?]+)(?:-episode-\d+/)'
    _HEADERS = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
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


    @staticmethod
    def _parse_link(webpage):
        # pattern = r'data-post="(?P<id>\d+)"\sdata-nume="(?P<number>\d+)"\sdata-type="(?P<type>[A-Za-z]+)"><span>(.+[^<])\s(?P<res>\d+p)[</]'
        pattern = (
                r'data-post="(?P<id>\d+)"\s' #id?
                r'data-nume="(?P<number>\d+)"\s' # number?
                r'data-type="(?P<type>[A-Za-z]+)"><span>(.+[^<])\s' #type nya apa?
                r'(?P<res>\d+p)[</]' # reolusi nya berapa?
        )
        return [m.groupdict() for m in re.finditer(pattern, webpage)]


    def _get_direct_link(self, data_post, nume, data_type):
        url = 'https://v1.samehadaku.how/wp-admin/admin-ajax.php'
        post_data = {
            'action': 'player_ajax',
            'post': data_post,
            'nume': nume,
            'type': data_type,
        }

        response = self._request_webpage(url, data_post,
                    data=urlencode_postdata(post_data), headers=self._HEADERS)

        return self._webpage_read_content(response, url, data_post, note='frfrfrrf')


    @staticmethod
    def _parse_direct_link(html):
        pattern = r'<iframe\ssrc="(https://(?:s0|www)\.(?:wibufile|blogger)\.com[^"]+)(?:\.mp4)?'
        match = re.search(pattern, html)
        if match:
            return match.group(1)
        return None


    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        soup = mobj.group('slug')
        webpage = self._download_webpage(url, soup)
        players = self._parse_link(webpage)

        formats = []
        video_id = 'null'

        for player in players:
            data_post = player.get('id')
            nume = player.get('number')
            data_type = player.get('type')
            resol = player.get('res')
            video_id = data_post

            ajax_html = self._get_direct_link(data_post, nume, data_type)
            video_url = self._parse_direct_link(ajax_html)

            # Blogger fallback
            if video_url and 'blogger.com' in video_url:
                try:
                    blogger_page = self._download_webpage(video_url, nume)
                    pat = r'"play_url":"(https://[^",]+)'
                    match = re.search(pat, blogger_page)
                    if match:
                        video_url = match.group(1)
                except Exception as e:
                    self.report_warning(f"Error {e}")

            if video_url:
                formats.append({
                    'url': video_url,
                    'resolution': resol,
                    'format_id': resol,
                })

        return {
            'title': self._og_search_title(webpage),
            'id': video_id,
            'formats': formats,
        }


class SameHadaKuPlaylistIE(SameHadaKuIE):
    IE_NAME = 'samehadaku playlist'
    _VALID_URL = r'https://v1\.samehadaku\.how/anime/(?P<slug>[^/?]+)'

    @staticmethod
    def _get_valid_link(webpage):
        pattern = r'href="(https://v1\.samehadaku\.how/[^"]+-episode-\d+/?)"'
        matches = re.findall(pattern, webpage)

        if matches:
            return matches

        return None


    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        soup = mobj.group('slug')
        webpage = self._download_webpage(url, soup)

        links = self._get_valid_link(webpage)
        dups = set()

        entries = []
        for link in links:
            if link and link not in dups:
                dups.add(link)
                entries.append(self.url_result(
                        link,
                        ie=SameHadaKuIE,
                        video_id=soup,
                    ),
                )

        return self.playlist_result(
            reversed(entries),
            playlist_id=soup,
            playlist_title=self._og_search_title(webpage),
        )

class SameHadaKuSearchIE(SearchInfoExtractor, SameHadaKuIE):
    IE_NAME = 'samehadaku:search'
    _SEARCH_KEY = 'samehadaku'
    _BASE_URL = 'https://v1.samehadaku.how'
    # https://v1.samehadaku.how/?s=oshi+no+ko

    def _get_html_page(self, query: str) -> str:
        return self._download_webpage(self._BASE_URL, video_id=query,
                    data=urlencode_postdata({ 's': query }), headers=self._HEADERS,
                    )

    def _get_valid_url(self, query: str) -> list:
        webpage = self._get_html_page(query)

        query = query.replace(' ', '-')

        pattern = fr'href="(https://v1\.samehadaku\.how/anime/{query}(?:-season-\d)?[^"?]+)'

        match = re.findall(pattern, webpage, re.IGNORECASE)

        if isinstance(match, list):
            return match

        return None


    def _search_results(self, query):
        valid_url = self._get_valid_url(query)
        for url in valid_url:
            yield self.url_result(url, ie=SameHadaKuPlaylistIE, video_id=query)

