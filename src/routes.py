# -*- coding: utf-8 -*-

import json
import datetime
import plotly
import math
import plotly.graph_objects as go

from itertools import islice
from flask import request, render_template, redirect, flash, url_for
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.urls import url_parse
from sqlalchemy import func

from . import function
from . import models
from . import forms
from . import enums

from src import app

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


#WEBSITE ROUTES
@app.errorhandler(404)
def not_found_error(error):
	return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
	db.session.rollback()
	return render_template('500.html'), 500

@app.route("/index", methods=["GET"])
@app.route("/", methods=["GET"])
def home():
	models.useractions.write_action(request=request, current_user=current_user)
	#get latest alert. Construct the form alertsform

	#fix this by ingesting LAT pointings in the pointings DB
	# TODO: Fermi count should be cached
	#response = s3.list_objects_v2(Bucket=config.AWS_BUCKET, Prefix='fit/')
	#if response['IsTruncated']:
	#	print('WARNING: More than 1000 objects in bucket. Implement pagination.')
	#if len(response['Contents']) < 1:
	#	fermi_events = 0
	#else:
	#	fermi_events = len([x for x in response['Contents'] if 'Fermi' in x['Key']])

	#inst_info = db.session.query(
	#	models.pointing,
	#	models.instrument
	#).group_by(
	#	models.pointing.instrumentid,
	#	models.instrument
	#).filter(
	#	models.pointing.status == enums.pointing_status.completed,
	#	models.instrument.id == models.pointing.instrumentid,
	#	models.pointing_event.pointingid == models.pointing.id,
	#	models.pointing_event.graceid != 'TEST_EVENT'
	#).order_by(
	#	func.count(models.pointing.id).desc()
	#).values(
	#	func.count(models.pointing.id).label('count'),
	#	models.instrument.instrument_name,
	#	models.instrument.id
	#)

	#inst_info = [list(inst_info), fermi_events]

	#graceids = db.session.query(
	#	models.gw_alert.graceid,
	#	models.gw_alert.alert_type,
	#).order_by(
	#	models.gw_alert.time_of_signal.desc()
	#).filter(
	#	models.gw_alert.graceid != 'TEST_EVENT'
	#).all()

	#gids = list(sorted(set([x.graceid for x in graceids]), reverse=True))
	#rets = []
	#for g in gids:
	#	gw_alerts = [x.alert_type for x in graceids if x.graceid == g]
	#	if 'Retraction' in gw_alerts:
	#		rets.append(g)

	#gids = [x for x in gids if x not in rets]
	#graceid = gids[0]

	#status = request.args.get('pointing_status')
	#status = status if status is not None else 'completed'

	#alerttype = request.args.get('alert_type')
	#args = {'graceid':'GW190425', 'pointing_status':status, 'alert_type':alerttype}
	#form = forms.AlertsForm
	#form, detection_overlays, inst_overlays, GRBoverlays, galaxy_cats = form.construct_alertform(form, args)
	#form.page = 'index'

	#return render_template("index.html", form=form, inst_table=inst_info, detection_overlays=detection_overlays, inst_overlays=inst_overlays, GRBoverlays=GRBoverlays, galaxy_cats=galaxy_cats)

	return render_template("index.html")

@app.route("/reported_instruments", methods=['GET'])
def reported_instruments():
	models.useractions.write_action(request=request, current_user=current_user)

	inst_info = db.session.query(
		models.pointing,
		models.instrument
	).filter(
		models.pointing.status == enums.pointing_status.completed,
		models.instrument.id == models.pointing.instrumentid,
		models.pointing_event.pointingid == models.pointing.id,
	).order_by(
		func.count(models.pointing.id).desc()
	).group_by(
		models.pointing.instrumentid,
		models.instrument
	).values(
		func.count(models.pointing.id).label('num'),
		models.instrument.instrument_name,
		models.instrument.id
	)

	return render_template("report.html", inst_table=list(inst_info))


