# DEPRECATED

from flask import Blueprint, request, g, Response, jsonify, current_app
from flask_jwt_extended import jwt_required
from config import Config
import urllib.parse
from utils import generate_non_confusable_code
from models import Study, Participant, Enrollment, Ping, PingTemplate, User
from app import db
from random import randint
from datetime import timedelta, datetime
import pytz

participants_bp = Blueprint('participants', __name__)



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
    
# TODO: add db rollback on error
def make_pings(participant_id, study_id):
    
    current_app.logger.info(f"Making pings for participant {participant_id} in study {study_id}")
    
    try:
        # Get participant
        participant = Participant.query.get(participant_id)
        if not participant:
            current_app.logger.error(f"Participant {participant_id} not found. Aborting ping creation for study {study_id}.")
            return
        
        # Get study
        study = Study.query.get(study_id)
        if not study:
            current_app.logger.error(f"Study {study_id} not found. Aborting ping creation for participant {participant_id}.")
            return
        
        # Get ping templates
        ping_templates = study.ping_templates
        if not ping_templates:
            current_app.logger.error(f"No ping templates found for study {study_id}. Aborting ping creation for participant {participant_id}.")
            return
        
        # Get enrollment
        enrollment = Enrollment.query.filter_by(participant_id=participant_id, study_id=study_id).first()
        if not enrollment:
            current_app.logger.error(f"Participant {participant_id} not enrolled in study {study_id}. Aborting ping creation.")
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
                                        start_day_num=ping['start_day'],
                                        start_time=ping['start_time'],
                                        end_day_num=ping['end_day'], 
                                        end_time=ping['end_time'], 
                                        tz=participant.tz)
                # Create ping
                ping = {
                    'participant_id': participant_id,
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
        current_app.logger.error(f"Error creating pings for participant {participant_id} in study {study_id}: {e}")
        return
    
    current_app.logger.info(f"Created {len(pings)} pings for participant {participant_id} in study {study_id}")
    return pings
    
    
@participants_bp.route('/participants/signup', methods=['POST'])
def study_signup():
    
    data = request.get_json()
    signup_code = data.get('signup_code')
    study_pid = data.get('study_pid')
    tz = data.get('tz')
    
    # Check if signup code is valid 
    study = Study.query.filter_by(code=signup_code).first()
    if not study:
        return jsonify({"error": "Invalid signup code"}), 404
    
    try:
        
        # Check if participant exists and if not, create
        # EDIT: WE DON'T KNOW IF PARTICIPANT EXISTS WITHOUT TELEGRAM ID - NEED TO CONSOLIDATE PARTICIPANT ENTRY AFTER TELEGRAM SIGNUP
        # participant = Participant.query.filter_by(study_pid=study_pid).first()
        # if not participant:
        #     participant = Participant(tz=tz)
        #     db.session.add(participant)
        
        # Check if timezone matches existing participant timezone
        # if participant.tz != tz:
        #     participant.tz = tz
        
        # Check if participant is already enrolled in study
        # participant = Participant.query.filter_by(study_pid=study_pid).first()
        # if participant:
        #     return jsonify({"error": "Participant already enrolled"}), 400
        
        # Enroll participant in study and set enrollment status to True
        enrollment = Enrollment(#participant_id=participant.id, 
                                study_id=study.id, 
                                tz=tz,
                                enrolled=True, 
                                study_pid=study_pid,
                                start_date=datetime.now(),
                                pr_completed=0.0,
                                )
        db.session.add(enrollment)
        
        # Commit
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error enrolling participant {study_pid} in study {study.id}: {e}")
        return jsonify({"error": "Internal server error"}), 500
    
    # Create pings for participant
    pings = make_pings(participant.id, study.id)
    if not pings:
        return jsonify({"error": "Internal server error"}), 500
    
    return jsonify({
        "message": "Participant enrolled successfully",
        "participant_id": participant.id,
        "study_id": study.id,
        "study_pid": study_pid,
        "tz": participant.tz
    }), 200


@participants_bp.route('/participants/<int:participant_id>', methods=['PUT'])
def update_participant(participant_id):

    participant = Participant.query.get(participant_id)
    if not participant:
        return jsonify({"error": "User not found"}), 404

    # data = request.get_json()
    # if 'public_name' in data:
    #     study.public_name = data['public_name']
    # if 'internal_name' in data:
    #     study.internal_name = data['internal_name']

    # db.session.commit()

    # current_app.logger.info(f"User {user.email} updated study {study_id}.")
    # return jsonify({
    #     "message": "Study updated successfully",
    #     "study": {"id": study.id, "public_name": study.public_name, "internal_name": study.internal_name}
    # }), 200
    

def generate_telegram_link(start_msg):
    bot_name = Config.BOT_NAME
    encoded_start_msg = urllib.parse.quote_plus(start_msg)
    url = f"https://t.me/{bot_name}?start={encoded_start_msg}"
    return url
    
    

