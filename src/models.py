# -*- coding: utf-8 -*-
import jwt
import geoalchemy2
import json
import datetime
import secrets
import math

from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.hybrid import hybrid_method
from geoalchemy2 import Geography
from time import time
from sqlalchemy import func, and_
from flask_login import UserMixin
from enum import IntEnum
from dateutil.parser import parse as date_parse

from src.function import isInt, isFloat
from src import app, gwtmconfig
from src import login

from . import function
from . import enums

db = SQLAlchemy(app)

def create_database_tables():
    app.config["SQLALCHEMY_DATABASE_URI"] = gwtmconfig.config.SQLALCHEMY_DATABASE_URI
    with app.app_context():
        db.create_all()


def to_json(inst, cls):
    """
    Jsonify the sql alchemy query result.
    """
    convert = dict()
    json_cols = [gw_galaxy_entry.info]
    # add your coversions for things like datetime's
    # and what-not that aren't serializable.
    d = dict()
    for c in cls.__table__.columns:
        v = getattr(inst, c.name)

        if c.type in convert.keys() and v is not None:
            try:
                d[c.name] = convert[c.type](v)
            except:  # noqa: E722
                d[c.name] = "Error:  Failed to covert using ", str(convert[c.type])
        elif c in json_cols:
            d[c.name] = v
        elif v is None:
            d[c.name] = str()
        elif "instrument_type" in str(v):
            d[c.name] = v.name
        elif "pointing_status" in str(v):
            d[c.name] = v.name
        elif "bandpass" in str(v):
            d[c.name] = v.name
        elif "depth_unit" in str(v):
            d[c.name] = v.name
        elif "geography" in str(c.type):
            # try:
            d[c.name] = str(geoalchemy2.shape.to_shape(v))
            # except:
            #   d[c.name] = v
        elif isinstance(v, (datetime.date, datetime.datetime)):
            d[c.name] = v.isoformat()
        else:
            d[c.name] = v
    # to fix the api do : return d, and json.dumps() in api returns...
    return json.dumps(d)


def parse_model(inst, cls):
    """
    Returns a string value for the sql alchemy query result.
    """
    convert = dict()
    json_cols = [gw_galaxy_entry.info]
    # add your coversions for things like datetime's
    # and what-not that aren't serializable.
    d = dict()
    for c in cls.__table__.columns:
        v = getattr(inst, c.name)

        if c.type in convert.keys() and v is not None:
            try:
                d[c.name] = convert[c.type](v)
            except:  # noqa: E722
                d[c.name] = "Error:  Failed to covert using ", str(convert[c.type])
        elif c in json_cols:
            d[c.name] = v
        elif v is None:
            d[c.name] = str()
        elif "instrument_type" in str(v):
            d[c.name] = v.name
        elif "pointing_status" in str(v):
            d[c.name] = v.name
        elif "bandpass" in str(v):
            d[c.name] = v.name
        elif "depth_unit" in str(v):
            d[c.name] = v.name
        elif "geography" in str(c.type):
            # try:
            d[c.name] = str(geoalchemy2.shape.to_shape(v))
            # except:
            #   d[c.name] = v
        elif isinstance(v, (datetime.date, datetime.datetime)):
            d[c.name] = v.isoformat()
        else:
            d[c.name] = v
    # to fix the api do : return d, and json.dumps() in api returns...
    return d


class valid_mapping():
    def __init__(self):
        self.valid = False
        self.errors = []
        self.warnings = []


class SpectralRangeHandler:
    '''
        Values for the central wave and bandwidth were taken from:
            http://svo2.cab.inta-csic.es/theory/fps/index.php?mode=browse
            notated by the 'source' field in the following dictionary
            for central_wavelength I used the lam_cen
            for bandwidth I used the FWHM

        Our base for the central wavelengths and bandwidths will be stored in
            Angstroms

        There are following static methods to convert the Angstrom values into ranges for
            frequency in Hz
            energy in eV
    '''

    '''
        spectral type enum
    '''

    class spectralrangetype(IntEnum):
        wavelength = 1
        energy = 2
        frequency = 3

    '''
        older bandpass dictionary
    '''
    bandpass_wavelength_dictionary = {
        enums.bandpass.U: {
            'source': 'CTIO/SOI.bessel_U',
            'central_wave': 3614.82,
            'bandwidth': 617.24
        },
        enums.bandpass.B: {
            'source': 'CTIO/SOI.bessel_B',
            'central_wave': 4317.0,
            'bandwidth': 991.48
        },
        enums.bandpass.V: {
            'source': 'CTIO/SOI.bessel_V',
            'central_wave': 5338.65,
            'bandwidth': 810.65
        },
        enums.bandpass.R: {
            'source': 'CTIO/SOI.bessel_R',
            'central_wave': 6311.86,
            'bandwidth': 1220.89
        },
        enums.bandpass.I: {
            'source': 'CTIO/SOI.bessel_I',
            'central_wave': 8748.91,
            'bandwidth': 2940.57
        },
        enums.bandpass.J: {
            'source': 'CTIO/ANDICAM/J',
            'central_wave': 12457.00,
            'bandwidth': 1608.86
        },
        enums.bandpass.H: {
            'source': 'CTIO/ANDICAM/H',
            'central_wave': 16333.11,
            'bandwidth': 2969.21
        },
        enums.bandpass.K: {
            'source': 'CTIO/ANDICAM/K',
            'central_wave': 21401.72,
            'bandwidth': 2894.54
        },
        enums.bandpass.u: {
            'source': 'CTIO/DECam.u_filter',
            'central_wave': 3552.98,
            'bandwidth': 885.05
        },
        enums.bandpass.g: {
            'source': 'CTIO/DECam.g_filter',
            'central_wave': 4730.50,
            'bandwidth': 1503.06
        },
        enums.bandpass.r: {
            'source': 'CTIO/DECam.r_filter',
            'central_wave': 6415.40,
            'bandwidth': 1487.58
        },
        enums.bandpass.i: {
            'source': 'CTIO/DECam.i_filter',
            'central_wave': 7836.21,
            'bandwidth': 1468.29
        },
        enums.bandpass.z: {
            'source': 'CTIO/DECam.z_filter',
            'central_wave': 9258.37,
            'bandwidth': 1521.09
        },
        enums.bandpass.UVW1: {
            'source': 'Swift/UVOT.UVW1',
            'central_wave': 2629.35,
            'bandwidth': 656.60
        },
        enums.bandpass.UVW2: {
            'source': 'Swift/UVOT.UVW2',
            'central_wave': 1967.37,
            'bandwidth': 584.89
        },
        enums.bandpass.UVM2: {
            'source': 'Swift/UVOT.UVM2',
            'central_wave': 2259.84,
            'bandwidth': 527.13
        },
        enums.bandpass.XRT: {
            'source': 'Manual calculation from 0.3-10keV',
            'central_wave': 21.2839,
            'bandwidth': 20.0441
        },
        enums.bandpass.clear: {
            'source': 'WHT/ULTRACAM.clear',
            'central_wave': 6977.45,
            'bandwidth': 2757.0
        },
        enums.bandpass.open: {
            'source': 'Coverage from 4000A-10000A',
            'central_wave': 7000,
            'bandwidth': 3000
        },
        enums.bandpass.UHF: {
            'source': 'manual conversion from 0.03-0.3GHz',
            'central_wave': 54961950633.331505,
            'bandwidth': 44968868699.998505
        },
        enums.bandpass.VHF: {
            'source': 'manual conversion from 0.3-1.0GHz',
            'central_wave': 6495503256.6665,
            'bandwidth': 3497578676.6665
        },
        enums.bandpass.L: {
            'source': 'manual conversion from 1-2GHz',
            'central_wave': 2248443435.0,
            'bandwidth': 749481145.0
        },
        enums.bandpass.S: {
            'source': 'manual conversion from 2-4GHz',
            'central_wave': 1124221715.25,
            'bandwidth': 374740574.75
        },
        enums.bandpass.C: {
            'source': 'manual conversion from 4-8GHz',
            'central_wave': 936851431.25,
            'bandwidth': 562110858.75
        },
        enums.bandpass.X: {
            'source': 'manual conversion from 8-12GHz',
            'central_wave': 312283810.41665,
            'bandwidth': 62456762.08335
        },
        enums.bandpass.TESS: {
            'source': 'TESS/TESS.Red',
            'central_wave': 7917.84,
            'bandwidth': 4010.94
        },
        # enums.bandpass.other: {
        #    'source' : None,
        #    'central_wave' : None,
        #    'bandwidth' : None
        # },
        enums.bandpass.BAT: {
            'source': 'manual conversion from 15-350keV',
            'central_wave': 0.431,
            'bandwidth': 0.3956
        },
        enums.bandpass.HESS: {
            'source': 'manual conversion from 10geV-50TeV',
            'central_wave': 6.200239850000001e-06,
            'bandwidth': 6.197760150000001e-06
        },
        enums.bandpass.WISEL: {
            'source': 'Iair figure he sent me in slack ~ 3700-7000A',
            'central_wave': 5350,
            'bandwidth': 1650
        },
        enums.bandpass.q: {
            'source': 'Danielle Piertese',
            'central_wave': 5800,
            'bandwidth': 2800
        }
    }

    '''
        method that returns the most likely bandpass name from central_wave and bandwidth
    '''

    @staticmethod
    def bandEnumFromCentralWaveBandwidth(central_wave, bandwidth):
        mindict = {}
        for band in SpectralRangeHandler.bandpass_wavelength_dictionary:
            mindict[band] = {
                'cw_diff': abs(
                    central_wave - SpectralRangeHandler.bandpass_wavelength_dictionary[band]['central_wave']),
                'bw_diff': abs(bandwidth - SpectralRangeHandler.bandpass_wavelength_dictionary[band]['bandwidth'])
            }

        min_cw_diff = min(x['cw_diff'] for x in mindict.values())

        bandname = [x for x, y in mindict.items() if y['cw_diff'] == min_cw_diff][0]
        return bandname

    '''
        method that returns the corresponding wave range to frequency in Hz
    '''

    @staticmethod
    def wavetoFrequency(central_wave=None, bandwidth=None, bandpass=None):
        wave_min, wave_max = SpectralRangeHandler.wavetoWaveRange(central_wave, bandwidth, bandpass)

        freq_max = 2997924580000000000.0 / wave_min
        freq_min = 2997924580000000000.0 / wave_max

        return freq_min, freq_max

    '''
        method that returns the corresponding wave range to energy in eV
    '''

    @staticmethod
    def wavetoEnergy(central_wave=None, bandwidth=None, bandpass=None):
        wave_min, wave_max = SpectralRangeHandler.wavetoWaveRange(central_wave, bandwidth, bandpass)

        ev_max = 12398 / wave_min
        ev_min = 12398 / wave_max

        return ev_min, ev_max

    '''
        method that returns the wavelength range from the central_wave and bandwidth, or bandpass
    '''

    @staticmethod
    def wavetoWaveRange(central_wave=None, bandwidth=None, bandpass=None):
        if central_wave is None and bandwidth is None and bandpass is not None:
            bp = SpectralRangeHandler.bandpass_wavelength_dictionary[bandpass]
            central_wave = bp['central_wave']
            bandwidth = bp['bandwidth']

        wave_min = central_wave - (bandwidth / 2.0)
        wave_max = central_wave + (bandwidth / 2.0)

        return wave_min, wave_max

    '''
        method that returns the central_wave and bandwidth from a given energy range (must be eV)
            higher energy corresponds to lower wavelength
            lower energy corresponds to higher wavelength
    '''

    @staticmethod
    def wavefromEnergyRange(min_energy, max_energy):

        wave_min = 12398 / max_energy
        wave_max = 12398 / max_energy

        bandwidth = 0.5 * (wave_max - wave_min)
        central_wave = wave_min + bandwidth

        return central_wave, bandwidth

    '''
        method that returns the central_wave and bandwidth from a given frequency range (must be Hz)
            higher frequency corresponds to lower wavelength
            lower frequency corresponds to higher wavelength
    '''

    @staticmethod
    def wavefromFrequencyRange(min_freq, max_freq):
        wave_min = 2997924580000000000.0 / max_freq
        wave_max = 2997924580000000000 / min_freq

        bandwidth = 0.5 * (wave_max - wave_min)
        central_wave = wave_min + bandwidth

        return central_wave, bandwidth


