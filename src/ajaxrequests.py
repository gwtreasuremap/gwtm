# -*- coding: utf-8 -*-

import json
import numpy as np
import healpy as hp
import astropy
import plotly
import plotly.graph_objects as go
import requests
import urllib.parse
import pandas as pd
import tempfile
import time
import hashlib
import ligo.skymap.postprocess

import shapely.wkb
from werkzeug.exceptions import HTTPException

from flask import request, jsonify
from flask_login import current_user
from sqlalchemy import func, or_
from plotly.subplots import make_subplots
import shapely

from . import function
from . import models
from . import forms
from . import enums
from . import gwtm_io
from src import app
from src.gwtmconfig import config
#from .tasks import celery

db = models.db

global colors
colors = [
	"#000000", "#FFFF00", "#1CE6FF", "#FF34FF", "#FF4A46", "#008941", "#006FA6", "#A30059",
	"#FFDBE5", "#7A4900", "#0000A6", "#63FFAC", "#B79762", "#004D43", "#8FB0FF", "#997D87",
	"#5A0007", "#809693", "#FEFFE6", "#1B4400", "#4FC601", "#3B5DFF", "#4A3B53", "#FF2F80",
	"#61615A", "#BA0900", "#6B7900", "#00C2A0", "#FFAA92", "#FF90C9", "#B903AA", "#D16100",
	"#DDEFFF", "#000035", "#7B4F4B", "#A1C299", "#300018", "#0AA6D8", "#013349", "#00846F",
	"#372101", "#FFB500", "#C2FFED", "#A079BF", "#CC0744", "#C0B9B2", "#C2FF99", "#001E09",
	"#00489C", "#6F0062", "#0CBD66", "#EEC3FF", "#456D75", "#B77B68", "#7A87A1", "#788D66",
	"#885578", "#FAD09F", "#FF8A9A", "#D157A0", "#BEC459", "#456648", "#0086ED", "#886F4C",
	"#34362D", "#B4A8BD", "#00A6AA", "#452C2C", "#636375", "#A3C8C9", "#FF913F", "#938A81",
	"#575329", "#00FECF", "#B05B6F", "#8CD0FF", "#3B9700", "#04F757", "#C8A1A1", "#1E6E00",
	"#7900D7", "#A77500", "#6367A9", "#A05837", "#6B002C", "#772600", "#D790FF", "#9B9700",
	"#549E79", "#FFF69F", "#201625", "#72418F", "#BC23FF", "#99ADC0", "#3A2465", "#922329",
	"#5B4534", "#FDE8DC", "#404E55", "#0089A3", "#CB7E98", "#A4E804", "#324E72", "#6A3A4C",
	"#83AB58", "#001C1E", "#D1F7CE", "#004B28", "#C8D0F6", "#A3A489", "#806C66", "#222800",
	"#BF5650", "#E83000", "#66796D", "#DA007C", "#FF1A59", "#8ADBB4", "#1E0200", "#5B4E51",
	"#C895C5", "#320033", "#FF6832", "#66E1D3", "#CFCDAC", "#D0AC94", "#7ED379", "#012C58"
	]

#AJAX FUNCTIONS
@app.route('/ajax_alertinstruments_footprints')
def ajax_alertinstruments_footprints():
	args = request.args
	graceid = args.get('graceid')
	graceid = models.gw_alert.graceidfromalternate(graceid)
	pointing_status = args.get('pointing_status')
	tos_mjd= float(args.get('tos_mjd'))
	if pointing_status is None:
		pointing_status = enums.pointing_status.completed

	pointing_filter = []
	pointing_filter.append(models.pointing_event.graceid == graceid)
	pointing_filter.append(models.pointing_event.pointingid == models.pointing.id)
	if pointing_status == 'pandc':
		ors = []
		ors.append(models.pointing.status == enums.pointing_status.completed)
		ors.append(models.pointing.status == enums.pointing_status.planned)
		pointing_filter.append(or_(*ors))
	elif (pointing_status is not None and pointing_status != 'all' and pointing_status != ''):
		pointing_filter.append(models.pointing.status == pointing_status)

	pointing_info = db.session.query(
		models.pointing.id,
		models.pointing.instrumentid,
		models.pointing.pos_angle,
		models.pointing.time,
		func.ST_AsText(models.pointing.position).label('position'),
		models.pointing.band,
		models.pointing.depth,
		models.pointing.depth_unit,
		models.pointing.status
	).filter(*pointing_filter).all()

	haskeyids = [x.id for x in pointing_info]
	hashpointingids =  hashlib.sha1(json.dumps(haskeyids).encode()).hexdigest()

	cache_key = f'cache/footprint_{graceid}_{pointing_status}_{hashpointingids}'

	#temp_overlays = cache.get(cache_key)
	temp_overlays = gwtm_io.get_cached_file(cache_key, config)

	if  temp_overlays:
		inst_overlays = json.loads(temp_overlays)

	else:
		instrumentids = [x.instrumentid for x in pointing_info]

		instrumentinfo = db.session.query(
			models.instrument.instrument_name,
			models.instrument.nickname,
			models.instrument.id
		).filter(
			models.instrument.id.in_(instrumentids)
		).all()

		footprintinfo = db.session.query(
			func.ST_AsText(models.footprint_ccd.footprint).label('footprint'),
			models.footprint_ccd.instrumentid
		).filter(
			models.footprint_ccd.instrumentid.in_(instrumentids)
		).all()

		inst_overlays = []
		colorlist=['#ffe119', '#4363d8', '#f58231', '#42d4f4', '#f032e6', '#fabebe', '#469990', '#e6beff', '#9A6324', '#fffac8', '#800000', '#aaffc3', '#000075', '#a9a9a9']

		for i,inst in enumerate([x for x in instrumentinfo if x.id != 49]):
			name = inst.nickname if inst.nickname and inst.nickname != 'None' else inst.instrument_name
			try:
				color = colorlist[i]
			except:  # noqa: E722
				color = colors[inst.id]
				pass
			footprint_ccds = [x.footprint for x in footprintinfo if x.instrumentid == inst.id]
			sanatized_ccds = function.sanatize_footprint_ccds(footprint_ccds)
			inst_pointings = [x for x in pointing_info if x.instrumentid == inst.id]
			pointing_geometries = []

			for p in inst_pointings:
				t = astropy.time.Time([p.time])
				ra, dec = function.sanatize_pointing(p.position)

				for ccd in sanatized_ccds:
					pointing_footprint = function.project_footprint(ccd, ra, dec, p.pos_angle)
					pointing_geometries.append({
						"polygon":pointing_footprint,
						"time":round(t.mjd[0]-tos_mjd, 3)
					})

			inst_overlays.append({
				"display":True,
				"name":name,
				"color":color,
				"contours":pointing_geometries
			})

		#cache.set(cache_key, inst_overlays)
		gwtm_io.set_cached_file(cache_key, inst_overlays, config)
		
	return jsonify(inst_overlays)

