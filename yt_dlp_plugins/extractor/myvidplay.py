import random
import time

from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import ExtractorError, parse_resolution, urljoin

# <iframe src="https://myvidplay.com/e/6zxkrj9xw2qk"


class MyVidPlayIE(InfoExtractor):
    # https://myvidplay.com/e/6zxkrj9xw2qk
    IE_NAME = 'myvidplay'
    _VALID_URL = r'https://myvidplay.com/e/(?P<id>\w+)'
    _EMBED_REGEX = [r'<iframe[^>]+src="(?P<url>https?://myvidplay\.com/[^"]+)"']

    def _real_extract(self, url):
        video_id = self._match_id(url)
        myvidplay_page = self._download_webpage(url, video_id)
        video_title = self._html_extract_title(myvidplay_page)
        return {
            'id': video_id,
            'title': video_title,
            'ext': 'mp4',
            'url': self._get_final_url(myvidplay_page),
            'thumbnail': self._og_search_thumbnail(myvidplay_page),
            **parse_resolution(video_title),
            'http_headers': {'referer': 'https://myvidplay.com/'},
        }

    def _get_final_url(self, webpage):
        token, md5_path = self._get_token_and_md5(webpage)
        md5_url = urljoin('https://myvidplay.com', md5_path)
        cloudatacdn_url = self._download_webpage(md5_url, 'cloudatacdn')
        if not cloudatacdn_url:
            raise ExtractorError('Tidak menemukan url dari clouddatacdn.com', expected=True)
        expiry, randomtoken = self._generate_expiry_and_random_token()
        return f'{cloudatacdn_url}{randomtoken}{token}{expiry}'

    def _get_token_and_md5(self, webpage):
        md5 = self._search_regex(r'\$\.get\(\'(/pass\w[^\']+)', webpage, 'md5', default=None)
        token = self._search_regex(r'return\sa+\s\+\s"(\?token[^"]+)', webpage, 'token', default=None)
        if token and md5:
            return token, md5
        if not token or not md5:
            raise ExtractorError('Tidak menemukan token atau md5 hash', expected=True)

    @staticmethod
    def _generate_expiry_and_random_token():
        chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
        random_token = ''.join(random.choices(chars, k=10))
        expiry = int((time.time() + 365 * 24 * 3600) * 1000)
        return expiry, random_token
