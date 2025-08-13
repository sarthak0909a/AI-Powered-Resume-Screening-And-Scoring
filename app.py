import re
import json
import requests
from flask import Flask, request, jsonify, render_template
import io
from docx import Document # For .docx parsing
from PyPDF2 import PdfReader # For .pdf parsing

app = Flask(__name__)

# Function to extract keywords from text
def extract_keywords(text):
    # Convert to lowercase and remove non-alphanumeric characters
    text = text.lower()
    # A simple regex to find words, could be improved for specific domains
    # This will capture sequences of letters and numbers, good for skills like 'python3', 'aws-lambda'
    keywords = set(re.findall(r'\b[a-z0-9_.-]+\b', text))
    # Remove common stop words or very short words that are unlikely to be meaningful keywords
    stop_words = {'a', 'an', 'the', 'and', 'or', 'in', 'on', 'at', 'for', 'to', 'with', 'is', 'are', 'was', 'were', 'be', 'of', 'from', 'by', 'as', 'it', 'its', 'he', 'she', 'they', 'we', 'you', 'your', 'our', 'my', 'me', 'us', 'him', 'her', 'them', 'this', 'that', 'these', 'those', 'can', 'will', 'would', 'should', 'could', 'has', 'have', 'had', 'do', 'does', 'did', 'not', 'no', 'yes', 'but', 'if', 'then', 'than', 'such', 'so', 'very', 'just', 'only', 'also', 'more', 'less', 'most', 'least', 'many', 'few', 'much', 'little', 'about', 'above', 'across', 'after', 'against', 'along', 'among', 'around', 'before', 'behind', 'below', 'beneath', 'beside', 'between', 'beyond', 'during', 'except', 'inside', 'into', 'near', 'off', 'out', 'outside', 'over', 'past', 'through', 'under', 'up', 'down', 'while', 'where', 'when', 'why', 'how', 'all', 'any', 'both', 'each', 'every', 'some', 'none', 'nothing', 'something', 'anything', 'everything', 'who', 'whom', 'whose', 'which', 'what', 'where', 'when', 'why', 'how', 'here', 'there', 'whence', 'whereby', 'wherein', 'whereupon', 'wherever', 'whither', 'whoever', 'whomever', 'whosever', 'whatever', 'whichever', 'whenever', 'wherever', 'however', 'therefore', 'consequently', 'accordingly', 'thus', 'hence', 'meanwhile', 'otherwise', 'unless', 'until', 'upon', 'within', 'without', 'via', 'etc', 'e.g', 'i.e', 'vs', 'etc.', 'i.e.', 'e.g.'}
    keywords = {word for word in keywords if word not in stop_words and len(word) > 2}
    return keywords

# Function to score resume based on job description
def score_resume(job_description_text, resume_text):
    """
    Scores a resume against a job description based on keyword matching.

    Args:
        job_description_text (str): The text of the job description.
        resume_text (str): The text of the resume.

    Returns:
        dict: A dictionary containing:
            - 'score' (float): The matching score (0-100%).
            - 'matched_keywords' (list): Keywords from JD found in resume.
            - 'missing_keywords' (list): Keywords from JD NOT found in resume.
    """
    if not job_description_text or not resume_text:
        return {
            'score': 0.0,
            'matched_keywords': [],
            'missing_keywords': [],
            'error': 'Both job description and resume text are required.'
        }

    # Extract keywords from both texts
    jd_keywords = extract_keywords(job_description_text)
    resume_keywords = extract_keywords(resume_text)

    # Find common keywords
    matched_keywords = list(jd_keywords.intersection(resume_keywords))

    # Find keywords present in JD but not in resume
    missing_keywords = list(jd_keywords.difference(resume_keywords))

    # Calculate score
    total_jd_keywords = len(jd_keywords)
    if total_jd_keywords == 0:
        score = 0.0
    else:
        score = (len(matched_keywords) / total_jd_keywords) * 100

    return {
        'score': score,
        'matched_keywords': matched_keywords,
        'missing_keywords': missing_keywords
    }

@app.route('/')
def index():
    """Renders the main HTML page."""
    return render_template('index.html')