@app.route('/ajax_alerttype')
def ajax_get_eventcontour():
	args = request.args
	urlid = args['urlid'].split('_')
	alertid = urlid[0]
	alertype= urlid[1]
	if len(urlid) > 2:
		alertype += urlid[2]

	alert = db.session.query(
		models.gw_alert
	).filter(
		models.gw_alert.id == int(alertid)
	).first()
	
	s3path = 'fit' if alert.role == 'observation' else 'test'

	if alert.far != 0:
		human_far, human_far_unit = function.get_farrate_farunit(alert.far)
		human_far=round(human_far,2)
		humanfar = "once per {} {}".format(str(round(human_far, 2)),human_far_unit)
	else:
		humanfar = ""

	if alert.time_coincidence_far != 0 and alert.time_coincidence_far is not None:
		time_coinc_farrate, time_coinc_farunit = function.get_farrate_farunit(alert.time_coincidence_far)
		time_coinc_farrate=round(time_coinc_farrate,2)
		human_time_coinc_far = "once per {} {}".format(str(round(time_coinc_farrate, 2)),time_coinc_farunit)
	else:
		human_time_coinc_far = ""

	if alert.time_sky_position_coincidence_far != 0 and alert.time_sky_position_coincidence_far is not None:
		time_skypos_coinc_farrate, time_skypos_coinc_farunit = function.get_farrate_farunit(alert.time_sky_position_coincidence_far)
		time_skypos_coinc_farrate=round(time_skypos_coinc_farrate,2)
		human_time_skypos_coinc_far = "once per {} {}".format(str(round(time_coinc_farrate, 2)),time_skypos_coinc_farunit)
	else:
		human_time_skypos_coinc_far = ""

	if alert.time_difference is not None:
		alert.time_difference = round(alert.time_difference, 3)

	if alert.distance is not None:
		alert.distance = round(alert.distance,3)
	else:
		alert.distance = ""
	if alert.distance_error is not None:
		alert.distance_error = round(alert.distance_error, 3)
	else:
		alert.distance = ""

	if alert.distance is not None and alert.distance_error is not None:
		distanceperror = "{} +/- {} Mpc".format(round(alert.distance, 3), round(alert.distance_error, 3))
	else:
		distanceperror = ''

	if alert.area_50 is not None:
		alert.area_50 = f"{round(alert.area_50, 3)} deg<sup>2</sup>"
	if alert.area_90 is not None:
		alert.area_90 = f"{round(alert.area_90, 3)} deg<sup>2</sup>"

	if alert.prob_bns is not None:
		alert.prob_bns = round(alert.prob_bns, 5)
	if alert.prob_nsbh is not None:
		alert.prob_nsbh = round(alert.prob_nsbh, 5)
	if alert.prob_gap is not None:
		alert.prob_gap = round(alert.prob_gap, 5)
	if alert.prob_bbh is not None:
		alert.prob_bbh = round(alert.prob_bbh, 5)
	if alert.prob_terrestrial is not None:
		alert.prob_terrestrial = round(alert.prob_terrestrial, 5)
	if alert.prob_hasns is not None:
		alert.prob_hasns = round(alert.prob_hasns, 5)
	if alert.prob_hasremenant is not None:
		alert.prob_hasremenant = round(alert.prob_hasremenant, 5)

	detection_overlays = []
	path_info = alert.graceid + '-' + alertype
	
	contourpath = f'{s3path}/'+path_info+'-contours-smooth.json'
	try:
		print(contourpath)
		_f = gwtm_io.download_gwtm_file(contourpath, source=config.STORAGE_BUCKET_SOURCE, config=config)
		contours_data = pd.read_json(_f)
		contour_geometry = []
		for contour in contours_data['features']:
			contour_geometry.extend(contour['geometry']['coordinates'])

		detection_overlays.append({
			"display":True,
			"name":"GW Contour",
			"color": '#e6194B',
			"contours":function.polygons2footprints(contour_geometry, 0)
		})
	except:  # noqa: E722
		print(f'No key: {contourpath}')
		pass

	payload = {
		'hidden_alertid':alertid,
		'detection_overlays':detection_overlays,
		'alert_group':alert.group,
		'alert_detectors':alert.detectors,
		'alert_time_of_signal':alert.time_of_signal,
		'alert_timesent':alert.timesent,
		'alert_human_far':humanfar,
		'alert_distance_plus_error':distanceperror,
		'alert_centralfreq':alert.centralfreq,
		'alert_duration':alert.duration,
		'alert_prob_bns':alert.prob_bns,
		'alert_prob_nsbh':alert.prob_nsbh,
		'alert_prob_gap':alert.prob_gap,
		'alert_prob_bbh':alert.prob_bbh,
		'alert_prob_terrestrial':alert.prob_terrestrial,
		'alert_prob_hasns':alert.prob_hasns,
		'alert_prob_hasremenant':alert.prob_hasremenant,
		'alert_area_50' : alert.area_50,
		'alert_area_90' : alert.area_90,
		'alert_avgra'   : alert.avgra,
		'alert_avgdec' : alert.avgdec,
		'alert_gcn_notice_id' : alert.gcn_notice_id,
		'alert_ivorn' : alert.ivorn,
		'alert_ext_coinc_observatory' : alert.ext_coinc_observatory ,
		'alert_ext_coinc_search' : alert.ext_coinc_search ,
		'alert_time_difference' : alert.time_difference ,
		'alert_time_coincidence_far' : human_time_coinc_far ,
		'alert_time_sky_position_coincidence_far' : human_time_skypos_coinc_far ,
		'selected_alert_type':alert.alert_type
	}

	return(jsonify(payload))