@login.user_loader
def load_user(id):
    return users.query.get(int(id))


# API Models

class users(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(25), index=True, unique=True)
    firstname = db.Column(db.String(25))
    lastname = db.Column(db.String(25))
    password_hash = db.Column(db.String(128))
    datecreated = db.Column(db.DateTime)
    email = db.Column(db.String(100))
    api_token = db.Column(db.String(128))
    verification_key = db.Column(db.String(128))
    verified = db.Column(db.Boolean)

    def get_id(self):
        return self.id

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def set_apitoken(self):
        self.api_token = secrets.token_urlsafe(28)

    def check_apitoken(self, token):
        return token == self.api_token

    def set_verification_key(self):
        self.verification_key = secrets.token_urlsafe(28)

    def check_verification_key(self, verification_key):
        return verification_key == self.verification_key

    def get_reset_password_token(self, expires_in=600):
        token = jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            app.config['SECRET_KEY'], algorithm='HS256').decode('utf-8')
        return token

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, app.config['SECRET_KEY'],
                            algorithms=['HS256'])['reset_password']
        except:  # noqa: E722
            return
        return users.query.get(id)


class usergroups(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.Integer)
    groupid = db.Column(db.Integer)
    role = db.Column(db.String(25))


class groups(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(25))
    datecreated = db.Column(db.DateTime)


class useractions(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.Integer)
    ipaddress = db.Column(db.String(50))
    url = db.Column(db.String())
    time = db.Column(db.DateTime)
    jsonvals = db.Column(db.JSON)
    method = db.Column(db.String(24))

    def write_action(request, current_user, jsonvals=None):
        if not app.debug:
            try:
                ipaddress = None
                if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
                    ipaddress = request.environ['REMOTE_ADDR']
                else:
                    ipaddress = request.environ['HTTP_X_FORWARDED_FOR']

                if jsonvals is None:
                    try:
                        jsonvals = request.get_json()
                    except:  # noqa: E722
                        jsonvals = {}

                ua = useractions(
                    userid=current_user.get_id(),
                    ipaddress=ipaddress,
                    url=request.url,
                    time=datetime.datetime.now(),
                    jsonvals=jsonvals,
                    method=request.method
                )
                db.session.add(ua)
                db.session.commit()
            except:  # noqa: E722
                print(f"error in writing user actions: request={request}")