@app.route('/upload_resume', methods=['POST'])
def upload_resume():
    """
    API endpoint to handle resume file uploads (.txt, .pdf, .docx)
    and extract text content.
    """
    if 'resume_file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400

    file = request.files['resume_file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    extracted_text = ""
    try:
        if file.filename.endswith('.txt'):
            extracted_text = file.read().decode('utf-8')
        elif file.filename.endswith('.pdf'):
            reader = PdfReader(io.BytesIO(file.read()))
            for page in reader.pages:
                extracted_text += page.extract_text() + "\n"
        elif file.filename.endswith('.docx'):
            document = Document(io.BytesIO(file.read()))
            for paragraph in document.paragraphs:
                extracted_text += paragraph.text + "\n"
        else:
            return jsonify({'error': 'Unsupported file type. Please upload .txt, .pdf, or .docx.'}), 400

        return jsonify({'extracted_text': extracted_text})

    except Exception as e:
        print(f"Error processing uploaded file: {e}")
        return jsonify({'error': f'Failed to process file: {str(e)}. Ensure it is a valid text-based document.'}), 500


@app.route('/score_resume', methods=['POST'])
def api_score_resume():
    """
    API endpoint to receive job description and resume text,
    and return a matching score and keyword details.
    """
    data = request.get_json()
    job_description = data.get('job_description', '')
    resume_text = data.get('resume_text', '')

    if not job_description or not resume_text:
        return jsonify({'error': 'Both job_description and resume_text are required.'}), 400

    result = score_resume(job_description, resume_text)

    # Check if the scoring function returned an error message
    if 'error' in result:
        return jsonify({'error': result['error']}), 400

    return jsonify(result)

# IMPORTANT: Replace "YOUR_API_KEY_HERE" with your actual Google Cloud API Key
# This key is necessary for the AI features to work when running locally.
# When running in the Canvas environment, this variable is automatically populated.
GOOGLE_API_KEY = "AIzaSyBX7R4vw5Y4LgWNTorvuNohNvown04pb0I" # Leave empty if running in Canvas, otherwise put your key here

@app.route('/analyze_resume_ai', methods=['POST'])
def analyze_resume_ai():
    """
    API endpoint to analyze resume using Gemini AI model.
    """
    data = request.get_json()
    job_description = data.get('job_description', '')
    resume_text = data.get('resume_text', '')

    if not job_description or not resume_text:
        return jsonify({'error': 'Both job_description and resume_text are required for AI analysis.'}), 400

    prompt = f"""
    Analyze the following resume against the provided job description.
    Provide a concise summary, list key strengths, and list areas for improvement.
    Format the output as a JSON object with keys: "summary", "strengths" (list of strings), and "weaknesses" (list of strings).

    Job Description:
    {job_description}

    Resume Text:
    {resume_text}
    """

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "summary": {"type": "STRING"},
                    "strengths": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"}
                    },
                    "weaknesses": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"}
                    }
                },
                "propertyOrdering": ["summary", "strengths", "weaknesses"]
            }
        }
    }

    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GOOGLE_API_KEY}"

    try:
        print(f"Sending payload to analyze_resume_ai:\n{json.dumps(payload, indent=2)}") # Debug print
        response = requests.post(api_url, json=payload)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        result = response.json()

        if result.get('candidates') and result['candidates'][0].get('content') and result['candidates'][0]['content'].get('parts'):
            ai_output_json_str = result['candidates'][0]['content']['parts'][0]['text']
            ai_analysis = json.loads(ai_output_json_str)
            return jsonify(ai_analysis)
        else:
            return jsonify({'error': 'Unexpected AI response structure or missing content.'}), 500

    except requests.exceptions.RequestException as e:
        print(f"Error calling Gemini API for analysis: {e}") # Specific error message
        return jsonify({'error': f'Failed to get AI analysis: {str(e)}'}), 500
    except json.JSONDecodeError as e:
        print(f"Error parsing AI response JSON for analysis: {e}") # Specific error message
        print(f"Raw AI response that failed to parse: {response.text if 'response' in locals() else 'No response text available'}")
        return jsonify({'error': f'Failed to parse AI analysis response: {str(e)}'}), 500
    except Exception as e:
        print(f"An unexpected error occurred during AI analysis: {e}")
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500