@app.route("/alert_select", methods=['GET'])
def alert_select():
	models.useractions.write_action(request=request, current_user=current_user)
	page = request.args.get('page', 1, type=int)
	selected_per_page = request.args.get('per_page', 25, type=int)
	offset = (page - 1) * selected_per_page

	selected_observing_run = request.args.get('observing_run', default="O4")
	selected_role = request.args.get('role', default="observation")
	selected_far = request.args.get('far', default="significant")
	selected_haspointings = request.args.get('haspointings', default="false")
	queryparam = request.args.get('queryparam', default=None)

	filter = []
	if selected_role != 'all':
		filter.append(models.gw_alert.role == selected_role)

	if selected_observing_run != 'all':
		filter.append(models.gw_alert.observing_run == selected_observing_run)

	allerts = db.session.query(models.gw_alert).filter(*filter).order_by(models.gw_alert.datecreated.asc()).all()
	gids = list(sorted(set([x.graceid for x in allerts]), reverse=True))

	p_event_counts = db.session.query(
		models.pointing_event
	).group_by(
		models.pointing_event.graceid
	).filter(
		models.pointing.id == models.pointing_event.pointingid,
		models.pointing.status == enums.pointing_status.completed,
		models.pointing_event.graceid.in_(gids)
	).values(
		func.count(models.pointing_event.graceid).label('pcount'),
		models.pointing_event.graceid
	)

	icecubes = db.session.query(
		models.icecube_notice,
		models.icecube_notice_coinc_event
	).filter(
		models.icecube_notice.graceid.in_(gids),
		models.icecube_notice_coinc_event.icecube_notice_id == models.icecube_notice.id
	).all()

	icecube_gids = [x.icecube_notice.graceid for x in icecubes]

	p_event_counts = list(p_event_counts)

	all_alerts = []
	cull_retracted = False
	if selected_far == "significant":
		allerts = [x for x in allerts if (x.far < 3.8e-7 and x.group != 'Burst') or (x.far < 3.2e-8 and x.group == 'Burst')]
		cull_retracted = True
	elif selected_far == "subthreshold":
		allerts = [x for x in allerts if (x.far >= 3.8e-7 and x.group != 'Burst') or (x.far >= 3.2e-8 and x.group == 'Burst')]
		cull_retracted = True

	for g in gids:
		glerts = [x for x in allerts if x.graceid == g]
		alert_types = [x.alert_type for x in glerts]
		atypes_retract = any([(x == 'Retraction' and cull_retracted) for x in alert_types])

		if len(glerts) and not atypes_retract:
			most_recent_date = list(sorted([x.datecreated for x in glerts], reverse=True))[0]
			most_recent_alert = [x for x in glerts if x.datecreated == most_recent_date][0]
			pcounts = [x.pcount for x in p_event_counts if g == x.graceid]
			alternateids = [gwa for gwa in glerts if (gwa.alternateid is not None and gwa.alternateid != '')]

			if len(alternateids):
				g = alternateids[0].alternateid

			pointing_counts = 0
			if len(pcounts):
				pointing_counts = pcounts[0]

			hasicecubenotice = g in icecube_gids

			if 'Retraction' in alert_types:
				all_alerts.append({
					"alertname" : g,
					"class":"Retracted",
					"alert_types":alert_types,
					"distance":"",
					"pcounts":pointing_counts,
					"has_icecube" : False
				})

			else:
				classification = most_recent_alert.getClassification()
				all_alerts.append({
					"alertname" : g,
					"class":classification,
					"alert_types":alert_types,
					"distance":str(round(most_recent_alert.distance, 2)) + " +/- " + str(round(most_recent_alert.distance_error, 2)),
					"pcounts":pointing_counts,
					"has_icecube" : hasicecubenotice
				})

	if selected_haspointings == 'true':
		all_alerts = [x for x in all_alerts if x['pcounts'] > 0]

	if queryparam is not None:
		all_alerts = [x for x in all_alerts if (queryparam in str(x['alertname']).lower() or queryparam in str(x['class']).lower())]

	total_alerts = len(all_alerts)

	total_pages = math.ceil(total_alerts / selected_per_page)

	all_alerts = list(islice(all_alerts, offset, offset+selected_per_page))

	observing_runs = {
		'all' : 'All',
		'O2':'O2',
		'O3':'O3',
		'O4':'O4'
	}

	roles = {
		'all' : 'All',
		'test': 'Test',
		'observation': 'Observation'
	}

	far = {
		'all' : 'All',
		'significant' : 'Significant',
		'subthreshold' : 'Subthreshold'
	}

	per_pages = {
		'10' : 10,
		'25' : 25,
		'50' : 50,
		'100': 100
	}

	return render_template("alert_select.html", alerts=all_alerts, observing_runs=observing_runs, roles=roles, far=far,
                           selected_haspointings=selected_haspointings, selected_observing_run=selected_observing_run,
                           selected_role=selected_role, selected_far=selected_far, page=page,
                           total_alerts=total_alerts, per_pages=per_pages, selected_per_page=str(selected_per_page), left=total_alerts-selected_per_page*page,
                           total_pages=total_pages, queryparam=queryparam)

