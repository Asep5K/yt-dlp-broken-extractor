import base64
import json
import re
import urllib.parse

from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import urlencode_postdata


class OtakuDesuBase(InfoExtractor):
    """BASE OTAKUDESU EXTRACTOR"""
    _BASE_URL_RE = r'https://otakudesu\.best/%s'
    _AJAX = 'https://otakudesu.best/wp-admin/admin-ajax.php'
    _HEADERS = {
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': 'https://otakudesu.best/',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
        }

    @staticmethod
    def _get_data_encode(webpage: str) -> str | None:
        """Buat ambil semua data dict yang di encode base64"""

        pattern = r'data-content="(\w[^">]+)'
        match = re.findall(pattern, webpage, re.DOTALL)
        if match:
            return match
        return None


    @staticmethod
    def _decode_data_encode(data_encoded: str) -> dict | None:
        data_encoded = base64.b64decode(data_encoded)
        decoded_str = data_encoded.decode('utf-8')
        return json.loads(decoded_str)


    @staticmethod
    def _get_nonce(webpage: str) -> str | None:
        pattern = r'action:"([^"]+)"'
        matches = re.findall(pattern, webpage)
        if len(matches) >= 2:
            return matches[0], matches[1] # nonce_action, video_action
        return None, None


    def _get_nonce_token(self, action):
        data = {
            'action': action,
        }
        
        response = self._request_webpage(self._AJAX, None, data=urlencode_postdata(data), headers=self._HEADERS)
        response_json = json.loads(self._webpage_read_content((response), self._AJAX, None))

        return response_json.get('data')


    def _get_iframe_html(self, data:dict, action:str, nonce:str) -> str | None:
        data_video ={
            'action': action,
            'nonce': nonce,
            **data,
        }
        response = self._request_webpage(self._AJAX, video_id=str(data['id']),
                    data=urlencode_postdata(data_video), headers=self._HEADERS)

        if response:
            response_text = self._webpage_read_content(response, self._AJAX, None)
            response_json = json.loads(response_text)

            if 'data' in response_json:
                return base64.b64decode(response_json['data']).decode('utf-8')

        return None

    @staticmethod
    def _get_direct_link(iframe):
        pattern = r'src="(https://pixeldrain\.com[^"]+)'
        matches = re.search(pattern, iframe)
        if matches:
            return matches.group(1)
        return None


class OtakuDesuIE(OtakuDesuBase):
    IE_NAME = 'otakudesu'
    _VALID_URL = OtakuDesuBase._BASE_URL_RE % r'episode/(?P<slug>[^/]+?)(?:/|$)'
    # 'https://otakudesu.best/episode/cskc-episode-1-sub-indo/'

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        soup = mobj.group('slug')
        webpage = self._download_webpage(url, soup)
        data_encoded = self._get_data_encode(webpage)

        if not data_encoded:
            self.report_warning('Ga nemu data-content!')
            return {}

        action_video, nonce = self._get_nonce(webpage)
        if action_video and nonce:
            nonce_token = self._get_nonce_token(nonce)

        formats = []
        for data in data_encoded:
            data_dict = self._decode_data_encode(data)
            iframe_link = self._get_iframe_html(data_dict, action_video, nonce_token)
            url = self._get_direct_link(iframe_link)
            if url:
                formats.append(
                    {
                        'url': url,
                        'ext': 'mp4',
                        'resolution': data_dict['q'],
                        'format_id': str(data_dict['i']),
                        'quality': int(data_dict['q'].replace('p', '')) if data_dict['q'] else None,
                    },
                )

        return {
            'id': str(data_dict['id']),
            'title': self._og_search_title(webpage),
            'formats': formats,
        }


class OtakuDesuPlaylistIE(OtakuDesuBase):
    IE_NAME = 'otakudesu playlist'
    _VALID_URL = OtakuDesuBase._BASE_URL_RE % r'anime/(?P<slug>[^/]+)'
    # https://otakudesu.best/anime/chanto-suenai-kyuuketsuki-sub-indo/


    @staticmethod
    def _get_valid_link(webpage):
        pattern = r'href="(https://otakudesu\.best/episode/[^/?]+)'
        matches = re.findall(pattern, webpage, re.DOTALL)
        if isinstance(matches, list):
            return reversed(matches)
        return None


    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        soup = mobj.group('slug')
        webpage = self._download_webpage(url, soup)
        links = self._get_valid_link(webpage)
        entries = []
        for link in links:
            entries.append(self.url_result(
                    link,
                    ie=OtakuDesuIE,
                    video_id=soup,
                ))
        return self.playlist_result(
            entries,
            playlist_id=soup,
            playlist_title=self._og_search_title(webpage, default=soup),
        )
