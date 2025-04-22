import os
import google.generativeai as genai
from sqlmodel import Session, select
from models import Note
from databases import engine
from fastapi import HTTPException
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Configure the Gemini API with your API key
try:
    GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
    if not GOOGLE_API_KEY:
        logger.warning("GOOGLE_API_KEY not found in environment variables")
    genai.configure(api_key=GOOGLE_API_KEY)
except Exception as e:
    logger.error(f"Error configuring Gemini API: {str(e)}")

def get_notes_by_category(category: str):
    """Retrieve all notes with the specified category from the database"""
    try:
        with Session(engine) as session:
            notes = session.exec(
                select(Note).where(Note.category == category)
            ).all()
            return notes
    except Exception as e:
        logger.error(f"Error retrieving notes by category: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

def generate_study_guide(category: str):
    """Generate a study guide from notes with the specified category"""
    # Get all notes with the specified category
    notes = get_notes_by_category(category)
    
    if not notes:
        return f"No notes found for category: {category}"
    
    # Combine the transcriptions from all notes
    combined_content = ""
    for note in notes:
        if note.transcription:
            combined_content += note.transcription + "\n\n"
        if note.summarized_notes:
            combined_content += note.summarized_notes + "\n\n"
    
    if not combined_content.strip():
        return f"No content found in notes for category: {category}"
    
    try:
        # Initialize the Gemini model
        model = genai.GenerativeModel('gemini-pro')
        
        # Create the prompt
        prompt = f"""
        Create a comprehensive study guide based on the following content. 
        Organize the information logically with clear sections, bullet points for key concepts, 
        and examples where appropriate.
        
        CONTENT:
        {combined_content}
        
        Make a study guide for this.
        """
        
        # Generate the study guide
        response = model.generate_content(prompt)
        
        if not response or not hasattr(response, 'text'):
            return "Failed to generate study guide. Please try again later."
        
        return response.text
    
    except Exception as e:
        logger.error(f"Error generating study guide with Gemini API: {str(e)}")
        return f"Error generating study guide: {str(e)}" 