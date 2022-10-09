"""
:Created: 24 July 2016
:Author: Lucas Connors

"""

import boto3
import os
import numpy as np
import pandas as pd
import seaborn as sns
import plotly.express as px 
import matplotlib.pyplot as plt
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from sklearn.metrics import euclidean_distances
from scipy.spatial.distance import cdist
import difflib
from collections import defaultdict
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.manifold import TSNE
from sklearn.decomposition import PCA
from sklearn.metrics import euclidean_distances
from scipy.spatial.distance import cdist
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.manifold import TSNE
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone
from gfklookupwidget.fields import GfkLookupField
from markdown_deux.templatetags.markdown_deux_tags import markdown_allowed
from pigeon.url.utils import add_params_to_url

from campaign.models import Project


class Album(models.Model):

    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    name = models.CharField(max_length=60)
    slug = models.SlugField(
        max_length=40,
        db_index=True,
        help_text="A short label for an album (used in URLs)",
    )
    release_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.name

    def validate_unique(self, exclude=None):
        if (
            self.project_id
            and Album.objects.exclude(id=self.id)
            .filter(project__artist=self.project.artist, slug=self.slug)
            .exists()
        ):
            raise ValidationError("Slug must be unique per artist")

    def save(self, *args, **kwargs):
        self.validate_unique()
        super().save(*args, **kwargs)

    def url(self):
        return reverse(
            "album",
            kwargs={"artist_slug": self.project.artist.slug, "album_slug": self.slug},
        )

    def discs(self):
        disc_numbers = (
            self.track_set.all()
            .values_list("disc_number", flat=True)
            .distinct()
            .order_by("disc_number")
        )
        return (
            self.track_set.filter(disc_number=disc).order_by("track_number")
            for disc in disc_numbers
        )

    def total_activity(self, activity_type):
        tracks = self.track_set.all()
        if not tracks:
            return 0

        all_activities = ActivityEstimate.objects.filter(activity_type=activity_type)
        album_events = (
            all_activities.filter(
                content_type=ContentType.objects.get_for_model(self), object_id=self.id
            ).aggregate(total=models.Sum("total"))["total"]
            or 0
        )
        track_events = (
            all_activities.filter(
                content_type=ContentType.objects.get_for_model(tracks[0]),
                object_id__in=tracks.values_list("id", flat=True),
            ).aggregate(total=models.Sum("total"))["total"]
            or 0
        )

        return album_events * tracks.count() + track_events

    def total_downloads(self):
        return self.total_activity(ActivityEstimate.ACTIVITY_DOWNLOAD)

    def total_streams(self):
        return self.total_activity(ActivityEstimate.ACTIVITY_STREAM)


class Track(models.Model):

    album = models.ForeignKey(Album, on_delete=models.CASCADE)
    disc_number = models.PositiveSmallIntegerField(default=1)
    track_number = models.PositiveSmallIntegerField()
    name = models.CharField(max_length=60)
    duration = models.DurationField(null=True, blank=True)

    class Meta:
        unique_together = (("album", "disc_number", "track_number"),)

    def __str__(self):
        return "{album} #{track_number}: {name}".format(
            album=str(self.album), track_number=self.track_number, name=self.name
        )

    def total_activity(self, activity_type):
        return (
            ActivityEstimate.objects.filter(
                models.Q(
                    content_type=ContentType.objects.get_for_model(self.album),
                    object_id=self.album.id,
                )
                | models.Q(
                    content_type=ContentType.objects.get_for_model(self),
                    object_id=self.id,
                ),
                activity_type=activity_type,
            ).aggregate(total=models.Sum("total"))["total"]
            or 0
        )

    def total_downloads(self):
        return self.total_activity(ActivityEstimate.ACTIVITY_DOWNLOAD)

    def total_streams(self):
        return self.total_activity(ActivityEstimate.ACTIVITY_STREAM)


class Artwork(models.Model):

    album = models.OneToOneField(Album, on_delete=models.CASCADE)
    img = models.ImageField(upload_to="artist/album")

    class Meta:
        verbose_name_plural = "Artwork"

    def __str__(self):
        return str(self.album)


