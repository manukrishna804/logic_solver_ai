import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
gemini_model = None
if API_KEY:
    try:
        genai.configure(api_key=API_KEY)
        # For older SDKs, just pass model name as positional argument
        gemini_model = genai.GenerativeModel("gemini-1.5-flash")
    except Exception as e:
        print("Failed to configure Gemini SDK:", e)
else:
    print("Warning: GOOGLE_API_KEY not set. The /generate-algorithm endpoint will return an error until it is configured.")

app = Flask(__name__)
CORS(app)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "api_key_present": bool(API_KEY),
        "model_initialized": gemini_model is not None
    })

@app.route("/generate-algorithm", methods=["POST"])
def generate_algorithm():
    data = request.json
    coding_question = data.get("coding_question")
    if not coding_question:
        return jsonify({"error": "No coding question provided"}), 400

    if gemini_model is None:
        return jsonify({"error": "GOOGLE_API_KEY not set or model not initialized. Set GOOGLE_API_KEY in your environment or .env file and restart the server."}), 500

    prompt = f"""Generate a clear, step-by-step algorithm for: '{coding_question}'

Requirements:
1. Use numbered list format (1., 2., 3., etc.)
2. Each step should be clear and concise
3. Include decision points clearly (use "If", "Else", "While", "For")
4. Include input/output steps
5. Make it easy to follow the logic flow
6. Use proper programming terminology
7. For complex algorithms like binary search, include detailed steps with proper variable tracking
8. Ensure each step is atomic and well-defined

Format example:
1. Start
2. Input: Get the number from user
3. If number % 2 == 0
4. Output: "Number is even"
5. Else
6. Output: "Number is odd"
7. End

For binary search example:
1. Start
2. Input: Get sorted array and target value
3. Initialize left = 0, right = array.length - 1
4. While left <= right
5. Calculate mid = (left + right) / 2
6. If array[mid] == target
7. Return mid (found)
8. Else if array[mid] < target
9. Set left = mid + 1
10. Else
11. Set right = mid - 1
12. Return -1 (not found)
13. End

Generate the algorithm:"""

    try:
        response = gemini_model.generate_content(prompt)
        # Depending on SDK, the output text may be in response.text or response.output_text
        algorithm_text = getattr(response, "text", None) or getattr(response, "output_text", None)
        if not algorithm_text:
            return jsonify({"error": "Failed to generate algorithm"}), 500
        return jsonify({"algorithm": algorithm_text})
    except Exception as e:
        print("Error:", e)
        return jsonify({"error": "Internal server error"}), 500

@app.route("/generate-flowchart", methods=["POST"])
def generate_flowchart():
    data = request.json
    algorithm_text = data.get("algorithm")
    if not algorithm_text:
        return jsonify({"error": "No algorithm provided"}), 400

    if gemini_model is None:
        return jsonify({"error": "GOOGLE_API_KEY not set or model not initialized"}), 500

    # First try to generate flowchart with AI
    try:
        prompt = f"""Convert this algorithm into a Mermaid.js flowchart:

{algorithm_text}

Create a flowchart with these rules:
1. Start with: flowchart TD
2. Use simple node IDs: A, B, C, D, E, F, G, H, I, J, K, L, M, N, O, P, Q, R, S, T
3. For decisions use: A{{"condition"}}
4. For processes use: A["action"]
5. For start/end use: A(["Start"]) or A(["End"])
6. Use arrows: A --> B
7. For yes/no branches: A -->|Yes| B and A -->|No| C
8. Keep labels short and clear (max 20 characters per node)
9. Follow the exact sequence of the algorithm
10. For loops, ensure proper flow back to the loop condition
11. For complex algorithms like binary search, include all decision points and variable updates

Example format for simple algorithm:
flowchart TD
    A(["Start"])
    B["Input: Get number"]
    C{{"number % 2 == 0?"}}
    D["Output: Even"]
    E["Output: Odd"]
    F(["End"])
    A --> B
    B --> C
    C -->|Yes| D
    C -->|No| E
    D --> F
    E --> F

Example format for binary search:
flowchart TD
    A(["Start"])
    B["Input: array, target"]
    C["left=0, right=length-1"]
    D{{"left <= right?"}}
    E["mid = (left+right)/2"]
    F{{"array[mid] == target?"}}
    G["Return mid"]
    H{{"array[mid] < target?"}}
    I["left = mid + 1"]
    J["right = mid - 1"]
    K["Return -1"]
    L(["End"])
    A --> B
    B --> C
    C --> D
    D -->|Yes| E
    D -->|No| K
    E --> F
    F -->|Yes| G
    F -->|No| H
    H -->|Yes| I
    H -->|No| J
    I --> D
    J --> D
    G --> L
    K --> L

Generate the flowchart:"""

        response = gemini_model.generate_content(prompt)
        flowchart_text = getattr(response, "text", None) or getattr(response, "output_text", None)
        
        if flowchart_text:
            # Clean and validate the flowchart
            flowchart_text = flowchart_text.strip()
            
            # Remove any markdown code blocks
            if flowchart_text.startswith("```"):
                lines = flowchart_text.split('\n')
                flowchart_text = '\n'.join([line for line in lines if not line.startswith('```')])
            
            # Ensure it starts with flowchart TD
            if not flowchart_text.startswith("flowchart"):
                flowchart_text = "flowchart TD\n" + flowchart_text
            
            # Validate basic syntax
            if validate_mermaid_syntax(flowchart_text):
                return jsonify({"flowchart": flowchart_text})
        
        # If AI generation fails, use fallback
        return generate_fallback_flowchart(algorithm_text)
        
    except Exception as e:
        print("Error generating flowchart:", e)
        # Use fallback if AI fails
        return generate_fallback_flowchart(algorithm_text)

