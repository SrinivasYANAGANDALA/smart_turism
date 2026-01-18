from flask import Blueprint, render_template, flash, redirect, url_for, request, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from app.extensions import db
from datetime import datetime
from app.utils import call_llm_api
from app.models import Trip, ItineraryItem, TripNote, PackingItem,User, SOSAlert
from datetime import datetime
from app.utils import call_llm_api, send_email  # ADD send_email


# Safe import with a fallback stub to avoid runtime errors if app.utils is not available
try:
    from app.utils import call_llm_api
except Exception:
    def call_llm_api(prompt):
        # Fallback behavior: return a clear disabled message so calling code can handle it
        return "AI functionality is disabled: call_llm_api not available."

dash_bp = Blueprint('dashboard', __name__)
from datetime import datetime
from app.models import Trip  # Adjust import according to your project structure

@dash_bp.route('/dashboard')
@login_required
def show_dashboard():
    """
    Displays the user's dashboard with their trips and next upcoming trip.
    """
    trips = Trip.query.filter_by(user_id=current_user.id).all()

    next_trip = None
    if trips:
        try:
            # Parse start_date and end_date to datetime objects if they are strings
            for trip in trips:
                if isinstance(trip.start_date, str):
                    trip.start_date = datetime.strptime(trip.start_date, '%Y-%m-%d')
                if isinstance(trip.end_date, str):
                    trip.end_date = datetime.strptime(trip.end_date, '%Y-%m-%d')

            # Sort trips by start_date
            sorted_trips = sorted(trips, key=lambda t: t.start_date)

            # Find the first trip where start_date is today or in the future
            today = datetime.today().date()
            future_trips = [t for t in sorted_trips if t.start_date.date() >= today]

            if future_trips:
                next_trip = future_trips[0]

        except Exception as e:
            print(f"Error parsing dates in trips: {e}")
            # fallback: choose first trip, but no formatting possible
            next_trip = trips[0]

    return render_template(
        'dashboard.html',
        trips=trips,
        next_trip=next_trip,
        user_name=current_user.name
    )
# Add these routes to your dashboard.py

@dash_bp.route('/send-sos', methods=['POST'])
@login_required
def send_sos():
    """
    Trigger SOS:
    - Save SOS alert in DB
    - Send detailed emergency email to user's emergency contact
    """
    try:
        data = request.get_json()

        latitude = data.get('latitude')
        longitude = data.get('longitude')
        message = data.get('message', 'Emergency SOS Alert')

        # ---------------- SAVE SOS ALERT ----------------
        sos_alert = SOSAlert(
            user_id=current_user.id,
            location_lat=latitude,
            location_lng=longitude,
            message=message
        )
        db.session.add(sos_alert)
        db.session.commit()

        # ---------------- EMAIL TARGET ----------------
        emergency_email = current_user.emergency_contact_email
        print("🚨 SOS EMAIL TARGET:", emergency_email)

        if not emergency_email:
            print("❌ No emergency email configured for user")
            return {'success': False, 'error': 'No emergency contact email'}, 400

        # ---------------- EMAIL CONTENT ----------------
        email_body = f"""
🚨🚨 EMERGENCY SOS ALERT 🚨🚨

This is an AUTOMATED emergency alert from TravelBuddy.

A registered user has triggered the SOS panic button and may be in immediate danger.

👤 USER DETAILS
Name: {current_user.name}
Phone: {current_user.phone_number or 'Not provided'}
Email: {current_user.email}

📍 LAST KNOWN LOCATION
Latitude: {latitude}
Longitude: {longitude}

🕒 TIME (UTC)
{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

⚠️ MESSAGE
{message}

🚑 WHAT YOU SHOULD DO NOW
• Try calling the user immediately
• Share this information with local authorities if needed
• Take urgent action to ensure their safety

This alert was generated through the TravelBuddy Smart Tourist Safety System.
Please do NOT ignore this email.

— TravelBuddy Safety Team
"""

        # ---------------- SEND EMAIL ----------------
        send_email(
            subject="🚨 URGENT SOS ALERT - TravelBuddy",
            recipients=[emergency_email],
            body=email_body
        )

        print("✅ SOS EMAIL SENT SUCCESSFULLY")

        return {'success': True}

    except Exception as e:
        db.session.rollback()
        print(f"❌ SOS ERROR: {e}")
        return {'success': False, 'error': str(e)}, 500

