import re
import secrets
import string
import time

from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import urljoin


class MyVidPlayIE(InfoExtractor):
    _VALID_URL = False

    def _extract_from_webpage(self, url, webpage):

        video_title = self._html_extract_title(webpage)

        md5 = self._search_regex(r'\$\.get\(\'(/pass\w[^\']+)', webpage, 'md5')
        token = self._search_regex(r'return\sa+\s\+\s"(\?token[^"]+)', webpage, 'token')

        if not md5 or not token:
            self.report_warning(f'Failed to extract MyVidPlay data from {url}')
            return {}

        valid_url = self._get_valid_url(md5, token)
        format_id, height , width = self._parse_height_from_title(video_title)
        return {
            'url': valid_url,
            'format_id': format_id,
            'height': height,
            'width': width,
            'thumbnail': self._og_search_thumbnail(webpage),
        }


    @staticmethod
    def _generate_random_token():
        """Generate random token and expiry for MyVidPlay"""
        rand = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))
        expiry = int((time.time() + 3600) * 1000)  # 1 hour from now
        return rand, expiry


    def _get_valid_url(self, md5, token):
        random, expiry = self._generate_random_token()
        md5_url = urljoin('https://myvidplay.com', md5)
        base_url = self._download_webpage(md5_url, 'base URL',
                                            tries=10, timeout=30,
                                            errnote='Failed to download MyVidPlay page')

        if not base_url:
            self.report_warning('gak nemu base url nya njir')

        return f'{base_url}{random}{token}{expiry}'

    def _parse_height_from_title(self, title):
        height = self._search_regex(r'\[?(\d+p)\]?', title,
                'parse height', flags=re.IGNORECASE,
                default=0, fatal=False)
        if height:
            format_id = height.lower()
            height = int(format_id.replace('p','')) if 'p' in format_id else format_id
            width = ( height * 16 ) / 9
            return format_id, height, width
        return None, None, None
