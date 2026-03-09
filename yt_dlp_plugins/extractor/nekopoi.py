import re
from itertools import count

from yt_dlp.extractor.common import (
    InfoExtractor,
    SearchInfoExtractor,
)
from yt_dlp.networking.exceptions import HTTPError
from yt_dlp.utils import (
    ExtractorError,
    get_element_html_by_class,
    get_element_html_by_id,
)


class NekoPoiIE(InfoExtractor):
    IE_NAME = 'nekopoi'
    _VALID_URL = r'https://nekopoi\.care/(?P<slug>[\w-]+)/?$'
    _EMBED_REGEX = [r'class="latestnow"><a\s*[^>]href="(?P<url>[^"]+)[^>]',
                    r'href="(?P<url>[^"]+)"[^>]\s*class="nk-episode-card"']
    # https://nekopoi.care/honey-blonde-2-episode-2-subtitle-indonesia/

    def _real_extract(self, url):
        slug = self._match_valid_url(url).group('slug')
        nekopoi_page = self._download_webpage(url, slug)
        return {
            'id': slug,
            'title': self._og_search_title(nekopoi_page) or self._html_extract_title(nekopoi_page),
            'description': self._og_search_description(nekopoi_page),
            **self._get_formats_and_thumbnails(nekopoi_page),
        }

    def _get_formats_and_thumbnails(self, webpage):
        formats = []
        thumbnails = []
        for url in self._get_url(webpage):
            _formats = self._extract_embed_url(url)
            if _formats and _formats.get('url'):
                formats.append(_formats)
            if _formats and _formats.get('formats'):
                formats.extend(_formats['formats'])
            if _formats and _formats.get('thumbnail'):
                thumbnails.append({'url': _formats['thumbnail']})
        return {'formats': formats, 'thumbnails': thumbnails}

    def _extract_embed_url(self, url):
        try:
            if 'vidnest' in url:
                webpage = self._download_webpage(url, 'vidnest page')
                return self._extract_jwplayer_data(webpage, 'jwplayer', require_title=False)
            return self._downloader.extract_info(url, download=False, process=False)
        except Exception as e:
            self.report_warning(f'Unexpected error: {e}')
            return {}

    def _get_url(self, webpage):
        for i in count(1):
            iframe_src = get_element_html_by_id(f'nk-stream-{i}', webpage)
            if not iframe_src:
                break
            embed_url = self._html_search_regex(r'iframe\s*[^>]src="([^"]+)"', iframe_src, 'embed url')
            if embed_url:
                yield embed_url

    def _download_webpage(self, *args, **kwargs):
        try:
            return super()._download_webpage(*args, **kwargs)
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError):
                self.report_warning('Nekopoi pake SafeLine WAF, butuh cookies fresh dari browser')
                status = getattr(e.cause, 'status', None)
                if status == 468:
                    raise ExtractorError('Coba refresh page nekopoi', expected=True)
            raise


class NekopoiHentaiIE(NekoPoiIE):
    # https://nekopoi.care/hentai/oneshota-the-animation/
    _VALID_URL = r'https://nekopoi\.care/hentai/(?P<slug>[\w-]+)/?$'
    IE_NAME = 'nekopoi:hentai'

    def _real_extract(self, url):
        slug = self._match_valid_url(url).group('slug')
        webpage = self._download_webpage(url, slug)
        content = get_element_html_by_class('nk-episode-grid', webpage)
        entries = []
        for nekopoi_url in re.finditer(r'href="(?P<url>[^"]+)"[^>]', content):
            if nekopoi_url:
                entries.append(self.url_result(url=nekopoi_url.group('url'), ie=NekoPoiIE.ie_key()))
        return self.playlist_result(entries=entries, playlist_id=slug,
                                    playlist_title=self._og_search_title(webpage) or slug,
                                    playlistT_description=self._og_search_description(webpage))


class NeekopoiSearchIE(SearchInfoExtractor, NekoPoiIE):
    IE_NAME = 'nekopoi:search'
    _SEARCH_KEY = 'nekopoi'

    def _search_results(self, query):
        base_url = f'https://nekopoi.care/search/{query}'
        for i in range(3):
            search_url = f'{base_url}/page/{i}'
            webpage = self._download_webpage(search_url, query, note=f'Downloading page {i}')
            content = get_element_html_by_class('nk-search-results', webpage)
            for nekopoi_url in re.finditer(r'href="(?P<url>[^"]+)"[^>]', content):
                if nekopoi_url:
                    yield self.url_result(url=nekopoi_url.group('url'), ie=NekoPoiIE.ie_key())