@app.route("/alerts", methods=['GET', 'POST'])
def alerts():
	models.useractions.write_action(request=request, current_user=current_user)
	graceid = request.args.get('graceids')
	status = request.args.get('pointing_status')
	status = status if status is not None else 'completed'
	alerttype = request.args.get('alert_type')

        # Get the optional JSON path argument for loading a renormed skymap
	renorm_arg = request.args.get('normed_path', default=False)
	
	args = {'graceid':graceid, 'pointing_status':status, 'alert_type': alerttype, 'renorm_skymap':renorm_arg}
	form = forms.AlertsForm
	form.page = 'alerts'
	form = form.construct_alertform(form, args)
        
	if graceid != 'None' and graceid is not None:
		return render_template("alerts.html", form=form, detection_overlays=form.detection_overlays, GRBoverlays=form.GRBoverlays)

	form.graceid = 'None'
	return render_template("alerts.html", form=form, detection_overlays=form.detection_overlays, GRBoverlays=form.GRBoverlays)


@app.route("/fairuse", methods=['GET'])
def fairuse():
	models.useractions.write_action(request=request, current_user=current_user)
	return render_template('fairuse.html')

@app.route("/status", methods=['GET'])
def status():
	models.useractions.write_action(request=request, current_user=current_user)
	return render_template('status.html')


@app.route("/documentation", methods=['GET'])
def documentation():
	models.useractions.write_action(request=request, current_user=current_user)
	return render_template('documentation.html')


@app.route("/jupyter_tutorial", methods=['GET'])
def jupyter():
	models.useractions.write_action(request=request, current_user=current_user)
	return render_template('jupyter_tutorial.html')


