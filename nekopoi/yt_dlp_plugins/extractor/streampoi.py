
from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import (
    decode_packed_codes,  # kurang baca source code aku kang 😅
    urlencode_postdata,
)


# jangan protes kalo kualitas kode nya jelek
# gw bukan programmer / yang ngerti banget python
# gw cuma iseng belajar aja
class StreamPoiIE(InfoExtractor):
    _VALID_URL = False
    _EMBED_REGEX = [
        r'<iframe\s*src=(https://streampoi\.com/.*?)',
    ]

    def _extract_from_webpage(self, url: str, webpage: str) -> list:
        if 'streampoi' not in url:
            raise self.StopExtraction
        if not webpage:
            return []
        js = self._get_packed_js(url, webpage)
        m3u8_url = self._search_regex(r'file\s*:\s*"([^"]+master\.m3u8[^"]*)"', js, 'm3u8 URL', fatal=False, default=None)
        try:
            return self._extract_m3u8_formats(
                m3u8_url, video_id='streampoi', ext='mp4',
            )
        except Exception as e:
            self.report_warning(f'StreamPoi: gagal extract formats: {e}')
            return []

    def _get_packed_js(self, url: str, webpage: str) -> str:
        """decode js code yang di obfuscated"""
        try:
            # coba decode
            return decode_packed_codes(webpage)
        except AttributeError:
            # kalo gagal berati request dulu
            webpage = self._get_js_page(url, webpage)
            return decode_packed_codes(webpage)
        except Exception:
            return

    def _get_js_page(self, url: str, webpage: str) -> str | None:
        """ambil token buat request js page nya"""
        _op = self._html_search_regex(r'name="op" value="(.*?)"', webpage, name='op', fatal=False, default=None)
        _auto = self._html_search_regex(r'name="auto" value="(.*?)"', webpage, name='auto', fatal=False, default=None)
        streampoi_url = 'https://streampoi.com/dl'
        if not _op or not _auto:
            self.report_warning('gak nemu op and auto')
            return
        data = {
            'op': _op,
            'auto': _auto,
            'file_code': url.rsplit('/', maxsplit=1)[1],
            'referer': url,
        }
        response = self._request_webpage(streampoi_url, 'request js page', data=urlencode_postdata(data))
        if response:
            return self._webpage_read_content(response, streampoi_url, video_id='js page', encoding='utf-8')
        return