def validate_mermaid_syntax(flowchart_text):
    """Basic validation of Mermaid syntax"""
    try:
        # Check for basic required elements
        if not flowchart_text.startswith("flowchart"):
            return False
        if "-->" not in flowchart_text:
            return False
        return True
    except:
        return False

def generate_fallback_flowchart(algorithm_text):
    """Generate a simple fallback flowchart for common patterns"""
    try:
        lines = [line.strip() for line in algorithm_text.split('\n') if line.strip()]
        
        # Simple pattern detection
        flowchart = "flowchart TD\n"
        flowchart += '    A(["Start"])\n'
        
        node_id = ord('B')
        prev_node = 'A'
        
        for i, line in enumerate(lines):
            if not line or not line[0].isdigit():
                continue
                
            # Remove numbering
            content = line.split('.', 1)[1].strip() if '.' in line else line
            
            # Detect decision points
            if any(word in content.lower() for word in ['if', 'while', 'for', 'else']):
                if 'if' in content.lower() or 'while' in content.lower() or 'for' in content.lower():
                    flowchart += f'    {chr(node_id)}{{"{content[:30]}..."}}\n'
                    decision_node = chr(node_id)
                    node_id += 1
                    
                    # Add yes/no branches
                    flowchart += f'    {chr(node_id)}["Yes"]\n'
                    flowchart += f'    {chr(node_id+1)}["No"]\n'
                    flowchart += f'    {decision_node} -->|Yes| {chr(node_id)}\n'
                    flowchart += f'    {decision_node} -->|No| {chr(node_id+1)}\n'
                    prev_node = chr(node_id)
                    node_id += 2
                else:
                    flowchart += f'    {chr(node_id)}["{content[:30]}..."]\n'
                    flowchart += f'    {prev_node} --> {chr(node_id)}\n'
                    prev_node = chr(node_id)
                    node_id += 1
            else:
                flowchart += f'    {chr(node_id)}["{content[:30]}..."]\n'
                flowchart += f'    {prev_node} --> {chr(node_id)}\n'
                prev_node = chr(node_id)
                node_id += 1
        
        flowchart += f'    {chr(node_id)}(["End"])\n'
        flowchart += f'    {prev_node} --> {chr(node_id)}\n'
        
        return jsonify({"flowchart": flowchart})
        
    except Exception as e:
        print("Fallback flowchart generation failed:", e)
        # Ultimate fallback
        simple_flowchart = """flowchart TD
    A(["Start"])
    B["Process Input"]
    C{{"Decision Point"}}
    D["Action 1"]
    E["Action 2"]
    F(["End"])
    A --> B
    B --> C
    C -->|Yes| D
    C -->|No| E
    D --> F
    E --> F"""
        return jsonify({"flowchart": simple_flowchart})