@app.route('/ajax_event_galaxies')
def ajax_event_galaxies():
	args = request.args
	alertid = args['alertid']
	event_galaxies = []

	galLists = db.session.query(models.gw_galaxy_list).filter(
		models.gw_galaxy_list.alertid == alertid,
	).all()
	galList_ids = list(set([x.id for x in galLists]))

	galEntries = db.session.query(
		models.gw_galaxy_entry.name,
		func.ST_AsText(models.gw_galaxy_entry.position).label('position'),
		models.gw_galaxy_entry.score,
		models.gw_galaxy_entry.info,
		models.gw_galaxy_entry.listid,
		models.gw_galaxy_entry.rank,
	).filter(
		models.gw_galaxy_entry.listid.in_(galList_ids)
	).all()

	for glist in galLists:
		markers = []
		entries = [x for x in galEntries if x.listid == glist.id]
		for e in entries:
			ra, dec = function.sanatize_pointing(e.position)
			markers.append({
				"name":e.name,
				"ra": ra,
				"dec": dec,
				"info":function.sanatize_gal_info(e, glist)
			})
		event_galaxies.append({
			"name":glist.groupname,
			"color":"",
			"markers":markers
		})

	return(jsonify(event_galaxies))


@app.route('/ajax_icecube_notice')
def ajax_icecube_notice():
	args = request.args
	graceid = args['graceid']
	return_events = []

	icecube_notices = db.session.query(models.icecube_notice).filter(
		models.icecube_notice.graceid == graceid
	)

	icecube_notice_ids = list(set([x.id for x in icecube_notices]))

	icecube_notice_events = db.session.query(
		models.icecube_notice_coinc_event
	).filter(
		models.icecube_notice_coinc_event.icecube_notice_id.in_(icecube_notice_ids)
	).all()

	for notice in icecube_notices:
		markers = []
		events = [x for x in icecube_notice_events if x.icecube_notice_id == notice.id]
		for i,e in enumerate(events):
			markers.append({
				"name":f"ICN_EVENT_{e.id}",
				"ra": e.ra,
				"dec": e.dec,
				"radius": e.ra_uncertainty,
				"info": function.sanatize_icecube_event(e, notice)
			})
		return_events.append({
			"name":f"ICECUBENotice{notice.id}",
			"color":"#324E72",
			"markers":markers
		})

	return(jsonify(return_events))


@app.route('/ajax_candidate')
def ajax_candidate_fetch():
	args = request.args
	graceid = args['graceid']
	graceid = models.gw_alert.graceidfromalternate(graceid)
	candidates = db.session.query(models.gw_candidate).filter(models.gw_candidate.graceid == graceid).all()

	markers = []
	payload = []
	for c in candidates:
		clean_position = shapely.wkb.loads(bytes(c.position.data), hex=True)
		ra, dec = function.sanatize_pointing(str(clean_position))

		markers.append({
			"name": c.candidate_name,
			"ra": ra,
			"dec": dec,
			"shape": "star",
			"info": function.sanatize_candidate_info(c, ra, dec)
		})
		
	if len(markers):
		payload.append({
			'name':'Candidates',
			'color':'',
			'markers':markers
		})
	return jsonify(payload)

@app.route('/ajax_scimma_xrt')
def ajax_scimma_xrt():
	args = request.args
	graceid = args['graceid']
	graceid = models.gw_alert.graceidfromalternate(graceid)

	if 'S190426' in graceid:
		graceid = 'S190426'

	keywords = {
			 'keyword':'',
			 'cone_search':'',
			 'polygon_search':'',
			 'alert_timestamp_after':'',
			 'alert_timestamp_before':'',
			 'role':'',
			 'event_trigger_number':graceid,
			 'ordering':'',
			 'page_size':1000,
	}
	base = 'http://skip.dev.hop.scimma.org/api/alerts/'
	url = '{}?{}'.format(base, urllib.parse.urlencode(keywords))
	r = requests.get(url)
	markers = []
	payload = []
	if r.status_code == 200:
		package = json.loads(r.text)['results']
		for p in package:
			markers.append(
				{
					'name':p['alert_identifier'],
					'ra':p['right_ascension'],
					'dec':p['declination'],
					'info':function.sanatize_XRT_source_info(p)
				}
			)
	else:
		print('something went wrong')

	if len(markers):
		payload.append({
			'name':'SCIMMA XRT Sources',
			'color':'',
			'markers':markers
		})

	return jsonify(payload)


