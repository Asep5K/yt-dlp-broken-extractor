import base64
import itertools
import re
import secrets
import string
import sys
import time
from pathlib import Path

from yt_dlp.extractor.common import InfoExtractor, SearchInfoExtractor
from yt_dlp.utils import int_or_none, urljoin, ExtractorError

sys.path.insert(0, str(Path(__file__).parent))
from .streampoi import StreamPoiIE


class NekoPoiBase(InfoExtractor):
    """Base class for NekoPoi extractors with shared utilities"""

    @staticmethod
    def _generate_random_token():
        """Generate random token and expiry for MyVidPlay"""
        rand = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))
        expiry = int((time.time() + 3600) * 1000)  # 1 hour from now
        return rand, expiry

    @staticmethod
    def _get_links(webpage):
        """Extract all video embed links from NekoPoi page"""
        # patterns = r'<iframe\ssrc=(https://(?:vidnest|bigshare|myvidplay|streampoi)\.(?:io|com)[^\s]+)'
        patterns = r'<iframe\ssrc=(https://(?:vidnest|bigshare|myvidplay)\.(?:io|com)[^\s]+)'
        links = re.findall(patterns, webpage)
        return links or []

    def _parse_myvidplay(self, link, video_id):
        """Extract MyVidPlay video URL with resolution"""
        html = self._download_webpage(link, video_id)
        title = self._html_extract_title(html)
        md5 = re.search(r'\$\.get\(\'(/pass\w[^\']+)', html)
        token = re.search(r'return\sa+\s\+\s"(\?token[^"]+)', html)

        if not md5 or not token:
            self.report_warning(f'Failed to extract MyVidPlay data from {link}')
            return []

        md5_url = urljoin('https://myvidplay.com', md5.group(1))
        base_link = self._download_webpage(md5_url, video_id)

        rand, expiry = self._generate_random_token()
        valid_url = f'{base_link}{rand}{token.group(1)}{expiry}'
        height = re.search(r'\[(\d+p)\]', title, re.IGNORECASE)
        if height:
            format_id = height.group(1).lower()
            height = int(format_id.replace('p',''))
            width = ( height * 16 ) / 9

        return [{
            'url': valid_url,
            'title': title,
            'http_headers': {
                'Referer': 'https://myvidplay.com/',
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
            },
            'ext': 'mp4',
            'format_id': f'myvidplay-{height}',
            'height': int_or_none(height),
            'width': int_or_none(width),
        }]

    def _parse_bigshare(self, link, video_id):
        """Extract BigShare video URL"""
        page = self._download_webpage(link, video_id)

        url_match = re.search(r'url:\s\'(https://cdn\.bigshare\.io[^(,\')]+)', page)
        token_match = re.search(r'let token\s*=\s*["\']([^"\']+)["\']', page)

        if not url_match:
            self.report_warning(f'Failed to extract BigShare URL from {link}')
            return []

        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
        }

        if token_match:
            try:
                decoded_token = base64.b64decode(token_match.group(1)).decode('utf-8')
                headers['X-CSRF-TOKEN'] = decoded_token
            except Exception as e:
                self.report_warning(f'Failed to decode BigShare token: {e}')

        return [{
            'url': url_match.group(1),
            'http_headers': headers,
            'ext': 'mp4',
            'protocol': 'https',
            'format_id': 'bigshare',
        }]

    def _parse_vidnest(self, link, video_id):
        """Extract VidNest video formats using JWPlayer data"""
        page = self._download_webpage(link, video_id)

        try:
            jwplayer_data = self._extract_jwplayer_data(page, video_id, require_title=False)

            formats = []
            if isinstance(jwplayer_data, dict):
                formats = jwplayer_data.get('formats', [])
            elif isinstance(jwplayer_data, list):
                formats = jwplayer_data

            # Filter dan bersihin formats
            clean_formats = []
            for f in formats:
                if isinstance(f, dict) and 'url' in f:
                    f['format_id'] = f'vidnest-{f.get("height", "unknown")}'
                    f.setdefault('http_headers', {})
                    f['http_headers']['Referer'] = 'https://vidnest.io/'
                    clean_formats.append(f)

            return clean_formats

        except Exception as e:
            self.report_warning(f'Failed to extract VidNest data: {e}')
            return []

    def _parse_streampoi(self, link, video_id):
        """Extract StreamPoi video formats directly using StreamPoiIE"""
        try:
            # Get StreamPoi extractor instance
            streampoi_ie = self._downloader.get_info_extractor(StreamPoiIE.ie_key())

            if not streampoi_ie:
                # Fallback to delegation
                return [{
                    '_type': 'url',
                    'url': link,
                    'ie_key': StreamPoiIE.ie_key(),
                }]

            # Extract formats directly
            ie_result = streampoi_ie.extract(link)

            if ie_result and 'formats' in ie_result:
                formats = ie_result['formats']

                # Add proper headers
                for f in formats:
                    f.setdefault('http_headers', {})
                    f['http_headers']['Referer'] = 'https://streampoi.com/'
                    f['http_headers']['User-Agent'] = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
                    f['format_id'] = f'streampoi-{f.get("height", "unknown")}'

                self.to_screen(f'Extracted {len(formats)} formats from StreamPoi')
                return formats

        except Exception as e:
            self.report_warning(f'StreamPoi extraction failed: {e}')

        # Fallback
        return [{
            '_type': 'url',
            'url': link,
            'ie_key': StreamPoiIE.ie_key(),
        }]

    def _extract_links(self, link, video_id):
        """Route link to appropriate parser"""
        if 'bigshare' in link:
            return self._parse_bigshare(link, video_id)
        elif 'vidnest' in link:
            return self._parse_vidnest(link, video_id)
        elif 'myvidplay' in link:
            return self._parse_myvidplay(link, video_id)
        elif 'streampoi' in link: # broken malas fix
            return self._parse_streampoi(link, video_id)
        else:
            self.report_debug(f'Unsupported link type: {link}')
            return []