class AlbumBio(models.Model):

    album = models.OneToOneField(Album, on_delete=models.CASCADE)
    bio = models.TextField(
        help_text="Tracklisting and other info about the album. " + markdown_allowed()
    )

    def __str__(self):
        return str(self.album)


class MarketplaceURL(models.Model):

    MARKETPLACE_ITUNES = "itunes"
    MARKETPLACE_APPLE_MUSIC = "apple"
    MARKETPLACE_CHOICES = (
        ("spotify", "Spotify"),
        (MARKETPLACE_ITUNES, "iTunes"),
        (MARKETPLACE_APPLE_MUSIC, "Apple Music"),
        ("google", "Google Play"),
        ("amazon", "Amazon"),
        ("tidal", "Tidal"),
        ("youtube", "YouTube"),
    )

    album = models.ForeignKey(Album, on_delete=models.CASCADE)
    medium = models.CharField(
        choices=MARKETPLACE_CHOICES, max_length=10, help_text="The type of marketplace"
    )
    url = models.URLField(unique=True, help_text="The URL to the album's page")

    class Meta:
        unique_together = (("album", "medium"),)

    def __str__(self):
        return "{album}: {medium}".format(
            album=str(self.album), medium=self.get_medium_display()
        )

    def marketplace_has_affiliate_token(self):
        return self.medium in (self.MARKETPLACE_ITUNES, self.MARKETPLACE_APPLE_MUSIC)

    def affiliate_url(self):
        if self.marketplace_has_affiliate_token() and hasattr(
            settings, "ITUNES_AFFILIATE_TOKEN"
        ):
            return add_params_to_url(self.url, {"at": settings.ITUNES_AFFILIATE_TOKEN})
        return self.url


class S3PrivateFileField(models.FileField):
    def __init__(
        self, verbose_name=None, name=None, upload_to="", storage=None, **kwargs
    ):
        super().__init__(
            verbose_name=verbose_name,
            name=name,
            upload_to=upload_to,
            storage=storage,
            **kwargs,
        )
        self.storage.default_acl = "private"


class Audio(models.Model):

    album = models.OneToOneField(Album, on_delete=models.CASCADE)
    file = S3PrivateFileField(upload_to="artist/audio")

    class Meta:
        verbose_name_plural = "Audio"

    def __str__(self):
        return str(self.album)

    def get_temporary_url(self, ttl=60):
        if hasattr(settings, "AWS_S3_BUCKET_NAME"):
            s3 = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            )
            key = "{media}/{filename}".format(
                media=settings.AWS_S3_KEY_PREFIX, filename=self.file.name
            )
            return s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": settings.AWS_S3_BUCKET_NAME, "Key": key},
                ExpiresIn=ttl,
            )
        return self.file.url


def activity_content_type_choices():
    return {
        "id__in": (
            ContentType.objects.get_for_model(Album).id,
            ContentType.objects.get_for_model(Track).id,
        )
    }


class ActivityEstimate(models.Model):

    ACTIVITY_STREAM = "stream"
    ACTIVITY_DOWNLOAD = "download"
    ACTIVITY_CHOICES = ((ACTIVITY_STREAM, "Stream"), (ACTIVITY_DOWNLOAD, "Download"))

    date = models.DateField(default=timezone.now)
    activity_type = models.CharField(choices=ACTIVITY_CHOICES, max_length=8)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
        limit_choices_to=activity_content_type_choices,
    )
    object_id = GfkLookupField("content_type")
    content_object = GenericForeignKey()
    total = models.PositiveIntegerField()

    class Meta:
        unique_together = (("date", "activity_type", "content_type", "object_id"),)

    def __str__(self):
        return str(self.content_object)

