def ensure_list(val):
    if isinstance(val, list):
        return val
    elif isinstance(val, str):
        # Split string into list items if separated by newlines
        return [item.strip() for item in val.split('\n') if item.strip()]
    return []

# --- Format the Analysis Output as an HTML Fragment ---
def format_string_response(result, job_info):
    suitability = result.get("Suitability", "N/A")
    interview_questions = result.get("Interview Questions", [])
    unsuitability_reasons = ensure_list(result.get("Reasons for Unsuitability", []))
    suggestions = ensure_list(result.get("Suggestions", []))
    matched_skills = ensure_list(result.get("Matched Skills", []))
    skill_match_percentage = result.get("Skill Match Percentage", "N/A")
    
    # For "Yes" suitability, ensure that more than 5 interview questions (i.e. at least 6) are provided.
    if suitability.lower() == "yes":
        if len(interview_questions) < 5:
            default_questions = [
                {
                    "Question": "Can you walk us through your most challenging project?",
                    "Answer": "This project involved [brief description] where I overcame [specific challenge] by [solution]."
                },
                {
                    "Question": "How do you stay updated with the latest developments in your field?",
                    "Answer": "I regularly engage with industry news, attend webinars, and follow key influencers."
                },
                {
                    "Question": "What strategies do you use to overcome technical challenges?",
                    "Answer": "I analyze the problem, research solutions, and consult with colleagues when necessary."
                },
                {
                    "Question": "Can you describe a time when you had to learn a new skill quickly?",
                    "Answer": "I took an online course and applied the knowledge immediately on a real-world project."
                },
                {
                    "Question": "How do you manage deadlines when multiple projects overlap?",
                    "Answer": "I prioritize tasks, set clear milestones, and maintain regular communication with my team."
                },
            ]
            # Calculate how many more questions are needed to reach at least 6.
            questions_needed = 5 - len(interview_questions)
            interview_questions.extend(default_questions[:questions_needed])
    
    job_role = job_info.get("role", "N/A")
    job_desc = job_info.get("description", "N/A")
    job_skills = job_info.get("skills", "N/A")
    
    job_details_html = f"""
        <h3>Job Details</h3>
        <p><strong>Role:</strong> {job_role}</p>
        <p><strong>Job Description:</strong> {job_desc}</p>
        <p><strong>Skills Required:</strong> {job_skills}</p>
    """
    
    matched_skills_html = f"""
        <h3>Matched Skills</h3>
        <p><strong>Percentage of Required Skills Matched:</strong> {skill_match_percentage}%</p>
        <ul>{"".join(f"<li>{s}</li>" for s in matched_skills)}</ul>
    """
    
    if suitability.lower() == "yes":
        extra_section = f"""
            <h3>Interview Questions</h3>
            <ul>{
                "".join(
                    f"<li><strong>Q:</strong> {item.get('Question', 'N/A')}<br><strong>A:</strong> {item.get('Answer', 'N/A')}</li>" 
                    for item in interview_questions
                )
            }</ul>
        """
    else:
        extra_section = f"""
            <h3>Reasons for Unsuitability</h3>
            <ul>{"".join(f"<li>{r}</li>" for r in unsuitability_reasons)}</ul>
            <h3>Suggestions for Improvement</h3>
            <ul>{"".join(f"<li>{s}</li>" for s in suggestions)}</ul>
        """
    
    formatted_html = f"""
        <div class="analysis-result" style="border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 8px; background-color: #ffffff; color: #000000;">
            <h2>Suitability: {suitability}</h2>
            {job_details_html}
            {matched_skills_html}
            {extra_section}
        </div>
    """
    return formatted_html
