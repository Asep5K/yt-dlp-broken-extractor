from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import (
    ExtractorError,
    get_element_html_by_id,
    urlencode_postdata,
)


# ini situs mentok 360p kah?
class TokuSatSuIE(InfoExtractor):
    IE_NAME = 'tokusatsuindo'
    _VALID_URL = r'https://www\.tokusatsuindo\.com/(?P<slug>[\w-]+)/?$'

    def _real_extract(self, url):
        slug = self._match_valid_url(url).group('slug')
        webpage = self._download_webpage(url, slug)

        # 1. cari layerc ontent
        content = get_element_html_by_id('muvipro_player_content_id', webpage)
        if not content:
            raise ExtractorError('No player content found', ecpected=True)

        # 2. extract video_id
        video_id = self._search_regex(r'data-id="(\d+)"', content, 'video_id')
        # 3. loop semua tab server
        formats = []
        thumbnails = []
        for tab_id in range(1, 3):  # cuma 3 server kurasa
            tab_html = get_element_html_by_id(f'p{tab_id}', content)
            if not tab_html:
                break

            # 4. request ke aja sendiri: https://tenor.com/view/aja-sendiri-gif-6852732088276811860
            embed_html = self._download_webpage(
                'https://www.tokusatsuindo.com/wp-admin/admin-ajax.php',
                video_id,
                data=urlencode_postdata({
                    'action': 'muvipro_player_content',
                    'tab': f'p{tab_id}',
                    'post_id': video_id,
                }), headers={'Referer': url}, note=f'Fetching server {tab_id}')

            # 5. extract iframe dari response
            iframe_url = self._search_regex(r'<iframe[^>]+src="([^"]+)"', embed_html, 'embed url', default=None)

            if iframe_url and 'gdplayer' not in iframe_url:
                # 6. panggil extractor yang sesuai
                if 'drive.google.com' in iframe_url:
                    ie = self._downloader.get_info_extractor('GoogleDrive')
                elif 'myvidplay.com' in iframe_url:
                    ie = self._downloader.get_info_extractor('MyVidPlay')
                else:
                    self.report_warning(f'Unsupported URL: {iframe_url}')
                    continue

                video_data = ie.extract(iframe_url)
                if video_data:
                    if video_data.get('formats'):
                        formats.extend(video_data['formats'])
                    elif video_data.get('url'):
                        formats.append(video_data)
                    if video_data.get('thumbnails'):
                        thumbnails.extend(video_data['thumbnails'])
        # 7 done, klo ga errrrror
        return {
            'id': slug,
            'title': self._html_extract_title(webpage),
            'formats': formats,
            'thumbnails': thumbnails,
        }
