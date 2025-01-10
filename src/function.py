
import numpy as np
import ephem
import urllib
import astropy.io.fits as astro_fits
import datetime
import math
import tempfile
import os
import geoalchemy2
import json
import io
import requests

from numpy import genfromtxt
from bs4 import BeautifulSoup
from shapely.geometry import Polygon
from shapely.geometry import Point
from urllib.request import urlopen

from src import app
from src import mail
from . import enums



class overlay():
	def __init__(self, name, color, contours):
		self.name = name
		self.color = color
		self.contours = contours


def readconfig(directory,_file):
    data=genfromtxt(directory+_file,str)
    gg={}
    for i in data:
        try:
            gg[i[0]]=eval(i[1])
        except:  # noqa: E722
            gg[i[0]]=i[1]
    return gg


def isInt(i):
	try:
		_ = int(i)
		return True
	except:  # noqa: E722
		return False


def isFloat(i):
	try:
		_ = float(i)
		return True
	except:  # noqa: E722
		return False


def floatNone(i):
    if i is not None:
        try:
            return float(i)
        except:  # noqa: E722
            return 0.0
    else:
        return None


def is_str_empty_or_None(i: str):
    if i and len(i):
        return False
    else:
        return True




def project(footprint, _ra, _dec):
        #footprint is a list of vertices points
        #   vertice points = [ra, dec]

        #_ra and _dec are the translated coordinates

        proj_footprint = []
        print(_ra, _dec)
        for p in footprint:
            print(p[0], p[1])
            if _dec >= 89:
                cosdec = 1
            else:
                cosdec = math.cos(math.radians(_dec))
            if p[0]+_ra > 360:
                  ra = 360 - (p[0]/cosdec) +_ra
            elif p[0]+_ra < 0:
                  ra = 360 + (p[0]/cosdec)+_ra
            else:
                ra = (p[0]/cosdec) + _ra

            if p[1]+_dec > 90:
                #ra = (ra + 180) % 360
                print("p[1] + dec > 90")
                dec = 90 - p[1]+_dec

            if p[1]+_dec < -90:
                #ra = (ra + 180) % 360
                print("p[1]+dec < -90")
                dec = -90 + p[1] + _dec
            else:
                print("else")
                dec = p[1] + _dec

            print(ra, dec)

            proj_footprint.append([ra, dec])
        return proj_footprint


def polygons2footprints(polygons, time_of_signal):
    #split list of poly corners into ra list and dec list
    footprints= []
    for polygon in polygons:
        if not isinstance(polygon[0], list): #type(polygon[0]) != list:
            polygon = [l.tolist() for l in polygon]  # noqa: E741
        footprints.append({'polygon':polygon, 'time':time_of_signal})
    return footprints


def sanatize_footprint_ccds(ccds):
	footprint_ccds = []
	for footprint in ccds:
		sanitized = footprint.strip('POLYGON ').strip(')(').split(',')
		polygon = []
		for vertex in sanitized:
			obj = vertex.split()
			ra = float(obj[0])
			dec = float(obj[1])
			polygon.append([ra,dec])
		footprint_ccds.append(polygon)
	return footprint_ccds


def sanatize_XRT_source_info(info):
    ret = "<p>"
    ret += "<b> Timestamp: </b>"+str(info['alert_timestamp'])+"<br>"
    ret += "<b> Identifier: </b>"+str(info['alert_identifier'])+"<br></p>"
    return ret


def sanatize_gal_info(entry, glist):
    ra, dec = sanatize_pointing(entry.position)
    ret = "<p>"
    ret = "<b> RA DEC: </b>"+str(round(ra,4))+" "+str(round(dec,4))+"<br>"
    ret += "<b>Score: </b>"+str(entry.score)+"<br>"
    ret += "<b>Rank: </b>"+str(entry.rank)+"<br>" 
    if glist.reference:
        ret+= f"<a href={glist.reference}>Reference</a> <br>"
    if glist.doi_url:
        ret+= f"<a href={glist.doi_url}>DOI</a> <br>"
    ret+="</p><b>Other Information:</b><br><p>"
    for key in entry.info.keys():
        ret += "<b>"+str(key)+":</b> "+str(entry.info[key]).split('\n')[0]+"<br>"
    ret += "</p>"
    return ret


