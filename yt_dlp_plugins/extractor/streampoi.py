from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import (
    ExtractorError,
    decode_packed_codes,  # kurang baca source code aku kang 😅
    urlencode_postdata,
)


class StreamPoiIE(InfoExtractor):
    IE_NAME = 'streampoi'
    # https://streampoi.com/e/bd96d4ucrfa6
    # src="https://streampoi.com/embed-r45mcvw6uysr.html"
    _VALID_URL = r'https://streampoi\.com/(?:e/)?(?P<id>[^/?#]+)$'
    _EMBED_REGEX = [r'<iframe[^>]+src="(?P<url>https?://streampoi\.com/[^"]+)"']

    def _real_extract(self, url):
        video_id = self._match_id(url)
        strampoi_page = self._get_streampoi_page(url, video_id)
        m3u8_url = self._search_regex(r'file\s*:\s*"([^"]+master\.m3u8[^"]*)"', strampoi_page, 'm3u8 URL')
        return {
            'title': video_id,
            'id': video_id,
            'formats': self._extract_m3u8_formats(m3u8_url, video_id),
        }

    def _get_streampoi_page(self, url, video_id):
        """
        Sebenernya tinggal hapus /e/ udah bisa request js page nya,
        Tapi ya biar nambah nambah baris code aja.
        """
        if '/e/' in url:
            streampoi_page = self._request_js_page(url, video_id)
        else:
            streampoi_page = self._download_webpage(url, video_id)
        return decode_packed_codes(streampoi_page)

    def _request_js_page(self, url, video_id):
        try:
            webpage = self._download_webpage(url, 'get op and auto, page')
            if webpage:
                op = self._html_search_regex(r'name="op"\s*value="([^"]+)"', webpage, name='op', fatal=False, default='embed')
                auto = self._html_search_regex(r'name="auto"\s*value="([^"])"', webpage, name='auto', fatal=False, default='1')
                post_data = {'op': op, 'auto': auto, 'file_code': video_id, 'referer': url}
                js_page = self._request_webpage('https://streampoi.com/dl', 'request js page', data=urlencode_postdata(post_data))
                return self._webpage_read_content(js_page, 'https://streampoi.com/dl', video_id='js page', encoding='utf-8')
        except Exception as e:
            raise ExtractorError(f'{e}', expected=True, cause=e)
