from flask import Flask, request, jsonify
from github import Github
import requests
import time
import os

# Configuration
SECRET = "mySecret12345"
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')

app = Flask(__name__)

def generate_code_with_llm(brief, checks):
    """Use AI PIPE to generate HTML/JS code based on brief"""
    import requests
    
    aipipe_token = os.environ.get('AIPIPE_TOKEN', '')
    
    prompt = f"""Create a complete single-page HTML application based on this brief:
{brief}

Requirements to check:
{chr(10).join(checks)}

Generate a complete HTML file with inline CSS and JavaScript. Make sure it meets all the requirements.
Only return the HTML code, nothing else."""
    
    response = requests.post(
        "https://aipipe.org/openrouter/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {aipipe_token}",
            "Content-Type": "application/json"
        },
        json={
            "model": "openai/gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}]
        }
    )
    
    return response.json()['choices'][0]['message']['content']

def create_github_repo(task_id, html_code):
    """Create GitHub repo, add files, enable Pages"""
    g = Github(GITHUB_TOKEN)
    user = g.get_user()
    
    repo_name = f"tds-{task_id}"
    
    # Create repo
    repo = user.create_repo(repo_name, private=False, auto_init=False)
    
    # Add index.html
    repo.create_file("index.html", "Initial commit", html_code, branch="main")
    
    # Add LICENSE
    license_text = """MIT License

Copyright (c) 2025

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""
    
    repo.create_file("LICENSE", "Add MIT license", license_text, branch="main")
    
    # Add README
    readme = f"""# {repo_name}

## Summary
This application was automatically generated based on project requirements.

## Setup
Open index.html in a browser or visit the GitHub Pages URL.

## Usage
Follow the on-screen instructions.

## Code Explanation
This is a single-page application built with HTML, CSS, and JavaScript.

## License
MIT License"""
    
    repo.create_file("README.md", "Add README", readme, branch="main")
    
    # Enable GitHub Pages
    # Enable GitHub Pages
    try:
        repo.create_pages_site(source={"branch": "main", "path": "/"})
    except Exception as e:
        print(f"Pages enable error (may already be enabled): {e}")
        # Try alternative method
        try:
            repo.edit(has_pages=True)
        except:
            pass
    
        
    return repo

def send_evaluation(evaluation_url, email, task, round_num, nonce, repo_url, commit_sha, pages_url):
    """Send repo details to evaluation URL with retry"""
    payload = {
        "email": email,
        "task": task,
        "round": round_num,
        "nonce": nonce,
        "repo_url": repo_url,
        "commit_sha": commit_sha,
        "pages_url": pages_url
    }
    
    for delay in [1, 2, 4, 8]:
        try:
            response = requests.post(evaluation_url, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
            if response.status_code == 200:
                return True
        except Exception as e:
            print(f"Evaluation error: {e}")
        time.sleep(delay)
    return False

@app.route('/deploy', methods=['POST'])
def deploy():
    data = request.json
    
    # Verify secret
    if data.get('secret') != SECRET:
        return jsonify({"error": "Invalid secret"}), 403
    
    try:
        # Extract data
        email = data['email']
        task = data['task']
        round_num = data['round']
        nonce = data['nonce']
        brief = data['brief']
        checks = data['checks']
        evaluation_url = data['evaluation_url']
        
        print(f"Processing task: {task}, round: {round_num}")
        
        # Generate code
        html_code = generate_code_with_llm(brief, checks)
        
        # Create repo
        repo = create_github_repo(task, html_code)
        
        # Wait a bit for GitHub to process
        time.sleep(5)
        
        # Get commit SHA
        commits = repo.get_commits()
        commit_sha = commits[0].sha
        
        # GitHub Pages URL
        pages_url = f"https://{repo.owner.login}.github.io/{repo.name}/"
        
        # Send evaluation
        send_evaluation(evaluation_url, email, task, round_num, nonce, 
                       repo.html_url, commit_sha, pages_url)
        
        return jsonify({"status": "success", "repo": repo.html_url}), 200
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "API is running", "endpoint": "/deploy"}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

