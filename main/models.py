from django.db import models
from django.contrib.auth.models import Permission, User
from django.core.validators import MaxValueValidator, MinValueValidator

# Create your models here.


class Movie(models.Model):
    title = models.CharField(max_length=200)
    genres = models.CharField(max_length=200, blank=True, null=True)
    poster = models.CharField(max_length=500, blank=True, null=True)

    def __str__(self):
        return self.title


class Rating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    rating = models.IntegerField(default=1, validators=[
                                 MaxValueValidator(5), MinValueValidator(0)])
