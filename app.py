from flask import Flask, request, jsonify
import os

app = Flask(__name__)
SECRET = "mySecret12345"

@app.route('/deploy', methods=['POST'])
def deploy():
    data = request.json
    print(f"Received request: {data}")
    
    if data.get('secret') != SECRET:
        return jsonify({"error": "Invalid secret"}), 403
    
    return jsonify({"status": "received"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
