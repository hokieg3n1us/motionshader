import io
from datetime import datetime, timedelta

import colorcet
import dask.dataframe
import datashader
import imageio
import numpy
from PIL import Image
from requests import Session


class GeospatialViewport:
    min_longitude: float = None
    max_longitude: float = None
    min_latitude: float = None
    max_latitude: float = None
    widthPixels: int = None
    heightPixels: int = None

    def __init__(self, min_longitude=-180.0, max_longitude=180.0, min_latitude=-90.0, max_latitude=90, widthPixels=1920,
                 heightPixels=1080) -> None:
        self.min_longitude = min_longitude
        self.max_longitude = max_longitude
        self.min_latitude = min_latitude
        self.max_latitude = max_latitude
        self.widthPixels = widthPixels
        self.heightPixels = heightPixels


class TemporalPlayback:
    start_time: datetime = None
    end_time: datetime = None
    frame_length: timedelta = None
    frame_step: timedelta = None
    frames_per_second: int = None

    def __init__(self, start_time: datetime, end_time: datetime, frame_length: timedelta, frame_step: timedelta,
                 frames_per_second: int):
        self.start_time = start_time
        self.end_time = end_time
        self.frame_length = frame_length
        self.frame_step = frame_step
        self.frames_per_second = frames_per_second


class Basemap:
    basemap_session: Session = None
    basemap_url: str = None
    basemap_layer: str = None

    def __init__(self, basemap_session: Session, basemap_url: str, basemap_layer: str) -> None:
        self.basemap_session = basemap_session
        self.basemap_url = basemap_url
        self.basemap_layer = basemap_layer

    def get_tiles(self, viewport: GeospatialViewport) -> Image:
        request_url = self.basemap_url + '?bbox={YMIN},{XMIN},{YMAX},{XMAX}&width={WIDTH}&height={HEIGHT}&layers={LAYER}&format=image/png&service=WMS&version=1.3.0&crs=EPSG:4326&request=GetMap&styles='
        request_url = request_url.format(XMIN=viewport.min_longitude, XMAX=viewport.max_longitude,
                                         YMIN=viewport.min_latitude, YMAX=viewport.max_latitude,
                                         WIDTH=viewport.widthPixels, HEIGHT=viewport.heightPixels,
                                         LAYER=self.basemap_layer)
        response = self.basemap_session.get(request_url)
        return Image.open(io.BytesIO(response.content)).convert("RGBA")


class Dataset:
    df = None
    longitude_column = None
    latitude_column = None

    def __init__(self, df: dask.dataframe, longitude_column: str, latitude_column: str) -> None:
        self.df = df
        self.longitude_column = longitude_column
        self.latitude_column = latitude_column

    def subset(self, start_time: datetime, end_time: datetime) -> dask.dataframe:
        return self.df[start_time: end_time]


class MotionVideo:
    dataset: Dataset = None
    basemap: Basemap = None

    def __init__(self, dataset: Dataset, basemap: Basemap) -> None:
        self.dataset = dataset
        self.basemap = basemap

    def _generate_frame(self, frame_df: dask.dataframe, viewport: GeospatialViewport, color_map):
        cvs = datashader.Canvas(plot_width=viewport.widthPixels, plot_height=viewport.heightPixels,
                                x_range=(viewport.min_longitude, viewport.max_longitude),
                                y_range=(viewport.min_latitude, viewport.max_latitude))
        agg = cvs.points(frame_df, self.dataset.longitude_column, self.dataset.latitude_column)
        return datashader.tf.shade(agg, cmap=color_map, how='eq_hist').to_pil().convert("RGBA")

    def to_gif(self, viewport: GeospatialViewport, playback: TemporalPlayback, file_base_name: str,
               color_map=colorcet.fire):
        imgs = []

        tiles = self.basemap.get_tiles(viewport)

        start = playback.start_time
        end = playback.end_time

        while start < end:
            frame_df = self.dataset.subset(start, start + playback.frame_length)
            frame = self._generate_frame(frame_df, viewport, color_map)
            img = Image.alpha_composite(tiles, frame)
            imgs.append(img)
            start = start + playback.frame_step

        imageio.mimsave(file_base_name + '.gif', imgs, fps=playback.frames_per_second)

    def to_video(self, viewport: GeospatialViewport, playback: TemporalPlayback, file_base_name: str,
                 color_map=colorcet.fire):

        tiles = self.basemap.get_tiles(viewport)

        start = playback.start_time
        end = playback.end_time

        mp4_writer = imageio.get_writer(file_base_name + '.mp4', fps=playback.frames_per_second)

        while start < end:
            frame_df = self.dataset.subset(start, start + playback.frame_length)
            frame = self._generate_frame(frame_df, viewport, color_map)
            mp4_writer.append_data(numpy.array(Image.alpha_composite(tiles, frame)))
            start = start + playback.frame_step

        mp4_writer.close()
