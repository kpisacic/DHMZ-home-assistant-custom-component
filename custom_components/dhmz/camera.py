"""Provide DHMZ radar image"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

import aiohttp
import voluptuous as vol
from io import BytesIO
from PIL import Image, ImageDraw

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
RADAR_MAP_URL_ANIM = "https://vrijeme.hr/radari/anim_kompozit{index}.png"
RADAR_MAP_URL_ANIM_GIF = "http://vrijeme.hr/anim_kompozit.gif"

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

    @property
    def name(self) -> str:
        """Return the component name."""
        return self._name

    @property
    def entity_picture(self):
        """Return a link to the camera feed as entity picture."""
        return RADAR_MAP_URL_STATIC

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
        """Retrieve new radar image and return whether this succeeded."""
        session = async_get_clientsession(self.hass)

        b_regenerate_needed = False

        # check first image, header and etag
        i = 0

        if self._images[i]["last_modified"]:
            headers = {"If-Modified-Since": self._images[i]["last_modified"] }
        else:
            headers = {}

        if self._images[i]["etag"] != "":
            # get header to compare etag
            _LOG.debug("HEAD url: %s", RADAR_MAP_URL_ANIM.format(index=i+1) )
            try:
                res = await session.head(RADAR_MAP_URL_ANIM.format(index=i+1) , timeout=5, headers=headers)
                res.raise_for_status()
            except (asyncio.TimeoutError, aiohttp.ClientError) as err:
                _LOG.error("Failed to fetch header, %s", err)
                return False

            if res.status == 304:
                _LOG.debug("HEAD - HTTP 304 - success")
            else:
                etag = res.headers.get("etag", None)
                if etag:
                    _LOG.debug("HEAD image - etag: %s", etag)
                    j = 0
                    while j < 25 and self._images[0]["etag"] != "":
                        # Check etag of first image in stack
                        if self._images[0]["etag"][-5:] != etag[-5:]:
                            # If etag differs, remove image from stack, and append empty image position
                            i_removed = self._images.pop(0)
                            _LOG.debug("Removed etag: %s", i_removed["etag"])
                            self._images.append({   "content_length": 0,
                                                    "etag": "",
                                                    "last_modified": None })
                            self._images_content.pop(0)
                            self._images_content.append(None)
                            j += 1
                        else:
                            break

        for i in range(25):

            # refresh images with empty etag (not fetched by now) and last image always
            if self._images[i]["etag"] == "" or i == 24:

                if self._images[i]["last_modified"]:
                    headers = {"If-Modified-Since": self._images[i]["last_modified"] }
                else:
                    headers = {}
                
                _LOG.debug("GET url: %s", RADAR_MAP_URL_ANIM.format(index=i+1) )
                try:
                    res = await session.get( RADAR_MAP_URL_ANIM.format(index=i+1) , timeout=5, headers=headers)
                    res.raise_for_status()
                except (asyncio.TimeoutError, aiohttp.ClientError) as err:
                    _LOG.error("Failed to fetch get, %s", err)
                    return False

                if res.status == 304:
                    _LOG.debug("GET - HTTP 304 - success")
                    continue

                try:
                    current_content = await res.read()
                except (asyncio.TimeoutError, aiohttp.ClientError) as err:
                    _LOG.error("Failed to read content, %s", err)
                    return False

                try:
                    self._images_content[i] = Image.open(BytesIO(current_content))
                    if self._show_location:
                        draw = ImageDraw.Draw(self._images_content[i])
                        x_coord = int( ( 0.11346541830650277 * self._longitude - 1.3351816168381 ) * float(self._images_content[i].size[0]) )
                        y_coord = int( (-0.15304197356993342 * self._latitude + 7.31403749212996 ) * float(self._images_content[i].size[1]) )
                        draw.ellipse((x_coord-5,y_coord-5,x_coord+5,y_coord+5), fill=(0,0,0), outline=(0,0,0))
                except OSError as err:
                    _LOG.error("OSError drawing on image: %s", RADAR_MAP_URL_ANIM.format(index=i+1) )
                    return False

                last_modified = res.headers.get("last-modified")
                if last_modified:
                    self._images[i]["last_modified"] = last_modified

                etag = res.headers.get("etag", None)
                if etag:
                    self._images[i]["etag"] = etag

                content_length = res.headers.get("content-length")
                if content_length:
                    self._images[i]["content_length"] = content_length

                b_regenerate_needed = True

                _LOG.debug("Stored image %s, etag: %s, content length: %s", i+1, etag, content_length)

        # Build new animated image
        if b_regenerate_needed:
            file_bytes_io = BytesIO()
            a_durations = [ self._previous_images_time for i in range(25)]
            a_durations[24] = self._current_image_time
            try:
                self._images_content[0].save(file_bytes_io, format=self._image_format, save_all=True, append_images=self._images_content[1:], optimize=True, duration=a_durations, loop=0)
            except (ValueError) as err:
                _LOG.error("ValueError converting to animated image")
            except (OSError) as err:
                _LOG.error("OSError converting to animated image")

            _LOG.debug("Converged to animated image done, size: %s", file_bytes_io.tell())

            self._last_image = file_bytes_io.getvalue()

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
