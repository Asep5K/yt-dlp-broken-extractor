from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import mimetype2ext, parse_resolution, traverse_obj

"""
 window.viewer_data = {"type":"file","api_response":{"id":"qptTixH5","name":"Anoter-02_480p-SAMEHADAKU.CARE.mp4","size":39293667,"views":140,"bandwidth_used":5595154005,"bandwidth_used_paid":0,"downloads":190,"date_upload":"2024-08-02T08:17:22.647Z","date_last_view":"2026-03-07T16:50:28.803Z","mime_type":"video/mp4","thumbnail_href":"/file/qptTixH5/thumbnail","hash_sha256":"fee79f4f76542da180161718e4be7c5eebfbe90a7a006ba167ab6701d5f3c1d1","delete_after_date":"0001-01-01T00:00:00Z","delete_after_downloads":0,"availability":"","availability_message":"","abuse_type":"","abuse_reporter_name":"","can_edit":false,"can_download":true,"show_ads":true,"allow_video_player":true,"download_speed_limit":0},"captcha_key":"6Lfbzz4UAAAAAAaBgox1R7jU0axiGneLDkOA-PKf","embedded":false,"user_ads_enabled":true,"theme_uri":"/theme.css"}
"""


class PixelDrainIE(InfoExtractor):
    IE_NAME = 'pixeldrain'
    # https://pixeldrain.com/u/qptTixH5
    # https://pixeldrain.com/api/file/HqDA7cxT XXX: aja sendiri
    _VALID_URL = r'https://pixeldrain\.com/u/(?P<id>\w+)'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        title = self._og_search_title(webpage) or self._html_extract_title(webpage)
        json_data = self._search_json(r'window.viewer_data\s*=\s*', webpage, 'JSON data', video_id, fatal=False)
        return {
            'id': video_id,
            'title': title,
            'url': self._og_search_video_url(webpage),
            'thumbnail': self._og_search_thumbnail(webpage),
            'description': self._og_search_description(webpage),
            'ext': mimetype2ext(self._og_search_property('video:type', webpage, 'mime type', fatal=False, default='mp4')),
            **parse_resolution(title),
            **traverse_obj(json_data, {
                'filesize': ('api_response', 'size'),
                'view_count': ('api_response', 'views'),
            }),
        }
