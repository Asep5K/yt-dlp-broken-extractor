
import re

from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import (
    decode_packed_codes,
    get_element_by_id,
    int_or_none,
    mimetype2ext,
    parse_resolution,
    sanitize_url,
    str_or_none,
    traverse_obj,
    try_call,
    unescapeHTML,
)


class KraKenFilesIE(InfoExtractor):
    # https://krakenfiles.com/view/ym8mqAovRT/file.html
    IE_NAME = 'krakenfiles'
    _VALID_URL = r'https://krakenfiles.com/view/(?P<id>\w+)/file.html'
    _EMBED_REGEX = [r'<a\shref="(?P<url>https://krakenfiles\.com/view/\w[^"])"']
    _ENABLED = False

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        # content = get_element_html_by_class('play-video-parent', webpage)
        # resp = self._request_webpage(url, display_id)
        # print(resp.headers)
        # url, mimetype = self._html_search_regex(r'<source\ssrc="(?P<url>[^"]+)"\s*type="(?P<mime>[^"]+)"[^>]', content, 'url & ext', group=('url', 'mime'))
        title = self._og_search_title(webpage)
        return {
            'url': url,
            'id': display_id,
            'title': title,
            # 'ext': mimetype2ext(mimetype),
            'thumbnail': self._og_search_thumbnail(webpage),
            **parse_resolution(title),
            'http_request': {
                'referer': 'https://krakenfiles.com/',
            },
        }


class PixelDrainIE(InfoExtractor):
    # https://pixeldrain.com/u/qptTixH5
    # https://pixeldrain.com/api/file/HqDA7cxT XXX: aja sendiri
    # "https://pixeldrain.com/l/WksjzbvX"
    # "https://pixeldrain.com/api/file/B5TzidMg"
    # _VALID_URL = r'https://pixeldrain\.com/(u|l|api/file)/(?P<id>\w+)'
    IE_NAME = 'pixeldrain'
    _VALID_URL = r'https://pixeldrain\.com/u/(?P<id>\w+)'
    _EMBED_REGEX = [
        r'<iframe[^>]+src="(?P<url>https://pixeldrain\.com/u[^"]+)"',
        r'href="(?P<url>https://pixeldrain\.com/u[^"]+)"',
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        title = self._og_search_title(webpage) or self._html_extract_title(webpage)
        uerel = self._og_search_video_url(webpage, fatal=False, default=self._og_search_url(webpage))
        response = self._request_webpage(uerel, video_id)
        if response.headers.get('Content-Type').lower() != 'video/mp4':
            self.raise_no_formats('', expected=True)
        return {
            'id': video_id,
            'title': title,
            'url': response.url,
            'thumbnail': self._og_search_thumbnail(webpage),
            'description': self._og_search_description(webpage),
            'ext': mimetype2ext(self._og_search_property('video:type', webpage, 'mime type', fatal=False, default=response.headers.get('Content-Type'))),
            'filesize': int_or_none(response.headers.get('Content-Length')),
            **parse_resolution(title),
        }


class StremTapeIE(InfoExtractor):
    # https://streamtape.com/e/vLLabkQwpzsw9j/
    # https://streamtape.com/e/8vrW77ZL3bioomq/"
    IE_NAME = 'streamtape'
    _VALID_URL = r'https://streamtape\.com/e/(?P<id>\w+)/?$'
    _WORKING = False

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        real_url = self._is_valid_url(webpage)
        response = self._request_webpage(real_url, video_id, expected_status=[200, 302, 403])
        return {
            'id': video_id,
            'url': response.url,
            'title': self._og_search_title(webpage),
            'description': self._og_search_description(webpage),
            'thumbnail': self._og_search_thumbnail(webpage),
            'ext': mimetype2ext(response.headers.get('Content-Type')) or 'mp4',
            'filesize': int_or_none(response.headers.get('Content-Length')),
        }

    def _is_valid_url(self, webpage):
        valid_token = self._get_valid_token(webpage)
        url_with_a_fake_token = get_element_by_id('botlink', webpage)
        url_with_a_real_token = self._replace_token(url_with_a_fake_token, valid_token)
        return self.__urljoin(url_with_a_real_token) + '&stream=1'

    def _replace_token(self, url, token):
        try:
            return re.sub(r'token=[\w%~-]+', token, url)
        except Exception as e:
            self.raise_no_formats(msg=e, expected=True)

    def _get_valid_token(self, webpage):
        # document.getElementById('ideoolink').innerHTML = "//streamtape.com/get_video?id=vL" + ''+ ('xnftbabkQwpzsw9j&expires=1773149492&ip=F0SSKRWRKxSHDN&token=ygxLXobytw63').substring(3).substring(1);
        # document.getElementById('ideoolink').innerHTML = "/streamtape.c" + ''+ ('xcdbom/get_video?id=vLLabkQwpzsw9j&expires=1773149419&ip=F0SSKRWRKxSHDN&token=cEnvdrQim9R7').substring(1).substring(2);
        # document.getElementById('ideoolink').innerHTML = "/streamtape.com/get_video?id" + ''+ ('xcdb=vLLabkQwpzsw9j&expires=1773149036&ip=F0SSKRWRKxSHDN&token=YeVyoacAxwpq').substring(1).substring(2);
        # document.getElementById('ideoolink').innerHTML = "//streamta" + ''+ ('xnftbe.com/get_video?id=vLLabkQwpzsw9j&expires=1773143288&ip=F0SSKRWRKxSHDN&token=khQAU0sN3twP').substring(3).substring(1);
        regex = r"""(?x)
                    document\.getElementById
                    \(\'ideoolink\'\)\.innerHTML\s*=\s*
                    "(?:[^"]+)"\s*\+\s*''\+\s*\(\'([^']+)\'\)
                    \.substring\((\d+)\)\.substring\((\d+)\)
                """
        raw_url = self._search_regex(regex, webpage, 'token')
        # xcdbm/get_video?id=vLLabkQwpzsw9j&expires=1773151423&ip=F0SSKRWRKxSHDN&token=9SwULGaXgV9Y
        if raw_url and 'token' in raw_url:
            return self._search_regex(r'&(token=.+)', raw_url, 'real token')

    @staticmethod
    def __urljoin(path):
        if path.startswith('//'):
            return 'https:' + path
        elif path.startswith('/'):
            return 'https:/' + path
        else:
            return path


class OdvidHideEmbedIE(InfoExtractor):
    # "https://odvidhide.com/embed/3h4tjtb3xswr"
    IE_NAME = 'odvidhide:embed'
    _VALID_URL = r'https://odvidhide\.com/embed/(?P<id>[\w]+)'

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id, tries=3, timeout=30, expected_status=[200, 403], impersonate=True)
        longor = 'File is no longer available as it expired or has been deleted.'
        if longor in webpage:
            self.raise_no_formats(msg=longor, expected=True)
        decoded_page = decode_packed_codes(webpage)
        json_data = self._search_json(r'var\s*links=', decoded_page, 'JSON data', display_id)
        return {
            'id': display_id,
            'title': self._html_extract_title(webpage),
            'formats': self._extract_m3u8_formats(json_data.get('hls2'), display_id),
        }