@dash_bp.route('/admin/dashboard')
@login_required
def admin_dashboard():
    """Admin dashboard showing customers and SOS alerts"""
    if current_user.role != 'admin':
        flash('Access denied. Admin role required.', 'danger')
        return redirect(url_for('dashboard.show_dashboard'))
    
    # Get all customers (tourists)
    customers = User.query.filter_by(role='tourist').all()
    
    # Get recent SOS alerts
    recent_sos = SOSAlert.query.join(User).order_by(SOSAlert.timestamp.desc()).limit(20).all()
    
    # Get active (unresolved) SOS alerts
    active_sos = SOSAlert.query.filter_by(status='active').join(User).order_by(SOSAlert.timestamp.desc()).all()
    
    return render_template('admin_dashboard.html', 
                         customers=customers, 
                         recent_sos=recent_sos,
                         active_sos=active_sos)

@dash_bp.route('/admin/resolve-sos/<int:sos_id>')
@login_required
def resolve_sos(sos_id):
    """Mark SOS alert as resolved"""
    if current_user.role != 'admin':
        return redirect(url_for('dashboard.show_dashboard'))
    
    sos = SOSAlert.query.get_or_404(sos_id)
    sos.status = 'resolved'
    db.session.commit()
    
    flash('SOS alert marked as resolved.', 'success')
    return redirect(url_for('dashboard.admin_dashboard'))

@dash_bp.route('/create_trip')
@login_required
def create_trip():
    """Renders the form for creating a new trip."""
    trip_id = request.args.get('trip_id')
    trip = None
    if trip_id:
        trip = Trip.query.get(trip_id)
        if not trip or trip.user_id != current_user.id:
            flash('Trip not found or unauthorized access.', 'danger')
            return redirect(url_for('dashboard.show_dashboard'))
    return render_template('create_edit_trip.html', trip=trip)



@dash_bp.route('/packing_list', methods=['GET', 'POST'])
@login_required
def packing_list():
    """
    Displays and allows managing a packing list.
    Integrates AI to generate suggestions for a selected trip or the latest trip.
    """
    user_trips = Trip.query.filter_by(user_id=current_user.id).all()
    
    # Filter packing items by currently selected trip (if any)
    selected_trip_id = request.args.get('trip_id', type=int) 
    selected_trip = None
    
    if selected_trip_id:
        selected_trip = Trip.query.get(selected_trip_id)
        if selected_trip and selected_trip.user_id != current_user.id:
            flash("Unauthorized access to selected trip.", "danger")
            selected_trip = None
    
    # If no trip is explicitly selected in the URL, try to default to the latest trip
    if not selected_trip and user_trips:
        try:
            # Handle both string and date objects safely
            selected_trip = sorted(
                user_trips, 
                key=lambda t: datetime.strptime(t.start_date, '%Y-%m-%d') if isinstance(t.start_date, str) else t.start_date, 
                reverse=True
            )[0]
        except Exception as e:
            print(f"Date sorting error: {e}")
            selected_trip = user_trips[0]

    current_packing_list = []
    if selected_trip:
        current_packing_list = PackingItem.query.filter_by(trip_id=selected_trip.id, is_ai_generated=False).all()

    if request.method == 'POST':
        item_name = request.form.get('item')
        if item_name:
            if selected_trip: 
                # CRITICAL: Ensure 'item' matches your models.py column name
                new_item = PackingItem(trip_id=selected_trip.id, item_name=item_name, is_ai_generated=False)
                db.session.add(new_item)
                db.session.commit()
                flash(f'"{item_name}" added to custom packing list for {selected_trip.title}!', 'success')
            else:
                flash("Please select a trip or create one first to add packing items.", "warning")
            
            return redirect(url_for('dashboard.packing_list', trip_id=selected_trip.id if selected_trip else ''))

    generated_ai_suggestions = []
    if selected_trip:
        # AI Prompt Logic
        llm_prompt = (
            f"Generate a comprehensive packing list with 8-12 essential items for a trip to {selected_trip.destination} "
            f"considering general weather and duration. "
            f"Provide comma-separated items ONLY (e.g., 'socks, jacket, toothbrush'). No other text."
        )
        
        ai_response = call_llm_api(llm_prompt)
        
        if ai_response and "AI functionality is disabled" not in ai_response and "Error" not in ai_response:
            generated_items = [item.strip().replace('.', '') for item in ai_response.split(',') if item.strip()]
            generated_ai_suggestions = generated_items
        else:
            generated_ai_suggestions = [] # Fail silently or show generic list
    else:
        generated_ai_suggestions = ["Select a trip to see suggestions."]

    return render_template('packing_list.html', 
                           current_packing_list=current_packing_list, 
                           ai_packing_list=generated_ai_suggestions,
                           user_trips=user_trips, 
                           selected_trip_id=selected_trip.id if selected_trip else None)


