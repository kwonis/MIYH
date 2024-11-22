from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from datetime import datetime, timedelta
from django.core.cache import cache
from .models import MovieCalendar
from .serializers import MovieCalendarSerializer, MovieRecommendationSerializer
from .utils import get_weather_by_location, check_korean_holiday, get_movie_recommendation, get_time_of_day, get_tmdb_movie
from community.models import Movie
from .utils import get_popular_movies

def fetch_calendar_data(user, year, month):
    """특정 월의 캘린더 데이터만 조회"""
    return MovieCalendar.objects.filter(
        user=user,
        date__year=year,
        date__month=month
    )

def check_current_choice(calendar_entries, today):
    """오늘의 선택 영화 확인"""
    return next((entry for entry in calendar_entries if entry.date == today), None)

def get_weather_data(latitude, longitude):
    """날씨 정보 조회"""
    weather_data = get_weather_by_location(latitude, longitude)
    return weather_data['weather'][0]['main'], weather_data['main']['temp']

def determine_season(month):
    """현재 계절 확인"""
    if month in [3, 4, 5]:
        return '봄'
    elif month in [6, 7, 8]:
        return '여름'
    elif month in [9, 10, 11]:
        return '가을'
    return '겨울'

def get_previous_tmdb_ids(calendar_entries):
    """이전에 선택한 영화 TMDB ID 목록"""
    return {entry.tmdb_id for entry in calendar_entries}

def fetch_recommended_movies(weather, season, time_of_day, previous_tmdb_ids, holiday, username):
    today = datetime.now().date()
    cache_key = f'movie_recommendation_{username}_{today}_{hash(str(previous_tmdb_ids))}'
    cached_movie = cache.get(cache_key)

    if cached_movie:
        return cached_movie

    recommended_tmdb_id, recommendation_type = get_movie_recommendation(
        weather, season, time_of_day, previous_tmdb_ids, holiday
    )

    if recommended_tmdb_id:
        movie_data = get_tmdb_movie(recommended_tmdb_id)
        if movie_data:
            # 전체 영화 목록에 추가
            Movie.objects.update_or_create(
                tmdb_id=movie_data['tmdb_id'],  # TMDB ID를 기준으로 저장
                defaults={
                    'title': movie_data['title'],
                    'poster_path': movie_data.get('poster_path'),
                    'overview': movie_data.get('overview'),
                    'release_date': movie_data.get('release_date'),
                    'popularity': movie_data.get('popularity', 0),
                }
            )
            result = (movie_data, recommendation_type)
            tomorrow = datetime.combine(today + timedelta(days=1), datetime.min.time())
            cache_timeout = int((tomorrow - datetime.now()).total_seconds())
            cache.set(cache_key, result, timeout=cache_timeout)
            return result

    return None, None

def fetch_popular_movie(previous_tmdb_ids, exclude_tmdb_id=None, username=None):
    today = datetime.now().date()
    cache_key = f'popular_movie_{username}_{today}'
    cached_movie = cache.get(cache_key)

    if cached_movie:
        return cached_movie

    popular_movies = get_popular_movies()

    for movie in popular_movies:
        if movie['id'] not in previous_tmdb_ids and movie['id'] != exclude_tmdb_id:
            movie_data = get_tmdb_movie(movie['id'])
            if movie_data:
                # 전체 영화 목록에 추가
                Movie.objects.update_or_create(
                    tmdb_id=movie_data['tmdb_id'],  # TMDB ID를 기준으로 저장
                    defaults={
                        'title': movie_data['title'],
                        'poster_path': movie_data.get('poster_path'),
                        'overview': movie_data.get('overview'),
                        'release_date': movie_data.get('release_date'),
                        'popularity': movie_data.get('popularity', 0),
                    }
                )
                tomorrow = datetime.combine(today + timedelta(days=1), datetime.min.time())
                cache_timeout = int((tomorrow - datetime.now()).total_seconds())
                cache.set(cache_key, movie_data, timeout=cache_timeout)
                return movie_data

    return None

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recommendation_view(request):
    user = request.user
    username = user.username

    latitude = request.GET.get('latitude', 37.5665)  # 서울의 위도 (기본값)
    longitude = request.GET.get('longitude', 126.9780)  # 서울의 경도 (기본값)

    weather, temp = get_weather_data(latitude, longitude)
    season = determine_season(datetime.now().month)
    time_of_day = get_time_of_day()
    holiday = check_korean_holiday(datetime.now().date())

    previous_tmdb_ids = get_previous_tmdb_ids(MovieCalendar.objects.filter(user=user))

    # 첫 번째 추천 (컨텍스트 기반)
    context_movie, recommendation_type = fetch_recommended_movies(
        weather, season, time_of_day, previous_tmdb_ids, holiday, username
    )

    # 두 번째 추천 (인기 영화)
    popular_movie = fetch_popular_movie(
        previous_tmdb_ids,
        context_movie['tmdb_id'] if context_movie else None,
        username
    )

    # 두 결과가 모두 준비될 때까지 대기
    while not context_movie or not popular_movie:
        if not context_movie:
            context_movie, recommendation_type = fetch_recommended_movies(
                weather, season, time_of_day, previous_tmdb_ids, holiday, username
            )
        if not popular_movie:
            popular_movie = fetch_popular_movie(
                previous_tmdb_ids,
                context_movie['tmdb_id'] if context_movie else None,
                username
            )

    recommended_movies = [m for m in [context_movie, popular_movie] if m]
    
    movie_serializer = MovieRecommendationSerializer(recommended_movies, many=True)

    return Response({
        'recommendations': movie_serializer.data
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def calendar_data_view(request, username):
    if request.user.username != username:
        return Response({'error': '자신의 달력만 볼 수 있습니다.'}, 
                        status=status.HTTP_403_FORBIDDEN)
    
    year = request.GET.get('year')
    month = request.GET.get('month')

    if not year or not month:
        return Response({'error': '년도와 월 정보가 필요합니다.'}, 
                        status=status.HTTP_400_BAD_REQUEST)

    today = datetime.now().date()
    calendar_entries = fetch_calendar_data(request.user, year, month)

    # 직렬화된 데이터 생성
    serializer = MovieCalendarSerializer(calendar_entries, many=True)

    return Response({
        'calendar_data': serializer.data
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def select_movie(request, username):
    if request.user.username != username:
        return Response({'error': '자신의 달력에만 영화를 선택할 수 있습니다.'}, 
                       status=status.HTTP_403_FORBIDDEN)

    tmdb_id = request.data.get('tmdb_id')
    if not tmdb_id:
        return Response({'error': '영화를 선택해주세요.'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    today = datetime.now().date()
    
    if MovieCalendar.objects.filter(user=request.user, date=today).exists():
        return Response({'error': '오늘은 이미 영화를 선택하셨습니다.'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    movie_data = get_tmdb_movie(tmdb_id)
    if not movie_data:
        return Response({'error': '유효하지 않은 영화입니다.'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    calendar_entry = MovieCalendar.objects.create(
        user=request.user,
        tmdb_id=movie_data['tmdb_id'],
        title=movie_data['title'],
        poster_path=movie_data['poster_path'],
        date=today
    )
    
    serializer = MovieCalendarSerializer(calendar_entry)
    return Response(serializer.data, status=status.HTTP_201_CREATED)