class RecommenderSystem(models.Model):

    data = pd.read_csv("C://Users//soham//Downloads//data.csv")
    genre_data = pd.read_csv('C://Users//soham//Downloads//data_by_genres.csv')
    year_data = pd.read_csv('C://Users//soham//Downloads//data_by_year.csv')
    cluster_pipeline = Pipeline([('scaler', StandardScaler()), ('kmeans', KMeans(n_clusters=10))])
    X = genre_data.select_dtypes(np.number)
    cluster_pipeline.fit(X)
    genre_data['cluster'] = cluster_pipeline.predict(X)
    tsne_pipeline = Pipeline([('scaler', StandardScaler()), ('tsne', TSNE(n_components=2, verbose=1))])
    genre_embedding = tsne_pipeline.fit_transform(X)
    projection = pd.DataFrame(columns=['x', 'y'], data=genre_embedding)
    projection['genres'] = genre_data['genres']
    projection['cluster'] = genre_data['cluster']
    song_cluster_pipeline = Pipeline([('scaler', StandardScaler()), ('kmeans', KMeans(n_clusters=20, verbose=False))], verbose=False)
    X = data.select_dtypes(np.number)
    number_cols = list(X.columns)
    song_cluster_pipeline.fit(X)
    song_cluster_labels = song_cluster_pipeline.predict(X)
    data['cluster_label'] = song_cluster_labels
    pca_pipeline = Pipeline([('scaler', StandardScaler()), ('PCA', PCA(n_components=2))])
    song_embedding = pca_pipeline.fit_transform(X)
    projection = pd.DataFrame(columns=['x', 'y'], data=song_embedding)
    projection['title'] = data['name']
    projection['cluster'] = data['cluster_label']
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id="fa3017cd775f4a87b73c890bf6fa1ede", client_secret="6b316306bfd5498c8ed76866eb49e9d3"))
    def find_song(name, year):
        song_data = defaultdict()
        results = sp.search(q= 'track: {} year: {}'.format(name,year), limit=1)
        if results['tracks']['items'] == []:
            return None

        results = results['tracks']['items'][0]
        track_id = results['id']
        audio_features = sp.audio_features(track_id)[0]

        song_data['name'] = [name]
        song_data['year'] = [year]
        song_data['explicit'] = [int(results['explicit'])]
        song_data['duration_ms'] = [results['duration_ms']]
        song_data['popularity'] = [results['popularity']] 
        
        for key, value in audio_features.items():
            song_data[key] = value

        return pd.DataFrame(song_data)
    number_cols = ['valence', 'year', 'acousticness', 'danceability', 'duration_ms', 'energy', 'explicit',
    'instrumentalness', 'key', 'liveness', 'loudness', 'mode', 'popularity', 'speechiness', 'tempo']


    def get_song_data(song, spotify_data):
    
        try:
            song_data = spotify_data[(spotify_data['name'] == song['name']) 
                                & (spotify_data['year'] == song['year'])].iloc[0]
            return song_data
    
        except IndexError:
            return find_song(song['name'], song['year'])
        

    def get_mean_vector(song_list, spotify_data):
        
        song_vectors = []
        
        for song in song_list:
            song_data = get_song_data(song, spotify_data)
            if song_data is None:
                print('Warning: {} does not exist in Spotify or in database'.format(song['name']))
                continue
            song_vector = song_data[number_cols].values
            song_vectors.append(song_vector)  
        
        song_matrix = np.array(list(song_vectors))
        return np.mean(song_matrix, axis=0)


    def flatten_dict_list(dict_list):
        
        flattened_dict = defaultdict()
        for key in dict_list[0].keys():
            flattened_dict[key] = []
        
        for dictionary in dict_list:
            for key, value in dictionary.items():
                flattened_dict[key].append(value)
                
        return flattened_dict


    def recommend_songs( song_list, spotify_data, n_songs=10):
        
        metadata_cols = ['name', 'year', 'artists']
        song_dict = flatten_dict_list(song_list)
        
        song_center = get_mean_vector(song_list, spotify_data)
        scaler = song_cluster_pipeline.steps[0][1]
        scaled_data = scaler.transform(spotify_data[number_cols])
        scaled_song_center = scaler.transform(song_center.reshape(1, -1))
        distances = cdist(scaled_song_center, scaled_data, 'cosine')
        index = list(np.argsort(distances)[:, :n_songs][0])
        
        rec_songs = spotify_data.iloc[index]
        rec_songs = rec_songs[~rec_songs['name'].isin(song_dict['name'])]
        return rec_songs[metadata_cols].to_dict(orient='records')

    recommend_songs([{'name': 'Come As You Are', 'year':1991},
                {'name': 'Smells Like Teen Spirit', 'year': 1991},
                {'name': 'Lithium', 'year': 1992},
                {'name': 'All Apologies', 'year': 1993},
                {'name': 'Stay Away', 'year': 1993}],  data)
        




