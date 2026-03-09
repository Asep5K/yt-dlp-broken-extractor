from itertools import count

from yt_dlp.extractor.common import InfoExtractor, SearchInfoExtractor
from yt_dlp.utils import (
    filter_dict,
    get_elements_by_class,
    parse_resolution,
    urlencode_postdata,
)


class SameHadaKuIE(InfoExtractor):
    IE_NAME = 'samehadaku'
    # https://v2.samehadaku.how/mato-seihei-no-slave-season-2-episode-1
    # https://v2.samehadaku.how/mato-seihei-no-slave-season-2-episode-2-uc/
    _VALID_URL = r'https://v2\.samehadaku\.how/(?P<slug>[\w-]+)/?$'

    def _real_extract(self, url):
        slug = self._match_valid_url(url).group('slug')
        webpage = self._download_webpage(url, slug)
        video_id = self._html_search_regex(r'data-post="(?P<id>[^"]+)"[^>]', webpage, 'video id', group='id')
        return filter_dict({
            'id': video_id,
            'title': self._og_search_title(webpage) or self._html_extract_title(webpage),
            'formats': self._build_format(video_id, slug),
        })

    @staticmethod
    def _parse_resolution(q):
        if not q:
            return None
        resolution = parse_resolution(q)
        if resolution and isinstance(resolution, dict):
            return resolution.get('height')
        res_map = {'FULLHD': 1080, 'SD': 480, 'HD': 720}
        for f, r in res_map.items():
            if f in q:
                return r
        return None

    def _build_format(self, video_id, slug):
        formats = []
        blocked_url = ['mega.nz', 'blogger']
        for url in self._get_url_from_iframe(video_id):
            if not url or any(domain in url for domain in blocked_url):
                continue
            try:
                info = self._downloader.extract_info(url, download=False, process=False)
                quality = self._parse_resolution(info.get('title', 'id')) or 'unknown'
                if info.get('url'):
                    formats.append({**info, 'height': quality, 'quality': quality, 'resolution': f'{quality}'})
                elif info.get('formats'):
                    for fmt in info['formats']:
                        fmt.update({'height': quality, 'quality': quality, 'resolution': f'{quality}'})
                        formats.append(fmt)
            except Exception as e:
                self.report_warning(e)
                continue
        return formats

    def _get_url_from_iframe(self, video_id):
        ajax_url = 'https://v2.samehadaku.how/wp-admin/admin-ajax.php'
        for i in count(1):
            data_post = {'action': 'player_ajax', 'post': video_id, 'nume': i, 'type': 'schtml'}
            iframe_src = self._download_webpage(ajax_url, 'iframe', data=urlencode_postdata(data_post))
            self.write_debug(iframe_src)
            if 'vidlion' in iframe_src:
                continue
            if not iframe_src:
                break
            __url__ = self._html_search_regex(r'src="([^"]+)"[^>]', iframe_src, 'url from iframe')
            if __url__:
                self.write_debug(f'Url: {__url__}')
                yield __url__


class SameHadaKuAnimeIE(InfoExtractor):
    # https://v2.samehadaku.how/anime/mato-seihei-no-slave-season-2/
    IE_NAME = 'samehadaku:anime'
    _VALID_URL = r'https://v2\.samehadaku\.how/anime/(?P<slug>[\w-]+)/?$'

    def _real_extract(self, url):
        slug = self._match_valid_url(url).group('slug')
        html = self._download_webpage(url, slug)
        entries = []
        for content in reversed(get_elements_by_class('eps', html)):
            url = self._html_search_regex(r'href="(?P<url>[^"]+)"', content, 'url', group='url')
            entries.append(self.url_result(url=url, ie=SameHadaKuIE.ie_key()))
        return self.playlist_result(playlist_id=slug, playlist_title=self._og_search_title(html) or self._html_extract_title(html), entries=entries)


class SameHadaKuSearchIE(SearchInfoExtractor):
    IE_NAME = 'samehadaku:search'
    _SEARCH_KEY = 'samehadaku'

    def _search_results(self, query):
        webpage = self._download_webpage('https://v2.samehadaku.how', video_id='search page', data=urlencode_postdata({'s': query}))
        for list_url in get_elements_by_class('animposx', webpage):
            url = self._html_search_regex(r'href="(?P<url>[^"]+)"', list_url, 'url', group='url')
            yield self.url_result(url=url, ie=SameHadaKuAnimeIE.ie_key())