class NekoPoiIE(NekoPoiBase):
    IE_NAME = 'nekopoi'
    _VALID_URL = r'https?://(?:www\.)?nekopoi\.care/(?:hentai|jav|info/)?(?P<slug>[^/?]+)'

    _TESTS = [{
        'url': 'https://nekopoi.care/l2d-sepongan-columbina-bagai-vakum-penghisap-sperma-genshin-impact',
        'info_dict': {
            'id': 'l2d-sepongan-columbina-bagai-vakum-penghisap-sperma-genshin-impact',
            'title': 'Sepongan Columbina Bagai Vakum Penghisap Sperma! – Genshin Impact',
            'ext': 'mp4',
        },
        'params': {'skip_download': True},
    }]

    def _real_extract(self, url):
        # Extract video ID and download page
        mobj = self._match_valid_url(url)
        slug = mobj.group('slug')
        webpage = self._download_webpage(url, slug)

        # Extract and clean title
        video_title = self._html_extract_title(webpage)
        title_match = re.search(r'(?:[.*])?\s(.*)\s– NekoPoi', video_title)
        if title_match:
            video_title = title_match.group(1)

        # Get all video links
        links = self._get_links(webpage)
        if not links:
            raise ExtractorError('No video links found on page')

        formats = []
        delegate_urls = []

        # Process each link
        for link in links:
            results = self._extract_links(link, slug)

            # Ensure results is a list
            if not isinstance(results, list):
                results = [results] if results else []

            for item in results:
                # Skip non-dict items
                if not isinstance(item, dict):
                    self.report_debug(f'Skipping non-dict item: {type(item)}')
                    continue

                # Case 1: Direct format with URL
                if 'url' in item:
                    # Ensure required fields
                    item.setdefault('ext', 'mp4')
                    item.setdefault('protocol', 'https')
                    item.setdefault('http_headers', {})
                    # item.setdefault('format_id', str(i += 1))
                    formats.append(item)

                # Case 2: URL to delegate to another extractor
                elif item.get('_type') == 'url':
                    delegate_urls.append(item['url'])

                # Case 3: Unknown format
                else:
                    self.report_debug(f'Unknown result format: {item}')

        # Clean formats: ensure all are dicts with url
        formats = [f for f in formats if isinstance(f, dict) and 'url' in f]

        # Decision logic: Prefer direct formats over delegation
        if formats:
            return {
                'id': slug,
                'title': video_title or slug,
                'formats': formats,
                'thumbnail': self._og_search_thumbnail(webpage, default=None),
            }

        elif delegate_urls:
            # Use the first delegate URL
            return self.url_result(
                delegate_urls[0],
                ie=StreamPoiIE.ie_key(),
                video_id=slug,
                video_title=video_title or slug,
            )

        else:
            raise ExtractorError('No playable content found')


class NekoPoiSearchIE(SearchInfoExtractor, NekoPoiBase):
    IE_NAME = 'nekopoi:search'
    _SEARCH_KEY = 'nekopoi'

    @staticmethod
    def _extract_urls(html):
        """Extract video URLs from search results page"""
        pattern = r'</div><h2><a\shref=(https://nekopoi\.care[^>]+)'
        return re.findall(pattern, html)

    def _search_results(self, query):
        base_url = f'https://nekopoi.care/search/{query}'

        for page_num in itertools.count(0):
            url = f'{base_url}/page/{page_num}' if page_num > 0 else base_url

            try:
                webpage = self._download_webpage(
                    url, query,
                    note=f'Downloading page {page_num}',
                    fatal=False,
                )

                if not webpage or 'No results found' in webpage:
                    break

                links = self._extract_urls(webpage)

                for link in links:
                    yield self.url_result(link, ie=NekoPoiIE)

            except Exception as e:
                self.report_warning(f'Search page {page_num} failed: {e}')
                break

# Dari curl error sampe 306 baris Python — ini bukan bug, ini evolusi
# Malas maintain btw
