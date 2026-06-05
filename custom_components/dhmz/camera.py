"""Provide DHMZ radar image"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

import aiohttp
import voluptuous as vol
from io import BytesIO
from PIL import Image, ImageDraw, ImageSequence

from homeassistant.components.camera import PLATFORM_SCHEMA, Camera
from homeassistant.const import CONF_NAME, CONF_LATITUDE, CONF_LONGITUDE

from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from homeassistant.util import dt as dt_util
from homeassistant.util import Throttle

MIN_TIME_BETWEEN_UPDATE = timedelta(minutes=2)

CONF_DELTA = "delta"
CONF_PREVIOUS_TIME = "previous_images_time"
CONF_CURRENT_TIME = "current_image_time"
CONF_SHOW_LOCATION = "mark_location"
CONF_IMAGE_FORMAT = "image_format"

RADAR_MAP_URL_STATIC = "https://vrijeme.hr/kompozit-stat.png"
RADAR_MAP_URL_ANIM = "https://prognoza.hr/karte/radar/anim_kompozit{index}.png"
RADAR_MAP_URL_ANIM_GIF = "https://vrijeme.hr/anim_kompozit.gif"

_LOG = logging.getLogger(__name__)

PLATFORM_SCHEMA = vol.All(
    PLATFORM_SCHEMA.extend(
        {
            vol.Optional(CONF_DELTA, default=300.0): vol.All(
                vol.Coerce(float), vol.Range(min=0)
            ),
            vol.Optional(CONF_NAME, default="DHMZ Radar"): cv.string,
            vol.Optional(CONF_PREVIOUS_TIME, default=125): vol.All(
                vol.Coerce(int), vol.Range(min=0)
            ),
            vol.Optional(CONF_CURRENT_TIME, default=2000): vol.All(
                vol.Coerce(int), vol.Range(min=0)
            ),
            vol.Inclusive(
                CONF_LATITUDE, "coordinates", "Latitude and longitude must exist together"
            ): cv.latitude,
            vol.Inclusive(
                CONF_LONGITUDE, "coordinates", "Latitude and longitude must exist together"
            ): cv.longitude,
            vol.Optional(CONF_SHOW_LOCATION, default=False): cv.boolean,
            vol.Optional(CONF_IMAGE_FORMAT, default="WebP"): cv.string,
        }
    )
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up DHMZ radar-loop camera component."""
    delta = config[CONF_DELTA]
    name = config[CONF_NAME]
    previous_images_time = config[CONF_PREVIOUS_TIME]
    current_image_time = config[CONF_CURRENT_TIME]
    latitude = config.get(CONF_LATITUDE, hass.config.latitude)
    longitude = config.get(CONF_LONGITUDE, hass.config.longitude)
    show_location = config.get(CONF_SHOW_LOCATION)
    image_format = config.get(CONF_IMAGE_FORMAT)

    async_add_entities([DhmzRadar(name, delta, previous_images_time, current_image_time, latitude, longitude, show_location, image_format)])