def sanatize_icecube_event(entry, notice):
    ret = "<p>"
    ret += "<b>RA DEC: </b>"+str(round(entry.ra,4))+" "+str(round(entry.dec,4))+"<br>"
    ret += "<b>Event dt: </b>"+str(entry.event_dt)+"<br>"
    ret += "<b>RA Uncertainty: </b>"+str(entry.ra_uncertainty)+"<br>" 
    ret += "<b>Containment Prob: </b>"+str(entry.containment_probability)+"<br>" 
    ret += "<b>Pval Gen: </b>"+str(entry.event_pval_generic)+"<br>" 
    ret += "<b>Pval Bayesian: </b>"+str(entry.event_pval_bayesian)+"<br>" 
    ret += "</p>"
    return ret


def sanatize_candidate_info(cand, ra: float, dec: float):
    ret = "<p><br>"
    ret += f"<b>RA DEC: </b>{str(round(ra,4))} {str(round(dec,4))}<br>"
    ret += f"<b>Discovery Date: </b>{cand.discovery_date}<br>"
    ret += f"<b>Magnitude: </b>{cand.discovery_magnitude}<br>"
    ret += f"<b>Central λ (A): </b>{cand.magnitude_central_wave}<br>"
    ret += f"<b>Bandwidth (A): </b>{cand.magnitude_bandwidth}<br>"
    ret += f"<b>Galaxy: </b>{cand.associated_galaxy}<br>"
    ret += f"<b>Redshift: </b>{cand.associated_galaxy_redshift}<br>"
    ret += f"<b>Distance: </b>{cand.associated_galaxy_distance}<br>"
    if cand.tns_url:
        ret += f"<br><a href=\"{cand.tns_url}\">TNS Source</a>"
    ret += "</p>"
    return ret


def sanatize_pointing(p):
    ra = float(p.split('(')[1].split(')')[0].split()[0])
    dec = float(p.split('(')[1].split(')')[0].split()[1])
    return ra,dec


def ra_dec_to_uvec(ra, dec):
    phi = np.deg2rad(90 - dec)
    theta = np.deg2rad(ra)
    x = np.cos(theta) * np.sin(phi)
    y = np.sin(theta) * np.sin(phi)
    z = np.cos(phi)
    return x, y, z


def uvec_to_ra_dec(x, y, z):
    r = np.sqrt(x**2 + y ** 2 + z ** 2)
    x /= r
    y /= r
    z /= r
    theta = np.arctan2(y, x)
    phi = np.arccos(z)
    dec = 90 - np.rad2deg(phi)
    if theta < 0:
        ra = 360 + np.rad2deg(theta)
    else:
        ra = np.rad2deg(theta)
    return ra, dec


def x_rot(theta_deg):
    theta = np.deg2rad(theta_deg)
    return np.matrix([
        [1, 0, 0],
        [0, np.cos(theta), -np.sin(theta)],
        [0, np.sin(theta), np.cos(theta)]
    ])


def y_rot(theta_deg):
    theta = np.deg2rad(theta_deg)
    return np.matrix([
        [np.cos(theta), 0, np.sin(theta)],
        [0, 1, 0],
        [-np.sin(theta), 0, np.cos(theta)]
    ])


def z_rot(theta_deg):
    theta = np.deg2rad(theta_deg)
    return np.matrix([
        [np.cos(theta), -np.sin(theta), 0],
        [np.sin(theta), np.cos(theta), 0],
        [0, 0, 1]
    ])


def project_footprint(footprint, ra, dec, pos_angle):
    if pos_angle is None:
        pos_angle = 0.0

    footprint_zero_center_ra = np.asarray([pt[0] for pt in footprint])
    footprint_zero_center_dec = np.asarray([pt[1] for pt in footprint])
    footprint_zero_center_uvec = ra_dec_to_uvec(footprint_zero_center_ra, footprint_zero_center_dec)
    footprint_zero_center_x, footprint_zero_center_y, footprint_zero_center_z = footprint_zero_center_uvec
    proj_footprint = []
    for idx in range(footprint_zero_center_x.shape[0]):
        vec = np.asarray([footprint_zero_center_x[idx], footprint_zero_center_y[idx], footprint_zero_center_z[idx]])
        new_vec = vec @ x_rot(-pos_angle) @ y_rot(dec) @ z_rot(-ra)
        new_x, new_y, new_z = new_vec.flat
        pt_ra, pt_dec = uvec_to_ra_dec(new_x, new_y, new_z)
        proj_footprint.append([pt_ra, pt_dec])
    return proj_footprint


