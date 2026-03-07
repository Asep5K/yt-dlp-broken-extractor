from yt_dlp.extractor.common import InfoExtractor


class VidaraIE(InfoExtractor):
    # https://vidara.to/e/socLCRdhMtOkc
    IE_NAME = 'vidara'
    _VALID_URL = r'https://vidara\.to/e/(?P<id>[\w]+)$'
    _EMBED_REGEX = [r'<iframe[^>]+src="(?P<url>https?://vidara\.to/e/[^"]+)"']

    def _real_extract(self, url):
        video_id = self._match_id(url)
        vidara_page = self._download_webpage(url, 'vidara page')
        vidara_json = self._download_json('https://vidara.to/api/stream', video_id, query={'filecode': video_id}, headers={'referer': url})
        return {
            'id': video_id,
            'thumbnail': vidara_json.get('thumbnail'),
            'title': self._html_extract_title(vidara_page),
            'formats': self._extract_m3u8_formats(vidara_json.get('streaming_url'), video_id),
            'language': vidara_json.get('default_sub_lang'),
        }
