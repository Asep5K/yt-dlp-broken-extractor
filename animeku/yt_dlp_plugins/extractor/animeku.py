import re

from yt_dlp.extractor.common import InfoExtractor


# situs sepi anime nya sedikit, jadi kode nya apa ada nya
class AnimeKu(InfoExtractor):
    def _get_html_page(self, url: str, slug: str) -> str:
        return self._download_webpage(url, slug)

    @classmethod
    def _get_urls(cls, webpage: str, title: str) -> list:
        # url asli =  https://animeku.site/anime/sozai-saishuka-no-isekai-ryokouki/
        # slug = sozai-saishuka-no-isekai-ryokouki
        # url match = <a href="https://animeku.site/sozai-saishuka-no-isekai-ryokouki-episode-12end/">
        pattern = fr'https://animeku\.site/{title}-episode-\d+(?:end)?/'
        episode_urls = re.findall(pattern, webpage)
        return list(dict.fromkeys(episode_urls))



    def _build_bunny_url_list(self, webpage: str ,title: str) -> list | None:
        episodes_link = self._get_urls(webpage, title)
        episodes = []
        for url in episodes_link:
            if url not in episodes:
                episodes.append(self._get_embed_url(url))
        return reversed(episodes)


    def _get_embed_url(self, link_episode):
        webpage = self._get_html_page(link_episode, link_episode)
        pattern = r'><iframe\ssrc="(https://player[^"]+)'
        match = re.search(pattern, webpage,re.DOTALL)
        if match:
            return match.group(1)
        return None


class AnimeKuIE(AnimeKu):
    IE_NAME = 'animeku'
    IE_DESC = 'Animeku website extractor'
    _VALID_URL = r'https?://animeku\.site/anime/(?P<slug>[^/?]+)'

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        soup = mobj.group('slug')
        webpage = self._get_html_page(url, soup)
        if not webpage:
            self.raise_no_formats('No episodes found')

        # Create playlist entries
        entries = []
        for ep_url in self._build_bunny_url_list(webpage, soup):
            if ep_url not in entries:
                # Biarkan extractor lain berkerja
                entries.append(self.url_result(
                    ep_url,
                    ie_key='BunnyCdn',
                    video_id=soup,
                ))

        # Return as playlist
        return self.playlist_result(
            entries,
            playlist_id=soup,
            playlist_title=self._og_search_title(webpage, default=soup),
        )