def getDataFromTLE(datetime, tleLatOffset=0, tleLonOffset=0.21):
    # Get TLE and parse
    url = "https://celestrak.com/satcat/tle.php?CATNR=33053"
    data = urlopen(url)
    tle_raw=data.read()
    clean_tle = ''.join(BeautifulSoup(tle_raw, "html.parser").stripped_strings)
    tle_obj = clean_tle.split('\r\n')

    # Print age of TLE
    # year = "20"+tle_obj[1][18:20]
    # day = tle_obj[1][20:32]
    #print("\nTLE most recently updated "+year+"DOY"+ day)
    
    # Create spacecraft instance
    Fermi = ephem.readtle(tle_obj[0],tle_obj[1],tle_obj[2])
    
    # Create observer
    observer_Fermi = ephem.Observer()
    observer_Fermi.lat = '0'
    observer_Fermi.long = '0'
    
    # Initialize lists
    lat = []
    lon = []
    elevation = []
    
    # Iterate through time; compute predicted locations
    observer_Fermi.date = ephem.date(datetime)
    
    try:
        Fermi.compute(observer_Fermi)
    except:  # noqa: E722
        return False, False, False

    lat.append(np.degrees(Fermi.sublat.znorm))
    lon.append(np.degrees(Fermi.sublong.norm))
    elevation.append(Fermi.elevation)
    # Correct for inaccuracy
    lon = np.array(lon) - tleLonOffset
    lat = np.array(lat) - tleLatOffset
    
    if len(lon) == 1: # Return single value instead of array if length is 1
        lon = lon[0]
        lat = lat[0]
        elevation = elevation[0]

    #check if spacecraft is in South Atlantic Anomaly polygon, flat space projection for now.
    SAAlonvertices = [33.900, 12.398, -9.103, -30.605, -38.400, -45.000, -65.000, -84.000, -89.200, -94.300, -94.300, -86.100, 33.900 ]
    SAAlatvertices = [-30.000, -19.867, -9.733, 0.400, 2.000, 2.000, -1.000, -6.155, -8.880, -14.220, -18.404, -30.000, -30.000 ]
    SAApoly = Polygon(list(zip(SAAlonvertices,SAAlatvertices)))

    satpos = Point(-(360-lon),lat)
    inSAA = SAApoly.contains(satpos)
    if inSAA:
        return False,False,False

    return lon, lat, elevation

# convert degrees to deg:amin:asec
def deg2dm(deg):
    sign = np.sign(deg)
    deg = np.abs(deg)
    d = np.floor(deg)
    m = (deg - d) * 60
    return int(sign*d), m

def getGeoCenter(datetime, lon, lat):
    # Define the observer to be at the location of the spacecraft
    observer = ephem.Observer()

    # Convert the longitude to +E (-180 to 180)
    if lon > 180:
       lon = (lon % 180) - 180

    lon_deg, lon_min = deg2dm(lon)
    lat_deg, lat_min = deg2dm(lat)

    lon_string = '%s:%s' % (lon_deg, lon_min)
    lat_string = '%s:%s' % (lat_deg, lat_min)

    observer.lon = lon_string
    observer.lat = lat_string
    
    # Set the time of the observations
    observer.date = ephem.date(datetime)
    
    # Get the ra and dec (in radians) of the point in the sky at altitude = 90 (directly overhead)
    ra_zenith_radians, dec_zenith_radians = observer.radec_of('0', '90')
    
    # convert the ra and dec to degrees
    ra_zenith = np.degrees(ra_zenith_radians)
    dec_zenith = np.degrees(dec_zenith_radians)
    
    ra_geocenter =  (ra_zenith+180) % 360
    dec_geocenter = -1 * dec_zenith
    
    return ra_geocenter, dec_geocenter
    
