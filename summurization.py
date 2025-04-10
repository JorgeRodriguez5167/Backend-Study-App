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


def summarize_and_categorize(text):
    """
    Summarizes and categorizes the given text using Gemini 1.5 Flash.

    Args:
        text (str): The text to process.

    Returns:
        tuple: A tuple containing the summary (str) and category (str),
               or descriptive error strings if an issue occurs.
    """
    print("\nAttempting to generate summary and category...") # Indicate progress
    try:
        # Initialize the generative model
        model = genai.GenerativeModel('gemini-1.5-flash-latest')

        # Define the prompt with clear instructions for the desired format
        prompt = f"""
        Analyze the following text and provide only a concise summary and a relevant category label.
        Follow this format exactly, with each part on a new line:
        Summary: [Your summary here]
        Category: [Your category label here]

        Text:
        ```
        {text}
        ```
        """

        # Generate the content
        response = model.generate_content(prompt)
        response_text = response.text
        print(f"Model Response:\n---\n{response_text}\n---")

        # --- Robust Parsing Logic ---
        summary_marker = "Summary:"
        category_marker = "Category:"

        summary_start_index = response_text.find(summary_marker)
        category_start_index = response_text.find(category_marker)

        # Check if both markers were found
        if summary_start_index != -1 and category_start_index != -1:
            # Extract summary: starts after "Summary:", ends before "Category:"
            summary_content_start = summary_start_index + len(summary_marker)
            summary = response_text[summary_content_start:category_start_index].strip()

            # Extract category: starts after "Category:", goes to end of string
            category_content_start = category_start_index + len(category_marker)
            category = response_text[category_content_start:].strip()

            # Basic cleanup: take the first line in case the model adds extra newlines
            summary = summary.split('\n')[0].strip()
            category = category.split('\n')[0].strip()

            # Check if extraction yielded non-empty results
            if summary and category:
                print("Successfully parsed summary and category.")
                return summary, category
            else:
                 print("Warning: Markers found, but parsing resulted in empty strings.")
                 return "Could not parse non-empty summary/category from response", "Parsing Error"
        else:
            # Log the failure to find markers
            print(f"Error: Could not find '{summary_marker}' or '{category_marker}' in response.")
            return "Could not parse summary/category from response format", "Parsing Error"

    # --- Error Handling ---
    except Exception as e:
        # Log the specific error for debugging purposes
        print(f"An error occurred during API call or processing: {e}")
        # Return a user-friendly error message and category
        return f"An error occurred processing the text.", f"Error: {type(e).__name__}"