@dash_bp.route('/delete_packing_item/<int:item_id>', methods=['POST'])
@login_required
def delete_packing_item(item_id):
    """
    Deletes an item from the packing list from the database.
    """
    item = PackingItem.query.get_or_404(item_id)
    if item.trip and item.trip.user_id != current_user.id:
        flash("Unauthorized action.", "danger")
        return redirect(url_for('dashboard.packing_list'))
    
    # Determine a safe display name for the item (models may use 'item_name' or 'name')
    item_display_name = getattr(item, 'item_name', None) or getattr(item, 'name', None) or 'Item'
    
    db.session.delete(item)
    db.session.commit()
    flash(f'"{item_display_name}" removed from packing list!', 'success')
    return redirect(url_for('dashboard.packing_list', trip_id=item.trip_id)) # Redirect back to the correct trip's list


@dash_bp.route('/budget_estimator', methods=['GET', 'POST'])
@login_required
def budget_estimator():
    """
    Calculates and displays an estimated budget based on user inputs.
    Integrates AI to generate budget summaries/tips.
    """
    total = None
    ai_budget_summary = None

    breakdown = {
        'Transport': 0.0,
        'Lodging': 0.0,
        'Food': 0.0,
        'Activities': 0.0
    }

    if request.method == 'POST':
        try:
            transport_cost = float(request.form.get('transport', 0))
            lodging_cost = float(request.form.get('lodging', 0))
            food_cost = float(request.form.get('food', 0))
            activities_cost = float(request.form.get('activities', 0))

            total = transport_cost + lodging_cost + food_cost + activities_cost
            breakdown = {
                'Transport': transport_cost,
                'Lodging': lodging_cost,
                'Food': food_cost,
                'Activities': activities_cost
            }
            flash('Budget estimated successfully!', 'success')

            budget_prompt = (
                f"Given the following estimated travel budget breakdown:\n"
                f"Transport: ₹{transport_cost:,.2f}\n"
                f"Lodging: ₹{lodging_cost:,.2f}\n"
                f"Food: ₹{food_cost:,.2f}\n"
                f"Activities: ₹{activities_cost:,.2f}\n"
                f"Total estimated budget: ₹{total:,.2f}\n\n"
                f"Please provide a brief budget summary and 2-3 actionable tips to potentially save money or optimize spending in a concise paragraph. Focus on the areas with highest costs or where savings are most likely. Ensure the response is a complete, well-formed paragraph."
            )
            print(f"DEBUG: Budget AI Prompt: {budget_prompt}")
            ai_response = call_llm_api(budget_prompt)

            if ai_response and "AI functionality is disabled" not in ai_response and "Error from AI" not in ai_response:
                ai_budget_summary = ai_response
                print(f"DEBUG: Budget AI Summary for template: {ai_budget_summary}")
            else:
                ai_budget_summary = "AI budget tips not available: " + ai_response
                print(f"DEBUG: Budget AI Summary set to error message: {ai_budget_summary}")

        except ValueError:
            flash('Please enter valid numerical values for all costs.', 'danger')

    print(f"DEBUG: Final breakdown object sent to template: {breakdown}")
    return render_template('budget_estimator.html', total=total, breakdown=breakdown, ai_budget_summary=ai_budget_summary)


