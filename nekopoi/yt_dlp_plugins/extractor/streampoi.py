import json
import re
import subprocess
from urllib.parse import urlencode

from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils._jsruntime import NodeJsRuntime
from yt_dlp.utils import ExtractorError, urlencode_postdata

'''
<body topmargin=0 leftmargin=0>
<form id="F1" action="/dl" method="POST">
<input type="hidden" name="op" value="embed">
<input type="hidden" name="file_code" value="">
<input type="hidden" name="auto" value="1">
<input type="hidden" name="referer" value="">
'''

class StreamPoiIE(InfoExtractor):
    IE_NAME = 'streampoi'
    # https://streampoi.com/e/6b8kkjwfp0jp
    _VALID_URL = r'https://streampoi\.com/e/(?P<id>\w+)'
    _ENDPOINT = 'https://streampoi.com/dl'
    _WORKING = False
    _ENABLED = False

    @staticmethod
    def _get_preamble():
        return '''
        // Fake jwplayer
        globalThis.jwplayer = function() {
            return {
                setup: function(config) {
                    console.log(JSON.stringify(config));
                    return this;
                },
                on: function() { return this; },
                addButton: function() { return this; }
            };
        };

        // Fake jQuery
        globalThis.$ = function() {
            return {
                hide: function() { return this; },
                show: function() { return this; },
                fadeIn: function() { return this; },
                detach: function() { return this; },
                insertAfter: function() { return this; },
                insertBefore: function() { return this; }
            };
        };
        $.ajaxSetup = function() { return this; };
        $.get = function() {
            return { done: function(cb) { cb(''); return this; } };
        };
        $.cookie = function() { return null; };

        // Fake localStorage
        globalThis.localStorage = {
            getItem: function() { return null; },
            setItem: function() {},
            removeItem: function() {}
        };

        globalThis.ls = globalThis.localStorage;
        '''

    def __init__(self):
        self._runtime = NodeJsRuntime()

        if not self._runtime.info:
            raise ExtractorError('NodeJs is required!')


    def _real_extract(self, url: str, title:str | None = None):
        token = self._match_id(url)
        data = self._build_data(url, token)
        html_page = self._request_webpage(self._ENDPOINT, token, data=data)
        json_dict = self._decode_js(self._get_obfuscated_js(html_page))

        formats = self._extract_m3u8_formats(
                json_dict['sources'][0]['file'],
                video_id=token,
                ext='mp4',
            )
        if formats:
            return {
                'id': token,
                'formats': formats,
            }
        return {}


    def _decode_js(self , obfs_js: str) -> dict:
        full_js = self._get_preamble() + obfs_js
        result = subprocess.run([self._runtime.info.path, '-e', full_js],
                capture_output=True, text=True)
        if result.returncode == 0:
            return json.loads(result.stdout)

        return {}

    def _get_obfuscated_js(self, html_page: str) -> str:
        html_page = html_page.read().decode('utf-8')
        obfuscated_code = re.search(r'\'>(eval\(function.*?)</script>', html_page, re.DOTALL)
        if not obfuscated_code:
            raise ExtractorError('gak nemu js njir')
            return None
        return obfuscated_code.group(1)


    def _build_data(self, url:str , token: str) -> dict:
        webpage = self._download_webpage(url,token)
        _op = self._html_search_regex(r'name="op" value="(.*?)"', webpage, name='op')
        _auto = self._html_search_regex(r'name="auto" value="(.*?)"', webpage, name='auto')
        if not _op and not _auto:
            raise ExtractorError('gak nemu op sama auto njir')

        return urlencode_postdata({
            'op': _op,
            'auto': _auto,
            'file_code': token,
            'referer': url,
        })


# ini yang paling broken sih
# sangat malas banget