def getearthsatpos(datetime):
    tleLonOffset=0.21
    tleLatOffset = 0

    try:
        lon, lat, elevation= getDataFromTLE(datetime, tleLatOffset=tleLatOffset, tleLonOffset=tleLonOffset)
    except:    # noqa: E722
        return False, False, False

    if not all([lon, lat, elevation]):
        return False, False, False

    # Get the geo center coordinates in ra and dec
    ra_geocenter, dec_geocenter = getGeoCenter(datetime, lon, lat)

    EARTH_RADIUS = 6378.140 * 1000 #in meters
    dtor = math.pi/180
    elev = elevation + EARTH_RADIUS
    earthsize_rad = np.arcsin(EARTH_RADIUS/elev)/dtor

    return ra_geocenter,dec_geocenter, earthsize_rad

def makeEarthContour(ra,dec,radius):
    thetas = np.linspace(0, -2*np.pi, 200)
    ras = radius * np.cos(thetas)
    decs = radius * np.sin(thetas)
    contour = np.c_[ras,decs]
    Earthcont = project_footprint(contour, ra, dec, 0)
    return Earthcont

def makeLATFoV(ra,dec,radius=65):
    thetas = np.linspace(0, -2*np.pi, 200)
    ras = radius * np.cos(thetas)
    decs = radius * np.sin(thetas)
    contour = np.c_[ras,decs]
    LATfov = project_footprint(contour, ra, dec, 0)
    return LATfov

def getFermiFT2file(timestamp):
    
    weekly_file_start = datetime.datetime(2008,8,7)
    base_week = 10
    day_diff = (timestamp - weekly_file_start).days
    week_diff = day_diff//7
    week = week_diff + base_week

    resp = urlopen("https://fermi.gsfc.nasa.gov/ssc/observations/timeline/ft2/files/")
    soup = BeautifulSoup(resp, from_encoding=resp.info().get_param('charset'), features="lxml")
    for link in soup.find_all('a', href=True):
        if 'FERMI' not in link['href'] or 'PRELIM' in link['href']:
            continue
        if int(link['href'].strip('FERMI_POINTING_FINAL').strip('_00.fits').split('_')[0]) == week:
            filename = (link['href'])
            
    url_base = 'https://fermi.gsfc.nasa.gov/ssc/observations/timeline/ft2/files/'
    pointing_file_url = url_base + filename
    
    try:
        resp = urlopen(pointing_file_url)
        exists = True
    except urllib.error.HTTPError:
        exists = False
        
    if not exists:
        raise ValueError('No Fermi FINAL pointing file found.')
    
    temp_dir = tempfile.mkdtemp()
    destination = os.path.join(temp_dir, filename)
    urllib.request.urlretrieve(pointing_file_url, destination)

    # return the location of the downloaded file
    return destination

def datetime2MET(timestamp):
    mettime=(timestamp-datetime.datetime(2001,1,1)).total_seconds()
    return mettime

def getFermiPointing(timestamp, theta_max=65, verbose=True):
    ft2file= getFermiFT2file(timestamp)

    # Open the FT2 file
    hdulist = astro_fits.open(ft2file)
    data = hdulist[1].data
    # Extract the spacecraft time
    tstart = data.field('start')
    tstop = data.field('stop')
    time = tstart + (tstop - tstart)/2.0

    trigger_met = datetime2MET(timestamp)

    if trigger_met is None:
        trigger_met = time[0]

    # Determine the index for the time closest to the triggertime
    index_closest = (np.abs(time - trigger_met)).argmin()   

    # Get the LAT pointing at the trigger time
    ra_lat_pointing = data.field('RA_SCZ')[index_closest]
    dec_lat_pointing = data.field('DEC_SCZ')[index_closest]

    if verbose:
        print("\nLAT Pointing @ %s (dt = %s seconds):\nRA = %s, Dec = %s\n" % (time[index_closest], time[index_closest]-trigger_met, ra_lat_pointing, dec_lat_pointing))

    return ra_lat_pointing, dec_lat_pointing