@dash_bp.route('/itinerary_builder/<int:trip_id>', methods=['GET', 'POST'])
@login_required
def itinerary_builder(trip_id):
    """
    Manages the itinerary for a specific trip, allowing adding and deleting activities.
    """
    print(f"DEBUG: Itinerary Builder route accessed for trip_id: {trip_id}")
    trip = Trip.query.get_or_404(trip_id)
    if trip.user_id != current_user.id:
        flash("Unauthorized access. You can only manage itineraries for your own trips.", "danger")
        return redirect(url_for('dashboard.show_dashboard'))
    print(f"DEBUG: Trip found for itinerary builder: {trip.title}")

    all_itinerary_items = ItineraryItem.query.filter_by(trip_id=trip_id).order_by(ItineraryItem.date, ItineraryItem.time).all()

    itinerary_by_day = {}
    for item in all_itinerary_items:
        date_str = item.date.strftime('%Y-%m-%d')
        if date_str not in itinerary_by_day:
            itinerary_by_day[date_str] = []
        itinerary_by_day[date_str].append(item)
    
    itinerary_for_template = []
    for date_str in sorted(itinerary_by_day.keys()):
        itinerary_for_template.append({
            'date': date_str,
            'activities_list': itinerary_by_day[date_str]
        })
    print(f"DEBUG: Itinerary data for template: {itinerary_for_template}")

    ai_itinerary_suggestions = None
    if request.method == 'GET': 
        # PROMPT REFINEMENT for LLM to ensure more robust itinerary suggestions
        ai_prompt = (
            f"Suggest 3-5 daily activities for a trip to {trip.destination} "
            f"from {trip.start_date} to {trip.end_date}. "
            f"Consider typical tourist attractions, local experiences, and the trip duration. "
            f"Format as 'Day X: Activity 1, Activity 2, Activity 3'. Each day on a new line. "
            f"e.g., 'Day 1: Explore Eiffel Tower, Visit Louvre, Dinner at a local bistro\nDay 2: Take a Seine River cruise, See the Arc de Triomphe, Shop on Champs-Élysées'. "
            f"Do NOT include any other text or introductory phrases. Ensure the response is complete for all suggested days."
        )
        ai_response = call_llm_api(ai_prompt)
        if ai_response and "AI functionality is disabled" not in ai_response and "Error from AI" not in ai_response:
            ai_itinerary_suggestions = ai_response.split('\n')
        else:
            ai_itinerary_suggestions = ["AI suggestions not available for this trip: " + ai_response]

    return render_template('itinerary_builder.html', 
                           trip=trip, 
                           itinerary=itinerary_for_template,
                           ai_itinerary_suggestions=ai_itinerary_suggestions)


@dash_bp.route('/itinerary/add_activity/<int:trip_id>', methods=['POST'])
@login_required
def add_activity(trip_id):
    """Adds a new activity to a trip's itinerary."""
    trip = Trip.query.get_or_404(trip_id)
    if trip.user_id != current_user.id:
        flash("Unauthorized action.", "danger")
        return redirect(url_for('dashboard.show_dashboard'))

    activity_date_str = request.form.get('date')
    activity_time = request.form.get('time')
    activity_description = request.form.get('description')

    if not all([activity_date_str, activity_description]):
        flash("Date and Description are required for an itinerary item.", "danger")
        return redirect(url_for('dashboard.itinerary_builder', trip_id=trip_id))

    try:
        activity_date = datetime.strptime(activity_date_str, '%Y-%m-%d').date()
    except ValueError:
        flash("Invalid date format. Please use YYYY-MM-DD.", "danger")
        return redirect(url_for('dashboard.itinerary_builder', trip_id=trip_id))

    new_item = ItineraryItem(
        trip_id=trip_id,
        date=activity_date,
        time=activity_time if activity_time else None,
        description=activity_description
    )
    db.session.add(new_item)
    db.session.commit()
    flash('Activity added to itinerary successfully!', 'success')
    return redirect(url_for('dashboard.itinerary_builder', trip_id=trip_id))

@dash_bp.route('/itinerary/delete_activity/<int:activity_id>', methods=['POST'])
@login_required
def delete_activity(activity_id):
    """Deletes an activity from a trip's itinerary."""
    item = ItineraryItem.query.get_or_404(activity_id)
    if item.trip and item.trip.user_id != current_user.id:
        flash("Unauthorized action.", "danger")
        return redirect(url_for('dashboard.show_dashboard'))
    
    trip_id = item.trip_id
    db.session.delete(item)
    db.session.commit()
    flash('Activity removed from itinerary!', 'success')
    return redirect(url_for('dashboard.itinerary_builder', trip_id=trip_id))