class DinTeZuVioIE(OdvidHideEmbedIE):
    # "https://dintezuvio.com/embed/pdoone5gsb8s"
    IE_NAME = 'dintezuvio:embed'
    _VALID_URL = r'https://dintezuvio\.com/embed/(?P<id>\w+)'


class MinoChiNosIE(OdvidHideEmbedIE):
    IE_NAME = 'minochinos:embed'
    # "https://minochinos.com/embed/1l11fhixp1dz"
    _VALID_URL = r'https://minochinos.com/embed/(?P<id>\w+)'


class FiledonIE(InfoExtractor):
    # https://filedon.co/embed/TwBIrZ2kRz
    #  https://filedon.co/embed/fn5i87h4mzbw # XXX: 404
    # <iframe src="https://filedon.co/embed/MT6G4YFp04"
    IE_NAME = 'filedon:embed'
    _VALID_URL = r'https://filedon\.co/embed/(?P<id>[\w]+)'
    _EMBED_REGEX = [r'<iframe\ssrc="(?P<url>https://filedon\.co/embed[^"]+)"']

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
                    lambda: mimetype2ext(traverse_obj(json_data, ('props', 'files', 'mime_type')))),
                'filesize': traverse_obj(json_data, ('props', 'files', 'size', {int_or_none})),
            }


class WibuFileIE(InfoExtractor):
    # 'https://api.wibufile.com/embed/265137d7-534a-49ea-9e33-ec1744a99a07'
    IE_NAME = 'wibufile:embed'
    _VALID_URL = r'https://api\.wibufile\.com/embed/(?P<id>[\w-]+)$'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        tries = self.get_param('retries')
        for i in range(1, tries):
            webpage = self._download_webpage(url, video_id, headers={'referer': 'https://v2.samehadaku.how/'})
            path_url = self._search_regex(r'\$\.ajax\(\{\s*url:\s*"(?P<url>[^"]+)[^,]"', webpage, 'url')
            request_url = sanitize_url(path_url, scheme='https')
            title = self._og_search_title(webpage) or self._html_extract_title(webpage)

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