@app.route('/ajax_resend_verification_email')
def ajax_resend_verification_email():
	userid = current_user.id
	user = models.users.query.filter_by(id=userid).first()
	function.send_account_validation_email(user, notify=False)
	return jsonify('')


@app.route('/ajax_request_doi')
def ajax_request_doi():
	args = request.args
	graceid = args['graceid']
	graceid = models.gw_alert.alternatefromgraceid(graceid)
	if args['ids'] != '':
		ids = [int(x) for x in args['ids'].split(',')]

		points = db.session.query(
			models.pointing
		).filter(
			models.pointing_event.pointingid == models.pointing.id,
			models.pointing.id.in_(ids),
			models.pointing_event.graceid == graceid
		).all()

		user = db.session.query(models.users).filter(models.users.id == current_user.get_id()).first()

		if 'doi_group_id' in args:
			valid, creators = models.doi_author.construct_creators(args['doi_group_id'], current_user.get_id())
			if not valid:
				creators = [{ 'name':str(user.firstname) + ' ' + str(user.lastname) }]
		else:
			creators = [{ 'name':str(user.firstname) + ' ' + str(user.lastname) }]


		insts = db.session.query(models.instrument).filter(models.instrument.id.in_([x.instrumentid for x in points]))
		inst_set = list(set([x.instrument_name for x in insts]))

		doi_url = args.get('doi_url')
		if doi_url:
			doi_id, doi_url = 0, doi_url
		else:
			doi_id, doi_url = function.create_pointing_doi(points, graceid, creators, inst_set)

		for p in points:
			p.doi_url = doi_url
			p.doi_id = doi_id

		db.session.commit()

		return jsonify(doi_url)


	return jsonify('')


def calc_prob_coverage(debug, graceid, mappathinfo, inst_cov, band_cov, depth, depth_unit, approx_cov, cache_key, slow, shigh, stype):

	approx_cov = True
	ztfid = 47 
	ztf_approx_id = 76
	decamid = 38
	decam_approx_id = 98
	
	approx_dict = {
		ztfid: ztf_approx_id,
		decamid: decam_approx_id
	}

	areas = []
	times = []
	probs = []

	#try:
	with tempfile.NamedTemporaryFile() as f:
		tmpdata = gwtm_io.download_gwtm_file(mappathinfo, source=config.STORAGE_BUCKET_SOURCE, config=config, decode=False)
		f.write(tmpdata)
		GWmap = hp.read_map(f.name)
		nside = hp.npix2nside(len(GWmap))
	#except:
	#	raise HTTPException('Calculator ERROR: Map not found. Please contact the administrator.')

	pointing_filter = []
	pointing_filter.append(models.pointing_event.graceid == graceid)
	pointing_filter.append(models.pointing.status == 'completed')
	pointing_filter.append(models.pointing_event.pointingid == models.pointing.id)
	pointing_filter.append(models.pointing.instrumentid != 49)

	if inst_cov != '':
		insts_cov = [int(x) for x in inst_cov.split(',')]
		pointing_filter.append(models.pointing.instrumentid.in_(insts_cov))
	#if band_cov != '':
	#	bands_cov = [x for x in band_cov.split(',')]
	#	pointing_filter.append(models.pointing.band.in_(bands_cov))
	if depth_unit != 'None' and depth_unit != '':
		pointing_filter.append(models.pointing.depth_unit == depth_unit)
	if depth is not None and function.isFloat(depth):
		if 'mag' in depth_unit:
			pointing_filter.append(models.pointing.depth >= float(depth))
		elif 'flux' in depth_unit:
			pointing_filter.append(models.pointing.depth <= float(depth))
		else:
			raise HTTPException('Unknown depth unit.')

	if slow is not None and shigh is not None:
		pointing_filter.append(models.pointing.inSpectralRange(slow, shigh, stype))

	pointings_sorted = db.session.query(
		models.pointing.id,
		models.pointing.instrumentid,
		models.pointing.pos_angle,
		func.ST_AsText(models.pointing.position).label('position'),
		models.pointing.band,
		models.pointing.depth,
		models.pointing.time
	).filter(
		*pointing_filter
	).order_by(
		models.pointing.time.asc()
	).all()

	instrumentids = [x.instrumentid for x in pointings_sorted]

	for apid in approx_dict.keys():
		if apid in instrumentids:
			instrumentids.append(approx_dict[apid])

	#filter and query the relevant instrument footprints
	footprintinfo = db.session.query(
		func.ST_AsText(models.footprint_ccd.footprint).label('footprint'),
		models.footprint_ccd.instrumentid
	).filter(
		models.footprint_ccd.instrumentid.in_(instrumentids)
	).all()

	#get GW T0 time
	time_of_signal = db.session.query(
		models.gw_alert.time_of_signal
	).filter(
		models.gw_alert.graceid == graceid
	).filter(
		models.gw_alert.time_of_signal is not None
	).order_by(
		models.gw_alert.datecreated.desc()
	).first()[0]

	if time_of_signal is None:
		raise HTTPException("<i><font color='red'>ERROR: Please contact administrator</font></i>")

	qps = []
	qpsarea=[]

	NSIDE4area = 512 #this gives pixarea of 0.013 deg^2 per pixel
	pixarea = hp.nside2pixarea(NSIDE4area, degrees=True)

	for p in pointings_sorted:
		ra, dec = function.sanatize_pointing(p.position)

		if approx_cov:
			if p.instrumentid in approx_dict.keys():
				footprint_ccds = [x.footprint for x in footprintinfo if x.instrumentid == approx_dict[p.instrumentid]]
			else:
				footprint_ccds = [x.footprint for x in footprintinfo if x.instrumentid ==  p.instrumentid]
		else:
			footprint_ccds = [x.footprint for x in footprintinfo if x.instrumentid ==  p.instrumentid]

		sanatized_ccds = function.sanatize_footprint_ccds(footprint_ccds)

		for ccd in sanatized_ccds:
			pointing_footprint = function.project_footprint(ccd, ra, dec, p.pos_angle)


			ras_poly = [x[0] for x in pointing_footprint][:-1]
			decs_poly = [x[1] for x in pointing_footprint][:-1]
			xyzpoly = astropy.coordinates.spherical_to_cartesian(1, np.deg2rad(decs_poly), np.deg2rad(ras_poly))
			qp = hp.query_polygon(nside,np.array(xyzpoly).T, inclusive=True)
			qps.extend(qp)

			#do a separate calc just for area coverage. hardcode NSIDE to be high enough so sampling error low
			qparea = hp.query_polygon(NSIDE4area, np.array(xyzpoly).T, inclusive=True)
			qpsarea.extend(qparea)

			#deduplicate indices, so that pixels already covered are not double counted
			deduped_indices=list(dict.fromkeys(qps))
			deduped_indices_area = list(dict.fromkeys(qpsarea))

			area = pixarea * len(deduped_indices_area)

			prob = 0
			for ind in deduped_indices:
				prob += GWmap[ind]
			elapsed = p.time - time_of_signal
			elapsed = elapsed.total_seconds()/3600
			times.append(elapsed)
			probs.append(prob)
			areas.append(area)

	cache_file = {
		'times': times,
		'probs': probs,
		'areas': areas,
	}
	gwtm_io.set_cached_file(cache_key, cache_file, config)

	return times, probs, areas


