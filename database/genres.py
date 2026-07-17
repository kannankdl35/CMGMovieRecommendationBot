"""
TMDb Genre IDs
https://developer.themoviedb.org/docs/genres
"""

# -------------------------------
# MOVIES
# -------------------------------

MOVIE_GENRES = {
    "action": 28,
    "adventure": 12,
    "animation": 16,
    "comedy": 35,
    "crime": 80,
    "documentary": 99,
    "drama": 18,
    "family": 10751,
    "fantasy": 14,
    "history": 36,
    "horror": 27,
    "music": 10402,
    "mystery": 9648,
    "romance": 10749,
    "scifi": 878,
    "tvmovie": 10770,
    "thriller": 53,
    "war": 10752,
    "western": 37,
}


# -------------------------------
# TV SERIES
# -------------------------------

TV_GENRES = {
    "action": 10759,      # Action & Adventure
    "adventure": 10759,
    "animation": 16,
    "comedy": 35,
    "crime": 80,
    "documentary": 99,
    "drama": 18,
    "family": 10751,
    "fantasy": 10765,     # Sci-Fi & Fantasy
    "history": 10768,     # War & Politics (closest TMDb category)
    "horror": 9648,       # Closest available
    "music": 10767,       # Talk
    "mystery": 9648,
    "romance": 10766,     # Soap
    "scifi": 10765,
    "tvmovie": 10767,
    "thriller": 9648,
    "war": 10768,
    "western": 37,
}
