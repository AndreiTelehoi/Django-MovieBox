from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from .models import Movie, Rating
from django.db.models import Q
from .forms import RatingForm
import csv
from django.http import Http404
from django.db.models import Case, When
import numpy as np
import pandas as pd
import json
import random
# Create your views here.


def add_users(request):
    file = 'main/users_final.csv'
    data = csv.reader(open(file), delimiter=",")
    for row in data:
        user_name = row[0]
        user = User.objects.create_user(user_name, password="qwerty123")
        user.save()
    return render(request, 'main/import_users.html')


def add_ratings(request):
    file = 'main/final_ratings.csv'
    data = csv.reader(open(file), delimiter=",")
    for row in data:
        user_id = row[0]
        movie_title = row[3]
        rating_value = row[2]
        ratingObject = Rating()
        ratingObject.movie = get_object_or_404(Movie, title=movie_title)
        ratingObject.user = get_object_or_404(User, pk=user_id)
        ratingObject.rating = int(float(rating_value))
        ratingObject.save()
    return render(request, 'main/import_ratings.html')


def home(request):
    user = request.user
    if not user:
        return render(request, 'main/home.html')
    else:
        return render(request, 'main/home.html', {'user': user})


def signup_user(request):
    if request.method == 'GET':
        return render(request, 'main/signup_user.html', {'form': UserCreationForm()})
    else:
        if request.POST['password1'] == request.POST['password2']:
            try:
                user = User.objects.create_user(
                    request.POST['username'], password=request.POST['password1']
                )
                user.save()
                login(request, user)
                return redirect('home')
            except IntegrityError:
                return render(request, 'main/signup_user.html', {'form': UserCreationForm(), 'error': 'username is already taken'})
        else:
            return render(request, 'main/signup_user.html', {'form': UserCreationForm(), 'error': 'passwords did not match'})


@login_required
def logout_user(request):
    if request.method == 'POST':
        logout(request)
        return redirect('home')


def login_user(request):
    if request.method == 'GET':
        return render(request, 'main/login_user.html', {'form': AuthenticationForm()})
    else:
        user = authenticate(
            request, username=request.POST['username'], password=request.POST['password']
        )
        if user is None:
            return render(request, 'main/login_user.html', {'form': AuthenticationForm(), 'error': 'username or password invalid'})
        else:
            login(request, user)
            return redirect('home')


@login_required
def browse(request):
    movies = Movie.objects.all()
    random_movies = Movie.objects.order_by('?')
    query = request.GET.get('q')
    if query:
        movies = Movie.objects.filter(Q(title__icontains=query)).distinct()
        return render(request, 'main/browse.html', {'movies': movies})
    return render(request, 'main/browse.html', {'random_movies': random_movies[:8]})


@login_required
def movie_details(request, movie_pk):
    movie = get_object_or_404(Movie, pk=movie_pk)
    ratings = Rating.objects.filter(user=request.user)
    if request.method == "POST":
        for rating in ratings:
            if movie == rating.movie:
                return render(request, 'main/movie_details.html', {'movie': movie, 'error': 'this movie is already in your collection or wishlist'})
        rate = request.POST['rating']
        ratingObject = Rating()
        ratingObject.user = request.user
        ratingObject.movie = movie
        ratingObject.rating = rate
        ratingObject.save()
        return redirect('movie_details', movie_pk=movie.id)
    return render(request, 'main/movie_details.html', {'movie': movie})


def rating_details(request, rating_pk):
    ratingObject = get_object_or_404(Rating, pk=rating_pk)
    movie = ratingObject.movie
    if request.method == 'POST':
        ratingObject.rating = request.POST['rating']
        ratingObject.save()
    return render(request, 'main/rating_details.html', {'rating': ratingObject})


@login_required
def collection(request):
    if request.GET.get('genre'):
        genre = request.GET.get('genre')
        if (genre == "all"):
            ratings = Rating.objects.filter(user=request.user)
        else:
            movies = Movie.objects.filter(
                Q(genres__icontains=genre)).distinct()
            unfiltered_ratings = Rating.objects.filter(user=request.user)
            ratings = []
            for rating in unfiltered_ratings:
                for movie in movies:
                    if rating.movie.title == movie.title:
                        ratings.append(rating)
            if not ratings:
                return render(request, 'main/collection.html', {'genre': genre})
    else:
        ratings = Rating.objects.filter(user=request.user)
        ratings = ratings.exclude(rating=0)
    return render(request, 'main/collection.html', {'ratings': ratings})


