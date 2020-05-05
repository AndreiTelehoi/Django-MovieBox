from import_export.admin import ImportExportModelAdmin
from django.contrib import admin
from .models import Movie, Rating


@admin.register(Movie)
class MovieAdmin(ImportExportModelAdmin):
    pass


@admin.register(Rating)
class RatingAdmin(ImportExportModelAdmin):
    pass
