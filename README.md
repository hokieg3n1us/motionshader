# motionshader
Generate a gif or mp4 from geospatial vector data.

![Demonstrationg using simulated dataset in Syra](https://github.com/hokieg3n1us/motionshader/raw/main/Syria.gif)

### Example ###
```python
import multiprocessing as mp
from datetime import datetime, timedelta

import dask.dataframe
import requests

from PIL import ImageFont

import colorcet
import motionshader

if __name__ == '__main__':
    # Motionshader expects a time indexed, sorted, Dask DataFrame with columns containing EPSG:4326 coordinates.
    # Motionshader is opinionated about using Dask DataFrames, for scaling this process to big data.
    df = dask.dataframe.read_csv('Syria-Simulated.csv', usecols=['timestamp', 'longitude', 'latitude'])
    df['timestamp'] = dask.dataframe.to_datetime(df['timestamp'])
    df = df.set_index('timestamp', npartitions=mp.cpu_count(), compute=True).persist()

    # Define a Basemap using a WMS Service and associated layer. Assumes EPSG:4326.
    # Provide a requests.Session() that can be customized for authentication or 2-way SSL verification.
    basemap = motionshader.Basemap(requests.Session(),
                                   'https://ows.terrestris.de/osm/service',
                                   'OSM-WMS')

    # Define the Dataset, providing a Dask DataFrame and the names of the longitude and latitude columns.
    dataset = motionshader.Dataset(df, 'longitude', 'latitude')

    # Define the MotionVideo, providing the dataset to be rendered and the basemap service.
    motion_video = motionshader.MotionVideo(dataset, basemap)

    start_datetime, end_datetime = df.index.min().compute(), df.index.max().compute()
    min_longitude, max_longitude = df.longitude.min().compute(), df.longitude.max().compute()
    min_latitude, max_latitude = df.latitude.min().compute(), df.latitude.max().compute()

    # GeospatialViewport allows defining where the 'camera' looks on the globe, and the resolution of the output.
    # TemporalPlayback defines the temporal bounds, temporal size of a frame, and the frames per second for the output.
    # In this example, a single frame contains 30 minutes of data, and steps forward 15 minutes between frames.
    viewport = motionshader.GeospatialViewport(min_longitude, max_longitude, min_latitude, max_latitude, 1920, 1080)
    playback = motionshader.TemporalPlayback(start_datetime, end_datetime, timedelta(seconds=15),
                                             timedelta(seconds=5), 5)

    # If a FrameAnnotation is provided to the rendering function, the time range and center coordinate will be
    # added onto each frame. The FrameAnnotation allows customizing the position of the label in pixel coordinates,
    # the font, the font color, the coordinate order, and the date format.
    annotation = motionshader.FrameAnnotation(10, 10, ImageFont.truetype('arial', 14),
                                              '#000000', True, '%Y-%m-%dT%H:%M:%S%z')

    # If a Watermark is provided to the rendering function, the watermark text provided will be added
    # onto each frame. The Watermark allows customizing the position of the watermark in pixel coordinates,
    # the font, and the font color.
    watermark = motionshader.FrameWatermark("Rendered using Motionshader", 10, viewport.height_pixels - 40,
                                            ImageFont.truetype('arial', 14),
                                            '#000000')

    # MotionVideo can be output as either a GIF or an MP4.
    motion_video.to_gif(viewport, playback, 'Syria', annotation, watermark, 1, colorcet.fire)
    motion_video.to_video(viewport, playback, 'Syria', annotation, watermark, 1, colorcet.fire)
```