@dash_bp.route('/trip_summary/<int:trip_id>')
@login_required
def trip_summary(trip_id):
    """
    Displays a summary of a specific trip, including its details,
    itinerary, packing list, budget, and notes.
    """
    print(f"DEBUG: trip_summary route received trip_id: {trip_id}")
    trip = Trip.query.get_or_404(trip_id)

    if trip.user_id != current_user.id:
        flash("Unauthorized access. You can only view summaries for your own trips.", "danger")
        return redirect(url_for('dashboard.show_dashboard'))
    
    print(f"DEBUG: Fetched trip object: {trip.title}, {trip.destination}, {trip.start_date}, {trip.end_date}, {trip.budget}")

    try:
        trip.start_date_obj = datetime.strptime(trip.start_date, '%Y-%m-%d').date()
        trip.end_date_obj = datetime.strptime(trip.end_date, '%Y-%m-%d').date()
    except ValueError as e:
        print(f"ERROR: Date parsing error in trip_summary for trip {trip.id}: {e}")
        trip.start_date_obj = None
        trip.end_date_obj = None

    total_budget = trip.budget

    # Fetch custom packing items for THIS specific trip
    packing_items_for_template = PackingItem.query.filter_by(trip_id=trip.id, is_ai_generated=False).all()
    # Ensure robust attribute access: models may use 'item_name' or 'name'
    packing_item_names = [getattr(item, 'item_name', None) or getattr(item, 'name', None) or 'Unknown' for item in packing_items_for_template]
    print(f"DEBUG: Custom Packing items for trip {trip.id}: {packing_item_names}")


    ai_packing_list_for_summary = []
    if trip.start_date_obj and trip.end_date_obj:
        # PROMPT REFINEMENT for LLM to ensure more complete packing list
        ai_prompt = (
            f"Generate a comprehensive packing list with 8-12 essential items for a trip to {trip.destination} from {trip.start_date_obj.strftime('%Y-%m-%d')} to {trip.end_date_obj.strftime('%Y-%m-%d')}. Consider general weather and typical travel needs. Provide the list as comma-separated items ONLY, e.g., 'socks, underwear, t-shirts, jacket, toiletries, phone charger, swimsuit, hat, sunglasses, comfortable shoes, small backpack'. Do NOT include any other text or introductory phrases. Ensure the list is complete and not cut off."
        )
        ai_response_content = call_llm_api(ai_prompt)
        
        if isinstance(ai_response_content, str) and "AI functionality is disabled" not in ai_response_content and "Error from AI" not in ai_response_content:
            ai_packing_list_for_summary = [item.strip().replace('.', '') for item in ai_response_content.split(',') if item.strip()]
        else:
            ai_packing_list_for_summary = ["AI suggestions not available for this trip: " + str(ai_response_content)]
        
    else:
        ai_packing_list_for_summary = ["AI suggestions not available due to date format issues for this trip."]

    print(f"DEBUG: AI Packing items for trip {trip.id} (summary): {ai_packing_list_for_summary}")


    itinerary_items_db = ItineraryItem.query.filter_by(trip_id=trip_id).order_by(ItineraryItem.date, ItineraryItem.time).all()
    itinerary_summary_data = {}
    for item in itinerary_items_db:
        date_key = item.date.strftime('%Y-%m-%d')
        if date_key not in itinerary_summary_data:
            itinerary_summary_data[date_key] = []
        time_str = f"{item.time} - " if item.time else ""
        itinerary_summary_data[date_key].append(f"{time_str}{item.description}")
    
    itinerary_for_template = []
    for date_str in sorted(itinerary_summary_data.keys()):
        itinerary_for_template.append({
            'date': date_str,
            'activities': itinerary_summary_data[date_str]
        })
    print(f"DEBUG: Itinerary for summary: {itinerary_for_template}")


    trip_note_obj = TripNote.query.filter_by(trip_id=trip_id).first()
    notes_content = trip_note_obj.content if trip_note_obj and trip_note_obj.content else "No specific notes for this trip yet."
    print(f"DEBUG: Notes content for summary: {notes_content[:50]}...")


    share_link = url_for('dashboard.trip_summary', trip_id=trip.id, _external=True)

    return render_template(
        'trip_summary.html',
        trip=trip,
        total_budget=total_budget,
        itinerary=itinerary_for_template,
        packing_items=packing_items_for_template,
        ai_packing_list=ai_packing_list_for_summary,
        notes=notes_content,
        share_link=share_link
    )