class DhmzRadar(Camera):
    """
    Rain radar imagery camera based on image URL taken from DHMZ.
    """

    def __init__(self, name: str, delta: float, previous_images_time: int, current_image_time: int, latitude, longitude, show_location, image_format):
        """
        Initialize the component.

        This constructor must be run in the event loop.
        """
        super().__init__()

        self._name = name

        # time a cached image stays valid for
        self._delta = delta

        self._previous_images_time = previous_images_time
        self._current_image_time = current_image_time

        self._longitude = longitude
        self._latitude = latitude
        self._show_location = show_location
        self._image_format = image_format

        # Condition that guards the loading indicator.
        #
        # Ensures that only one reader can cause an http request at the same
        # time, and that all readers are notified after this request completes.
        #
        # invariant: this condition is private to and owned by this instance.
        self._condition = asyncio.Condition()

        self._last_image: Optional[bytes] = None
        self._last_resized_image: Optional[bytes] = None
        # value of the last seen last modified header
        self._last_modified: Optional[str] = None
        # loading status
        self._loading = False
        # deadline for image refresh - self.delta after last successful load
        self._deadline: Optional[datetime] = None
        # Initialize storage for images
        self._images_content = [ None for i in range(25) ]
        self._images = [ {
                "content_length": 0,
                "etag": "",
                "last_modified": None
            } for i in range(25) ]
        self._last_gif_modified = None
        self._last_gif_etag = None

    @property
    def name(self) -> str:
        """Return the component name."""
        return self._name

    @property
    def entity_picture(self):
        """Return a link to the camera feed as entity picture."""
        return RADAR_MAP_URL_STATIC

    @property
    def content_type(self) -> str:
        """Return the content type of the image."""
        if self._last_image:
            if self._last_image.startswith(b"GIF8"):
                return "image/gif"
            if self._last_image.startswith(b"RIFF") and b"WEBP" in self._last_image[:16]:
                return "image/webp"
            if self._last_image.startswith(b"\x89PNG\r\n\x1a\n"):
                return "image/png"
        return "image/jpeg"

    @content_type.setter
    def content_type(self, value) -> None:
        """Set the content type of the image (no-op)."""
        pass

    def __needs_refresh(self) -> bool:
        if not (self._delta and self._deadline and self._last_image):
            return True

        return dt_util.utcnow() > self._deadline

    async def __retrieve_radar_image_old(self, width, height) -> bool:
        """Retrieve old radar image format (GIF) and return whether this succeeded."""
        session = async_get_clientsession(self.hass)

        if self._images[0]["last_modified"]:
            headers = {"If-Modified-Since": self._images[0]["last_modified"] }
        else:
            headers = {}

        _LOG.debug("GET url: %s", RADAR_MAP_URL_ANIM_GIF )
        try:
            res = await session.get( RADAR_MAP_URL_ANIM_GIF , timeout=5, headers=headers)
            res.raise_for_status()
        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            _LOG.error("Failed to fetch get, %s", err)
            return False

        if res.status == 304:
            _LOG.debug("GET - HTTP 304 - success")
            return True

        try:
            current_content = await res.read()
        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            _LOG.error("Failed to read content, %s", err)
            return False

        self._last_image = BytesIO(current_content).getvalue()

        last_modified = res.headers.get("last-modified")
        if last_modified:
            self._images[0]["last_modified"] = last_modified

        _LOG.debug("Got image %s", RADAR_MAP_URL_ANIM_GIF )

        return True

    async def __retrieve_radar_image(self, width, height) -> bool:
        """Retrieve animated GIF and return whether this succeeded."""
        session = async_get_clientsession(self.hass)

        headers = {}
        if self._last_gif_modified:
            headers["If-Modified-Since"] = self._last_gif_modified
        if self._last_gif_etag:
            headers["If-None-Match"] = self._last_gif_etag

        _LOG.debug("GET url: %s", RADAR_MAP_URL_ANIM_GIF)
        try:
            res = await session.get(RADAR_MAP_URL_ANIM_GIF, timeout=10, headers=headers)
            res.raise_for_status()
        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            _LOG.error("Failed to fetch DHMZ radar GIF: %s", err)
            return False

        if res.status == 304:
            _LOG.debug("DHMZ radar GIF - HTTP 304 (not modified)")
            return True

        try:
            current_content = await res.read()
        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            _LOG.error("Failed to read DHMZ radar GIF content: %s", err)
            return False

        # Update cache headers
        self._last_gif_modified = res.headers.get("last-modified")
        self._last_gif_etag = res.headers.get("etag")

        if not self._show_location:
            if self._image_format and self._image_format.upper() == "WEBP":
                # Convert GIF to WebP animation
                try:
                    im = Image.open(BytesIO(current_content))
                    frames = []
                    durations = []
                    for frame in ImageSequence.Iterator(im):
                        frames.append(frame.copy().convert("RGBA"))
                        durations.append(frame.info.get('duration', 100))
                    
                    file_bytes_io = BytesIO()
                    frames[0].save(
                        file_bytes_io,
                        format="WEBP",
                        save_all=True,
                        append_images=frames[1:],
                        optimize=True,
                        duration=durations,
                        loop=0
                    )
                    self._last_image = file_bytes_io.getvalue()
                    _LOG.debug("Converted DHMZ radar GIF to WebP animation")
                    return True
                except Exception as err:
                    _LOG.error("Failed to convert GIF to WebP: %s", err)
                    self._last_image = current_content
                    return True
            else:
                self._last_image = current_content
                return True

        # Process frames to draw location marker
        try:
            im = Image.open(BytesIO(current_content))
            frames = []
            durations = []
            
            for frame in ImageSequence.Iterator(im):
                frame_copied = frame.copy().convert("RGBA")
                draw = ImageDraw.Draw(frame_copied)
                
                x_coord = int((0.11346541830650277 * self._longitude - 1.3351816168381) * float(im.size[0]))
                y_coord = int((-0.15304197356993342 * self._latitude + 7.31403749212996) * float(im.size[1]))
                
                # Draw marker
                draw.ellipse((x_coord-4, y_coord-4, x_coord+4, y_coord+4), fill=(255, 0, 0), outline=(0, 0, 0))
                
                frames.append(frame_copied)
                durations.append(frame.info.get('duration', 100))
                
            file_bytes_io = BytesIO()
            fmt = self._image_format if self._image_format else "GIF"
            frames[0].save(
                file_bytes_io,
                format=fmt,
                save_all=True,
                append_images=frames[1:],
                optimize=True,
                duration=durations,
                loop=0
            )
            self._last_image = file_bytes_io.getvalue()
            _LOG.debug("Processed and saved DHMZ radar animation, format: %s", fmt)
            return True
        except Exception as err:
            _LOG.error("Error drawing location on DHMZ radar GIF: %s", err)
            self._last_image = current_content
            return True

    async def async_camera_image(self, width: int = 0, height: int = 0) -> Optional[bytes]:
        """
        Return a still image response from the camera.

        Uses ayncio conditions to make sure only one task enters the critical
        section at the same time. Otherwise, two http requests would start
        when two tabs with home assistant are open.

        The condition is entered in two sections because otherwise the lock
        would be held while doing the http request.

        A boolean (_loading) is used to indicate the loading status instead of
        _last_image since that is initialized to None.

        For reference:
          * :func:`asyncio.Condition.wait` releases the lock and acquires it
            again before continuing.
          * :func:`asyncio.Condition.notify_all` requires the lock to be held.
        """
        if not self.__needs_refresh():
            _LOG.debug("Last image returned, did not need refresh, width: %s, height: %s", width, height)
            return self._last_image

        # get lock, check iff loading, await notification if loading
        async with self._condition:
            # can not be tested - mocked http response returns immediately
            if self._loading:
                _LOG.debug("already loading - waiting for notification")
                await self._condition.wait()
                return self._last_image

            # Set loading status **while holding lock**, makes other tasks wait
            self._loading = True

        try:
            now = dt_util.utcnow()
            was_updated = await self.__retrieve_radar_image(width, height)
            if was_updated == False:
                was_updated = await self.__retrieve_radar_image_old(width, height)
            # was updated? Set new deadline relative to now before loading
            if was_updated:
                self._deadline = now + timedelta(seconds=self._delta)

            _LOG.debug("Last image returned, after refresh, width: %s, height: %s", width, height)
            return self._last_image
        finally:
            # get lock, unset loading status, notify all waiting tasks
            async with self._condition:
                self._loading = False
                self._condition.notify_all()
