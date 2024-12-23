from flask import Blueprint, request, jsonify, current_app, redirect
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from models import User, Study, PingTemplate, UserStudy, Ping, Enrollment
from permissions import user_has_study_permission, get_current_user
from random import randint
from datetime import timedelta, datetime, timezone
import pytz
from utils import generate_non_confusable_code
import secrets

particpant_facing_bp = Blueprint('particpant_facing', __name__)


@particpant_facing_bp.route('/ping/<ping_id>', methods=['GET'])
def ping_forwarder(ping_id):
    """
    Forward a ping to the appropriate URL.
    :param ping_id: The ID of the ping to forward.
    
    
    """
    # Log the start of the request
    current_app.logger.info("Received request to forward ping.")
    
    # Get the ping
    ping = Ping.query.get(ping_id)
    
    # Check if the ping exists
    if not ping:
        current_app.logger.error(f"Failed to find ping with ID {ping_id}.")
        return jsonify({"error": "Ping not found."}), 404
    
    # Get query variable: code
    code = request.args.get('code')
    
    # Check if code is present and matches the ping's code
    if not code or code != ping.forwarding_code:
        current_app.logger.error(f"Invalid forwarding code: {code}.")
        return jsonify({"error": "Invalid code."}), 400
    
    # Redirect to ping.url
    return redirect(ping.url)


def random_time(start_date: datetime, start_day_num: int, start_time: str, end_day_num: int, end_time: str, tz: str) -> datetime:
    interval_start_date = start_date + timedelta(days=start_day_num)
    interval_end_date = start_date + timedelta(days=end_day_num)
    start_time = datetime.strptime(start_time, '%H:%M').time()
    end_time = datetime.strptime(end_time, '%H:%M').time()
    try:
        tz = pytz.timezone(tz)
    except pytz.exceptions.UnknownTimeZoneError:
        current_app.logger.error(f"Invalid timezone {tz}.")
        return
    interval_start_ts = datetime.combine(interval_start_date, start_time, tzinfo=tz)
    interval_end_ts = datetime.combine(interval_end_date, end_time, tzinfo=tz)
    ping_interval_length = interval_end_ts - interval_start_ts
    ping_time = interval_start_ts + timedelta(seconds=randint(0, ping_interval_length.total_seconds()))
    return ping_time
    
def make_pings(enrollment_id, study_id):
    
    current_app.logger.info(f"Making pings for enrollment {enrollment_id} in study {study_id}")
    
    try:
        # Get enrollment
        enrollment = Enrollment.query.get(enrollment_id)
        if not enrollment:
            current_app.logger.error(f"Enrollment {enrollment_id} not found. Aborting ping creation for study {study.id}.")
            return
        
        # Get study
        study = Study.query.get(study_id)
        if not study:
            current_app.logger.error(f"Study {study_id} not found. Aborting ping creation for participant {enrollment_id}.")
            return
        
        # Get ping templates
        ping_templates = study.ping_templates
        if not ping_templates:
            current_app.logger.error(f"No ping templates found for study {study_id}. Aborting ping creation for participant {enrollment_id}.")
            return
        
        # note some assumptions:
        # signup date is Day 0
        # start time and end time are in format HH:MM
        # schedule is a list of dictionaries with keys 'start_day_num', 'start_time', 'end_day_num', 'end_time'
        pings = []
        for pt in ping_templates:
            for ping in pt.schedule:
                # Generate random time within the ping interval
                ping_time = random_time(start_date=enrollment.start_date, 
                                        start_day_num=ping['start_day_num'],
                                        start_time=ping['start_time'],
                                        end_day_num=ping['end_day_num'], 
                                        end_time=ping['end_time'], 
                                        tz=enrollment.tz)
                # Create ping
                ping = {
                    'enrollment_id': enrollment_id,
                    'study_id': study_id,
                    'ping_template_id': pt.id,
                    'scheduled_ts': ping_time,
                    'expire_ts': ping_time + pt.expire_latency,
                    'reminder_ts': ping_time + pt.reminder_latency,
                    'day_num': ping['start_day_num'],
                    'url': pt.url,
                    'ping_sent': False,
                    'reminder_sent': False 
                }
                pings.append(ping)
                db.session.add(Ping(**ping))
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating pings for enrollment {enrollment_id} in study {study_id}")
        current_app.logger.exception(e)
        return
    
    current_app.logger.info(f"Created {len(pings)} pings for enrollment {enrollment_id} in study {study_id}")
    return pings
    
    
@particpant_facing_bp.route('/signup', methods=['POST'])
def study_signup():
    '''
    This endpoint is used to collect the timezone of a participant and enroll them in a study.
    It also creates pings for the participant based on the study's ping templates (though this may be moved to after collecting telegram ID).
    They still need to have their telegram ID collected and linked to the enrollment.
    The endpoint ultimately returns a unique code for them (and saves it in the database) that they can provide to the telegram bot 
    in order to link their telegram ID to their enrollment.
    '''
    
    data = request.get_json()
    signup_code = data.get('signup_code')
    study_pid = data.get('study_pid')
    tz = data.get('tz')
    
    # Check if signup code is valid 
    study = Study.query.filter_by(code=signup_code).first()
    if not study:
        return jsonify({"error": "Invalid signup code"}), 404
    
    # Generate a unique code for the participant to link their telegram ID
    telegram_link_code = None
    while True:
        telegram_link_code = generate_non_confusable_code(length=6)
        if not Enrollment.query.filter_by(telegram_link_code=telegram_link_code).first():
            break
        
    # Create a new enrollment
    try:
        enrollment = Enrollment(study_id=study.id, 
                                tz=tz,
                                enrolled=True, 
                                study_pid=study_pid,
                                start_date=datetime.now().date(),
                                pr_completed=0.0,
                                telegram_link_code=telegram_link_code,
                                telegram_link_code_expire_ts=datetime.now(timezone.utc) + timedelta(days=current_app.config["TELEGRAM_LINK_CODE_EXPIRY_DAYS"])
                                )
        db.session.add(enrollment)
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error with enrollment in study {study.id} using signup code {signup_code} for study pid {study_pid}")
        current_app.logger.exception(e)
        return jsonify({"error": "Internal server error"}), 500
    
    # Create pings for participant
    pings = make_pings(
        enrollment_id=enrollment.id, 
        study_id=study.id
        )
    if not pings:
        return jsonify({"error": "Internal server error"}), 500
    
    return jsonify({
        "message": "Participant enrolled successfully",
        "telegram_link_code": telegram_link_code,
        "participant_id": enrollment.id,
        "study_id": study.id,
        "study_pid": study_pid,
        "tz": enrollment.tz
    }), 200
    


@particpant_facing_bp.route('/enrollment/login', methods=['POST'])
def participant_login():
    '''
    This endpoint is used to generate a one-time login link for a participant.
    '''
    
    data = request.get_json()
    telegram_id = data.get('telegram_id')
    
    # Create a new OTP
    otp = secrets.token_urlsafe(16)
    expiry = datetime.now() + timedelta(minutes=current_app.config["ENROLLMENT_DASHBOARD_OTP_EXPIRY_MINS"])
    

    
    
    
    