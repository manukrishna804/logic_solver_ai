import os
import google.generativeai as genai
from flask import Flask, request, jsonify
from flask_cors import CORS

# Initialize Flask app
app = Flask(__name__)
# Enable CORS for the frontend to communicate with this server
CORS(app)

# Configure the Gemini API with your API key
# It's recommended to set your API key as an environment variable
# If not, you can replace os.getenv('GOOGLE_API_KEY') with your key
API_KEY = os.getenv('GOOGLE_API_KEY')
if not API_KEY:
    print("Warning: GOOGLE_API_KEY environment variable not set. Please set it or hardcode your API key.")
    # For demonstration purposes, you can uncomment the line below and add your key
    # API_KEY = "YOUR_API_KEY"
genai.configure(api_key=API_KEY)

# Initialize the Generative Model
gemini_model = genai.GenerativeModel('gemini-1.5-flash-latest')

@app.route('/generate-algorithm', methods=['POST'])
def generate_algorithm_endpoint():
    """
    Receives a coding problem from the frontend and generates an algorithm.
    """
    try:
        # Get the problem from the request body
        data = request.json
        coding_question = data.get('coding_question')

        if not coding_question:
            return jsonify({'error': 'No coding question provided.'}), 400

        # Define the prompt for the Gemini model
        prompt = f"Generate a concise, step-by-step algorithm for the following coding problem. The first step should always be 'Start' and the last step should be 'End'. The output should be a single markdown list with no extra headings or text, just the algorithm. Use a numbered list."
        
        # Generate content using the Gemini API
        response = gemini_model.generate_content(
            prompt,
            tools=[{"google_search": {}}]
        )

        # Extract the generated text from the response
        algorithm_text = response.text
        
        # Return the algorithm text as a JSON response
        return jsonify({'algorithm': algorithm_text})

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({'error': 'An internal server error occurred.'}), 500

if __name__ == '__main__':
    # Run the Flask app on a specific port
    app.run(debug=True, port=5000)
