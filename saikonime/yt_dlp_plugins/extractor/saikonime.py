import html
import json
import re

from yt_dlp.extractor.common import InfoExtractor, SearchInfoExtractor


# TODO: Tambahin error handling
class SaikoNimeIE(InfoExtractor):
    IE_NAME = 'saikonime'
    # https://tv.saikonime.com/sousou-no-frieren-season-2-episode-01-subtitle-indonesia/
    _VALID_URL = r'https://tv\.saikonime\.com/(?P<slug>.*?(?:-episode-[^/]+))'

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        soup = mobj.group('slug')
        html_webpage = self._download_webpage(url, soup)


        video_metadata = self._search_json(
            r'<script type="application/ld\+json">',
            html_webpage, 'video metadata', soup,
            end_pattern='</script>',
        )


        embed_url = video_metadata.get('embedUrl')
        video_id = embed_url.split('/')[-1]

        blogger_link = self._get_blogger_link(embed_url, video_id)

        # biarkan extractor lain berkerja
        return self.url_result(url=blogger_link, ie='Blogger', video_id=video_id, video_title=video_metadata['name'])


    def _get_blogger_link(self, url, video_id):
        html_webpage = self._download_webpage(url, video_id)

        return self._html_search_regex(
            pattern=r'src="(https://www\.blogger\.com/video.g[^"]+)',string=html_webpage, name='bloger')


class SaikoNimePlaylistIE(InfoExtractor):
    IE_NAME = 'saikonime playlist'
    # https://tv.saikonime.com/anime/sousou-no-frieren-season-2
    _VALID_URL = r'https://tv\.saikonime\.com/anime/(?P<slug>\w.+)'

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        soup = mobj.group('slug')

        episodes = self._get_all_episodes_from_html(url, soup)
        entries = []
        for episode in episodes:
            entries.append(self.url_result(
                url=episode, ie=SaikoNimeIE, video_id=soup,
            ))

        return self.playlist_result(entries=entries,playlist_id=soup, plalist_title=soup)


    def _get_all_episodes_from_html(self, url: str, video_id: str) -> list:
        html_page = self._download_webpage(url, video_id)

        search_regex = r'href="(https://tv\.saikonime\.com/(?:[^/]+?)(?:-episode-\d+)?[^/]*/?)"'
        title = self._html_extract_title(html_page)
        matches = re.findall(search_regex, html_page, re.DOTALL)
        if title:
            self._TITLE = title

        if matches and isinstance(matches, list):
            episode_urls = []
            for url in matches:
                clean_url = url.split('"')[0]
                if '-episode-' in clean_url and clean_url.endswith('/'):
                    episode_urls.append(clean_url)

            return reversed(episode_urls)
        return None

# TODO: nambahin search engine
class SaikoNimeSearchIE(SearchInfoExtractor):
    IE_NAME = 'saikonime:search'
    _SEARCH_KEY = 'saikonime'
    _WORKING = False
    _ENABLED = False
    # https://tv.saikonime.com/livewire/message/search-component


    def _get_initial_data(self, webpage):
        raw_json = self._search_regex(
        r'wire:initial-data="({.+?})"',
        webpage, 'livewire data',
    )

        # 2. Unescape HTML entities

        clean_json = html.unescape(raw_json)
        return json.loads(clean_json)


    def _get_token(self):
        homepage = self._download_webpage('https://tv.saikonime.com', 'get token')
        pattern = r'name="csrf-token"\scontent="(.*?)">'
        csrf_token = self._html_search_regex(pattern, homepage, name='csrf-token')
        # wire:id="dxBc3BQ7PUeBiQpCs0B9"
        component_id = self._html_search_regex(r'wire:id="(.*?)"', homepage, name='component:id')

        data = self._get_initial_data(homepage)


        return csrf_token, component_id, data

    @staticmethod
    def _build_data(query, data_dict):

        # print(data_dict)
        data = {
            'fingerprint': data_dict['fingerprint'],
            'serverMemo': data_dict['serverMemo'],
            'updates': [
                {
                    'type': 'syncInput',
                    'payload': {
                        'id': 'modal-search',
                        'name': 'q',
                        'value': query,
                    },
                },
            ],
        }

        return json.dumps(data, ensure_ascii=False)

    def _search_results(self, query):

        _token, _comp, _data = self._get_token()
        # print(token, comp, data, type(data))

        # results = self._request_webpage(endpoint, query, data=self._build_data(query, data), headers=headers)
        # results = self._download_json(endpoint, query, data=self._build_data(query, data), headers=headers)
        # print(results)
        # print(self._webpage_read_content(results, endpoint, query))
