# format.py

# Helper to ensure list format, especially for potentially string-based list returns from LLM
def ensure_list(val):
    if isinstance(val, list):
        return val
    elif isinstance(val, str):
        # Split string into list items if separated by newlines or common delimiters, handling potential numbering
        items = []
        for line in val.split('\n'):
            line = line.strip()
            if not line:
                continue
            # Remove common list prefixes like "1. ", "- ", "* "
            if len(line) > 2 and line[1] == '.' and line[0].isdigit():
                items.append(line[2:].strip())
            elif len(line) > 1 and line[0] in ['-', '*']:
                items.append(line[1:].strip())
            else:
                items.append(line)
        return items
    return [] # Return empty list if not list or string

# Helper to ensure list of dictionaries for questions
def ensure_question_list(val):
     if isinstance(val, list):
         # Check if items are dicts with expected keys, otherwise try to parse
         if all(isinstance(item, dict) and "Question" in item and "Answer" in item for item in val):
             return val
         else:
             # Attempt basic parsing if it's a list of strings (less ideal)
             parsed_list = []
             for item in val:
                 if isinstance(item, str):
                     q_part = item
                     a_part = "N/A" # Default answer if structure is wrong
                     # Simple split logic (adjust if LLM uses different separators)
                     if "Answer:" in item:
                         parts = item.split("Answer:", 1)
                         q_part = parts[0].replace("Question:", "").strip()
                         a_part = parts[1].strip()
                     elif "A:" in item:
                          parts = item.split("A:", 1)
                          q_part = parts[0].replace("Q:", "").strip()
                          a_part = parts[1].strip()

                     parsed_list.append({"Question": q_part, "Answer": a_part})
                 elif isinstance(item, dict): # Keep existing dicts
                      parsed_list.append(item)
             return parsed_list

     return [] # Default to empty list


# --- Format the Analysis Output as an HTML Fragment ---
def format_string_response(result, job_info):
    # Extract data using .get() with defaults and ensure correct types
    suitability = result.get("Suitability", "N/A")
    # Use helpers to ensure lists
    interview_questions = ensure_question_list(result.get("Interview Questions", []))
    behavioral_questions = ensure_list(result.get("Behavioral Questions", []))
    unsuitability_reasons = ensure_list(result.get("Reasons for Unsuitability", []))
    suggestions = ensure_list(result.get("Suggestions", []))
    matched_skills = ensure_list(result.get("Matched Skills", []))
    skill_match_percentage = result.get("Skill Match Percentage", "N/A")
    
    # Format HTML base structure
    html = f"""
    <div class="analysis-result">
        <h2>Suitability: {suitability}</h2>

        <h3>Job Details</h3>
        <p><strong>Role:</strong> {job_info.get("role", "N/A")}</p>
        <p><strong>Description:</strong> {job_info.get("description", "N/A")}</p>
        <p><strong>Skills Required:</strong> {', '.join(job_info.get("skills", []))}</p>

        <h3>Matched Skills</h3>
        <p><strong>Percentage:</strong> {skill_match_percentage}%</p>
        <ul>
            {''.join(f'<li>{skill}</li>' for skill in matched_skills)}
        </ul>
    """
    
    # Add conditional sections based on suitability
    if suitability.lower() == "yes":
        tech_questions_html = "".join(
            f"<li><strong>Q:</strong> {item.get('Question', 'N/A')}<br><strong>A:</strong> {item.get('Answer', 'N/A')}</li>"
            for item in interview_questions
        )
        behav_questions_html = "".join(
            f"<li>{q}</li>"
            for q in behavioral_questions
        )

        html += f"""
            <h3>Interview Questions</h3>
            <h4>Technical Questions:</h4>
            <ul>{tech_questions_html if tech_questions_html else "<li>No technical questions generated.</li>"}</ul>
            <h4>Behavioral Questions:</h4>
            <ul>{behav_questions_html if behav_questions_html else "<li>No behavioral questions generated.</li>"}</ul>
        """
    elif suitability.lower() == "no":
        reasons_html = "".join(f"<li>{r}</li>" for r in unsuitability_reasons)
        suggestions_html = "".join(f"<li>{s}</li>" for s in suggestions)
        html += f"""
            <h3>Reasons for Unsuitability</h3>
            <ul>{reasons_html if reasons_html else "<li>No specific reasons provided.</li>"}</ul>
            <h3>Suggestions for Improvement</h3>
            <ul>{suggestions_html if suggestions_html else "<li>No specific suggestions provided.</li>"}</ul>
        """
    else:
        html += "<p>Analysis result did not clearly indicate suitability.</p>"
    
    # Close the main div
    html += "</div>"
    
    return html