def pointing_crossmatch(pointing, otherpointings, dist_thresh=None):

	if dist_thresh is None:

		filtered_pointings = [x for x in otherpointings if (
			x.status.name == pointing.status and \
			x.instrumentid == int(pointing.instrumentid) and \
			x.band.name == pointing.band and \
			x.time == pointing.time and \
			x.pos_angle == floatNone(pointing.pos_angle)
		)]

		for p in filtered_pointings:
			p_pos = str(geoalchemy2.shape.to_shape(p.position))
			if sanatize_pointing(p_pos) == sanatize_pointing(pointing.position):
				return True

	else:

		p_ra, p_dec = sanatize_pointing(pointing.position)

		filtered_pointings = [x for x in otherpointings if (
			x.status.name == pointing.status and \
			x.instrumentid == int(pointing.instrumentid) and \
			x.band.name == pointing.band
		)]

		for p in filtered_pointings:
			ra, dec = sanatize_pointing(str(geoalchemy2.shape.to_shape(p.position)))
			sep = 206264.806*(float(ephem.separation((ra, dec ), (p_ra, p_dec))))
			if sep < dist_thresh:
				return True

	return False


def extract_polygon(p, scale):
	vertices = []
	errors = []
	try:
		for itera,line in enumerate(p.split('\r\n')):
			if line.strip() != "":
				splitlineconfusion = line.split('(')[1].split(')')[0].split(',')
				x = round(float(splitlineconfusion[0])*scale, 5)
				y = round(float(splitlineconfusion[1])*scale, 5)
				vertices.append([x, y])

	except Exception as e:
		errors.append("Error: " + str(e))
		errors.append("For line "+str(itera+1)+": "+line)
		errors.append("Please check the example for correct format")
		return [vertices, errors]

	if len(vertices) < 3:
		errors.append('Invalid Polygon. Must have more than 2 vertices')
		return [vertices, errors]

	if vertices[0] != vertices[len(vertices)-1]:
		vertices.append(vertices[0])

	return [vertices, errors]


def create_geography(vertices):
	geom = "POLYGON(("
	for v in vertices:
		geom += str(v[0])+" "+str(v[1])+", "
	geom = geom[0:len(geom)-2]
	geom += "))"
	return geom


def send_email(subject, recipients, html_body, attachments=[]):
	#msg = Message(subject, sender=sender, recipients=recipients)
	#msg.body = text_body
	#msg.html = html_body
	#with app.app_context():
	#	mail.send(msg)
    #mail.send_message("swyatt@email.arizona.edu", "This is a subject", 
    #        "app_mail working")
    mail.send_message(recipients, subject, html_body, attachments)


def send_account_validation_email(user, notify=True):
	send_email(
		"Treasure Map Account Verification",
		[user.email],
		"<p>Hello "+user.firstname+",<br><br> \
		Thank you for registering for The Gravitational Wave Treasure Map Project! Please follow this <a href=\"http://treasuremap.space/login?verification_key="+user.verification_key+"\">address</a> to verify your account. <br>\
		Please do not reply to this email<br><br> \
		Cheers from the Treasure Map team </p>",
	)
	if notify:
		send_email(
			"Treasure Map Account Verification",
			['swyatt@email.arizona.edu'],
			"<p>Hey Sam,<br><br> \
			New GWTM account registration: <br> \
			"+user.firstname+" "+user.lastname+" <br> \
			email: "+user.email+" <br> \
			username: "+user.username+" <br><br> \
			Cheers you beautiful bastard</p>",
		)


def send_password_reset_email(user):
	token = user.get_reset_password_token()
	send_email('GWTM Reset Your Password',
			   [user.email],
			   "<p>Dear "+user.username+",</p> \
				<p>\
				To reset your password \
				<a href=\"http://treasuremap.space/reset_password?token="+token+"&_external=True\"> \
				click here \
				</a>.\
				</p>\
				<p>Alternatively, you can paste the following link in your browser's address bar:</p>\
				<p>http://treasuremap.space/reset_password?token="+token+"&_external=True</p>\
				<p>If you have not requested a password reset simply ignore this message.</p>\
				<p>Sincerely,</p>\
				<p>The Treasure Map Team</p>"
	)