def calc_renormalized_skymap(debug, graceid, mappathinfo, inst_cov, band_cov, depth, depth_unit, approx_cov, cache_key, slow, shigh, stype):

	approx_cov = True
	ztfid = 47 
	ztf_approx_id = 76
	decamid = 38
	decam_approx_id = 98
	
	approx_dict = {
		ztfid: ztf_approx_id,
		decamid: decam_approx_id
	}

	#try:
	with tempfile.NamedTemporaryFile() as f:
		tmpdata = gwtm_io.download_gwtm_file(mappathinfo, source=config.STORAGE_BUCKET_SOURCE, config=config, decode=False)
		f.write(tmpdata)
		skymap = hp.read_map(f.name)
		nside = hp.npix2nside(len(skymap))
	#except:
	#	raise HTTPException('Calculator ERROR: Map not found. Please contact the administrator.')

	pointing_filter = []
	pointing_filter.append(models.pointing_event.graceid == graceid)
	pointing_filter.append(models.pointing.status == 'completed')
	pointing_filter.append(models.pointing_event.pointingid == models.pointing.id)
	pointing_filter.append(models.pointing.instrumentid != 49)

	if inst_cov != '':
		insts_cov = [int(x) for x in inst_cov.split(',')]
		pointing_filter.append(models.pointing.instrumentid.in_(insts_cov))
	#if band_cov != '':
	#	bands_cov = [x for x in band_cov.split(',')]
	#	pointing_filter.append(models.pointing.band.in_(bands_cov))
	if depth_unit != 'None' and depth_unit != '':
		pointing_filter.append(models.pointing.depth_unit == depth_unit)
	if depth is not None and function.isFloat(depth):
		if 'mag' in depth_unit:
			pointing_filter.append(models.pointing.depth >= float(depth))
		elif 'flux' in depth_unit:
			pointing_filter.append(models.pointing.depth <= float(depth))
		else:
			raise HTTPException('Unknown depth unit.')

	if slow is not None and shigh is not None:
		pointing_filter.append(models.pointing.inSpectralRange(slow, shigh, stype))

	pointings_sorted = db.session.query(
		models.pointing.id,
		models.pointing.instrumentid,
		models.pointing.pos_angle,
		func.ST_AsText(models.pointing.position).label('position'),
		models.pointing.band,
		models.pointing.depth,
		models.pointing.time
	).filter(
		*pointing_filter
	).order_by(
		models.pointing.time.asc()
	).all()

	instrumentids = [x.instrumentid for x in pointings_sorted]

	for apid in approx_dict.keys():
		if apid in instrumentids:
			instrumentids.append(approx_dict[apid])

	#filter and query the relevant instrument footprints
	footprintinfo = db.session.query(
		func.ST_AsText(models.footprint_ccd.footprint).label('footprint'),
		models.footprint_ccd.instrumentid
	).filter(
		models.footprint_ccd.instrumentid.in_(instrumentids)
	).all()
	
	qps = []

        #add coordinate indices of all pointings
	for p in pointings_sorted:
		#convert ra, dec info into numerical data
		ra, dec = function.sanatize_pointing(p.position)

		#footprints of ccds for each instrument
		if approx_cov:
			if p.instrumentid in approx_dict.keys():
				footprint_ccds = [x.footprint for x in footprintinfo if x.instrumentid == approx_dict[p.instrumentid]]
			else:
				footprint_ccds = [x.footprint for x in footprintinfo if x.instrumentid ==  p.instrumentid]
		else:
			footprint_ccds = [x.footprint for x in footprintinfo if x.instrumentid ==  p.instrumentid]
                #convert footprint info into numerical data
		sanatized_ccds = function.sanatize_footprint_ccds(footprint_ccds)
		#project each ccd footprint onto the pointing
		for ccd in sanatized_ccds:
			pointing_footprint = function.project_footprint(ccd, ra, dec, p.pos_angle)

			#add footprint coordinates to pixel array
			ras_poly = [x[0] for x in pointing_footprint][:-1]
			decs_poly = [x[1] for x in pointing_footprint][:-1]
			xyzpoly = astropy.coordinates.spherical_to_cartesian(1, np.deg2rad(decs_poly), np.deg2rad(ras_poly))
			qp = hp.query_polygon(nside,np.array(xyzpoly).T, inclusive=True)
			qps.extend(qp)

			deduped_indices=list(dict.fromkeys(qps))
	
	skymap[deduped_indices] = 0
	normed_skymap = skymap/np.sum(skymap)
	normed_contours_json = calc_renormalized_skymap_contours(normed_skymap)
	
	cache_file = {
		'contours_json': normed_contours_json,
	}
	gwtm_io.set_cached_file(cache_key, cache_file, config)

	return normed_contours_json

