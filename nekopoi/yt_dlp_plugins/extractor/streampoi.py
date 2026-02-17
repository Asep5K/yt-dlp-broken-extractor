
from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import (
    decode_packed_codes,  # kurang baca source code aku kang 😅
    urlencode_postdata,
)


class StreamPoiIE(InfoExtractor):
    _VALID_URL = False

    def _extract_from_webpage(self, url: str, webpage:str) -> list:
        js = self._get_packed_js(url, webpage)
        m3u8_url = self._search_regex(r'file\s*:\s*"([^"]+master\.m3u8[^"]*)"', js, 'm3u8 URL', fatal=True, default=None)
        # thumbnail = self._search_regex(r'image:"(https:+(:?.jpg)?[^"]*)', js, 'tumbnail', fatal=False)

        return self._extract_m3u8_formats(m3u8_url, video_id='m3u8 URL', ext='mp4')


    def _get_packed_js(self, url: str, webpage: str) -> str:
        """decode js code yang di obfuscated"""
        try:
            # coba decode
            return decode_packed_codes(webpage)
        except AttributeError:
            # kalo gagal berati request dulu
            webpage = self._get_js_page(url, webpage)
            return decode_packed_codes(webpage)


    def _get_js_page(self, url: str, webpage: str) -> str | None:
        """ambil token buat request js page nya"""
        _op = self._html_search_regex(r'name="op" value="(.*?)"', webpage, name='op')
        _auto = self._html_search_regex(r'name="auto" value="(.*?)"', webpage, name='auto')
        streampoi_url = 'https://streampoi.com/dl'
        if not _op and not _auto:
            self.report_warning('gak nemu op and auto')
            return None

        data = {
            'op': _op,
            'auto': _auto,
            'file_code': url.rsplit('/', maxsplit=1)[1],
            'referer': url,
        }

        response = self._request_webpage(streampoi_url, 'request js page', data=urlencode_postdata(data))

        if response:
            return self._webpage_read_content(response, streampoi_url, video_id='js page', encoding='utf-8')

        return None
