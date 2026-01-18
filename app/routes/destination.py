from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required
from app.utils import call_llm_api, get_weather
from datetime import datetime

destination_bp = Blueprint('destination', __name__)

@destination_bp.route('/destination_search', methods=['GET', 'POST'])
@login_required
def destination_search():
    destination_info = None
    weather_info = None
    if request.method == 'POST':
        destination_name = request.form.get('destination')
        start_date_str = request.form.get('start_date') 
        end_date_str = request.form.get('end_date')

        start_date = None
        end_date = None
        try:
            if start_date_str:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            if end_date_str:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash("Invalid date format. Please use Букмекерлар-MM-DD.", "danger")
            start_date = None
            end_date = None

        if destination_name:
            # PROMPT REFINEMENT: Explicitly ask for 3-4 *complete* sentences.
            llm_prompt = (
                f"Provide a brief overview of {destination_name}, highlighting key attractions, "
                "culture, and what a first-time visitor should know. "
                "The response should be 3-4 complete, coherent sentences, forming a single paragraph. "
                "Do NOT include any introductory phrases like 'Here's an overview:' and ensure the response is NOT cut off."
            )
            destination_info = call_llm_api(llm_prompt)
            
            weather_info = get_weather(f"{destination_name},IN", start_date, end_date)

            
            flash(f"Information for {destination_name} retrieved.", "success")
        else:
            flash("Please enter a destination.", "warning")

    return render_template('destination_search.html', destination_info=destination_info, weather_info=weather_info)