def calc_renormalized_skymap_contours(normed_skymap):
	#generate map of confidence levels from skymap
	i = np.flipud(np.argsort(normed_skymap))
	cumsum = np.cumsum(normed_skymap[i])
	cls = np.empty_like(normed_skymap)
	cls[i] = cumsum * 100 #convert probability to percent
	#input ring-indexed healpix array to make ligo contours at 50%, 90%
	paths = list(ligo.skymap.postprocess.contour(cls, [50, 90], nest=False, degrees=True, simplify=True))

	#create json, where the "features" key holds a list of 2 contours
	contours_json = json.dumps({
		'type': 'FeatureCollection',
		'features': [
			{
				'type': 'Feature',
				'properties': {
					'credible_level': contour
				},
				'geometry': {
					'type': 'MultiLineString',
					'coordinates': path
				}
			}
			for contour, path in zip([50,90], paths)
		]
	})
	return contours_json


def generate_prob_plot(times, probs, areas):
	fig = make_subplots(specs=[[{"secondary_y": True}]])

	fig.add_trace(go.Scatter(x=times, y=[prob*100 for prob in probs],
						mode='lines',
						name='Probability'), secondary_y=False)
	fig.add_trace(go.Scatter(x=times, y=areas,
						mode='lines',
						name='Area'), secondary_y=True)
	fig.update_xaxes(title_text="Hours since GW T0")
	fig.update_yaxes(title_text="Percent of GW localization posterior covered", secondary_y=False)
	fig.update_yaxes(title_text="Area coverage (deg<sup>2</sup>)", secondary_y=True)
	coverage_div = plotly.offline.plot(fig,output_type='div',include_plotlyjs=False, show_link=False)

	return coverage_div


@app.route("/ajax_coverage_calculator", methods=['GET', 'POST'])
def plot_prob_coverage():
	start = time.time()

	debug = app.debug
	graceid = models.gw_alert.graceidfromalternate(request.args.get('graceid'))
	mappathinfo = request.args.get('mappathinfo')
	inst_cov = request.args.get('inst_cov')
	band_cov = request.args.get('band_cov')
	depth = request.args.get('depth_cov')
	depth_unit = request.args.get('depth_unit')
	approx_cov = int(request.args.get('approx_cov')) == 1
	spec_range_type = request.args.get('spec_range_type')
	spec_range_unit = request.args.get('spec_range_unit')
	spec_range_low = request.args.get('spec_range_low')
	spec_range_high = request.args.get('spec_range_high')
	slow, shigh = None, None
	specenum = None
	
	pointing_filter = []
	pointing_filter.append(models.pointing_event.graceid == graceid)
	pointing_filter.append(models.pointing.status == 'completed')
	pointing_filter.append(models.pointing_event.pointingid == models.pointing.id)
	pointing_filter.append(models.pointing.instrumentid != 49)

	if inst_cov != '':
		insts_cov = [int(x) for x in inst_cov.split(',')]
		pointing_filter.append(models.pointing.instrumentid.in_(insts_cov))
	#if band_cov != '':
	#	bands_cov = [x for x in band_cov.split(',')]
	#	pointing_filter.append(models.pointing.band.in_(bands_cov))
	if depth_unit != 'None' and depth_unit != '':
		pointing_filter.append(models.pointing.depth_unit == depth_unit)
	if depth is not None and function.isFloat(depth):
		if 'mag' in depth_unit:
			pointing_filter.append(models.pointing.depth >= float(depth))
		elif 'flux' in depth_unit:
			pointing_filter.append(models.pointing.depth <= float(depth))
		else:
			raise HTTPException('Unknown depth unit.')
		
	if spec_range_low not in ['', None] and spec_range_high not in ['', None]:
		if spec_range_type == 'wavelength':
			unit = [x for x in enums.wavelength_units if spec_range_unit == x.name][0]
			scale = enums.wavelength_units.get_scale(unit)
			slow, shigh = float(spec_range_low)*scale, float(spec_range_high)*scale
		if spec_range_type == 'energy':
			unit = [x for x in enums.energy_units if spec_range_unit == x.name][0]
			scale = enums.energy_units.get_scale(unit)
			slow, shigh = float(spec_range_low)*scale, float(spec_range_high)*scale
		if spec_range_type == 'frequency':
			unit = [x for x in enums.frequency_units if spec_range_unit == x.name][0]
			scale = enums.frequency_units.get_scale(unit)
			slow, shigh = float(spec_range_low)*scale, float(spec_range_high)*scale
			
		specenum = [x for x in models.SpectralRangeHandler.spectralrangetype if spec_range_type == x.name][0]
		pointing_filter.append(models.pointing.inSpectralRange(slow, shigh, specenum))

	pointings_sorted = db.session.query(
		models.pointing.id
	).filter(
		*pointing_filter
	).order_by(
		models.pointing.time.asc()
	).all()

	pointingids = [x.id for x in pointings_sorted]
	pointingids = sorted(pointingids)
	hashpointingids =  hashlib.sha1(json.dumps(pointingids).encode()).hexdigest()

	cache_key = f'cache/prob_{graceid}_{approx_cov}_{hashpointingids}'
	cache_file = gwtm_io.get_cached_file(cache_key, config)
	
	if cache_file is None:
		times, probs, areas = calc_prob_coverage(debug, graceid, mappathinfo, inst_cov, band_cov, depth, depth_unit, approx_cov, cache_key, slow, shigh, specenum)

	else:
		cov_result = json.loads(cache_file)
		times = cov_result['times']
		probs = cov_result['probs']
		areas = cov_result['areas']
		#times = cache.get(f'{cache_key}_times')
		#probs = cache.get(f'{cache_key}_probs')
		#areas = cache.get(f'{cache_key}_areas')

	#if not all([times, probs, areas]):
	#	result = calc_prob_coverage.delay(debug, graceid, mappathinfo, inst_cov, band_cov, depth, depth_unit, approx_cov, cache_key, slow, shigh, specenum)
	#	return jsonify({'result_id': result.id})

	coverage_div = generate_prob_plot(times, probs, areas)

	end = time.time()

	total = end-start
	print('total time doing coverage calculator: {}'.format(total))
	if len(areas):
		print('total area: {}'.format(areas[-1]))
		print('total probability: {}'.format(probs[-1]))

	return coverage_div