@login_required
def delete_rating(request, rating_pk):
    rating = get_object_or_404(Rating, pk=rating_pk, user=request.user)
    print(rating)
    if request.method == 'POST':
        if rating.rating == 0:
            rating.delete()
            return redirect('wishlist')
        else:
            rating.delete()
            return redirect('collection')


@login_required
def recommendations(request):
    ratings_check = Rating.objects.filter(user=request.user)
    ratings_check = ratings_check.exclude(rating=0)
    print(ratings_check.count())
    if ratings_check.count() >= 4:
        is_empty = False
        if request.method == 'POST':

            # TODO: read dataset
            ratings = pd.read_csv('main/dataset/ratings.csv')
            movies = pd.read_csv('main/dataset/movies_metadata.csv')
            ratings = pd.merge(movies, ratings).drop(
                ['genres', 'timestamp'], axis=1)
            ratings.head()

            # TODO: normalize dataset
            userRatings = ratings.pivot_table(index=['userId'], columns=[
                'title'], values='rating')
            userRatings.head()
            userRatings = userRatings.dropna(
                thresh=10, axis=1).fillna(0, axis=1)

            # TODO: generate correlation matrix using pearson correlation
            corrMatrix = userRatings.corr(method='pearson')
            corrMatrix.head(100)

            # TODO: calculate similar ratings
            def get_similar(movie_name, rating):
                similar_ratings = corrMatrix[movie_name] * (rating - 2.5)
                similar_ratings = similar_ratings.sort_values(ascending=False)
                return similar_ratings

            # TODO: get list of movies from current user's collection
            ratings = Rating.objects.filter(user=request.user)

            user_movies = []
            for rating in ratings:
                movie_title = rating.movie.title
                movie_rating = rating.rating
                user_movies.append([movie_title, movie_rating])

            # TODO: generate recommendations
            similar_movies = pd.DataFrame()
            for movie, rating in user_movies:
                try:
                    similar_movies = similar_movies.append(
                        get_similar(movie, rating), ignore_index=True)
                except KeyError:
                    pass

            # TODO: create list from dataframe
            recommendations_df = similar_movies.sum().sort_values(ascending=False)
            recommendations_dict = recommendations_df.to_dict()
            recommendations_list = []

            for key in recommendations_dict.keys():
                recommendations_list.append(key)

            # TODO: remove duplicates
            for movie, rating in user_movies:
                if movie in recommendations_list:
                    recommendations_list.remove(movie)

            recommendations_list = recommendations_list[:20]

            # TODO: generate movie objects list
            movies = []
            for recommendation in recommendations_list:
                movie = get_object_or_404(Movie, title=recommendation)
                movies.append(movie)

            return render(request, 'main/recommendations.html',
                          {'movies': movies, 'is_empty': is_empty})
        else:
            return render(request, 'main/recommendations.html')
    else:
        is_empty = True
        return render(request, 'main/recommendations.html', {'is_empty': is_empty})


@login_required
def wishlist(request):
    ratings = Rating.objects.filter(user=request.user)
    ratings = ratings.filter(rating=0)
    return render(request, 'main/wishlist.html', {'ratings': ratings})


@login_required
def add_wish(request, movie_pk):
    movie = get_object_or_404(Movie, pk=movie_pk)
    ratings = Rating.objects.filter(user=request.user)
    if request.method == "POST":
        for rating in ratings:
            if movie == rating.movie:
                return render(request, 'main/movie_details.html',
                              {'movie': movie,
                               'error': 'this movie is already in your collection or wishlist'
                               })
        ratingObject = Rating()
        ratingObject.user = request.user
        ratingObject.movie = movie
        ratingObject.rating = 0
        ratingObject.save()
        return redirect("wishlist")


def wish_details(request, rating_pk):
    ratingObject = get_object_or_404(Rating, pk=rating_pk)
    movie = ratingObject.movie
    if request.method == 'POST':
        ratingObject.rating = request.POST['rating']
        ratingObject.save()
        return redirect("collection")
    return render(request, 'main/wish_details.html', {'rating': ratingObject})