@app.route("/development_blog", methods=['GET'])
def devblog():
	models.useractions.write_action(request=request, current_user=current_user)
	return render_template('development_blog.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
	models.useractions.write_action(request=request, current_user=current_user)
	if current_user.is_authenticated:
		return redirect('/index')
	form = forms.RegistrationForm()
	if form.validate_on_submit():
		user = models.users(
			username=form.username.data,
			email=form.email.data,
			firstname=form.firstname.data,
			lastname=form.lastname.data,
			datecreated=datetime.datetime.now(),
			verified = False
			)
		user.set_password(form.password.data)
		user.set_verification_key()
		db.session.add(user)
		db.session.flush()
		db.session.commit()
		function.send_account_validation_email(user)

		flash("An email has been sent to "+user.email+". Please follow further instructions to activate this account (Mail might be sent to Spam folder)")
		return redirect('/index')
	return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
	models.useractions.write_action(request=request, current_user=current_user)
	verification_key = request.args.get("verification_key")
	form = forms.LoginForm()

	if current_user.is_authenticated:
		logout_user()

	if verification_key and not form.validate_on_submit():
		flash('Please login with your email and password to verify account')
		user = models.users.query.filter_by(verification_key=verification_key).first()
		form.username.data = user.username
		form.verification_key = verification_key

	if form.validate_on_submit():
		user = models.users.query.filter_by(username=form.username.data).first()

		if user is None or not user.check_password(form.password.data):
			flash('Invalid username or password')
			return redirect('login')

		login_user(user, remember=form.remember_me.data)

		if verification_key == user.verification_key and not user.verified:
			user.verified = True
			user.set_apitoken()
			db.session.commit()
			flash("Your account has been verified, go to Profile to access your api_token")

		next_page = request.args.get('next')
		if not next_page or url_parse(next_page).netloc != '':
			next_page = '/index'

		return redirect(next_page)
	return render_template('login.html', form=form)


@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
	models.useractions.write_action(request=request, current_user=current_user)
	token = request.args.get('token')
	if current_user.is_authenticated:
		return redirect(url_for('login'))
	user = models.users.verify_reset_password_token(token)
	if not user:
		flash("Invalid reset token")
		return redirect(url_for('login'))
	form = forms.ResetPasswordForm()
	if form.validate_on_submit():
		user.set_password(form.password.data)
		db.session.commit()
		flash('Your password has been reset.')
		return redirect(url_for('login'))
	return render_template('reset_password.html', form=form)


@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
	models.useractions.write_action(request=request, current_user=current_user)
	if current_user.is_authenticated:
		return redirect(url_for('index'))
	form = forms.ResetPasswordRequestForm()
	if form.validate_on_submit():
		user = models.users.query.filter_by(email=form.email.data).first()
		if user:
			function.send_password_reset_email(user)
			flash('Check your email for the instructions to reset your password (Mail might be sent to Spam folder)')
			return redirect(url_for('login'))
		else:
			flash('Cannot find a user with that email')
	return render_template('reset_password_request.html',
						   title='Reset Password', form=form)


@app.route('/manage_user', methods=['GET', 'POST'])
@login_required
def manage_user():
	models.useractions.write_action(request=request, current_user=current_user)
	userid = int(current_user.get_id())

	form = forms.ManageUserForm()
	form.construct_form(userid=userid)

	return render_template('manage_user.html', form=form)


@app.route('/search_pointings', methods=['GET', 'POST'])
def search_pointings():
	models.useractions.write_action(request=request, current_user=current_user)
	form = forms.SearchPointingsForm()
	form.populate_selectdowns()
	form.populate_creator_groups(current_user.get_id())

	if request.method == 'POST':
		args = request.form
		formgraceid = args.get("graceid")

		gids = form.graceids
		for g in gids:
			if g['value'] == formgraceid:
				g['selected'] = True
		form.graceids = gids

		alternateids = db.session.query(models.gw_alert).filter(
			models.gw_alert.alternateid == formgraceid
		).all()

		if len(alternateids):
			graceid = alternateids[0].graceid
		else:
			graceid = formgraceid

		filter = []
		filter.append(models.pointing_event.graceid.contains(graceid))
		filter.append(models.pointing_event.pointingid == models.pointing.id)

		status_choice = args.getlist("status")
		stats = form.statuses
		for s in stats:
			if s['value'] in status_choice:
				s['selected'] = True
		form.statuses = stats

		if len(status_choice):
			if "all" not in status_choice:
				filter.append(models.pointing.status.in_(status_choice))

		band_choice = args.getlist("band")
		bands = form.bands
		for b in bands:
			if b['value'] in band_choice:
				b['selected'] = True
		form.bands = bands

		if len(band_choice):
			if "all" not in band_choice:
				filter.append(models.pointing.band.in_(band_choice))

		if form.my_points.data:
			filter.append(models.pointing.submitterid == current_user.get_id())

		filter.append(models.pointing.submitterid == models.users.id)
		filter.append(models.pointing.instrumentid == models.instrument.id)

		results = db.session.query(models.pointing.id,
								   func.ST_AsText(models.pointing.position).label('position'),
								   models.pointing.instrumentid,
								   models.pointing.band,
								   models.pointing.pos_angle,
								   models.pointing.depth,
								   models.pointing.time,
								   models.pointing.status,
								   models.pointing.doi_url,
								   models.pointing.doi_id,
								   models.instrument.instrument_name,
								   models.users.username,
								   models.pointing.submitterid
								   ).filter(*filter).all()

		return render_template('search_pointings.html', form=form, search_result=results, nresults=len(results))
	return render_template('search_pointings.html', form=form)


@app.route('/search_instruments', methods=['GET', 'POST'])
def search_instruments():
	models.useractions.write_action(request=request, current_user=current_user)
	form = forms.SearchInstrumentsForm()
	if request.method == 'POST':
		if form.types.data != '' and form.types.data != 'all':
			results = db.session.query(models.instrument).filter(models.instrument.instrument_name.ilike(form.name.data +'%')).\
			filter(models.instrument.instrument_type == form.types.data).all()
		else:
			results = db.session.query(models.instrument).filter(models.instrument.instrument_name.ilike(form.name.data +'%')).all()
		return render_template('search_instruments.html', form=form, search_result=results)
	return render_template('search_instruments.html', form=form)


@app.route('/submit_pointings', methods=['GET', 'POST'])
@login_required
def submit_pointing():
	models.useractions.write_action(request=request, current_user=current_user)
	form = forms.SubmitPointingForm()
	form.populate_graceids()
	form.populate_instruments()
	form.populate_creator_groups(current_user.get_id())

	if request.method == 'POST':

		#pointing object
		pointing = models.pointing()

		#default required fields
		graceid = models.gw_alert.graceidfromalternate(form.graceids.data)
		status = form.obs_status.data
		ra = form.ra.data
		dec = form.dec.data
		instrument = form.instruments.data
		band = form.obs_bandpass.data
		depth_err = form.depth_err.data
		depth = form.depth.data
		depth_unit = form.depth_unit.data

		#validation
		if graceid == 'None':
			flash('GraceID is required')
			return render_template('submit_pointings.html', form=form)

		if status == 'None':
			flash('Status is required')
			return render_template('submit_pointings.html', form=form)

		if not function.isFloat(ra) or not function.isFloat(dec):
			flash("RA and DEC must be decimal")
			return render_template('submit_pointings.html', form=form)

		if instrument == 'None':
			flash('Instrument is required')
			return render_template('submit_pointings.html', form=form)

		instrumentid, instrument_type = int(instrument.split('_')[0]), instrument.split('_')[1]

		if band == 'None' and instrument_type == "photometric":
			flash('Bandpass is required for photometric instrument')
			return render_template('submit_pointings.html', form=form)

		if depth is None:
			flash('Depth is required')
			return render_template('submit_pointings.html', form=form)

		if depth_unit == 'None':
			flash('Depth Unit is required')
			return render_template('submit_pointings.html', form=form)

		#inserting
		pointing.datecreated = datetime.datetime.now()
		pointing.position="POINT("+str(ra)+" "+str(dec)+")"
		pointing.submitterid = current_user.get_id()
		pointing.status = status
		pointing.instrumentid = instrumentid
		pointing.band = band
		pointing.depth = depth
		pointing.depth_err = depth_err
		pointing.depth_unit = depth_unit

		#conditional status
		if status == enums.pointing_status.completed.name:

			#required fields
			completed_time = form.completed_obs_time.data
			pos_angle = form.pos_angle.data

			#validation
			print(completed_time)
			if completed_time is None:
				flash('Completed time is required')
				flash('Completed time must be in the format of \'%Y-%m-%dT%H:%M:%S.%f\'')
				return render_template('submit_pointings.html', form=form)
			if pos_angle is None:
				flash('Position Angle is required')
				return render_template('submit_pointings.html', form=form)

			#inserting
			pointing.time = completed_time
			pointing.pos_angle = pos_angle

		#conditional status
		if status == enums.pointing_status.planned.name:

			#required fields
			planned_time = form.planned_obs_time.data

			#validation
			if planned_time is None:
				flash('Planned time is required')
				flash('Planned time must be in the format of \'%Y-%m-%dT%H:%M:%S.%f\'')
				return render_template('submit_pointings.html', form=form)

			#inserting
			pointing.time = planned_time


		otherpointings = db.session.query(models.pointing).filter(
			models.pointing.id == models.pointing_event.pointingid,
			models.pointing_event.graceid == graceid
		).all()

		if function.pointing_crossmatch(pointing, otherpointings):
			flash("Pointing already submitted")
			return render_template('submit_pointings.html', form=form)

		#commiting data
		db.session.add(pointing)
		db.session.flush()

		pointing_e = models.pointing_event(
				graceid=graceid,
				pointingid=pointing.id
		)
		db.session.add(pointing_e)
		db.session.commit()

		flash("Successful submission of Pointing. Your Pointing ID is "+str(pointing.id))
		flash("Please keep track of your pointing ids")

		if form.request_doi.data:
			user = models.users.query.filter_by(id=pointing.submitterid).first()
			if form.doi_creator_groups.data != 'None':
				valid, creators = models.doi_author.construct_creators(form.doi_creator_groups.data, user.id)
				print(creators)
				if not valid:
					creators = [{"name":str(user.firstname) + " " + str(user.lastname), "affiliation":""}]
			else:
				creators = [{"name":str(user.firstname) + " " + str(user.lastname), "affiliation":""}]

			points = [pointing]

			insts = db.session.query(models.instrument).filter(models.instrument.id.in_([x.instrumentid for x in points]))
			inst_set = list(set([x.instrument_name for x in insts]))

			if form.doi_url.data:
				pointing.doi_id, pointing.doi_url = 0, form.doi_url.data
			else:
				graceid = models.gw_alert.alternatefromgraceid(graceid)
				pointing.doi_id, pointing.doi_url = function.create_pointing_doi(points, graceid, creators, inst_set)
			db.session.commit()
			flash("Your DOI url is: "+pointing.doi_url)

		return redirect("/index")

	return render_template('submit_pointings.html', form=form)


@app.route('/submit_instrument', methods=['GET', 'POST'])
@login_required
def submit_instrument():
	models.useractions.write_action(request=request, current_user=current_user)
	form = forms.SubmitInstrumentForm()

	insts = db.session.query(
		models.instrument
	).order_by(
		models.instrument.datecreated
	).all()

	if request.method == 'POST' or False:

		instrument = models.instrument()
		valid_map = instrument.from_json(form, current_user.get_id())

		if len(valid_map[0].errors) > 0:
			for e in valid_map[0].errors:
				flash(e)
			return render_template('submit_instrument.html', form=form, plot=None)

		footprint = valid_map[1]

		db.session.add(instrument)
		db.session.flush()

		for f in footprint:
			fccd = models.footprint_ccd(
				instrumentid = instrument.id,
				footprint = f
			)
			db.session.add(fccd)

		db.session.commit()

		flash("Successful submission of Instrument. Your instrument ID is "+str(instrument.id))
		return redirect("/index")

	return render_template('submit_instrument.html', form=form, plot=None, insts=insts)


@app.route('/instrument_info')
def instrument_info():
	models.useractions.write_action(request=request, current_user=current_user)
	instid = request.args.get('id')

	instrument = db.session.query(
		models.instrument,
		models.users.username,
		func.ST_AsText(models.footprint_ccd.footprint).label('footprint')
	).filter(
		models.instrument.id == instid,
		models.instrument.id == models.footprint_ccd.instrumentid,
		models.instrument.submitterid == models.users.id
	).all()

	events_contributed = db.session.query(
		models.pointing,
		models.gw_alert.graceid
	).filter(
		models.pointing.instrumentid == instid,
		models.pointing_event.pointingid == models.pointing.id,
		models.gw_alert.graceid == models.pointing_event.graceid,
		models.pointing.status ==enums.pointing_status.completed
	).all()

	gids = sorted(list(set([x.graceid for x in events_contributed])), reverse=True)
	events = []
	for g in gids:
		numevents = len([x for x in events_contributed if x.graceid == g])
		events.append({'event':g, 'count':str(numevents)})

	if len(instrument) > 0:
		inst = instrument[0].instrument
		username = instrument[0].username
		sanatized_ccds = function.sanatize_footprint_ccds([x.footprint for x in instrument])
		trace = []
		vertices = sanatized_ccds
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
			width=500,
			height=500,
			yaxis=dict(
				matches='x',
				scaleanchor="x",
				scaleratio=1,
				constrain='domain',
			)
		)
		data = fig
		graphJSON = json.dumps(data, cls=plotly.utils.PlotlyJSONEncoder)

	return render_template('instrument_info.html', inst=inst, graph=graphJSON, events=events, username=username)