#@app.route('/prob_calc_results/<result_id>', methods=['GET'])
#def get_calc_result(result_id):
#	result = AsyncResult(result_id, app=celery)
#	if result.ready():
#		cache_key = result.get()
#		cache_file = json.loads(gwtm_io.get_cached_file(cache_key, config))
#		times = cache_file['times']
#		probs = cache_file['probs']
#		areas = cache_file['areas']
		#times = cache.get(f'{cache_key}_times')
		#probs = cache.get(f'{cache_key}_probs')
		#areas = cache.get(f'{cache_key}_areas')
#		return generate_prob_plot(times, probs, areas)
#	else:
#		return 'false'


@app.route("/ajax_renormalize_skymap", methods=['GET', 'POST'])
def plot_renormalized_skymap():
	start = time.time()

	debug = app.debug
	graceid = models.gw_alert.graceidfromalternate(request.args.get('graceid'))
	mappathinfo = request.args.get('mappathinfo')
	inst_cov = request.args.get('inst_cov')
	band_cov = request.args.get('band_cov')
	depth = request.args.get('depth_cov')
	depth_unit = request.args.get('depth_unit')
	approx_cov = int(request.args.get('approx_cov')) == 1
	spec_range_type = request.args.get('spec_range_type')
	spec_range_unit = request.args.get('spec_range_unit')
	spec_range_low = request.args.get('spec_range_low')
	spec_range_high = request.args.get('spec_range_high')
	slow, shigh = None, None
	specenum = None
	
	pointing_filter = []
	pointing_filter.append(models.pointing_event.graceid == graceid)
	pointing_filter.append(models.pointing.status == 'completed')
	pointing_filter.append(models.pointing_event.pointingid == models.pointing.id)
	pointing_filter.append(models.pointing.instrumentid != 49)

	if inst_cov != '':
		insts_cov = [int(x) for x in inst_cov.split(',')]
		pointing_filter.append(models.pointing.instrumentid.in_(insts_cov))
	#if band_cov != '':
	#	bands_cov = [x for x in band_cov.split(',')]
	#	pointing_filter.append(models.pointing.band.in_(bands_cov))
	if depth_unit != 'None' and depth_unit != '':
		pointing_filter.append(models.pointing.depth_unit == depth_unit)
	if depth is not None and function.isFloat(depth):
		if 'mag' in depth_unit:
			pointing_filter.append(models.pointing.depth >= float(depth))
		elif 'flux' in depth_unit:
			pointing_filter.append(models.pointing.depth <= float(depth))
		else:
			raise HTTPException('Unknown depth unit.')
		
	if spec_range_low not in ['', None] and spec_range_high not in ['', None]:
		if spec_range_type == 'wavelength':
			unit = [x for x in enums.wavelength_units if spec_range_unit == x.name][0]
			scale = enums.wavelength_units.get_scale(unit)
			slow, shigh = float(spec_range_low)*scale, float(spec_range_high)*scale
		if spec_range_type == 'energy':
			unit = [x for x in enums.energy_units if spec_range_unit == x.name][0]
			scale = enums.energy_units.get_scale(unit)
			slow, shigh = float(spec_range_low)*scale, float(spec_range_high)*scale
		if spec_range_type == 'frequency':
			unit = [x for x in enums.frequency_units if spec_range_unit == x.name][0]
			scale = enums.frequency_units.get_scale(unit)
			slow, shigh = float(spec_range_low)*scale, float(spec_range_high)*scale
			
		specenum = [x for x in models.SpectralRangeHandler.spectralrangetype if spec_range_type == x.name][0]
		pointing_filter.append(models.pointing.inSpectralRange(slow, shigh, specenum))

	pointings_sorted = db.session.query(
		models.pointing.id
	).filter(
		*pointing_filter
	).order_by(
		models.pointing.time.asc()
	).all()

	pointingids = [x.id for x in pointings_sorted]
	pointingids = sorted(pointingids)
	hashpointingids =  hashlib.sha1(json.dumps(pointingids).encode()).hexdigest()

	cache_key = f'cache/normed_contours_{graceid}_{approx_cov}_{hashpointingids}'
	#try to load a cached contour
	cache_file = gwtm_io.get_cached_file(cache_key, config)
	#can't find a cached one, then generate one (warning, can be slow)
	if cache_file is None:
		normed_contours = calc_renormalized_skymap(debug, graceid, mappathinfo, inst_cov, band_cov, depth, depth_unit, approx_cov, cache_key, slow, shigh, specenum)
        
	end = time.time()

	total = end-start
	print('total time doing renormalize skymap: {}'.format(total))
        
	return cache_key


