# Written by Joe Britton, 2022


import logging
import asyncio
from highfinesse import wlm_constants as wlm
from enum import IntEnum
try:  # permits running in simulation mode on linux
    from ctypes import windll, c_double, c_ushort, c_long, c_bool, byref, c_short
except ImportError:
    pass

logger = logging.getLogger(__name__)

# These wavelength ranges do not match those in the documentation, but are
# extracted from the one multi-range WS6 we have access to
WavelengthRange = {
    "VIS_NIR": 6,
    "IR": 7
}


class WLMMeasurementStatus(IntEnum):
    OKAY = 0,
    UNDER_EXPOSED = 1,
    OVER_EXPOSED = 2,
    ERROR = 3


class WLMException(Exception):
    """ Raised on errors involving the WLM interface library (windata.dll) """
    def __init__(self, value):
        s = 'WLMException: {}'.format(value)
        logger.error(s)


class HighFinesse:
    """Driver for HighFinesse wavemeter used by Britton Lab
    """

    def __init__(self, simulation=False):
        self.simulation = simulation
        if self.simulation:
            logger.info('simulation mode active')
            return

        try:
            self.lib = lib = windll.wlmData
        except Exception as e:
            raise WLMException("Failed to load WLM DLL (is HighFinesse software installed?): {}".format(e))

        self.wlm_model = -1
        self.wlm_hw_rev = -1
        self.wlm_fw_rev = -1
        self.wlm_fw_build = -1

        # configure DLL function arg/return types
        lib.Operation.restype = c_long
        lib.Operation.argtypes = [c_ushort]
        lib.GetOperationState.restype = c_ushort
        lib.GetOperationState.argtypes = [c_ushort]
        lib.GetTemperature.restype = c_double
        lib.GetTemperature.argtypes = [c_double]
        lib.GetPressure.restype = c_double
        lib.GetPressure.argtypes = [c_double]
        lib.SetExposureModeNum.restype = c_long
        lib.SetExposureModeNum.argtypes = [c_long, c_bool]
        lib.GetFrequencyNum.restype = c_double
        lib.GetFrequencyNum.argtypes = [c_long, c_double]

        # Check the WLM server application is running and start it if necessary
        if not lib.Instantiate(wlm.cInstCheckForWLM, 0, 0, 0):
            logger.info("Starting WLM server")
            res = lib.ControlWLMEx(wlm.cCtrlWLMShow | wlm.cCtrlWLMWait,
                                   0, 0, 10000, 1)
            codes = wlm.control_wlm_to_str(res)
            if "flServerStarted" not in codes:
                raise WLMException("Error starting WLM server application : "
                                   "{}".format(codes))
            for code in codes:
                if code == "flServerStarted":
                    continue
                logger.warning("Unexpected return code from ControlWLMEx: {} "
                               .format(code))

        logger.info("Connected to WLM server")
        self.id()

    def close(self):
        """Do what's needed to close. """

    async def init(self):
        """Hook for async loop."""
        pass

    async def id(self):
        """ :returns: WLM identification string """
        if self.simulation:
            return "WLM simulator"

        """Sends the id command and prints output."""
        self.wlm_model = self.lib.GetWLMVersion(0)
        self.wlm_hw_rev = self.lib.GetWLMVersion(1)
        self.wlm_fw_rev = self.lib.GetWLMVersion(2)
        self.wlm_fw_build = self.lib.GetWLMVersion(3)

        if self.wlm_model < 5 or self.wlm_model > 10:
            raise WLMException("Unrecognised WLM model: {}".format(
                self.wlm_model))

        # WS/6 have 1, WS/7 & WS/8 & WS/U have 2
        self._num_ccds = 2 if self.wlm_model >= 7 else 1

        return "WLM {} rev {}, firmware {}.{}".format(
            self.wlm_model, self.wlm_hw_rev, self.wlm_fw_rev,
            self.wlm_fw_build)

    async def get_status(self):
        """Hook for async loop."""
        # TODO implement this
        pass

    async def ping(self):
        if self.simulation:
            logger.debug('ping simulation')
            return True
        try:
            await self.get_status()
        except asyncio.CancelledError:
            raise
        except Exception:
            raise WLMException('ping failed')
            return False
        logger.debug("ping successful")
        return True

    async def get_temperature(self):
        """ Returns the temperature of the wavemeter in C """
        if self.simulation:
            return 25.0

        temp = self.lib.GetTemperature(0)
        if temp < 0:
            raise WLMException(
                "Error reading WLM temperature: {}".format(temp))
        return temp

    async def get_pressure(self):
        """ Returns the pressure inside the wavemeter in mBar
        :raises WLMException: with an error code of -1006 if the wavemeter does
          not support pressure measurements
        """
        if self.simulation:
            return 1013.25

        pressure = self.lib.GetPressure(0)
        if pressure < 0:
            raise WLMException(
                "Error reading WLM pressure: {}". format(pressure))
        return pressure

    async def get_frequency(self, ch):
        """ Returns the frequency of the specified channel.

        :returns: the tuple (status, frequency) where status is a
          WLMMeasurementStatus and frequency is in Hz.
        """
        if self.simulation:
            return WLMMeasurementStatus.OKAY.value, 123.456789e12

        # this should never time out, but it does...
        # I've had a long discussion with the HF engineers about why this
        # occurs on some units, without any real success.
        try:
            # self._get_fresh_data()
            freq = self.lib.GetFrequencyNum(ch, 0)
        except WLMException as e:
            logger.error("error during frequency read: {}".format(e))
            return WLMMeasurementStatus.ERROR.value, 0

        if freq > 0:
            return WLMMeasurementStatus.OKAY.value, freq * 1e12
        elif freq == wlm.ErrBigSignal:
            logger.warning("OVER_EXPOSED: ch {}".format(ch))
            return WLMMeasurementStatus.OVER_EXPOSED.value, 0
        elif freq == wlm.ErrLowSignal:
            logger.warning("UNDER_EXPOSED: ch {}".format(ch))
            return WLMMeasurementStatus.UNDER_EXPOSED.value, 0
        else:
            logger.error("error getting frequency: {}"
                         .format(wlm.error_to_str(freq)))
            return WLMMeasurementStatus.ERROR.value, 0