@dash_bp.route('/trip_notes/<int:trip_id>', methods=['GET', 'POST'])
@login_required
def trip_notes(trip_id):
    """
    Allows users to save and view trip notes and upload documents for a specific trip.
    """
    print(f"DEBUG: Trip Notes route accessed for trip_id: {trip_id}")
    trip = Trip.query.get_or_404(trip_id)
    if trip.user_id != current_user.id:
        flash("Unauthorized access. You can only view/edit notes for your own trips.", "danger")
        return redirect(url_for('dashboard.show_dashboard'))
    print(f"DEBUG: Trip found for notes: {trip.title}")

    trip_note_obj = TripNote.query.filter_by(trip_id=trip_id).first()
    current_notes_content = trip_note_obj.content if trip_note_obj else ""

    return render_template('trip_notes.html', trip=trip, notes=current_notes_content)

@dash_bp.route('/trip_notes/save/<int:trip_id>', methods=['POST'])
@login_required
def save_notes_docs(trip_id):
    """
    Handles saving trip notes and uploading documents for a specific trip.
    """
    trip = Trip.query.get_or_404(trip_id)
    if trip.user_id != current_user.id:
        flash("Unauthorized action.", "danger")
        return redirect(url_for('dashboard.show_dashboard'))

    notes_text = request.form.get('notes')
    file = request.files.get('doc')

    trip_note_obj = TripNote.query.filter_by(trip_id=trip_id).first()
    if trip_note_obj:
        trip_note_obj.content = notes_text
    else:
        new_note = TripNote(trip_id=trip_id, content=notes_text)
        db.session.add(new_note)
    db.session.commit()
    flash("Trip notes saved successfully.", "success")

    if file and file.filename != '':
        if 'UPLOAD_FOLDER' not in current_app.config:
            flash("UPLOAD_FOLDER is not configured. File upload disabled.", "danger")
        else:
            filename = secure_filename(file.filename)
            upload_folder = current_app.config['UPLOAD_FOLDER']
            os.makedirs(upload_folder, exist_ok=True)
            filepath = os.path.join(upload_folder, filename)
            try:
                file.save(filepath)
                flash(f"Document '{filename}' uploaded successfully.", "success")
            except Exception as e:
                flash(f"Error saving file: {e}", "danger")
    else:
        if not notes_text: 
            flash("No document selected for upload and no notes provided.", "info")

    return redirect(url_for('dashboard.trip_notes', trip_id=trip_id))
# Add these imports to the top of dashboard.py
import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app
from app import db
# ... (your other routes) ...

@dash_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        # --- Handle Profile Image Upload ---
        profile_pic = request.files.get('profile_image')
        if profile_pic and profile_pic.filename != '':
            # Create a secure and unique filename
            filename = secure_filename(profile_pic.filename)
            pic_name = str(uuid.uuid1()) + "_" + filename
            
            # Define the path and ensure the folder exists
            upload_folder = current_app.config['UPLOAD_FOLDER']
            os.makedirs(upload_folder, exist_ok=True)
            
            # Delete old picture if it's not the default
            if current_user.profile_image and current_user.profile_image != 'default.jpg':
                old_pic_path = os.path.join(upload_folder, current_user.profile_image)
                if os.path.exists(old_pic_path):
                    os.remove(old_pic_path)
            print(f"Saving profile image to: {os.path.join(upload_folder, pic_name)}")
            # Save the new picture
            profile_pic.save(os.path.join(upload_folder, pic_name))
            
            # Update the database record
            current_user.profile_image = pic_name
            flash('Profile picture updated!', 'success')

        # --- Update Basic Information ---
        current_user.name = request.form.get('name')
        current_user.email = request.form.get('email')
        current_user.username = request.form.get('username')
        current_user.phone_number = request.form.get('phone_number')

        # --- Update Security: Password ---
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        if new_password:
            if new_password == confirm_password:
                current_user.set_password(new_password)
                flash('Password updated successfully!', 'success')
            else:
                flash('New password and confirmation do not match.', 'danger')
                return redirect(url_for('dashboard.profile'))

        # --- Update Smart Tourist Safety System ---
        current_user.emergency_contact_name = request.form.get('emergency_contact_name')
        current_user.emergency_contact_number = request.form.get('emergency_contact_number')
        current_user.emergency_contact_email = request.form.get('emergency_contact_email')  # ✅ FIX
        current_user.is_real_time_tracking_enabled = 'tracking_enabled' in request.form
        current_user.preferred_language = request.form.get('preferred_language')

        # --- Commit All Changes to Database ---
        try:
            db.session.commit()
            flash('Profile details updated successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while updating your profile: {e}', 'danger')

        return redirect(url_for('dashboard.profile'))

    # For GET requests, just render the page
    return render_template('profile.html', user=current_user)