@app.route('/ajax_preview_footprint', methods=['GET'])
def preview_footprint():
	args = request.args

	form = forms.SubmitInstrumentForm(
		instrument_name = args.get('instrument_name'),
		instrument_type = args.get('instrument_type'),
		unit = args.get('unit'),
		footprint_type = args.get('footprint_type'),
		height = args.get('height'),
		width = args.get('width'),
		radius = args.get('radius'),
		polygon = args.get('polygon')
	)

	instrument = models.instrument()
	v = instrument.from_json(form, 0, True)

	if len(v[0].errors) == 0:
		trace = []
		vertices = v[2]
		for vert in vertices:
			xs = [v[0] for v in vert]
			ys =[v[1] for v in vert]
			trace1 = go.Scatter(
				x=xs,
				y=ys,
				line_color='blue',
				fill='tozeroy',
				fillcolor='violet'
			)
			trace.append(trace1)
		fig = go.Figure(data=trace)
		fig.update_layout(
			showlegend=False,
			xaxis_title = 'degrees',
			yaxis_title = 'degrees',
			yaxis=dict(
				matches='x',
				scaleanchor="x",
				scaleratio=1,
				constrain='domain',
			)
		)
		data = fig
		graphJSON = json.dumps(data, cls=plotly.utils.PlotlyJSONEncoder)
		return graphJSON
	print(v[0].errors)
	return jsonify("")


@app.route('/ajax_pointingfromid')
def get_pointing_fromID():
	args = request.args
	if 'id' in args and function.isInt(args.get('id')):
		#try:
		id = int(args.get('id'))
		pfilter = []
		pfilter.append(models.pointing.submitterid == current_user.get_id())
		pfilter.append(models.pointing.status == enums.pointing_status.planned)

		pointings = models.pointing.pointings_from_IDS([id], pfilter)

		if len(pointings) > 0:
			pointing = pointings[str(id)]

			pointing_json = {}

			position = pointing.position
			ra = position.split('POINT(')[1].split(' ')[0]
			dec = position.split('POINT(')[1].split(' ')[1].split(')')[0]

			pointing_json['ra'] = ra
			pointing_json['dec'] = dec
			pointing_json['graceid'] = pointing.graceid
			pointing_json['instrument'] = str(pointing.instrumentid)+'_'+enums.instrument_type(pointing.instrument_type).name
			pointing_json['band'] = pointing.band.name
			pointing_json['depth'] = pointing.depth
			pointing_json['depth_err'] = pointing.depth_err

			return jsonify(pointing_json)
		#except Exception as e:
		#	print(e)
		#	pass
	return jsonify('')

@app.route('/ajax_update_spectral_range_from_selected_bands')
def spectral_range_from_selected_bands():
	args = request.args
	band_cov = args.get('band_cov')
	spectral_type = args.get('spectral_type')
	spectral_unit = args.get('spectral_unit')
	# spec_low = args.get('spec_range_low')
	# spec_high = args.get('spec_range_high')

	if band_cov != '' and band_cov != 'null':
		bands = band_cov.split(',')
		
		mins, maxs = [], []
		for b in bands:
			bandname = [x for x in enums.bandpass if b == x.name][0]
			band_min, band_max = None, None
			if spectral_type == 'wavelength':
				band_min, band_max = models.SpectralRangeHandler.wavetoWaveRange(bandpass=bandname)
				unit = [x for x in enums.wavelength_units if spectral_unit == x.name][0]
				scale = enums.wavelength_units.get_scale(unit)
			if spectral_type == 'energy':
				band_min, band_max = models.SpectralRangeHandler.wavetoEnergy(bandpass=bandname)
				unit = [x for x in enums.energy_units if spectral_unit == x.name][0]
				scale = enums.energy_units.get_scale(unit)
			if spectral_type == 'frequency':
				band_min, band_max = models.SpectralRangeHandler.wavetoFrequency(bandpass=bandname)
				unit = [x for x in enums.frequency_units if spectral_unit == x.name][0]
				scale = enums.frequency_units.get_scale(unit)

			if band_min and band_max:
				mins.append(band_min/scale)
				maxs.append(band_max/scale)
		
		if len(mins):
			ret = {
				'total_min':min(mins),
				'total_max':max(maxs)
			}	
			return ret

	else:
		return {
			'total_min':'',
			'total_max':''
		}
