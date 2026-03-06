import base64
import json
import re
from typing import Any

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
    def _extract_data_contents(webpage: str) -> list[str]:
        """Extract all base64-encoded data from webpage."""
        pattern = r'data-content="(\w[^">]+)'
        matches = re.findall(pattern, webpage, re.DOTALL)
        return matches if matches else []

    @staticmethod
    def _decode_data(data_encoded: str) -> dict[str, Any] | None:
        """Decode base64-encoded data string to dict."""
        try:
            decoded_bytes = base64.b64decode(data_encoded)
            decoded_str = decoded_bytes.decode('utf-8')
            return json.loads(decoded_str)
        except (base64.binascii.Error, json.JSONDecodeError, UnicodeDecodeError):
            return None

    @staticmethod
    def _extract_nonce_data(webpage: str) -> tuple[str | None, str | None]:
        """Extract action and nonce from webpage.

        Returns:
            Tuple of (action, nonce)
        """
        pattern = r'action:"([^"]+)"'
        matches = re.findall(pattern, webpage)
        if len(matches) >= 2:
            return matches[0], matches[1]
        return None, None

    def _fetch_nonce_token(self, action: str) -> str | None:
        """Fetch nonce token from AJAX endpoint."""
        data = {'action': action}
        try:
            response = self._request_webpage(
                self._AJAX,
                None,
                data=urlencode_postdata(data),
                headers=self._HEADERS,
            )
            if not response:
                return None
            response_text = self._webpage_read_content(response, self._AJAX, None)
            response_json = json.loads(response_text)
            return response_json.get('data')
        except (json.JSONDecodeError, AttributeError):
            return None

    def _get_iframe_html(self, data: dict[str, Any], action: str, nonce: str) -> str | None:
        """Fetch and decode iframe HTML from AJAX endpoint."""
        data_video = {
            'action': action,
            'nonce': nonce,
            **data,
        }
        try:
            response = self._request_webpage(
                self._AJAX,
                video_id=str(data.get('id', '')),
                data=urlencode_postdata(data_video),
                headers=self._HEADERS,
            )
            if not response:
                return None

            response_text = self._webpage_read_content(response, self._AJAX, None)
            response_json = json.loads(response_text)

            if 'data' in response_json:
                return base64.b64decode(response_json['data']).decode('utf-8')
        except (
            base64.binascii.Error,
            json.JSONDecodeError,
            UnicodeDecodeError,
            AttributeError,
        ):
            pass
        return None

    @staticmethod
    def _extract_direct_link(iframe: str) -> str | None:
        """Extract direct video link from iframe HTML."""
        patterns = [
            r'src="(https://pixeldrain\.com[^"]+)',
            r'src="(https://[^"]+\.mp4[^"]*)',
            r'href="(https://[^"]+\.mp4[^"]*)',
        ]
        for pattern in patterns:
            match = re.search(pattern, iframe)
            if match:
                return match.group(1)
        return None


class OtakuDesuIE(OtakuDesuBase):
    """OtakuDesu episode extractor."""

    IE_NAME = 'otakudesu'
    _VALID_URL = OtakuDesuBase._BASE_URL_RE % r'episode/(?P<slug>[^/]+?)(?:/|$)'

    def _real_extract(self, url: str) -> dict[str, Any]:
        slug = self._match_valid_url(url).group('slug')
        webpage = self._download_webpage(url, slug)

        data_contents = self._extract_data_contents(webpage)
        if not data_contents:
            self.report_warning('No data-content found in webpage')
            return {'id': slug, 'formats': []}

        action, nonce = self._extract_nonce_data(webpage)
        nonce_token = None
        if action and nonce:
            nonce_token = self._fetch_nonce_token(nonce)

        if not nonce_token:
            self.report_warning('Failed to fetch nonce token')
            return {'id': slug, 'formats': []}

        formats = []
        for data_str in data_contents:
            data_dict = self._decode_data(data_str)
            if not data_dict:
                continue

            iframe_html = self._get_iframe_html(data_dict, action, nonce_token)
            if not iframe_html:
                continue

            direct_url = self._extract_direct_link(iframe_html)
            if not direct_url:
                continue

            quality = data_dict.get('q', '')
            height = int(quality.replace('p', '')) if quality else None

            formats.append(
                {
                    'url': direct_url,
                    'ext': 'mp4',
                    'resolution': quality,
                    'format_id': str(data_dict.get('i', '')),
                    'quality': height,
                    'height': height,
                },
            )

        # Sort by quality descending
        formats.sort(key=lambda x: x.get('quality') or 0, reverse=True)

        return {
            'id': str(data_dict.get('id', slug)) if data_dict else slug,
            'title': self._og_search_title(webpage, default=slug),
            'formats': formats,
        }


class OtakuDesuPlaylistIE(OtakuDesuBase):
    """OtakuDesu anime playlist extractor."""

    IE_NAME = 'otakudesu:playlist'
    _VALID_URL = OtakuDesuBase._BASE_URL_RE % r'anime/(?P<slug>[^/]+)'

    @staticmethod
    def _extract_episode_links(webpage: str) -> list[str]:
        """Extract all episode links from anime page."""
        pattern = r'href="(https://otakudesu\.best/episode/[^/?]+)'
        matches = re.findall(pattern, webpage, re.DOTALL)
        # Remove duplicates while preserving order
        seen = set()
        unique_links = []
        for link in matches:
            if link not in seen:
                seen.add(link)
                unique_links.append(link)
        return list(reversed(unique_links))

    def _real_extract(self, url: str) -> dict[str, Any]:
        slug = self._match_valid_url(url).group('slug')
        webpage = self._download_webpage(url, slug)

        episode_links = self._extract_episode_links(webpage)
        if not episode_links:
            self.report_warning('No episode links found')
            return {
                'id': slug,
                'title': slug,
                'entries': [],
            }

        entries = []
        for link in episode_links:
            entries.append(
                self.url_result(
                    link,
                    ie=OtakuDesuIE,
                    video_id=slug,
                ),
            )

        return self.playlist_result(
            entries,
            playlist_id=slug,
            playlist_title=self._og_search_title(webpage, default=slug),
        )
