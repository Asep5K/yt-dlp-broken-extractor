import base64
import re

from yt_dlp.extractor.common import InfoExtractor, SearchInfoExtractor
from yt_dlp.utils import (
    get_domain,
    get_element_by_class,
    get_element_html_by_class,
    int_or_none,
    merge_dicts,
    str_or_none,
    traverse_obj,
    urlencode_postdata,
)


class OtaKuDesuIE(InfoExtractor):
    IE_NAME = 'otakudesu'
    # https://otakudesu.blog/episode/gnsa-episode-1-sub-indo/
    _VALID_URL = r'https://otakudesu\.blog/episode/(?P<slug>[\w-]+)/?$'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._referer = None
        self._ajax_dot_king_php = 'https://otakudesu.blog/wp-admin/admin-ajax.php'

    def _real_extract(self, url):
        self._referer = url
        slug = self._match_valid_url(url).group('slug')
        webpage = self._download_webpage(url, slug)
        return merge_dicts(
            self._extract(webpage, slug),
            {'title': self._og_search_title(webpage) or self._html_extract_title(webpage) or slug})

    def _extract(self, webpage, slug):
        formats = []
        blocked_domain = ['desustream.info', 'mega.nz']
        for data_json in self._request_url(webpage):
            url = data_json.pop('url', None)
            # TODO: bikin extractor mega.nz & desustream
            if not url or any(domain in url for domain in blocked_domain):
                self.write_debug(f'Unsuported url: {url}')
                continue
            info = self._downloader.extract_info(url, download=False, process=False)
            try:
                if info.get('formats'):
                    formats.extend(merge_dicts(fmt, data_json)for fmt in info['formats'])
                elif info.get('url'):
                    formats.append(merge_dicts(info, data_json))
            except AttributeError:
                self.report_warning('No formats or url found!')
                continue
        return {'id': str_or_none(data_json['id']) or slug, 'formats': formats}

    def _request_url(self, webpage):
        for postdata in self._get_data_content(webpage):
            json_data = self._download_json(self._ajax_dot_king_php, 'base64 iframe',
                                            data=urlencode_postdata(postdata), headers={'referer': self._referer})
            if not json_data.get('data'):
                continue
            try:
                iframe_html = base64.b64decode(json_data['data']).decode()
                url = self._html_search_regex(r'<iframe[^>]+src="(?P<url>[^"]+)"', iframe_html, 'url', group='url')
                if not url:
                    continue
                domain = get_domain(url)
                q_h = traverse_obj(postdata, ('q', {lambda qh: int_or_none(qh.replace('p', ''))}))
                yield {
                    'url': url,
                    'quality': q_h,
                    'height': q_h,
                    'format_note': f'{domain} {q_h}',
                    **traverse_obj(postdata, {
                        'id': ('id'),
                        'resolution': ('q')}),
                }
            except base64.binascii.Error as e:
                self.report_warning(f'Base64 error: {e}')
                continue
            except Exception as e:
                self.report_warning(f'Unexpected error: {e}')
                continue

    def _get_action_and_nonce(self, webpage):
        postdata_action = self._search_regex(r'\.fail\(function.*?[^\)]\$\.ajax.*?[^}]data:\s*{\s*action:"([^}]+)"', webpage, 'action token')
        nonce = self._download_json(self._ajax_dot_king_php, postdata_action, query={'action': postdata_action}, note='Get Nonce')
        action = self._search_regex(r'action["\']?\s*:\s*["\']([a-f0-9]{32})["\']', webpage, 'nonce action', fatal=False, default='2a3505c93b0035d3f455df82bf976b84')
        datapost = {'action': action, 'nonce': nonce['data']}
        self.write_debug(datapost)
        return datapost

    def _get_data_content(self, webpage):
        datapost = self._get_action_and_nonce(webpage)
        mirror_stream = get_element_by_class('mirrorstream', webpage)
        for base64_url in re.finditer(r'data-content="(?P<b64>[^"]+)">', mirror_stream):
            if not base64_url:
                continue
            data_str = base64.b64decode(base64_url.group('b64')).decode()
            postdata_json = self._parse_json(data_str, 'base64 data post')
            self.write_debug(postdata_json)
            yield {**postdata_json, **datapost}


class OtaKuDesuAnimeIE(InfoExtractor):
    IE_NAME = 'otakudesu:anime'
    _VALID_URL = r'https://otakudesu.blog/anime/(?P<slug>[\w-]+)/?$'

    def _real_extract(self, url):
        slug = self._match_valid_url(url).group('slug')
        webpage = self._download_webpage(url, slug)
        html = get_element_html_by_class('venser', webpage)
        entries = []
        blocked = ['/batch/', '/lengkap/']
        for match_url in re.finditer(r'href="(?P<url>https://otakudesu[^"]+)"[^>]target=', html):
            if not match_url or any(block in match_url.group('url') for block in blocked):
                continue
            entries.append(self.url_result(url=match_url.group('url'), ie=OtaKuDesuIE.ie_key()))
        return self.playlist_result(entries=reversed(entries), playlist_title=self._og_search_title(webpage))


class OtaKuDesuSearchIE(SearchInfoExtractor):
    IE_NAME = 'otakudesu:search'
    _SEARCH_KEY = 'otakudesu'
    # 'https://otakudesu.blog/?s=blue+archive&post_type=anime'
    # </i> Hasil Pencarian (Max. hanya sampai 12 hasil)<h1></div>

    def _search_results(self, query):
        webpage = self._download_webpage('https://otakudesu.blog/', query, query={'s': query, 'post_type': 'anime'})
        for match_url in re.finditer(r'title="(?P<url>https://otakudesu[^"]+)"', webpage):
            if not match_url:
                continue
            url = match_url.group('url')
            yield self.url_result(url=url, ie=OtaKuDesuAnimeIE.ie_key())
            # {'_type': 'url', 'id': query, 'url': url, 'ie_key': 'OtaKuDesuAnime'}