@app.route('/doi_author_group', methods=['GET','POST'])
def doi_author_group():
	models.useractions.write_action(request=request, current_user=current_user)
	#I want to be able to edit/and create on the same page
	#test for the id, if there is one, then load it
	form = request.form
	groupid = request.args.get('doi_group_id')

	#test to load page
	if groupid and request.method != 'POST':
		doi_author_group = db.session.query(models.doi_author_group).filter(models.doi_author_group.id == groupid).first()

		if doi_author_group.userid != int(current_user.get_id()):
			flash("Invalid Author Group. You may only view your own")
			return redirect('/manage_user')

		authors = db.session.query(models.doi_author).filter(models.doi_author.author_groupid == groupid).order_by(models.doi_author.id).all()
		return render_template('doi_author_group.html', group_info=doi_author_group, authors=authors)

	#test to save
	if groupid and request.method == 'POST':
		authors = models.doi_author.authors_from_page(form)
		group_name = form.get('group_name')

		group_info = db.session.query(models.doi_author_group).filter(models.doi_author_group.id == groupid).first()
		group_info.name = group_name

		valid, message = function.validate_authors(authors)
		if not valid:
			flash(message)
			return render_template('doi_author_group.html', group_info=group_info, authors=authors, create=False)
		if group_name is None or group_name == "":
			flash("Group Name is required")
			return render_template('doi_author_group.html', group_info=group_info, authors=authors, create=False)

		prev_authors = db.session.query(models.doi_author).filter(models.doi_author.author_groupid == groupid)

		curr_ids = [x.id for x in authors]
		for pre_auth in prev_authors:
			if pre_auth.id not in curr_ids:
				db.session.delete(pre_auth)

		for a in authors:
			a.author_groupid = int(groupid)
			if a.id is None:
				db.session.add(a)
			prev = prev_authors.filter(models.doi_author.id == a.id).first()
			if prev:
				prev.name = a.name
				prev.affiliation = a.affiliation
				prev.orcid = a.orcid
				prev.gnd = a.gnd
				prev.pos_order = a.pos_order

		db.session.flush()
		db.session.commit()

		return redirect('/manage_user')

	#test if new save
	if groupid is None and request.method == 'POST':
		authors = models.doi_author.authors_from_page(form)
		group_name = form.get('group_name')
		group_info = models.doi_author_group(
			name=group_name,
			userid=current_user.get_id()
		)
		valid, message = function.validate_authors(authors)
		if not valid:
			flash(message)
			return render_template('doi_author_group.html', group_info=group_info, authors=authors, create=True)
		if group_name is None or group_name == "":
			flash("Group Name is required")
			return render_template('doi_author_group.html', group_info=group_info, authors=authors, create=True)

		db.session.add(group_info)
		db.session.flush()

		for a in authors:
			a.author_groupid = group_info.id
			db.session.add(a)

		db.session.commit()

		return redirect('/manage_user')

	return render_template('doi_author_group.html', create=True)


@app.route('/logout')
def logout():
	models.useractions.write_action(request=request, current_user=current_user)
	logout_user()
	return redirect('/index')
