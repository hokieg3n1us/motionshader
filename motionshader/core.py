import io
from datetime import datetime, timedelta

import colorcet
import dask.dataframe
import datashader
import imageio
import numpy
from PIL.ImageFont import FreeTypeFont
from PIL import Image, ImageDraw, ImageFont
from requests import Session


class GeospatialViewport:
    min_longitude: float = None
    max_longitude: float = None
    min_latitude: float = None
    max_latitude: float = None
    center_longitude: float = None
    center_latitude: float = None
    width_pixels: int = None
    height_pixels: int = None

    def __init__(self, min_longitude=-180.0, max_longitude=180.0, min_latitude=-90.0, max_latitude=90,
                 width_pixels=1920,
                 height_pixels=1080) -> None:
        self.min_longitude = min_longitude
        self.max_longitude = max_longitude
        self.min_latitude = min_latitude
        self.max_latitude = max_latitude
        self.width_pixels = width_pixels
        self.height_pixels = height_pixels
        self.center_longitude = self.min_longitude + ((self.max_longitude - self.min_longitude) / 2.0)
        self.center_latitude = self.min_latitude + ((self.max_latitude - self.min_latitude) / 2.0)


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
                                         WIDTH=viewport.width_pixels, HEIGHT=viewport.height_pixels,
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


class FrameAnnotation:
    pos_x = 0
    pos_y = 0
    font = None
    font_color = None
    lon_lat = None
    date_format = None

    def __init__(self, pos_x: int, pos_y: int, font: FreeTypeFont = ImageFont.truetype('arial', 10),
                 font_color: str = '#000000', lon_lat: bool = True, date_format: str = '%Y-%m-%dT%H:%M:%S%z') -> None:
        self.pos_x = pos_x
        self.pos_y = pos_y
        self.font = font
        self.font_color = font_color
        self.lon_lat = lon_lat
        self.date_format = date_format

    def annotate(self, img, start_time, end_time, center_longitude, center_latitude):
        image_draw = ImageDraw.Draw(img)

        annotation = "Time Range: {}/{} Center Coordinate: ({:0>3.3f}, {:0>2.3f})".format(
            start_time.strftime(self.date_format), end_time.strftime(self.date_format),
            center_longitude, center_latitude)

        if not self.lon_lat:
            annotation = "Time Range: {}/{} Center Coordinate: ({:0>2.3f}, {:0>3.3f})".format(
                start_time.strftime(self.date_format), end_time.strftime(self.date_format),
                center_latitude, center_longitude)

        image_draw.text((self.pos_x, self.pos_y), annotation, font=self.font, fill=self.font_color)

        return img


class FrameWatermark:
    watermark = ""
    pos_x = 0
    pos_y = 0
    font = None
    font_color = None

    def __init__(self, watermark: str, pos_x: int, pos_y: int, font: FreeTypeFont = ImageFont.truetype('arial', 10),
                 font_color: str = '#000000') -> None:
        self.watermark = watermark
        self.pos_x = pos_x
        self.pos_y = pos_y
        self.font = font
        self.font_color = font_color

    def add_watermark(self, img):
        image_draw = ImageDraw.Draw(img)

        image_draw.text((self.pos_x, self.pos_y), self.watermark, font=self.font, fill=self.font_color)

        return img


class MotionVideo:
    dataset: Dataset = None
    basemap: Basemap = None

    def __init__(self, dataset: Dataset, basemap: Basemap) -> None:
        self.dataset = dataset
        self.basemap = basemap

    def _generate_frame(self, frame_df: dask.dataframe, viewport: GeospatialViewport, scale_points_pixels: int, color_map):
        cvs = datashader.Canvas(plot_width=viewport.width_pixels, plot_height=viewport.height_pixels,
                                x_range=(viewport.min_longitude, viewport.max_longitude),
                                y_range=(viewport.min_latitude, viewport.max_latitude))
        agg = cvs.points(frame_df, self.dataset.longitude_column, self.dataset.latitude_column)

        img = datashader.tf.shade(agg, cmap=color_map, how='eq_hist')

        if scale_points_pixels != 0:
            img = datashader.tf.spread(img, px=scale_points_pixels, shape="circle")

        return img.to_pil().convert("RGBA")

    def to_gif(self, viewport: GeospatialViewport, playback: TemporalPlayback, file_base_name: str,
               annotation: FrameAnnotation = None,
               watermark: FrameWatermark = None, scale_points_pixels: int = 0, color_map=colorcet.fire):
        imgs = []

        tiles = self.basemap.get_tiles(viewport)

        start = playback.start_time
        end = playback.end_time

        while start < end:
            frame_df = self.dataset.subset(start, start + playback.frame_length)
            frame = self._generate_frame(frame_df, viewport, scale_points_pixels, color_map)
            img = Image.alpha_composite(tiles, frame)

            if annotation is not None:
                img = annotation.annotate(img, start, (start + playback.frame_length), viewport.center_longitude,
                                          viewport.center_latitude)
            if watermark is not None:
                img = watermark.add_watermark(img)

            imgs.append(img)

            start = start + playback.frame_step

        imageio.mimsave(file_base_name + '.gif', imgs, fps=playback.frames_per_second)

    def to_video(self, viewport: GeospatialViewport, playback: TemporalPlayback, file_base_name: str,
                 annotation: FrameAnnotation = None,
                 watermark: FrameWatermark = None, scale_points_pixels: int = 0, color_map=colorcet.fire):

        tiles = self.basemap.get_tiles(viewport)

        start = playback.start_time
        end = playback.end_time

        mp4_writer = imageio.get_writer(file_base_name + '.mp4', fps=playback.frames_per_second)

        while start < end:
            frame_df = self.dataset.subset(start, start + playback.frame_length)
            frame = self._generate_frame(frame_df, viewport, scale_points_pixels, color_map)
            img = Image.alpha_composite(tiles, frame)

            if annotation is not None:
                img = annotation.annotate(img, start, (start + playback.frame_length), viewport.center_longitude,
                                          viewport.center_latitude)
            if watermark is not None:
                img = watermark.add_watermark(img)

            mp4_writer.append_data(numpy.array(img))
            start = start + playback.frame_step

        mp4_writer.close()