@app.route("/generate-code", methods=["POST"])
def generate_code():
    data = request.json
    algorithm_text = data.get("algorithm")
    programming_language = data.get("programming_language", "python")
    
    if not algorithm_text:
        return jsonify({"error": "No algorithm provided"}), 400

    if gemini_model is None:
        return jsonify({"error": "GOOGLE_API_KEY not set or model not initialized"}), 500

    prompt = f"""Convert this algorithm into clean, simple {programming_language} code:

{algorithm_text}

Requirements:
1. Write ONLY the essential solution code
2. Keep it simple and concise
3. Include minimal necessary comments
4. NO verbose explanations or documentation
5. NO example usage or test cases
6. NO extensive error handling
7. Focus on the core algorithm implementation
8. Use clear variable names

For Python:
- Simple function with clear logic
- Basic comments only
- Use 4 spaces for indentation (no tabs)
- Follow PEP 8 style guidelines
- Ensure proper indentation for if/else, loops, and function blocks

For Java:
- Simple class with main method
- Essential code only

For JavaScript:
- Simple function
- Clean ES6+ syntax

Generate ONLY the essential {programming_language} code:"""

    try:
        response = gemini_model.generate_content(prompt)
        code_text = getattr(response, "text", None) or getattr(response, "output_text", None)
        if not code_text:
            return jsonify({"error": "Failed to generate code"}), 500
        
        # Clean up the code to remove verbose content
        cleaned_code = clean_generated_code(code_text, programming_language)
        return jsonify({"code": cleaned_code})
    except Exception as e:
        print("Error generating code:", e)
        return jsonify({"error": "Internal server error"}), 500

def clean_generated_code(code_text, language):
    """Clean up generated code to remove verbose content and keep only essential solution"""
    lines = code_text.split('\n')
    cleaned_lines = []
    
    # Remove common verbose patterns
    skip_patterns = [
        "Here's the",
        "Here is the",
        "The following",
        "This code",
        "Example usage:",
        "Test case:",
        "Sample input:",
        "Output:",
        "Explanation:",
        "Note:",
        "Remember:",
        "Make sure",
        "Don't forget",
        "You can",
        "This will",
        "The function",
        "This implementation",
        "```",
        "---",
        "===",
        "***"
    ]
    
    in_code_block = False
    for line in lines:
        original_line = line
        line = line.strip()
        
        # Skip empty lines at the beginning
        if not line and not cleaned_lines:
            continue
            
        # Check if we're entering a code block
        if line.startswith("```"):
            in_code_block = not in_code_block
            continue
            
        # If we're in a code block, add the line
        if in_code_block:
            cleaned_lines.append(original_line)  # Keep original indentation
            continue
            
        # Skip verbose explanation lines
        if any(pattern.lower() in line.lower() for pattern in skip_patterns):
            continue
            
        # Skip lines that are clearly explanations (not code)
        if (line and 
            not line.startswith(('#', '//', '/*', '*', '//', '--')) and
            not any(char in line for char in ['{', '}', '(', ')', '=', ';', ':', '->', 'def ', 'function ', 'class ', 'public ', 'private ', 'import ', 'from ', 'const ', 'let ', 'var ']) and
            not line.startswith(('if ', 'for ', 'while ', 'return ', 'print', 'console', 'System.out'))):
            continue
            
        # Add the line if it looks like code
        if line:
            cleaned_lines.append(original_line)  # Keep original indentation
    
    # Join lines and clean up
    result = '\n'.join(cleaned_lines)
    
    # Fix Python indentation if it's Python code
    if language.lower() == 'python':
        result = fix_python_indentation(result)
    
    # Remove multiple consecutive empty lines
    import re
    result = re.sub(r'\n\s*\n\s*\n', '\n\n', result)
    
    # Remove leading/trailing whitespace
    result = result.strip()
    
    return result

def fix_python_indentation(code):
    """Fix Python indentation to ensure proper syntax"""
    lines = code.split('\n')
    fixed_lines = []
    indent_level = 0
    indent_size = 4  # Standard Python indentation
    
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # Skip empty lines
        if not stripped:
            fixed_lines.append('')
            i += 1
            continue
        
        # Handle dedentation keywords (reduce indent level)
        if stripped.startswith(('else:', 'elif ', 'except:', 'finally:', 'except ')):
            indent_level = max(0, indent_level - 1)
        elif stripped.startswith(('except ', 'except:')):
            indent_level = max(0, indent_level - 1)
        
        # Add the line with proper indentation
        indent = ' ' * (indent_level * indent_size)
        fixed_lines.append(indent + stripped)
        
        # Handle indentation for next line
        if stripped.endswith(':'):
            indent_level += 1
        elif stripped.startswith(('return ', 'break', 'continue', 'pass')):
            # These usually end a block, next line should be dedented
            pass
        elif stripped.startswith(('if ', 'for ', 'while ', 'def ', 'class ', 'try:', 'with ')):
            # These start a new block
            pass
        
        i += 1
    
    return '\n'.join(fixed_lines)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