def create_pointing_doi(points, graceid, creators, insts):
    points_json = []

    for p in points:
        if p.status == enums.pointing_status.completed:
            points_json.append(p.parse)

    if len(insts) > 1:
        inst_str = "These observations were taken on the"
        for i in insts:
            if i == insts[len(insts)-1]:
                inst_str +=  " and " + i
            else:
                inst_str += " " + i + ","

        inst_str += " instruments."
    else:
        inst_str = "These observations were taken on the " + insts[0] + " instrument."

    if len(points_json):
        payload = {
            'data' : {
                "metadata": {
                    "title":"Submitted Completed pointings to the Gravitational Wave Treasure Map for event " + graceid,
                    "upload_type":"dataset",
                    "creators":creators,
                    "description":"Attached in a .json file is the completed pointing information for "+str(len(points_json))+" observation(s) for the EM counterpart search associated with the gravitational wave event " + graceid +". " + inst_str
                }
            },
            'data_file' : { 'name':'completed_pointings_'+graceid+'.json' },
            'files' : { 'file':io.StringIO(json.dumps(points_json)) },
            'headers' : { "Content-Type": "application/json" },
        }

        d_id, url = create_doi(payload)
        return d_id, url

    return None, None


def create_galaxy_score_doi(galaxies, creators, reference, graceid, alert_type):

    ref_str = '' if reference is None else "A reference to these calculations can be found here: {}".format(reference)

    gal_json = []

    for g in galaxies:
        gal_json.append(g.json)

    payload = {
        'data' : {
            "metadata": {
                "title":"Submitted Galaxy Scores to the Gravitational Wave Treasure Map for event {} {}".format(graceid, alert_type),
                "upload_type":"dataset",
                "creators":creators,
                "description":"Attached in a .json file is the ranked galaxy information within the contour region of the EM counterpart search associated with the gravitational wave event " + graceid +" "+alert_type+". "+ref_str
            }
        },
        'data_file' : { 'name':'event_galaxies_'+graceid+'.json' },
        'files' : { 'file':io.StringIO(json.dumps(gal_json)) },
        'headers' : { "Content-Type": "application/json" },
    }

    d_id, url = create_doi(payload)
    return d_id, url


def create_doi(payload):

    ACCESS_TOKEN = app.config['ZENODO_ACCESS_KEY']
    data = payload['data']
    data_file = payload['data_file']
    files = payload['files']
    headers = payload['headers']

    r = requests.post('https://zenodo.org/api/deposit/depositions', params={'access_token': ACCESS_TOKEN}, json={}, headers=headers)
    d_id = r.json()['id']
    r = requests.post('https://zenodo.org/api/deposit/depositions/%s/files' % d_id, params={'access_token': ACCESS_TOKEN}, data=data_file, files=files)
    r = requests.put('https://zenodo.org/api/deposit/depositions/%s' % d_id, data=json.dumps(data), params={'access_token': ACCESS_TOKEN}, headers=headers)
    r = requests.post('https://zenodo.org/api/deposit/depositions/%s/actions/publish' % d_id, params={'access_token': ACCESS_TOKEN})

    return_json = r.json()
    try:
        doi_url = return_json['doi_url']
    except:  # noqa: E722
        doi_url = None
    return int(d_id), doi_url


def validate_authors(authors):
	if len(authors) == 0:
		return False, "At least one author is required"
	for a in authors:
		if a.name is None or a.name == "":
			return False, "Author Name is required"
		if a.affiliation is None or a.affiliation == "":
			return False, "Affiliation is required"
	return True, ''


def by_chunk(items, chunk_size=1000):
    """
    Separate iterable objects by chunks

    For example:
    >>> by_chunk([1, 2, 3, 4, 5], chunk_size=2)
    >>> [[1, 2], [3, 4], [5]]

    Parameters
    ----------
    chunk_size: int
    items: Iterable

    Returns
    -------
    List
    """
    bucket = []
    for item in items:
        if len(bucket) >= chunk_size:
            yield bucket
            bucket = []
        bucket.append(item)
    yield bucket

def get_farrate_farunit(far):
    farrate = 1/far
    farunit = "s"
    if farrate > 86400:
        farunit = "days"
        farrate /= 86400
        if farrate > 365:
            farrate /= 365.25
            farunit = "years"
        elif farrate > 30:
            farrate /= 30
            farunit = "months"
        elif farrate > 7:
            farrate /= 7
            farunit = "weeks"
    
    return farrate, farunit