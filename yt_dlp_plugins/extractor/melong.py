import base64
import re

from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import (
    get_element_html_by_class,
)


class MelongIE(InfoExtractor):
    # https://tv12.melongmovies.com/the-race-curva/
    IE_NAME = 'melongmovies'
    _VALID_URL = r'https://tv12\.melongmovies\.com/(?P<slug>[\w-]+)/?$'
    _WORKING = False

    def _real_extract(self, url):
        self._url = url
        slug = self._match_valid_url(url).group('slug')
        webpage = self._download_webpage(url, slug)
        return {
            'id': slug,
            'title': self._html_extract_title(webpage) or slug,
            'formats': self._extract(webpage),
        }

    def _extract(self, webpage):
        formats = []
        skip_url = ['melongfilm', 'youtube', 'hglink.to']
        for url in self._get_url(webpage):
            if url is None:
                break
            if any(domain in url for domain in skip_url):
                continue
            info = self._downloader.extract_info(url, download=False, process=False)
            if info.get('formats'):
                formats.extend(info['formats'])
            elif info.get('url'):
                formats.append(info)
            else:
                continue
        return formats

    def _get_url(self, webpage):
        server = get_element_html_by_class('mirror', webpage)
        if server is None:
            info = self._downloader.extract_info(self._url, download=False, force_generic_extractor=True)
            return info
        """
        <ul class="mirror">
                <li>
            <a href="#/" data-em="PGlmcmFtZSBzcmM9Imh0dHBzOi8vbWVsb25nZmlsbS40bWVwbGF5ZXIuY29tLyNoNmpnbiIgd2lkdGg9IjEwMCUiIGhlaWdodD0iMTAwJSIgZnJhbWVib3JkZXI9IjAiIGFsbG93ZnVsbHNjcmVlbj48L2lmcmFtZT4=" data-index="1" data-href="https://tv12.melongmovies.com/the-race-curva/" class="active">
            PLAYER4            </a>
            </li>
                    <li>
            <a href="#/" data-em="PElGUkFNRSBTUkM9Imh0dHBzOi8vbWlub2NoaW5vcy5jb20vZW1iZWQvMWwxMWZoaXhwMWR6IiBGUkFNRUJPUkRFUj0wIE1BUkdJTldJRFRIPTAgTUFSR0lOSEVJR0hUPTAgU0NST0xMSU5HPU5PIFdJRFRIPTY0MCBIRUlHSFQ9MzYwIGFsbG93ZnVsbHNjcmVlbj48L0lGUkFNRT4=" data-index="2" data-href="https://tv12.melongmovies.com/the-race-curva/mirror/2">
            EARNVIDS            </a>
            </li>
                    <li>
            <a href="#/" data-em="PGlmcmFtZSBzcmM9Imh0dHBzOi8vc3RyZWFtdGFwZS5jb20vZS92TExhYmtRd3B6c3c5ai8iIHdpZHRoPSI4MDAiIGhlaWdodD0iNjAwIiBhbGxvd2Z1bGxzY3JlZW4gYWxsb3d0cmFuc3BhcmVuY3kgYWxsb3c9ImF1dG9wbGF5IiBzY3JvbGxpbmc9Im5vIiBmcmFtZWJvcmRlcj0iMCI+PC9pZnJhbWU+" data-index="3" data-href="https://tv12.melongmovies.com/the-race-curva/mirror/3">
            STREAMTAPE            </a>
            </li>
                </ul>
        """
        # href="#/" data-em="PGlmcmFtZSBzcmM9Imh0dHBzOi8vbWVsb25nZmlsbS40bWVwbGF5ZXIuY29tLyNoNmpnbiIgd2lkdGg9IjEwMCUiIGhlaWdodD0iMTAwJSIgZnJhbWVib3JkZXI9IjAiIGFsbG93ZnVsbHNjcmVlbj48L2lmcmFtZT4=" data-index="1" data-href="https://tv12.melongmovies.com/the-race-curva/" class="active">
        for b64_iframe in re.finditer(r'data-em="(?P<b64>[^"]+)"\s*data-index="\d+"', server, re.I):
            if not b64_iframe:
                break
            try:
                iframe_src = base64.b64decode(b64_iframe.group('b64')).decode()
                __url__ = self._html_search_regex(r'src="(?P<url>[^"]+)"', iframe_src, 'url', group='url', flags=re.I)
                yield __url__
            except base64.binascii.Error:
                continue
