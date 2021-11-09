import multiprocessing as mp
from datetime import datetime, timedelta

import dask.dataframe
import requests
from PIL import ImageFont

import motionshader

if __name__ == '__main__':
    # Motionshader expects a time indexed, sorted, Dask DataFrame with columns containing EPSG:4326 coordinates.
    # Motionshader is opinionated about using Dask DataFrames, for scaling this process to big data.
    df = dask.dataframe.read_csv('ACLED.csv', usecols=['timestamp', 'longitude', 'latitude', 'event_type'])
    df = df.categorize(columns=['event_type'])
    df['timestamp'] = dask.dataframe.to_datetime(df['timestamp'], unit='s')
    df = df.set_index('timestamp', npartitions=mp.cpu_count(), compute=True).persist()

    # Define a Basemap using a WMS Service and associated layer. Assumes EPSG:4326.
    # Provide a requests.Session() that can be customized for authentication or 2-way SSL verification.
    basemap = motionshader.Basemap(basemap_session=requests.Session(),
                                   basemap_url='https://ows.terrestris.de/osm/service',
                                   basemap_layer='OSM-WMS')

    # Define the Dataset, providing a Dask DataFrame and the names of the longitude and latitude columns.
    dataset = motionshader.Dataset(data=df, longitude_column='longitude', latitude_column='latitude',
                                   cat_column='event_type')

    # Define the MotionVideo, providing the dataset to be rendered and the basemap service.
    motion_video = motionshader.MotionVideo(dataset=dataset, basemap=basemap)

    start_datetime, end_datetime = datetime(2020, 1, 1), datetime(2021, 1, 1)
    min_longitude, max_longitude = df.longitude.min().compute(), df.longitude.max().compute()
    min_latitude, max_latitude = df.latitude.min().compute(), df.latitude.max().compute()

    # GeospatialViewport allows defining where the 'camera' looks on the globe, and the resolution of the output.
    # TemporalPlayback defines the temporal bounds, temporal size of a frame, and the frames per second for the output.
    # In this example, a single frame contains 7 days of data, and steps forward 7 days between frames.
    viewport = motionshader.GeospatialViewport(min_longitude=min_longitude, max_longitude=max_longitude,
                                               min_latitude=min_latitude, max_latitude=max_latitude, width_pixels=1920,
                                               height_pixels=1080)
    playback = motionshader.TemporalPlayback(start_time=start_datetime, end_time=end_datetime,
                                             frame_length=timedelta(days=7),
                                             frame_step=timedelta(days=7), frames_per_second=1)

    # If a FrameAnnotation is provided to the rendering function, the time range and center coordinate will be
    # added onto each frame. The FrameAnnotation allows customizing the position of the label in pixel coordinates,
    # the font, the font color, the coordinate order, and the date format.
    annotation = motionshader.FrameAnnotation(pos_x=10, pos_y=10, font=ImageFont.truetype('arial', 14),
                                              font_color='#000000', lon_lat=True, date_format='%Y-%m-%dT%H:%M:%S%z')

    # If a Watermark is provided to the rendering function, the watermark text provided will be added
    # onto each frame. The Watermark allows customizing the position of the watermark in pixel coordinates,
    # the font, and the font color.
    watermark = motionshader.FrameWatermark(watermark='Rendered using Motionshader', pos_x=10,
                                            pos_y=viewport.height_pixels - 40,
                                            font=ImageFont.truetype('arial', 14),
                                            font_color='#000000')

    color_map = {
        'Protests': '#ff33cc',
        'Riots': '#ffff00',
        'Violence against civilians': '#ff0000',
        'Battles': '#66ff33',
        'Strategic developments': '#9933ff',
        'Explosions/Remote violence': '#0000ff'
    }

    # MotionVideo can be output as either a GIF or an MP4.
    motion_video.to_gif(viewport=viewport, playback=playback, file_name='ACLED_Categorical.gif', annotation=annotation,
                        watermark=watermark, scale_points_pixels=1, color_map=color_map)
    motion_video.to_video(viewport=viewport, playback=playback, file_name='ACLED_Categorical.mp4',
                          annotation=annotation, watermark=watermark, scale_points_pixels=1, color_map=color_map)
