from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import (
    mimetype2ext,
    parse_resolution,
    sanitize_url,
    traverse_obj,
)

"""
{
  "status": "ok",
  "server_time": "2026-03-09T06:46:44+0700",
  "query": {
    "source": "db",
    "id": "7317",
    "alt": "-1"
  },
  "embed_link": "//api.wibufile.com/embed/48d07574-c797-429a-b737-d33f5580d107/?alt=-1",
  "download_link": "//api.wibufile.com/download/48d07574-c797-429a-b737-d33f5580d107/?alt=-1",
  "request_link": "//api.wibufile.com/embed2/?source=db&id=7317&alt=-1",
  "title": "HellMode 01",
  "poster": "",
  "sources": [
    {
      "file": "https://s0.wibufile.com/video01/HellMode-01-480p-SAMEHADAKU.CARE.mp4",
      "type": "video/mp4",
      "label": "Original"
    }
  ],
  "tracks": []
}

"""

# SEMRAWUT


class WibufileIE(InfoExtractor):
    IE_NAME = 'wibufile'
    # 'https://api.wibufile.com/embed/265137d7-534a-49ea-9e33-ec1744a99a07'
    _VALID_URL = r'https://api\.wibufile\.com/embed/(?P<id>[\w-]+)$'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        tries = self.get_param('retries')
        for i in range(1, tries):
            webpage = self._download_webpage(url, video_id, headers={'referer': 'https://v2.samehadaku.how/'})
            path_url = self._search_regex(r'\$\.ajax\(\{\s*url:\s*"(?P<url>[^"]+)[^,]"', webpage, 'url')
            request_url = sanitize_url(path_url, scheme='https')
            title = self._og_search_title(webpage) or self._html_extract_title(webpage)
            tries = self.get_param('retries')
            data_dict = self._download_json(request_url, 'JSON data')
            status = data_dict.get('status')
            if status == 'fail':
                self.to_screen(f'retry {i}')
                continue
            if status == 'ok':
                formats = traverse_obj(data_dict, ('sources'))
                if not formats:
                    self.raise_no_formats(msg='No formats found', expected=True, video_id=video_id)
                for fmt in formats:
                    url = fmt.pop('file')
                    ext = fmt.pop('type')
                    fmt.pop('label')
                    fmt.update({'url': url, 'ext': mimetype2ext(ext), **parse_resolution(url)})
                return {
                    'id': traverse_obj(data_dict, ('query', 'id'), default=video_id),
                    'title': traverse_obj(data_dict, ('title'), default=title),
                    'formats': formats,
                }
