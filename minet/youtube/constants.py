# =============================================================================
# Minet YouTube Constants
# =============================================================================
#
# General constants used throughout the YouTube functions.
#

YOUTUBE_API_BASE_URL = 'https://www.googleapis.com/youtube/v3'
YOUTUBE_API_MAX_VIDEOS_PER_CALL = 50

YOUTUBE_VIDEO_CSV_HEADERS = [
    'video_id',
    'published_at',
    'channel_id',
    'title',
    'description',
    'channel_title',
    'view_count',
    'like_count',
    'dislike_count',
    'favorite_count',
    'comment_count',
    'no_stat_likes',
    'duration',
    'caption'
]