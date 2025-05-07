import os
import google.generativeai as genai
from sqlmodel import Session, select
from models import Note
from databases import engine
from fastapi import HTTPException
import logging
from dotenv import load_dotenv
#File worked on by Jorge Rdz

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Configure the Gemini API
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Check if the key was loaded successfully
if not GOOGLE_API_KEY:
    logger.error("API key not found. Ensure the 'GOOGLE_API_KEY' environment variable is set correctly.")
else:
    genai.configure(api_key=GOOGLE_API_KEY)
    logger.info("Gemini API Key configured successfully.")

def get_notes_by_category(category: str, user_id: int):
    """Retrieve notes with the specified category belonging to the specified user"""
    try:
        with Session(engine) as session:
            notes = session.exec(
                select(Note).where(
                    (Note.category == category) & 
                    (Note.user_id == user_id)
                )
            ).all()
            logger.info(f"Retrieved {len(notes)} notes for user {user_id} with category '{category}'")
            return notes
    except Exception as e:
        logger.error(f"Error retrieving notes by category and user_id: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

def generate_study_guide(category: str, user_id: int):
    """Generate a study guide from notes with the specified category belonging to the user"""
    # Get notes with the specified category belonging to the user
    notes = get_notes_by_category(category, user_id)
    
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
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        # Create the prompt with clear instructions to create guide
        prompt = f"""
        Create a comprehensive study guide based on the following content. 
        Structure your response with these elements:
        1. Key Concepts: Bullet points of the main ideas and theories
        2. Definitions: Important terms and their meanings
        3. Examples: Practical applications or illustrations of concepts
        4. Summary: A concise overview connecting the main points
        
        CONTENT:
        ```
        {combined_content}
        ```
        
        Make a well-organized study guide for this content.
        """
        
        # Generate the study guide
        response = model.generate_content(prompt)
        
        if not response or not hasattr(response, 'text'):
            return "Failed to generate study guide. Please try again later."
        
        logger.info(f"Successfully generated study guide for user {user_id}, category: {category}")
        return response.text
    
    except Exception as e:
        logger.error(f"Error generating study guide with Gemini API: {str(e)}")
        return f"Error generating study guide: {str(e)}" 