from app.models import SafetyAlert,LocationHistory # Make sure these are imported
from datetime import datetime

@dash_bp.route('/report_safety_alert', methods=['GET', 'POST'])
@login_required
def report_safety_alert():
    if request.method == 'POST':
        alert_type = request.form.get('alert_type')
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')
        details = request.form.get('details')

        if not all([alert_type, latitude, longitude]):
            flash('Please provide all required information for the alert.', 'danger')
            return redirect(url_for('dashboard.report_safety_alert'))

        try:
            new_alert = SafetyAlert(
                user_id=current_user.id,
                alert_type=alert_type,
                latitude=float(latitude),
                longitude=float(longitude),
                details=details,
                timestamp=datetime.utcnow()
            )
            db.session.add(new_alert)
            db.session.commit()
            flash('Safety alert reported successfully!', 'success')
            return redirect(url_for('dashboard.show_dashboard'))
        except ValueError:
            flash('Invalid latitude or longitude values.', 'danger')
            return redirect(url_for('dashboard.report_safety_alert'))
            
    return render_template('report_safety_alert.html')
@dash_bp.route('/safety_map')
@login_required
def safety_map():
    # 1. Fetch alerts (which have lat/lng data)
    safety_alerts = SafetyAlert.query.order_by(SafetyAlert.timestamp.desc()).all()
    
    # 2. Prepare data for the map (Leaflet needs clean JSON-serializable data)
    alerts_data = []
    for alert in safety_alerts:
        if alert.latitude and alert.longitude:
            alerts_data.append({
                'id': alert.id,
                'type': alert.alert_type,
                'lat': alert.latitude,
                'lng': alert.longitude,
                'details': alert.details
            })
    
    # 3. Pass 'alerts' to the template (NOT locations)
    return render_template('safety_map.html', alerts=alerts_data)

@dash_bp.route('/safety_settings', methods=['GET', 'POST'])
@login_required
def safety_settings():
    """Tourist safety settings and preferences"""
    if request.method == 'POST':
        # Update safety preferences
        current_user.is_real_time_tracking_enabled = bool(request.form.get('tracking_enabled'))
        current_user.preferred_language = request.form.get('preferred_language', 'en')
        
        # Update emergency contact info
        emergency_name = request.form.get('emergency_name')
        emergency_number = request.form.get('emergency_number')
        
        if emergency_name and emergency_number:
            current_user.emergency_contact_name = emergency_name
            current_user.emergency_contact_number = emergency_number
        
        db.session.commit()
        flash('Safety settings updated successfully!', 'success')
        return redirect(url_for('dashboard.show_dashboard'))
    
    return render_template('safety_settings.html')
@dash_bp.route('/trip/delete/<int:trip_id>', methods=['POST'])
@login_required
def delete_trip(trip_id):
    trip = Trip.query.get_or_404(trip_id)

    # Security check
    if trip.user_id != current_user.id:
        flash("Unauthorized action.", "danger")
        return redirect(url_for('dashboard.show_dashboard'))

    try:
        trip_title = trip.title

        db.session.delete(trip)
        db.session.commit()

        flash(f"Trip '{trip_title}' deleted successfully.", "success")
        print(f"✅ Trip deleted: {trip_title}")

    except Exception as e:
        db.session.rollback()
        print(f"❌ ERROR deleting trip: {e}")
        flash("Failed to delete trip.", "danger")

    return redirect(url_for('dashboard.show_dashboard'))