class instrument(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    instrument_name = db.Column(db.String(25))
    nickname = db.Column(db.String(25))
    instrument_type = db.Column(db.Enum(enums.instrument_type))
    datecreated = db.Column(db.DateTime)
    # footprint = db.Column(Geography('POLYGON', srid=4326))
    submitterid = db.Column(db.Integer)

    @property
    def json(self):
        return to_json(self, self.__class__)

    @property
    def parse(self):
        return parse_model(self, self.__class__)

    def from_json(self, form, userid, preview=False):
        v = valid_mapping()

        nickname = form.instrument_nickname.data
        submitterid = userid
        instrument_name = form.instrument_name.data
        footprint = []
        multi_vertices = []

        u = form.unit.data
        if (u is None or u == "choose") and not preview:
            v.errors.append('Unit is required')
            return [v]

        scale = 1
        if u == "deg":
            scale = 1
        if u == "arcmin":
            scale = 1 / 60.0
        if u == "arcsec":
            scale = 1 / (60.0 * 60.0)

        if form.footprint_type.data == 'Rectangular':
            h, w = form.height.data, form.width.data
            if h is None or w is None:
                v.errors.append('Height and Width are required for Rectangular shape')
                return [v]
            if not isFloat(h) or not isFloat(w):
                v.errors.append('Height and Width must be decimal')
                return [v]

            vertices = []
            half_h = round(0.5 * float(h) * scale, 4)
            half_w = round(0.5 * float(w) * scale, 4)
            vertices.append([-half_w, half_h])
            vertices.append([half_w, half_h])
            vertices.append([half_w, -half_h])
            vertices.append([-half_w, -half_h])
            vertices.append([-half_w, half_h])

            multi_vertices.append(vertices)
            geom = function.create_geography(vertices)
            footprint.append(geom)

        if form.footprint_type.data == 'Circular':
            r = form.radius.data

            if r is None:
                v.errors.append('Radius is required for Circular shape')
                return [v]
            if not isFloat(r):
                v.errors.append('Radius must be decimal')
                return [v]

            r = float(r) * float(scale)
            vertices = []
            steps = len(range(0, 360, int(360 / 20)))
            ang = float(360 / (steps))

            for a in range(0, steps):
                a = float(a)
                x = r * math.cos(math.radians(90 - a * ang))
                y = r * math.sin(math.radians(90 - a * ang))
                if abs(x) < 1e-10:
                    x = 0.0
                if abs(y) < 1e-10:
                    y = 0.0
                x = round(x, 4)
                y = round(y, 4)
                vertices.append([x, y])
            vertices.append(vertices[0])

            multi_vertices.append(vertices)
            geom = function.create_geography(vertices)
            footprint.append(geom)

        if form.footprint_type.data == 'Polygon':
            p = form.polygon.data
            if p is None:
                v.errors.append('Polygon is required for Polygon shape')
                return [v]

            vertices = []

            if "[" in p and "]" in p:
                polygons = p.split("#")
                for poly in polygons:
                    try:
                        poly = poly.split('[')[1].split(']')[0]
                        result = function.extract_polygon(poly, scale)
                        if len(result[1]) > 0:
                            for e in result[1]:
                                v.errors.append(e)
                            return [v]
                        else:
                            vertices = result[0]

                        multi_vertices.append(vertices)
                        geom = function.create_geography(vertices)
                        footprint.append(geom)
                    except Exception as e:
                        v.errors.append("Invalid Polygon. If error persists, contact administrator")
                        return [v]

            else:
                result = function.extract_polygon(p, scale)
                if len(result[1]) > 0:
                    for e in result[1]:
                        v.errors.append(e)
                    return [v]
                else:
                    vertices = result[0]

                multi_vertices.append(vertices)
                geom = function.create_geography(vertices)
                footprint.append(geom)

        if len(footprint) == 0:
            v.errors.append('Footprint required')
            return [v]

        self.nickname = nickname
        self.instrument_name = instrument_name
        self.instrument_type = enums.instrument_type.photometric
        self.submitterid = submitterid
        self.datecreated = datetime.datetime.now()
        return [v, footprint, multi_vertices]


class footprint_ccd(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    instrumentid = db.Column(db.Integer)
    footprint = db.Column(Geography('POLYGON', srid=4326))

    @property
    def json(self):
        return to_json(self, self.__class__)

    @property
    def parse(self):
        return parse_model(self, self.__class__)


class pointing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.Enum(enums.pointing_status))
    position = db.Column(Geography('POINT', srid=4326))
    galaxy_catalog = db.Column(db.Integer)
    galaxy_catalogid = db.Column(db.Integer)
    instrumentid = db.Column(db.Integer)
    depth = db.Column(db.Float)
    depth_err = db.Column(db.Float)
    depth_unit = db.Column(db.Enum(enums.depth_unit))
    time = db.Column(db.DateTime)
    datecreated = db.Column(db.DateTime)
    dateupdated = db.Column(db.DateTime)
    submitterid = db.Column(db.Integer)
    pos_angle = db.Column(db.Float)
    band = db.Column(db.Enum(enums.bandpass))
    doi_url = db.Column(db.String(100))
    doi_id = db.Column(db.Integer)
    central_wave = db.Column(db.Float)
    bandwidth = db.Column(db.Float)

    @property
    def json(self):
        return to_json(self, self.__class__)

    @property
    def parse(self):
        return parse_model(self, self.__class__)

    @hybrid_method
    def inSpectralRange(self, spectral_min, spectral_max, spectral_type):
        '''
        function to determine if a pointing is within a given range for spectral types:
            wavelength (Angstroms)
            energy (eV)
            frequency (Hz)

        it inputs the range of the spectral type (minimum and maximum values for given type) and
            determines if the pointing's observation is in that range. The boolean logic is all
            encompassing; whether the endpoints are confined entirely within the provided range
        '''

        if spectral_type == SpectralRangeHandler.spectralrangetype.wavelength:
            thismin, thismax = SpectralRangeHandler.wavetoWaveRange(self.central_wave, self.bandwidth)
        if spectral_type == SpectralRangeHandler.spectralrangetype.energy:
            thismin, thismax = SpectralRangeHandler.wavetoEnergy(self.central_wave, self.bandwidth)
        if spectral_type == SpectralRangeHandler.spectralrangetype.frequency:
            thismin, thismax = SpectralRangeHandler.wavetoFrequency(self.central_wave, self.bandwidth)

        if thismin >= spectral_min and thismax <= spectral_max:
            return True

        return False

    @inSpectralRange.expression
    def inSpectralRange(cls, spectral_min, spectral_max, spectral_type):
        '''
        function to determine if a pointing is within a given range for spectral types:
            wavelength (Angstroms)
            energy (eV)
            frequency (Hz)

        it inputs the range of the spectral type (minimum and maximum values for given type) and
            determines if the pointing's observation is in that range. The boolean logic is all
            encompassing; whether the endpoints are confined entirely within the provided range
        '''

        if spectral_type == SpectralRangeHandler.spectralrangetype.wavelength:
            thismin, thismax = SpectralRangeHandler.wavetoWaveRange(cls.central_wave, cls.bandwidth)
        if spectral_type == SpectralRangeHandler.spectralrangetype.energy:
            thismin, thismax = SpectralRangeHandler.wavetoEnergy(cls.central_wave, cls.bandwidth)
        if spectral_type == SpectralRangeHandler.spectralrangetype.frequency:
            thismin, thismax = SpectralRangeHandler.wavetoFrequency(cls.central_wave, cls.bandwidth)

        return and_(thismin >= spectral_min, thismax <= spectral_max)
        # if thismin >= spectral_min and thismax <= spectral_max:
        #    return True

        # return False

    @staticmethod
    def pointings_from_IDS(ids, filter=[]):

        filter.append(instrument.id == pointing.instrumentid)
        filter.append(pointing_event.pointingid.in_(ids))
        filter.append(pointing.id.in_(ids))

        pointings = db.session.query(
            pointing.id,
            func.ST_AsText(pointing.position).label('position'),
            pointing.instrumentid,
            pointing.band,
            pointing.pos_angle,
            pointing.depth,
            pointing.depth_err,
            pointing.depth_unit,
            pointing.time,
            pointing.status,
            pointing.central_wave,
            pointing.bandwidth,
            instrument.instrument_name,
            instrument.instrument_type,
            pointing_event.graceid
        ).filter(*filter).all()

        pointing_returns = {}
        for p in pointings:
            pointing_returns[str(p.id)] = p

        return pointing_returns

    def from_json(self, p, dbinsts, userid, planned_pointings, otherpointings):  # dbusers):
        v = valid_mapping()

        PLANNED = False
        if 'id' in p:
            PLANNED = True
            pointingid = p['id']
            planned_pointing = planned_pointings[str(pointingid)]

            if planned_pointing.status == enums.pointing_status.completed or planned_pointing.status == enums.pointing_status.cancelled:
                v.errors.append('This pointing has already been ' + planned_pointing.status.name)

            self.position = planned_pointing.position
            self.depth = planned_pointing.depth
            self.depth_err = planned_pointing.depth_err
            self.depth_unit = planned_pointing.depth_unit
            self.status = enums.pointing_status.completed
            self.band = planned_pointing.band
            self.central_wave = planned_pointing.central_wave
            self.bandwidth = planned_pointing.bandwidth
            self.instrumentid = planned_pointing.instrumentid
            self.pos_angle = planned_pointing.pos_angle

        if 'status' in p:
            userstatus = p['status']
            validstatusints = [int(b) for b in enums.pointing_status if b.name != 'cancelled']
            validstatusstr = [str(b.name) for b in enums.pointing_status if b.name != 'cancelled']
            if userstatus in validstatusints or userstatus in validstatusstr:
                statusenum = \
                [ps for ps in enums.pointing_status if userstatus == int(ps) or userstatus == str(ps.name)][0]
                self.status = statusenum
        elif not PLANNED:
            self.status = enums.pointing_status.completed
        else:
            v.warnings.append("No status given, or unrecognized status. Setting the status to planned")
            self.status = enums.pointing_status.planned

        if 'position' in p and not PLANNED:
            pos = p['position']
            if pos is not None:
                if all([x in pos for x in ["POINT", "(", ")", " "]]) and "," not in pos:
                    self.position = p['position']
                else:
                    v.errors.append(
                        "Invalid position argument. Must be decimal format ra/RA, dec/DEC, or geometry type \"POINT(RA DEC)\"")
        elif not PLANNED:
            if 'ra' in p or 'RA' in p:
                ra = p['ra'] if 'ra' in p else p['RA']
                if not isFloat(ra):
                    ra = None
            else:
                ra = None

            if 'dec' in p or 'DEC' in p:
                dec = p['dec'] if 'dec' in p else p['DEC']
                if not isFloat(dec):
                    dec = None
            else:
                dec = None

            if ra is None or dec is None:
                v.errors.append(
                    "Invalid position argument. Must be decimal format ra/RA, dec/DEC, or geometry type \"POINT(RA DEC)\"")
            else:
                self.position = "POINT(" + str(ra) + " " + str(dec) + ")"

        if 'instrumentid' in p and not PLANNED:
            inst = p['instrumentid']
            validinst = False
            if isInt(inst):
                insts = [x for x in dbinsts if x.id == int(inst)]
                if len(insts) > 0:
                    self.instrumentid = inst
                    validinst = True
            else:
                insts = [x for x in dbinsts if x.instrument_name == inst]
                inames = [x.instrument_name for x in insts]
                if inst in inames:
                    instmatch = insts[0].id
                    validinst = True
                    self.instrumentid = instmatch

            if validinst is False:
                v.errors.append("Invalid instrumentid. Can be id or name of instrument")
        elif not PLANNED:
            v.errors.append("Field instrumentid is required")

        if 'depth' in p:
            if isFloat(p['depth']):
                self.depth = p['depth']
            else:
                v.errors.append('Invalid depth. Must b and not PLANNEDe decimal')
        elif self.status == enums.pointing_status.completed and not PLANNED:
            v.errors.append('depth is required for completed observations')

        if 'depth_unit' in p:
            du = p['depth_unit']
            validdepthunit = [int(b) for b in enums.depth_unit]
            validdepthunitstr = [str(b.name) for b in enums.depth_unit]
            if du in validdepthunit or du in validdepthunitstr:
                duenum = [d for d in enums.depth_unit if int(d) == du or str(d.name) == du][0]
                self.depth_unit = duenum
            else:
                v.errors.append('Invalid depth_unit. Must be ab_mag, vega_mag, flux_erg, or flux_jy')
        else:
            v.errors.append('depth_unit is required')

        if 'depth_err' in p:
            if isFloat(p['depth_err']):
                self.depth_err = p['depth_err']
            else:
                v.errors.append('Invalid depth_err. Must be decimal')

        if 'pos_angle' in p:
            if isFloat(p['pos_angle']):
                self.pos_angle = p['pos_angle']
            else:
                v.errors.append('Invalid pos_angle. Must be decimal')
        elif self.status == enums.pointing_status.completed and self.pos_angle is not None:
            v.errors.append('pos_angle is required for completed observations')

        if 'time' in p:
            try:
                self.time = date_parse(p['time'])
            except:  # noqa: E722
                v.errors.append(
                    "Error parsing date. Should be %Y-%m-%dT%H:%M:%S.%f format. e.g. 2019-05-01T12:00:00.00")
        elif self.status == enums.pointing_status.planned:
            v.errors.append("Field \"time\" is required for when the pointing is planned to be observed")
        elif self.status == enums.pointing_status.completed:
            v.errors.append('Field \"time\" is required for the observed pointing')

        self.submitterid = userid
        self.datecreated = datetime.datetime.now()

        if "wavelength_regime" in p and "wavelength_unit" in p and not PLANNED:

            try:
                regime = str(p['wavelength_regime']).split('[')[1].split(']')[0].split(',')
                wave_min, wave_max = float(regime[0]), float(regime[1])

                validwavelengthunits_ints = [int(b) for b in enums.wavelength_units]
                validwavelengthunits_str = [str(b.name) for b in enums.wavelength_units]
                user_unit = p['wavelength_unit']

                if user_unit in validwavelengthunits_ints or user_unit in validwavelengthunits_str:
                    wuenum = [w for w in enums.wavelength_units if int(w) == user_unit or str(w.name) == user_unit][0]
                    scale = enums.wavelength_units.get_scale(wuenum)
                    wave_min = wave_min * scale
                    wave_max = wave_max * scale

                    self.bandwidth = 0.5 * (wave_max - wave_min)
                    self.central_wave = wave_min + self.bandwidth
                    self.band = SpectralRangeHandler.bandEnumFromCentralWaveBandwidth(self.central_wave, self.bandwidth)
                    p['band'] = self.band
                else:
                    v.errors.append(
                        'Wavelength Unit is required, valid units are \'angstrom\', \'nanometer\', and \'micron\'')
            except:  # noqa: E722
                v.errors.append('Error parsing \'wavelength_regime\'. required format is a list: \'[low, high]\'')

        if "frequency_regime" in p and "frequency_unit" in p and not PLANNED:

            try:
                regime = str(p['frequency_regime']).split('[')[1].split(']')[0].split(',')
                min_freq, max_freq = float(regime[0]), float(regime[1])

                validfrequnits_ints = [int(b) for b in enums.frequency_units]
                validfrequnits_str = [str(b.name) for b in enums.frequency_units]
                user_unit = p['frequency_unit']

                if user_unit in validfrequnits_ints or user_unit in validfrequnits_str:
                    fuenum = [w for w in enums.frequency_units if int(w) == user_unit or str(w.name) == user_unit][0]
                    scale = enums.frequency_units.get_scale(fuenum)
                    min_freq = min_freq * scale
                    max_freq = max_freq * scale

                    self.central_wave, self.bandwidth = SpectralRangeHandler.wavefromFrequencyRange(min_freq, max_freq)
                    self.band = SpectralRangeHandler.bandEnumFromCentralWaveBandwidth(self.central_wave, self.bandwidth)
                    p['band'] = self.band
                else:
                    v.errors.append(
                        'Frequency Unit is required, valid units are \'Hz\', \'kHz\', \'MHz\', \'GHz\', and \'THz\'')
            except:  # noqa: E722
                v.errors.apend('Error parsing \'frequency_regime\'. required format is a list: \'[low, high]\'')

        if "energy_regime" in p and "energy_unit" in p and not PLANNED:
            try:
                regime = str(p['energy_regime']).split('[')[1].split(']')[0].split(',')
                min_energy, max_energy = float(regime[0]), float(regime[1])

                validenergyunits_ints = [int(b) for b in enums.energy_units]
                validenergyunits_str = [str(b.name) for b in enums.energy_units]
                user_unit = p['energy_unit']

                if user_unit in validenergyunits_ints or user_unit in validenergyunits_str:
                    euenum = [w for w in enums.energy_units if int(w) == user_unit or str(w.name) == user_unit][0]
                    scale = enums.energy_units.get_scale(euenum)
                    min_energy = min_energy * scale
                    max_energy = max_energy * scale

                    self.central_wave, self.bandwidth = SpectralRangeHandler.wavefromEnergyRange(min_energy, max_energy)
                    self.band = SpectralRangeHandler.bandEnumFromCentralWaveBandwidth(self.central_wave, self.bandwidth)
                    p['band'] = self.band
                else:
                    v.errors.append(
                        '\'energy_unit\' is required, valid units are \'eV\', \'keV\', \'MeV\', \'GeV\', and \'TeV\'')
            except:  # noqa: E722
                v.errors.apend('Error parsing \'energy_regime\'. required format is a list: \'[low, high]\'')
            pass

        if 'central_wave' in p and not PLANNED:
            central_wave = p['central_wave']
            if isFloat(central_wave):
                self.central_wave = central_wave
            else:
                v.errors.append('Error parsing \'central_wave\'. required format is decimal')

        if 'bandwidth' in p and not PLANNED:
            bandwidth = p['bandwidth']
            if isFloat(bandwidth):
                self.bandwidth = bandwidth
            else:
                v.errors.append('Error parsing \'bandwidth\'. required format is decimal')

        if "band" in p and not PLANNED:
            validbandints = [int(b) for b in enums.bandpass]
            validbandstr = [str(b.name) for b in enums.bandpass]
            userband = p['band']
            if userband in validbandints or userband in validbandstr:
                bandenum = [b for b in enums.bandpass if userband == int(b) or userband == str(b.name)][0]
                self.band = userband
                if self.central_wave is None and self.bandwidth is None:
                    bandinfo = SpectralRangeHandler.bandpass_wavelength_dictionary[bandenum]
                    self.central_wave = bandinfo['central_wave']
                    self.bandwidth = bandinfo['bandwidth']
            else:
                v.errors.append(
                    "Field \"band\" is invalid, or manually state the wavelength, frequency, or energy regime of your observation")

        if self.bandwidth is None or self.central_wave is None:
            v.errors.append(
                'Error Parsing Bandpass/Energy/Frequency information. Please refer to http://treasuremap.space/documentation for further assistance')
        elif self.band is None:
            self.band = SpectralRangeHandler.bandEnumFromCentralWaveBandwidth(self.central_wave, self.bandwidth)

        if function.pointing_crossmatch(self, otherpointings):
            v.errors.append("Pointing already submitted")

        # valid if no errors
        v.valid = len(v.errors) == 0
        return v


class pointing_event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pointingid = db.Column(db.Integer)
    graceid = db.Column(db.String)

    @property
    def json(self):
        return to_json(self, self.__class__)

    @property
    def parse(self):
        return parse_model(self, self.__class__)


class glade_2p3(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pgc_number = db.Column(db.Integer)
    position = db.Column(Geography('POINT', srid=4326))
    gwgc_name = db.Column(db.String)
    hyperleda_name = db.Column(db.String)
    _2mass_name = db.Column(db.String)
    sdssdr12_name = db.Column(db.String)
    distance = db.Column(db.Float)
    distance_error = db.Column(db.Float)
    redshift = db.Column(db.Float)
    bmag = db.Column(db.Float)
    bmag_err = db.Column(db.Float)
    bmag_abs = db.Column(db.Float)
    jmag = db.Column(db.Float)
    jmag_err = db.Column(db.Float)
    hmag = db.Column(db.Float)
    hmag_err = db.Column(db.Float)
    kmag = db.Column(db.Float)
    kmag_err = db.Column(db.Float)
    flag1 = db.Column(db.String(1))
    flag2 = db.Column(db.Integer)
    flag3 = db.Column(db.Integer)

    @property
    def json(self):
        return to_json(self, self.__class__)

    @property
    def parse(self):
        return parse_model(self, self.__class__)


class gw_alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    graceid = db.Column(db.String)
    alternateid = db.Column(db.String)
    role = db.Column(db.String)
    timesent = db.Column(db.DateTime)
    time_of_signal = db.Column(db.DateTime)
    packet_type = db.Column(db.Integer)
    alert_type = db.Column(db.String)
    detectors = db.Column(db.String)
    description = db.Column(db.String)
    far = db.Column(db.Float)
    skymap_fits_url = db.Column(db.String)
    distance = db.Column(db.Float)
    distance_error = db.Column(db.Float)
    prob_bns = db.Column(db.Float)
    prob_nsbh = db.Column(db.Float)
    prob_gap = db.Column(db.Float)
    prob_bbh = db.Column(db.Float)
    prob_terrestrial = db.Column(db.Float)
    prob_hasns = db.Column(db.Float)
    prob_hasremenant = db.Column(db.Float)
    datecreated = db.Column(db.DateTime)
    group = db.Column(db.String)
    centralfreq = db.Column(db.Float)
    duration = db.Column(db.Float)
    avgra = db.Column(db.Float)
    avgdec = db.Column(db.Float)
    observing_run = db.Column(db.String)
    pipeline = db.Column(db.String)
    search = db.Column(db.String)

    gcn_notice_id = db.Column(db.Integer)
    ivorn = db.Column(db.String)
    ext_coinc_observatory = db.Column(db.String)
    ext_coinc_search = db.Column(db.String)
    time_difference = db.Column(db.Float)
    time_coincidence_far = db.Column(db.Float)
    time_sky_position_coincidence_far = db.Column(db.Float)
    area_90 = db.Column(db.Float)
    area_50 = db.Column(db.Float)

    @staticmethod
    def from_json(args):
        akeys = args.keys()

        alert = gw_alert(
            graceid=args['graceid'] if 'graceid' in akeys else 'ERROR',
            alternateid=args['alternateid'] if 'alternateid' in akeys else '',
            role=args['role'] if 'role' in akeys else 'ERROR',
            observing_run=args['observing_run'] if 'observing_run' in akeys else 'ERROR',
            description=args['description'] if 'description' in akeys else 'ERROR',
            alert_type=args['alert_type'] if 'alert_type' in akeys else 'ERROR',
            datecreated=args['datecreated'] if 'datecreated' in akeys else datetime.datetime.now(),
            packet_type=args['packet_type'] if 'packet_type' in akeys else 0,
            far=args['far'] if 'far' in akeys else 0.0,
            group=args['group'] if 'group' in akeys else '',
            pipeline=args['pipeline'] if 'pipeline' in akeys else '',
            search=args['search'] if 'search' in akeys else '',
            detectors=args['detectors'] if 'detectors' in akeys else '',
            prob_hasns=args['prob_hasns'] if 'prob_hasns' in akeys else 0.0,
            prob_hasremenant=args['prob_hasremenant'] if 'prob_hasremenant' in akeys else 0.0,
            prob_gap=args['prob_gap'] if 'prob_gap' in akeys else 0.0,
            prob_bns=args['prob_bns'] if 'prob_bns' in akeys else 0.0,
            prob_nsbh=args['prob_nsbh'] if 'prob_nsbh' in akeys else 0.0,
            prob_bbh=args['prob_bbh'] if 'prob_bbh' in akeys else 0.0,
            prob_terrestrial=args['prob_terrestrial'] if 'prob_terrestrial' in akeys else 0.0,
            skymap_fits_url=args['skymap_fits_url'] if 'skymap_fits_url' in akeys else '',
            avgra=args['avgra'] if 'avgra' in akeys else 0.0,
            avgdec=args['avgdec'] if 'avgdec' in akeys else 0.0,
            time_of_signal=args['time_of_signal'] if 'time_of_signal' in akeys else datetime.datetime(year=1991,
                                                                                                      month=12, day=23),
            distance=args['distance'] if 'distance' in akeys else 0.0,
            distance_error=args['distance_error'] if 'distance_error' in akeys else 0.0,
            timesent=args['timesent'] if 'timesent' in akeys else datetime.datetime(year=1991, month=12, day=23),
            centralfreq=args['centralfreq'] if 'centralfreq' in akeys else 0.0,
            duration=args['duration'] if 'duration' in akeys else 0.0,
            area_90=args['area_90'] if 'area_90' in akeys else 0.0,
            area_50=args['area_50'] if 'area_50' in akeys else 0.0,
            gcn_notice_id=args['gcn_notice_id'] if 'gcn_notice_id' in akeys else 0,
            ivorn=args['ivorn'] if 'ivorn' in akeys else '',
            ext_coinc_observatory=args['ext_coinc_observatory'] if 'ext_coinc_observatory' in akeys else '',
            ext_coinc_search=args['ext_coinc_search'] if 'ext_coinc_search' in akeys else '',
            time_difference=args['time_difference'] if 'time_difference' in akeys else 0.0,
            time_coincidence_far=args['time_coincidence_far'] if 'time_coincidence_far' in akeys else 0.0,
            time_sky_position_coincidence_far=args[
                'time_sky_position_coincidence_far'] if 'time_sky_position_coincidence_far' in akeys else 0.0,
        )
        return alert

    def getClassification(self):

        if self.group == 'Burst':
            return 'None (detected as burst)'

        probs = [
            {"prob": self.prob_bns if self.prob_bns else 0.0, "class": "BNS"},
            {"prob": self.prob_nsbh if self.prob_nsbh else 0.0, "class": "NSBH"},
            {"prob": self.prob_bbh if self.prob_bbh else 0.0, "class": "BBH"},
            {"prob": self.prob_terrestrial if self.prob_terrestrial else 0.0, "class": "Terrestrial"},
            {"prob": self.prob_gap if self.prob_gap else 0.0, "class": "Mass Gap"}
        ]

        sorted_probs = sorted([x for x in probs if x['prob'] > 0.01], key=lambda i: i['prob'], reverse=True)

        classification = ""
        for p in sorted_probs:
            classification += p["class"] + ": (" + str(round(100 * p['prob'], 1)) + "%) "

        return classification

    @property
    def json(self):
        return to_json(self, self.__class__)

    @property
    def parse(self):
        return parse_model(self, self.__class__)

    @staticmethod
    def graceidfromalternate(graceid):
        # if there is an input alternate id for this event, it will find the original graceid
        # else it will return the input graceid

        alternateids = db.session.query(gw_alert).filter(
            gw_alert.alternateid == graceid
        ).all()

        if len(alternateids):
            graceid = alternateids[0].graceid

        return graceid

    @staticmethod
    def alternatefromgraceid(graceid):

        alternateids = db.session.query(gw_alert).filter(
            gw_alert.graceid == graceid,
            gw_alert.alternateid != "",
            gw_alert.alternateid is not None
        ).all()
        if len(alternateids):
            graceid = alternateids[0].alternateid

        return graceid


class gw_galaxy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    graceid = db.Column(db.String)
    galaxy_catalog = db.Column(db.Integer)
    galaxy_catalogID = db.Column(db.Integer)

    @property
    def json(self):
        return to_json(self, self.__class__)


class event_galaxy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    graceid = db.Column(db.String)
    galaxy_catalog = db.Column(db.Integer)
    galaxy_catalogID = db.Column(db.Integer)

    @property
    def json(self):
        return to_json(self, self.__class__)

    @property
    def parse(self):
        return parse_model(self, self.__class__)


class gw_galaxy_score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gw_galaxyID = db.Column(db.Integer)
    score_type = db.Column(db.Enum(enums.gw_galaxy_score_type))
    score = db.Column(db.Float)

    @property
    def json(self):
        return to_json(self, self.__class__)

    @property
    def parse(self):
        return parse_model(self, self.__class__)


class doi_author_group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.Integer)
    name = db.Column(db.String)

    @property
    def json(self):
        return to_json(self, self.__class__)

    @property
    def parse(self):
        return parse_model(self, self.__class__)


class doi_author(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    affiliation = db.Column(db.String)
    orcid = db.Column(db.String)
    gnd = db.Column(db.String)
    pos_order = db.Column(db.Integer)
    author_groupid = db.Column(db.Integer)

    @property
    def json(self):
        return to_json(self, self.__class__)

    @property
    def parse(self):
        return parse_model(self, self.__class__)

    @staticmethod
    def construct_creators(doi_group_id, userid):

        if isInt(doi_group_id):
            authors = db.session.query(doi_author).filter(
                doi_author.author_groupid == int(doi_group_id),
                doi_author.author_groupid == doi_author_group.id,
                doi_author_group.userid == userid
            ).order_by(
                doi_author.id
            ).all()
        else:
            authors = db.session.query(doi_author).filter(
                doi_author.author_groupid == doi_author_group.id,
                doi_author_group.name == doi_group_id,
                doi_author_group.userid == userid
            ).order_by(
                doi_author.id
            ).all()

        if len(authors) == 0:
            return False, []

        creators = []
        for a in authors:
            a_dict = {"name": a.name, "affiliation": a.affiliation}
            if a.orcid:
                a_dict['orcid'] = a.orcid
            if a.gnd:
                a_dict['gnd'] = a.gnd
            creators.append(a_dict)

        return True, creators

    @staticmethod
    def authors_from_page(form):
        authors = []
        for aid, an, aff, orc, gnd in zip(
                form.getlist('author_id'),
                form.getlist('author_name'),
                form.getlist('affiliation'),
                form.getlist('orcid'),
                form.getlist('gnd')
        ):

            if str(aid) == "" or str(aid) == "None":
                authors.append(
                    doi_author(
                        name=an,
                        affiliation=aff,
                        orcid=orc,
                        gnd=gnd
                    )
                )
            else:
                authors.append(
                    doi_author(
                        id=int(aid),
                        name=an,
                        affiliation=aff,
                        orcid=orc,
                        gnd=gnd
                    )
                )
        return authors


class gw_galaxy_list(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    graceid = db.Column(db.String)
    groupname = db.Column(db.String)
    submitterid = db.Column(db.Integer)
    reference = db.Column(db.String)
    alertid = db.Column(db.String)
    doi_url = db.Column(db.String(100))
    doi_id = db.Column(db.Integer)

    @property
    def json(self):
        return to_json(self, self.__class__)

    @property
    def parse(self):
        return parse_model(self, self.__class__)


class gw_galaxy_entry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    listid = db.Column(db.Integer)
    name = db.Column(db.String)
    score = db.Column(db.Float)
    position = db.Column(Geography('POINT', srid=4326))
    rank = db.Column(db.Integer)
    info = db.Column(db.JSON)

    @property
    def json(self):
        return to_json(self, self.__class__)

    @property
    def parse(self):
        return parse_model(self, self.__class__)

    def from_json(self, p):  # dbusers):
        v = valid_mapping()

        if 'position' in p:
            pos = p['position']
            if all([x in pos for x in ["POINT", "(", ")", " "]]) and "," not in pos:
                self.position = p['position']
            else:
                v.errors.append(
                    "Invalid position argument. Must be decimal format ra/RA, dec/DEC, or geometry type \"POINT(RA DEC)\"")
        else:
            if 'ra' in p or 'RA' in p:
                ra = p['ra'] if 'ra' in p else p['RA']
                if not isFloat(ra):
                    ra = None
            else:
                ra = None

            if 'dec' in p or 'DEC' in p:
                dec = p['dec'] if 'dec' in p else p['DEC']
                if not isFloat(dec):
                    dec = None
            else:
                dec = None

            if ra is None or dec is None:
                v.errors.append(
                    "Invalid position argument. Must be decimal format ra/RA, dec/DEC, or geometry type \"POINT(RA, DEC)\"")
            else:
                self.position = "POINT(" + str(ra) + " " + str(dec) + ")"

        if 'score' in p:
            if isFloat(p['score']):
                self.score = p['score']
            else:
                v.errors.append('Invalid score. Must be decimal')
        else:
            v.errors.append("\'score\' is required")

        if 'name' in p:
            self.name = p['name']
        else:
            v.errors.append("\'name\' is required for each galaxy in list")

        if 'rank' in p:
            if isInt(p['rank']):
                self.rank = p['rank']
            else:
                v.errors.append('Invalid rank. Must be Integer')
        else:
            v.errors.append("\'rank\' is required for each galaxy in list")

        if 'info' in p:
            self.info = p['info']

        v.valid = len(v.errors) == 0
        return v


class icecube_notice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ref_id = db.Column(db.String)
    graceid = db.Column(db.String)
    alert_datetime = db.Column(db.DateTime)
    datecreated = db.Column(db.DateTime)
    observation_start = db.Column(db.DateTime)
    observation_stop = db.Column(db.DateTime)
    pval_generic = db.Column(db.Float)
    pval_bayesian = db.Column(db.Float)
    most_probable_direction_ra = db.Column(db.Float)
    most_probable_direction_dec = db.Column(db.Float)
    flux_sens_low = db.Column(db.Float)
    flux_sens_high = db.Column(db.Float)
    sens_energy_range_low = db.Column(db.Float)
    sens_energy_range_high = db.Column(db.Float)

    @property
    def json(self):
        return to_json(self, self.__class__)

    @property
    def parse(self):
        return parse_model(self, self.__class__)

    @staticmethod
    def from_json(args):
        akeys = args.keys()

        notice = icecube_notice(
            graceid=args['graceid'] if 'graceid' in akeys else 'ERROR',
            ref_id=args['ref_id'] if 'ref_id' in akeys else 'ERROR',
            alert_datetime=args['alert_datetime'] if 'alert_datetime' in akeys else datetime.datetime(year=1991,
                                                                                                      month=12, day=23),
            observation_start=args['observation_start'] if 'observation_start' in akeys else datetime.datetime(
                year=1991, month=12, day=23),
            observation_stop=args['observation_stop'] if 'observation_stop' in akeys else datetime.datetime(year=1991,
                                                                                                            month=12,
                                                                                                            day=23),
            pval_generic=args['pval_generic'] if 'pval_generic' in akeys else 0.0,
            pval_bayesian=args['pval_bayesian'] if 'pval_bayesian' in akeys else 0.0,
            most_probable_direction_ra=args[
                'most_probable_direction_ra'] if 'most_probable_direction_ra' in akeys else 0.0,
            most_probable_direction_dec=args[
                'most_probable_direction_dec'] if 'most_probable_direction_dec' in akeys else 0.0,
            flux_sens_low=args['flux_sens_low'] if 'flux_sens_low' in akeys else 0.0,
            flux_sens_high=args['flux_sens_high'] if 'flux_sens_high' in akeys else 0.0,
            sens_energy_range_low=args['sens_energy_range_low'] if 'sens_energy_range_low' in akeys else 0.0,
            sens_energy_range_high=args['sens_energy_range_high'] if 'sens_energy_range_high' in akeys else 0.0,
            datecreated=args['datecreated'] if 'datecreated' in akeys else datetime.datetime.now(),
        )
        return notice

    def already_exists(self):
        other_notices = db.session.query(
            icecube_notice
        ).filter(
            icecube_notice.graceid == self.graceid,
            icecube_notice.observation_start == self.observation_start,
            icecube_notice.observation_stop == self.observation_stop,
            icecube_notice.pval_generic == self.pval_generic,
            icecube_notice.pval_bayesian == self.pval_bayesian,
            icecube_notice.most_probable_direction_ra == self.most_probable_direction_ra,
            icecube_notice.most_probable_direction_dec == self.most_probable_direction_dec
        ).all()

        if len(other_notices):
            return True
        return False


class icecube_notice_coinc_event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    icecube_notice_id = db.Column(db.Integer)
    datecreated = db.Column(db.DateTime)
    event_dt = db.Column(db.Float)
    ra = db.Column(db.Float)
    dec = db.Column(db.Float)
    containment_probability = db.Column(db.Float)
    event_pval_generic = db.Column(db.Float)
    event_pval_bayesian = db.Column(db.Float)
    ra_uncertainty = db.Column(db.Float)
    uncertainty_shape = db.Column(db.String)

    @property
    def json(self):
        return to_json(self, self.__class__)

    @property
    def parse(self):
        return parse_model(self, self.__class__)

    @staticmethod
    def from_json(args):
        akeys = args.keys()

        event = icecube_notice_coinc_event(
            icecube_notice_id=args['icecube_notice_id'] if 'icecube_notice_id' in akeys else -999,
            event_dt=args['event_dt'] if 'event_dt' in akeys else 0.0,
            ra=args['ra'] if 'ra' in akeys else 0.0,
            dec=args['dec'] if 'dec' in akeys else 0.0,
            containment_probability=args['containment_probability'] if 'containment_probability' in akeys else 0.0,
            event_pval_generic=args['event_pval_generic'] if 'event_pval_generic' in akeys else 0.0,
            event_pval_bayesian=args['event_pval_bayesian'] if 'event_pval_bayesian' in akeys else 0.0,
            ra_uncertainty=args['ra_uncertainty'] if 'ra_uncertainty' in akeys else 0.0,
            uncertainty_shape=args['uncertainty_shape'] if 'uncertainty_shape' in akeys else 0.0,
            datecreated=args['datecreated'] if 'datecreated' in akeys else datetime.datetime.now(),
        )
        return event


class gw_candidate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    datecreated = db.Column(db.DateTime)
    submitterid = db.Column(db.Integer)
    graceid = db.Column(db.String)
    candidate_name = db.Column(db.String)
    tns_name = db.Column(db.String, nullable=True)
    tns_url = db.Column(db.String, nullable=True)
    position = db.Column(Geography('POINT', srid=4326))
    discovery_date = db.Column(db.DateTime)
    discovery_magnitude = db.Column(db.Float)
    magnitude_central_wave = db.Column(db.Float)
    magnitude_bandwidth = db.Column(db.Float)
    magnitude_unit = db.Column(db.Enum(enums.depth_unit))
    magnitude_bandpass = db.Column(db.Enum(enums.bandpass))
    associated_galaxy = db.Column(db.String, nullable=True)
    associated_galaxy_redshift = db.Column(db.Float, nullable=True)
    associated_galaxy_distance = db.Column(db.Float, nullable=True)

    @property
    def json(self):
        return to_json(self, self.__class__)

    @property
    def parse(self):
        return parse_model(self, self.__class__)

    def from_json(self, p, graceid, userid):
        self.datecreated = datetime.datetime.now()
        self.graceid = graceid
        self.submitterid = userid

        v = valid_mapping()

        if 'position' in p:
            pos = p['position']
            if all([x in pos for x in ["POINT", "(", ")", " "]]) and "," not in pos:
                self.position = p['position']
            else:
                v.errors.append(
                    "Invalid position argument. Must be decimal format ra/RA, dec/DEC, or geometry type \"POINT(RA DEC)\"")
        else:
            if 'ra' in p or 'RA' in p:
                ra = p['ra'] if 'ra' in p else p['RA']
                if not isFloat(ra):
                    ra = None
            else:
                ra = None

            if 'dec' in p or 'DEC' in p:
                dec = p['dec'] if 'dec' in p else p['DEC']
                if not isFloat(dec):
                    dec = None
            else:
                dec = None

            if ra is None or dec is None:
                v.errors.append(
                    "Invalid position argument. Must be decimal format ra/RA, dec/DEC, or geometry type \"POINT(RA, DEC)\"")
            else:
                self.position = "POINT(" + str(ra) + " " + str(dec) + ")"

        if 'candidate_name' in p:
            candidate_name = p["candidate_name"]
            if isinstance(candidate_name, str):
                self.candidate_name = candidate_name
            else:
                v.errors.append("Invalid \'candidate_name\' type. Must be str")
        else:
            v.errors.append("Error: \'candidate_name\' is required")

        if 'tns_name' in p:
            tns_name = p["tns_name"]
            if isinstance(tns_name, str):
                self.tns_name = tns_name
            else:
                v.errors.append("Invalid \'tns_name\' type. Must be str")
        if 'tns_url' in p:
            tns_url = p['tns_url']
            if isinstance(tns_url, str):
                if not function.is_str_empty_or_None(tns_url):
                    if "https://www.wis-tns.org/object/" not in tns_url:
                        v.errors.append(
                            "Invalid \'tns_url\'. Must contain following format: https://www.wis-tns.org/object/\\{tns_name\\}")
                    else:
                        self.tns_url = tns_url
            else:
                v.errors.append("Invalid \'tns_url\' type. Must be str")

        if 'associated_galaxy' in p:
            associated_galaxy = p['associated_galaxy']
            if isinstance(associated_galaxy, str):
                self.associated_galaxy = associated_galaxy
            else:
                v.errors.append("Invalid format for \'associated_galaxy\'. Must be str")

        if 'associated_galaxy_redshift' in p:
            associated_galaxy_redshift = p['associated_galaxy_redshift']
            if isinstance(associated_galaxy_redshift, float):
                self.associated_galaxy_redshift = associated_galaxy_redshift
            else:
                v.warnings.append("Invalid format for \'associated_galaxy_redshift\'. Must be float")

        if 'associated_galaxy_distance' in p:
            associated_galaxy_distance = p['associated_galaxy_distance']
            if isinstance(associated_galaxy_distance, float):
                self.associated_galaxy_distance = associated_galaxy_distance
            else:
                v.warnings.append("Invalid format for \'associated_galaxy_distance\'. Must be float")

        if 'discovery_date' in p:
            try:
                self.discovery_date = date_parse(p['discovery_date'])
            except:  # noqa: E722
                v.errors.append(
                    "Error parsing \'discovery_date\'. Should be %Y-%m-%dT%H:%M:%S.%f format. e.g. 2019-05-01T12:00:00.00")
        else:
            v.errors.append("Error: \'discovery_date\' is required")

        if 'discovery_magnitude' in p:
            discovery_magnitude = p['discovery_magnitude']
            if isFloat(discovery_magnitude):
                self.discovery_magnitude = discovery_magnitude
            else:
                v.errors.append("Error: Invalid \'discovery_magnitude\' type. Must be float")
        else:
            v.errors.append("Error: \'discovery_mag\' is required")

        if 'magnitude_unit' in p:
            mu = p['magnitude_unit']
            validdepthunit = [int(b) for b in enums.depth_unit]
            validdepthunitstr = [str(b.name) for b in enums.depth_unit]
            if mu in validdepthunit or mu in validdepthunitstr:
                duenum = [d for d in enums.depth_unit if int(d) == mu or str(d.name) == mu][0]
                self.magnitude_unit = duenum
            else:
                v.errors.append(
                    'Invalid magnitude_unit. Must be \'ab_mag\', \'vega_mag\', \'flux_erg\', or \'flux_jy\'')
        else:
            v.errors.append('magnitude_unit is required')

        if "wavelength_regime" in p and "wavelength_unit" in p:
            try:
                regime = None
                in_regime = p["wavelength_regime"]
                if isinstance(in_regime, str):
                    regime = str(p['wavelength_regime']).split('[')[1].split(']')[0].split(',')
                elif isinstance(in_regime, list):
                    regime = in_regime

                if regime:
                    wave_min, wave_max = float(regime[0]), float(regime[1])

                    validwavelengthunits_ints = [int(b) for b in enums.wavelength_units]
                    validwavelengthunits_str = [str(b.name) for b in enums.wavelength_units]
                    user_unit = p['wavelength_unit']

                    if user_unit in validwavelengthunits_ints or user_unit in validwavelengthunits_str:
                        wuenum = [w for w in enums.wavelength_units if int(w) == user_unit or str(w.name) == user_unit][
                            0]
                        scale = enums.wavelength_units.get_scale(wuenum)
                        wave_min = wave_min * scale
                        wave_max = wave_max * scale

                        self.magnitude_bandwidth = 0.5 * (wave_max - wave_min)
                        self.magnitude_central_wave = wave_min + self.magnitude_bandwidth
                        self.band = SpectralRangeHandler.bandEnumFromCentralWaveBandwidth(self.magnitude_central_wave,
                                                                                          self.magnitude_bandwidth)
                        p['band'] = self.magnitude_bandwidth
                    else:
                        v.errors.append(
                            'Error: \'wavelength_unit\' is required, valid units are \'angstrom\', \'nanometer\', and \'micron\'')
            except:  # noqa: E722
                v.errors.append('Error parsing \'wavelength_regime\'. required format is a list: \'[low, high]\'')

        if "frequency_regime" in p and "frequency_unit" in p:
            try:
                regime = None
                in_regime = p["frequency_regime"]
                if isinstance(in_regime, str):
                    regime = str(p['frequency_regime']).split('[')[1].split(']')[0].split(',')
                elif isinstance(in_regime, list):
                    regime = in_regime

                if regime:
                    min_freq, max_freq = float(regime[0]), float(regime[1])

                    validfrequnits_ints = [int(b) for b in enums.frequency_units]
                    validfrequnits_str = [str(b.name) for b in enums.frequency_units]
                    user_unit = p['frequency_unit']

                    if user_unit in validfrequnits_ints or user_unit in validfrequnits_str:
                        fuenum = [w for w in enums.frequency_units if int(w) == user_unit or str(w.name) == user_unit][
                            0]
                        scale = enums.frequency_units.get_scale(fuenum)
                        min_freq = min_freq * scale
                        max_freq = max_freq * scale

                        self.magnitude_central_wave, self.magnitude_bandwidth = SpectralRangeHandler.wavefromFrequencyRange(
                            min_freq, max_freq)
                        self.magnitude_bandpass = SpectralRangeHandler.bandEnumFromCentralWaveBandwidth(
                            self.magnitude_central_wave, self.magnitude_bandwidth)
                        p['magnitude_bandpass'] = self.magnitude_bandpass
                    else:
                        v.errors.append(
                            'Frequency Unit is required, valid units are \'Hz\', \'kHz\', \'MHz\', \'GHz\', and \'THz\'')
            except:  # noqa: E722
                v.errors.apend('Error parsing \'frequency_regime\'. required format is a list: \'[low, high]\'')

        if "energy_regime" in p and "energy_unit" in p:
            try:
                regime = None
                in_regime = p["energy_regime"]
                if isinstance(in_regime, str):
                    regime = str(p['energy_regime']).split('[')[1].split(']')[0].split(',')
                elif isinstance(in_regime, list):
                    regime = in_regime

                if regime:
                    min_energy, max_energy = float(regime[0]), float(regime[1])

                    validenergyunits_ints = [int(b) for b in enums.energy_units]
                    validenergyunits_str = [str(b.name) for b in enums.energy_units]
                    user_unit = p['energy_unit']

                    if user_unit in validenergyunits_ints or user_unit in validenergyunits_str:
                        euenum = [w for w in enums.energy_units if int(w) == user_unit or str(w.name) == user_unit][0]
                        scale = enums.energy_units.get_scale(euenum)
                        min_energy = min_energy * scale
                        max_energy = max_energy * scale

                        self.magnitude_central_wave, self.magnitude_bandwidth = SpectralRangeHandler.wavefromEnergyRange(
                            min_energy, max_energy)
                        self.magnitude_bandpass = SpectralRangeHandler.bandEnumFromCentralWaveBandwidth(
                            self.magnitude_central_wave, self.magnitude_bandwidth)
                        p['magnitude_bandpass'] = self.magnitude_bandpass
                    else:
                        v.errors.append(
                            '\'energy_unit\' is required, valid units are \'eV\', \'keV\', \'MeV\', \'GeV\', and \'TeV\'')
            except:  # noqa: E722
                v.errors.apend('Error parsing \'energy_regime\'. required format is a list: \'[low, high]\'')
            pass

        if 'magnitude_central_wave' in p:
            magnitude_central_wave = p['magnitude_central_wave']
            if isFloat(magnitude_central_wave):
                self.magnitude_central_wave = magnitude_central_wave
            else:
                v.errors.append('Error parsing \'magnitude_central_wave\'. required format is decimal')

        if 'magnitude_bandwidth' in p:
            magnitude_bandwidth = p['magnitude_bandwidth']
            if isFloat(magnitude_bandwidth):
                self.magnitude_bandwidth = magnitude_bandwidth
            else:
                v.errors.append('Error parsing \'magnitude_bandwidth\'. required format is decimal')

        if "magnitude_bandpass" in p:
            validbandints = [int(b) for b in enums.bandpass]
            validbandstr = [str(b.name) for b in enums.bandpass]
            userband = p['magnitude_bandpass']
            if userband in validbandints or userband in validbandstr:
                bandenum = [b for b in enums.bandpass if userband == int(b) or userband == str(b.name)][0]
                self.magnitude_bandpass = userband
                if self.magnitude_central_wave is None and self.magnitude_bandwidth is None:
                    bandinfo = SpectralRangeHandler.bandpass_wavelength_dictionary[bandenum]
                    self.magnitude_central_wave = bandinfo['central_wave']
                    self.magnitude_bandwidth = bandinfo['bandwidth']
            else:
                v.errors.append(
                    "Field \"magnitude_bandpass\" is invalid, or manually state the wavelength, frequency, or energy regime of your observation")

        if self.magnitude_bandwidth is None or self.magnitude_central_wave is None:
            v.errors.append(
                'Error Parsing Bandpass/Energy/Frequency information. Please refer to http://treasuremap.space/documentation for further assistance')
        elif self.magnitude_bandpass is None:
            self.magnitude_bandpass = SpectralRangeHandler.bandEnumFromCentralWaveBandwidth(self.magnitude_central_wave,
                                                                                            self.magnitude_bandwidth)

        # valid if no errors
        v.valid = len(v.errors) == 0
        return v
