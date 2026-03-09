from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import (
    int_or_none,
    mimetype2ext,
    str_or_none,
    traverse_obj,
    try_call,
    unescapeHTML,
)


class FiledonIE(InfoExtractor):
    IE_NAME = 'filedon'
    _VALID_URL = r'https://filedon\.co/embed/(?P<id>[\w]+)'
    # https://filedon.co/embed/TwBIrZ2kRz

    #  https://filedon.co/embed/fn5i87h4mzbw # XXX: 404
    def _real_extract(self, url):
        video_id = self._match_id(url)
        filedon_page = self._download_webpage(url, video_id)
        json_data = self._search_json(r'<div\s*id="app"\s*data-page="', unescapeHTML(filedon_page), 'data json', video_id)
        if json_data and isinstance(json_data, dict):
            return {
                'id': traverse_obj(json_data, ('props', 'files', 'id', {str_or_none})),
                'url': traverse_obj(json_data, ('props', 'url')),
                'title': traverse_obj(json_data, ('props', 'files', 'name')),
                'ext': try_call(
                    lambda: traverse_obj(json_data, ('props', 'files', 'extension')),
                    lambda: mimetype2ext(traverse_obj(json_data, ('props', 'files', 'mime_type'))),
                ),
                'filesize': traverse_obj(json_data, ('props', 'files', 'size', {int_or_none})),
            }
