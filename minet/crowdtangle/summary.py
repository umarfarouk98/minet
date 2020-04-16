# =============================================================================
# Minet CrowdTangle Links Summary
# =============================================================================
#
# Function related to link summary using CrowdTangle's APIs.
#
from collections import namedtuple
from urllib.parse import quote

from minet.crowdtangle.exceptions import (
    CrowdTangleMissingTokenError,
    CrowdTangleInvalidTokenError,
    CrowdTangleInvalidRequest
)
from minet.utils import create_pool, request_json, RateLimiter, nested_get
from minet.crowdtangle.constants import (
    CROWDTANGLE_LINKS_DEFAULT_RATE_LIMIT,
    CROWDTANGLE_SUMMARY_DEFAULT_SORT_TYPE,
    CROWDTANGLE_SUMMARY_SORT_TYPES,
    CROWDTANGLE_DEFAULT_TIMEOUT,
    CROWDTANGLE_OUTPUT_FORMATS
)
from minet.crowdtangle.formatters import (
    format_post,
    format_summary
)

CrowdTangleSummaryResult = namedtuple('CrowdTangleSummaryResult', ['link', 'item', 'stats'])
CrowdTangleSummaryResultWithPosts = namedtuple('CrowdTangleSummaryResultWithPosts', ['link', 'item', 'stats', 'posts'])

URL_TEMPLATE = (
    'https://api.crowdtangle.com/links'
    '?token=%(token)s'
    '&count=%(count)s'
    '&startDate=%(start_date)s'
    '&includeSummary=true'
    '&link=%(link)s'
    '&sortBy=%(sort_by)s'
)


def forge_url(link, token, start_date, sort_by, include_posts=False):
    return URL_TEMPLATE % {
        'token': token,
        'count': 1 if not include_posts else 100,
        'start_date': start_date,
        'link': quote(link, safe=''),
        'sort_by': sort_by
    }


def crowdtangle_summary(iterator, token=None, start_date=None, with_top_posts=False,
                        rate_limit=CROWDTANGLE_LINKS_DEFAULT_RATE_LIMIT, key=None,
                        sort_by=CROWDTANGLE_SUMMARY_DEFAULT_SORT_TYPE, format='csv_dict_row'):

    if token is None:
        raise CrowdTangleMissingTokenError

    if format not in CROWDTANGLE_OUTPUT_FORMATS:
        raise TypeError('minet.crowdtangle.summary: unkown `format`.')

    if not isinstance(start_date, str):
        raise TypeError('minet.crowdtangle.summary: expecting a `start_date` kwarg.')

    if sort_by not in CROWDTANGLE_SUMMARY_SORT_TYPES:
        raise TypeError('minet.crowdtangle.summary: unknown `sort_by`.')

    http = create_pool(timeout=CROWDTANGLE_DEFAULT_TIMEOUT)
    rate_limiter = RateLimiter(rate_limit, 60.0)

    for item in iterator:
        link = item

        if callable(key):
            link = key(item)

        with rate_limiter:

            # Fetching
            api_url = forge_url(
                link,
                token,
                start_date,
                sort_by,
                with_top_posts
            )

            err, response, data = request_json(http, api_url)

            if err is not None:
                raise err

            if response.status == 401:
                raise CrowdTangleInvalidTokenError

            if response.status >= 400:
                raise CrowdTangleInvalidRequest(api_url)

            stats = nested_get(['result', 'summary', 'facebook'], data)
            posts = nested_get(['result', 'posts'], data) if with_top_posts else None

            if stats is not None:
                if format == 'csv_dict_row':
                    stats = format_summary(stats, as_dict=True)
                elif format == 'csv_row':
                    stats = format_summary(stats)

            if not with_top_posts:
                yield CrowdTangleSummaryResult(link, item, stats)

            else:
                if posts is not None:
                    if format == 'csv_dict_row':
                        posts = [format_post(post, as_dict=True) for post in posts]
                    elif format == 'csv_row':
                        posts = [format_post(post) for post in posts]

                yield CrowdTangleSummaryResultWithPosts(link, item, stats, posts)