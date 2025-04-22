import google.generativeai as genai
import os
from dotenv import load_dotenv # Used to load variables from a .env file

# acessing environemnet for the key
load_dotenv()

# Retrieve the API key securely from environment variables
# The actual key string is NOT written in this code.
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Check if the key was loaded successfully
if not GOOGLE_API_KEY:
    # Stop if the key isn't found, providing a helpful error message.
    raise ValueError("API key not found. Ensure the 'GOOGLE_API_KEY' environment variable is set correctly (e.g., in your .env file or system environment).")
else:
    genai.configure(api_key=GOOGLE_API_KEY)
    print("API Key configured successfully.") 


def summarize_text(text):
    """
    Summarizes the given text using Gemini 1.5 Flash.

    Args:
        text (str): The text to process.

    Returns:
        str: A concise summary of the text,
             or a descriptive error string if an issue occurs.
    """
    print("\nAttempting to generate summary...") # Indicate progress
    try:
        # Initialize the generative model
        model = genai.GenerativeModel('gemini-1.5-flash-latest')

        # Define the prompt with clear instructions
        prompt = f"""
        Provide a concise summary of the following text:

        Text:
        ```
        {text}
        ```
        
        Summary:
        """

        # Generate the content
        response = model.generate_content(prompt)
        summary = response.text.strip()
        print(f"Generated summary:\n---\n{summary}\n---")

        return summary

    # --- Error Handling ---
    except Exception as e:
        # Log the specific error for debugging purposes
        print(f"An error occurred during API call or processing: {e}")
        # Return a user-friendly error message
        return f"An error occurred processing the text: {type(e).__name__}"


# For backward compatibility
def summarize_and_categorize(text):
    """Legacy function that returns summary and a default category"""
    summary = summarize_text(text)
    return summary, "General"