@app.route('/generate_interview_questions', methods=['POST'])
def generate_interview_questions():
    """
    API endpoint to generate interview questions using Gemini AI model.
    """
    data = request.get_json()
    job_description = data.get('job_description', '')
    resume_text = data.get('resume_text', '')

    if not job_description or not resume_text:
        return jsonify({'error': 'Both job_description and resume_text are required to generate questions.'}), 400

    prompt = f"""
    Generate 5-7 relevant interview questions based on the following job description and candidate's resume.
    Focus on behavioral, technical, and situational questions that assess their fit for the role.
    The output must be a JSON object with a single key "questions" which contains an array of strings.

    Example JSON Output:
    {{
      "questions": [
        "Question 1?",
        "Question 2?",
        "Question 3?"
      ]
    }}

    Job Description:
    {job_description}

    Resume Text:
    {resume_text}
    """

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "questions": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"}
                    }
                },
                "propertyOrdering": ["questions"]
            }
        }
    }

    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GOOGLE_API_KEY}"

    try:
        print(f"Sending payload to generate_interview_questions:\n{json.dumps(payload, indent=2)}") # Debug print
        response = requests.post(api_url, json=payload)
        response.raise_for_status()
        result = response.json()

        if result.get('candidates') and result['candidates'][0].get('content') and result['candidates'][0]['content'].get('parts'):
            ai_output_json_str = result['candidates'][0]['content']['parts'][0]['text']
            questions_data = json.loads(ai_output_json_str)
            return jsonify(questions_data)
        else:
            return jsonify({'error': 'Unexpected AI response structure or missing content for questions.'}), 500

    except requests.exceptions.RequestException as e:
        print(f"Error calling Gemini API for questions: {e}")
        return jsonify({'error': f'Failed to generate interview questions: {str(e)}'}), 500
    except json.JSONDecodeError as e:
        print(f"Error parsing AI questions response JSON: {e}")
        print(f"Raw AI questions response that failed to parse: {response.text if 'response' in locals() else 'No response text available'}")
        return jsonify({'error': f'Failed to parse interview questions response: {str(e)}'}), 500
    except Exception as e:
        print(f"An unexpected error occurred during interview question generation: {e}")
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500


@app.route('/suggest_resume_improvements', methods=['POST'])
def suggest_resume_improvements():
    """
    API endpoint to suggest resume improvements using Gemini AI model.
    """
    data = request.get_json()
    job_description = data.get('job_description', '')
    resume_text = data.get('resume_text', '')

    if not job_description or not resume_text:
        return jsonify({'error': 'Both job_description and resume_text are required to suggest improvements.'}), 400

    prompt = f"""
    Based on the following job description and candidate's resume, provide specific and actionable suggestions
    to improve the resume's alignment with the role. Focus on content, keywords, and presentation.
    The output must be a JSON object with a single key "suggestions" which contains an array of strings.

    Example JSON Output:
    {{
      "suggestions": [
        "Suggestion 1.",
        "Suggestion 2.",
        "Suggestion 3."
      ]
    }}

    Job Description:
    {job_description}

    Resume Text:
    {resume_text}
    """

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "suggestions": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"}
                    }
                },
                "propertyOrdering": ["suggestions"]
            }
        }
    }

    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GOOGLE_API_KEY}"

    try:
        print(f"Sending payload to suggest_resume_improvements:\n{json.dumps(payload, indent=2)}") # Debug print
        response = requests.post(api_url, json=payload)
        response.raise_for_status()
        result = response.json()

        if result.get('candidates') and result['candidates'][0].get('content') and result['candidates'][0]['content'].get('parts'):
            ai_output_json_str = result['candidates'][0]['content']['parts'][0]['text']
            suggestions_data = json.loads(ai_output_json_str)
            return jsonify(suggestions_data)
        else:
            return jsonify({'error': 'Unexpected AI response structure or missing content for suggestions.'}), 500

    except requests.exceptions.RequestException as e:
        print(f"Error calling Gemini API for suggestions: {e}")
        return jsonify({'error': f'Failed to get resume improvement suggestions: {str(e)}'}), 500
    except json.JSONDecodeError as e:
        print(f"Error parsing AI suggestions response JSON: {e}")
        print(f"Raw AI suggestions response that failed to parse: {response.text if 'response' in locals() else 'No response text available'}")
        return jsonify({'error': f'Failed to parse resume improvement suggestions response: {str(e)}'}), 500
    except Exception as e:
        print(f"An unexpected error occurred during resume improvement suggestion generation: {e}")
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500


if __name__ == '__main__':
    app.run(debug=True)
